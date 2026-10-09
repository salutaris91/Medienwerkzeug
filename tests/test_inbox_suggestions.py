import os
import unittest
import tempfile
import time
from unittest.mock import patch, MagicMock
import gui.api.project_api as project_api


class TestInboxSuggestions(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.inbox_dir = os.path.join(self.temp_dir.name, "inbox")
        os.makedirs(self.inbox_dir, exist_ok=True)

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

        settings = self.persistence.load_settings()
        settings["inbox_dir"] = self.inbox_dir
        self.persistence.save_settings(settings)

        # Reset cache globals before each test
        project_api._inbox_cache = {}
        project_api._inbox_cache_time = 0

        from gui.main import app
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key-12345'
        self.app = app
        self.client = app.test_client()

    def tearDown(self):
        os.environ.pop("MW_SETTINGS_FILE", None)
        os.environ.pop("MW_JOBS_STATE_FILE", None)
        os.environ.pop("MW_ENV_FILE", None)
        os.environ.pop("MW_DATA_DIR", None)
        os.environ.pop("FLASK_SECRET_KEY", None)
        self.persistence._cached_settings = None
        project_api._inbox_cache = {}
        project_api._inbox_cache_time = 0
        self.temp_dir.cleanup()

    def test_inbox_suggestions_payload_folder_and_single_file(self):
        """AK1: Folder modified_at = max(mtime), total_size = sum(st_size); single file matches its own stats."""
        # 1. Create a project folder with 2 video files
        proj_folder = os.path.join(self.inbox_dir, "MyShow.S01")
        os.makedirs(proj_folder, exist_ok=True)

        file1 = os.path.join(proj_folder, "MyShow.S01E01.mp4")
        with open(file1, "wb") as f:
            f.write(b"x" * 1500)
        os.utime(file1, (1700000100, 1700000100))

        file2 = os.path.join(proj_folder, "MyShow.S01E02.mkv")
        with open(file2, "wb") as f:
            f.write(b"y" * 2500)
        os.utime(file2, (1700000900, 1700000900))

        # 2. Create a standalone video file in inbox root
        single_file = os.path.join(self.inbox_dir, "StandAloneMovie.2023.mp4")
        with open(single_file, "wb") as f:
            f.write(b"z" * 4000)
        os.utime(single_file, (1700000500, 1700000500))

        # Test via GET /api/inbox/analyze endpoint
        res = self.client.get('/api/inbox/analyze')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("suggestions", data)

        suggestions = {s["project"]: s for s in data["suggestions"]}
        self.assertIn("MyShow.S01", suggestions)
        self.assertIn("StandAloneMovie.2023.mp4", suggestions)

        # Verify folder stats
        folder_sug = suggestions["MyShow.S01"]
        self.assertEqual(folder_sug["video_count"], 2)
        self.assertEqual(folder_sug["total_size"], 4000)
        self.assertEqual(folder_sug["modified_at"], 1700000900)
        self.assertIsInstance(folder_sug["modified_at"], int)
        self.assertIsInstance(folder_sug["total_size"], int)

        # Verify single file stats
        single_sug = suggestions["StandAloneMovie.2023.mp4"]
        self.assertEqual(single_sug["video_count"], 1)
        self.assertEqual(single_sug["total_size"], 4000)
        self.assertEqual(single_sug["modified_at"], 1700000500)
        self.assertIsInstance(single_sug["modified_at"], int)
        self.assertIsInstance(single_sug["total_size"], int)

    def test_inbox_suggestions_stat_error_partial_failure(self):
        """AK2: If os.stat fails on one file, project stays in suggestions, failing file counts as 0/skipped, error is logged."""
        proj_folder = os.path.join(self.inbox_dir, "BrokenFiles.S01")
        os.makedirs(proj_folder, exist_ok=True)

        good_file = os.path.join(proj_folder, "BrokenFiles.S01E01.mp4")
        with open(good_file, "wb") as f:
            f.write(b"a" * 1200)
        os.utime(good_file, (1700000300, 1700000300))

        bad_file = os.path.join(proj_folder, "BrokenFiles.S01E02.mp4")
        with open(bad_file, "wb") as f:
            f.write(b"b" * 2000)
        os.utime(bad_file, (1700000800, 1700000800))

        real_stat = os.stat

        def mock_stat(path_arg, *args, **kwargs):
            if "S01E02" in str(path_arg):
                raise OSError("Simulated disk read error on bad file")
            return real_stat(path_arg, *args, **kwargs)

        with patch("os.stat", side_effect=mock_stat), patch("gui.api.project_api.log_message") as mock_log:
            suggestions = project_api.get_inbox_suggestions()
            self.assertEqual(len(suggestions), 1)
            sug = suggestions[0]
            self.assertEqual(sug["project"], "BrokenFiles.S01")
            self.assertEqual(sug["total_size"], 1200)
            self.assertEqual(sug["modified_at"], 1700000300)

            # Check that error was logged
            mock_log.assert_called()
            logged_messages = [call.args[0] for call in mock_log.call_args_list]
            self.assertTrue(any("Größen-/Datums-Berechnung" in msg for msg in logged_messages))

    def test_inbox_suggestions_stat_error_all_files_fail(self):
        """AK2: If all files fail os.stat, project remains in suggestions with modified_at=None and total_size=0."""
        proj_folder = os.path.join(self.inbox_dir, "AllBroken.S01")
        os.makedirs(proj_folder, exist_ok=True)

        f1 = os.path.join(proj_folder, "AllBroken.S01E01.mp4")
        with open(f1, "wb") as f:
            f.write(b"c" * 1000)

        real_stat = os.stat

        def mock_stat_all_fail(path_arg, *args, **kwargs):
            if str(path_arg).endswith(".mp4") or "AllBroken.S01E01" in str(path_arg):
                raise OSError("I/O error reading stats")
            return real_stat(path_arg, *args, **kwargs)

        with patch("os.stat", side_effect=mock_stat_all_fail), patch("gui.api.project_api.log_message") as mock_log:
            suggestions = project_api.get_inbox_suggestions()
            self.assertEqual(len(suggestions), 1)
            sug = suggestions[0]
            self.assertEqual(sug["project"], "AllBroken.S01")
            self.assertEqual(sug["total_size"], 0)
            self.assertIsNone(sug["modified_at"])
            mock_log.assert_called()

    def test_inbox_suggestions_is_dir(self):
        """AK1b: is_dir is True for directories (even with 1 video), False for single files."""
        # 1. Folder with exactly 1 video file -> is_dir: True
        single_video_folder = os.path.join(self.inbox_dir, "SingleVideoFolder")
        os.makedirs(single_video_folder, exist_ok=True)
        vf1 = os.path.join(single_video_folder, "Video.mp4")
        with open(vf1, "wb") as f:
            f.write(b"x" * 100)

        # 2. Folder with multiple video files -> is_dir: True
        multi_video_folder = os.path.join(self.inbox_dir, "MultiVideoFolder")
        os.makedirs(multi_video_folder, exist_ok=True)
        vf2 = os.path.join(multi_video_folder, "Ep01.mp4")
        vf3 = os.path.join(multi_video_folder, "Ep02.mp4")
        with open(vf2, "wb") as f:
            f.write(b"x" * 100)
        with open(vf3, "wb") as f:
            f.write(b"x" * 100)

        # 3. Standalone video file in inbox root -> is_dir: False
        standalone_file = os.path.join(self.inbox_dir, "StandaloneFile.mkv")
        with open(standalone_file, "wb") as f:
            f.write(b"x" * 100)

        res = self.client.get('/api/inbox/analyze')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        suggestions = {s["project"]: s for s in data["suggestions"]}

        self.assertIn("SingleVideoFolder", suggestions)
        self.assertEqual(suggestions["SingleVideoFolder"]["video_count"], 1)
        self.assertIs(suggestions["SingleVideoFolder"]["is_dir"], True)

        self.assertIn("MultiVideoFolder", suggestions)
        self.assertEqual(suggestions["MultiVideoFolder"]["video_count"], 2)
        self.assertIs(suggestions["MultiVideoFolder"]["is_dir"], True)

        self.assertIn("StandaloneFile.mkv", suggestions)
        self.assertEqual(suggestions["StandaloneFile.mkv"]["video_count"], 1)
        self.assertIs(suggestions["StandaloneFile.mkv"]["is_dir"], False)


if __name__ == "__main__":
    unittest.main()
