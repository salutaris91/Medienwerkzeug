"""Tests for the transient-failure retry around metadata JSON, HTML, and binary fetches (ROADMAP #54)."""

import http.client
import json
import os
import tempfile
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

from gui import mw_metadata


class _FakeResponse:
    def __init__(self, payload, headers=None, raw_bytes=None, read_exc=None):
        self._payload = payload
        self._raw_bytes = raw_bytes
        self._read_exc = read_exc
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        if self._read_exc is not None:
            raise self._read_exc
        if self._raw_bytes is not None:
            return self._raw_bytes
        if isinstance(self._payload, bytes):
            return self._payload
        if isinstance(self._payload, str):
            return self._payload.encode("utf-8")
        return json.dumps(self._payload).encode("utf-8")


def _build_request():
    return urllib.request.Request("https://example.invalid/test")


class TestMetadataRetry(unittest.TestCase):
    def test_fetch_json_with_retry_recovers_from_transient_timeout(self):
        calls = []

        def fake_urlopen(request, timeout=None):
            calls.append(timeout)
            if len(calls) == 1:
                raise TimeoutError("The read operation timed out")
            return _FakeResponse({"title": "Killing Faith"})

        logged = []
        with patch.object(urllib.request, "urlopen", fake_urlopen), \
             patch.object(mw_metadata.time, "sleep", lambda seconds: None), \
             patch.object(mw_metadata, "log_message", logged.append):
            result = mw_metadata.fetch_json_with_retry(_build_request, context="Test")

        self.assertEqual(result, {"title": "Killing Faith"})
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(logged), 1)
        self.assertIn("Versuch 1/3", logged[0])

    def test_fetch_json_with_retry_gives_up_visibly_after_all_attempts(self):
        attempts = []

        def fake_urlopen(request, timeout=None):
            attempts.append(1)
            raise urllib.error.URLError("timed out")

        logged = []
        with patch.object(urllib.request, "urlopen", fake_urlopen), \
             patch.object(mw_metadata.time, "sleep", lambda seconds: None), \
             patch.object(mw_metadata, "log_message", logged.append):
            with self.assertRaises(urllib.error.URLError):
                mw_metadata.fetch_json_with_retry(_build_request, context="Test")

        self.assertEqual(len(attempts), 3)
        self.assertEqual(len(logged), 3)

    def test_fetch_json_with_retry_does_not_retry_http_errors(self):
        attempts = []

        def fake_urlopen(request, timeout=None):
            attempts.append(1)
            raise urllib.error.HTTPError("https://example.invalid", 404, "not found", None, None)

        with patch.object(urllib.request, "urlopen", fake_urlopen), \
             patch.object(mw_metadata.time, "sleep", lambda seconds: None):
            with self.assertRaises(urllib.error.HTTPError):
                mw_metadata.fetch_json_with_retry(_build_request, context="Test")

        self.assertEqual(len(attempts), 1)

    def test_fetch_movie_nfo_data_logs_and_returns_error_after_retries(self):
        def fake_urlopen(request, timeout=None):
            raise TimeoutError("The read operation timed out")

        logged = []
        with patch.object(urllib.request, "urlopen", fake_urlopen), \
             patch.object(mw_metadata.time, "sleep", lambda seconds: None), \
             patch.object(mw_metadata, "log_message", logged.append):
            result = mw_metadata.fetch_movie_nfo_data("tmdb_movie", "1200320")

        self.assertIn("TMDB-Filmmetadaten konnten nicht geladen werden", result["error"])
        self.assertTrue(any("nicht abrufbar" in line for line in logged))

    def test_search_tvmaze_recovers_from_transient_urlerror(self):
        calls = []

        def fake_urlopen(request, timeout=None):
            calls.append(request.full_url)
            if len(calls) == 1:
                raise urllib.error.URLError("Connection reset by peer")
            return _FakeResponse([
                {
                    "show": {
                        "id": 1234,
                        "name": "Dark",
                        "premiered": "2017-12-01",
                        "network": {"country": {"name": "Germany"}},
                    }
                }
            ])

        with patch.object(urllib.request, "urlopen", fake_urlopen), \
             patch.object(mw_metadata.time, "sleep", lambda seconds: None):
            results = mw_metadata.search_tvmaze("Dark")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], 1234)
        self.assertEqual(results[0]["name"], "Dark (2017) [Germany]")
        self.assertEqual(len(calls), 2)

    def test_fetch_tmdb_tv_recovers_from_transient_urlerror(self):
        calls = []

        def fake_urlopen(request, timeout=None):
            calls.append(request.full_url)
            if len(calls) == 1:
                raise urllib.error.URLError("timed out")
            return _FakeResponse({
                "episodes": [
                    {
                        "episode_number": 1,
                        "name": "Geheimnisse",
                        "air_date": "2017-12-01",
                    }
                ]
            })

        with patch.object(mw_metadata, "TMDB_API_KEY", "0123456789abcdef0123456789abcdef"), \
             patch.object(urllib.request, "urlopen", fake_urlopen), \
             patch.object(mw_metadata.time, "sleep", lambda seconds: None):
            result = mw_metadata.fetch_tmdb_tv("70523", 1, lang="de-DE")

        self.assertEqual(result, {"1": {"title": "Geheimnisse", "date": "2017-12-01"}})
        self.assertEqual(len(calls), 2)

    def test_search_tvdb_recovers_from_transient_urlerror(self):
        calls = []

        def fake_urlopen(request, timeout=None):
            calls.append(request.full_url)
            if len(calls) == 1:
                raise urllib.error.URLError("Temporary failure in name resolution")
            return _FakeResponse({
                "data": [
                    {
                        "tvdb_id": 332606,
                        "name": "Dark",
                        "year": "2017",
                        "translations": {"deu": "Dark"},
                        "country": "deu",
                    }
                ]
            })

        with patch.object(mw_metadata, "get_tvdb_token", lambda: "fake_tvdb_token"), \
             patch.object(urllib.request, "urlopen", fake_urlopen), \
             patch.object(mw_metadata.time, "sleep", lambda seconds: None):
            results = mw_metadata.search_tvdb("Dark", lang="deu")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "332606")
        self.assertEqual(results[0]["provider"], "tvdb")
        self.assertEqual(len(calls), 2)

    def test_search_mediathek_recovers_from_transient_urlerror(self):
        calls = []

        def fake_urlopen(request, timeout=None):
            calls.append(request.full_url)
            if len(calls) == 1:
                raise urllib.error.URLError("Connection refused")
            return _FakeResponse({
                "result": {
                    "results": [
                        {
                            "topic": "Tatort",
                            "title": "Tatort: Borowski",
                            "channel": "ARD",
                        }
                    ]
                }
            })

        with patch.object(urllib.request, "urlopen", fake_urlopen), \
             patch.object(mw_metadata.time, "sleep", lambda seconds: None):
            results = mw_metadata.search_mediathek("Tatort")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "Tatort")
        self.assertEqual(results[0]["name"], "Tatort [ARD]")
        self.assertEqual(results[0]["provider"], "mediathek")
        self.assertEqual(len(calls), 2)

    def test_converted_function_does_not_retry_http_404(self):
        attempts = []

        def fake_urlopen(request, timeout=None):
            attempts.append(request.full_url)
            raise urllib.error.HTTPError(request.full_url, 404, "Not Found", None, None)

        with patch.object(urllib.request, "urlopen", fake_urlopen), \
             patch.object(mw_metadata.time, "sleep", lambda seconds: None):
            results = mw_metadata.search_tvmaze("NonexistentShow")

        self.assertEqual(results, [])
        self.assertEqual(len(attempts), 1)

    def test_e4_ak3_html_retries_search_ofdb_fernsehserien_and_mediathek_topic(self):
        # 1. search_ofdb recovers from transient timeout and does not retry HTTP 404
        ofdb_calls = []
        ofdb_html = (
            '<table><tr><td><a href="https://www.ofdb.de/film/391234,Killing-Faith">'
            '<span class="tooltipster">Killing Faith</span></a></td><td>2025</td></tr></table>'
        )

        def fake_ofdb_urlopen(request, timeout=None):
            ofdb_calls.append(request.full_url)
            if len(ofdb_calls) == 1:
                raise TimeoutError("OFDb search read timeout")
            return _FakeResponse(ofdb_html)

        with patch.object(urllib.request, "urlopen", fake_ofdb_urlopen), \
             patch.object(mw_metadata.time, "sleep", lambda seconds: None), \
             patch.object(mw_metadata, "log_message", lambda msg: None):
            results = mw_metadata.search_ofdb("Killing Faith")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "ofdb_391234_Killing-Faith")
        self.assertEqual(results[0]["title"], "Killing Faith")
        self.assertEqual(results[0]["year"], "2025")
        self.assertEqual(len(ofdb_calls), 2)

        ofdb_404_calls = []

        def fake_ofdb_404(request, timeout=None):
            ofdb_404_calls.append(request.full_url)
            raise urllib.error.HTTPError(request.full_url, 404, "Not Found", None, None)

        with patch.object(urllib.request, "urlopen", fake_ofdb_404), \
             patch.object(mw_metadata.time, "sleep", lambda seconds: None):
            self.assertEqual(mw_metadata.search_ofdb("Killing Faith"), [])
        self.assertEqual(len(ofdb_404_calls), 1)

        # 2. get_fernsehserien_episodes recovers from transient URLError and does not retry 404
        fs_calls = []
        fs_html = (
            '<td class="episodenliste-episodennummer">1.</td>'
            '<span itemprop="name">Der Anfang</span>'
        )

        def fake_fs_urlopen(request, timeout=None):
            fs_calls.append(request.full_url)
            if len(fs_calls) == 1:
                raise urllib.error.URLError("temporary stall")
            return _FakeResponse(fs_html)

        with patch.object(urllib.request, "urlopen", fake_fs_urlopen), \
             patch.object(mw_metadata.time, "sleep", lambda seconds: None), \
             patch.object(mw_metadata, "log_message", lambda msg: None):
            episodes = mw_metadata.get_fernsehserien_episodes("Dark", 1)

        self.assertEqual(episodes, {"1": "Der Anfang"})
        self.assertEqual(len(fs_calls), 2)

        fs_404_calls = []

        def fake_fs_404(request, timeout=None):
            fs_404_calls.append(request.full_url)
            raise urllib.error.HTTPError(request.full_url, 404, "Not Found", None, None)

        with patch.object(urllib.request, "urlopen", fake_fs_404), \
             patch.object(mw_metadata.time, "sleep", lambda seconds: None):
            self.assertEqual(mw_metadata.get_fernsehserien_episodes("Unknown", 1), {})
        self.assertEqual(len(fs_404_calls), 1)

        # 3. resolve_mediathek_url_topic uses opener with fetch_html_with_retry and does not retry HTTP 404
        opener_calls = []

        class _FakeOpener:
            def open(self, request, timeout=None):
                opener_calls.append((request.full_url, timeout))
                if len(opener_calls) == 1:
                    raise TimeoutError("Mediathek redirect stall")
                return _FakeResponse("<html><head><title>Vorschau: Terra X - Die Erde | ZDFmediathek</title></head></html>")

        with patch.object(urllib.request, "build_opener", return_value=_FakeOpener()), \
             patch.object(mw_metadata.time, "sleep", lambda seconds: None), \
             patch.object(mw_metadata, "log_message", lambda msg: None):
            topic = mw_metadata.resolve_mediathek_url_topic("https://www.zdf.de/dokumentation/terra-x/folge-1.html")

        self.assertEqual(topic, "Terra X")
        self.assertEqual(len(opener_calls), 2)

        opener_404_calls = []

        class _FakeOpener404:
            def open(self, request, timeout=None):
                opener_404_calls.append(request.full_url)
                raise urllib.error.HTTPError(request.full_url, 404, "Not Found", None, None)

        with patch.object(urllib.request, "build_opener", return_value=_FakeOpener404()), \
             patch.object(mw_metadata.time, "sleep", lambda seconds: None):
            fallback_topic = mw_metadata.resolve_mediathek_url_topic("https://www.ardmediathek.de/sendung/terra-x/12345")
        self.assertEqual(fallback_topic, "Terra X")
        self.assertEqual(len(opener_404_calls), 1)

    def test_e4_ak3_binary_download_with_retry_and_byte_integrity(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # 1. Recovers from transient TimeoutError on first attempt and writes complete file on second
            target_ok = os.path.join(tmp_dir, "poster.jpg")
            payload_bytes = b"\xff\xd8\xff\xe0" + b"x" * 120
            dl_calls = []

            def fake_dl_recover(request, timeout=None):
                dl_calls.append(request)
                if len(dl_calls) == 1:
                    raise TimeoutError("socket read timed out")
                return _FakeResponse(
                    None,
                    headers={"Content-Length": str(len(payload_bytes))},
                    raw_bytes=payload_bytes,
                )

            logged = []
            with patch.object(urllib.request, "urlopen", fake_dl_recover), \
                 patch.object(mw_metadata.time, "sleep", lambda seconds: None), \
                 patch.object(mw_metadata, "log_message", logged.append):
                mw_metadata._download_with_timeout("https://image.tmdb.org/t/p/original/poster.jpg", target_ok)

            self.assertEqual(len(dl_calls), 2)
            self.assertIsNot(dl_calls[0], dl_calls[1], "Each attempt must build a fresh Request")
            self.assertTrue(os.path.exists(target_ok))
            with open(target_ok, "rb") as f:
                self.assertEqual(f.read(), payload_bytes)
            self.assertEqual(len(logged), 1)

            # 2. Incomplete byte stream (Content-Length mismatch) retries and leaves NO partial file on failure
            target_partial = os.path.join(tmp_dir, "truncated.jpg")
            partial_calls = []

            def fake_dl_truncated(request, timeout=None):
                partial_calls.append(1)
                return _FakeResponse(
                    None,
                    headers={"Content-Length": "100"},
                    raw_bytes=b"x" * 40,
                )

            with patch.object(urllib.request, "urlopen", fake_dl_truncated), \
                 patch.object(mw_metadata.time, "sleep", lambda seconds: None), \
                 patch.object(mw_metadata, "log_message", lambda msg: None):
                with self.assertRaises(OSError) as ctx:
                    mw_metadata._download_with_retry("https://image.tmdb.org/t/p/original/trunc.jpg", target_partial)

            self.assertIn("Unvollständiger Download", str(ctx.exception))
            self.assertEqual(len(partial_calls), 3)
            self.assertFalse(os.path.exists(target_partial), "No truncated file may remain on disk")

            # 2b. http.client.IncompleteRead raised inside r.read() recovers on retry or fails cleanly after 3 attempts
            target_inc_ok = os.path.join(tmp_dir, "incomplete_recover.jpg")
            inc_recover_calls = []

            def fake_dl_incomplete_recover(request, timeout=None):
                inc_recover_calls.append(request)
                if len(inc_recover_calls) == 1:
                    return _FakeResponse(
                        None,
                        headers={"Content-Length": str(len(payload_bytes))},
                        read_exc=http.client.IncompleteRead(b"x" * 40, len(payload_bytes) - 40),
                    )
                return _FakeResponse(
                    None,
                    headers={"Content-Length": str(len(payload_bytes))},
                    raw_bytes=payload_bytes,
                )

            with patch.object(urllib.request, "urlopen", fake_dl_incomplete_recover), \
                 patch.object(mw_metadata.time, "sleep", lambda seconds: None), \
                 patch.object(mw_metadata, "log_message", lambda msg: None):
                mw_metadata._download_with_retry("https://image.tmdb.org/t/p/original/inc_ok.jpg", target_inc_ok)

            self.assertEqual(len(inc_recover_calls), 2)
            self.assertTrue(os.path.exists(target_inc_ok))
            with open(target_inc_ok, "rb") as f:
                self.assertEqual(f.read(), payload_bytes)

            target_inc_fail = os.path.join(tmp_dir, "incomplete_fail.jpg")
            inc_fail_calls = []

            def fake_dl_incomplete_fail(request, timeout=None):
                inc_fail_calls.append(1)
                return _FakeResponse(
                    None,
                    headers={"Content-Length": "100"},
                    read_exc=http.client.IncompleteRead(b"x" * 40, 60),
                )

            with patch.object(urllib.request, "urlopen", fake_dl_incomplete_fail), \
                 patch.object(mw_metadata.time, "sleep", lambda seconds: None), \
                 patch.object(mw_metadata, "log_message", lambda msg: None):
                with self.assertRaises(OSError) as ctx_inc:
                    mw_metadata._download_with_retry("https://image.tmdb.org/t/p/original/inc_fail.jpg", target_inc_fail)

            self.assertIn("40 von 100 Bytes", str(ctx_inc.exception))
            self.assertIsInstance(ctx_inc.exception.__cause__, http.client.IncompleteRead)
            self.assertEqual(len(inc_fail_calls), 3)
            self.assertFalse(os.path.exists(target_inc_fail))

            # 3. 0-byte response raises OSError, retries, and leaves no 0-byte file on disk
            target_empty = os.path.join(tmp_dir, "empty.jpg")
            empty_calls = []

            def fake_dl_empty(request, timeout=None):
                empty_calls.append(1)
                return _FakeResponse(None, raw_bytes=b"")

            with patch.object(urllib.request, "urlopen", fake_dl_empty), \
                 patch.object(mw_metadata.time, "sleep", lambda seconds: None), \
                 patch.object(mw_metadata, "log_message", lambda msg: None):
                with self.assertRaises(OSError) as ctx_empty:
                    mw_metadata._download_with_retry("https://image.tmdb.org/t/p/original/empty.jpg", target_empty)

            self.assertIn("0 Bytes", str(ctx_empty.exception))
            self.assertEqual(len(empty_calls), 3)
            self.assertFalse(os.path.exists(target_empty), "No 0-byte file may remain on disk")

            # 4. HTTP 404 is NOT retried
            target_404 = os.path.join(tmp_dir, "missing.jpg")
            http_404_calls = []

            def fake_dl_404(request, timeout=None):
                http_404_calls.append(1)
                raise urllib.error.HTTPError(request.full_url, 404, "Not Found", None, None)

            with patch.object(urllib.request, "urlopen", fake_dl_404), \
                 patch.object(mw_metadata.time, "sleep", lambda seconds: None):
                with self.assertRaises(urllib.error.HTTPError):
                    mw_metadata._download_with_retry("https://image.tmdb.org/t/p/original/404.jpg", target_404)

            self.assertEqual(len(http_404_calls), 1)
            self.assertFalse(os.path.exists(target_404))


if __name__ == "__main__":
    unittest.main()
