import os
import unittest
import tempfile
import json
import sys
from unittest.mock import patch, MagicMock
import queue

class TestFixSeriesQueueAndNaming(unittest.TestCase):
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

        # Explicitly patch settings paths in all modules to override import cache
        import gui.core.utils as utils
        utils.SETTINGS_FILE = self.settings_file
        utils.SETTINGS_DIR = self.temp_dir.name
        utils._cached_settings = None

        import gui.core.persistence as persistence
        persistence.SETTINGS_FILE = self.settings_file
        persistence._cached_settings = None

        import gui.core.jobs as jobs
        jobs.JOBS_STATE_FILE = self.jobs_state_file

        # Reset login rate limit failed attempts cache
        import gui.api.system_api as system_api
        with system_api.failed_attempts_lock:
            system_api.failed_attempts.clear()

        from gui.main import app
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key-12345'
        self.app = app
        self.client = app.test_client()

        settings = persistence.load_settings()
        self.inbox_dir = os.path.join(self.temp_dir.name, "inbox")
        self.outbox_dir = os.path.join(self.temp_dir.name, "outbox")
        self.nas_root = os.path.join(self.temp_dir.name, "nas")
        settings["inbox_dir"] = self.inbox_dir
        settings["outbox_dir"] = self.outbox_dir
        settings["nas_root"] = self.nas_root
        persistence.save_settings(settings)

        os.makedirs(self.inbox_dir, exist_ok=True)
        os.makedirs(self.outbox_dir, exist_ok=True)
        os.makedirs(self.nas_root, exist_ok=True)

        # Set password AFTER settings have been saved to ensure it is not overwritten
        persistence.set_password("test-password")

        self.csrf_token = None
        self._login_and_get_csrf()

        # Reset active jobs RAM cache
        jobs.active_jobs.clear()
        jobs._last_saved_time.clear()
        jobs._last_saved_progress.clear()
        jobs._jobs_loaded = False
        self.jobs = jobs

    def _login_and_get_csrf(self):
        res = self.client.post("/api/auth/login", json={"password": "test-password"})
        cookies = self.client.get_cookie("mw_csrf_token")
        if cookies:
            self.csrf_token = cookies.value

    def _post(self, url, json_data=None):
        headers = {}
        if self.csrf_token:
            headers["X-CSRF-Token"] = self.csrf_token
        return self.client.post(url, json=json_data, headers=headers)

    def tearDown(self):
        os.environ.pop("MW_SETTINGS_FILE", None)
        os.environ.pop("MW_JOBS_STATE_FILE", None)
        os.environ.pop("MW_ENV_FILE", None)
        os.environ.pop("MW_DATA_DIR", None)
        os.environ.pop("FLASK_SECRET_KEY", None)
        self.temp_dir.cleanup()

    def test_update_job_terminal_state_freezing(self):
        """Test 1: update_job freezes progress/message updates in terminal states (done/error)."""
        job_id = "test-terminal-job"
        self.jobs.create_job(job_id, "Terminal Job", "movie", {})
        
        # Set to running
        self.jobs.update_job(job_id, status="running", progress=10, message="In Arbeit")
        job = self.jobs.get_job(job_id)
        self.assertEqual(job["status"], "running")
        self.assertEqual(job["progress"], 10)
        self.assertEqual(job["message"], "In Arbeit")

        # Complete job -> done
        self.jobs.update_job(job_id, status="done", progress=100, message="Erfolgreich")
        job = self.jobs.get_job(job_id)
        self.assertEqual(job["status"], "done")
        
        # Attempt progress/message update while in done status (must be ignored)
        self.jobs.update_job(job_id, progress=50, message="Lagging thread update")
        job = self.jobs.get_job(job_id)
        self.assertEqual(job["progress"], 100)
        self.assertEqual(job["message"], "Erfolgreich")

        # Retry job -> reset status to running (must go through)
        self.jobs.update_job(job_id, status="running", progress=0, message="Wiederaufnahme")
        job = self.jobs.get_job(job_id)
        self.assertEqual(job["status"], "running")
        self.assertEqual(job["progress"], 0)
        self.assertEqual(job["message"], "Wiederaufnahme")

    @patch("gui.core.helpers.sys.platform", "linux")
    @patch("gui.core.helpers.subprocess.run")
    def test_open_folder_in_finder_safety(self, mock_run):
        """Test 5: open_folder_in_finder handles Docker runtime and Linux errors safely."""
        from gui.core.helpers import open_folder_in_finder

        # Test Docker mode: must be No-Op
        os.environ["MW_RUNTIME"] = "docker"
        open_folder_in_finder(self.temp_dir.name)
        mock_run.assert_not_called()

        # Test normal Linux mode: runs xdg-open
        os.environ.pop("MW_RUNTIME", None)
        open_folder_in_finder(self.temp_dir.name)
        mock_run.assert_called_with(["xdg-open", os.path.abspath(self.temp_dir.name)])

        # Test Linux error handling: xdg-open throws exception, should not crash
        mock_run.side_effect = OSError("No such file or directory")
        try:
            open_folder_in_finder(self.temp_dir.name)
        except Exception as e:
            self.fail(f"open_folder_in_finder raised an exception: {e}")

    @patch("gui.api.search_api.mw_metadata.fetch_tvdb")
    def test_fetch_episodes_api_error_handling(self, mock_fetch):
        """Test 4: /api/fetch-episodes returns HTTP 500 on exceptions instead of empty 200."""
        # Query known provider and force exception
        mock_fetch.side_effect = RuntimeError("Mocked TVDB exception")
        res = self.client.get("/api/fetch-episodes?provider=tvdb&show_id=123")
        self.assertEqual(res.status_code, 500)
        data = res.get_json()
        self.assertIn("error", data)
        self.assertEqual(data["status"], "error")

    @patch("gui.api.queue_api.mw_metadata.fetch_mediathek_episodes")
    def test_preview_resolution_sall_fallback(self, mock_fetch):
        """Test 6: preview_process uses ui_season when season='all' and no SxxExx pattern matches."""
        # Mock flat provider episodes list (Mediathek result, no SxxExx keys)
        mock_fetch.return_value = {
            "1": {"title": "Serengeti Tag 1", "plot": ""},
            "2": {"title": "Serengeti Tag 2", "plot": ""}
        }

        # Create dummy directory in inbox with two files
        inbox_show_dir = os.path.join(self.inbox_dir, "Serengeti")
        os.makedirs(inbox_show_dir, exist_ok=True)
        file1 = os.path.join(inbox_show_dir, "folge1.mp4")
        file2 = os.path.join(inbox_show_dir, "folge2.mp4")
        open(file1, "w").close()
        open(file2, "w").close()

        payload = {
            "media_type": "tv",  # Explicitly specify tv media_type
            "project_name": "Serengeti",
            "show_name": "Serengeti",
            "show_id": "mediathek_show_123",
            "provider": "mediathek",
            "season": "all",
            "ui_season": 3,  # Explicitly request Season 3 in UI
            "mappings": {
                "folge1.mp4": "1",
                "folge2.mp4": "2"
            }
        }

        res = self._post("/api/preview_process", json_data=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        
        # Verify that filenames are prefixed with S03 instead of Sall
        renames = data["renames"]
        self.assertEqual(len(renames), 2)
        new_names = [r["new"] for r in renames]
        self.assertIn("Serengeti - S03E01 - Tag 1.mp4", new_names)
        self.assertIn("Serengeti - S03E02 - Tag 2.mp4", new_names)

    @patch("gui.workers.processor.threading.Thread")
    @patch("gui.workers.processor.os.rename")
    @patch("gui.workers.processor.queue.Queue")
    def test_thread_lifecycle_on_exception(self, mock_queue_class, mock_rename, mock_thread_class):
        """Test 2: TV processing sequential loop wraps in try/finally to ensure transfer thread join."""
        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread
        
        # Mock Queue instance to capture puts
        mock_queue = MagicMock()
        mock_queue_class.return_value = mock_queue

        # Setup process params
        params = {
            "media_type": "tv",
            "project_name": "Serengeti",
            "show_name": "Serengeti",
            "show_id": "mediathek_show_123",
            "provider": "mediathek",
            "season": "all",
            "ui_season": 1,
            "mappings": {
                "folge1.mp4": "1"
            },
            "task_id": "test-task"
        }

        # Mock rename to raise exception
        mock_rename.side_effect = RuntimeError("Mocked rename failure")

        # Create dummy directory structure
        inbox_show_dir = os.path.join(self.inbox_dir, "Serengeti")
        os.makedirs(inbox_show_dir, exist_ok=True)
        open(os.path.join(inbox_show_dir, "folge1.mp4"), "w").close()

        # Trigger process_worker in a mock environment
        from gui.workers.processor import process_worker

        try:
            process_worker(params)
        except Exception:
            pass

        # Verify that Sentinel None was pushed to transfer_queue (mock_queue)
        # and mock_thread.join() was called in the finally block
        mock_queue.put.assert_called_with(None)
        mock_thread.join.assert_called_once()
