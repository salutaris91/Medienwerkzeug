import os
import tempfile
import unittest
from unittest.mock import patch
from wsgiref.validate import validator
from werkzeug.test import Client

from gui.core.transfers import (
    _calculate_cloud_upload_timeout_sec,
    copy_to_cloud_target,
)


class TestCloudTransferAndLogs(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self._env_keys = (
            "MW_SETTINGS_FILE",
            "MW_JOBS_STATE_FILE",
            "MW_ENV_FILE",
            "MW_DATA_DIR",
            "FLASK_SECRET_KEY",
        )
        self._prev_env = {k: os.environ.get(k) for k in self._env_keys}

        self.settings_file = os.path.join(self.temp_dir.name, "settings.json")
        self.jobs_state_file = os.path.join(self.temp_dir.name, "jobs_state.json")
        self.env_file = os.path.join(self.temp_dir.name, ".env")

        os.environ["MW_SETTINGS_FILE"] = self.settings_file
        os.environ["MW_JOBS_STATE_FILE"] = self.jobs_state_file
        os.environ["MW_ENV_FILE"] = self.env_file
        os.environ["MW_DATA_DIR"] = self.temp_dir.name
        os.environ["FLASK_SECRET_KEY"] = "test-secret-key"

        import gui.core.persistence as persistence
        persistence._cached_settings = None

        self.src_dir = os.path.join(self.temp_dir.name, "Die Odyssee (2026)")
        os.makedirs(self.src_dir, exist_ok=True)
        self.src_file = os.path.join(self.src_dir, "Die Odyssee (2026).mkv")
        with open(self.src_file, "wb") as f:
            f.write(b"demo")

        self.settings = {
            "onboarded": True,
            "password_hash": "",
            "nas_root": "/nas",
            "storage_targets": [
                {
                    "id": "pcloud",
                    "name": "pCloud",
                    "type": "cloud",
                    "enabled": True,
                    "root_path": "",
                    "rclone_remote": "pcloud:",
                }
            ],
            "sync_categories": [
                {
                    "id": "filme",
                    "nas_sub": "/Filme",
                    "pcloud_remote": "pcloud:03_Filme",
                }
            ],
        }
        persistence.save_settings(self.settings)

    def tearDown(self):
        for k, prev in self._prev_env.items():
            if prev is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = prev
        self.temp_dir.cleanup()

    def test_rclone_notice_stats_progress_and_retry_reset(self):
        """Testfall 1: rclone nutzt --stats-log-level NOTICE, parst 0 B/s + MiB/s und resettet bei Retry."""
        progress_events = []
        logged_messages = []

        def fake_run(cmd, max_attempts=3, timeout_sec=300, line_callback=None):
            self.assertIn("--stats-log-level", cmd)
            idx = cmd.index("--stats-log-level")
            self.assertEqual(cmd[idx + 1], "NOTICE")

            sample_lines = [
                "2026/11/23 07:00:01 NOTICE:     0 B / 27.02 GiB, 0%, 0 B/s, ETA -\n",
                "2026/11/23 07:00:02 NOTICE:   2.70 GiB / 27.02 GiB, 10%, 4.25 MiB/s, ETA 1h45m\n",
                "2026/11/23 07:00:03 NOTICE:   4.05 GiB / 27.02 GiB, 15%, 4.50 MiB/s, ETA 1h30m\n",
                "2026/11/23 07:00:04 NOTICE:   5.40 GiB / 27.02 GiB, 20%, 4.10 MiB/s, ETA 1h20m\n",
                "2026/11/23 07:01:00 NOTICE:     0 B / 27.02 GiB, 0%, 0 B/s, ETA -\n",
                "2026/11/23 07:01:10 NOTICE:   2.70 GiB / 27.02 GiB, 10%, 3.90 MiB/s, ETA 1h50m\n",
            ]
            for line in sample_lines:
                line_callback(line)
            return True

        with patch("gui.core.transfers.load_settings", return_value=self.settings), \
             patch("gui.core.transfers.shutil.which", return_value="/usr/bin/rclone"), \
             patch("gui.core.transfers.run_with_retries_and_timeout", side_effect=fake_run), \
             patch("gui.core.transfers.log_message", side_effect=logged_messages.append):
            ok = copy_to_cloud_target(
                self.src_dir,
                "/nas/Filme",
                "pcloud",
                task_id=lambda pct, msg: progress_events.append((pct, msg)),
            )

        self.assertTrue(ok)
        self.assertEqual(
            progress_events,
            [
                (0, "Upload (pCloud): 0% (0 B/s)"),
                (10, "Upload (pCloud): 10% (4.25 MiB/s)"),
                (15, "Upload (pCloud): 15% (4.50 MiB/s)"),
                (20, "Upload (pCloud): 20% (4.10 MiB/s)"),
                (0, "Upload (pCloud): 0% (0 B/s)"),
                (10, "Upload (pCloud): 10% (3.90 MiB/s)"),
            ],
        )

        pct_logs = [m for m in logged_messages if m.startswith("Upload (pCloud):")]
        self.assertEqual(
            pct_logs,
            [
                "Upload (pCloud): 0% (0 B/s)",
                "Upload (pCloud): 10% (4.25 MiB/s)",
                "Upload (pCloud): 20% (4.10 MiB/s)",
                "Upload (pCloud): 0% (0 B/s)",
                "Upload (pCloud): 10% (3.90 MiB/s)",
            ],
        )

    def test_dynamic_cloud_upload_timeout_bounds_and_usage(self):
        """Testfall 2: Timeout skaliert mit Dateigröße (min 3600s, >50000s bei ~28 GiB, max 172800s)."""
        self.assertEqual(
            _calculate_cloud_upload_timeout_sec(os.path.join(self.temp_dir.name, "missing")),
            3600,
        )
        self.assertEqual(_calculate_cloud_upload_timeout_sec(self.src_dir), 3600)

        size_28_gib = 28 * 1024 ** 3
        with patch("gui.core.transfers.os.path.getsize", return_value=size_28_gib):
            large_timeout = _calculate_cloud_upload_timeout_sec(self.src_dir)
        self.assertGreater(large_timeout, 50000)
        self.assertLessEqual(large_timeout, 172800)

        size_200_gib = 200 * 1024 ** 3
        with patch("gui.core.transfers.os.path.getsize", return_value=size_200_gib):
            capped_timeout = _calculate_cloud_upload_timeout_sec(self.src_dir)
        self.assertEqual(capped_timeout, 172800)

        captured_timeouts = []

        def fake_run(cmd, max_attempts=3, timeout_sec=300, line_callback=None):
            captured_timeouts.append(timeout_sec)
            return True

        with patch("gui.core.transfers.load_settings", return_value=self.settings), \
             patch("gui.core.transfers.shutil.which", return_value="/usr/bin/rclone"), \
             patch("gui.core.transfers.os.path.getsize", return_value=size_28_gib), \
             patch("gui.core.transfers.run_with_retries_and_timeout", side_effect=fake_run), \
             patch("gui.core.transfers.log_message"):
            ok = copy_to_cloud_target(self.src_dir, "/nas/Filme", "pcloud")

        self.assertTrue(ok)
        self.assertEqual(len(captured_timeouts), 1)
        self.assertGreater(captured_timeouts[0], 50000)

    def test_rclone_error_lines_logged_without_duplication(self):
        """Testfall 3: Fehler- und Diagnosezeilen werden bei Fehlschlag nicht verschluckt und nicht doppelt geloggt."""
        logged_messages = []
        error_line = "2026/11/23 07:30:00 ERROR : Die Odyssee (2026).mkv: Failed to copy: quota exceeded"
        diag_line = "2026/11/23 07:30:01 NOTICE: Final transfer summary without percent"

        def fake_run(cmd, max_attempts=3, timeout_sec=300, line_callback=None):
            line_callback(error_line + "\n")
            line_callback(diag_line + "\n")
            return False

        with patch("gui.core.transfers.load_settings", return_value=self.settings), \
             patch("gui.core.transfers.shutil.which", return_value="/usr/bin/rclone"), \
             patch("gui.core.transfers.run_with_retries_and_timeout", side_effect=fake_run), \
             patch("gui.core.transfers.log_message", side_effect=logged_messages.append):
            ok = copy_to_cloud_target(self.src_dir, "/nas/Filme", "pcloud")

        self.assertFalse(ok)
        expected_err = f"   rclone: {error_line}"
        expected_diag = f"   rclone: {diag_line}"
        self.assertEqual(logged_messages.count(expected_err), 1)
        self.assertEqual(logged_messages.count(expected_diag), 1)

    def test_api_logs_pep3333_wsgi_compliant_sse(self):
        """Testfall 4: /api/logs liefert PEP-3333-konformes SSE ohne verbotenen Connection-Header."""
        from gui.main import app

        validated_app = validator(app.wsgi_app)
        client = Client(validated_app)
        response = client.get("/api/logs", buffered=False)
        try:
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.mimetype, "text/event-stream")
            header_names_lower = {k.lower() for k in response.headers.keys()}
            self.assertNotIn("connection", header_names_lower)
            self.assertEqual(response.headers.get("Cache-Control"), "no-cache")
            self.assertEqual(response.headers.get("X-Accel-Buffering"), "no")

            first_chunk = next(response.response)
            self.assertEqual(
                first_chunk,
                b"data: Konsole verbunden. Log-Streaming aktiv...\n\n",
            )
        finally:
            response.close()


if __name__ == "__main__":
    unittest.main()
