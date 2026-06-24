import os
import unittest
import tempfile
import shutil
from unittest.mock import patch

import gui.core.persistence as persistence
import gui.core.trash as trash
import gui.workers.processor as processor
from gui.api.queue_api import handle_api_preview_process
from gui.main import app

class TestMovieProcessingFixes(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.settings_file = os.path.join(self.temp_dir.name, "settings.json")
        self.jobs_state_file = os.path.join(self.temp_dir.name, "jobs_state.json")
        self.env_file = os.path.join(self.temp_dir.name, ".env")

        # Set environment variables to isolate configurations
        os.environ["MW_SETTINGS_FILE"] = self.settings_file
        os.environ["MW_JOBS_STATE_FILE"] = self.jobs_state_file
        os.environ["MW_ENV_FILE"] = self.env_file
        os.environ["MW_DATA_DIR"] = self.temp_dir.name

        import sys
        utils_modules = set()
        import gui.core.utils as core_utils
        utils_modules.add(core_utils)

        for m in list(sys.modules.values()):
            if m is not None:
                if getattr(m, "__name__", None) == "gui.core.utils":
                    utils_modules.add(m)
                for attr_name in dir(m):
                    try:
                        attr = getattr(m, attr_name)
                        if getattr(attr, "__name__", None) == "gui.core.utils":
                            utils_modules.add(attr)
                    except Exception:
                        pass

        self.patched_utils = utils_modules
        self.orig_utils_paths = {}

        for u in self.patched_utils:
            self.orig_utils_paths[u] = {
                "DATA_DIR": getattr(u, "DATA_DIR", None),
                "PROFILES_DIR": getattr(u, "PROFILES_DIR", None),
                "HISTORY_FILE": getattr(u, "HISTORY_FILE", None)
            }
            u.DATA_DIR = self.temp_dir.name
            u.PROFILES_DIR = os.path.join(self.temp_dir.name, "profiles")
            u.HISTORY_FILE = os.path.join(self.temp_dir.name, "konv_history.json")

        os.makedirs(os.path.join(self.temp_dir.name, "profiles"), exist_ok=True)

        persistence._cached_settings = None
        persistence._cached_env = None

        self.inbox_dir = os.path.join(self.temp_dir.name, "inbox")
        self.outbox_dir = os.path.join(self.temp_dir.name, "outbox")
        self.nas_root = os.path.join(self.temp_dir.name, "nas")

        os.makedirs(self.inbox_dir, exist_ok=True)
        os.makedirs(self.outbox_dir, exist_ok=True)
        os.makedirs(self.nas_root, exist_ok=True)

        # Write clean settings
        self.settings = {
            "inbox_dir": self.inbox_dir,
            "outbox_dir": self.outbox_dir,
            "nas_root": self.nas_root,
            "media_server": "emby",
            "storage_targets": [
                {"id": "nas", "type": "nas", "root_path": self.nas_root, "enabled": True}
            ],
            "sync_categories": [
                {"id": "1", "name": "Filme", "nas_sub": "/Filme", "pcloud_remote": "pcloud:01_Filme"}
            ]
        }
        persistence.save_settings(self.settings)

        # Set up mock trash directory to verify deleted files
        self.mock_trash_dir = os.path.join(self.temp_dir.name, "mock_trash")
        os.makedirs(self.mock_trash_dir, exist_ok=True)

        # Mock trash.send_to_trash
        def mock_send_to_trash(filepath):
            if os.path.exists(filepath):
                dest = os.path.join(self.mock_trash_dir, os.path.basename(filepath))
                if os.path.exists(dest):
                    if os.path.isdir(dest):
                        shutil.rmtree(dest)
                    else:
                        os.remove(dest)
                shutil.move(filepath, dest)
            return True
        self.patcher_trash = patch("gui.core.trash.send_to_trash", side_effect=mock_send_to_trash)
        self.patcher_trash.start()

        # Mock ensure_nas_mounted
        self.patcher_nas = patch("gui.workers.processor.ensure_nas_mounted", return_value=True)
        self.patcher_nas.start()

        # Mock run_rsync_with_progress
        def mock_rsync(src, dst, task_id=None, move=False):
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                if os.path.isdir(dst):
                    shutil.copy(src, os.path.join(dst, os.path.basename(src)))
                else:
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy(src, dst)
            return True
        self.patcher_rsync = patch("gui.workers.processor.run_rsync_with_progress", side_effect=mock_rsync)
        self.patcher_rsync.start()

        # Flask Test Client setup
        app.config['TESTING'] = True
        self.client = app.test_client()

        # Bypass auth for Flask requests
        persistence.set_password("test-password")
        res = self.client.post("/api/auth/login", json={"password": "test-password"})
        self.assertEqual(res.status_code, 200)
        cookies = self.client.get_cookie("mw_csrf_token")
        self.csrf_token = cookies.value if cookies else None

    def tearDown(self):
        self.patcher_trash.stop()
        self.patcher_nas.stop()
        self.patcher_rsync.stop()

        for u, paths in self.orig_utils_paths.items():
            u.DATA_DIR = paths["DATA_DIR"]
            u.PROFILES_DIR = paths["PROFILES_DIR"]
            u.HISTORY_FILE = paths["HISTORY_FILE"]

        os.environ.pop("MW_SETTINGS_FILE", None)
        os.environ.pop("MW_JOBS_STATE_FILE", None)
        os.environ.pop("MW_ENV_FILE", None)
        os.environ.pop("MW_DATA_DIR", None)

        self.temp_dir.cleanup()

    def _post(self, url, json_data=None):
        headers = {}
        if self.csrf_token:
            headers["X-CSRF-Token"] = self.csrf_token
        return self.client.post(url, json=json_data, headers=headers)

    def test_sample_detection_in_preview(self):
        """Test 1: Filmprojekt mit Hauptfilm + Sample/sample.mkv sortiert Sample in Junk."""
        proj_dir = os.path.join(self.inbox_dir, "Dragonkeeper")
        os.makedirs(proj_dir)

        # Create main movie (400 MB)
        main_video = os.path.join(proj_dir, "dragonkeeper_main.mkv")
        with open(main_video, "wb") as f:
            f.truncate(400 * 1024 * 1024)

        # Create sample (20 MB)
        sample_video = os.path.join(proj_dir, "sample.mkv")
        with open(sample_video, "wb") as f:
            f.truncate(20 * 1024 * 1024)

        # Create main sub and sample sub
        main_sub = os.path.join(proj_dir, "dragonkeeper_main.srt")
        with open(main_sub, "w") as f:
            f.write("main subtitles")

        sample_sub = os.path.join(proj_dir, "sample.srt")
        with open(sample_sub, "w") as f:
            f.write("sample subtitles")

        params = {
            "media_type": "movie",
            "project_name": "Dragonkeeper",
            "movie_name": "Dragonkeeper (2024)",
            "destination_id": "1",
            "copy_to_nas": True
        }

        res = self._post("/api/preview-process", json_data=params)
        self.assertEqual(res.status_code, 200)

        data = res.get_json()
        self.assertIsNotNone(data)

        # Main video and sub should be mapped to the cleaned movie name
        renames = data.get("renames", [])
        subs = data.get("subs", [])
        junk = data.get("junk", [])

        rename_olds = [r["old"] for r in renames]
        sub_olds = [s["old"] for s in subs]

        self.assertIn("dragonkeeper_main.mkv", rename_olds)
        self.assertIn("dragonkeeper_main.srt", sub_olds)

        # Sample video and sample sub should be categorized as junk
        self.assertIn("sample.mkv", junk)
        self.assertIn("sample.srt", junk)

    def test_sample_by_name(self):
        """Test 2: Kleine Datei mit 'sample' im Namen landet ohne Hauptfilm als Junk in der Vorschau."""
        # Note: If there's another video file, the sample by name is sent to junk even if they are both small.
        proj_dir = os.path.join(self.inbox_dir, "SampleMovie")
        os.makedirs(proj_dir)

        # Create a small main movie (15 MB) without 'sample' in the name
        main_video = os.path.join(proj_dir, "movie.mkv")
        with open(main_video, "wb") as f:
            f.truncate(15 * 1024 * 1024)

        # Create a sample (10 MB) with 'sample' in the name
        sample_video = os.path.join(proj_dir, "some_sample.mkv")
        with open(sample_video, "wb") as f:
            f.truncate(10 * 1024 * 1024)

        params = {
            "media_type": "movie",
            "project_name": "SampleMovie",
            "movie_name": "Sample Movie",
            "destination_id": "1",
            "copy_to_nas": True
        }

        res = self._post("/api/preview-process", json_data=params)
        self.assertEqual(res.status_code, 200)

        data = res.get_json()
        self.assertIsNotNone(data)

        junk = data.get("junk", [])
        renames = [r["old"] for r in data.get("renames", [])]

        self.assertIn("some_sample.mkv", junk)
        self.assertIn("movie.mkv", renames)

    def test_single_movie_with_sample_in_title_is_not_junk(self):
        """Eine einzelne Hauptdatei mit 'sample' im Namen bleibt der Hauptfilm."""
        proj_dir = os.path.join(self.inbox_dir, "SampleTitleMovie")
        os.makedirs(proj_dir)

        video = os.path.join(proj_dir, "The Sample Movie.mkv")
        with open(video, "wb") as f:
            f.truncate(20 * 1024 * 1024)

        subtitle = os.path.join(proj_dir, "The Sample Movie.srt")
        with open(subtitle, "w") as f:
            f.write("subtitles")

        params = {
            "media_type": "movie",
            "project_name": "SampleTitleMovie",
            "movie_name": "The Sample Movie (2026)",
            "destination_id": "1",
            "copy_to_nas": True
        }

        res = self._post("/api/preview-process", json_data=params)
        self.assertEqual(res.status_code, 200)

        data = res.get_json()
        self.assertIsNotNone(data)

        renames = [r["old"] for r in data.get("renames", [])]
        subs = [s["old"] for s in data.get("subs", [])]
        junk = data.get("junk", [])

        self.assertIn("The Sample Movie.mkv", renames)
        self.assertIn("The Sample Movie.srt", subs)
        self.assertNotIn("The Sample Movie.mkv", junk)
        self.assertNotIn("The Sample Movie.srt", junk)

    def test_collision_protection_in_processor(self):
        """Test 3: Kollisionsschutz bricht ab, wenn Duplikate nicht in explicit_junk deklariert sind."""
        proj_dir = os.path.join(self.inbox_dir, "CollisionMovie")
        os.makedirs(proj_dir)

        # Create two files that might collide if named the same
        file1 = os.path.join(proj_dir, "file1.mkv")
        with open(file1, "wb") as f:
            f.truncate(400 * 1024 * 1024)

        file2 = os.path.join(proj_dir, "file2.mkv")
        with open(file2, "wb") as f:
            f.truncate(200 * 1024 * 1024)

        params = {
            "media_type": "movie",
            "project_name": "CollisionMovie",
            "movie_name": "Collision Movie (2026)",
            "destination_id": "1",
            "copy_to_nas": True,
            "explicit_renames": [
                {"old": "file1.mkv", "new": "Collision Movie (2026).mkv"},
                {"old": "file2.mkv", "new": "Collision Movie (2026).mkv"}
            ],
            "explicit_subs": [],
            "explicit_junk": [] # empty! should cause RuntimeError
        }

        # Calling processor.process_worker directly should raise RuntimeError
        with self.assertRaises(RuntimeError) as context:
            processor.process_worker(params)

        self.assertIn("Kollision im Namensschema erkannt", str(context.exception))

        # Now test with smaller file in explicit_junk: it should pass
        params["explicit_junk"] = ["file2.mkv"]
        # Clear outbox if any partial run occurred
        if os.path.exists(self.outbox_dir):
            shutil.rmtree(self.outbox_dir)
            os.makedirs(self.outbox_dir)

        # This should execute successfully
        processor.process_worker(params)

        # Check that the smaller file was sent to trash
        self.assertTrue(os.path.exists(os.path.join(self.mock_trash_dir, "file2.mkv")))
        # And the larger file was renamed and moved to outbox
        dest_movie_dir = os.path.join(self.outbox_dir, "Filme", "Collision Movie (2026)")
        self.assertTrue(os.path.exists(os.path.join(dest_movie_dir, "Collision Movie (2026).mkv")))

    def test_artwork_extension_protection(self):
        """Test 4: Keine Bildendungs-Mischung (z.B. .jpg nicht zu .png kopieren)."""
        proj_dir = os.path.join(self.inbox_dir, "ArtworkMovie")
        os.makedirs(proj_dir)

        # Create video file
        video = os.path.join(proj_dir, "movie.mkv")
        with open(video, "wb") as f:
            f.truncate(10 * 1024 * 1024)

        # Create poster as PNG
        poster = os.path.join(proj_dir, "poster.png")
        with open(poster, "w") as f:
            f.write("png data")

        # Create backdrop as JPG
        backdrop = os.path.join(proj_dir, "fanart.jpg")
        with open(backdrop, "w") as f:
            f.write("jpg data")

        params = {
            "media_type": "movie",
            "project_name": "ArtworkMovie",
            "movie_name": "Artwork Movie (2026)",
            "destination_id": "1",
            "copy_to_nas": True,
            "explicit_renames": [
                {"old": "movie.mkv", "new": "Artwork Movie (2026).mkv"}
            ],
            "explicit_subs": [],
            "explicit_junk": []
        }

        # Run process_worker
        processor.process_worker(params)

        # Output directory is outbox/Filme/Artwork Movie (2026)
        dest_movie_dir = os.path.join(self.outbox_dir, "Filme", "Artwork Movie (2026)")

        # Verify poster.png was copied / exists, but folder.png should not exist (deduplicated)
        self.assertTrue(os.path.exists(os.path.join(dest_movie_dir, "poster.png")))
        self.assertFalse(os.path.exists(os.path.join(dest_movie_dir, "folder.png")))

        # BUT poster.jpg or folder.jpg should NOT exist
        self.assertFalse(os.path.exists(os.path.join(dest_movie_dir, "poster.jpg")))
        self.assertFalse(os.path.exists(os.path.join(dest_movie_dir, "folder.jpg")))

        # Verify fanart.jpg exists
        self.assertTrue(os.path.exists(os.path.join(dest_movie_dir, "fanart.jpg")))
        # fanart.png should NOT exist
        self.assertFalse(os.path.exists(os.path.join(dest_movie_dir, "fanart.png")))

    def test_no_movie_title_artwork_duplicates(self):
        """Test 5: Keine Filmtitel-poster.jpg Duplikate werden erstellt."""
        proj_dir = os.path.join(self.inbox_dir, "DuplicateMovie")
        os.makedirs(proj_dir)

        # Create movie video file
        video = os.path.join(proj_dir, "movie.mkv")
        with open(video, "wb") as f:
            f.truncate(10 * 1024 * 1024)

        # Create title-specific poster file
        title_poster = os.path.join(proj_dir, "Artwork Movie (2026)-poster.jpg")
        with open(title_poster, "w") as f:
            f.write("poster data")

        # Create title-specific fanart file
        title_fanart = os.path.join(proj_dir, "Artwork Movie (2026)-fanart.jpg")
        with open(title_fanart, "w") as f:
            f.write("fanart data")

        params = {
            "media_type": "movie",
            "project_name": "DuplicateMovie",
            "movie_name": "Artwork Movie (2026)",
            "destination_id": "1",
            "copy_to_nas": True,
            "explicit_renames": [
                {"old": "movie.mkv", "new": "Artwork Movie (2026).mkv"}
            ],
            "explicit_subs": [],
            "explicit_junk": []
        }

        # Run process_worker
        processor.process_worker(params)

        # Output directory is outbox/Filme/Artwork Movie (2026)
        dest_movie_dir = os.path.join(self.outbox_dir, "Filme", "Artwork Movie (2026)")

        # Core compatibility poster files should be created
        self.assertTrue(os.path.exists(os.path.join(dest_movie_dir, "poster.jpg")))
        self.assertFalse(os.path.exists(os.path.join(dest_movie_dir, "folder.jpg")))
        self.assertTrue(os.path.exists(os.path.join(dest_movie_dir, "fanart.jpg")))

        # Title-specific files should be cleaned up / NOT exist in outbox
        self.assertFalse(os.path.exists(os.path.join(dest_movie_dir, "Artwork Movie (2026)-poster.jpg")))
        self.assertFalse(os.path.exists(os.path.join(dest_movie_dir, "Artwork Movie (2026)-fanart.jpg")))

    def test_artwork_source_jpg(self):
        """Test: Quelle liefert .jpg -> nur .jpg Core-Dateien entstehen."""
        proj_dir = os.path.join(self.inbox_dir, "JpgSourceMovie")
        os.makedirs(proj_dir)

        # Create movie video file
        video = os.path.join(proj_dir, "movie.mkv")
        with open(video, "wb") as f:
            f.truncate(10 * 1024 * 1024)

        # Create poster.jpg
        with open(os.path.join(proj_dir, "poster.jpg"), "w") as f:
            f.write("jpg poster")

        params = {
            "media_type": "movie",
            "project_name": "JpgSourceMovie",
            "movie_name": "Jpg Movie (2026)",
            "destination_id": "1",
            "copy_to_nas": True,
            "explicit_renames": [
                {"old": "movie.mkv", "new": "Jpg Movie (2026).mkv"}
            ],
            "explicit_subs": [],
            "explicit_junk": []
        }

        processor.process_worker(params)
        dest_movie_dir = os.path.join(self.outbox_dir, "Filme", "Jpg Movie (2026)")

        self.assertTrue(os.path.exists(os.path.join(dest_movie_dir, "poster.jpg")))
        self.assertFalse(os.path.exists(os.path.join(dest_movie_dir, "folder.jpg")))
        self.assertFalse(os.path.exists(os.path.join(dest_movie_dir, "poster.png")))
        self.assertFalse(os.path.exists(os.path.join(dest_movie_dir, "folder.png")))

    def test_artwork_source_png(self):
        """Test: Quelle liefert .png -> nur .png Core-Dateien entstehen."""
        proj_dir = os.path.join(self.inbox_dir, "PngSourceMovie")
        os.makedirs(proj_dir)

        # Create movie video file
        video = os.path.join(proj_dir, "movie.mkv")
        with open(video, "wb") as f:
            f.truncate(10 * 1024 * 1024)

        # Create poster.png
        with open(os.path.join(proj_dir, "poster.png"), "w") as f:
            f.write("png poster")

        params = {
            "media_type": "movie",
            "project_name": "PngSourceMovie",
            "movie_name": "Png Movie (2026)",
            "destination_id": "1",
            "copy_to_nas": True,
            "explicit_renames": [
                {"old": "movie.mkv", "new": "Png Movie (2026).mkv"}
            ],
            "explicit_subs": [],
            "explicit_junk": []
        }

        processor.process_worker(params)
        dest_movie_dir = os.path.join(self.outbox_dir, "Filme", "Png Movie (2026)")

        self.assertTrue(os.path.exists(os.path.join(dest_movie_dir, "poster.png")))
        self.assertFalse(os.path.exists(os.path.join(dest_movie_dir, "folder.png")))
        self.assertFalse(os.path.exists(os.path.join(dest_movie_dir, "poster.jpg")))
        self.assertFalse(os.path.exists(os.path.join(dest_movie_dir, "folder.jpg")))

    def test_artwork_reduction_of_parallel_extensions(self):
        """Test: Parallele .jpg/.png-Varianten werden auf eine Quelle reduziert (andere gelöscht)."""
        proj_dir = os.path.join(self.inbox_dir, "ReductionMovie")
        os.makedirs(proj_dir)

        # Create movie video file
        video = os.path.join(proj_dir, "movie.mkv")
        with open(video, "wb") as f:
            f.truncate(10 * 1024 * 1024)

        # Create poster.jpg AND poster.png
        with open(os.path.join(proj_dir, "poster.jpg"), "w") as f:
            f.write("jpg poster")
        with open(os.path.join(proj_dir, "poster.png"), "w") as f:
            f.write("png poster")

        # Create fanart.jpg AND fanart.png
        with open(os.path.join(proj_dir, "fanart.jpg"), "w") as f:
            f.write("jpg fanart")
        with open(os.path.join(proj_dir, "fanart.png"), "w") as f:
            f.write("png fanart")

        params = {
            "media_type": "movie",
            "project_name": "ReductionMovie",
            "movie_name": "Reduction Movie (2026)",
            "destination_id": "1",
            "copy_to_nas": True,
            "explicit_renames": [
                {"old": "movie.mkv", "new": "Reduction Movie (2026).mkv"}
            ],
            "explicit_subs": [],
            "explicit_junk": []
        }

        processor.process_worker(params)
        dest_movie_dir = os.path.join(self.outbox_dir, "Filme", "Reduction Movie (2026)")

        # Master poster.jpg is preferred in priority, so poster.png/folder.png should be deleted
        self.assertTrue(os.path.exists(os.path.join(dest_movie_dir, "poster.jpg")))
        self.assertFalse(os.path.exists(os.path.join(dest_movie_dir, "folder.jpg")))
        self.assertFalse(os.path.exists(os.path.join(dest_movie_dir, "poster.png")))
        self.assertFalse(os.path.exists(os.path.join(dest_movie_dir, "folder.png")))

        # Master fanart.jpg is preferred. fanart.png/backdrop.png/backdrop.jpg should be deleted/not exist
        self.assertTrue(os.path.exists(os.path.join(dest_movie_dir, "fanart.jpg")))
        self.assertFalse(os.path.exists(os.path.join(dest_movie_dir, "backdrop.jpg")))
        self.assertFalse(os.path.exists(os.path.join(dest_movie_dir, "fanart.png")))
        self.assertFalse(os.path.exists(os.path.join(dest_movie_dir, "backdrop.png")))

    def test_no_nas_cleanup_by_default(self):
        """Test: NAS-Ziel wird ohne explizite Cleanup-Option nicht gelöscht/bereinigt."""
        proj_dir = os.path.join(self.inbox_dir, "NasSafetyMovie")
        os.makedirs(proj_dir)

        # Create movie video file
        video = os.path.join(proj_dir, "movie.mkv")
        with open(video, "wb") as f:
            f.truncate(10 * 1024 * 1024)

        with open(os.path.join(proj_dir, "poster.jpg"), "w") as f:
            f.write("jpg poster")

        # Create a pre-existing unrelated file in the NAS destination directory
        nas_movie_dir = os.path.join(self.nas_root, "Filme", "NasSafety Movie (2026)")
        os.makedirs(nas_movie_dir, exist_ok=True)
        unrelated_file = os.path.join(nas_movie_dir, "old_legacy_file.txt")
        with open(unrelated_file, "w") as f:
            f.write("existing legacy data")

        params = {
            "media_type": "movie",
            "project_name": "NasSafetyMovie",
            "movie_name": "NasSafety Movie (2026)",
            "destination_id": "1",
            "copy_to_nas": True,
            "explicit_renames": [
                {"old": "movie.mkv", "new": "NasSafety Movie (2026).mkv"}
            ],
            "explicit_subs": [],
            "explicit_junk": []
        }

        processor.process_worker(params)

        # The new files are copied to NAS
        self.assertTrue(os.path.exists(os.path.join(nas_movie_dir, "NasSafety Movie (2026).mkv")))
        self.assertTrue(os.path.exists(os.path.join(nas_movie_dir, "poster.jpg")))

        # BUT the pre-existing unrelated file is NOT deleted / stays intact!
        self.assertTrue(os.path.exists(unrelated_file))

    def test_artwork_source_webp(self):
        """Test: Quelle liefert .webp -> nur .webp Core-Dateien entstehen."""
        proj_dir = os.path.join(self.inbox_dir, "WebpSourceMovie")
        os.makedirs(proj_dir)

        video = os.path.join(proj_dir, "movie.mkv")
        with open(video, "wb") as f:
            f.truncate(10 * 1024 * 1024)

        with open(os.path.join(proj_dir, "poster.webp"), "w") as f:
            f.write("webp poster")
        with open(os.path.join(proj_dir, "fanart.webp"), "w") as f:
            f.write("webp fanart")

        params = {
            "media_type": "movie",
            "project_name": "WebpSourceMovie",
            "movie_name": "Webp Movie (2026)",
            "destination_id": "1",
            "copy_to_nas": True,
            "explicit_renames": [
                {"old": "movie.mkv", "new": "Webp Movie (2026).mkv"}
            ],
            "explicit_subs": [],
            "explicit_junk": []
        }

        processor.process_worker(params)
        dest_movie_dir = os.path.join(self.outbox_dir, "Filme", "Webp Movie (2026)")

        self.assertTrue(os.path.exists(os.path.join(dest_movie_dir, "poster.webp")))
        self.assertFalse(os.path.exists(os.path.join(dest_movie_dir, "folder.webp")))
        self.assertTrue(os.path.exists(os.path.join(dest_movie_dir, "fanart.webp")))
        self.assertFalse(os.path.exists(os.path.join(dest_movie_dir, "backdrop.webp")))
        self.assertFalse(os.path.exists(os.path.join(dest_movie_dir, "poster.jpg")))
        self.assertFalse(os.path.exists(os.path.join(dest_movie_dir, "folder.jpg")))
        self.assertFalse(os.path.exists(os.path.join(dest_movie_dir, "fanart.jpg")))
        self.assertFalse(os.path.exists(os.path.join(dest_movie_dir, "backdrop.jpg")))

    def test_subtitle_suffix_parsing_and_pairing(self):
        """Test 7: VobSub Untertitel-Erkennung, Suffix-Parsing und Paarbindung."""
        proj_dir = os.path.join(self.inbox_dir, "SubtitleMovie")
        os.makedirs(proj_dir)

        # Hauptfilm
        video = os.path.join(proj_dir, "movie.mkv")
        with open(video, "wb") as f:
            f.truncate(10 * 1024 * 1024)

        # Untertitel-Paar (forced de) in verschachteltem Ordner
        nested_dir = os.path.join(proj_dir, "Funny Dude", "SUBS")
        os.makedirs(nested_dir)
        
        sub_file = os.path.join(nested_dir, "1080p-ger_forced.sub")
        idx_file = os.path.join(nested_dir, "1080p-ger_forced.idx")
        with open(sub_file, "w") as f: f.write("sub content")
        with open(idx_file, "w") as f: f.write("idx content")

        params = {
            "media_type": "movie",
            "project_name": "SubtitleMovie",
            "movie_name": "Cold Storage (2026)",
            "destination_id": "1",
            "copy_to_nas": True
        }

        # 1. Vorschau testen
        res = self._post("/api/preview-process", json_data=params)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        
        subs = data.get("subs", [])
        sub_olds = [s["old"] for s in subs]
        sub_news = [s["new"] for s in subs]
        
        # Prüfen, ob .sub und .idx als Untertitel erkannt wurden
        self.assertIn("Funny Dude/SUBS/1080p-ger_forced.sub", sub_olds)
        self.assertIn("Funny Dude/SUBS/1080p-ger_forced.idx", sub_olds)
        
        # Prüfen, ob sie den korrekten Namen (inkl. .de.forced) tragen
        self.assertIn("Cold Storage (2026).de.forced.sub", sub_news)
        self.assertIn("Cold Storage (2026).de.forced.idx", sub_news)

        # 2. Verarbeitung ausführen
        # Mappings und explizite Zuweisungen simulieren
        params["explicit_renames"] = [{"old": "movie.mkv", "new": "Cold Storage (2026).mkv"}]
        params["explicit_subs"] = subs
        params["explicit_junk"] = []
        
        processor.process_worker(params)
        
        dest_movie_dir = os.path.join(self.outbox_dir, "Filme", "Cold Storage (2026)")
        
        # Hauptfilm und umbenannte Untertitel auf oberster Ebene prüfen
        self.assertTrue(os.path.exists(os.path.join(dest_movie_dir, "Cold Storage (2026).mkv")))
        self.assertTrue(os.path.exists(os.path.join(dest_movie_dir, "Cold Storage (2026).de.forced.sub")))
        self.assertTrue(os.path.exists(os.path.join(dest_movie_dir, "Cold Storage (2026).de.forced.idx")))
        
        # Prüfen, dass der verschachtelte Quell-Ordner nicht aufs NAS gewandert ist
        self.assertFalse(os.path.exists(os.path.join(dest_movie_dir, "Funny Dude")))

    def test_recursive_safe_move_and_fallback(self):
        """Test 8: Rekursives Hochziehen, Quarantäne-Ausschluss, Auffangregel und Kollisionszähler."""
        proj_dir = os.path.join(self.inbox_dir, "SafeMoveMovie")
        os.makedirs(proj_dir)

        # Hauptfilm
        video = os.path.join(proj_dir, "movie.mkv")
        with open(video, "wb") as f:
            f.truncate(10 * 1024 * 1024)

        # Unbekannte Datei (z. B. RARBG.txt) im Hauptverzeichnis
        rarbg_file = os.path.join(proj_dir, "RARBG.txt")
        with open(rarbg_file, "w") as f: f.write("rarbg info")

        # Unbekannte Datei in verschachteltem Ordner (sollte hochgezogen werden)
        nested_dir = os.path.join(proj_dir, "nested_folder")
        os.makedirs(nested_dir)
        nested_unknown = os.path.join(nested_dir, "extra.txt")
        with open(nested_unknown, "w") as f: f.write("extra info")

        # Junk-Datei (sollte im Trash landen)
        junk_file = os.path.join(proj_dir, "junkfile.tmp")
        with open(junk_file, "w") as f: f.write("trash me")

        params = {
            "media_type": "movie",
            "project_name": "SafeMoveMovie",
            "movie_name": "Safe Move Movie (2026)",
            "destination_id": "1",
            "copy_to_nas": True,
            "explicit_renames": [
                {"old": "movie.mkv", "new": "Safe Move Movie (2026).mkv"}
            ],
            "explicit_subs": [],
            "explicit_junk": ["junkfile.tmp"]
        }

        processor.process_worker(params)
        dest_movie_dir = os.path.join(self.outbox_dir, "Filme", "Safe Move Movie (2026)")

        # 1. Prüfen, ob Junk-Datei gelöscht und NICHT im Ziel ist
        self.assertTrue(os.path.exists(os.path.join(self.mock_trash_dir, "junkfile.tmp")))
        self.assertFalse(os.path.exists(os.path.join(dest_movie_dir, "junkfile.tmp")))

        # 2. Prüfen, ob RARBG.txt nach der Auffangregel umbenannt wurde
        self.assertTrue(os.path.exists(os.path.join(dest_movie_dir, "Safe Move Movie (2026).txt")))

        # 3. Prüfen, ob nested_folder/extra.txt hochgezogen und kollisionsfrei umbenannt wurde (Safe Move Movie (2026).2.txt)
        self.assertTrue(os.path.exists(os.path.join(dest_movie_dir, "Safe Move Movie (2026).2.txt")))

        # 4. Prüfen, dass der verschachtelte Ordner nicht im Ziel ist und im Quellverzeichnis gelöscht wurde
        self.assertFalse(os.path.exists(os.path.join(dest_movie_dir, "nested_folder")))
        self.assertFalse(os.path.exists(os.path.join(proj_dir, "nested_folder")))

    def test_endswith_component_matching_and_vobsub_fallback_pairing(self):
        """Test 9: Prüft komponentenweises Pfadmatching sowie VobSub-Kopplung bei der Auffangregel."""
        proj_dir = os.path.join(self.inbox_dir, "FallbackPairingMovie")
        os.makedirs(proj_dir)

        # Hauptfilm
        video = os.path.join(proj_dir, "movie.mkv")
        with open(video, "wb") as f:
            f.truncate(5 * 1024 * 1024)

        # 1. Komponentenweiser Pfad-Matching-Test:
        # danger.sub soll ger.sub in der Whitelist NICHT matchen (da keine os.sep-Grenze)
        danger_sub = os.path.join(proj_dir, "danger.sub")
        with open(danger_sub, "w") as f: f.write("danger")

        # 2. VobSub-Kollisions-Kopplungstest (ohne Whitelist):
        # Paar A (a.sub, a.idx) und Paar B (b.sub, b.idx)
        os.makedirs(os.path.join(proj_dir, "PaarA"))
        with open(os.path.join(proj_dir, "PaarA", "a.sub"), "w") as f: f.write("subA")
        with open(os.path.join(proj_dir, "PaarA", "a.idx"), "w") as f: f.write("idxA")

        os.makedirs(os.path.join(proj_dir, "PaarB"))
        with open(os.path.join(proj_dir, "PaarB", "b.sub"), "w") as f: f.write("subB")
        with open(os.path.join(proj_dir, "PaarB", "b.idx"), "w") as f: f.write("idxB")

        params = {
            "media_type": "movie",
            "project_name": "FallbackPairingMovie",
            "movie_name": "Fallback Movie (2026)",
            "destination_id": "1",
            "copy_to_nas": True,
            "explicit_renames": [
                {"old": "movie.mkv", "new": "Fallback Movie (2026).mkv"}
            ],
            # Wir fügen eine Whitelist-Zuweisung für "ger.sub" hinzu.
            # "danger.sub" darf darauf nicht matchen!
            "explicit_subs": [
                {"old": "ger.sub", "new": "Fallback Movie (2026).de.forced.sub"}
            ],
            "explicit_junk": []
        }

        processor.process_worker(params)
        dest_movie_dir = os.path.join(self.outbox_dir, "Filme", "Fallback Movie (2026)")

        # danger.sub darf NICHT zu "Fallback Movie (2026).de.forced.sub" umbenannt worden sein!
        self.assertFalse(os.path.exists(os.path.join(dest_movie_dir, "Fallback Movie (2026).de.forced.sub")))

        # Nun prüfen wir, ob die Paare A und B sauber zusammengehalten wurden.
        dest_files = os.listdir(dest_movie_dir)
        sub_idx_bases = {}
        for f in dest_files:
            if f.endswith(('.sub', '.idx')):
                base, ext = os.path.splitext(f)
                if base not in sub_idx_bases:
                    sub_idx_bases[base] = set()
                sub_idx_bases[base].add(ext)

        # Für jedes gefundene Paar-Präfix müssen sowohl .sub als auch .idx vorhanden sein.
        # Einzeldateien ohne Partner (wie danger.sub) werden übersprungen.
        for base, exts in sub_idx_bases.items():
            if "Fallback Movie (2026).de.forced" in base or len(exts) == 1:
                continue
            self.assertEqual(exts, {'.sub', '.idx'})

    @patch("gui.workers.processor.copy_to_cloud_target", return_value=True)
    def test_closure_cloud_transfer_integration(self, mock_copy_to_cloud):
        """Integrationstest für den Closure-Fehler: copy_to_cloud_target muss im Transfer-Thread aufrufbar sein."""
        proj_dir = os.path.join(self.inbox_dir, "CloudMovie")
        os.makedirs(proj_dir)

        # Create movie video file
        video = os.path.join(proj_dir, "movie.mkv")
        with open(video, "wb") as f:
            f.truncate(5 * 1024 * 1024)

        # Configure settings to have a cloud target
        settings = self.settings.copy()
        settings["storage_targets"].append({
            "id": "pcloud",
            "type": "pcloud",
            "name": "pCloud Target",
            "enabled": True,
            "root_path": "/pcloud_mock"
        })
        persistence.save_settings(settings)

        params = {
            "media_type": "movie",
            "project_name": "CloudMovie",
            "movie_name": "Cloud Movie (2026)",
            "destination_id": "1",
            "copy_to_nas": False,
            "copy_to_pcloud": True, # Triggers cloud transfer
            "explicit_renames": [
                {"old": "movie.mkv", "new": "Cloud Movie (2026).mkv"}
            ],
            "explicit_subs": [],
            "explicit_junk": []
        }

        # Run process_worker
        # This will spin up the transfer_worker thread which calls copy_to_cloud_target.
        # If there's a closure bug, it raises cannot access free variable, which is caught
        # in transfer_errors and raised at the end.
        processor.process_worker(params)

        # Verify copy_to_cloud_target was called successfully
        mock_copy_to_cloud.assert_called_once()

    @patch("gui.workers.processor.copy_to_cloud_target", return_value=True)
    @patch("gui.workers.processor.mw_metadata.generate_tvshow_nfo")
    @patch("gui.workers.processor.mw_metadata.generate_episode_nfo")
    def test_closure_cloud_transfer_tv_integration(self, mock_gen_ep, mock_gen_tv, mock_copy_to_cloud):
        """Integrationstest für den Closure-Fehler im TV-Pfad."""
        proj_dir = os.path.join(self.inbox_dir, "CloudTVShow")
        os.makedirs(proj_dir)

        # Create tv episode file
        video = os.path.join(proj_dir, "episode1.mkv")
        with open(video, "wb") as f:
            f.truncate(5 * 1024 * 1024)

        # Configure settings to have a cloud target
        settings = self.settings.copy()
        settings["storage_targets"].append({
            "id": "pcloud",
            "type": "pcloud",
            "name": "pCloud Target",
            "enabled": True,
            "root_path": "/pcloud_mock"
        })
        persistence.save_settings(settings)

        params = {
            "media_type": "tv",
            "project_name": "CloudTVShow",
            "show_name": "Cloud TV Show",
            "show_id": "12345",
            "provider": "tmdb_tv",
            "season": "1",
            "episode": "1",
            "destination_id": "1",
            "copy_to_nas": False,
            "copy_to_pcloud": True, # Triggers cloud transfer
            "mappings": {"episode1.mkv": 1},
            "explicit_renames": [
                {"old": "episode1.mkv", "new": "Cloud TV Show - S01E01.mkv"}
            ],
            "explicit_subs": [],
            "explicit_junk": []
        }

        # Run process_worker
        # This will spin up the transfer_worker thread inside series processing block which calls copy_to_cloud_target.
        # If there's a closure bug, it raises cannot access free variable.
        processor.process_worker(params)

        # Verify copy_to_cloud_target was called successfully
        mock_copy_to_cloud.assert_called_once()

    @patch("gui.workers.processor.run_ffmpeg_with_progress", return_value=True)
    def test_movie_processing_with_convert(self, mock_run_ffmpeg):
        """Test: Film-Verarbeitung mit Konvertierungsoption convert=True und Mocks."""
        proj_dir = os.path.join(self.inbox_dir, "ConvertMovie")
        os.makedirs(proj_dir)

        # Create movie video file
        video = os.path.join(proj_dir, "movie_to_convert.mp4")
        with open(video, "wb") as f:
            f.truncate(10 * 1024 * 1024)

        params = {
            "media_type": "movie",
            "project_name": "ConvertMovie",
            "movie_name": "Converted Movie (2026)",
            "destination_id": "1",
            "copy_to_nas": True,
            "convert": True,
            "quality": 60,
            "delete_original": True,
            "explicit_renames": [
                {"old": "movie_to_convert.mp4", "new": "Converted Movie (2026).mp4"}
            ],
            "explicit_subs": [],
            "explicit_junk": []
        }

        # Mock run_ffmpeg_with_progress to actually write a dummy .mkv file so os.rename and checks pass
        def mock_ffmpeg(cmd, filepath, task_id=None, log_queue=None):
            # The output filename is the last element of the command
            temp_out = cmd[-1]
            with open(temp_out, "w") as f_out:
                f_out.write("converted video data")
            return True
        mock_run_ffmpeg.side_effect = mock_ffmpeg

        # Clear history to check added ratio
        import gui.core.utils as core_utils
        core_utils.save_konv_history([])

        # Run process_worker
        processor.process_worker(params)

        # Output folder check
        dest_movie_dir = os.path.join(self.outbox_dir, "Filme", "Converted Movie (2026)")
        self.assertTrue(os.path.exists(dest_movie_dir))
        
        # Converted .mkv file should exist
        self.assertTrue(os.path.exists(os.path.join(dest_movie_dir, "Converted Movie (2026).mkv")))
        # Original .mp4 file should NOT exist in outbox
        self.assertFalse(os.path.exists(os.path.join(dest_movie_dir, "Converted Movie (2026).mp4")))
        # Original file should be sent to trash (mock_trash_dir) since delete_original=True
        self.assertTrue(os.path.exists(os.path.join(self.mock_trash_dir, "Converted Movie (2026).mp4")))

        history = core_utils.load_konv_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["quality"], 60)
        self.assertEqual(history[0]["content_type"], "movie")
        self.assertEqual(history[0]["filename"], "Converted Movie (2026).mp4")

if __name__ == "__main__":
    unittest.main()
