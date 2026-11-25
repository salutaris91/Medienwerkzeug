import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import MagicMock, patch


def _wait_until(predicate, timeout=4.0, interval=0.02):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return bool(predicate())


class TestRoadmap95QueueControl(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.settings_file = os.path.join(self.temp_dir.name, "settings.json")
        self.jobs_state_file = os.path.join(self.temp_dir.name, "jobs_state.json")
        self.env_file = os.path.join(self.temp_dir.name, ".env")

        self._orig_env = {
            k: os.environ.get(k)
            for k in ("MW_SETTINGS_FILE", "MW_JOBS_STATE_FILE", "MW_ENV_FILE", "MW_DATA_DIR", "FLASK_SECRET_KEY")
        }
        os.environ["MW_SETTINGS_FILE"] = self.settings_file
        os.environ["MW_JOBS_STATE_FILE"] = self.jobs_state_file
        os.environ["MW_ENV_FILE"] = self.env_file
        os.environ["MW_DATA_DIR"] = self.temp_dir.name
        os.environ["FLASK_SECRET_KEY"] = "test-secret"

        import gui.core.persistence as persistence
        import gui.core.utils as utils
        import gui.core.jobs as jobs
        from gui.core.helpers import job_queue

        persistence._cached_settings = None
        persistence._MOCK_SETTINGS = None
        utils._MOCK_SETTINGS = None
        self.persistence = persistence
        self.jobs = jobs
        self.job_queue = job_queue

        with self.job_queue.mutex:
            self.job_queue.queue.clear()
            self.job_queue.unfinished_tasks = 0

        with self.jobs.active_jobs_lock:
            self.jobs.active_jobs.clear()
            with self.jobs._job_controls_lock:
                self.jobs._job_controls.clear()
        self.jobs._last_saved_time.clear()
        self.jobs._last_saved_progress.clear()
        self.jobs._jobs_loaded = True

        self.inbox_dir = os.path.join(self.temp_dir.name, "inbox")
        self.outbox_dir = os.path.join(self.temp_dir.name, "outbox")
        self.nas_root = os.path.join(self.temp_dir.name, "nas")
        for d in (self.inbox_dir, self.outbox_dir, self.nas_root, os.path.join(self.nas_root, "Filme")):
            os.makedirs(d, exist_ok=True)

        settings = persistence.load_settings()
        settings["data_dir"] = self.temp_dir.name
        settings["inbox_dir"] = self.inbox_dir
        settings["outbox_dir"] = self.outbox_dir
        settings["nas_root"] = self.nas_root
        settings["onboarded"] = True
        settings["storage_targets"] = [
            {"id": "nas", "type": "nas", "root_path": self.nas_root, "enabled": True, "name": "NAS"},
            {"id": "pcloud", "type": "pcloud", "root_path": "", "enabled": False, "name": "pCloud"},
        ]
        settings["sync_categories"] = [
            {"id": "1", "name": "Filme", "type": "movie", "nas_sub": "/Filme", "targets": {"nas": "/Filme", "pcloud": ""}}
        ]
        persistence.save_settings(settings)
        persistence.set_password("test-password")

        from gui.main import app
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-secret"
        self.client = app.test_client()
        self.client.post("/api/auth/login", json={"password": "test-password"})
        cookie = self.client.get_cookie("mw_csrf_token")
        self.csrf_token = cookie.value if cookie else ""

    def tearDown(self):
        from gui.core.helpers import _job_log_handles, close_job_log
        with self.job_queue.mutex:
            self.job_queue.queue.clear()
            self.job_queue.unfinished_tasks = 0
        for tid in list(_job_log_handles.keys()):
            close_job_log(tid)
        with self.jobs.active_jobs_lock:
            self.jobs.active_jobs.clear()
            with self.jobs._job_controls_lock:
                self.jobs._job_controls.clear()
        for k, v in self._orig_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self.persistence._cached_settings = None
        self.temp_dir.cleanup()

    def _post(self, url, payload=..., raw_data=None):
        headers = {"X-CSRF-Token": self.csrf_token}
        if raw_data is not None:
            headers["Content-Type"] = "application/json"
            return self.client.post(url, data=raw_data, headers=headers)
        return self.client.post(url, json=None if payload is ... else payload, headers=headers)

    def _enqueue_job(self, job_id, params=None, pipeline=None):
        params = params or {"media_type": "movie", "project_name": job_id}
        pipeline = pipeline or {
            "metadata": {"status": "done", "progress": 100},
            "convert": {"status": "pending", "progress": 0},
            "nas": {"status": "skipped", "progress": 0},
        }
        job = self.jobs.create_job(job_id, f"Job {job_id}", "movie", params, pipeline=pipeline, status="queued")
        self.job_queue.put(job)
        return job

    def test_ak1_cancel_queued_api_validation_clear_and_restart_guard(self):
        """AK1: Cancel queued job, validate JSON bodies, conditional paused_from, clear & system restart."""
        self._enqueue_job("q-cancel")
        self.assertEqual(self.job_queue.unfinished_tasks, 1)

        # GET /api/queue omits paused_from when None
        q_before = self.client.get("/api/queue").get_json()["jobs"]
        self.assertNotIn("paused_from", q_before[0])

        # Non-dict / missing task_id validation on all 4 endpoints -> HTTP 400 (no AttributeError)
        for ep in ("/api/queue/cancel", "/api/queue/pause", "/api/queue/resume", "/api/queue/retry"):
            for bad_raw in ('["x"]', '"str"', "123", "{}"):
                resp = self._post(ep, raw_data=bad_raw)
                self.assertEqual(resp.status_code, 400, f"{ep} with {bad_raw} must return 400")
            self.assertEqual(self._post(ep, {"task_id": "missing-id"}).status_code, 404)

        res = self._post("/api/queue/cancel", {"task_id": "q-cancel"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["job_status"], "cancelled")
        self.assertEqual(self.job_queue.unfinished_tasks, 0)
        self.assertEqual(len(self.job_queue.queue), 0)

        job = self.jobs.get_job("q-cancel")
        self.assertEqual(job["status"], "cancelled")
        self.assertEqual(job["pipeline"]["metadata"]["status"], "done")
        self.assertEqual(job["pipeline"]["convert"]["status"], "cancelled")
        self.assertEqual(job["pipeline"]["nas"]["status"], "skipped")

        # Cancelling an already terminal job returns 400
        self.assertEqual(self._post("/api/queue/cancel", {"task_id": "q-cancel"}).status_code, 400)

        # Cancelled job does NOT block /api/system/restart with 'busy'
        with patch("gui.api.system_api._restart_server_process"):
            r_restart = self._post("/api/system/restart", {})
        self.assertEqual(r_restart.get_json()["status"], "restarting")

        # Active intermediate states DO block /api/system/restart with 'busy'
        self.jobs.create_job("paused-one", "Paused", "movie", {}, status="paused")
        self.assertEqual(self._post("/api/system/restart", {}).get_json()["status"], "busy")

        # /api/queue/clear removes only done/error/cancelled and keeps active states + job_queue
        for st in ("done", "error", "queued", "running", "pausing", "cancelling"):
            self.jobs.create_job(f"st-{st}", st, "movie", {}, status=st)
        self.job_queue.put({"id": "st-queued", "params": {}})
        self.assertEqual(self._post("/api/queue/clear", {}).status_code, 200)
        remaining = {j["id"] for j in self.jobs.get_all_jobs()}
        self.assertEqual(remaining, {"paused-one", "st-queued", "st-running", "st-pausing", "st-cancelling"})
        self.assertEqual(len(self.job_queue.queue), 1)

    def test_ak2_pause_queued_overtake_resume_and_worker_races(self):
        """AK2: Queued Job A paused -> Job B overtakes -> Job A resumed; dequeue & end-of-run races stay safe."""
        executed_order = []

        def fake_worker(params):
            tid = params["task_id"]
            executed_order.append(tid)
            if tid == "race-end-cancelling":
                # Simulate cancel arriving right after last checkpoint before worker exits
                with self.jobs.active_jobs_lock:
                    self.jobs.active_jobs[tid]["status"] = "cancelling"

        self._enqueue_job("job-a")
        self._enqueue_job("job-b")

        r_pause = self._post("/api/queue/pause", {"task_id": "job-a"})
        self.assertEqual(r_pause.status_code, 200)
        self.assertEqual(r_pause.get_json()["job_status"], "paused")
        q_jobs = {j["id"]: j for j in self.client.get("/api/queue").get_json()["jobs"]}
        self.assertEqual(q_jobs["job-a"]["paused_from"], "queued")

        from gui.workers.processor import job_queue_worker
        with patch("gui.workers.processor.process_worker", side_effect=fake_worker):
            worker_t = threading.Thread(target=job_queue_worker, daemon=True)
            worker_t.start()

            self.assertTrue(_wait_until(lambda: self.jobs.get_job("job-b")["status"] == "done"))
            self.assertEqual(self.jobs.get_job("job-a")["status"], "paused")
            self.assertEqual(executed_order, ["job-b"])

            # Resume Job A -> runs to done
            r_res = self._post("/api/queue/resume", {"task_id": "job-a"})
            self.assertEqual(r_res.status_code, 200)
            self.assertEqual(r_res.get_json()["job_status"], "queued")
            self.assertTrue(_wait_until(lambda: self.jobs.get_job("job-a")["status"] == "done"))
            self.assertEqual(executed_order, ["job-b", "job-a"])

            # End-of-run race: job still 'cancelling' on worker exit must finalize to 'cancelled'
            self._enqueue_job("race-end-cancelling")
            self.assertTrue(_wait_until(lambda: self.jobs.get_job("race-end-cancelling")["status"] == "cancelled"))

            self.job_queue.put(None)
            worker_t.join(timeout=2.0)
            self.assertFalse(worker_t.is_alive())
            self.assertEqual(self.job_queue.unfinished_tasks, 0)

        # Dequeue-race: item already popped from job_queue while status == 'queued', paused then cancelled before process_worker
        self.jobs.create_job("deq-race", "Dequeue Race", "movie", {"media_type": "movie"}, status="queued")
        ok, _, st = self.jobs.pause_job("deq-race")
        self.assertTrue(ok)
        self.assertEqual(st, "pausing")
        self.assertEqual(self.jobs.get_job("deq-race")["paused_from"], "running")

        entered_worker = []
        def run_single_dequeued():
            try:
                claimed, _ = self.jobs.claim_or_skip_dequeued_job("deq-race")
                if claimed:
                    entered_worker.append(True)
            except self.jobs.JobCancelledError:
                self.jobs.finalize_cancelled_job("deq-race")
            finally:
                self.jobs.finalize_cancelling_job_if_needed("deq-race")
                self.jobs.cleanup_job_control("deq-race")

        t_deq = threading.Thread(target=run_single_dequeued, daemon=True)
        t_deq.start()
        self.assertTrue(_wait_until(lambda: self.jobs.get_job("deq-race")["status"] == "paused"))
        self.jobs.cancel_job("deq-race")
        t_deq.join(timeout=2.0)
        self.assertFalse(t_deq.is_alive())
        self.assertEqual(entered_worker, [])
        self.assertEqual(self.jobs.get_job("deq-race")["status"], "cancelled")

    def test_ak3_subprocess_group_kill_no_retry_conversion_and_transfer_cleanup(self):
        """AK3: Kills full process group without retry, protects originals/pre-existing files, cleans partial outputs."""
        from gui.core.resilience import run_with_retries_and_timeout
        from gui.core import media, transfers

        # 1. Real subprocess + child in same process group via run_with_retries_and_timeout
        job_id = "subproc-kill-job"
        self.jobs.create_job(job_id, "Subproc Kill", "movie", {}, status="running")
        pid_file = os.path.join(self.temp_dir.name, "child.pid")
        attempts_counter = []
        py_script = (
            "import subprocess, sys, time; "
            f"c = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)']); "
            f"open({pid_file!r}, 'w').write(str(c.pid)); "
            "sys.stdout.write('READY\\n'); sys.stdout.flush(); time.sleep(30)"
        )
        err_holder = []

        def run_subproc():
            with self.jobs.bind_job_context(job_id):
                try:
                    run_with_retries_and_timeout(
                        [sys.executable, "-c", py_script],
                        max_attempts=3,
                        timeout_sec=30,
                        line_callback=lambda ln: attempts_counter.append(ln.strip()),
                    )
                except BaseException as exc:
                    err_holder.append(exc)
                    if isinstance(exc, self.jobs.JobCancelledError):
                        self.jobs.finalize_cancelled_job(job_id)

        t = threading.Thread(target=run_subproc, daemon=True)
        t.start()
        self.assertTrue(_wait_until(lambda: os.path.isfile(pid_file) and len(attempts_counter) >= 1))
        with open(pid_file, "r", encoding="utf-8") as f:
            child_pid = int(f.read().strip())

        r_cancel = self._post("/api/queue/cancel", {"task_id": job_id})
        self.assertEqual(r_cancel.status_code, 200)
        t.join(timeout=3.0)
        self.assertFalse(t.is_alive())
        self.assertEqual(len(err_holder), 1)
        self.assertIsInstance(err_holder[0], self.jobs.JobCancelledError)
        self.assertEqual(attempts_counter, ["READY"])  # No retry attempt started!
        self.assertEqual(self.jobs.get_job(job_id)["status"], "cancelled")

        def _pid_dead(pid):
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return True
            except PermissionError:
                return False
            # In containers whose PID 1 does not reap reparented orphans, killed children sit in State 'Z' (zombie)
            try:
                with open(f"/proc/{pid}/status", "r", encoding="utf-8") as fh:
                    for line in fh:
                        if line.startswith("State:"):
                            return line.split(":", 1)[1].strip()[:1] in ("Z", "X")
            except FileNotFoundError:
                return True
            except OSError:
                pass
            res = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True)
            stat_str = (res.stdout or "").strip()
            return res.returncode != 0 or not stat_str or stat_str.startswith("Z")

        self.assertTrue(_wait_until(lambda: _pid_dead(child_pid), timeout=2.5))

        # 2. execute_video_conversion: no libx265 fallback & no delete_original trash on cancel; temp_output deleted
        conv_job = "conv-cancel-job"
        self.jobs.create_job(conv_job, "Conv Cancel", "movie", {}, status="running")
        src_vid = os.path.join(self.inbox_dir, "orig.mp4")
        tmp_vid = os.path.join(self.inbox_dir, "orig_neu.mkv")
        fin_vid = os.path.join(self.inbox_dir, "orig.mkv")
        with open(src_vid, "wb") as f:
            f.write(b"ORIGINAL_VIDEO")

        ffmpeg_calls = []
        trash_mock = MagicMock()

        def fake_ffmpeg(cmd, filepath, task_id=None, log_queue=None):
            ffmpeg_calls.append(cmd)
            with open(tmp_vid, "wb") as tf:
                tf.write(b"PARTIAL_CONV")
            self.jobs.cancel_job(conv_job)
            raise self.jobs.JobCancelledError("Abgebrochen")

        with self.jobs.bind_job_context(conv_job), \
             patch("gui.core.media.build_hevc_ffmpeg_cmd", return_value=["ffmpeg", "-vaapi_device", "/dev/dri/renderD128", "-i", src_vid, tmp_vid]):
            with self.assertRaises(self.jobs.JobCancelledError):
                media.execute_video_conversion(
                    src_vid, tmp_vid, fin_vid, 60, "movie", "orig.mp4",
                    delete_original=True, progress_callback=conv_job,
                    log_message_fn=lambda m: None, run_ffmpeg_fn=fake_ffmpeg, send_to_trash_fn=trash_mock,
                )
        self.assertEqual(len(ffmpeg_calls), 1)
        trash_mock.assert_not_called()
        self.assertFalse(os.path.exists(tmp_vid))
        self.assertTrue(os.path.isfile(src_vid))

        # 3. Transfer cleanup: removes newly created partial folder/file, keeps pre-existing file byte-identical!
        big_src = os.path.join(self.outbox_dir, "big.bin")
        with open(big_src, "wb") as f:
            f.write(b"X" * (3 * 1024 * 1024))

        # 3a. Newly created folder -> removed completely on cancel
        new_folder_src = os.path.join(self.outbox_dir, "NewMovieDir")
        os.makedirs(new_folder_src, exist_ok=True)
        with open(os.path.join(new_folder_src, "movie.nfo"), "wb") as f:
            f.write(b"<movie/>")
        shutil.copy2(big_src, os.path.join(new_folder_src, "movie.mkv"))
        new_folder_dst = os.path.join(self.nas_root, "Filme", "NewMovieDir")

        copy_job_1 = "copy-cancel-new-dir"
        self.jobs.create_job(copy_job_1, "Copy New Dir", "movie", {}, status="running")
        with self.jobs.bind_job_context(copy_job_1), \
             patch("gui.core.transfers.subprocess.Popen", side_effect=FileNotFoundError("no rsync")):
            with self.assertRaises(self.jobs.JobCancelledError):
                transfers.run_rsync_with_progress(
                    new_folder_src,
                    new_folder_dst,
                    task_id=lambda pct, _m: self.jobs.cancel_job(copy_job_1) if pct >= 10 else None,
                )
        self.assertFalse(os.path.exists(new_folder_dst))

        # 3b. Pre-existing destination file -> content stays byte-identical on cancel!
        preexisting_file = os.path.join(self.nas_root, "Filme", "existing.bin")
        with open(preexisting_file, "wb") as f:
            f.write(b"ORIGINAL_BYTES_MUST_SURVIVE")

        copy_job_2 = "copy-cancel-preexisting"
        self.jobs.create_job(copy_job_2, "Copy Preexisting", "movie", {}, status="running")
        with self.jobs.bind_job_context(copy_job_2):
            with self.assertRaises(self.jobs.JobCancelledError):
                transfers.run_copy_fallback(
                    big_src,
                    preexisting_file,
                    task_id=lambda pct, _m: self.jobs.cancel_job(copy_job_2) if pct >= 10 else None,
                )
        with open(preexisting_file, "rb") as f:
            self.assertEqual(f.read(), b"ORIGINAL_BYTES_MUST_SURVIVE")

        # 3c. run_rsync_with_progress on pre-existing folder omits --inplace, removes new partial file, keeps existing bytes
        pre_dir_dst = os.path.join(self.nas_root, "Filme", "ExistingMovieDir")
        os.makedirs(pre_dir_dst, exist_ok=True)
        keep_nfo = os.path.join(pre_dir_dst, "movie.nfo")
        with open(keep_nfo, "wb") as f:
            f.write(b"<movie>PREEXISTING_NFO_BYTES</movie>")
        seen_rsync_cmds = []

        class _FakeRsyncProc:
            pid = 999991
            returncode = -15
            def __init__(self_p, cmd, **_kw):
                seen_rsync_cmds.append(list(cmd))
                with open(os.path.join(pre_dir_dst, "partial_new.mkv"), "wb") as pf:
                    pf.write(b"HALF_WRITTEN")
                self_p.stdout = io.BytesIO(b"  25%   10.00MB/s\n")
            def wait(self_p, timeout=None):
                return self_p.returncode
            def poll(self_p):
                return self_p.returncode

        rsync_job_3 = "rsync-cancel-preexisting-dir"
        self.jobs.create_job(rsync_job_3, "Rsync Preexisting Dir", "movie", {}, status="running")
        with self.jobs.bind_job_context(rsync_job_3), \
             patch("gui.core.transfers.get_rsync_progress_flag", return_value="--progress"), \
             patch("gui.core.transfers.subprocess.Popen", side_effect=_FakeRsyncProc):
            with self.assertRaises(self.jobs.JobCancelledError):
                transfers.run_rsync_with_progress(
                    new_folder_src,
                    pre_dir_dst,
                    task_id=lambda pct, _m: self.jobs.cancel_job(rsync_job_3) if pct >= 20 else None,
                )
        self.assertNotIn("--inplace", seen_rsync_cmds[0])
        self.assertFalse(os.path.exists(os.path.join(pre_dir_dst, "partial_new.mkv")))
        with open(keep_nfo, "rb") as f:
            self.assertEqual(f.read(), b"<movie>PREEXISTING_NFO_BYTES</movie>")

        # 4. youtube_merge cancel during upload preserves pending_videos and cleans .temp_yt_<task_id>
        settings = self.persistence.load_settings()
        settings["youtube_subscriptions"] = [{
            "id": "sub-1",
            "pending_videos": [{"id": "vid-1", "title": "Part 1"}],
            "downloaded_ids": [],
        }]
        self.persistence.save_settings(settings)

        yt_id = "yt-merge-cancel"
        yt_params = {
            "task_id": yt_id,
            "media_type": "youtube_merge",
            "yt_urls": ["https://example.com/1"],
            "title": "MergedDoc",
            "subscription_id": "sub-1",
            "video_ids_to_remove": ["vid-1"],
            "destination_id": "1",
            "copy_to_nas": True,
        }
        self.jobs.create_job(yt_id, "YT Merge", "youtube_merge", yt_params, status="running")

        def fake_ytdlp_ok(cmd, task_id=None, log_queue=None):
            temp_d = cmd[cmd.index("-P") + 1]
            with open(os.path.join(temp_d, "part_01.mkv"), "wb") as pf:
                pf.write(b"part-bytes")
            return True

        def fake_nas_rsync_cancel(*_a, **_kw):
            self.jobs.cancel_job(yt_id)
            raise self.jobs.JobCancelledError("Abgebrochen")

        from gui.workers.processor import process_worker
        with patch("gui.workers.processor.run_ytdlp_with_progress", side_effect=fake_ytdlp_ok), \
             patch("gui.workers.processor.ensure_nas_mounted", return_value=True), \
             patch("gui.workers.processor.run_rsync_with_progress", side_effect=fake_nas_rsync_cancel):
            with self.assertRaises(self.jobs.JobCancelledError):
                process_worker(yt_params)

        self.assertFalse(os.path.exists(os.path.join(self.inbox_dir, f".temp_yt_{yt_id}")))
        sub_after = self.persistence.load_settings()["youtube_subscriptions"][0]
        self.assertEqual([v["id"] for v in sub_after["pending_videos"]], ["vid-1"])
        self.assertEqual(sub_after["downloaded_ids"], [])

    def test_ak4_cooperative_pause_progress_guard_resume_and_cancel_from_paused(self):
        """AK4: Cooperative pausing -> paused -> resume -> done; progress guard; cancel wakes normalize & YT event."""
        # 1. Cooperative pause on running job + progress/running guard during 'pausing'
        job_id = "coop-pause-job"
        self.jobs.create_job(job_id, "Coop Job", "movie", {}, status="running")
        step1_started = threading.Event()
        allow_step1_finish = threading.Event()

        def worker_steps():
            with self.jobs.bind_job_context(job_id):
                self.jobs.wait_if_paused_or_cancelled(job_id)
                step1_started.set()
                allow_step1_finish.wait(timeout=3.0)
                # Checkpoint between step 1 and step 2 -> must park in 'paused'
                self.jobs.wait_if_paused_or_cancelled(job_id)
                self.jobs.update_job(job_id, status="done", progress=100, message="Erfolgreich beendet")

        wt = threading.Thread(target=worker_steps, daemon=True)
        wt.start()
        self.assertTrue(step1_started.wait(timeout=2.0))

        r_pause = self._post("/api/queue/pause", {"task_id": job_id})
        self.assertEqual(r_pause.status_code, 200)
        self.assertEqual(r_pause.get_json()["job_status"], "pausing")

        # Worker progress & status='running' updates during 'pausing' keep status='pausing' and prefix
        self.jobs.update_job(job_id, status="running", progress=42, message="Upload: 42%")
        snap_pausing = self.jobs.get_job(job_id)
        self.assertEqual(snap_pausing["status"], "pausing")
        self.assertEqual(snap_pausing["progress"], 42)
        self.assertTrue(snap_pausing["message"].startswith("Pausiert nach aktuellem Schritt"))
        self.assertIn("Upload: 42%", snap_pausing["message"])

        allow_step1_finish.set()
        self.assertTrue(_wait_until(lambda: self.jobs.get_job(job_id)["status"] == "paused"))
        self.assertEqual(self.jobs.get_job(job_id)["message"], "Pausiert")

        # Lagging worker update while 'paused' keeps 'Pausiert' message intact
        self.jobs.update_job(job_id, status="running", message="Unerwünschtes Update")
        self.assertEqual(self.jobs.get_job(job_id)["status"], "paused")
        self.assertEqual(self.jobs.get_job(job_id)["message"], "Pausiert")

        r_resume = self._post("/api/queue/resume", {"task_id": job_id})
        self.assertEqual(r_resume.status_code, 200)
        self.assertEqual(r_resume.get_json()["job_status"], "running")
        wt.join(timeout=2.0)
        self.assertEqual(self.jobs.get_job(job_id)["status"], "done")

        # 2. Normalize job integration: pause at item boundary, then cancel from paused -> immediate wakeup -> cancelled
        entered_first = threading.Event()
        release_first = threading.Event()

        def fake_apply_moves(items, on_progress=None):
            for idx, it in enumerate(items):
                if idx == 0:
                    entered_first.set()
                    release_first.wait(timeout=3.0)
                if on_progress:
                    on_progress(idx, len(items), it.get("label", "Film"))
            return {"moved": len(items), "skipped": 0, "errors": []}

        with patch("gui.core.transfers.validate_nas_library_preflight", return_value=(True, "")), \
             patch("gui.core.film_normalize.apply_moves", side_effect=fake_apply_moves):
            r_norm = self._post("/api/nas/normalize-films/apply", {"items": [{"label": "A"}, {"label": "B"}]})
            self.assertEqual(r_norm.status_code, 200)
            norm_id = r_norm.get_json()["task_id"]
            self.assertTrue(entered_first.wait(timeout=2.0))

            self.assertEqual(self._post("/api/queue/pause", {"task_id": norm_id}).status_code, 200)
            release_first.set()
            self.assertTrue(_wait_until(lambda: self.jobs.get_job(norm_id)["status"] == "paused"))

            # Cancel while parked in pause wakes thread immediately -> cancelled
            self.assertEqual(self._post("/api/queue/cancel", {"task_id": norm_id}).status_code, 200)
            self.assertTrue(_wait_until(lambda: self.jobs.get_job(norm_id)["status"] == "cancelled"))
            self.assertEqual(self.jobs.get_job(norm_id)["pipeline"]["normalize"]["status"], "cancelled")

        # 3. YouTube wait_event wakeup on cancel
        yt_wait_id = "yt-wait-cancel"
        self.jobs.create_job(yt_wait_id, "YT Wait", "youtube", {}, status="running")
        ev = threading.Event()
        self.jobs.register_job_wait_event(yt_wait_id, ev)
        woke = []

        def wait_yt():
            ev.wait(timeout=3.0)
            try:
                self.jobs.wait_if_paused_or_cancelled(yt_wait_id)
            except self.jobs.JobCancelledError:
                woke.append("cancelled")
                self.jobs.finalize_cancelled_job(yt_wait_id)

        ty = threading.Thread(target=wait_yt, daemon=True)
        ty.start()
        self._post("/api/queue/cancel", {"task_id": yt_wait_id})
        ty.join(timeout=2.0)
        self.assertEqual(woke, ["cancelled"])
        self.assertEqual(self.jobs.get_job(yt_wait_id)["status"], "cancelled")

    def test_interleaving_races_re_pause_parallel_retry_and_finalize_cleanup_barrier(self):
        """Deterministic race tests for R1 Findings 1, 3, and 4."""
        from gui.main import app
        from gui.workers import processor as proc_mod

        # 1. Finding 1: Dequeue-pause -> Resume -> immediate new Pause right as checkpoint exits
        re_id = "re-pause-after-claim-checkpoint"
        self.jobs.create_job(re_id, "RePause", "movie", {"media_type": "movie"}, status="queued")
        self.jobs.pause_job(re_id)  # removed_count == 0 -> status='pausing', resume_event cleared

        orig_wait = self.jobs.wait_if_paused_or_cancelled
        hooked_once = []
        reached_worker_body = threading.Event()

        def hooked_wait(explicit_task_id=None, _claim_if_queued=False):
            orig_wait(explicit_task_id, _claim_if_queued=_claim_if_queued)
            if _claim_if_queued and not hooked_once:
                hooked_once.append(True)
                # Immediate second pause right after wait_if_paused_or_cancelled returns inside claim_or_skip_dequeued_job
                ok_p, _, st_p = self.jobs.pause_job(re_id)
                self.assertTrue(ok_p)
                self.assertEqual(st_p, "pausing")

        def run_re_pause_worker():
            with self.jobs.bind_job_context(re_id) as ctx:
                try:
                    claimed, keep = self.jobs.claim_or_skip_dequeued_job(re_id)
                    if claimed:
                        # Status MUST still be 'pausing' here (never overwritten with 'running')
                        self.assertEqual(self.jobs.get_job(re_id)["status"], "pausing")
                        reached_worker_body.set()
                        self.jobs.wait_if_paused_or_cancelled(re_id)
                        self.jobs.update_job(re_id, status="done", progress=100)
                finally:
                    if not keep:
                        self.jobs.cleanup_job_control(re_id, expected_ctrl=ctx.ctrl)

        with patch.object(self.jobs, "wait_if_paused_or_cancelled", side_effect=hooked_wait):
            tw = threading.Thread(target=run_re_pause_worker, daemon=True)
            tw.start()
            self.assertTrue(_wait_until(lambda: self.jobs.get_job(re_id)["status"] == "paused"))
            # First resume -> hook fires immediate second pause -> worker parks in 'paused' again at next checkpoint
            self.jobs.resume_job(re_id)
            self.assertTrue(reached_worker_body.wait(timeout=2.0))
            self.assertTrue(_wait_until(lambda: self.jobs.get_job(re_id)["status"] == "paused"))
            self.assertTrue(tw.is_alive())
            # Second resume -> completes to 'done'
            self.jobs.resume_job(re_id)
            tw.join(timeout=2.0)
            self.assertFalse(tw.is_alive())
            self.assertEqual(self.jobs.get_job(re_id)["status"], "done")

        # 2. Finding 3: 5 parallel POST /api/queue/retry requests -> atomic single enqueue, no control reset race
        par_id = "parallel-retry-job"
        self.jobs.create_job(par_id, "Parallel Retry", "movie", {"media_type": "movie"}, status="cancelled")
        barrier = threading.Barrier(5)
        codes = []
        codes_lock = threading.Lock()

        def retry_caller():
            c = app.test_client()
            c.post("/api/auth/login", json={"password": "test-password"})
            tok = c.get_cookie("mw_csrf_token").value
            barrier.wait(timeout=3.0)
            resp = c.post("/api/queue/retry", json={"task_id": par_id}, headers={"X-CSRF-Token": tok})
            with codes_lock:
                codes.append(resp.status_code)

        threads = [threading.Thread(target=retry_caller, daemon=True) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=3.0)

        self.assertEqual(sorted(codes), [200, 400, 400, 400, 400])
        self.assertEqual(len(self.job_queue.queue), 1)
        self.assertEqual(self.job_queue.unfinished_tasks, 1)
        # Pause winning retry -> late retry request must return 400 without resetting pause or control events
        self.assertEqual(self._post("/api/queue/pause", {"task_id": par_id}).status_code, 200)
        par_ctrl = self.jobs.get_job_control(par_id)
        self.assertEqual(self._post("/api/queue/retry", {"task_id": par_id}).status_code, 400)
        self.assertIs(self.jobs.get_job_control(par_id), par_ctrl)
        self.assertEqual(self.jobs.get_job(par_id)["status"], "paused")
        self._post("/api/queue/cancel", {"task_id": par_id})

        # 3. Finding 4: Barrier-controlled Finalize ('cancelled') -> Retry -> Pause -> Old-Worker-Cleanup
        fin_id = "finalize-retry-cleanup-race"
        self._enqueue_job(fin_id)
        in_old_finally = threading.Event()
        release_old_finally = threading.Event()
        w1_cleaned_up = threading.Event()
        w1_entered = threading.Event()
        orig_fin_if_needed = self.jobs.finalize_cancelling_job_if_needed
        intercepted = []

        def barrier_finalize_if_needed(tid, expected_ctrl=self.jobs._UNSET):
            if tid == fin_id and not intercepted:
                intercepted.append(True)
                in_old_finally.set()
                release_old_finally.wait(timeout=3.0)
            return orig_fin_if_needed(tid, expected_ctrl=expected_ctrl)

        def fake_proc_w1(params):
            w1_entered.set()
            self.jobs.get_job_control(params["task_id"]).cancel_event.wait(timeout=3.0)
            raise self.jobs.JobCancelledError("Abgebrochen")

        with patch.object(self.jobs, "finalize_cancelling_job_if_needed", side_effect=barrier_finalize_if_needed), \
             patch.object(proc_mod, "process_worker", side_effect=fake_proc_w1):
            w1 = threading.Thread(target=proc_mod.job_queue_worker, daemon=True)
            w1.start()
            self.assertTrue(w1_entered.wait(timeout=2.0))
            self._post("/api/queue/cancel", {"task_id": fin_id})
            # Wait until Worker #1 has published status='cancelled' and is suspended before cleanup_job_control
            self.assertTrue(in_old_finally.wait(timeout=2.0))
            self.assertEqual(self.jobs.get_job(fin_id)["status"], "cancelled")

            # Now Retry + claim on Worker #2 + Pause BEFORE Worker #1 runs cleanup_job_control!
            self.assertEqual(self._post("/api/queue/retry", {"task_id": fin_id}).status_code, 200)
            popped = self.job_queue.get(timeout=1.0)
            self.job_queue.task_done()
            self.assertEqual(popped["id"], fin_id)

            w2_parked = threading.Event()
            def run_w2():
                with self.jobs.bind_job_context(fin_id) as ctx2:
                    try:
                        claimed2, keep2 = self.jobs.claim_or_skip_dequeued_job(fin_id)
                        self.assertTrue(claimed2)
                        w2_parked.set()
                        w1_cleaned_up.wait(timeout=3.0)
                        self.jobs.wait_if_paused_or_cancelled(fin_id)
                        self.jobs.update_job(fin_id, status="done", progress=100)
                    finally:
                        if not keep2:
                            self.jobs.cleanup_job_control(fin_id, expected_ctrl=ctx2.ctrl)

            w2 = threading.Thread(target=run_w2, daemon=True)
            w2.start()
            self.assertTrue(w2_parked.wait(timeout=2.0))
            ctrl_2 = self.jobs.get_job_control(fin_id)

            self.assertEqual(self._post("/api/queue/pause", {"task_id": fin_id}).status_code, 200)
            self.assertFalse(ctrl_2.resume_event.is_set())

            # Release Worker #1 to run cleanup_job_control + stop Worker #1 strictly BEFORE w2 hits checkpoint
            self.job_queue.put(None)
            release_old_finally.set()
            w1.join(timeout=2.0)
            self.assertFalse(w1.is_alive())
            w1_cleaned_up.set()

            # ctrl_2 and its cleared resume_event MUST survive -> Worker #2 parks in 'paused', NOT 'running'!
            self.assertIs(self.jobs._job_controls.get(fin_id), ctrl_2)
            self.assertTrue(_wait_until(lambda: self.jobs.get_job(fin_id)["status"] == "paused"))
            self.assertTrue(w2.is_alive())

            self._post("/api/queue/resume", {"task_id": fin_id})
            w2.join(timeout=2.0)
            self.assertFalse(w2.is_alive())
            self.assertEqual(self.jobs.get_job(fin_id)["status"], "done")

    def test_commit_job_retry_state_persistence_cancelling_stale_terminal_and_isolation(self):
        """Delta Test 1: commit_job_retry_state persists to disk (incl. cancelling), rejects stale/terminal, isolates jobs."""
        job_id = "retry-state-job"
        self.jobs.create_job(
            job_id, "Retry State", "tv", {"media_type": "tv", "main_nfo_fingerprint": None}, status="running"
        )
        ctrl_1 = self.jobs.get_job_control(job_id)

        with self.jobs.bind_job_context(job_id, ctrl=ctrl_1):
            ok1 = self.jobs.commit_job_retry_state(
                job_id,
                retry_state={"step0_done": True, "tv_renamed": {"ep1.mp4": "Show - S01E01.mp4"}},
                params_patch={"main_nfo_fingerprint": "fp-run-1"},
            )
            self.assertTrue(ok1)

            # Transition to 'cancelling' -> commit_job_retry_state must still persist for current run
            self.jobs.cancel_job(job_id)
            self.assertEqual(self.jobs.get_job(job_id)["status"], "cancelling")
            ok2 = self.jobs.commit_job_retry_state(
                job_id,
                retry_state={"tv_nfo_generated": {"ep1.mp4": "Show - S01E01.nfo"}},
                params_patch={"main_nfo_fingerprint": "fp-cancelling"},
            )
            self.assertTrue(ok2)

        with open(self.jobs_state_file, "r", encoding="utf-8") as fh:
            disk_job = json.load(fh)[job_id]
        self.assertEqual(
            disk_job["retry_state"],
            {
                "step0_done": True,
                "tv_renamed": {"ep1.mp4": "Show - S01E01.mp4"},
                "tv_nfo_generated": {"ep1.mp4": "Show - S01E01.nfo"},
            },
        )
        self.assertEqual(disk_job["params"]["main_nfo_fingerprint"], "fp-cancelling")
        self.assertNotIn("manifest", disk_job)

        # Stale run context (bound is not cur_ctrl) -> rejected
        self.jobs.reset_job_control(job_id)
        with self.jobs.bind_job_context(job_id, ctrl=ctrl_1):
            self.assertFalse(
                self.jobs.commit_job_retry_state(
                    job_id,
                    retry_state={"step0_done": False},
                    params_patch={"main_nfo_fingerprint": "stale-fp"},
                )
            )
        self.assertEqual(self.jobs.get_job(job_id)["params"]["main_nfo_fingerprint"], "fp-cancelling")

        # Terminal statuses ('done', 'error', 'cancelled') -> rejected
        for term_status in ("done", "error", "cancelled"):
            with self.jobs.active_jobs_lock:
                self.jobs.active_jobs[job_id]["status"] = term_status
            self.assertFalse(
                self.jobs.commit_job_retry_state(
                    job_id,
                    retry_state={"step0_done": False, "tampered": term_status},
                    params_patch={"main_nfo_fingerprint": f"fp-{term_status}"},
                )
            )
        with open(self.jobs_state_file, "r", encoding="utf-8") as fh:
            disk_after = json.load(fh)[job_id]
        self.assertTrue(disk_after["retry_state"]["step0_done"])
        self.assertNotIn("tampered", disk_after["retry_state"])
        self.assertEqual(disk_after["params"]["main_nfo_fingerprint"], "fp-cancelling")

        # Foreign new job -> inherits no retry_state or params
        foreign = self.jobs.create_job("foreign-fresh-job", "Fresh", "tv", {"media_type": "tv"}, status="queued")
        self.assertNotIn("retry_state", foreign)
        self.assertNotIn("main_nfo_fingerprint", foreign["params"])

    def test_handle_transfer_task_cancel_cleans_new_nas_dirs_and_missing_src_no_empty_dir(self):
        """Delta Test 4: _handle_transfer_task with real subprocess cancel removes new NAS dirs, keeps parent dirs, and creates no dir on FileNotFoundError."""
        from gui.workers.processor import _handle_transfer_task

        real_popen = subprocess.Popen
        nas_movies_root = os.path.join(self.nas_root, "Filme")
        nas_show_root = os.path.join(self.nas_root, "Serien", "VorbestandsSerie")
        os.makedirs(nas_movies_root, exist_ok=True)
        os.makedirs(nas_show_root, exist_ok=True)

        outbox_movie_dir = os.path.join(self.outbox_dir, "Filme", "CancelMovie (2026)")
        os.makedirs(outbox_movie_dir, exist_ok=True)
        with open(os.path.join(outbox_movie_dir, "CancelMovie (2026).mkv"), "wb") as f:
            f.write(b"MOVIE_DATA")
        with open(os.path.join(outbox_movie_dir, "CancelMovie (2026).nfo"), "wb") as f:
            f.write(b"<movie/>")

        outbox_ep_dir = os.path.join(
            self.outbox_dir, "Serien", "VorbestandsSerie", "Staffel 1", "VorbestandsSerie - S01E01 - Pilot"
        )
        os.makedirs(outbox_ep_dir, exist_ok=True)
        with open(os.path.join(outbox_ep_dir, "VorbestandsSerie - S01E01 - Pilot.mkv"), "wb") as f:
            f.write(b"EP_DATA")
        with open(os.path.join(outbox_ep_dir, "VorbestandsSerie - S01E01 - Pilot.nfo"), "wb") as f:
            f.write(b"<episodedetails/>")

        dest_movie_nas = os.path.join(nas_movies_root, "CancelMovie (2026)")
        dest_season_nas = os.path.join(nas_show_root, "Staffel 1")
        dest_ep_nas = os.path.join(dest_season_nas, "VorbestandsSerie - S01E01 - Pilot")

        cases = [
            (
                "movie-nas-cancel",
                {
                    "type": "movie_nas_transfer",
                    "target_id": "nas",
                    "file_idx": 0,
                    "dest_movie_dir_outbox": outbox_movie_dir,
                    "dest_movie_dir_nas": dest_movie_nas,
                    "final_filename": "CancelMovie (2026).mkv",
                },
                os.path.join(dest_movie_nas, "CancelMovie (2026).mkv"),
                [dest_movie_nas],
                nas_movies_root,
            ),
            (
                "tv-nas-cancel",
                {
                    "type": "nas_transfer",
                    "target_id": "nas",
                    "file_idx": 0,
                    "dest_dir_outbox": outbox_ep_dir,
                    "dest_dir_nas": dest_ep_nas,
                    "final_filename": "VorbestandsSerie - S01E01 - Pilot.mkv",
                    "clean_title": "VorbestandsSerie - S01E01 - Pilot",
                },
                os.path.join(dest_ep_nas, "VorbestandsSerie - S01E01 - Pilot.mkv"),
                [dest_ep_nas, dest_season_nas],
                nas_show_root,
            ),
        ]

        for job_id, task_dict, partial_target_file, must_not_exist, parent_must_exist in cases:
            with self.subTest(job_id=job_id):
                self.jobs.create_job(job_id, job_id, "movie", {}, status="running")
                spawned_procs = []

                def spawn_fake_rsync(_cmd, _target_f=partial_target_file, **kw):
                    script = (
                        "import os, sys, time; "
                        f"p = {_target_f!r}; "
                        "os.makedirs(os.path.dirname(p), exist_ok=True); "
                        "open(p, 'wb').write(b'PARTIAL'); "
                        "sys.stdout.write('  25%   12.00MB/s\\n'); sys.stdout.flush(); "
                        "time.sleep(30)"
                    )
                    proc = real_popen([sys.executable, "-c", script], **kw)
                    spawned_procs.append(proc)
                    return proc

                target_progs = {"nas": [0]}
                target_speeds = {"nas": [""]}
                plock = threading.RLock()

                def on_global_prog(_jid=job_id):
                    if target_progs["nas"][0] >= 20:
                        self.jobs.cancel_job(_jid)

                try:
                    with self.jobs.bind_job_context(job_id), \
                         patch("gui.core.transfers.get_rsync_progress_flag", return_value="--progress"), \
                         patch("gui.core.transfers.subprocess.Popen", side_effect=spawn_fake_rsync):
                        with self.assertRaises(self.jobs.JobCancelledError):
                            _handle_transfer_task(
                                task_dict, job_id, target_progs, target_speeds, plock, 1, lambda _m: None, on_global_prog
                            )
                finally:
                    for proc in spawned_procs:
                        if proc.stdout:
                            proc.stdout.close()

                for p in must_not_exist:
                    self.assertFalse(os.path.exists(p), f"Newly created NAS dir {p} must be cleaned up on cancel")
                self.assertTrue(os.path.isdir(parent_must_exist), f"Pre-existing NAS parent {parent_must_exist} must stay")

        # Missing source raising FileNotFoundError -> no empty target folder is pre-created by _handle_transfer_task
        missing_movie_nas = os.path.join(nas_movies_root, "MissingSrcFilm (2026)")
        missing_ep_nas = os.path.join(nas_show_root, "Staffel 9", "VorbestandsSerie - S09E01 - Missing")
        for m_id, m_task, m_dst in (
            (
                "missing-movie-src",
                {
                    "type": "movie_nas_transfer",
                    "target_id": "nas",
                    "file_idx": 0,
                    "dest_movie_dir_outbox": os.path.join(self.outbox_dir, "Filme", "DoesNotExist"),
                    "dest_movie_dir_nas": missing_movie_nas,
                    "final_filename": "DoesNotExist.mkv",
                },
                missing_movie_nas,
            ),
            (
                "missing-tv-src",
                {
                    "type": "nas_transfer",
                    "target_id": "nas",
                    "file_idx": 0,
                    "dest_dir_outbox": os.path.join(self.outbox_dir, "Serien", "DoesNotExist"),
                    "dest_dir_nas": missing_ep_nas,
                    "final_filename": "DoesNotExist.mkv",
                    "clean_title": "DoesNotExist",
                },
                os.path.dirname(missing_ep_nas),
            ),
        ):
            self.jobs.create_job(m_id, m_id, "movie", {}, status="running")
            with self.jobs.bind_job_context(m_id), \
                 patch("gui.workers.processor.run_rsync_with_progress", side_effect=FileNotFoundError("Quelle fehlt")):
                with self.assertRaises(FileNotFoundError):
                    _handle_transfer_task(
                        m_task, m_id, {"nas": [0]}, {"nas": [""]}, threading.RLock(), 1, lambda _m: None, lambda: None
                    )
            self.assertFalse(os.path.exists(m_dst))


if __name__ == "__main__":
    unittest.main()
