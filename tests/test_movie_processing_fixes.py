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

        # Verify poster.png was copied to folder.png (since Emby copies poster to folder)
        self.assertTrue(os.path.exists(os.path.join(dest_movie_dir, "poster.png")))
        self.assertTrue(os.path.exists(os.path.join(dest_movie_dir, "folder.png")))

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
        self.assertTrue(os.path.exists(os.path.join(dest_movie_dir, "folder.jpg")))
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
        self.assertTrue(os.path.exists(os.path.join(dest_movie_dir, "folder.jpg")))
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
        self.assertTrue(os.path.exists(os.path.join(dest_movie_dir, "folder.png")))
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
        self.assertTrue(os.path.exists(os.path.join(dest_movie_dir, "folder.jpg")))
        self.assertFalse(os.path.exists(os.path.join(dest_movie_dir, "poster.png")))
        self.assertFalse(os.path.exists(os.path.join(dest_movie_dir, "folder.png")))

        # Master fanart.jpg is preferred, backdrop.jpg/fanart.jpg are created from it. fanart.png/backdrop.png should be deleted
        self.assertTrue(os.path.exists(os.path.join(dest_movie_dir, "fanart.jpg")))
        self.assertTrue(os.path.exists(os.path.join(dest_movie_dir, "backdrop.jpg")))
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

if __name__ == "__main__":
    unittest.main()
