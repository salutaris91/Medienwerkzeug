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

    def test_inbox_suggestions_single_video_folder_fields_ak2(self):
        """AK2: Folder with exactly 1 video per 10-ext list has single_video_relpath and single_video_query; others don't."""
        # 1. Folder with exactly 1 video in subfolder (nested)
        single_nested_folder = os.path.join(self.inbox_dir, "ThWaDeS11E23")
        nested_sub = os.path.join(single_nested_folder, "Sub")
        os.makedirs(nested_sub, exist_ok=True)
        vf_nested = os.path.join(nested_sub, "The.Walking.Dead.S11E23.720p.mkv")
        with open(vf_nested, "wb") as f:
            f.write(b"x" * 100)

        # 2. Folder with 2 videos by 10-ext list (.mp4 + .wmv), where 6-ext list only counts 1 (.mp4)
        mixed_folder = os.path.join(self.inbox_dir, "MixedFolder.S01")
        os.makedirs(mixed_folder, exist_ok=True)
        with open(os.path.join(mixed_folder, "Ep01.mp4"), "wb") as f:
            f.write(b"x" * 100)
        with open(os.path.join(mixed_folder, "Ep02.wmv"), "wb") as f:
            f.write(b"x" * 100)

        # 3. Folder with 0 videos by 6-ext list (e.g. only .flv) -> must not appear in suggestions
        flv_only_folder = os.path.join(self.inbox_dir, "FlvOnlyFolder")
        os.makedirs(flv_only_folder, exist_ok=True)
        with open(os.path.join(flv_only_folder, "Video.flv"), "wb") as f:
            f.write(b"x" * 100)

        # 4. Standalone file in inbox root
        standalone_file = os.path.join(self.inbox_dir, "The.Walking.Dead.S11E24.mkv")
        with open(standalone_file, "wb") as f:
            f.write(b"x" * 100)

        res = self.client.get('/api/inbox/analyze')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        suggestions = {s["project"]: s for s in data["suggestions"]}

        # (a) Folder with 1 video delivers single_video_relpath and single_video_query
        self.assertIn("ThWaDeS11E23", suggestions)
        single_sug = suggestions["ThWaDeS11E23"]
        self.assertEqual(single_sug["single_video_relpath"], "ThWaDeS11E23/Sub/The.Walking.Dead.S11E23.720p.mkv")
        self.assertEqual(single_sug["single_video_query"], "The.Walking.Dead")
        self.assertEqual(single_sug["video_count"], 1)

        # (b) Folder with 2 videos by 10-ext list does NOT have either field; video_count is 1 (6-ext list)
        self.assertIn("MixedFolder.S01", suggestions)
        mixed_sug = suggestions["MixedFolder.S01"]
        self.assertNotIn("single_video_relpath", mixed_sug)
        self.assertNotIn("single_video_query", mixed_sug)
        self.assertEqual(mixed_sug["video_count"], 1)

        # (c) Folder with 0 videos by 6-ext list does not appear at all
        self.assertNotIn("FlvOnlyFolder", suggestions)

        # (d) Standalone file does NOT have the additive fields
        self.assertIn("The.Walking.Dead.S11E24.mkv", suggestions)
        stand_sug = suggestions["The.Walking.Dead.S11E24.mkv"]
        self.assertNotIn("single_video_relpath", stand_sug)
        self.assertNotIn("single_video_query", stand_sug)
        self.assertEqual(stand_sug["suggested_query"], "The.Walking.Dead")

    def test_inbox_suggestions_single_video_query_pipeline_ak3(self):
        """AK3: single_video_query byte-identical to root suggested_query, fallback to folder suggested_query."""
        filename = "The.Walking.Dead.S11E23.720p.mkv"

        # 1. Single file in root
        root_file = os.path.join(self.inbox_dir, filename)
        with open(root_file, "wb") as f:
            f.write(b"x" * 100)

        # 2. Same filename inside single-video folder
        folder = os.path.join(self.inbox_dir, "ThWaDeS11E23")
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, filename), "wb") as f:
            f.write(b"x" * 100)

        # 3. Single-video folder with filename lacking SxxExx (e.g. video.mkv) -> fallback to folder query
        fallback_folder = os.path.join(self.inbox_dir, "ThWaDeS11E24")
        os.makedirs(fallback_folder, exist_ok=True)
        with open(os.path.join(fallback_folder, "video.mkv"), "wb") as f:
            f.write(b"x" * 100)

        res = self.client.get('/api/inbox/analyze')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        suggestions = {s["project"]: s for s in data["suggestions"]}

        root_sug = suggestions[filename]
        folder_sug = suggestions["ThWaDeS11E23"]
        fallback_sug = suggestions["ThWaDeS11E24"]

        # Byte-identical query
        self.assertEqual(folder_sug["single_video_query"], root_sug["suggested_query"])
        self.assertEqual(folder_sug["single_video_query"], "The.Walking.Dead")

        # Fallback when filename has no SxxExx: fallback to folder's suggested_query
        self.assertEqual(fallback_sug["single_video_query"], fallback_sug["suggested_query"])
        self.assertEqual(fallback_sug["single_video_query"], "ThWaDe")

    def test_ak1_lanterns_pattern_single_video_with_sample(self):
        """AK1: Lanterns pattern with >300MB episode, <300MB sample in Sample/, .nfo, .sfv, and foreign folder."""
        proj_dir = os.path.join(self.inbox_dir, "XyzS01E01")
        rel_dir = os.path.join(proj_dir, "Xyz.S01E01.Rel")
        sample_dir = os.path.join(rel_dir, "Sample")
        foreign_dir = os.path.join(proj_dir, "!!!WENN IHR MICH UNTERSTUETZEN WOLLT!!!")
        os.makedirs(sample_dir, exist_ok=True)
        os.makedirs(foreign_dir, exist_ok=True)

        main_mkv = os.path.join(rel_dir, "xyz.s01e01.rel.mkv")
        with open(main_mkv, "wb") as f:
            f.truncate(350 * 1024 * 1024)

        sample_mkv = os.path.join(sample_dir, "xyz.s01e01.rel-sample.mkv")
        with open(sample_mkv, "wb") as f:
            f.truncate(68 * 1024 * 1024)

        with open(os.path.join(rel_dir, "xyz.s01e01.rel.nfo"), "wb") as f:
            f.write(b"release info")
        with open(os.path.join(rel_dir, "xyz.s01e01.rel.sfv"), "wb") as f:
            f.write(b"checksums")
        with open(os.path.join(foreign_dir, "info.txt"), "wb") as f:
            f.write(b"support text")
        with open(os.path.join(foreign_dir, "link.URL"), "wb") as f:
            f.write(b"[InternetShortcut]\nURL=https://example.invalid")

        res = self.client.get('/api/inbox/analyze')
        self.assertEqual(res.status_code, 200)
        suggestions = {s["project"]: s for s in res.get_json()["suggestions"]}

        self.assertIn("XyzS01E01", suggestions)
        sug = suggestions["XyzS01E01"]
        self.assertEqual(
            sug.get("single_video_relpath"),
            "XyzS01E01/Xyz.S01E01.Rel/xyz.s01e01.rel.mkv",
        )
        self.assertEqual(sug.get("single_video_query"), "xyz")
        self.assertEqual(sug.get("video_count"), 2)

    def test_ak2_sample_by_name_or_path_segment_even_when_large(self):
        """AK2: Folder with large episode and second file matching sample by filename or path segment (>300MB) is single-video."""
        # 1. Sample by filename (> 300 MB)
        dir_by_name = os.path.join(self.inbox_dir, "ByNameS01E01")
        os.makedirs(dir_by_name, exist_ok=True)
        with open(os.path.join(dir_by_name, "Show.S01E01.mkv"), "wb") as f:
            f.truncate(400 * 1024 * 1024)
        with open(os.path.join(dir_by_name, "Show.S01E01-Sample.mkv"), "wb") as f:
            f.truncate(350 * 1024 * 1024)

        # 2. Sample by path segment 'Sample' (> 300 MB, filename without 'sample')
        dir_by_path = os.path.join(self.inbox_dir, "ByPathS01E02")
        sample_sub = os.path.join(dir_by_path, "Sample")
        os.makedirs(sample_sub, exist_ok=True)
        with open(os.path.join(dir_by_path, "Show.S01E02.mkv"), "wb") as f:
            f.truncate(400 * 1024 * 1024)
        with open(os.path.join(sample_sub, "preview_clip.mkv"), "wb") as f:
            f.truncate(350 * 1024 * 1024)

        res = self.client.get('/api/inbox/analyze')
        self.assertEqual(res.status_code, 200)
        suggestions = {s["project"]: s for s in res.get_json()["suggestions"]}

        sug_name = suggestions["ByNameS01E01"]
        self.assertEqual(sug_name.get("single_video_relpath"), "ByNameS01E01/Show.S01E01.mkv")
        self.assertEqual(sug_name.get("single_video_query"), "Show")
        self.assertEqual(sug_name.get("video_count"), 2)

        sug_path = suggestions["ByPathS01E02"]
        self.assertEqual(sug_path.get("single_video_relpath"), "ByPathS01E02/Show.S01E02.mkv")
        self.assertEqual(sug_path.get("single_video_query"), "Show")
        self.assertEqual(sug_path.get("video_count"), 2)

    def test_ak3_sample_by_size_only_without_sample_keyword(self):
        """AK3: Folder with one file >300MB and a second <300MB without 'sample' in name/path is single-video."""
        proj_dir = os.path.join(self.inbox_dir, "BySizeS01E01")
        os.makedirs(proj_dir, exist_ok=True)
        with open(os.path.join(proj_dir, "Show.S01E01.mkv"), "wb") as f:
            f.truncate(350 * 1024 * 1024)
        with open(os.path.join(proj_dir, "extra_teaser.mkv"), "wb") as f:
            f.truncate(50 * 1024 * 1024)

        res = self.client.get('/api/inbox/analyze')
        self.assertEqual(res.status_code, 200)
        suggestions = {s["project"]: s for s in res.get_json()["suggestions"]}

        sug = suggestions["BySizeS01E01"]
        self.assertEqual(sug.get("single_video_relpath"), "BySizeS01E01/Show.S01E01.mkv")
        self.assertEqual(sug.get("single_video_query"), "Show")
        self.assertEqual(sug.get("video_count"), 2)

    def test_ak4_two_real_videos_remain_non_single(self):
        """AK4: Two videos >300MB without 'sample' or two small videos <300MB do not get single_video_relpath."""
        # 1. Two large videos > 300 MB
        two_large = os.path.join(self.inbox_dir, "TwoLarge.S01")
        os.makedirs(two_large, exist_ok=True)
        with open(os.path.join(two_large, "Show.S01E01.mkv"), "wb") as f:
            f.truncate(350 * 1024 * 1024)
        with open(os.path.join(two_large, "Show.S01E02.mkv"), "wb") as f:
            f.truncate(360 * 1024 * 1024)

        # 2. Two small videos < 300 MB (no file > 300 MB -> criterion 2 does not apply)
        two_small = os.path.join(self.inbox_dir, "TwoSmall.S01")
        os.makedirs(two_small, exist_ok=True)
        with open(os.path.join(two_small, "Show.S01E01.mkv"), "wb") as f:
            f.truncate(80 * 1024 * 1024)
        with open(os.path.join(two_small, "Show.S01E02.mkv"), "wb") as f:
            f.truncate(20 * 1024 * 1024)

        res = self.client.get('/api/inbox/analyze')
        self.assertEqual(res.status_code, 200)
        suggestions = {s["project"]: s for s in res.get_json()["suggestions"]}

        self.assertNotIn("single_video_relpath", suggestions["TwoLarge.S01"])
        self.assertNotIn("single_video_query", suggestions["TwoLarge.S01"])
        self.assertEqual(suggestions["TwoLarge.S01"]["video_count"], 2)

        self.assertNotIn("single_video_relpath", suggestions["TwoSmall.S01"])
        self.assertNotIn("single_video_query", suggestions["TwoSmall.S01"])
        self.assertEqual(suggestions["TwoSmall.S01"]["video_count"], 2)

    def test_ak5_only_sample_excluded_but_single_small_video_kept(self):
        """AK5: Folder whose only video is a sample (criterion 1) gets no single_video_relpath; single small normal video does."""
        # 1. Only video has 'sample' in filename
        only_sample_name = os.path.join(self.inbox_dir, "OnlySampleName")
        os.makedirs(only_sample_name, exist_ok=True)
        with open(os.path.join(only_sample_name, "xyz-sample.mkv"), "wb") as f:
            f.truncate(50 * 1024 * 1024)

        # 2. Only video is inside 'Sample/' path segment
        only_sample_path = os.path.join(self.inbox_dir, "OnlySamplePath")
        os.makedirs(os.path.join(only_sample_path, "Sample"), exist_ok=True)
        with open(os.path.join(only_sample_path, "Sample", "xyz.s01e01.mkv"), "wb") as f:
            f.truncate(50 * 1024 * 1024)

        # 3. Single small video without 'sample' marker remains single-video folder
        single_small = os.path.join(self.inbox_dir, "SingleSmallNormal")
        os.makedirs(single_small, exist_ok=True)
        with open(os.path.join(single_small, "Show.S01E01.mkv"), "wb") as f:
            f.truncate(50 * 1024 * 1024)

        res = self.client.get('/api/inbox/analyze')
        self.assertEqual(res.status_code, 200)
        suggestions = {s["project"]: s for s in res.get_json()["suggestions"]}

        self.assertNotIn("single_video_relpath", suggestions["OnlySampleName"])
        self.assertNotIn("single_video_query", suggestions["OnlySampleName"])

        self.assertNotIn("single_video_relpath", suggestions["OnlySamplePath"])
        self.assertNotIn("single_video_query", suggestions["OnlySamplePath"])

        self.assertEqual(
            suggestions["SingleSmallNormal"].get("single_video_relpath"),
            "SingleSmallNormal/Show.S01E01.mkv",
        )
        self.assertEqual(suggestions["SingleSmallNormal"].get("single_video_query"), "Show")

    def test_ak6_shared_sample_rule_between_analyze_and_preview(self):
        """AK6: /api/inbox/analyze and /api/preview-process evaluate the same files as samples; movie-only rule stays in queue_api."""
        outbox_dir = os.path.join(self.temp_dir.name, "outbox")
        os.makedirs(outbox_dir, exist_ok=True)
        settings = self.persistence.load_settings()
        settings["outbox_dir"] = outbox_dir
        self.persistence.save_settings(settings)

        # Folder 1: 1 main video (>300MB) + 1 path-sample + 1 size-sample (<300MB)
        shared_dir = os.path.join(self.inbox_dir, "SharedSampleFolder")
        os.makedirs(os.path.join(shared_dir, "Sample"), exist_ok=True)
        with open(os.path.join(shared_dir, "Show.S01E01.mkv"), "wb") as f:
            f.truncate(350 * 1024 * 1024)
        with open(os.path.join(shared_dir, "Sample", "clip.mkv"), "wb") as f:
            f.truncate(40 * 1024 * 1024)
        with open(os.path.join(shared_dir, "teaser.mkv"), "wb") as f:
            f.truncate(30 * 1024 * 1024)

        # Folder 2: 2 large non-sample videos (>300MB)
        two_large_dir = os.path.join(self.inbox_dir, "TwoLargeFolder")
        os.makedirs(two_large_dir, exist_ok=True)
        with open(os.path.join(two_large_dir, "Part1.mkv"), "wb") as f:
            f.truncate(400 * 1024 * 1024)
        with open(os.path.join(two_large_dir, "Part2.mkv"), "wb") as f:
            f.truncate(350 * 1024 * 1024)

        # A. Analyze check: SharedSampleFolder is recognized as single-video; TwoLargeFolder is not
        res_analyze = self.client.get('/api/inbox/analyze')
        self.assertEqual(res_analyze.status_code, 200)
        suggestions = {s["project"]: s for s in res_analyze.get_json()["suggestions"]}

        self.assertEqual(
            suggestions["SharedSampleFolder"].get("single_video_relpath"),
            "SharedSampleFolder/Show.S01E01.mkv",
        )
        self.assertNotIn("single_video_relpath", suggestions["TwoLargeFolder"])

        # B. Preview check on SharedSampleFolder: both samples go to junk, main video to renames
        res_prev1 = self.client.post('/api/preview-process', json={
            "media_type": "movie",
            "project_name": "SharedSampleFolder",
            "movie_name": "Shared Movie (2024)",
            "copy_to_nas": False,
        })
        self.assertEqual(res_prev1.status_code, 200)
        prev1 = res_prev1.get_json()
        self.assertEqual([r["old"] for r in prev1.get("renames", [])], ["Show.S01E01.mkv"])
        self.assertIn("Sample/clip.mkv", prev1.get("junk", []))
        self.assertIn("teaser.mkv", prev1.get("junk", []))

        # C. Preview check on TwoLargeFolder: movie rule marks second large video as junk in movie preview
        res_prev2 = self.client.post('/api/preview-process', json={
            "media_type": "movie",
            "project_name": "TwoLargeFolder",
            "movie_name": "Two Large (2024)",
            "copy_to_nas": False,
        })
        self.assertEqual(res_prev2.status_code, 200)
        prev2 = res_prev2.get_json()
        self.assertEqual([r["old"] for r in prev2.get("renames", [])], ["Part1.mkv"])
        self.assertIn("Part2.mkv", prev2.get("junk", []))


if __name__ == "__main__":
    unittest.main()
