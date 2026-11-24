import json
import os
import tempfile
import threading
import unittest
import urllib.parse
from unittest.mock import patch

import gui.api.project_api as project_api
import gui.core.persistence as persistence
import gui.mw_metadata as mw_metadata


class _FakeHttpResponse:
    def __init__(self, payload):
        self._bytes = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._bytes

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class TestRoadmap94LiveSearch(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.orig_env = {
            k: os.environ.get(k)
            for k in (
                "MW_SETTINGS_FILE",
                "MW_ENV_FILE",
                "MW_JOBS_STATE_FILE",
                "MW_DATA_DIR",
                "FLASK_SECRET_KEY",
            )
        }
        os.environ["MW_SETTINGS_FILE"] = os.path.join(self.temp_dir.name, "settings.json")
        os.environ["MW_ENV_FILE"] = os.path.join(self.temp_dir.name, ".env")
        os.environ["MW_JOBS_STATE_FILE"] = os.path.join(self.temp_dir.name, "jobs_state.json")
        os.environ["MW_DATA_DIR"] = self.temp_dir.name
        os.environ["FLASK_SECRET_KEY"] = "test-secret-roadmap-94"

        persistence._cached_settings = None
        persistence._cached_env = None
        project_api._inbox_cache = []
        project_api._inbox_cache_time = 0

        self.inbox_dir = os.path.join(self.temp_dir.name, "inbox")
        self.outbox_dir = os.path.join(self.temp_dir.name, "outbox")
        self.nas_root = os.path.join(self.temp_dir.name, "nas")
        os.makedirs(self.inbox_dir, exist_ok=True)
        os.makedirs(self.outbox_dir, exist_ok=True)
        os.makedirs(self.nas_root, exist_ok=True)

        settings = persistence.load_settings()
        settings.update(
            {
                "onboarded": True,
                "inbox_dir": self.inbox_dir,
                "outbox_dir": self.outbox_dir,
                "nas_root": self.nas_root,
            }
        )
        persistence.save_settings(settings)

        from gui.main import app

        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-secret-roadmap-94"
        self.app = app
        self.client = app.test_client()

    def tearDown(self):
        project_api._inbox_cache = []
        project_api._inbox_cache_time = 0
        for k, v in self.orig_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        persistence._cached_settings = None
        persistence._cached_env = None
        self.temp_dir.cleanup()

    @staticmethod
    def _parse_tmdb_call(req):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        parsed = urllib.parse.urlparse(url)
        qs = urllib.parse.parse_qs(parsed.query)
        return (
            parsed.path,
            qs.get("query", [""])[0],
            qs.get("year", [None])[0],
        )

    def test_1_tmdb_colloquial_and_apostrophe_fallback(self):
        """Colloquial queries ('Wo ist mein Auto', contractions) fall back to core content words when primary search returns 0 results."""
        calls = []
        dude_hit = {
            "id": 8859,
            "title": "Ey Mann, wo is’ mein Auto?",
            "release_date": "2000-12-15",
            "genre_ids": [35],
        }

        def fake_urlopen(req, timeout=15):
            path, q_param, year_param = self._parse_tmdb_call(req)
            calls.append((q_param, year_param))
            if q_param in ("mein Auto", "Ey Mann mein Auto", "Look Up"):
                return _FakeHttpResponse({"results": [dude_hit]})
            return _FakeHttpResponse({"results": []})

        with (
            patch.object(mw_metadata, "TMDB_API_KEY", "0" * 32),
            patch.object(mw_metadata.time, "sleep", return_value=None),
            patch("urllib.request.urlopen", side_effect=fake_urlopen),
        ):
            res1 = mw_metadata.search_tmdb_movie("Wo ist mein Auto")
            self.assertEqual(len(res1), 1)
            self.assertEqual(res1[0]["id"], 8859)
            self.assertEqual(res1[0]["name"], "Ey Mann, wo is’ mein Auto? (2000)")
            self.assertEqual(calls, [("Wo ist mein Auto", None), ("mein Auto", None)])

            calls.clear()
            res2 = mw_metadata.search_tmdb_movie("Don't What's Look Up")
            self.assertEqual(len(res2), 1)
            self.assertEqual(calls[0], ("Don't What's Look Up", None))
            self.assertEqual(calls[1], ("Look Up", None))

    def test_2_tmdb_fallback_year_hint_cand2_id_exclusion_and_call_cap(self):
        """Fallback extracts year_hint, reaches cand2 before dropping year, skips redundant year queries, caps at 2 extra calls, and skips IDs/primary hits."""
        calls = []
        dude_hit = {
            "id": 8859,
            "title": "Ey Mann, wo is’ mein Auto?",
            "release_date": "2000-12-15",
            "genre_ids": [35],
        }

        def fake_urlopen(req, timeout=15):
            path, q_param, year_param = self._parse_tmdb_call(req)
            calls.append((path, q_param, year_param))
            if q_param == "Matrix":
                return _FakeHttpResponse(
                    {"results": [{"id": 603, "title": "Matrix", "release_date": "1999-03-30", "genre_ids": [28]}]}
                )
            if q_param == "mein Auto" and year_param in ("2000", None):
                return _FakeHttpResponse({"results": [dude_hit]})
            return _FakeHttpResponse({"results": []})

        with (
            patch.object(mw_metadata, "TMDB_API_KEY", "0" * 32),
            patch.object(mw_metadata.time, "sleep", return_value=None),
            patch("urllib.request.urlopen", side_effect=fake_urlopen),
        ):
            # 1) Query with matching year -> 1st extra call uses year="2000"
            calls.clear()
            res = mw_metadata.search_tmdb_movie("Wo ist mein Auto 2000")
            self.assertEqual(len(res), 1)
            self.assertEqual(
                [(q, y) for _, q, y in calls],
                [("Wo ist mein Auto", None), ("mein Auto", "2000")],
            )

            # 2) Query with wrong year 2001 -> 1st extra call ("mein Auto", "2001") empty, 2nd extra call ("mein Auto", None) hits
            calls.clear()
            res_wrong_year = mw_metadata.search_tmdb_movie("Wo ist mein Auto 2001")
            self.assertEqual(len(res_wrong_year), 1)
            self.assertEqual(
                [(q, y) for _, q, y in calls],
                [("Wo ist mein Auto", None), ("mein Auto", "2001"), ("mein Auto", None)],
            )

            # 3) Extra wrong word + year -> cand1 ("ach mein Auto", "2000") empty, 2nd extra call reaches cand2 ("mein Auto", "2000")
            calls.clear()
            res_cand2 = mw_metadata.search_tmdb_movie("ach wo ist mein Auto 2000")
            self.assertEqual(len(res_cand2), 1)
            self.assertEqual(
                [(q, y) for _, q, y in calls],
                [("ach wo ist mein Auto", None), ("ach mein Auto", "2000"), ("mein Auto", "2000")],
            )

            # 4) Single-token gibberish with year -> primary already queried ("XyzQuuxBlorb", None), no redundant &year=2024 call!
            calls.clear()
            res_none = mw_metadata.search_tmdb_movie("XyzQuuxBlorb 2024")
            self.assertEqual(res_none, [])
            self.assertEqual([(q, y) for _, q, y in calls], [("XyzQuuxBlorb", None)])

            # 5) Multi-token gibberish -> at most 2 extra calls after primary
            calls.clear()
            res_cap = mw_metadata.search_tmdb_movie("XyzQuuxBlorb Ist Ein Testfilm 2024")
            self.assertEqual(res_cap, [])
            self.assertLessEqual(len(calls), 3)  # 1 primary + max 2 extra calls

            # 6) Primary hit -> 0 extra calls
            calls.clear()
            res_primary = mw_metadata.search_tmdb_movie("Matrix")
            self.assertEqual(len(res_primary), 1)
            self.assertEqual(len(calls), 1)

            # 7) Direct IDs with 0 results -> no word fallback
            for raw_id in ("tt9999999", "tmdb:9999999", "1917"):
                calls.clear()
                res_id = mw_metadata.search_tmdb_movie(raw_id)
                self.assertEqual(res_id, [])
                search_queries = [q for p, q, _ in calls if p.endswith("/search/movie") and q]
                self.assertLessEqual(len(search_queries), 1)

    def test_3_inbox_suggestions_and_scan_project_video_filenames(self):
        """get_inbox_suggestions and /api/scan-project return deterministically sorted non-sample video_filenames."""
        # 1) Obfuscated folder with main movie + sample
        em_dir = os.path.join(self.inbox_dir, "EMwimA2000")
        os.makedirs(os.path.join(em_dir, "Release"), exist_ok=True)
        os.makedirs(os.path.join(em_dir, "Sample"), exist_ok=True)
        with open(os.path.join(em_dir, "Release", "Ey.Mann.wo.is.mein.Auto.2000.mkv"), "wb") as f:
            f.write(b"x" * 4096)
        with open(os.path.join(em_dir, "Sample", "ey-sample.mkv"), "wb") as f:
            f.write(b"s" * 128)

        # 2) Multi-file folder (unsorted creation order CD2 before CD1)
        multi_dir = os.path.join(self.inbox_dir, "ZweiteilerOrdner")
        os.makedirs(multi_dir, exist_ok=True)
        for name in ("CD2.mkv", "CD1.mkv"):
            with open(os.path.join(multi_dir, name), "wb") as f:
                f.write(b"v" * 2048)

        # 3) Loose single file in inbox root
        with open(os.path.join(self.inbox_dir, "Solo.Film.2020.mkv"), "wb") as f:
            f.write(b"m" * 2048)

        project_api._inbox_cache = []
        project_api._inbox_cache_time = 0
        with patch("gui.api.project_api.media.get_video_codec", return_value="hevc"):
            suggestions = project_api.get_inbox_suggestions()

        by_project = {entry["project"]: entry for entry in suggestions}
        self.assertIn("EMwimA2000", by_project)
        self.assertEqual(by_project["EMwimA2000"]["video_filenames"], ["Ey.Mann.wo.is.mein.Auto.2000.mkv"])
        self.assertEqual(
            by_project["EMwimA2000"]["single_video_relpath"],
            "EMwimA2000/Release/Ey.Mann.wo.is.mein.Auto.2000.mkv",
        )
        self.assertEqual(by_project["ZweiteilerOrdner"]["video_filenames"], ["CD1.mkv", "CD2.mkv"])
        self.assertEqual(by_project["Solo.Film.2020.mkv"]["video_filenames"], [])

        with patch("gui.api.project_api.media.get_video_codec", return_value="hevc"):
            res_em = self.client.get("/api/scan-project?project=EMwimA2000")
            self.assertEqual(res_em.status_code, 200)
            self.assertEqual(res_em.get_json()["video_filenames"], ["Ey.Mann.wo.is.mein.Auto.2000.mkv"])

            res_multi = self.client.get("/api/scan-project?project=ZweiteilerOrdner")
            self.assertEqual(res_multi.status_code, 200)
            self.assertEqual(res_multi.get_json()["video_filenames"], ["CD1.mkv", "CD2.mkv"])

            res_solo = self.client.get("/api/scan-project?project=Solo.Film.2020.mkv")
            self.assertEqual(res_solo.status_code, 200)
            self.assertEqual(res_solo.get_json()["video_filenames"], ["Solo.Film.2020.mkv"])

    @patch("gui.api.search_api.mw_metadata.search_ofdb")
    @patch("gui.api.search_api.mw_metadata.search_tmdb_movie")
    def test_4_parallel_movie_search_and_resilience(self, mock_tmdb, mock_ofdb):
        """/api/search?type=movie runs TMDb and OFDb concurrently, sorts by match score, and survives single-provider errors."""
        barrier = threading.Barrier(2, timeout=2.0)
        thread_ids = []
        lock = threading.Lock()

        def tmdb_concurrent(_q):
            with lock:
                thread_ids.append(threading.get_ident())
            barrier.wait()
            return [{"id": 8859, "name": "Ey Mann, wo is’ mein Auto? (2000)"}]

        def ofdb_concurrent(_q):
            with lock:
                thread_ids.append(threading.get_ident())
            barrier.wait()
            return [{"id": "ofdb_1_auto", "title": "Auto", "year": "2000"}]

        mock_tmdb.side_effect = tmdb_concurrent
        mock_ofdb.side_effect = ofdb_concurrent

        res = self.client.get("/api/search?type=movie&q=Auto")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(set(thread_ids)), 2, "TMDb and OFDb must execute concurrently in two distinct worker threads")
        items = res.get_json()
        self.assertEqual(len(items), 2)
        self.assertEqual({it["provider"] for it in items}, {"tmdb", "ofdb"})
        # Exact title match "Auto (2000)" scores higher for query "Auto"
        self.assertEqual(items[0]["provider"], "ofdb")

        mock_tmdb.side_effect = mw_metadata.MetadataProviderUnavailable("TMDb down", status_code=503)
        mock_ofdb.side_effect = None
        mock_ofdb.return_value = [{"id": "ofdb_1_auto", "title": "Auto", "year": "2000"}]
        res_partial = self.client.get("/api/search?type=movie&q=Auto")
        self.assertEqual(res_partial.status_code, 200)
        partial_items = res_partial.get_json()
        self.assertEqual(len(partial_items), 1)
        self.assertEqual(partial_items[0]["provider"], "ofdb")


if __name__ == "__main__":
    unittest.main()
