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
        self.assertTrue(os.path.exists(os.path.join(outbox_s1_e1, "MyShow - S01E01 - Pilot.srt")))

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


if __name__ == "__main__":
    unittest.main()
