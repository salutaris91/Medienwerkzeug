"""Tests for the transient-failure retry around metadata JSON fetches."""

import json
import urllib.error
import urllib.request

import pytest

from gui import mw_metadata


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self._payload).encode()


def _build_request():
    return urllib.request.Request("https://example.invalid/test")


def test_fetch_json_with_retry_recovers_from_transient_timeout(monkeypatch):
    calls = []

    def fake_urlopen(request, timeout=None):
        calls.append(timeout)
        if len(calls) == 1:
            raise TimeoutError("The read operation timed out")
        return _FakeResponse({"title": "Killing Faith"})

    logged = []
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(mw_metadata.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(mw_metadata, "log_message", logged.append)

    result = mw_metadata.fetch_json_with_retry(_build_request, context="Test")

    assert result == {"title": "Killing Faith"}
    assert len(calls) == 2
    assert len(logged) == 1
    assert "Versuch 1/3" in logged[0]


def test_fetch_json_with_retry_gives_up_visibly_after_all_attempts(monkeypatch):
    attempts = []

    def fake_urlopen(request, timeout=None):
        attempts.append(1)
        raise urllib.error.URLError("timed out")

    logged = []
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(mw_metadata.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(mw_metadata, "log_message", logged.append)

    with pytest.raises(urllib.error.URLError):
        mw_metadata.fetch_json_with_retry(_build_request, context="Test")

    assert len(attempts) == 3
    assert len(logged) == 3


def test_fetch_json_with_retry_does_not_retry_http_errors(monkeypatch):
    attempts = []

    def fake_urlopen(request, timeout=None):
        attempts.append(1)
        raise urllib.error.HTTPError("https://example.invalid", 404, "not found", None, None)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(mw_metadata.time, "sleep", lambda seconds: None)

    with pytest.raises(urllib.error.HTTPError):
        mw_metadata.fetch_json_with_retry(_build_request, context="Test")

    # A 404/401 is a real answer from the service, not a transient stall.
    assert len(attempts) == 1


def test_fetch_movie_nfo_data_logs_and_returns_error_after_retries(monkeypatch):
    def fake_urlopen(request, timeout=None):
        raise TimeoutError("The read operation timed out")

    logged = []
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(mw_metadata.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(mw_metadata, "log_message", logged.append)

    result = mw_metadata.fetch_movie_nfo_data("tmdb_movie", "1200320")

    assert "TMDB-Filmmetadaten konnten nicht geladen werden" in result["error"]
    # Three retry logs plus the final visible NFO-agent failure log.
    assert any("nicht abrufbar" in line for line in logged)


def test_search_tvmaze_recovers_from_transient_urlerror(monkeypatch):
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

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(mw_metadata.time, "sleep", lambda seconds: None)

    results = mw_metadata.search_tvmaze("Dark")

    assert len(results) == 1
    assert results[0]["id"] == 1234
    assert results[0]["name"] == "Dark (2017) [Germany]"
    assert len(calls) == 2


def test_fetch_tmdb_tv_recovers_from_transient_urlerror(monkeypatch):
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

    monkeypatch.setattr(mw_metadata, "TMDB_API_KEY", "0123456789abcdef0123456789abcdef")
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(mw_metadata.time, "sleep", lambda seconds: None)

    result = mw_metadata.fetch_tmdb_tv("70523", 1, lang="de-DE")

    assert result == {"1": {"title": "Geheimnisse", "date": "2017-12-01"}}
    assert len(calls) == 2


def test_search_tvdb_recovers_from_transient_urlerror(monkeypatch):
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

    monkeypatch.setattr(mw_metadata, "get_tvdb_token", lambda: "fake_tvdb_token")
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(mw_metadata.time, "sleep", lambda seconds: None)

    results = mw_metadata.search_tvdb("Dark", lang="deu")

    assert len(results) == 1
    assert results[0]["id"] == "332606"
    assert results[0]["provider"] == "tvdb"
    assert len(calls) == 2


def test_search_mediathek_recovers_from_transient_urlerror(monkeypatch):
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

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(mw_metadata.time, "sleep", lambda seconds: None)

    results = mw_metadata.search_mediathek("Tatort")

    assert len(results) == 1
    assert results[0]["id"] == "Tatort"
    assert results[0]["name"] == "Tatort [ARD]"
    assert results[0]["provider"] == "mediathek"
    assert len(calls) == 2


def test_converted_function_does_not_retry_http_404(monkeypatch):
    attempts = []

    def fake_urlopen(request, timeout=None):
        attempts.append(request.full_url)
        raise urllib.error.HTTPError(request.full_url, 404, "Not Found", None, None)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(mw_metadata.time, "sleep", lambda seconds: None)

    # Calling search_tvmaze when server returns 404
    results = mw_metadata.search_tvmaze("NonexistentShow")

    assert results == []
    # Real HTTP error (404) is NOT retried: exactly 1 attempt
    assert len(attempts) == 1
