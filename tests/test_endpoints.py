import os
import unittest
import tempfile
import json
from unittest.mock import patch, MagicMock

class TestEndpoints(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.settings_file = os.path.join(self.temp_dir.name, "settings.json")
        self.jobs_state_file = os.path.join(self.temp_dir.name, "jobs_state.json")
        self.env_file = os.path.join(self.temp_dir.name, ".env")

        os.environ["MW_SETTINGS_FILE"] = self.settings_file
        os.environ["MW_JOBS_STATE_FILE"] = self.jobs_state_file
        os.environ["MW_ENV_FILE"] = self.env_file
        os.environ["MW_DATA_DIR"] = self.temp_dir.name
        os.environ["FLASK_SECRET_KEY"] = "test-secret-key-12345"

        import gui.core.persistence as persistence
        self.persistence = persistence
        self.persistence._cached_settings = None

        from gui.main import app
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key-12345'
        self.app = app
        self.client = app.test_client()

        settings = self.persistence.load_settings()
        settings["inbox_dir"] = os.path.join(self.temp_dir.name, "inbox")
        settings["outbox_dir"] = os.path.join(self.temp_dir.name, "outbox")
        settings["nas_root"] = os.path.join(self.temp_dir.name, "nas")
        self.persistence.save_settings(settings)
        
        if settings.get("inbox_dir"):
            os.makedirs(settings["inbox_dir"], exist_ok=True)
        if settings.get("outbox_dir"):
            os.makedirs(settings["outbox_dir"], exist_ok=True)
        if settings.get("nas_root"):
            os.makedirs(settings["nas_root"], exist_ok=True)

        self.csrf_token = None
        self._login_and_get_csrf()

    def _login_and_get_csrf(self):
        self.persistence.set_password("test-password")
        res = self.client.post("/api/auth/login", json={"password": "test-password"})
        self.assertEqual(res.status_code, 200)
        cookies = self.client.get_cookie("mw_csrf_token")
        if cookies:
            self.csrf_token = cookies.value
            
    def _post(self, url, json=None):
        headers = {}
        if self.csrf_token:
            headers["X-CSRF-Token"] = self.csrf_token
        return self.client.post(url, json=json, headers=headers)

    def tearDown(self):
        os.environ.pop("MW_SETTINGS_FILE", None)
        os.environ.pop("MW_JOBS_STATE_FILE", None)
        os.environ.pop("MW_ENV_FILE", None)
        os.environ.pop("MW_DATA_DIR", None)
        os.environ.pop("FLASK_SECRET_KEY", None)
        self.temp_dir.cleanup()

    @patch("gui.api.nas_api.ensure_nas_mounted", return_value=True)
    def test_nas_series(self, mock_nas):
        res = self._post("/api/nas-series", json={"category_id": "test_cat"})
        self.assertEqual(res.status_code, 200)

    @patch("gui.api.nas_api.ensure_nas_mounted", return_value=True)
    def test_nas_seasons(self, mock_nas):
        res = self._post("/api/nas-seasons", json={"series_name": "Test Series", "category_id": "test_cat"})
        self.assertEqual(res.status_code, 200)

    @patch("gui.core.jobs.get_all_jobs", return_value=[])
    @patch("gui.core.jobs.clear_finished_jobs", return_value=None)
    def test_queue_endpoints(self, mock_clear, mock_get):
        res = self.client.get("/api/queue")
        self.assertEqual(res.status_code, 200)
        
        res = self._post("/api/queue-clear", json={"job_id": "all"})
        self.assertEqual(res.status_code, 200)
        
        # Test without body/content-type to ensure it's robust (silent=True)
        headers = {}
        if self.csrf_token:
            headers["X-CSRF-Token"] = self.csrf_token
        res_no_body = self.client.post("/api/queue-clear", headers=headers)
        self.assertEqual(res_no_body.status_code, 200)
        self.assertEqual(mock_clear.call_count, 2)

    @patch("gui.core.jobs.get_all_jobs", return_value=[{"id": "legacy-job", "status": "queued"}])
    def test_queue_endpoint_handles_incomplete_legacy_jobs(self, mock_get):
        res = self.client.get("/api/queue")

        self.assertEqual(res.status_code, 200)
        payload = res.get_json()
        self.assertEqual(payload["jobs"], [{
            "id": "legacy-job",
            "type": "unknown",
            "name": "",
            "status": "queued",
            "progress": 0,
            "message": "",
            "timestamp": 0,
            "pipeline": None,
            "project_name": ""
        }])

    @patch("gui.api.nas_api.ensure_nas_mounted", return_value=True)
    def test_streamfab_import(self, mock_nas):
        # Preview is GET
        res = self.client.get("/api/streamfab-import/preview")
        self.assertEqual(res.status_code, 200)
        
        # Import is POST
        res = self._post("/api/streamfab-import", json={"import_groups": []})
        self.assertEqual(res.status_code, 200)

    @patch("gui.api.search_api.mw_metadata.search_all_db", return_value=[])
    @patch("gui.api.search_api.mw_metadata.search_tmdb_movie", return_value=[])
    def test_search_api(self, mock_tmdb, mock_all):
        res = self._post("/api/search", json={"query": "test", "type": "show"})
        self.assertEqual(res.status_code, 200)
        
        res = self._post("/api/search", json={"query": "test", "type": "movie"})
        self.assertEqual(res.status_code, 200)

    @patch("gui.api.queue_api.job_queue.put")
    @patch("gui.core.jobs.create_job")
    def test_preview_and_process(self, mock_create, mock_put):
        # preview-process
        res = self._post("/api/preview-process", json={"folder": "test_folder"})
        self.assertEqual(res.status_code, 200)
        
        # process
        res = self._post("/api/process", json={"folder": "test_folder", "metadata": {}})
        self.assertEqual(res.status_code, 200)

    @patch('gui.mw_metadata.search_all_db')
    def test_search_provider_unavailable(self, mock_search):
        from gui.mw_metadata import MetadataProviderUnavailable
        mock_search.side_effect = MetadataProviderUnavailable("TMDB offline", status_code=503)
        res = self._post("/api/search", json={"query": "test", "type": "movie"})
        self.assertEqual(res.status_code, 503)
        self.assertIn("error", res.json)
        self.assertIn("TMDB offline", res.json["error"])

    @patch('gui.mw_metadata.search_all_db')
    def test_search_provider_invalid_key(self, mock_search):
        from gui.mw_metadata import MetadataProviderUnavailable
        mock_search.side_effect = MetadataProviderUnavailable("API-Key ungueltig", status_code=502)
        res = self._post("/api/search", json={"query": "test", "type": "movie"})
        self.assertEqual(res.status_code, 502)
        self.assertIn("error", res.json)
        self.assertIn("API-Key ungueltig", res.json["error"])

    @patch('gui.api.search_api.mw_metadata.search_tmdb_movie')
    @patch('gui.api.search_api.mw_metadata.search_ofdb')
    def test_search_resilience_partial_failure(self, mock_ofdb, mock_tmdb):
        from gui.mw_metadata import MetadataProviderUnavailable
        mock_tmdb.side_effect = MetadataProviderUnavailable("TMDB offline", status_code=503)
        mock_ofdb.return_value = [{"id": "ofdb_123_abc", "title": "Test Movie", "year": "2026"}]
        
        res = self.client.get("/api/search?q=test&type=movie")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["provider"], "ofdb")
        self.assertEqual(data[0]["name"], "Test Movie (2026)")

    @patch('gui.api.search_api.mw_metadata.search_tmdb_movie')
    @patch('gui.api.search_api.mw_metadata.search_ofdb')
    def test_search_resilience_total_failure(self, mock_ofdb, mock_tmdb):
        from gui.mw_metadata import MetadataProviderUnavailable
        mock_tmdb.side_effect = MetadataProviderUnavailable("TMDB offline", status_code=503)
        mock_ofdb.return_value = []
        
        res = self.client.get("/api/search?q=test&type=movie")
        self.assertEqual(res.status_code, 503)
        self.assertIn("error", res.json)
        self.assertIn("TMDB offline", res.json["error"])

    @patch('gui.mw_metadata.search_tmdb_tv')
    @patch('gui.mw_metadata.search_tvdb')
    @patch('gui.mw_metadata.search_tvmaze')
    def test_search_resilience_tv_partial_failure(self, mock_tvmaze, mock_tvdb, mock_tmdb):
        from gui.mw_metadata import MetadataProviderUnavailable
        mock_tmdb.side_effect = MetadataProviderUnavailable("TMDB-TV offline", status_code=502)
        mock_tvdb.side_effect = MetadataProviderUnavailable("TVDB offline", status_code=503)
        mock_tvmaze.return_value = [{"id": "tvmaze_123", "name": "Test Show (2026)"}]
        
        res = self.client.get("/api/search?q=test&type=tv")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(len(data) >= 2)
        providers = [item["provider"] for item in data]
        self.assertIn("tvmaze", providers)
        self.assertIn("mediathek", providers)

    @patch('gui.mw_metadata.search_tmdb_tv')
    @patch('gui.mw_metadata.search_tvdb')
    @patch('gui.mw_metadata.search_tvmaze')
    def test_search_resilience_tv_total_failure(self, mock_tvmaze, mock_tvdb, mock_tmdb):
        from gui.mw_metadata import MetadataProviderUnavailable
        mock_tmdb.side_effect = MetadataProviderUnavailable("TMDB-TV offline", status_code=502)
        mock_tvdb.side_effect = MetadataProviderUnavailable("TVDB offline", status_code=503)
        mock_tvmaze.return_value = []
        
        res = self.client.get("/api/search?q=test&type=tv")
        self.assertIn(res.status_code, [502, 503])
        self.assertIn("error", res.json)
        self.assertTrue("offline" in res.json["error"])



    @patch('gui.api.nas_api.ensure_nas_mounted')
    def test_nas_seasons_offline(self, mock_ensure_mounted):
        mock_ensure_mounted.return_value = False
        res = self.client.get('/api/nas-seasons?folder=Test')
        self.assertEqual(res.status_code, 200)

    @patch.dict(os.environ, {"MW_RUNTIME": "docker"})
    @patch("gui.api.youtube_api.subprocess.run")
    def test_yt_fetch_docker_skips_browser_cookies(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "title": "Test Video",
                "uploader": "Test Channel",
                "duration": 42,
                "formats": [],
                "subtitles": {},
                "automatic_captions": {}
            }),
            stderr=""
        )

        res = self._post("/api/yt/fetch", json={"url": "https://youtube.com/watch?v=abc"})

        self.assertEqual(res.status_code, 200)
        called_cmd = mock_run.call_args[0][0]
        self.assertNotIn("--cookies-from-browser", called_cmd)
        self.assertEqual(called_cmd[-1], "https://youtube.com/watch?v=abc")

    @patch.dict(os.environ, {"MW_RUNTIME": "desktop"})
    @patch("gui.api.youtube_api.subprocess.run")
    def test_yt_fetch_desktop_uses_browser_cookies_first(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "title": "Test Video",
                "uploader": "Test Channel",
                "duration": 42,
                "formats": [],
                "subtitles": {},
                "automatic_captions": {}
            }),
            stderr=""
        )

        res = self._post("/api/yt/fetch", json={"url": "https://youtube.com/watch?v=abc"})

        self.assertEqual(res.status_code, 200)
        called_cmd = mock_run.call_args[0][0]
        self.assertIn("--cookies-from-browser", called_cmd)
        self.assertIn("chrome", called_cmd)

    def test_api_profiles_fallback(self):
        settings = self.persistence.load_settings()
        settings["profiles_path"] = "/readonly/invalid/path/profiles"
        self.persistence.save_settings(settings)
        
        original_makedirs = os.makedirs
        def mock_makedirs_impl(path, exist_ok=False):
            if "invalid/path" in path:
                raise PermissionError("Access denied")
            original_makedirs(path, exist_ok=exist_ok)
            
        with patch('gui.api.system_api.os.makedirs', side_effect=mock_makedirs_impl) as mock_makedirs:
            res = self.client.get("/api/profiles")
            self.assertEqual(res.status_code, 200)
            
            self.assertEqual(mock_makedirs.call_count, 2)
            self.assertEqual(mock_makedirs.call_args_list[0][0][0], "/readonly/invalid/path/profiles")
            self.assertEqual(mock_makedirs.call_args_list[1][0][0], os.path.join(self.temp_dir.name, "profiles"))

    @patch('gui.mw_metadata.search_tmdb_tv')
    @patch('gui.mw_metadata.search_tvdb')
    @patch('gui.mw_metadata.search_tvmaze')
    def test_search_tv_provider_unavailable(self, mock_tvmaze, mock_tvdb, mock_tmdb):
        from gui.mw_metadata import MetadataProviderUnavailable
        mock_tmdb.side_effect = MetadataProviderUnavailable("TMDb TV offline", status_code=502)
        mock_tvdb.side_effect = MetadataProviderUnavailable("TVDb offline", status_code=503)
        mock_tvmaze.return_value = []
        
        res = self.client.get("/api/search?q=test&type=tv")
        self.assertEqual(res.status_code, 502)
        self.assertIn("error", res.json)
        self.assertIn("TMDb TV offline", res.json["error"])

    def test_youtube_tasks_lock_defined(self):
        from gui.workers.processor import active_yt_tasks, active_yt_tasks_lock
        from gui.api.youtube_api import active_yt_tasks as api_tasks, active_yt_tasks_lock as api_lock
        
        self.assertIsNotNone(active_yt_tasks)
        self.assertIsNotNone(active_yt_tasks_lock)
        self.assertIs(active_yt_tasks, api_tasks)
        self.assertIs(active_yt_tasks_lock, api_lock)
        
        res = self.client.get("/api/yt/segments?taskId=nonexistent")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("error", data)
        self.assertEqual(data["error"], "Task nicht gefunden.")

    @patch("gui.api.system_api.fetch_latest_github_version")
    @patch("gui.api.system_api.get_runtime_capabilities")
    @patch("gui.core.persistence.load_env_keys")
    def test_update_status_endpoint(self, mock_env_keys, mock_caps, mock_fetch):
        mock_env_keys.return_value = {}
        original_env_repo = os.environ.pop("MW_UPDATE_REPO", None)
        mock_caps.return_value = {"runtime": "desktop"}
        
        res = self.client.get("/api/update-status")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertFalse(data["update_check_available"])
        self.assertEqual(data["runtime"], "desktop")
        
        os.environ["MW_UPDATE_REPO"] = "salutaris91/Medienwerkzeug"
        mock_fetch.return_value = None
        res = self.client.get("/api/update-status")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["update_check_available"])
        self.assertIsNone(data["latest_version"])
        self.assertIn("error", data)
        
        mock_fetch.return_value = "1.1.0"
        mock_caps.return_value = {"runtime": "docker"}
        with patch("gui.api.system_api.MW_APP_VERSION", "1.0.0"):
            res = self.client.get("/api/update-status")
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertTrue(data["update_available"])
            self.assertEqual(data["latest_version"], "1.1.0")
            self.assertEqual(data["runtime"], "docker")
            self.assertEqual(data["recommended_command"], "docker compose pull && docker compose up -d")

        if original_env_repo is not None:
            os.environ["MW_UPDATE_REPO"] = original_env_repo
        else:
            os.environ.pop("MW_UPDATE_REPO", None)

if __name__ == "__main__":
    unittest.main()
