import os
import unittest
import tempfile
import time
import copy
import json
import shutil

class TestJobs(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.settings_file = os.path.join(self.temp_dir.name, "settings.json")
        self.jobs_state_file = os.path.join(self.temp_dir.name, "jobs_state.json")
        self.env_file = os.path.join(self.temp_dir.name, ".env")

        # Inject environment variables to force isolation
        os.environ["MW_SETTINGS_FILE"] = self.jobs_state_file  # persistence uses MW_SETTINGS_FILE / MW_JOBS_STATE_FILE
        os.environ["MW_JOBS_STATE_FILE"] = self.jobs_state_file
        os.environ["MW_ENV_FILE"] = self.env_file
        os.environ["MW_DATA_DIR"] = self.temp_dir.name

        # Write dummy settings
        self.inbox_dir = os.path.join(self.temp_dir.name, "inbox")
        self.outbox_dir = os.path.join(self.temp_dir.name, "outbox")
        os.makedirs(self.inbox_dir, exist_ok=True)
        os.makedirs(self.outbox_dir, exist_ok=True)
        
        with open(self.settings_file, "w", encoding="utf-8") as f:
            json.dump({
                "version": 1,
                "inbox_dir": self.inbox_dir,
                "outbox_dir": self.outbox_dir
            }, f)
        os.environ["MW_SETTINGS_FILE"] = self.settings_file

        # Import dynamically to apply environment variables
        import gui.core.jobs as jobs
        self.jobs = jobs
        
        # Reset internal states in jobs module and persistence cache
        import gui.core.persistence as persistence
        persistence._cached_settings = None
        persistence._cached_env = None
        self.jobs.active_jobs.clear()
        self.jobs._last_saved_time.clear()
        self.jobs._last_saved_progress.clear()
        self.jobs._jobs_loaded = False

    def tearDown(self):
        os.environ.pop("MW_SETTINGS_FILE", None)
        os.environ.pop("MW_JOBS_STATE_FILE", None)
        os.environ.pop("MW_ENV_FILE", None)
        os.environ.pop("MW_DATA_DIR", None)
        self.temp_dir.cleanup()

    def test_create_and_get_job(self):
        """Verifies job creation, loading, and recovery into RAM cache."""
        job = self.jobs.create_job("test-job-1", "Test Job 1", "movie", {"param1": "val1"})
        self.assertEqual(job["status"], "queued")
        self.assertEqual(job["progress"], 0)
        
        # Load from disk
        self.jobs.active_jobs.clear()  # clear memory cache
        loaded_job = self.jobs.get_job("test-job-1")
        self.assertIsNotNone(loaded_job)
        self.assertEqual(loaded_job["name"], "Test Job 1")
        self.assertEqual(loaded_job["params"]["param1"], "val1")

    def test_job_throttling(self):
        """Tests that progress updates are throttled but status and 0%/100% are immediate."""
        job_id = "throttled-job"
        self.jobs.create_job(job_id, "Throttled Job", "movie", {})
        
        # Initially stored on disk with progress 0
        with open(self.jobs_state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data[job_id]["progress"], 0)
        
        # Immediate status update to running (status change should write immediately)
        self.jobs.update_job(job_id, status="running")
        with open(self.jobs_state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data[job_id]["status"], "running")

        # Update progress to 10% (should write immediately since it's the first progress update and leap >= 5)
        self.jobs.update_job(job_id, progress=10)
        with open(self.jobs_state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data[job_id]["progress"], 10)

        # Update progress to 12% (leap is 2, time delta is 0, should be throttled/not written to disk)
        self.jobs.update_job(job_id, progress=12)
        with open(self.jobs_state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data[job_id]["progress"], 10)  # still 10 on disk!

        # Update progress to 20% (leap is 10, leap >= 5, should be written immediately)
        self.jobs.update_job(job_id, progress=20)
        with open(self.jobs_state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data[job_id]["progress"], 20)

    def test_crash_recovery(self):
        """Checks if interrupted jobs ('running' or 'queued') are recovered to 'error' state on startup."""
        # Create a pre-existing state on disk with running and done jobs
        disk_state = {
            "job-done": {"id": "job-done", "status": "done", "progress": 100, "message": "Success"},
            "job-running": {"id": "job-running", "status": "running", "progress": 50, "message": "Running"},
            "job-queued": {"id": "job-queued", "status": "queued", "progress": 0, "message": "Queued"},
        }
        with open(self.jobs_state_file, "w", encoding="utf-8") as f:
            json.dump(disk_state, f)
            
        self.jobs.recover_interrupted_jobs()
        
        # Verify from disk and RAM
        recovered = self.jobs.get_all_jobs()
        recovered_dict = {j["id"]: j for j in recovered}
        
        self.assertEqual(recovered_dict["job-done"]["status"], "done")
        self.assertEqual(recovered_dict["job-running"]["status"], "error")
        self.assertIn("unerwartet", recovered_dict["job-running"]["message"])
        self.assertEqual(recovered_dict["job-queued"]["status"], "error")

    def test_temp_quarantine(self):
        """Verifies that orphaned .mwtmp files older than 12 hours are moved to quarantine."""
        # Create temporary files
        old_file = os.path.join(self.inbox_dir, "old_file.mwtmp")
        new_file = os.path.join(self.inbox_dir, "new_file.mwtmp")
        regular_file = os.path.join(self.inbox_dir, "regular.mkv")
        
        with open(old_file, "w") as f: f.write("old content")
        with open(new_file, "w") as f: f.write("new content")
        with open(regular_file, "w") as f: f.write("regular content")
        
        # Set modification times
        now = time.time()
        os.utime(old_file, (now - 13 * 3600, now - 13 * 3600))  # 13 hours old
        os.utime(new_file, (now - 2 * 3600, now - 2 * 3600))    # 2 hours old
        os.utime(regular_file, (now - 24 * 3600, now - 24 * 3600)) # 24 hours old regular file
        
        self.jobs.clean_orphaned_temp_files()
        
        # Check destinations
        quarantine_dir = os.path.join(self.temp_dir.name, "quarantine")
        self.assertTrue(os.path.exists(os.path.join(quarantine_dir, "old_file.mwtmp")))
        self.assertFalse(os.path.exists(old_file))
        
        self.assertTrue(os.path.exists(new_file))
        self.assertFalse(os.path.exists(os.path.join(quarantine_dir, "new_file.mwtmp")))
        
        self.assertTrue(os.path.exists(regular_file))
        self.assertFalse(os.path.exists(os.path.join(quarantine_dir, "regular.mkv")))

    def test_clear_finished_jobs_and_queue_drain(self):
        """Verifies that clear_finished_jobs removes done, error, and queued jobs, and safely drains job_queue."""
        # Create some jobs
        self.jobs.create_job("job-done", "Job Done", "movie", {})
        self.jobs.create_job("job-error", "Job Error", "movie", {})
        self.jobs.create_job("job-queued", "Job Queued", "movie", {})
        self.jobs.create_job("job-running", "Job Running", "movie", {})
        
        # Set statuses
        self.jobs.update_job("job-done", status="done")
        self.jobs.update_job("job-error", status="error")
        self.jobs.update_job("job-queued", status="queued")
        self.jobs.update_job("job-running", status="running")
        
        # Populate the actual queue module job_queue
        from gui.core.helpers import job_queue
        # Push 2 dummy items to the internal queue
        job_queue.put({"id": "job-queued", "type": "test"})
        job_queue.put({"id": "some-other-queued", "type": "test"})
        
        initial_unfinished = job_queue.unfinished_tasks
        
        # Act
        self.jobs.clear_finished_jobs()
        
        # Verify active_jobs dictionary
        active = self.jobs.active_jobs
        self.assertNotIn("job-done", active)
        self.assertNotIn("job-error", active)
        self.assertNotIn("job-queued", active)
        self.assertIn("job-running", active)  # running should remain!
        
        # Verify job_queue is drained and unfinished_tasks is adjusted correctly
        self.assertEqual(len(job_queue.queue), 0)
        self.assertEqual(job_queue.unfinished_tasks, initial_unfinished - 2)

    def test_get_all_jobs_no_deadlock(self):
        """Verifies that calling get_all_jobs() when active_jobs is empty does not deadlock."""
        self.jobs.active_jobs.clear()
        
        # We start the call in a separate thread with a timeout to detect deadlocks.
        import threading
        
        thread = threading.Thread(target=self.jobs.get_all_jobs)
        thread.start()
        thread.join(timeout=2.0)
        
        self.assertFalse(thread.is_alive(), "get_all_jobs() deadlocked when active_jobs was empty!")

    def test_get_all_jobs_concurrent_no_double_load(self):
        """Verifies that concurrent calls to get_all_jobs() when active_jobs is empty do not cause double disk-reads."""
        self.jobs.active_jobs.clear()
        
        # Spy/Mock load_jobs_from_disk to count calls
        original_load = self.jobs.load_jobs_from_disk
        call_count = 0
        def mocked_load():
            nonlocal call_count
            call_count += 1
            # Simulate a small delay to widen the race window
            time.sleep(0.1)
            return original_load()
            
        self.jobs.load_jobs_from_disk = mocked_load
        
        try:
            import threading
            threads = [threading.Thread(target=self.jobs.get_all_jobs) for _ in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=2.0)
                
            self.assertEqual(call_count, 1, "load_jobs_from_disk was called more than once concurrently!")
        finally:
            self.jobs.load_jobs_from_disk = original_load

if __name__ == "__main__":
    unittest.main()
