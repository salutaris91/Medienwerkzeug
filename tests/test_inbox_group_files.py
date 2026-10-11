import os
import unittest
import tempfile
import json
import time
from unittest.mock import patch, MagicMock

import gui.core.helpers as helpers
import gui.core.persistence as persistence
import gui.workers.processor as processor
from gui.main import app


class TestInboxGroupFiles(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.inbox_dir = os.path.join(self.temp_dir.name, "inbox")
        self.outbox_dir = os.path.join(self.temp_dir.name, "outbox")
        self.nas_dir = os.path.join(self.temp_dir.name, "nas")
        os.makedirs(self.inbox_dir, exist_ok=True)
        os.makedirs(self.outbox_dir, exist_ok=True)
        os.makedirs(self.nas_dir, exist_ok=True)

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

        persistence.SETTINGS_FILE = self.settings_file
        persistence._cached_settings = None

        settings = persistence.load_settings()
        settings["inbox_dir"] = self.inbox_dir
        settings["outbox_dir"] = self.outbox_dir
        settings["nas_root"] = self.nas_dir
        for target in settings.get("storage_targets", []):
            if target.get("id") == "nas":
                target["root_path"] = self.nas_dir
        persistence.save_settings(settings)

        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key-12345'
        self.client = app.test_client()

    def tearDown(self):
        os.environ.pop("MW_SETTINGS_FILE", None)
        os.environ.pop("MW_JOBS_STATE_FILE", None)
        os.environ.pop("MW_ENV_FILE", None)
        os.environ.pop("MW_DATA_DIR", None)
        os.environ.pop("FLASK_SECRET_KEY", None)
        import gui.core.utils as utils
        utils._cached_settings = None
        persistence._cached_settings = None
        from gui.core.helpers import job_queue
        with job_queue.mutex:
            job_queue.queue.clear()
            job_queue.unfinished_tasks = 0
        self.temp_dir.cleanup()

    # =========================================================================
    # AK5: Validation & Helper Tests
    # =========================================================================
    def test_validate_group_files_success_and_deduplication(self):
        """AK5: Valid files are accepted and deduplicated case-insensitively."""
        f1 = os.path.join(self.inbox_dir, "Show.S01E01.mkv")
        f2 = os.path.join(self.inbox_dir, "Show.S01E02.mp4")
        with open(f1, "wb") as f: f.write(b"video1")
        with open(f2, "wb") as f: f.write(b"video2")

        res = helpers.validate_group_files(self.inbox_dir, ["Show.S01E01.mkv", "Show.S01E02.mp4", "show.s01e01.MKV"])
        self.assertEqual(res, ["Show.S01E01.mkv", "Show.S01E02.mp4"])

    def test_validate_group_files_rejections(self):
        """AK5: Rejects absolute paths, '..', non-existent, directories, non-video extensions, outside inbox."""
        f_valid = os.path.join(self.inbox_dir, "Valid.mkv")
        with open(f_valid, "wb") as f: f.write(b"video")

        sub_dir = os.path.join(self.inbox_dir, "SubDir")
        os.makedirs(sub_dir, exist_ok=True)

        txt_file = os.path.join(self.inbox_dir, "Info.txt")
        with open(txt_file, "wb") as f: f.write(b"text")

        # 1. Absolute path
        with self.assertRaises(ValueError) as ctx:
            helpers.validate_group_files(self.inbox_dir, [f_valid])
        self.assertIn("Absolute Pfade", str(ctx.exception))

        # 2. '..' traversal
        with self.assertRaises(ValueError) as ctx:
            helpers.validate_group_files(self.inbox_dir, ["../outside.mkv"])
        self.assertIn("Pfad-Traversal", str(ctx.exception))

        # 3. Non-existent file
        with self.assertRaises(ValueError) as ctx:
            helpers.validate_group_files(self.inbox_dir, ["Ghost.mkv"])
        self.assertIn("existiert nicht", str(ctx.exception))

        # 4. Directory name
        with self.assertRaises(ValueError) as ctx:
            helpers.validate_group_files(self.inbox_dir, ["SubDir"])
        self.assertIn("Ordner sind im files-Parameter nicht erlaubt", str(ctx.exception))

        # 5. Non-video extension
        with self.assertRaises(ValueError) as ctx:
            helpers.validate_group_files(self.inbox_dir, ["Info.txt"])
        self.assertIn("keine unterstützte Videodatei", str(ctx.exception))

        # 6. Empty list / invalid type
        with self.assertRaises(ValueError):
            helpers.validate_group_files(self.inbox_dir, [])
        with self.assertRaises(ValueError):
            helpers.validate_group_files(self.inbox_dir, "NotAList")

    def test_find_group_companion_files(self):
        """AK5 / ADR-65-2: Finds same-directory siblings starting with video stem, excluding videos."""
        v1 = os.path.join(self.inbox_dir, "Show.S01E01.mkv")
        s1 = os.path.join(self.inbox_dir, "Show.S01E01.de.srt")
        n1 = os.path.join(self.inbox_dir, "Show.S01E01.nfo")
        foreign = os.path.join(self.inbox_dir, "Foreign.txt")

        for p in [v1, s1, n1, foreign]:
            with open(p, "wb") as f: f.write(b"data")

        companions = helpers.find_group_companion_files(self.inbox_dir, ["Show.S01E01.mkv"])
        self.assertIn("Show.S01E01.de.srt", companions)
        self.assertIn("Show.S01E01.nfo", companions)
        self.assertNotIn("Show.S01E01.mkv", companions)
        self.assertNotIn("Foreign.txt", companions)

    def test_find_group_companion_files_stem_boundary_numeric_prefix(self):
        """F1: Group ['Folge 1.mkv'] with 'Folge 1.srt', 'Folge 10.mkv', 'Folge 10.srt' -> companions are exactly ['Folge 1.srt']."""
        f1_vid = os.path.join(self.inbox_dir, "Folge 1.mkv")
        f1_srt = os.path.join(self.inbox_dir, "Folge 1.srt")
        f10_vid = os.path.join(self.inbox_dir, "Folge 10.mkv")
        f10_srt = os.path.join(self.inbox_dir, "Folge 10.srt")

        for p in [f1_vid, f1_srt, f10_vid, f10_srt]:
            with open(p, "wb") as f: f.write(b"data")

        companions = helpers.find_group_companion_files(self.inbox_dir, ["Folge 1.mkv"])
        self.assertEqual(companions, ["Folge 1.srt"])

    def test_find_group_companion_files_sample_video_exclusion(self):
        """F1: 'Show.S01E01-sample.mkv' is not a companion of 'Show.S01E01.mkv', 'Show.S01E01.de.srt' is."""
        v1 = os.path.join(self.inbox_dir, "Show.S01E01.mkv")
        sample_vid = os.path.join(self.inbox_dir, "Show.S01E01-sample.mkv")
        sub = os.path.join(self.inbox_dir, "Show.S01E01.de.srt")

        for p in [v1, sample_vid, sub]:
            with open(p, "wb") as f: f.write(b"data")

        companions = helpers.find_group_companion_files(self.inbox_dir, ["Show.S01E01.mkv"])
        self.assertIn("Show.S01E01.de.srt", companions)
        self.assertNotIn("Show.S01E01-sample.mkv", companions)
        self.assertEqual(companions, ["Show.S01E01.de.srt"])

    def test_safe_move_recursive_allowed_files_same_name_in_subfolder_remains(self):
        """F2: safe_move_recursive with allowed_files leaves identically named file in a foreign subfolder untouched."""
        root_sub = os.path.join(self.inbox_dir, "Show.S01E01.de.srt")
        foreign_sub_dir = os.path.join(self.inbox_dir, "OtherShowFolder")
        os.makedirs(foreign_sub_dir, exist_ok=True)
        foreign_sub = os.path.join(foreign_sub_dir, "Show.S01E01.de.srt")

        dest_dir = os.path.join(self.outbox_dir, "TargetFolder")
        os.makedirs(dest_dir, exist_ok=True)

        with open(root_sub, "wb") as f: f.write(b"root_sub")
        with open(foreign_sub, "wb") as f: f.write(b"foreign_sub")

        # allowed_files only specifies the root file
        processor.safe_move_recursive(
            self.inbox_dir,
            dest_dir,
            prefix_filter=None,
            whitelist=[{"old": "Show.S01E01.de.srt", "new": "Show.S01E01.de.srt"}],
            allowed_files=["Show.S01E01.de.srt"],
            cleanup_empty_dirs=False
        )

        # Root file was moved to dest_dir
        self.assertFalse(os.path.exists(root_sub))
        self.assertTrue(os.path.exists(os.path.join(dest_dir, "Show.S01E01.de.srt")))
        with open(os.path.join(dest_dir, "Show.S01E01.de.srt"), "rb") as f:
            self.assertEqual(f.read(), b"root_sub")

        # Foreign subfolder file remains untouched in inbox
        self.assertTrue(os.path.exists(foreign_sub))
        with open(foreign_sub, "rb") as f:
            self.assertEqual(f.read(), b"foreign_sub")

    def test_preview_process_files_validation_endpoints(self):
        """AK5: /preview_process returns HTTP 400 on invalid files and mismatched mappings."""
        v1 = os.path.join(self.inbox_dir, "Ep01.mkv")
        with open(v1, "wb") as f: f.write(b"video")

        # 1. Invalid file in files list -> HTTP 400
        res = self.client.post('/api/preview-process', json={
            "media_type": "tv",
            "files": ["Ep01.mkv", "NonExistent.mkv"],
            "mappings": {"Ep01.mkv": 1}
        })
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("existiert nicht", data.get("error") or data.get("message"))

        # 2. Directory in files list -> HTTP 400
        sub_dir = os.path.join(self.inbox_dir, "FolderEntry")
        os.makedirs(sub_dir, exist_ok=True)
        res = self.client.post('/api/preview-process', json={
            "media_type": "tv",
            "files": ["FolderEntry"],
            "mappings": {"FolderEntry": 1}
        })
        self.assertEqual(res.status_code, 400)

        # 3. Mapping key not in files -> HTTP 400 (AK6(e))
        res = self.client.post('/api/preview-process', json={
            "media_type": "tv",
            "files": ["Ep01.mkv"],
            "mappings": {"Ep01.mkv": 1, "Unrelated.mkv": 2}
        })
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("Ungültiger Mapping-Schlüssel", data.get("error") or data.get("message"))

    def test_process_endpoint_files_validation(self):
        """AK5 / AK6(e): /process returns HTTP 400 on invalid files and mismatched mappings."""
        v1 = os.path.join(self.inbox_dir, "Ep01.mkv")
        with open(v1, "wb") as f: f.write(b"video")

        # 1. Directory in files -> HTTP 400
        sub_dir = os.path.join(self.inbox_dir, "FolderEntry2")
        os.makedirs(sub_dir, exist_ok=True)
        res = self.client.post('/api/process', json={
            "media_type": "tv",
            "files": ["FolderEntry2"],
            "mappings": {"FolderEntry2": 1}
        })
        self.assertEqual(res.status_code, 400)

        # 2. Mapping key not in files -> HTTP 400 (AK6(e))
        res = self.client.post('/api/process', json={
            "media_type": "tv",
            "files": ["Ep01.mkv"],
            "mappings": {"Ep01.mkv": 1, "ForeignEp.mkv": 2}
        })
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("Ungültiger Mapping-Schlüssel", data.get("error") or data.get("message"))

        # 3. Valid files and mappings -> HTTP 200
        res = self.client.post('/api/process', json={
            "media_type": "tv",
            "files": ["Ep01.mkv"],
            "mappings": {"Ep01.mkv": 1}
        })
        self.assertEqual(res.status_code, 200)

    # =========================================================================
    # AK6: Scope Enforcement in Processor Execution
    # =========================================================================
    def test_files_job_scope_enforcement_and_untouched_foreign_files(self):
        """
        AK6: Executes a files[] job with tmp-inbox:
        - Group: 3 episodes + 1 subtitle
        - Foreign project: video + subtitle + .nfo + empty folder
        - Adversarial collision file: foreign file starting with clean_title
        Verifies ONLY group and companions are touched; foreign files/folders and collision file remain.
        """
        # 1. Setup Group
        ep1 = os.path.join(self.inbox_dir, "Show.S01E01.mkv")
        ep2 = os.path.join(self.inbox_dir, "Show.S01E02.mkv")
        ep3 = os.path.join(self.inbox_dir, "Show.S01E03.mkv")
        sub1 = os.path.join(self.inbox_dir, "Show.S01E01.de.srt")

        with open(ep1, "wb") as f: f.write(b"ep1")
        with open(ep2, "wb") as f: f.write(b"ep2")
        with open(ep3, "wb") as f: f.write(b"ep3")
        with open(sub1, "wb") as f: f.write(b"sub1")

        # 2. Setup Foreign project
        foreign_vid = os.path.join(self.inbox_dir, "ForeignMovie.2023.mkv")
        foreign_sub = os.path.join(self.inbox_dir, "ForeignMovie.2023.de.srt")
        foreign_nfo = os.path.join(self.inbox_dir, "ForeignMovie.2023.nfo")
        foreign_empty_dir = os.path.join(self.inbox_dir, "ForeignEmptyDir")

        with open(foreign_vid, "wb") as f: f.write(b"foreignvid")
        with open(foreign_sub, "wb") as f: f.write(b"foreignsub")
        with open(foreign_nfo, "wb") as f: f.write(b"foreignnfo")
        os.makedirs(foreign_empty_dir, exist_ok=True)

        # 3. Setup Adversarial collision file (starts with clean_title of S01E01: "MyShow - S01E01 - Pilot")
        adversarial_file = os.path.join(self.inbox_dir, "MyShow - S01E01 - Pilot.adversarial.txt")
        with open(adversarial_file, "wb") as f: f.write(b"adversarial")

        # Execute process_worker with files param
        params = {
            "media_type": "tv",
            "show_name": "MyShow",
            "season": 1,
            "copy_to_nas": False,
            "copy_to_pcloud": False,
            "files": ["Show.S01E01.mkv", "Show.S01E02.mkv", "Show.S01E03.mkv"],
            "mappings": {
                "Show.S01E01.mkv": {"season": 1, "episode": 1, "title": "Pilot"},
                "Show.S01E02.mkv": {"season": 1, "episode": 2, "title": "Second"},
                "Show.S01E03.mkv": {"season": 1, "episode": 3, "title": "Third"},
            }
        }

        with patch("gui.workers.processor.ensure_nas_mounted", return_value=True), \
             patch("gui.mw_metadata.generate_tvshow_nfo", return_value={"nfo": True}), \
             patch("gui.mw_metadata.generate_episode_nfo", return_value={"nfo": True}):
            processor.process_worker(params)

        # Verifications:
        # A. Group files moved to Outbox
        outbox_show = os.path.join(self.outbox_dir, "Serien", "MyShow")
        outbox_s1_e1 = os.path.join(outbox_show, "Staffel 1", "MyShow - S01E01 - Pilot")
        self.assertTrue(os.path.exists(os.path.join(outbox_s1_e1, "MyShow - S01E01 - Pilot.mkv")))
        self.assertTrue(os.path.exists(os.path.join(outbox_s1_e1, "MyShow - S01E01 - Pilot.de.srt")))

        # B. Group files removed from Inbox
        self.assertFalse(os.path.exists(ep1))
        self.assertFalse(os.path.exists(ep2))
        self.assertFalse(os.path.exists(ep3))
        self.assertFalse(os.path.exists(sub1))

        # C. tvshow.nfo was NOT written to inbox_root
        self.assertFalse(os.path.exists(os.path.join(self.inbox_dir, "tvshow.nfo")))

        # D. Adversarial collision file remains untouched in Inbox
        self.assertTrue(os.path.exists(adversarial_file))

        # E. Foreign project files remain untouched in Inbox
        self.assertTrue(os.path.exists(foreign_vid))
        self.assertTrue(os.path.exists(foreign_sub))
        self.assertTrue(os.path.exists(foreign_nfo))

        # F. Foreign empty folder was NOT deleted/trashed
        self.assertTrue(os.path.exists(foreign_empty_dir))

    def test_explicit_junk_outside_scope_aborts_loudly(self):
        """AK6(d): explicit_junk/explicit_subs outside scope aborts loudly before moving anything."""
        ep1 = os.path.join(self.inbox_dir, "Show.S01E01.mkv")
        with open(ep1, "wb") as f: f.write(b"ep1")

        foreign = os.path.join(self.inbox_dir, "Foreign.mkv")
        with open(foreign, "wb") as f: f.write(b"foreign")

        params = {
            "media_type": "tv",
            "show_name": "MyShow",
            "season": 1,
            "copy_to_nas": False,
            "files": ["Show.S01E01.mkv"],
            "mappings": {"Show.S01E01.mkv": 1},
            "explicit_junk": ["Foreign.mkv"]  # Outside scope!
        }

        with self.assertRaises(RuntimeError) as ctx:
            processor.process_worker(params)
        self.assertIn("Sicherheitsabbruch", str(ctx.exception))
        # Verify no files were moved
        self.assertTrue(os.path.exists(ep1))
        self.assertTrue(os.path.exists(foreign))

    def test_key_contract_v1_exact_mapping_match(self):
        """AK6(f) / ADR-65-2: In files[] mode, mapping lookup requires exact key matching."""
        ep1 = os.path.join(self.inbox_dir, "SubFolder", "Show.S01E01.mkv")
        os.makedirs(os.path.dirname(ep1), exist_ok=True)
        with open(ep1, "wb") as f: f.write(b"ep1")

        # Preview with exact relative path in mappings
        res = self.client.post('/api/preview-process', json={
            "media_type": "tv",
            "files": ["SubFolder/Show.S01E01.mkv"],
            "mappings": {"SubFolder/Show.S01E01.mkv": {"season": 1, "episode": 5, "title": "Exact"}}
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(len(data["renames"]), 1)
        self.assertIn("S01E05", data["renames"][0]["new"])

    # =========================================================================
    # AK7: TOCTOU Failure
    # =========================================================================
    def test_toctou_missing_file_raises_with_filename(self):
        """AK7: A file deleted before execution raises RuntimeError naming the missing file."""
        ep1 = os.path.join(self.inbox_dir, "Show.S01E01.mkv")
        with open(ep1, "wb") as f: f.write(b"ep1")

        params = {
            "media_type": "tv",
            "show_name": "MyShow",
            "season": 1,
            "copy_to_nas": False,
            "files": ["Show.S01E01.mkv", "Show.S01E02.mkv"],  # E02 does not exist!
            "mappings": {
                "Show.S01E01.mkv": 1,
                "Show.S01E02.mkv": 2
            }
        }

        # validate_group_files will reject non-existent during validation,
        # but test TOCTOU specifically if file was present during preview and removed before process_worker:
        ep2 = os.path.join(self.inbox_dir, "Show.S01E02.mkv")
        with open(ep2, "wb") as f: f.write(b"ep2")

        # Remove ep2 right before worker execution
        os.remove(ep2)

        with self.assertRaises(RuntimeError) as ctx:
            processor.process_worker(params)
        self.assertIn("Show.S01E02.mkv", str(ctx.exception))
        self.assertIn("existiert nicht", str(ctx.exception))

    # =========================================================================
    # AK8: Backwards Compatibility
    # =========================================================================
    def test_backwards_compatibility_paths_without_files_param(self):
        """AK8: Jobs without files param behave exactly as before."""
        # 1. Folder project
        proj_dir = os.path.join(self.inbox_dir, "ClassicShow.S01")
        os.makedirs(proj_dir, exist_ok=True)
        vf = os.path.join(proj_dir, "ClassicShow.S01E01.mkv")
        with open(vf, "wb") as f: f.write(b"classic")

        params_folder = {
            "media_type": "tv",
            "project_name": "ClassicShow.S01",
            "show_name": "ClassicShow",
            "season": 1,
            "copy_to_nas": False,
            "mappings": {"ClassicShow.S01E01.mkv": 1}
        }

        with patch("gui.workers.processor.ensure_nas_mounted", return_value=True), \
             patch("gui.mw_metadata.generate_tvshow_nfo", return_value={"nfo": True}), \
             patch("gui.mw_metadata.generate_episode_nfo", return_value={"nfo": True}):
            processor.process_worker(params_folder)

        out_file = os.path.join(self.outbox_dir, "Serien", "ClassicShow", "Staffel 1", "ClassicShow - S01E01", "ClassicShow - S01E01.mkv")
        self.assertTrue(os.path.exists(out_file))

        # 2. Standalone file project
        single_vid = os.path.join(self.inbox_dir, "SingleMovie.2023.mkv")
        with open(single_vid, "wb") as f: f.write(b"movie")

        params_movie = {
            "media_type": "movie",
            "project_name": "SingleMovie.2023.mkv",
            "movie_name": "SingleMovie (2023)",
            "copy_to_nas": False
        }

        with patch("gui.workers.processor.ensure_nas_mounted", return_value=True), \
             patch("gui.mw_metadata.generate_movie_nfo", return_value={"nfo": True}):
            processor.process_worker(params_movie)

        out_movie = os.path.join(self.outbox_dir, "Filme", "SingleMovie (2023)", "SingleMovie (2023).mkv")
        self.assertTrue(os.path.exists(out_movie))

    # =========================================================================
    # Review Round 2 Fixes (R1, R2, R3, R4, D1/D3)
    # =========================================================================
    def test_r1_files_param_with_non_tv_media_type_rejected(self):
        """
        R1: /preview_process and /process reject files[] with media_type != 'tv' (HTTP 400);
        process_worker raises RuntimeError and leaves files untouched.
        """
        mov_file = os.path.join(self.inbox_dir, "MyMovie.mkv")
        with open(mov_file, "wb") as f: f.write(b"movie_data")

        # 1. /preview_process with movie -> 400
        res = self.client.post('/api/preview-process', json={
            "media_type": "movie",
            "files": ["MyMovie.mkv"],
            "movie_name": "MyMovie"
        })
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("files[]", data.get("error") or data.get("message"))

        # 2. /process with movie -> 400
        res = self.client.post('/api/process', json={
            "media_type": "movie",
            "files": ["MyMovie.mkv"],
            "movie_name": "MyMovie"
        })
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("files[]", data.get("error") or data.get("message"))

        # 3. process_worker with movie and files -> RuntimeError, no files moved
        with self.assertRaises(RuntimeError) as ctx:
            processor.process_worker({
                "media_type": "movie",
                "files": ["MyMovie.mkv"],
                "movie_name": "MyMovie"
            })
        self.assertIn("files[] wird nur für media_type 'tv' unterstützt", str(ctx.exception))
        self.assertTrue(os.path.exists(mov_file))

    def test_r2_explicit_junk_same_basename_in_other_folder_aborts_loudly(self):
        """
        R2: Scope check requires exact normalized relative path match against scope_files;
        having the same basename in another folder triggers a loud safety abort without touching files.
        """
        ep1 = os.path.join(self.inbox_dir, "Folge 1.mkv")
        sub1 = os.path.join(self.inbox_dir, "Folge 1.srt")
        with open(ep1, "wb") as f: f.write(b"ep1")
        with open(sub1, "wb") as f: f.write(b"sub1")

        foreign_dir = os.path.join(self.inbox_dir, "Fremdordner")
        os.makedirs(foreign_dir, exist_ok=True)
        foreign_sub = os.path.join(foreign_dir, "Folge 1.srt")
        with open(foreign_sub, "wb") as f: f.write(b"foreign_sub")

        params = {
            "media_type": "tv",
            "show_name": "MyShow",
            "season": 1,
            "copy_to_nas": False,
            "files": ["Folge 1.mkv"],
            "mappings": {"Folge 1.mkv": 1},
            "explicit_junk": ["Fremdordner/Folge 1.srt"]  # Outside scope despite matching basename!
        }

        with self.assertRaises(RuntimeError) as ctx:
            processor.process_worker(params)
        self.assertIn("Sicherheitsabbruch", str(ctx.exception))
        self.assertTrue(os.path.exists(ep1))
        self.assertTrue(os.path.exists(sub1))
        self.assertTrue(os.path.exists(foreign_sub))

    def test_r3_fallback_subtitle_rename_boundary_and_foreign_file_untouched(self):
        """
        R3: Group ['Folge 1.mkv'] without explicit_renames renames only companion subtitles
        respecting word/dot boundary; foreign 'Folge 10.srt' in inbox root remains untouched.
        """
        ep1 = os.path.join(self.inbox_dir, "Folge 1.mkv")
        sub1 = os.path.join(self.inbox_dir, "Folge 1.de.srt")
        foreign_sub = os.path.join(self.inbox_dir, "Folge 10.srt")
        foreign_vid = os.path.join(self.inbox_dir, "Folge 10.mkv")

        with open(ep1, "wb") as f: f.write(b"ep1")
        with open(sub1, "wb") as f: f.write(b"sub1")
        with open(foreign_sub, "wb") as f: f.write(b"foreign_sub")
        with open(foreign_vid, "wb") as f: f.write(b"foreign_vid")

        params = {
            "media_type": "tv",
            "show_name": "MyShow",
            "season": 1,
            "copy_to_nas": False,
            "files": ["Folge 1.mkv"],
            "mappings": {"Folge 1.mkv": 1}
            # explicit_renames is None!
        }

        with patch("gui.workers.processor.ensure_nas_mounted", return_value=True), \
             patch("gui.mw_metadata.generate_tvshow_nfo", return_value={"nfo": True}), \
             patch("gui.mw_metadata.generate_episode_nfo", return_value={"nfo": True}):
            processor.process_worker(params)

        # Companion subtitle was renamed and moved to outbox preserving language suffix
        out_sub = os.path.join(self.outbox_dir, "Serien", "MyShow", "Staffel 1", "MyShow - S01E01", "MyShow - S01E01.de.srt")
        self.assertTrue(os.path.exists(out_sub))

        # Foreign files in root remain completely untouched
        self.assertTrue(os.path.exists(foreign_sub))
        self.assertTrue(os.path.exists(foreign_vid))
        with open(foreign_sub, "rb") as f:
            self.assertEqual(f.read(), b"foreign_sub")

    def test_r4_subfolder_group_with_companion_file_moved_to_outbox(self):
        """
        R4: Group located in a subfolder with companion subtitle moves both video and subtitle to outbox.
        """
        sub_dir = os.path.join(self.inbox_dir, "Season 1")
        os.makedirs(sub_dir, exist_ok=True)
        ep1 = os.path.join(sub_dir, "Episode 01.mkv")
        sub1 = os.path.join(sub_dir, "Episode 01.de.srt")

        with open(ep1, "wb") as f: f.write(b"ep1")
        with open(sub1, "wb") as f: f.write(b"sub1")

        params = {
            "media_type": "tv",
            "show_name": "MyShow",
            "season": 1,
            "copy_to_nas": False,
            "files": ["Season 1/Episode 01.mkv"],
            "mappings": {"Season 1/Episode 01.mkv": {"season": 1, "episode": 1, "title": "SubTest"}}
        }

        with patch("gui.workers.processor.ensure_nas_mounted", return_value=True), \
             patch("gui.mw_metadata.generate_tvshow_nfo", return_value={"nfo": True}), \
             patch("gui.mw_metadata.generate_episode_nfo", return_value={"nfo": True}):
            processor.process_worker(params)

        out_ep = os.path.join(self.outbox_dir, "Serien", "MyShow", "Staffel 1", "MyShow - S01E01 - SubTest", "MyShow - S01E01 - SubTest.mkv")
        out_sub = os.path.join(self.outbox_dir, "Serien", "MyShow", "Staffel 1", "MyShow - S01E01 - SubTest", "MyShow - S01E01 - SubTest.de.srt")
        self.assertTrue(os.path.exists(out_ep))
        self.assertTrue(os.path.exists(out_sub))
        self.assertFalse(os.path.exists(ep1))
        self.assertFalse(os.path.exists(sub1))

    def test_d3_regression_tv_single_file_job_without_files_cleans_empty_dirs(self):
        """
        D3 / D1: Regression test for TV single file job WITHOUT files param (direct file in inbox root).
        Behaves exactly as pre-#65, including cleaning empty subdirectories in inbox.
        """
        ep = os.path.join(self.inbox_dir, "SingleShow.S01E01.mkv")
        with open(ep, "wb") as f: f.write(b"single_show")

        empty_subdir = os.path.join(self.inbox_dir, "LeftoverEmptyDir")
        os.makedirs(empty_subdir, exist_ok=True)

        params = {
            "media_type": "tv",
            "project_name": "SingleShow.S01E01.mkv",
            "show_name": "SingleShow",
            "season": 1,
            "copy_to_nas": False,
            "mappings": {"SingleShow.S01E01.mkv": 1}
        }

        with patch("gui.workers.processor.ensure_nas_mounted", return_value=True), \
             patch("gui.mw_metadata.generate_tvshow_nfo", return_value={"nfo": True}), \
             patch("gui.mw_metadata.generate_episode_nfo", return_value={"nfo": True}):
            processor.process_worker(params)

        out_ep = os.path.join(self.outbox_dir, "Serien", "SingleShow", "Staffel 1", "SingleShow - S01E01", "SingleShow - S01E01.mkv")
        self.assertTrue(os.path.exists(out_ep))
        # Empty directory was cleaned up as pre-#65 behavior
        self.assertFalse(os.path.exists(empty_subdir))

    def test_fallback_subtitle_rename_multiple_languages_preserved(self):
        """
        R3: Multiple subtitle files with different language tags (de, en, forced)
        are all preserved and moved to outbox without collision or silent overwriting.
        """
        ep1 = os.path.join(self.inbox_dir, "Folge 1.mkv")
        sub_de = os.path.join(self.inbox_dir, "Folge 1.de.srt")
        sub_en = os.path.join(self.inbox_dir, "Folge 1.en.srt")
        sub_forced = os.path.join(self.inbox_dir, "Folge 1.forced.de.srt")

        with open(ep1, "wb") as f: f.write(b"ep1")
        with open(sub_de, "wb") as f: f.write(b"sub_de")
        with open(sub_en, "wb") as f: f.write(b"sub_en")
        with open(sub_forced, "wb") as f: f.write(b"sub_forced")

        params = {
            "media_type": "tv",
            "show_name": "MyShow",
            "season": 1,
            "copy_to_nas": False,
            "files": ["Folge 1.mkv"],
            "mappings": {"Folge 1.mkv": 1}
        }

        with patch("gui.workers.processor.ensure_nas_mounted", return_value=True), \
             patch("gui.mw_metadata.generate_tvshow_nfo", return_value={"nfo": True}), \
             patch("gui.mw_metadata.generate_episode_nfo", return_value={"nfo": True}):
            processor.process_worker(params)

        out_dir = os.path.join(self.outbox_dir, "Serien", "MyShow", "Staffel 1", "MyShow - S01E01")
        self.assertTrue(os.path.exists(os.path.join(out_dir, "MyShow - S01E01.mkv")))
        self.assertTrue(os.path.exists(os.path.join(out_dir, "MyShow - S01E01.de.srt")))
        self.assertTrue(os.path.exists(os.path.join(out_dir, "MyShow - S01E01.en.srt")))
        self.assertTrue(os.path.exists(os.path.join(out_dir, "MyShow - S01E01.forced.de.srt")))

        # Inbox has all companion subtitles removed
        self.assertFalse(os.path.exists(sub_de))
        self.assertFalse(os.path.exists(sub_en))
        self.assertFalse(os.path.exists(sub_forced))

    def test_explicit_subs_and_renames_outside_scope_aborts_loudly(self):
        """
        R2: Scope checks for explicit_subs and explicit_renames abort loudly when referencing foreign files.
        """
        ep1 = os.path.join(self.inbox_dir, "Folge 1.mkv")
        with open(ep1, "wb") as f: f.write(b"ep1")

        # 1. explicit_subs with out-of-scope file
        params_subs = {
            "media_type": "tv",
            "show_name": "MyShow",
            "season": 1,
            "copy_to_nas": False,
            "files": ["Folge 1.mkv"],
            "mappings": {"Folge 1.mkv": 1},
            "explicit_subs": [{"old": "ForeignSub.srt", "new": "MyShow - S01E01.srt"}]
        }
        with self.assertRaises(RuntimeError) as ctx:
            processor.process_worker(params_subs)
        self.assertIn("Sicherheitsabbruch", str(ctx.exception))

        # 2. explicit_renames with out-of-scope file
        params_renames = {
            "media_type": "tv",
            "show_name": "MyShow",
            "season": 1,
            "copy_to_nas": False,
            "files": ["Folge 1.mkv"],
            "mappings": {"Folge 1.mkv": 1},
            "explicit_renames": [{"old": "ForeignEp.mkv", "new": "MyShow - S01E01.mkv"}]
        }
        with self.assertRaises(RuntimeError) as ctx:
            processor.process_worker(params_renames)
        self.assertIn("Sicherheitsabbruch", str(ctx.exception))

    # =========================================================================
    # N1, N2, N3: Target collision and destination boundary security tests
    # =========================================================================
    def test_n1_fallback_video_target_collision_with_foreign_file_aborts_loudly(self):
        """
        N1: Fallback video rename (explicit_renames=None) detects existing foreign file
        with the exact target name in inbox root and aborts with RuntimeError without overwriting it.
        """
        ep1 = os.path.join(self.inbox_dir, "Show.S01E01.mkv")
        with open(ep1, "wb") as f:
            f.write(b"ep1_original_content")

        foreign_target = os.path.join(self.inbox_dir, "MyShow - S01E01 - Pilot.mkv")
        with open(foreign_target, "wb") as f:
            f.write(b"foreign_target_do_not_overwrite")

        params = {
            "media_type": "tv",
            "show_name": "MyShow",
            "season": 1,
            "copy_to_nas": False,
            "files": ["Show.S01E01.mkv"],
            "mappings": {"Show.S01E01.mkv": {"season": 1, "episode": 1, "title": "Pilot"}}
            # explicit_renames is None
        }

        with patch("gui.workers.processor.ensure_nas_mounted", return_value=True), \
             patch("gui.mw_metadata.generate_tvshow_nfo", return_value={"nfo": True}), \
             patch("gui.mw_metadata.generate_episode_nfo", return_value={"nfo": True}):
            with self.assertRaises(RuntimeError) as ctx:
                processor.process_worker(params)

        self.assertIn("Kollision", str(ctx.exception))
        self.assertIn("MyShow - S01E01 - Pilot.mkv", str(ctx.exception))

        # Foreign file must remain completely untouched with its original content
        self.assertTrue(os.path.exists(foreign_target))
        with open(foreign_target, "rb") as f:
            self.assertEqual(f.read(), b"foreign_target_do_not_overwrite")
        # Original file also remains
        self.assertTrue(os.path.exists(ep1))

    def test_n1_nfo_target_collision_with_foreign_file_aborts_loudly(self):
        """
        N1: Episode NFO generation in files-job detects existing foreign .nfo in inbox root
        and aborts with RuntimeError without overwriting it.
        """
        ep1 = os.path.join(self.inbox_dir, "Show.S01E01.mkv")
        with open(ep1, "wb") as f:
            f.write(b"ep1_original_content")

        foreign_nfo = os.path.join(self.inbox_dir, "MyShow - S01E01 - Pilot.nfo")
        with open(foreign_nfo, "wb") as f:
            f.write(b"foreign_nfo_content_do_not_touch")

        params = {
            "media_type": "tv",
            "show_name": "MyShow",
            "season": 1,
            "provider": "tvdb",
            "show_id": "12345",
            "copy_to_nas": False,
            "files": ["Show.S01E01.mkv"],
            "mappings": {"Show.S01E01.mkv": {"season": 1, "episode": 1, "title": "Pilot"}}
        }

        with patch("gui.workers.processor.ensure_nas_mounted", return_value=True), \
             patch("gui.mw_metadata.generate_tvshow_nfo", return_value={"nfo": True}):
            with self.assertRaises(RuntimeError) as ctx:
                processor.process_worker(params)

        self.assertIn("Kollision", str(ctx.exception))
        self.assertIn("MyShow - S01E01 - Pilot.nfo", str(ctx.exception))

        # Foreign NFO must remain completely untouched
        self.assertTrue(os.path.exists(foreign_nfo))
        with open(foreign_nfo, "rb") as f:
            self.assertEqual(f.read(), b"foreign_nfo_content_do_not_touch")

    def test_n2_explicit_renames_destination_validation_and_collisions(self):
        """
        N2: explicit_renames target 'new' is validated:
        (a) absolute path rejected, (b) '..' traversal rejected, (c) existing foreign target causes loud abort before move.
        """
        ep1 = os.path.join(self.inbox_dir, "Show.S01E01.mkv")
        with open(ep1, "wb") as f:
            f.write(b"ep1_content")

        foreign_dir = os.path.join(self.inbox_dir, "Fremdordner")
        os.makedirs(foreign_dir, exist_ok=True)
        foreign_file = os.path.join(foreign_dir, "Target.mkv")
        with open(foreign_file, "wb") as f:
            f.write(b"foreign_target_content")

        # 1. 'new' is an absolute path
        params_abs = {
            "media_type": "tv",
            "show_name": "MyShow",
            "season": 1,
            "copy_to_nas": False,
            "files": ["Show.S01E01.mkv"],
            "mappings": {"Show.S01E01.mkv": 1},
            "explicit_renames": [{"old": "Show.S01E01.mkv", "new": "/tmp/evil/Absolute.mkv"}]
        }
        with self.assertRaises(RuntimeError) as ctx:
            processor.process_worker(params_abs)
        self.assertIn("Sicherheitsabbruch", str(ctx.exception))
        self.assertIn("absoluter Pfad", str(ctx.exception))
        self.assertTrue(os.path.exists(ep1))

        # 2. 'new' contains '..' traversal
        params_traversal = {
            "media_type": "tv",
            "show_name": "MyShow",
            "season": 1,
            "copy_to_nas": False,
            "files": ["Show.S01E01.mkv"],
            "mappings": {"Show.S01E01.mkv": 1},
            "explicit_renames": [{"old": "Show.S01E01.mkv", "new": "../outside.mkv"}]
        }
        with self.assertRaises(RuntimeError) as ctx:
            processor.process_worker(params_traversal)
        self.assertIn("Sicherheitsabbruch", str(ctx.exception))
        self.assertTrue(os.path.exists(ep1))

        # 3. 'new' points to an existing foreign file -> collision abort before any move
        params_collision = {
            "media_type": "tv",
            "show_name": "MyShow",
            "season": 1,
            "copy_to_nas": False,
            "files": ["Show.S01E01.mkv"],
            "mappings": {"Show.S01E01.mkv": 1},
            "explicit_renames": [{"old": "Show.S01E01.mkv", "new": "Fremdordner/Target.mkv"}]
        }
        with self.assertRaises(RuntimeError) as ctx:
            processor.process_worker(params_collision)
        self.assertIn("Kollision", str(ctx.exception))
        self.assertIn("Fremdordner/Target.mkv", str(ctx.exception))

        # Foreign file and source file must remain untouched
        self.assertTrue(os.path.exists(foreign_file))
        with open(foreign_file, "rb") as f:
            self.assertEqual(f.read(), b"foreign_target_content")
        self.assertTrue(os.path.exists(ep1))

    def test_n2_explicit_subs_destination_validation_and_collisions(self):
        """
        N2: explicit_subs target 'new' is validated:
        (a) absolute path rejected, (b) '..' traversal rejected, (c) existing foreign target causes loud abort.
        """
        ep1 = os.path.join(self.inbox_dir, "Show.S01E01.mkv")
        sub1 = os.path.join(self.inbox_dir, "Show.S01E01.srt")
        with open(ep1, "wb") as f:
            f.write(b"ep1_content")
        with open(sub1, "wb") as f:
            f.write(b"sub1_content")

        foreign_sub = os.path.join(self.inbox_dir, "ExistingSub.srt")
        with open(foreign_sub, "wb") as f:
            f.write(b"foreign_sub_content")

        # 1. 'new' is an absolute path
        params_abs = {
            "media_type": "tv",
            "show_name": "MyShow",
            "season": 1,
            "copy_to_nas": False,
            "files": ["Show.S01E01.mkv"],
            "mappings": {"Show.S01E01.mkv": 1},
            "explicit_subs": [{"old": "Show.S01E01.srt", "new": "/tmp/evil/Absolute.srt"}]
        }
        with self.assertRaises(RuntimeError) as ctx:
            processor.process_worker(params_abs)
        self.assertIn("Sicherheitsabbruch", str(ctx.exception))
        self.assertIn("absoluter Pfad", str(ctx.exception))

        # 2. 'new' contains '..' traversal
        params_traversal = {
            "media_type": "tv",
            "show_name": "MyShow",
            "season": 1,
            "copy_to_nas": False,
            "files": ["Show.S01E01.mkv"],
            "mappings": {"Show.S01E01.mkv": 1},
            "explicit_subs": [{"old": "Show.S01E01.srt", "new": "../outside.srt"}]
        }
        with self.assertRaises(RuntimeError) as ctx:
            processor.process_worker(params_traversal)
        self.assertIn("Sicherheitsabbruch", str(ctx.exception))

        # 3. 'new' points to an existing foreign subtitle file
        params_collision = {
            "media_type": "tv",
            "show_name": "MyShow",
            "season": 1,
            "copy_to_nas": False,
            "files": ["Show.S01E01.mkv"],
            "mappings": {"Show.S01E01.mkv": 1},
            "explicit_subs": [{"old": "Show.S01E01.srt", "new": "ExistingSub.srt"}]
        }
        with self.assertRaises(RuntimeError) as ctx:
            processor.process_worker(params_collision)
        self.assertIn("Kollision", str(ctx.exception))
        self.assertIn("ExistingSub.srt", str(ctx.exception))

        # Foreign sub remains untouched
        self.assertTrue(os.path.exists(foreign_sub))
        with open(foreign_sub, "rb") as f:
            self.assertEqual(f.read(), b"foreign_sub_content")

    def test_n3_convert_temp_target_collision_aborts_loudly(self):
        """
        N3: convert=True with files-job checks that temp target ('{clean_title}_neu.mkv')
        does not collide with an existing foreign file in inbox root.
        """
        ep1 = os.path.join(self.inbox_dir, "Show.S01E01.mp4")
        with open(ep1, "wb") as f:
            f.write(b"mp4_video_content")

        foreign_temp = os.path.join(self.inbox_dir, "MyShow - S01E01 - Pilot_neu.mkv")
        with open(foreign_temp, "wb") as f:
            f.write(b"foreign_temp_content")

        params = {
            "media_type": "tv",
            "show_name": "MyShow",
            "season": 1,
            "convert": True,
            "copy_to_nas": False,
            "files": ["Show.S01E01.mp4"],
            "mappings": {"Show.S01E01.mp4": {"season": 1, "episode": 1, "title": "Pilot"}}
        }

        with patch("gui.workers.processor.ensure_nas_mounted", return_value=True), \
             patch("gui.mw_metadata.generate_tvshow_nfo", return_value={"nfo": True}), \
             patch("gui.mw_metadata.generate_episode_nfo", return_value={"nfo": True}):
            with self.assertRaises(RuntimeError) as ctx:
                processor.process_worker(params)

        self.assertIn("Kollision bei Konvertierung: Temp-Ziel", str(ctx.exception))
        self.assertTrue(os.path.exists(foreign_temp))
        with open(foreign_temp, "rb") as f:
            self.assertEqual(f.read(), b"foreign_temp_content")

    def test_n3_convert_final_target_collision_aborts_loudly(self):
        """
        N3: convert=True with files-job checks that final target ('{clean_title}.mkv')
        does not collide with an existing foreign file in inbox root when converting non-mkv (.mp4).
        """
        ep1 = os.path.join(self.inbox_dir, "Show.S01E01.mp4")
        with open(ep1, "wb") as f:
            f.write(b"mp4_video_content")

        foreign_final = os.path.join(self.inbox_dir, "MyShow - S01E01 - Pilot.mkv")
        with open(foreign_final, "wb") as f:
            f.write(b"foreign_final_content")

        params = {
            "media_type": "tv",
            "show_name": "MyShow",
            "season": 1,
            "convert": True,
            "copy_to_nas": False,
            "files": ["Show.S01E01.mp4"],
            "mappings": {"Show.S01E01.mp4": {"season": 1, "episode": 1, "title": "Pilot"}}
        }

        with patch("gui.workers.processor.ensure_nas_mounted", return_value=True), \
             patch("gui.mw_metadata.generate_tvshow_nfo", return_value={"nfo": True}), \
             patch("gui.mw_metadata.generate_episode_nfo", return_value={"nfo": True}):
            with self.assertRaises(RuntimeError) as ctx:
                processor.process_worker(params)

        self.assertIn("Kollision bei Konvertierung: Ziel", str(ctx.exception))
        self.assertTrue(os.path.exists(foreign_final))
        with open(foreign_final, "rb") as f:
            self.assertEqual(f.read(), b"foreign_final_content")


if __name__ == "__main__":
    unittest.main()
