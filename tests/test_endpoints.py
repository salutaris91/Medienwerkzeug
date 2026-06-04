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


    @patch('gui.api.nas_api.ensure_nas_mounted')
    def test_nas_seasons_offline(self, mock_ensure_mounted):
        mock_ensure_mounted.return_value = False
        res = self.client.get('/api/nas-seasons?folder=Test')
        self.assertEqual(res.status_code, 200)
    def test_api_profiles_fallback(self):
        settings = self.persistence.load_settings()
        settings["profiles_path"] = "/readonly/invalid/path/profiles"
        self.persistence.save_settings(settings)
        
        with patch('gui.api.system_api.os.makedirs') as mock_makedirs:
            mock_makedirs.side_effect = [PermissionError("Access denied"), None]
            
            res = self.client.get("/api/profiles")
            self.assertEqual(res.status_code, 200)
            
            self.assertEqual(mock_makedirs.call_count, 2)
            self.assertEqual(mock_makedirs.call_args_list[0][0][0], "/readonly/invalid/path/profiles")
            self.assertEqual(mock_makedirs.call_args_list[1][0][0], os.path.join(self.temp_dir.name, "profiles"))

if __name__ == "__main__":
    unittest.main()
