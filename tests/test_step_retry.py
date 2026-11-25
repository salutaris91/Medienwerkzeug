import os
import unittest
import tempfile
import json
import shutil
from unittest.mock import patch, MagicMock

class TestStepRetry(unittest.TestCase):
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

        import gui.core.utils as utils
        utils.SETTINGS_FILE = self.settings_file
        utils.SETTINGS_DIR = self.temp_dir.name
        utils._cached_settings = None

        import gui.core.persistence as persistence
        persistence.SETTINGS_FILE = self.settings_file
        persistence._cached_settings = None

        import gui.core.jobs as jobs
        jobs.JOBS_STATE_FILE = self.jobs_state_file
        self.jobs = jobs

        from gui.main import app
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key-12345'
        self.app = app
        self.client = app.test_client()

        settings = persistence.load_settings()
        self.inbox_dir = os.path.join(self.temp_dir.name, "inbox")
        self.outbox_dir = os.path.join(self.temp_dir.name, "outbox")
        self.nas_root = os.path.join(self.temp_dir.name, "nas")
        settings["data_dir"] = self.temp_dir.name
        settings["inbox_dir"] = self.inbox_dir
        settings["outbox_dir"] = self.outbox_dir
        settings["nas_root"] = self.nas_root
        settings["storage_targets"] = [
            {"id": "nas", "type": "nas", "root_path": self.nas_root, "enabled": True, "name": "NAS Target"},
            {"id": "pcloud", "type": "pcloud", "enabled": False, "name": "Cloud Target"}
        ]
        persistence.save_settings(settings)

        os.makedirs(self.inbox_dir, exist_ok=True)
        os.makedirs(self.outbox_dir, exist_ok=True)
        os.makedirs(self.nas_root, exist_ok=True)

        persistence.set_password("test-password")
        self.csrf_token = None
        self._login_and_get_csrf()

        self.jobs.active_jobs.clear()
        with self.jobs._job_controls_lock:
            self.jobs._job_controls.clear()
        self.jobs._last_saved_time.clear()
        self.jobs._last_saved_progress.clear()
        self.jobs._jobs_loaded = False

    def _login_and_get_csrf(self):
        self.client.post("/api/auth/login", json={"password": "test-password"})
        cookie = self.client.get_cookie("mw_csrf_token")
        if cookie:
            self.csrf_token = cookie.value

    def _post(self, url, json_data=None):
        headers = {}
        if self.csrf_token:
            headers["X-CSRF-Token"] = self.csrf_token
        return self.client.post(url, json=json_data, headers=headers)

    def tearDown(self):
        from gui.core.helpers import job_queue, _job_log_handles, close_job_log
        with job_queue.mutex:
            job_queue.queue.clear()
            job_queue.unfinished_tasks = 0
        for tid in list(_job_log_handles.keys()):
            close_job_log(tid)
        os.environ.pop("MW_SETTINGS_FILE", None)
        os.environ.pop("MW_JOBS_STATE_FILE", None)
        os.environ.pop("MW_ENV_FILE", None)
        os.environ.pop("MW_DATA_DIR", None)
        os.environ.pop("FLASK_SECRET_KEY", None)
        self.temp_dir.cleanup()

    def test_pipeline_merging_on_retry(self):
        """test_pipeline_merging_on_retry: Verifies that Done steps are preserved and new targets merged."""
        job_id = "test-retry-job"
        pipeline = {
            "metadata": {"status": "done", "progress": 100},
            "convert": {"status": "error", "progress": 40},
            "nas": {"status": "pending", "progress": 0}
        }
        params = {
            "show_id": "123",
            "provider": "tvdb",
            "convert": True,
            "copy_to_nas": True,
            "copy_to_pcloud": True
        }
        self.jobs.create_job(job_id, "Test Retry", "tv", params, pipeline=pipeline, status="error")

        # Now simulate user editing storage targets in settings (enabling pcloud target)
        import gui.core.persistence as persistence
        settings = persistence.load_settings()
        settings["storage_targets"][1]["enabled"] = True
        persistence.save_settings(settings)

        # Trigger retry through endpoint
        res = self._post("/api/queue/retry", {"task_id": job_id})
        self.assertEqual(res.status_code, 200)

        job = self.jobs.get_job(job_id)
        self.assertEqual(job["status"], "queued")
        self.assertEqual(job["progress"], 0)

        new_pipeline = job["pipeline"]
        # Metadata must stay Done with progress 100
        self.assertEqual(new_pipeline["metadata"]["status"], "done")
        self.assertEqual(new_pipeline["metadata"]["progress"], 100)

        # Convert was error, must become pending with progress 0
        self.assertEqual(new_pipeline["convert"]["status"], "pending")
        self.assertEqual(new_pipeline["convert"]["progress"], 0)

        # NAS was pending, stays pending with progress 0
        self.assertEqual(new_pipeline["nas"]["status"], "pending")
        self.assertEqual(new_pipeline["nas"]["progress"], 0)

        # New pCloud target was enabled in settings, must be merged as pending
        self.assertIn("pcloud", new_pipeline)
        self.assertEqual(new_pipeline["pcloud"]["status"], "pending")
        self.assertEqual(new_pipeline["pcloud"]["progress"], 0)

    @patch("gui.workers.processor.mw_metadata.generate_tvshow_nfo")
    @patch("gui.workers.processor.mw_metadata.fetch_tvdb")
    @patch("gui.workers.processor.run_rsync_with_progress")
    @patch("gui.workers.processor.ensure_nas_mounted")
    def test_tv_show_step_retry(self, mock_nas_mounted, mock_rsync, mock_fetch_tvdb, mock_tvshow_nfo):
        """test_tv_show_step_retry: Tests TV show retry when Episode 1 is done/processed and Episode 2 needs work."""
        mock_nas_mounted.return_value = True
        mock_rsync.return_value = True
        mock_fetch_tvdb.return_value = {
            "1": {"title": "Episode One"},
            "2": {"title": "Episode Two"}
        }

        # Setup folders
        show_dir = os.path.join(self.inbox_dir, "MyShow")
        os.makedirs(show_dir, exist_ok=True)
        # Only Episode 2 is left in the inbox (Episode 1 was successfully processed and moved in first run)
        ep2_file = os.path.join(show_dir, "video2.mp4")
        with open(ep2_file, "w") as f:
            f.write("video2 content")

        # Episode 1 is already in the outbox
        outbox_show_dir = os.path.join(self.outbox_dir, "Serien", "MyShow", "Staffel 1", "MyShow - S01E01 - Episode One")
        os.makedirs(outbox_show_dir, exist_ok=True)
        ep1_outbox = os.path.join(outbox_show_dir, "MyShow - S01E01 - Episode One.mp4")
        with open(ep1_outbox, "w") as f:
            f.write("video1 content")

        # Setup job and pipeline state
        job_id = "tv-show-retry-job"
        pipeline = {
            "metadata": {"status": "done", "progress": 100},
            "convert": {"status": "done", "progress": 100},
            "nas": {"status": "error", "progress": 50}
        }
        params = {
            "media_type": "tv",
            "show_name": "MyShow",
            "show_id": "123",
            "provider": "tvdb",
            "season": "1",
            "convert": False,
            "copy_to_nas": True,
            "mappings": {
                "video1.mp4": 1,
                "video2.mp4": 2
            },
            "project_name": "MyShow",
            "task_id": job_id
        }
        # Manifest maps video1.mp4 to its processed target filename and outbox dir
        manifest = {
            "video1.mp4": {
                "target_filename": "MyShow - S01E01 - Episode One.mp4",
                "dest_dir_outbox": outbox_show_dir,
                "clean_title": "MyShow - S01E01 - Episode One",
                "season": 1,
                "episode": 1
            }
        }

        # Create job with manifest
        job = self.jobs.create_job(job_id, "TV Show", "tv", params, pipeline=pipeline, status="queued")
        self.jobs.update_job(job_id, manifest=manifest, status="error")

        # Trigger retry API endpoint to merge pipeline
        res = self._post("/api/queue/retry", {"task_id": job_id})
        self.assertEqual(res.status_code, 200)

        # Now run the worker using the updated parameters
        from gui.workers.processor import process_worker
        updated_job = self.jobs.get_job(job_id)
        
        # We need to simulate that we process inside MyShow dir
        params_with_dir = updated_job["params"].copy()
        params_with_dir["current_dir"] = show_dir
        
        # Run worker synchronously (simulating job_queue_worker lifecycle)
        process_worker(params_with_dir)
        job_state = self.jobs.get_job(job_id)
        if job_state and job_state.get("status") != "error":
            self.jobs.update_job(job_id, status="done", progress=100, message="Erfolgreich beendet")

        # Check outcomes:
        # 1. tvshow.nfo should NOT be generated again since metadata was done
        mock_tvshow_nfo.assert_not_called()

        # 2. Episode 2 must be processed and moved to outbox
        outbox_ep2_dir = os.path.join(self.outbox_dir, "Serien", "MyShow", "Staffel 1", "MyShow - S01E02 - Episode Two")
        ep2_outbox = os.path.join(outbox_ep2_dir, "MyShow - S01E02 - Episode Two.mp4")
        self.assertTrue(os.path.exists(ep2_outbox))

        # 3. Rsync (NAS target) must have been called for BOTH episodes (since nas target copy was error/pending)
        # mock_rsync calls: call(src_ep1, dest_ep1, ...), call(src_ep2, dest_ep2, ...)
        self.assertEqual(mock_rsync.call_count, 2)

        # 4. Job status must be done now
        self.assertEqual(self.jobs.get_job(job_id)["status"], "done")

    @patch("gui.workers.processor.run_ytdlp_with_progress")
    @patch("gui.workers.processor.run_rsync_with_progress")
    @patch("gui.workers.processor.ensure_nas_mounted")
    def test_youtube_download_step_retry(self, mock_nas_mounted, mock_rsync, mock_ytdlp):
        """test_youtube_download_step_retry: Tests YouTube download retry when download is already done but copy failed."""
        mock_nas_mounted.return_value = True
        mock_rsync.return_value = True

        # Setup folders
        temp_yt_dir = os.path.join(self.inbox_dir, ".temp_yt_yt-retry-job")
        os.makedirs(temp_yt_dir, exist_ok=True) # Usually empty on retry

        outbox_show_dir = os.path.join(self.outbox_dir, "Serien", "MyShow", "Staffel 1", "MyShow - S01E01 - Ep1")
        os.makedirs(outbox_show_dir, exist_ok=True)
        ep1_outbox = os.path.join(outbox_show_dir, "MyShow - S01E01 - Ep1.mp4")
        with open(ep1_outbox, "w") as f:
            f.write("video content")

        # Setup job and pipeline state
        job_id = "yt-retry-job"
        pipeline = {
            "metadata": {"status": "done", "progress": 100},
            "convert": {"status": "skipped", "progress": 0},
            "nas": {"status": "error", "progress": 0}
        }
        params = {
            "media_type": "youtube",
            "metadata_mode": "tv",
            "show_name": "MyShow",
            "show_id": "123",
            "provider": "tvdb",
            "season": "1",
            "episode": "1",
            "yt_url": "https://youtube.com/watch?v=123",
            "yt_urls": ["https://youtube.com/watch?v=123"],
            "url": "https://youtube.com/watch?v=123",
            "copy_to_nas": True,
            "task_id": job_id,
            "destination_id": "2"
        }
        manifest = {
            "video1.mp4": {
                "target_filename": "MyShow - S01E01 - Ep1.mp4",
                "dest_dir_outbox": outbox_show_dir,
                "clean_title": "MyShow - S01E01 - Ep1",
                "season": 1,
                "episode": 1
            }
        }

        # Create job with manifest
        self.jobs.create_job(job_id, "YouTube Show", "youtube", params, pipeline=pipeline, status="queued")
        self.jobs.update_job(job_id, manifest=manifest, status="error")

        # Trigger retry API endpoint to merge pipeline
        res = self._post("/api/queue/retry", {"task_id": job_id})
        self.assertEqual(res.status_code, 200)

        # Run worker
        from gui.workers.processor import process_worker
        updated_job = self.jobs.get_job(job_id)
        process_worker(updated_job["params"])

        # Check outcomes:
        # 1. yt-dlp should NOT be called since metadata is done
        mock_ytdlp.assert_not_called()

        # 2. Rsync must be called to copy the already present outbox file to the NAS
        mock_rsync.assert_called_once()
        self.assertEqual(self.jobs.get_job(job_id)["status"], "done")

    def test_retry_pcloud_enabled_but_not_selected(self):
        """Tests that if pcloud target is enabled in settings but not selected in job, it stays skipped on retry."""
        job_id = "pcloud-not-selected-job"
        pipeline = {
            "metadata": {"status": "done", "progress": 100},
            "convert": {"status": "skipped", "progress": 0},
            "nas": {"status": "error", "progress": 0}
        }
        params = {
            "show_id": "123",
            "provider": "tvdb",
            "convert": False,
            "copy_to_nas": True,
            # copy_to_pcloud is explicitly False
            "copy_to_pcloud": False
        }
        self.jobs.create_job(job_id, "Test Pcloud Selected", "tv", params, pipeline=pipeline, status="error")

        # Enable pcloud target in settings
        import gui.core.persistence as persistence
        settings = persistence.load_settings()
        settings["storage_targets"][1]["enabled"] = True
        persistence.save_settings(settings)

        # Trigger retry
        res = self._post("/api/queue/retry", {"task_id": job_id})
        self.assertEqual(res.status_code, 200)

        job = self.jobs.get_job(job_id)
        new_pipeline = job["pipeline"]
        
        # NAS target was error, must become pending
        self.assertEqual(new_pipeline["nas"]["status"], "pending")
        # pCloud target was enabled in settings, but NOT selected in job params -> must remain skipped
        self.assertEqual(new_pipeline["pcloud"]["status"], "skipped")

    @patch("gui.workers.processor.mw_metadata.generate_tvshow_nfo")
    @patch("gui.workers.processor.mw_metadata.fetch_tvdb")
    @patch("gui.workers.processor.run_rsync_with_progress")
    @patch("gui.workers.processor.ensure_nas_mounted")
    def test_tv_show_retry_manifest_but_outbox_missing(self, mock_nas_mounted, mock_rsync, mock_fetch_tvdb, mock_tvshow_nfo):
        """Tests that TV Show retry does NOT bypass when manifest exists but the file is missing from outbox."""
        mock_nas_mounted.return_value = True
        mock_rsync.return_value = True
        mock_fetch_tvdb.return_value = {
            "1": {"title": "Episode One"}
        }

        # Setup folders
        show_dir = os.path.join(self.inbox_dir, "MyShow")
        os.makedirs(show_dir, exist_ok=True)
        # Episode 1 is in inbox
        ep1_file = os.path.join(show_dir, "video1.mp4")
        with open(ep1_file, "w") as f:
            f.write("video1 content")

        # File is NOT in the outbox (even though it's in the manifest)
        outbox_show_dir = os.path.join(self.outbox_dir, "Serien", "MyShow", "Staffel 1", "MyShow - S01E01 - Episode One")
        # Ensure directory doesn't have the file
        if os.path.exists(outbox_show_dir):
            shutil.rmtree(outbox_show_dir)

        # Setup job and pipeline state
        job_id = "tv-show-retry-missing-outbox-job"
        pipeline = {
            "metadata": {"status": "done", "progress": 100},
            "convert": {"status": "done", "progress": 100},
            "nas": {"status": "error", "progress": 50}
        }
        params = {
            "media_type": "tv",
            "show_name": "MyShow",
            "show_id": "123",
            "provider": "tvdb",
            "season": "1",
            "convert": False,
            "copy_to_nas": True,
            "mappings": {
                "video1.mp4": 1
            },
            "project_name": "MyShow",
            "task_id": job_id
        }
        manifest = {
            "video1.mp4": {
                "target_filename": "MyShow - S01E01 - Episode One.mp4",
                "dest_dir_outbox": outbox_show_dir,
                "clean_title": "MyShow - S01E01 - Episode One",
                "season": 1,
                "episode": 1
            }
        }

        self.jobs.create_job(job_id, "TV Show", "tv", params, pipeline=pipeline, status="queued")
        self.jobs.update_job(job_id, manifest=manifest, status="error")

        # Retry
        res = self._post("/api/queue/retry", {"task_id": job_id})
        self.assertEqual(res.status_code, 200)

        # Run worker
        from gui.workers.processor import process_worker
        updated_job = self.jobs.get_job(job_id)
        params_with_dir = updated_job["params"].copy()
        params_with_dir["current_dir"] = show_dir
        
        process_worker(params_with_dir)

        # The file was missing in outbox, so the worker MUST have processed it (moved/renamed it)
        ep1_outbox = os.path.join(outbox_show_dir, "MyShow - S01E01 - Episode One.mp4")
        self.assertTrue(os.path.exists(ep1_outbox), "File should have been re-moved to outbox because it was missing.")

    @patch("gui.workers.processor.run_ytdlp_with_progress")
    @patch("gui.workers.processor.run_rsync_with_progress")
    @patch("gui.workers.processor.ensure_nas_mounted")
    def test_youtube_retry_manifest_but_outbox_missing(self, mock_nas_mounted, mock_rsync, mock_ytdlp):
        """Tests that YouTube retry does NOT bypass when manifest exists but the file is missing from outbox."""
        mock_nas_mounted.return_value = True
        mock_rsync.return_value = True
        mock_ytdlp.return_value = True

        # Setup folders
        temp_yt_dir = os.path.join(self.inbox_dir, ".temp_yt_yt-retry-missing-job")
        os.makedirs(temp_yt_dir, exist_ok=True)

        outbox_show_dir = os.path.join(self.outbox_dir, "Serien", "MyShow", "Staffel 1", "MyShow - S01E01 - Ep1")
        if os.path.exists(outbox_show_dir):
            shutil.rmtree(outbox_show_dir)

        job_id = "yt-retry-missing-job"
        pipeline = {
            "metadata": {"status": "done", "progress": 100},
            "convert": {"status": "skipped", "progress": 0},
            "nas": {"status": "error", "progress": 0}
        }
        params = {
            "media_type": "youtube",
            "metadata_mode": "tv",
            "show_name": "MyShow",
            "show_id": "123",
            "provider": "tvdb",
            "season": "1",
            "episode": "1",
            "yt_url": "https://youtube.com/watch?v=123",
            "yt_urls": ["https://youtube.com/watch?v=123"],
            "url": "https://youtube.com/watch?v=123",
            "copy_to_nas": True,
            "task_id": job_id,
            "destination_id": "2"
        }
        manifest = {
            "video1.mp4": {
                "target_filename": "MyShow - S01E01 - Ep1.mp4",
                "dest_dir_outbox": outbox_show_dir,
                "clean_title": "MyShow - S01E01 - Ep1",
                "season": 1,
                "episode": 1
            }
        }

        self.jobs.create_job(job_id, "YouTube Show", "youtube", params, pipeline=pipeline, status="queued")
        self.jobs.update_job(job_id, manifest=manifest, status="error")

        # Retry
        res = self._post("/api/queue/retry", {"task_id": job_id})
        self.assertEqual(res.status_code, 200)

        # Run worker
        from gui.workers.processor import process_worker
        updated_job = self.jobs.get_job(job_id)
        process_worker(updated_job["params"])

        # Since the file was missing from outbox, the worker MUST run yt-dlp to download it again
        mock_ytdlp.assert_called_once()

    @patch("gui.workers.processor.mw_metadata.generate_tvshow_nfo")
    @patch("gui.workers.processor.mw_metadata.fetch_tvdb")
    @patch("gui.workers.processor.run_rsync_with_progress")
    @patch("gui.workers.processor.ensure_nas_mounted")
    def test_tv_show_retry_overrides_paths_from_manifest(self, mock_nas_mounted, mock_rsync, mock_fetch_tvdb, mock_tvshow_nfo):
        """test_tv_show_retry_overrides_paths_from_manifest: Verifies that TV show retry uses dest_dir_outbox, clean_title and target_filename from the manifest, even if the recalculation produces different results."""
        mock_nas_mounted.return_value = True
        mock_rsync.return_value = True
        mock_fetch_tvdb.return_value = {
            "1": {"title": "Recalculated Episode Title"}  # Different title
        }

        # Setup folders
        show_dir = os.path.join(self.inbox_dir, "MyShow")
        os.makedirs(show_dir, exist_ok=True)
        # Episode 1 is in inbox
        ep1_file = os.path.join(show_dir, "video1.mp4")
        with open(ep1_file, "w") as f:
            f.write("video1 content")

        # The manifest points to a different title and directory than recalculated
        manifest_outbox_dir = os.path.join(self.outbox_dir, "Serien", "MyShow", "Staffel 1", "MyShow - S01E01 - Original Title")
        os.makedirs(manifest_outbox_dir, exist_ok=True)
        manifest_file = os.path.join(manifest_outbox_dir, "MyShow - S01E01 - Original Title.mp4")
        with open(manifest_file, "w") as f:
            f.write("original file content")

        # Setup job and pipeline state
        job_id = "tv-show-path-override-job"
        pipeline = {
            "metadata": {"status": "done", "progress": 100},
            "convert": {"status": "done", "progress": 100},
            "nas": {"status": "error", "progress": 50}
        }
        params = {
            "media_type": "tv",
            "show_name": "MyShow",
            "show_id": "123",
            "provider": "tvdb",
            "season": "1",
            "convert": False,
            "copy_to_nas": True,
            "mappings": {
                "video1.mp4": 1
            },
            "project_name": "MyShow",
            "task_id": job_id
        }
        manifest = {
            "video1.mp4": {
                "target_filename": "MyShow - S01E01 - Original Title.mp4",
                "dest_dir_outbox": manifest_outbox_dir,
                "clean_title": "MyShow - S01E01 - Original Title",
                "season": 1,
                "episode": 1
            }
        }

        self.jobs.create_job(job_id, "TV Show", "tv", params, pipeline=pipeline, status="queued")
        self.jobs.update_job(job_id, manifest=manifest, status="error")

        # Retry
        res = self._post("/api/queue/retry", {"task_id": job_id})
        self.assertEqual(res.status_code, 200)

        # Run worker
        from gui.workers.processor import process_worker
        updated_job = self.jobs.get_job(job_id)
        params_with_dir = updated_job["params"].copy()
        params_with_dir["current_dir"] = show_dir
        
        process_worker(params_with_dir)

        # Check that rsync was called with the path from the MANIFEST, not the recalculated path
        # Recalculated path would have had 'Recalculated Episode Title' in it.
        # Manifest path has 'Original Title'.
        self.assertEqual(mock_rsync.call_count, 1)
        args, kwargs = mock_rsync.call_args
        src_arg = args[0]
        self.assertIn("Original Title", src_arg)
        self.assertNotIn("Recalculated", src_arg)

    @patch("gui.workers.processor.run_ytdlp_with_progress")
    @patch("gui.workers.processor.run_rsync_with_progress")
    @patch("gui.workers.processor.ensure_nas_mounted")
    def test_youtube_retry_manifest_with_converted_mkv(self, mock_nas_mounted, mock_rsync, mock_ytdlp):
        """test_youtube_retry_manifest_with_converted_mkv: Tests YouTube retry when download is already done and converted to .mkv, validating that bypass is active and the .mkv filename is copied to the NAS."""
        mock_nas_mounted.return_value = True
        mock_rsync.return_value = True

        outbox_show_dir = os.path.join(self.outbox_dir, "Serien", "MyShow", "Staffel 1", "MyShow - S01E01 - Ep1")
        os.makedirs(outbox_show_dir, exist_ok=True)
        # Only the converted .mkv version exists in outbox, the original .mp4 from manifest is missing
        ep1_outbox_mkv = os.path.join(outbox_show_dir, "MyShow - S01E01 - Ep1.mkv")
        with open(ep1_outbox_mkv, "w") as f:
            f.write("converted video content")

        job_id = "yt-mkv-retry-job"
        pipeline = {
            "metadata": {"status": "done", "progress": 100},
            "convert": {"status": "skipped", "progress": 0},
            "nas": {"status": "error", "progress": 0}
        }
        params = {
            "media_type": "youtube",
            "metadata_mode": "tv",
            "show_name": "MyShow",
            "show_id": "123",
            "provider": "tvdb",
            "season": "1",
            "episode": "1",
            "yt_url": "https://youtube.com/watch?v=123",
            "yt_urls": ["https://youtube.com/watch?v=123"],
            "url": "https://youtube.com/watch?v=123",
            "copy_to_nas": True,
            "task_id": job_id,
            "destination_id": "2"
        }
        manifest = {
            "video1.mp4": {
                "target_filename": "MyShow - S01E01 - Ep1.mp4",  # Original extension is .mp4
                "dest_dir_outbox": outbox_show_dir,
                "clean_title": "MyShow - S01E01 - Ep1",
                "season": 1,
                "episode": 1
            }
        }

        self.jobs.create_job(job_id, "YouTube Show", "youtube", params, pipeline=pipeline, status="queued")
        self.jobs.update_job(job_id, manifest=manifest, status="error")

        # Retry
        res = self._post("/api/queue/retry", {"task_id": job_id})
        self.assertEqual(res.status_code, 200)

        # Run worker
        from gui.workers.processor import process_worker
        updated_job = self.jobs.get_job(job_id)
        process_worker(updated_job["params"])

        # Check outcomes:
        # 1. yt-dlp should NOT be called since the .mkv file in outbox makes the bypass valid
        mock_ytdlp.assert_not_called()

        # 2. Rsync must be called with the .mkv file path
        mock_rsync.assert_called_once()
        args, kwargs = mock_rsync.call_args
        src_arg = args[0]
        self.assertTrue(src_arg.endswith(".mkv"), f"Expected src to end with .mkv, got {src_arg}")

    @patch("gui.workers.processor.media.execute_video_conversion")
    @patch("gui.workers.processor.mw_metadata.generate_tvshow_nfo")
    @patch("gui.workers.processor.mw_metadata.fetch_tvdb")
    @patch("gui.workers.processor.run_rsync_with_progress")
    @patch("gui.workers.processor.ensure_nas_mounted")
    def test_tv_show_retry_manifest_with_converted_mkv(self, mock_nas_mounted, mock_rsync, mock_fetch_tvdb, mock_tvshow_nfo, mock_execute_conv):
        """test_tv_show_retry_manifest_with_converted_mkv: Tests TV show retry when original file in manifest is .mp4, but only the converted .mkv version exists in the outbox, validating that bypass is active and the .mkv filename is used."""
        mock_nas_mounted.return_value = True
        mock_rsync.return_value = True
        mock_fetch_tvdb.return_value = {
            "1": {"title": "Episode One"}
        }

        # Setup folders
        show_dir = os.path.join(self.inbox_dir, "MyShow")
        os.makedirs(show_dir, exist_ok=True)
        # Episode 1 is in inbox
        ep1_file = os.path.join(show_dir, "video1.mp4")
        with open(ep1_file, "w") as f:
            f.write("video1 content")

        outbox_show_dir = os.path.join(self.outbox_dir, "Serien", "MyShow", "Staffel 1", "MyShow - S01E01 - Episode One")
        os.makedirs(outbox_show_dir, exist_ok=True)
        # Only the converted .mkv version exists in outbox
        ep1_outbox_mkv = os.path.join(outbox_show_dir, "MyShow - S01E01 - Episode One.mkv")
        with open(ep1_outbox_mkv, "w") as f:
            f.write("converted video content")

        # Setup job and pipeline state
        job_id = "tv-show-mkv-retry-job"
        pipeline = {
            "metadata": {"status": "done", "progress": 100},
            "convert": {"status": "error", "progress": 50},
            "nas": {"status": "error", "progress": 50}
        }
        params = {
            "media_type": "tv",
            "show_name": "MyShow",
            "show_id": "123",
            "provider": "tvdb",
            "season": "1",
            "convert": True,
            "copy_to_nas": True,
            "mappings": {
                "video1.mp4": 1
            },
            "project_name": "MyShow",
            "task_id": job_id
        }
        manifest = {
            "video1.mp4": {
                "target_filename": "MyShow - S01E01 - Episode One.mp4",  # Original extension in manifest is .mp4
                "dest_dir_outbox": outbox_show_dir,
                "clean_title": "MyShow - S01E01 - Episode One",
                "season": 1,
                "episode": 1
            }
        }

        self.jobs.create_job(job_id, "TV Show", "tv", params, pipeline=pipeline, status="queued")
        self.jobs.update_job(job_id, manifest=manifest, status="error")

        # Retry
        res = self._post("/api/queue/retry", {"task_id": job_id})
        self.assertEqual(res.status_code, 200)

        # Run worker
        from gui.workers.processor import process_worker
        updated_job = self.jobs.get_job(job_id)
        params_with_dir = updated_job["params"].copy()
        params_with_dir["current_dir"] = show_dir
        
        process_worker(params_with_dir)

        # 1. tvshow.nfo should NOT be generated again since metadata was done
        mock_tvshow_nfo.assert_not_called()

        # 2. execute_video_conversion should NOT be called since convert is skipped (.mkv exists)
        mock_execute_conv.assert_not_called()

        # 3. Rsync must be called with the .mkv file path from the manifest
        mock_rsync.assert_called_once()
        args, kwargs = mock_rsync.call_args
        src_arg = args[0]
        self.assertTrue(src_arg.endswith(".mkv"), f"Expected TV show src to end with .mkv, got {src_arg}")

    @patch("gui.workers.processor.copy_to_cloud_target", return_value=True)
    @patch("gui.workers.processor.run_rsync_with_progress", return_value=True)
    @patch("gui.workers.processor.mw_metadata.generate_movie_nfo")
    @patch("gui.workers.processor.media.execute_video_conversion")
    def test_cancelled_movie_retry_after_outbox_move_and_foreign_outbox_guard(
        self, mock_conv, mock_movie_nfo, mock_rsync, mock_cloud
    ):
        """AK5 Fall A + Leitplanke: Movie retry resumes from manifest in outbox; fresh job ignores foreign outbox file."""
        import gui.core.persistence as persistence
        from gui.workers.processor import process_worker

        settings = persistence.load_settings()
        settings["storage_targets"][1]["enabled"] = True
        persistence.save_settings(settings)

        outbox_movie_dir = os.path.join(self.outbox_dir, "Filme", "Inception (2010)")
        os.makedirs(outbox_movie_dir, exist_ok=True)
        with open(os.path.join(outbox_movie_dir, "Inception (2010).mkv"), "wb") as f:
            f.write(b"converted-outbox-movie")

        job_id = "cancelled-movie-outbox-job"
        params = {
            "media_type": "movie",
            "project_name": "MissingInboxFolder",
            "movie_name": "Inception (2010)",
            "movie_id": "27205",
            "provider": "tmdb",
            "convert": True,
            "copy_to_nas": True,
            "copy_to_pcloud": True,
            "explicit_renames": [{"old": "raw.mp4", "new": "Inception (2010).mp4"}],
            "task_id": job_id,
        }
        pipeline = {
            "metadata": {"status": "done", "progress": 100},
            "convert": {"status": "done", "progress": 100},
            "nas": {"status": "done", "progress": 100},
            "pcloud": {"status": "cancelled", "progress": 45},
        }
        manifest = {
            "Inception (2010).mp4": {
                "target_filename": "Inception (2010).mkv",
                "dest_movie_dir_outbox": outbox_movie_dir,
                "clean_movie_name": "Inception (2010)",
            }
        }
        self.jobs.create_job(job_id, "Inception (2010)", "movie", params, pipeline=pipeline, status="queued")
        self.jobs.update_job(job_id, manifest=manifest, status="cancelled")

        res = self._post("/api/queue/retry", {"task_id": job_id})
        self.assertEqual(res.status_code, 200)
        retried = self.jobs.get_job(job_id)
        self.assertEqual(retried["pipeline"]["nas"]["status"], "done")
        self.assertEqual(retried["pipeline"]["pcloud"]["status"], "pending")

        self.jobs.update_job(job_id, status="running")
        process_worker(retried["params"])
        self.jobs.update_job(job_id, status="done", progress=100)

        mock_movie_nfo.assert_not_called()
        mock_conv.assert_not_called()
        mock_rsync.assert_not_called()
        mock_cloud.assert_called_once()
        self.assertEqual(self.jobs.get_job(job_id)["status"], "done")

        # Leitplanke regression check: fresh job WITHOUT manifest must NOT treat foreign outbox file as its own work
        fresh_proj = os.path.join(self.inbox_dir, "FreshInception")
        os.makedirs(fresh_proj, exist_ok=True)
        with open(os.path.join(fresh_proj, "Inception (2010).mp4"), "wb") as f:
            f.write(b"fresh-inbox-video")
        mock_movie_nfo.return_value = {"nfo": True}
        fresh_id = "fresh-movie-no-manifest"
        fresh_params = {
            "media_type": "movie",
            "project_name": "FreshInception",
            "movie_name": "Inception (2010)",
            "movie_id": "27205",
            "provider": "tmdb",
            "convert": False,
            "copy_to_nas": False,
            "copy_to_pcloud": False,
            "task_id": fresh_id,
        }
        self.jobs.create_job(fresh_id, "Fresh Inception", "movie", fresh_params, status="running")
        process_worker(fresh_params)
        mock_movie_nfo.assert_called_once()

    @patch("gui.core.trash.send_to_trash")
    def test_cancelled_wizard_movie_retry_before_outbox_move_and_type_guards(self, mock_trash):
        """AK5 Fall B + ADR 3.1: Wizard movie cancelled during convert retries without NFO mismatch or junk loss."""
        from gui.workers.processor import process_worker
        from gui.core.jobs import JobCancelledError

        mock_trash.side_effect = lambda p, *a, **kw: (os.remove(p) if os.path.isfile(p) else shutil.rmtree(p, ignore_errors=True)) or True

        proj_dir = os.path.join(self.inbox_dir, "OdysseeProj")
        os.makedirs(proj_dir, exist_ok=True)
        with open(os.path.join(proj_dir, "raw.mkv"), "wb") as f:
            f.write(b"raw-video-bytes")
        with open(os.path.join(proj_dir, "Die Odyssee (2026).nfo"), "w", encoding="utf-8") as f:
            f.write("<movie><title>Stale Junk NFO</title></movie>")

        def fake_gen_movie_nfo(mid, folder, base, **kwargs):
            p = os.path.join(folder, f"{base}.nfo")
            with open(p, "w", encoding="utf-8") as nf:
                nf.write('<?xml version="1.0" encoding="UTF-8"?>\n<movie><title>TMDb Base</title><year>2026</year></movie>\n')
            return {"nfo": True}

        job_id = "wizard-cancel-during-convert"
        params = {
            "task_id": job_id,
            "project_name": "OdysseeProj",
            "media_type": "movie",
            "movie_name": "Die Odyssee (2026)",
            "movie_id": "99901",
            "provider": "tmdb",
            "convert": True,
            "copy_to_nas": False,
            "copy_to_pcloud": False,
            "wizard_overrides": True,
            "main_nfo_fingerprint": None,
            "nfo_overrides": {"movie": {"title": "Die Odyssee", "year": "2026", "fsk": "12"}},
            "explicit_renames": [{"old": "raw.mkv", "new": "Die Odyssee (2026).mkv"}],
            "explicit_junk": ["Die Odyssee (2026).nfo"],
        }
        pipeline = {
            "metadata": {"status": "pending", "progress": 0},
            "convert": {"status": "pending", "progress": 0},
            "nas": {"status": "skipped", "progress": 0},
            "pcloud": {"status": "skipped", "progress": 0},
        }
        self.jobs.create_job(job_id, "Die Odyssee (2026)", "movie", params, pipeline=pipeline, status="running")

        # Run 1: cancel during conversion -> metadata is already 'done' and fresh NFO sits in proj_dir
        with patch("gui.workers.processor.mw_metadata.generate_movie_nfo", side_effect=fake_gen_movie_nfo), \
             patch("gui.workers.processor.media.execute_video_conversion", side_effect=JobCancelledError("Abgebrochen")):
            with self.assertRaises(JobCancelledError):
                process_worker(params)
        self.jobs.finalize_cancelled_job(job_id)

        self.assertEqual(self.jobs.get_job(job_id)["status"], "cancelled")
        self.assertEqual(self.jobs.get_job(job_id)["pipeline"]["metadata"]["status"], "done")
        self.assertTrue(os.path.isfile(os.path.join(proj_dir, "Die Odyssee (2026).nfo")))

        # Retry via API and run conversion to completion
        res_retry = self._post("/api/queue/retry", {"task_id": job_id})
        self.assertEqual(res_retry.status_code, 200)
        self.jobs.update_job(job_id, status="running")

        def fake_conv_ok(**kwargs):
            if kwargs["target_filepath"] != kwargs["final_filepath"]:
                shutil.copy2(kwargs["target_filepath"], kwargs["final_filepath"])
            return True, os.path.basename(kwargs["final_filepath"])

        with patch("gui.workers.processor.mw_metadata.generate_movie_nfo", side_effect=AssertionError("Must not regenerate NFO")), \
             patch("gui.workers.processor.media.execute_video_conversion", side_effect=fake_conv_ok):
            process_worker(self.jobs.get_job(job_id)["params"])

        outbox_nfo = os.path.join(self.outbox_dir, "Filme", "Die Odyssee (2026)", "Die Odyssee (2026).nfo")
        self.assertTrue(os.path.isfile(outbox_nfo))
        with open(outbox_nfo, "r", encoding="utf-8") as f:
            nfo_xml = f.read()
        self.assertIn("<title>Die Odyssee</title>", nfo_xml)
        self.assertIn("FSK 12", nfo_xml)

        # Reject normalize & unknown types with HTTP 400; keep legacy job['type'] == 'tv' compatible
        for bad_type in ("normalize", "unknown"):
            bad_id = f"job-{bad_type}"
            self.jobs.create_job(bad_id, bad_id, bad_type, {}, status="cancelled")
            r_bad = self._post("/api/queue/retry", {"task_id": bad_id})
            self.assertEqual(r_bad.status_code, 400)

        legacy_id = "legacy-tv-without-media-type"
        self.jobs.create_job(legacy_id, "Legacy TV", "tv", {"show_id": "1", "provider": "tvdb"}, status="cancelled")
        r_leg = self._post("/api/queue/retry", {"task_id": legacy_id})
        self.assertEqual(r_leg.status_code, 200)
        self.assertEqual(self.jobs.get_job(legacy_id)["params"]["media_type"], "tv")

    @patch("gui.core.trash.send_to_trash", return_value=True)
    @patch("gui.workers.processor.ensure_nas_mounted", return_value=True)
    @patch("gui.workers.processor.copy_to_cloud_target", return_value=True)
    @patch("gui.workers.processor.run_rsync_with_progress", return_value=True)
    def test_real_queue_worker_mid_outbox_move_cancel_preserves_manifest_and_retries(
        self, mock_rsync, mock_cloud, _mock_nas, _mock_trash
    ):
        """AK5 + R1 Finding 2: Real queue worker cancelled between video Outbox move and manifest finalize still retries."""
        import threading
        import time
        import gui.core.persistence as persistence
        import gui.workers.processor as proc_mod
        from gui.core.helpers import job_queue

        settings = persistence.load_settings()
        settings["storage_targets"][1]["enabled"] = True
        persistence.save_settings(settings)

        proj_dir = os.path.join(self.inbox_dir, "MidMoveProj")
        os.makedirs(proj_dir, exist_ok=True)
        with open(os.path.join(proj_dir, "raw.mp4"), "wb") as f:
            f.write(b"movie-bytes")

        def fake_gen_nfo(_mid, folder, base, **_kw):
            with open(os.path.join(folder, f"{base}.nfo"), "w", encoding="utf-8") as nf:
                nf.write("<movie><title>Interstellar</title></movie>")
            return {"nfo": True}

        job_id = "mid-move-cancel-job"
        params = {
            "task_id": job_id,
            "project_name": "MidMoveProj",
            "media_type": "movie",
            "movie_name": "Interstellar (2014)",
            "movie_id": "157336",
            "provider": "tmdb",
            "convert": False,
            "copy_to_nas": True,
            "copy_to_pcloud": True,
        }
        pipeline = {
            "metadata": {"status": "pending", "progress": 0},
            "convert": {"status": "skipped", "progress": 0},
            "nas": {"status": "pending", "progress": 0},
            "pcloud": {"status": "pending", "progress": 0},
        }
        job = self.jobs.create_job(job_id, "Interstellar (2014)", "movie", params, pipeline=pipeline, status="queued")

        orig_safe_move = proc_mod.safe_move_recursive
        cancel_triggered = []

        def cancel_after_video_moved(src_dir, dest_dir, *a, **kw):
            if not cancel_triggered:
                cancel_triggered.append(True)
                # Video file is ALREADY moved to Outbox; trigger real cancel ('cancelling') and abort mid-move!
                self.jobs.cancel_job(job_id)
                raise self.jobs.JobCancelledError("Abgebrochen während Outbox-Move")
            return orig_safe_move(src_dir, dest_dir, *a, **kw)

        def wait_status(expected, timeout=4.0):
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if self.jobs.get_job(job_id)["status"] == expected:
                    return True
                time.sleep(0.02)
            return self.jobs.get_job(job_id)["status"] == expected

        with patch("gui.workers.processor.mw_metadata.generate_movie_nfo", side_effect=fake_gen_nfo), \
             patch("gui.workers.processor.safe_move_recursive", side_effect=cancel_after_video_moved):
            worker_t = threading.Thread(target=proc_mod.job_queue_worker, daemon=True)
            worker_t.start()
            try:
                job_queue.put(job)
                self.assertTrue(wait_status("cancelled"))

                cancelled_snap = self.jobs.get_job(job_id)
                outbox_dir = os.path.join(self.outbox_dir, "Filme", "Interstellar (2014)")
                self.assertTrue(os.path.isfile(os.path.join(outbox_dir, "Interstellar (2014).mp4")))
                self.assertIn("raw.mp4", cancelled_snap.get("manifest", {}))
                mock_rsync.assert_not_called()

                # Retry through API -> real job_queue_worker resumes via manifest, sweeps NFO, transfers to NAS & Cloud
                r_retry = self._post("/api/queue/retry", {"task_id": job_id})
                self.assertEqual(r_retry.status_code, 200)
                self.assertTrue(wait_status("done"))
            finally:
                job_queue.put(None)
                worker_t.join(timeout=2.0)

        self.assertTrue(os.path.isfile(os.path.join(outbox_dir, "Interstellar (2014).nfo")))
        mock_rsync.assert_called_once()
        mock_cloud.assert_called_once()

    @patch("gui.core.trash.send_to_trash", return_value=True)
    @patch("gui.workers.processor.ensure_nas_mounted", return_value=True)
    @patch("gui.workers.processor.mw_metadata.generate_tvshow_nfo", return_value={"nfo": True})
    @patch("gui.workers.processor.mw_metadata.generate_episode_nfo", return_value={"nfo": True})
    @patch("gui.workers.processor.mw_metadata.fetch_tvdb", return_value={"1": {"title": "Pilot"}})
    @patch("gui.workers.processor.mw_metadata.generate_movie_nfo", return_value={"nfo": True})
    def test_failed_outbox_move_partial_or_foreign_dest_not_confirmed_movie_and_tv(
        self, _m_mnfo, _m_tvdb, _m_epnfo, _m_shownfo, _m_nas, _m_trash
    ):
        """R2 Finding: Failed shutil.move (partial cross-FS file or unchanged foreign target) never confirms manifest in movie or TV."""
        import threading
        import time
        import gui.core.persistence as persistence
        import gui.workers.processor as proc_mod
        from gui.core.helpers import job_queue

        settings = persistence.load_settings()
        settings["storage_targets"][1]["enabled"] = True
        persistence.save_settings(settings)
        real_move = shutil.move

        def wait_job(jid, expected, timeout=4.0):
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if self.jobs.get_job(jid)["status"] == expected:
                    return True
                time.sleep(0.02)
            return self.jobs.get_job(jid)["status"] == expected

        for media_type in ("movie", "tv"):
            for mode in ("partial", "foreign"):
                with self.subTest(media_type=media_type, mode=mode):
                    tag = f"{media_type}_{mode}"
                    job_id = f"move-fail-{tag}"
                    proj_name = f"Proj_{tag}"
                    proj_dir = os.path.join(self.inbox_dir, proj_name)
                    os.makedirs(proj_dir, exist_ok=True)
                    complete_bytes = f"COMPLETE_INBOX_SOURCE_{tag}".encode("utf-8")
                    bad_bytes = (
                        f"PARTIAL_TRUNCATED_{tag}".encode("utf-8")
                        if mode == "partial"
                        else f"FOREIGN_PREEXISTING_{tag}".encode("utf-8")
                    )
                    with open(os.path.join(proj_dir, "raw.mp4"), "wb") as f:
                        f.write(complete_bytes)

                    if media_type == "movie":
                        title = f"MoveFilm {mode} (2025)"
                        outbox_video = os.path.join(self.outbox_dir, "Filme", title, f"{title}.mp4")
                        params = {
                            "task_id": job_id, "project_name": proj_name, "media_type": "movie",
                            "movie_name": title, "movie_id": "42", "provider": "tmdb",
                            "convert": False, "copy_to_nas": True, "copy_to_pcloud": True,
                        }
                    else:
                        show = f"MoveShow {mode}"
                        ep_stem = f"{show} - S01E01 - Pilot"
                        outbox_video = os.path.join(self.outbox_dir, "Serien", show, "Staffel 1", ep_stem, f"{ep_stem}.mp4")
                        params = {
                            "task_id": job_id, "project_name": proj_name, "media_type": "tv",
                            "show_name": show, "show_id": "77", "provider": "tvdb", "season": "1",
                            "mappings": {"raw.mp4": 1}, "convert": False, "copy_to_nas": True, "copy_to_pcloud": True,
                        }

                    if mode == "foreign":
                        os.makedirs(os.path.dirname(outbox_video), exist_ok=True)
                        with open(outbox_video, "wb") as f:
                            f.write(bad_bytes)

                    pipeline = {
                        "metadata": {"status": "pending", "progress": 0},
                        "convert": {"status": "skipped", "progress": 0},
                        "nas": {"status": "pending", "progress": 0},
                        "pcloud": {"status": "pending", "progress": 0},
                    }
                    job = self.jobs.create_job(job_id, job_id, media_type, params, pipeline=pipeline, status="queued")

                    fail_moves = [True]
                    transferred_nas_payloads = []
                    cloud_calls = []

                    def controlled_move(src, dst, *a, **kw):
                        if os.path.abspath(dst) == os.path.abspath(outbox_video) and fail_moves[0]:
                            if mode == "partial":
                                os.makedirs(os.path.dirname(dst), exist_ok=True)
                                with open(dst, "wb") as pf:
                                    pf.write(bad_bytes)
                                raise OSError("ENOSPC: simulated cross-FS partial copy failure")
                            raise PermissionError("EACCES: foreign destination locked")
                        return real_move(src, dst, *a, **kw)

                    def capture_rsync(src_p, _dst_p, *_a, **_kw):
                        vfile = src_p if os.path.isfile(src_p) else outbox_video
                        if os.path.isfile(vfile):
                            with open(vfile, "rb") as vf:
                                transferred_nas_payloads.append(vf.read())
                        return True

                    with patch("gui.workers.processor.shutil.move", side_effect=controlled_move), \
                         patch("gui.workers.processor.run_rsync_with_progress", side_effect=capture_rsync), \
                         patch("gui.workers.processor.copy_to_cloud_target", side_effect=lambda *a, **kw: cloud_calls.append(a[0]) or True):
                        wt = threading.Thread(target=proc_mod.job_queue_worker, daemon=True)
                        wt.start()
                        try:
                            # Run 1: shutil.move fails -> partial or foreign file sits at outbox_video
                            job_queue.put(job)
                            self.assertTrue(wait_job(job_id, "error"))
                            snap_err = self.jobs.get_job(job_id)
                            self.assertEqual(snap_err.get("manifest", {}), {})
                            self.assertTrue(os.path.isfile(outbox_video))
                            with open(outbox_video, "rb") as f:
                                self.assertEqual(f.read(), bad_bytes)
                            self.assertEqual(transferred_nas_payloads, [])
                            self.assertEqual(cloud_calls, [])

                            # Even if a crash left a provisional manifest entry, retry strips it & refuses bypass while move still fails
                            with self.jobs.active_jobs_lock:
                                self.jobs.active_jobs[job_id]["manifest"] = {
                                    "raw.mp4": {
                                        "target_filename": os.path.basename(outbox_video),
                                        "dest_movie_dir_outbox": os.path.dirname(outbox_video),
                                        "dest_dir_outbox": os.path.dirname(outbox_video),
                                        "provisional": True,
                                    }
                                }
                            self.assertEqual(self._post("/api/queue/retry", {"task_id": job_id}).status_code, 200)
                            self.assertEqual(self.jobs.get_job(job_id).get("manifest", {}), {})
                            self.assertTrue(wait_job(job_id, "error"))
                            with open(outbox_video, "rb") as f:
                                self.assertEqual(f.read(), bad_bytes)
                            self.assertEqual(transferred_nas_payloads, [])

                            # Now obstacle is resolved -> Retry processes complete Inbox source and transfers complete bytes!
                            fail_moves[0] = False
                            self.assertEqual(self._post("/api/queue/retry", {"task_id": job_id}).status_code, 200)
                            self.assertTrue(wait_job(job_id, "done"))
                        finally:
                            job_queue.put(None)
                            wt.join(timeout=2.0)

                    with open(outbox_video, "rb") as f:
                        self.assertEqual(f.read(), complete_bytes)
                    self.assertIn(complete_bytes, transferred_nas_payloads)
                    self.assertNotIn(bad_bytes, transferred_nas_payloads)
                    self.assertEqual(len(cloud_calls), 1)
                    done_mf = self.jobs.get_job(job_id).get("manifest", {})
                    self.assertEqual(len(done_mf), 1)
                    for entry in done_mf.values():
                        self.assertFalse(entry.get("provisional", False))

    @patch("gui.workers.processor.ensure_nas_mounted", return_value=True)
    @patch("gui.workers.processor.run_rsync_with_progress", return_value=True)
    @patch("gui.workers.processor.mw_metadata.fetch_tvdb")
    def test_tv_multi_episode_cancel_and_retry_conversion_and_checkpoint(
        self, mock_fetch_tvdb, mock_rsync, _mock_nas
    ):
        """Delta Test 2: N=2 TV job cancelled during Ep1 conversion (with/without explicit_renames + #96 explicit_junk), post-Ep1 conversion before Outbox move, or at Ep1/Ep2 checkpoint retries both episodes without NFO quarantine, orphaned show-root NFO, or foreign MKV adoption."""
        from gui.workers.processor import job_queue_worker, process_worker
        from gui.core.helpers import job_queue
        from gui.core.jobs import JobCancelledError

        mock_fetch_tvdb.return_value = {"1": {"title": "Alpha"}, "2": {"title": "Beta"}}

        mode_shows = {
            "conv_explicit_junk": "DarkShow One",
            "conv_implicit_rename": "DarkShow Two",
            "checkpoint_after_ep1_outbox": "DarkShow Three",
            "post_conv_explicit_rename": "DarkShow Four",
        }
        for mode, show_name in mode_shows.items():
            with self.subTest(mode=mode):
                mock_rsync.reset_mock()
                while not job_queue.empty():
                    job_queue.get_nowait()
                    job_queue.task_done()
                job_id = f"tv-2ep-{mode}"
                proj_dir = os.path.join(self.inbox_dir, f"Proj_{mode}")
                os.makedirs(proj_dir, exist_ok=True)
                with open(os.path.join(proj_dir, "raw1.mp4"), "wb") as f:
                    f.write(b"EP1_RAW_BYTES")
                with open(os.path.join(proj_dir, "raw2.mp4"), "wb") as f:
                    f.write(b"EP2_RAW_BYTES")
                if mode == "conv_implicit_rename":
                    with open(os.path.join(proj_dir, "raw1.srt"), "wb") as f:
                        f.write(b"SUB1_BYTES")
                    with open(os.path.join(proj_dir, "raw2.srt"), "wb") as f:
                        f.write(b"SUB2_BYTES")

                ep1_clean = f"{show_name} - S01E01 - Alpha"
                ep2_clean = f"{show_name} - S01E02 - Beta"
                stale_nfo_path = os.path.join(proj_dir, f"{ep1_clean}.nfo")
                if mode == "conv_explicit_junk":
                    with open(stale_nfo_path, "w", encoding="utf-8") as f:
                        f.write("<episodedetails><title>STALE_JUNK_NFO</title></episodedetails>")

                trashed_contents = []

                def track_trash(path, *_a, **_kw):
                    if os.path.isfile(path):
                        with open(path, "r", encoding="utf-8", errors="ignore") as tf:
                            trashed_contents.append((os.path.basename(path), tf.read()))
                        os.remove(path)
                    elif os.path.isdir(path):
                        shutil.rmtree(path, ignore_errors=True)
                    return True

                def fake_gen_show_nfo(_prov, _sid, folder, **_kw):
                    with open(os.path.join(folder, "tvshow.nfo"), "w", encoding="utf-8") as nf:
                        nf.write(f"<tvshow><title>{show_name}</title></tvshow>")
                    return {"nfo": True}

                def fake_gen_ep_nfo(_prov, _sid, _s, ep, folder, base, **kw):
                    p = os.path.join(folder, f"{base}.nfo")
                    if not kw.get("overwrite") and os.path.isfile(p):
                        return {"nfo": False}
                    with open(p, "w", encoding="utf-8") as nf:
                        nf.write(f"<episodedetails><title>FRESH_EP_{ep}</title></episodedetails>")
                    return {"nfo": True}

                use_explicit = mode in ("conv_explicit_junk", "post_conv_explicit_rename")
                params = {
                    "task_id": job_id,
                    "project_name": f"Proj_{mode}",
                    "media_type": "tv",
                    "show_name": show_name,
                    "show_id": "555",
                    "provider": "tvdb",
                    "season": "1",
                    "mappings": {"raw1.mp4": 1, "raw2.mp4": 2},
                    "convert": True,
                    "copy_to_nas": True,
                    "overwrite_nfo": False,
                    "explicit_renames": (
                        [
                            {"old": "raw1.mp4", "new": f"{ep1_clean}.mp4"},
                            {"old": "raw2.mp4", "new": f"{ep2_clean}.mp4"},
                        ]
                        if use_explicit
                        else None
                    ),
                    "explicit_junk": [f"{ep1_clean}.nfo"] if mode == "conv_explicit_junk" else [],
                }
                pipeline = {
                    "metadata": {"status": "pending", "progress": 0},
                    "convert": {"status": "pending", "progress": 0},
                    "nas": {"status": "pending", "progress": 0},
                }
                self.jobs.create_job(job_id, show_name, "tv", params, pipeline=pipeline, status="running")

                conv_calls = [0]
                orig_commit_mf = self.jobs.commit_job_manifest
                ep1_manifest_committed = []

                def hook_commit_mf(tid, mf):
                    res = orig_commit_mf(tid, mf)
                    if (
                        mode == "checkpoint_after_ep1_outbox"
                        and not ep1_manifest_committed
                        and isinstance(mf, dict)
                        and "raw1.mp4" in mf
                    ):
                        ep1_manifest_committed.append(True)
                        # Trigger cancel right before the post-Outbox-move episode checkpoint
                        self.jobs.cancel_job(job_id)
                    return res

                def fake_conv_run1(**kwargs):
                    conv_calls[0] += 1
                    if mode.startswith("conv_") and conv_calls[0] == 1:
                        self.jobs.cancel_job(job_id)
                        raise JobCancelledError("Abgebrochen während Ep1 H.265-Konvertierung")
                    shutil.copy2(kwargs["target_filepath"], kwargs["final_filepath"])
                    if mode == "post_conv_explicit_rename" and conv_calls[0] == 1:
                        os.remove(kwargs["target_filepath"])
                        self.jobs.cancel_job(job_id)
                    return True, os.path.basename(kwargs["final_filepath"])

                with patch("gui.core.trash.send_to_trash", side_effect=track_trash), \
                     patch("gui.core.jobs.commit_job_manifest", side_effect=hook_commit_mf), \
                     patch("gui.workers.processor.mw_metadata.generate_tvshow_nfo", side_effect=fake_gen_show_nfo), \
                     patch("gui.workers.processor.mw_metadata.generate_episode_nfo", side_effect=fake_gen_ep_nfo), \
                     patch("gui.workers.processor.media.execute_video_conversion", side_effect=fake_conv_run1):
                    with self.assertRaises(JobCancelledError):
                        process_worker(params)
                self.jobs.finalize_cancelled_job(job_id)

                snap_cancelled = self.jobs.get_job(job_id)
                self.assertEqual(snap_cancelled["status"], "cancelled")
                self.assertNotEqual(snap_cancelled["pipeline"]["metadata"]["status"], "done")

                # Trigger /api/queue/retry and run via job_queue_worker to completion
                self.assertEqual(self._post("/api/queue/retry", {"task_id": job_id}).status_code, 200)
                job_queue.put(None)

                run2_conv_calls = [0]

                def fake_conv_run2(**kwargs):
                    run2_conv_calls[0] += 1
                    shutil.copy2(kwargs["target_filepath"], kwargs["final_filepath"])
                    return True, os.path.basename(kwargs["final_filepath"])

                with patch("gui.core.trash.send_to_trash", side_effect=track_trash), \
                     patch("gui.workers.processor.mw_metadata.generate_tvshow_nfo", side_effect=fake_gen_show_nfo), \
                     patch("gui.workers.processor.mw_metadata.generate_episode_nfo", side_effect=fake_gen_ep_nfo), \
                     patch("gui.workers.processor.media.execute_video_conversion", side_effect=fake_conv_run2):
                    job_queue_worker()

                self.assertEqual(self.jobs.get_job(job_id)["status"], "done")
                if mode == "post_conv_explicit_rename":
                    self.assertEqual(run2_conv_calls[0], 1)

                show_outbox = os.path.join(self.outbox_dir, "Serien", show_name)
                ep1_outbox_dir = os.path.join(show_outbox, "Staffel 1", ep1_clean)
                ep2_outbox_dir = os.path.join(show_outbox, "Staffel 1", ep2_clean)

                self.assertTrue(os.path.isfile(os.path.join(ep1_outbox_dir, f"{ep1_clean}.mkv")))
                self.assertTrue(os.path.isfile(os.path.join(ep1_outbox_dir, f"{ep1_clean}.nfo")))
                self.assertTrue(os.path.isfile(os.path.join(ep2_outbox_dir, f"{ep2_clean}.mkv")))
                self.assertTrue(os.path.isfile(os.path.join(ep2_outbox_dir, f"{ep2_clean}.nfo")))
                if mode == "conv_implicit_rename":
                    self.assertTrue(os.path.isfile(os.path.join(ep1_outbox_dir, f"{ep1_clean}.srt")))
                    self.assertTrue(os.path.isfile(os.path.join(ep2_outbox_dir, f"{ep2_clean}.srt")))

                with open(os.path.join(ep1_outbox_dir, f"{ep1_clean}.nfo"), "r", encoding="utf-8") as f:
                    self.assertIn("FRESH_EP_1", f.read())

                # No generated fresh NFO was ever quarantined (#96)
                for _fname, payload in trashed_contents:
                    self.assertNotIn("FRESH_EP_", payload)

                # No orphaned episode NFO in series root folder
                self.assertFalse(os.path.exists(os.path.join(show_outbox, f"{ep1_clean}.nfo")))
                self.assertFalse(os.path.exists(os.path.join(show_outbox, f"{ep2_clean}.nfo")))

        # Negative test: new job with missing expected source and foreign <clean_title>.mkv must NOT adopt foreign MKV
        for neg_label, neg_src, neg_renames in (
            ("empty_list", "raw1.mp4", []),
            ("empty_list_mkv_src", "raw1.mkv", []),
            ("explicit_missing_src", "raw1.mp4", [{"old": "raw1.mp4", "new": "ForeignGuardShow - S01E01 - Alpha.mp4"}]),
            ("explicit_missing_mkv_src", "raw1.mkv", [{"old": "raw1.mkv", "new": "ForeignGuardShow - S01E01 - Alpha.mkv"}]),
            ("implicit_none", "raw1.mp4", None),
        ):
            with self.subTest(foreign_mkv_guard=neg_label):
                mock_rsync.reset_mock()
                neg_job_id = f"tv-foreign-mkv-{neg_label}"
                neg_proj_dir = os.path.join(self.inbox_dir, f"Proj_Foreign_{neg_label}")
                os.makedirs(neg_proj_dir, exist_ok=True)
                foreign_clean = "ForeignGuardShow - S01E01 - Alpha"
                foreign_mkv = os.path.join(neg_proj_dir, f"{foreign_clean}.mkv")
                with open(foreign_mkv, "wb") as f:
                    f.write(b"FOREIGN_PREEXISTING_MKV")

                neg_params = {
                    "task_id": neg_job_id,
                    "project_name": f"Proj_Foreign_{neg_label}",
                    "media_type": "tv",
                    "show_name": "ForeignGuardShow",
                    "show_id": "555",
                    "provider": "tvdb",
                    "season": "1",
                    "mappings": {neg_src: 1},
                    "convert": True,
                    "copy_to_nas": True,
                    "explicit_renames": neg_renames,
                }
                self.jobs.create_job(
                    neg_job_id,
                    "ForeignGuardShow",
                    "tv",
                    neg_params,
                    pipeline={
                        "metadata": {"status": "pending", "progress": 0},
                        "convert": {"status": "pending", "progress": 0},
                        "nas": {"status": "pending", "progress": 0},
                    },
                    status="running",
                )
                with patch("gui.workers.processor.mw_metadata.generate_tvshow_nfo", return_value={"nfo": True}), \
                     patch("gui.workers.processor.mw_metadata.generate_episode_nfo", return_value={"nfo": True}), \
                     patch("gui.workers.processor.media.execute_video_conversion") as mock_neg_conv:
                    process_worker(neg_params)
                mock_neg_conv.assert_not_called()
                mock_rsync.assert_not_called()
                self.assertTrue(os.path.isfile(foreign_mkv), "Foreign MKV must remain untouched in inbox")
                neg_outbox_mkv = os.path.join(
                    self.outbox_dir, "Serien", "ForeignGuardShow", "Staffel 1", foreign_clean, f"{foreign_clean}.mkv"
                )
                self.assertFalse(os.path.exists(neg_outbox_mkv), "Foreign MKV must not be adopted into outbox")
                self.assertEqual(self.jobs.get_job(neg_job_id).get("manifest", {}), {})

        # Positive test: new job with explicit_renames=[] and existing already-correctly-named episode succeeds (project and files_param)
        for use_files_param in (False, True):
            with self.subTest(prenamed_explicit_empty=use_files_param):
                mock_rsync.reset_mock()
                pos_show = "PreNamedFilesShow" if use_files_param else "PreNamedProjShow"
                pos_job_id = f"tv-prenamed-{'files' if use_files_param else 'proj'}"
                pos_clean = f"{pos_show} - S01E01 - Alpha"
                pos_fname = f"{pos_clean}.mkv"
                pos_dir = self.inbox_dir if use_files_param else os.path.join(self.inbox_dir, "Proj_PreNamed")
                os.makedirs(pos_dir, exist_ok=True)
                with open(os.path.join(pos_dir, pos_fname), "wb") as f:
                    f.write(b"PRENAMED_VALID_EPISODE")

                pos_params = {
                    "task_id": pos_job_id,
                    "media_type": "tv",
                    "show_name": pos_show,
                    "show_id": "555",
                    "provider": "tvdb",
                    "season": "1",
                    "mappings": {pos_fname: 1},
                    "convert": False,
                    "copy_to_nas": True,
                    "explicit_renames": [],
                    **({"files": [pos_fname]} if use_files_param else {"project_name": "Proj_PreNamed"}),
                }
                self.jobs.create_job(
                    pos_job_id,
                    pos_show,
                    "tv",
                    pos_params,
                    pipeline={
                        "metadata": {"status": "pending", "progress": 0},
                        "convert": {"status": "skipped", "progress": 0},
                        "nas": {"status": "pending", "progress": 0},
                    },
                    status="running",
                )
                with patch("gui.workers.processor.mw_metadata.generate_tvshow_nfo", return_value={"nfo": True}), \
                     patch("gui.workers.processor.mw_metadata.generate_episode_nfo", return_value={"nfo": True}):
                    process_worker(pos_params)
                pos_outbox_mkv = os.path.join(
                    self.outbox_dir, "Serien", pos_show, "Staffel 1", pos_clean, pos_fname
                )
                self.assertTrue(os.path.isfile(pos_outbox_mkv))
                self.assertIn(pos_fname, self.jobs.get_job(pos_job_id).get("manifest", {}))

    @patch("gui.core.trash.send_to_trash")
    def test_wizard_movie_cancel_during_nfo_artwork_retry_and_tamper_detection(self, mock_trash):
        """Delta Test 3: Wizard movie cancelled after writing NFO (during artwork download, before metadata=done) retries without NfoConflictError; external tampering still raises NfoConflictError."""
        from gui.workers.processor import job_queue_worker, process_worker
        from gui.core.helpers import job_queue
        from gui.core.jobs import JobCancelledError
        from gui.core.nfo_mutation import NfoConflictError

        mock_trash.side_effect = (
            lambda p, *_a, **_kw: (os.remove(p) if os.path.isfile(p) else shutil.rmtree(p, ignore_errors=True)) or True
        )

        proj_dir = os.path.join(self.inbox_dir, "ArrivalProj")
        os.makedirs(proj_dir, exist_ok=True)
        with open(os.path.join(proj_dir, "raw.mkv"), "wb") as f:
            f.write(b"MOVIE_BYTES")
        nfo_path = os.path.join(proj_dir, "Arrival (2016).nfo")
        with open(nfo_path, "w", encoding="utf-8") as f:
            f.write("<movie><title>Old Junk NFO</title></movie>")

        job_id = "wizard-cancel-during-artwork"
        params = {
            "task_id": job_id,
            "project_name": "ArrivalProj",
            "media_type": "movie",
            "movie_name": "Arrival (2016)",
            "movie_id": "329865",
            "provider": "tmdb",
            "convert": False,
            "copy_to_nas": False,
            "copy_to_pcloud": False,
            "wizard_overrides": True,
            "main_nfo_fingerprint": None,
            "nfo_overrides": {"movie": {"title": "Arrival", "year": "2016", "fsk": "12"}},
            "explicit_renames": [{"old": "raw.mkv", "new": "Arrival (2016).mkv"}],
            "explicit_junk": ["Arrival (2016).nfo"],
        }
        pipeline = {
            "metadata": {"status": "pending", "progress": 0},
            "convert": {"status": "skipped", "progress": 0},
            "nas": {"status": "skipped", "progress": 0},
            "pcloud": {"status": "skipped", "progress": 0},
        }
        self.jobs.create_job(job_id, "Arrival (2016)", "movie", params, pipeline=pipeline, status="running")

        def gen_nfo_cancel_during_artwork(_mid, folder, base, **_kw):
            p = os.path.join(folder, f"{base}.nfo")
            with open(p, "w", encoding="utf-8") as nf:
                nf.write('<?xml version="1.0" encoding="UTF-8"?>\n<movie><title>Arrival TMDb</title></movie>\n')
            # User cancels while artwork download is running inside generate_movie_nfo
            self.jobs.cancel_job(job_id)
            raise JobCancelledError("Abgebrochen während Artwork-Download")

        with patch("gui.workers.processor.mw_metadata.generate_movie_nfo", side_effect=gen_nfo_cancel_during_artwork):
            with self.assertRaises(JobCancelledError):
                process_worker(self.jobs.get_job(job_id)["params"])
        self.jobs.finalize_cancelled_job(job_id)

        snap_after_cancel = self.jobs.get_job(job_id)
        self.assertEqual(snap_after_cancel["status"], "cancelled")
        self.assertNotEqual(snap_after_cancel["pipeline"]["metadata"]["status"], "done")
        self.assertIsNotNone(snap_after_cancel["params"]["main_nfo_fingerprint"])
        self.assertTrue(os.path.isfile(nfo_path))

        # External manipulation between cancel and retry MUST still trigger NfoConflictError
        self.assertEqual(self._post("/api/queue/retry", {"task_id": job_id}).status_code, 200)
        self.jobs.update_job(job_id, status="running")
        with open(nfo_path, "r", encoding="utf-8") as f:
            untampered_xml = f.read()
        with open(nfo_path, "w", encoding="utf-8") as f:
            f.write("<movie><title>Externally Tampered By Third Party</title></movie>")

        with self.assertRaises(RuntimeError) as ctx_err:
            process_worker(self.jobs.get_job(job_id)["params"])
        self.assertIsInstance(ctx_err.exception.__cause__, NfoConflictError)
        self.assertEqual(self.jobs.get_job(job_id)["status"], "error")

        # Restore untampered NFO from Run 1 -> /api/queue/retry + job_queue_worker reloads persisted params and completes to 'done'
        with open(nfo_path, "w", encoding="utf-8") as f:
            f.write(untampered_xml)
        while not job_queue.empty():
            job_queue.get_nowait()
            job_queue.task_done()
        self.assertEqual(self._post("/api/queue/retry", {"task_id": job_id}).status_code, 200)
        # Put a stale params snapshot on the queued dict entry to prove job_queue_worker reloads latest params from get_job(task_id)
        with job_queue.mutex:
            job_queue.queue[0]["params"] = {**job_queue.queue[0]["params"], "main_nfo_fingerprint": None}
        job_queue.put(None)

        def gen_nfo_ok(_mid, folder, base, **_kw):
            p = os.path.join(folder, f"{base}.nfo")
            with open(p, "w", encoding="utf-8") as nf:
                nf.write('<?xml version="1.0" encoding="UTF-8"?>\n<movie><title>Arrival TMDb</title></movie>\n')
            return {"nfo": True}

        with patch("gui.workers.processor.mw_metadata.generate_movie_nfo", side_effect=gen_nfo_ok):
            job_queue_worker()

        outbox_nfo = os.path.join(self.outbox_dir, "Filme", "Arrival (2016)", "Arrival (2016).nfo")
        self.assertTrue(os.path.isfile(outbox_nfo))
        with open(outbox_nfo, "r", encoding="utf-8") as f:
            final_xml = f.read()
        self.assertIn("<title>Arrival</title>", final_xml)
        self.assertIn("FSK 12", final_xml)
        self.assertEqual(self.jobs.get_job(job_id)["status"], "done")
