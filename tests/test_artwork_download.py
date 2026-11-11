"""Tests for Etappe E5 — Artwork-Auswahl (ROADMAP #92, #51): E5-AK1, E5-AK2, Option 1A/2A/3A."""

import base64
import json
import os
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

from flask import Flask

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gui import mw_metadata
from gui.api.search_api import search_api
import gui.core.persistence as persistence
import gui.workers.processor as processor


VALID_TMDB_KEY = "0123456789abcdef0123456789abcdef"
SAMPLE_JPEG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00" + b"J" * 64
SAMPLE_PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"P" * 64
SAMPLE_WEBP_BYTES = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"W" * 32


class _FakeHttpResponse:
    def __init__(self, payload=None, headers=None, raw_bytes=None):
        self._payload = payload
        self._raw_bytes = raw_bytes
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        if self._raw_bytes is not None:
            return self._raw_bytes
        if isinstance(self._payload, bytes):
            return self._payload
        if isinstance(self._payload, str):
            return self._payload.encode("utf-8")
        return json.dumps(self._payload).encode("utf-8")


class TestArtworkDownload(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.register_blueprint(search_api, url_prefix="/api")
        self.client = self.app.test_client()

    def test_e5_ak1_fetch_tmdb_image_candidates_vs_fetch_tmdb_images(self):
        """E5-AK1: fetch_tmdb_image_candidates returns sorted candidate lists while fetch_tmdb_images stays a single-URL dict."""
        tmdb_images_payload = {
            "posters": [
                {"file_path": "/en_poster.jpg", "iso_639_1": "en", "width": 1000, "height": 1500},
                {"file_path": "/neutral_poster.jpg", "iso_639_1": None, "width": 2000, "height": 3000},
                {"file_path": "/de_poster_1.jpg", "iso_639_1": "de", "width": 1000, "height": 1500},
                {"file_path": "/de_poster_2.jpg", "iso_639_1": "de", "width": 1400, "height": 2100},
                {"file_path": "invalid_no_slash.jpg", "iso_639_1": "de"},
            ],
            "backdrops": [
                {"file_path": "/en_bd.jpg", "iso_639_1": "en", "width": 1920, "height": 1080},
                {"file_path": "/neutral_bd.jpg", "iso_639_1": "", "width": 3840, "height": 2160},
            ],
            "logos": [
                {"file_path": "/en_logo.png", "iso_639_1": "en", "width": 800, "height": 300},
                {"file_path": "/de_logo.png", "iso_639_1": "de", "width": 900, "height": 350},
            ],
        }

        with patch.object(mw_metadata, "TMDB_API_KEY", VALID_TMDB_KEY), \
             patch.object(urllib.request, "urlopen", return_value=_FakeHttpResponse(tmdb_images_payload)):
            single_res = mw_metadata.fetch_tmdb_images("movie", "603")
            cand_res = mw_metadata.fetch_tmdb_image_candidates("movie", "603")

        # 1. fetch_tmdb_images signature & return contract is unchanged (single URL string per role)
        self.assertEqual(single_res, {
            "poster": "https://image.tmdb.org/t/p/original/de_poster_1.jpg",
            "backdrop": "https://image.tmdb.org/t/p/original/neutral_bd.jpg",
            "logo": "https://image.tmdb.org/t/p/original/de_logo.png",
        })

        # 2. fetch_tmdb_image_candidates returns sorted lists (de -> neutral -> en) with original + thumb URLs
        self.assertEqual(cand_res["tmdb_id"], "603")
        self.assertEqual(
            [p["url"] for p in cand_res["posters"]],
            [
                "https://image.tmdb.org/t/p/original/de_poster_1.jpg",
                "https://image.tmdb.org/t/p/original/de_poster_2.jpg",
                "https://image.tmdb.org/t/p/original/neutral_poster.jpg",
                "https://image.tmdb.org/t/p/original/en_poster.jpg",
            ],
        )
        self.assertEqual(cand_res["posters"][0]["thumb_url"], "https://image.tmdb.org/t/p/w185/de_poster_1.jpg")
        self.assertEqual(cand_res["posters"][0]["lang"], "de")
        self.assertEqual(cand_res["posters"][0]["width"], 1000)
        self.assertEqual(cand_res["posters"][0]["height"], 1500)
        self.assertEqual(cand_res["posters"][0]["url"], single_res["poster"])

        self.assertEqual(
            [b["thumb_url"] for b in cand_res["backdrops"]],
            [
                "https://image.tmdb.org/t/p/w300/neutral_bd.jpg",
                "https://image.tmdb.org/t/p/w300/en_bd.jpg",
            ],
        )
        self.assertEqual(cand_res["backdrops"][0]["url"], single_res["backdrop"])

        self.assertEqual(
            [l["thumb_url"] for l in cand_res["logos"]],
            [
                "https://image.tmdb.org/t/p/w185/de_logo.png",
                "https://image.tmdb.org/t/p/w185/en_logo.png",
            ],
        )
        self.assertEqual(cand_res["logos"][0]["url"], single_res["logo"])

        # Missing TMDB_API_KEY raises MetadataKeyMissing
        with patch.object(mw_metadata, "TMDB_API_KEY", ""):
            with self.assertRaises(mw_metadata.MetadataKeyMissing):
                mw_metadata.fetch_tmdb_image_candidates("movie", "603")

    def test_option_2a_resolve_movie_artwork_candidates_and_api_endpoint(self):
        """Option 2A: /api/artwork/candidates resolves direct tmdb_id or falls back to TMDb title+year search."""
        fake_candidates = {
            "tmdb_id": "603",
            "posters": [{"url": "https://image.tmdb.org/t/p/original/p1.jpg", "thumb_url": "https://image.tmdb.org/t/p/w185/p1.jpg", "lang": "de", "width": 1000, "height": 1500}],
            "backdrops": [],
            "logos": [],
        }
        fake_search_results = [
            {"id": 604, "name": "Matrix Reloaded (2003)"},
            {"id": 603, "name": "Matrix (1999)"},
        ]

        with patch.object(mw_metadata, "TMDB_API_KEY", VALID_TMDB_KEY), \
             patch.object(mw_metadata, "search_tmdb_movie", return_value=fake_search_results) as mock_search, \
             patch.object(mw_metadata, "fetch_tmdb_image_candidates", return_value=fake_candidates) as mock_fetch:
            # 1. Direct numeric tmdb_id does not search by title
            res_direct = self.client.get("/api/artwork/candidates?tmdb_id=603")
            self.assertEqual(res_direct.status_code, 200)
            data_direct = res_direct.get_json()
            self.assertEqual(data_direct["tmdb_id"], "603")
            self.assertEqual(len(data_direct["posters"]), 1)
            mock_search.assert_not_called()
            mock_fetch.assert_called_once_with("movie", "603", limit_per_role=24)

            mock_fetch.reset_mock()

            # 2. Non-numeric movie_id (e.g. OFDb) + query + year searches TMDb and picks matching year (1999 -> id 603)
            res_search = self.client.post(
                "/api/artwork/candidates",
                json={"tmdb_id": "ofdb_154_Die-Matrix", "query": "Matrix", "year": "1999"},
            )
            self.assertEqual(res_search.status_code, 200)
            data_search = res_search.get_json()
            self.assertEqual(data_search["tmdb_id"], "603")
            self.assertEqual(data_search["matched_title"], "Matrix (1999)")
            self.assertEqual(len(data_search["matches"]), 2)
            mock_search.assert_called_once_with("Matrix")
            mock_fetch.assert_called_once_with("movie", "603", limit_per_role=24)

        # 3. Missing key returns 503 with error message
        with patch.object(mw_metadata, "TMDB_API_KEY", ""):
            res_err = self.client.get("/api/artwork/candidates?tmdb_id=603")
            self.assertEqual(res_err.status_code, 503)
            self.assertIn("TMDB_API_KEY", res_err.get_json()["error"])

        # 4. Non-object POST JSON bodies (list, string, number) return clean 400 JSON error instead of unhandled 500
        for invalid_body in (["x"], "x", 123):
            with self.subTest(invalid_body=invalid_body):
                res_bad_json = self.client.post("/api/artwork/candidates", json=invalid_body)
                self.assertEqual(res_bad_json.status_code, 400)
                bad_payload = res_bad_json.get_json()
                self.assertIsInstance(bad_payload, dict)
                self.assertIn("error", bad_payload)

    def test_e5_ak2_download_retry_integrity_deselection_and_ssrf_guard(self):
        """E5-AK2 & Option 3A: Selected artwork uses retry + integrity check; 'none' suppresses fallback; SSRF URLs rejected."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # 1. Transient failure on 1st attempt recovers on 2nd attempt; old poster.png is cleaned up
            old_png = os.path.join(tmp_dir, "poster.png")
            with open(old_png, "wb") as f:
                f.write(b"old-png")

            dl_attempts = []

            def fake_urlopen_recover(req, timeout=None):
                dl_attempts.append(req.full_url)
                if len(dl_attempts) == 1:
                    raise TimeoutError("transient read timeout")
                return _FakeHttpResponse(
                    headers={"Content-Length": str(len(SAMPLE_JPEG_BYTES))},
                    raw_bytes=SAMPLE_JPEG_BYTES,
                )

            with patch.object(urllib.request, "urlopen", fake_urlopen_recover), \
                 patch.object(mw_metadata.time, "sleep", lambda s: None), \
                 patch.object(mw_metadata, "log_message", lambda msg: None):
                res = mw_metadata.apply_movie_artwork_overrides(
                    tmp_dir,
                    "Matrix (1999)",
                    {"poster": {"mode": "url", "url": "https://image.tmdb.org/t/p/original/selected_poster.jpg"}},
                    settings={"media_server": "emby"},
                )

            self.assertTrue(res["poster"]["ok"])
            self.assertEqual(len(dl_attempts), 2)
            self.assertTrue(os.path.exists(os.path.join(tmp_dir, "poster.jpg")))
            self.assertFalse(os.path.exists(old_png), "Old poster.png must be removed after new poster.jpg succeeds")

            # 2. Truncated download (Content-Length mismatch) fails after 3 attempts, preserves existing poster.jpg, leaves no .part
            trunc_attempts = []

            def fake_urlopen_truncated(req, timeout=None):
                trunc_attempts.append(1)
                return _FakeHttpResponse(
                    headers={"Content-Length": "500"},
                    raw_bytes=b"\xff\xd8\xff" + b"x" * 20,
                )

            with patch.object(urllib.request, "urlopen", fake_urlopen_truncated), \
                 patch.object(mw_metadata.time, "sleep", lambda s: None), \
                 patch.object(mw_metadata, "log_message", lambda msg: None):
                res_trunc = mw_metadata.apply_movie_artwork_overrides(
                    tmp_dir,
                    "Matrix (1999)",
                    {"poster": {"mode": "url", "url": "https://image.tmdb.org/t/p/original/broken.png"}},
                    settings={"media_server": "emby"},
                )

            self.assertFalse(res_trunc["poster"]["ok"])
            self.assertEqual(len(trunc_attempts), 3)
            self.assertFalse(os.path.exists(os.path.join(tmp_dir, "poster.png.part")))
            self.assertFalse(os.path.exists(os.path.join(tmp_dir, "poster.png")))
            self.assertTrue(os.path.exists(os.path.join(tmp_dir, "poster.jpg")), "Existing poster.jpg must remain intact on failed update")

            # 3. SSRF guard rejects non-TMDb domains, http://, path traversal, and non-image extensions
            for bad_url in (
                "http://image.tmdb.org/t/p/original/poster.jpg",
                "https://evil.example.com/t/p/original/poster.jpg",
                "https://127.0.0.1/t/p/original/poster.jpg",
                "https://image.tmdb.org/t/p/original/../secret.jpg",
                "https://image.tmdb.org/other/path/poster.jpg",
                "https://image.tmdb.org/t/p/original/vector.svg",
                "file:///etc/passwd",
            ):
                with self.subTest(bad_url=bad_url):
                    with self.assertRaises(ValueError):
                        mw_metadata.validate_tmdb_image_url(bad_url)

        # 4. Deselection ('none') in generate_movie_nfo suppresses both fetch_tmdb_images and data['poster_path']/['backdrop_path'] fallback
        with tempfile.TemporaryDirectory() as nfo_dir:
            movie_api_data = {
                "title": "Matrix",
                "original_title": "The Matrix",
                "overview": "Plot",
                "release_date": "1999-03-30",
                "poster_path": "/fallback_poster.jpg",
                "backdrop_path": "/fallback_backdrop.jpg",
                "genres": [{"name": "Sci-Fi"}],
                "release_dates": {"results": []},
                "credits": {"cast": []},
            }
            downloaded_urls = []

            def fake_download(url, path, *args, **kwargs):
                downloaded_urls.append(url)
                with open(path, "wb") as f:
                    f.write(SAMPLE_JPEG_BYTES)
                return len(SAMPLE_JPEG_BYTES)

            with patch.object(mw_metadata, "TMDB_API_KEY", VALID_TMDB_KEY), \
                 patch.object(mw_metadata, "load_settings", return_value={"media_server": "emby"}), \
                 patch.object(mw_metadata, "fetch_json_with_retry", return_value=movie_api_data), \
                 patch.object(mw_metadata, "fetch_tmdb_images") as mock_fetch_imgs, \
                 patch.object(mw_metadata, "_download_with_retry", side_effect=fake_download):
                nfo_res = mw_metadata.generate_movie_nfo(
                    "603",
                    nfo_dir,
                    "Matrix (1999)",
                    overwrite=True,
                    artwork_overrides={
                        "poster": "none",
                        "backdrop": {"mode": "url", "url": "https://image.tmdb.org/t/p/original/custom_bd.jpg"},
                        "logo": "none",
                    },
                )

            mock_fetch_imgs.assert_not_called()
            self.assertEqual(downloaded_urls, ["https://image.tmdb.org/t/p/original/custom_bd.jpg"])
            self.assertFalse(nfo_res["poster"])
            self.assertTrue(nfo_res["fanart"])
            self.assertFalse(nfo_res["logo"])
            self.assertFalse(os.path.exists(os.path.join(nfo_dir, "poster.jpg")))
            self.assertTrue(os.path.exists(os.path.join(nfo_dir, "fanart.jpg")))

    def test_option_1a_local_upload_magic_bytes_and_size_validation(self):
        """Option 1A: Valid JPEG/PNG/WebP data URLs are saved by magic bytes; spoofed or oversized files are rejected."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            jpeg_b64 = "data:image/jpeg;base64," + base64.b64encode(SAMPLE_JPEG_BYTES).decode("ascii")
            png_b64 = "data:image/png;base64," + base64.b64encode(SAMPLE_PNG_BYTES).decode("ascii")
            webp_b64 = "data:image/webp;base64," + base64.b64encode(SAMPLE_WEBP_BYTES).decode("ascii")

            res = mw_metadata.apply_movie_artwork_overrides(
                tmp_dir,
                "Matrix (1999)",
                {
                    "poster": {"mode": "upload", "data_url": jpeg_b64},
                    "backdrop": {"mode": "upload", "data_url": webp_b64},
                    "logo": {"mode": "upload", "data_url": png_b64},
                },
                settings={"media_server": "emby"},
            )
            self.assertTrue(res["poster"]["ok"])
            self.assertTrue(res["backdrop"]["ok"])
            self.assertTrue(res["logo"]["ok"])
            self.assertTrue(os.path.isfile(os.path.join(tmp_dir, "poster.jpg")))
            self.assertTrue(os.path.isfile(os.path.join(tmp_dir, "fanart.webp")))
            self.assertTrue(os.path.isfile(os.path.join(tmp_dir, "logo.png")))

            # Spoofed SVG/HTML with image/jpeg MIME header is rejected by magic-byte check
            spoofed_svg = "data:image/jpeg;base64," + base64.b64encode(b"<svg onload=alert(1)></svg>").decode("ascii")
            with self.assertRaises(ValueError):
                mw_metadata.decode_and_validate_uploaded_image(spoofed_svg)

            # Oversized payload is rejected before/during decode
            with self.assertRaises(ValueError):
                mw_metadata.decode_and_validate_uploaded_image(jpeg_b64, max_bytes=10)

    def test_processor_applies_artwork_overrides_for_ofdb_and_manual_imports(self):
        """Option 1A & 2A: processor.py applies artwork_overrides even when NFO provider is 'ofdb' or 'manual'."""
        with tempfile.TemporaryDirectory() as tmp_root:
            orig_env = {
                k: os.environ.get(k)
                for k in ("MW_SETTINGS_FILE", "MW_JOBS_STATE_FILE", "MW_ENV_FILE", "MW_DATA_DIR")
            }
            try:
                os.environ["MW_SETTINGS_FILE"] = os.path.join(tmp_root, "settings.json")
                os.environ["MW_JOBS_STATE_FILE"] = os.path.join(tmp_root, "jobs_state.json")
                os.environ["MW_ENV_FILE"] = os.path.join(tmp_root, ".env")
                os.environ["MW_DATA_DIR"] = tmp_root
                persistence._cached_settings = None
                persistence._cached_env = None

                inbox_dir = os.path.join(tmp_root, "inbox")
                outbox_dir = os.path.join(tmp_root, "outbox")
                nas_root = os.path.join(tmp_root, "nas")
                os.makedirs(inbox_dir, exist_ok=True)
                os.makedirs(outbox_dir, exist_ok=True)
                os.makedirs(nas_root, exist_ok=True)

                persistence.save_settings({
                    "inbox_dir": inbox_dir,
                    "outbox_dir": outbox_dir,
                    "nas_root": nas_root,
                    "media_server": "emby",
                    "storage_targets": [{"id": "nas", "type": "nas", "root_path": nas_root, "enabled": True}],
                })

                proj_dir = os.path.join(inbox_dir, "Matrix_OFDb")
                os.makedirs(proj_dir, exist_ok=True)
                with open(os.path.join(proj_dir, "matrix.mkv"), "wb") as f:
                    f.write(b"video")

                def fake_ofdb_nfo(mid, folder, base):
                    with open(os.path.join(folder, f"{base}.nfo"), "w", encoding="utf-8") as nf:
                        nf.write('<?xml version="1.0" encoding="UTF-8"?>\n<movie><title>Matrix</title></movie>\n')
                    return {"nfo": True}

                png_data_url = "data:image/png;base64," + base64.b64encode(SAMPLE_PNG_BYTES).decode("ascii")

                with patch("gui.core.trash.send_to_trash", return_value=True), \
                     patch("gui.workers.processor.ensure_nas_mounted", return_value=True), \
                     patch("gui.workers.processor.run_rsync_with_progress", return_value=True), \
                     patch("gui.mw_metadata.generate_ofdb_nfo", side_effect=fake_ofdb_nfo), \
                     patch.object(
                         urllib.request,
                         "urlopen",
                         return_value=_FakeHttpResponse(
                             headers={"Content-Length": str(len(SAMPLE_JPEG_BYTES))},
                             raw_bytes=SAMPLE_JPEG_BYTES,
                         ),
                     ):
                    processor.process_worker({
                        "project_name": "Matrix_OFDb",
                        "media_type": "movie",
                        "movie_name": "Matrix (1999)",
                        "movie_id": "ofdb_154_Die-Matrix",
                        "provider": "ofdb",
                        "convert": False,
                        "copy_to_nas": False,
                        "copy_to_pcloud": False,
                        "delete_original": False,
                        "overwrite_nfo": False,
                        "wizard_overrides": True,
                        "nfo_overrides": {"movie": {"title": "Matrix", "year": "1999", "fsk": "16"}},
                        "artwork_overrides": {
                            "poster": {"mode": "url", "url": "https://image.tmdb.org/t/p/original/tmdb_poster_for_ofdb.jpg"},
                            "backdrop": "none",
                            "logo": {"mode": "upload", "data_url": png_data_url},
                        },
                    })

                out_movie_dir = os.path.join(outbox_dir, "Filme", "Matrix (1999)")
                self.assertTrue(os.path.isfile(os.path.join(out_movie_dir, "poster.jpg")))
                self.assertTrue(os.path.isfile(os.path.join(out_movie_dir, "logo.png")))
                self.assertFalse(os.path.exists(os.path.join(out_movie_dir, "fanart.jpg")))
            finally:
                for k, v in orig_env.items():
                    if v is None:
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = v
                persistence._cached_settings = None
                persistence._cached_env = None

    def test_generate_movie_nfo_early_branches_return_logo_flag(self):
        """Early return branches (manual, url_mediathek:, http(s)://, 'existiert') include consistent 'logo' flag."""
        png_data_url = "data:image/png;base64," + base64.b64encode(SAMPLE_PNG_BYTES).decode("ascii")
        overrides = {"logo": {"mode": "upload", "data_url": png_data_url}}

        with patch.object(mw_metadata, "load_settings", return_value={"media_server": "emby"}), \
             patch.object(mw_metadata, "log_message", lambda msg: None), \
             patch.object(mw_metadata, "fetch_ytdlp_url_metadata", return_value=[]):
            for tmdb_arg in ("manual", "url_mediathek:Tatort", "https://example.org/video"):
                with self.subTest(tmdb_arg=tmdb_arg), tempfile.TemporaryDirectory() as tmp_dir:
                    res = mw_metadata.generate_movie_nfo(
                        tmdb_arg,
                        tmp_dir,
                        "TestFilm (2024)",
                        overwrite=True,
                        artwork_overrides=overrides,
                    )
                    self.assertTrue(res["nfo"])
                    self.assertFalse(res["poster"])
                    self.assertFalse(res["fanart"])
                    self.assertTrue(res["logo"])
                    self.assertTrue(os.path.isfile(os.path.join(tmp_dir, "logo.png")))

    def test_e5b_multi_backdrop_emby_jellyfin_cleanup_and_processor(self):
        """E5b: Ordered multi-backdrop saves fanart/backdrop + -1/-2, cleans stale extras, rejects poster/logo/>10, and survives processor."""
        png_data_url = "data:image/png;base64," + base64.b64encode(SAMPLE_PNG_BYTES).decode("ascii")
        multi_spec = {
            "mode": "multi",
            "items": [
                {"mode": "url", "url": "https://image.tmdb.org/t/p/original/bd_main.jpg"},
                {"mode": "url", "url": "https://image.tmdb.org/t/p/original/bd_second.jpg"},
                {"mode": "upload", "data_url": png_data_url},
            ],
        }

        # 1. Direct validation: poster/logo multi and >10 backdrops raise ValueError
        for invalid_role in ("poster", "logo"):
            with self.assertRaises(ValueError):
                mw_metadata._parse_artwork_override_spec(multi_spec, role=invalid_role)
        too_many_spec = {
            "mode": "multi",
            "items": [
                {"mode": "url", "url": f"https://image.tmdb.org/t/p/original/bd_{i}.jpg"}
                for i in range(11)
            ],
        }
        with self.assertRaises(ValueError):
            mw_metadata._parse_artwork_override_spec(too_many_spec, role="backdrop")

        # 2. Jellyfin naming (backdrop.jpg, backdrop-1.jpg, backdrop-2.png) + stale extra cleanup
        with tempfile.TemporaryDirectory() as jf_dir:
            stale_extra = os.path.join(jf_dir, "backdrop-3.jpg")
            with open(stale_extra, "wb") as sf:
                sf.write(b"stale")

            with patch.object(
                urllib.request,
                "urlopen",
                side_effect=lambda req, timeout=None: _FakeHttpResponse(
                    headers={"Content-Length": str(len(SAMPLE_JPEG_BYTES))},
                    raw_bytes=SAMPLE_JPEG_BYTES,
                ),
            ), patch.object(mw_metadata, "log_message", lambda msg: None):
                res_jf = mw_metadata.apply_movie_artwork_overrides(
                    jf_dir,
                    "Matrix (1999)",
                    {"backdrop": multi_spec, "poster": multi_spec},
                    settings={"media_server": "jellyfin"},
                )
                self.assertTrue(res_jf["backdrop"]["ok"])
                self.assertFalse(res_jf["poster"]["ok"])
                self.assertIn("backdrop", res_jf["poster"]["error"])
                self.assertTrue(os.path.isfile(os.path.join(jf_dir, "backdrop.jpg")))
                self.assertTrue(os.path.isfile(os.path.join(jf_dir, "backdrop-1.jpg")))
                self.assertTrue(os.path.isfile(os.path.join(jf_dir, "backdrop-2.png")))
                self.assertFalse(os.path.exists(stale_extra))

                # Switching back to a single backdrop cleans up backdrop-1.jpg and backdrop-2.png
                res_single = mw_metadata.apply_movie_artwork_overrides(
                    jf_dir,
                    "Matrix (1999)",
                    {"backdrop": {"mode": "url", "url": "https://image.tmdb.org/t/p/original/bd_only.jpg"}},
                    settings={"media_server": "jellyfin"},
                )
                self.assertTrue(res_single["backdrop"]["ok"])
                self.assertTrue(os.path.isfile(os.path.join(jf_dir, "backdrop.jpg")))
                self.assertFalse(os.path.exists(os.path.join(jf_dir, "backdrop-1.jpg")))
                self.assertFalse(os.path.exists(os.path.join(jf_dir, "backdrop-2.png")))

        # 3. Full processor.process_worker run (Emby): fanart.jpg, fanart-1.jpg, fanart-2.png reach Outbox movie folder
        with tempfile.TemporaryDirectory() as tmp_root:
            orig_env = {
                k: os.environ.get(k)
                for k in ("MW_SETTINGS_FILE", "MW_JOBS_STATE_FILE", "MW_ENV_FILE", "MW_DATA_DIR")
            }
            try:
                os.environ["MW_SETTINGS_FILE"] = os.path.join(tmp_root, "settings.json")
                os.environ["MW_JOBS_STATE_FILE"] = os.path.join(tmp_root, "jobs_state.json")
                os.environ["MW_ENV_FILE"] = os.path.join(tmp_root, ".env")
                os.environ["MW_DATA_DIR"] = tmp_root
                persistence._cached_settings = None
                persistence._cached_env = None

                inbox_dir = os.path.join(tmp_root, "inbox")
                outbox_dir = os.path.join(tmp_root, "outbox")
                nas_root = os.path.join(tmp_root, "nas")
                os.makedirs(inbox_dir, exist_ok=True)
                os.makedirs(outbox_dir, exist_ok=True)
                os.makedirs(nas_root, exist_ok=True)

                persistence.save_settings({
                    "inbox_dir": inbox_dir,
                    "outbox_dir": outbox_dir,
                    "nas_root": nas_root,
                    "media_server": "emby",
                    "storage_targets": [{"id": "nas", "type": "nas", "root_path": nas_root, "enabled": True}],
                })

                proj_dir = os.path.join(inbox_dir, "Matrix_Multi")
                os.makedirs(proj_dir, exist_ok=True)
                with open(os.path.join(proj_dir, "matrix.mkv"), "wb") as f:
                    f.write(b"video")

                with patch("gui.core.trash.send_to_trash", return_value=True), \
                     patch("gui.workers.processor.ensure_nas_mounted", return_value=True), \
                     patch("gui.workers.processor.run_rsync_with_progress", return_value=True), \
                     patch.object(
                         urllib.request,
                         "urlopen",
                         side_effect=lambda req, timeout=None: _FakeHttpResponse(
                             headers={"Content-Length": str(len(SAMPLE_JPEG_BYTES))},
                             raw_bytes=SAMPLE_JPEG_BYTES,
                         ),
                     ):
                    processor.process_worker({
                        "project_name": "Matrix_Multi",
                        "media_type": "movie",
                        "movie_name": "Matrix (1999)",
                        "movie_id": "manual",
                        "provider": "manual",
                        "convert": False,
                        "copy_to_nas": False,
                        "copy_to_pcloud": False,
                        "delete_original": False,
                        "overwrite_nfo": False,
                        "wizard_overrides": True,
                        "nfo_overrides": {"movie": {"title": "Matrix", "year": "1999"}},
                        "artwork_overrides": {"backdrop": multi_spec},
                    })

                out_movie_dir = os.path.join(outbox_dir, "Filme", "Matrix (1999)")
                self.assertTrue(os.path.isfile(os.path.join(out_movie_dir, "fanart.jpg")))
                self.assertTrue(os.path.isfile(os.path.join(out_movie_dir, "fanart-1.jpg")))
                self.assertTrue(os.path.isfile(os.path.join(out_movie_dir, "fanart-2.png")))
            finally:
                for k, v in orig_env.items():
                    if v is None:
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = v
                persistence._cached_settings = None
                persistence._cached_env = None


if __name__ == "__main__":
    unittest.main()
