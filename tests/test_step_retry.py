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
        settings["inbox_dir"] = self.inbox_dir
        settings["outbox_dir"] = self.outbox_dir
        settings["nas_root"] = self.nas_root
        settings["storage_targets"] = [
            {"id": "nas", "type": "nas", "enabled": True, "name": "NAS Target"},
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
