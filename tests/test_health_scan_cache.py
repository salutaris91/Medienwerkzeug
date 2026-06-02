import sys
import os
import unittest
import unittest.mock
import json
import tempfile
import time
import shutil

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gui.core import health_cache
from gui.core import artwork_validators
from gui.core import health
from gui.core import utils

class TestHealthScanCache(unittest.TestCase):
    
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_path = os.path.join(self.temp_dir.name, "health_folder_cache.json")
        self.cache_mgr = health_cache.HealthCacheManager(cache_path=self.cache_path)
        self.validator = artwork_validators.get_validator("emby")
        
    def tearDown(self):
        self.temp_dir.cleanup()
        
    def test_get_cache_key(self):
        key = health_cache.get_cache_key("emby")
        self.assertEqual(key, f"{health_cache.SCAN_VERSION}:emby")
        
    def test_cache_load_save(self):
        key = "1:emby"
        self.assertEqual(self.cache_mgr._load_cache(), {})
        
        self.cache_mgr.set_cached_entry("/path/to/movie", key, [{"key": "health:1"}], {"some": "state"}, files_checked=3)
        
        # Vor dem flush() ist der Cache noch nicht auf der Festplatte
        self.assertEqual(self.cache_mgr._load_cache(), {})
        
        entry = self.cache_mgr.get_cached_entry("/path/to/movie", key)
        self.assertIsNotNone(entry)
        self.assertEqual(entry["cache_key"], key)
        self.assertEqual(entry["issues"], [{"key": "health:1"}])
        self.assertEqual(entry["state_data"], {"some": "state"})
        self.assertEqual(entry["files_checked"], 3)
        
        # Cache auf Festplatte schreiben
        self.cache_mgr.flush()
        
        # Jetzt muss es in der Datei sein
        loaded = self.cache_mgr._load_cache()
        self.assertIn(os.path.realpath("/path/to/movie"), loaded)
        
        # Ein neuer Manager lädt es korrekt von Platte
        new_mgr = health_cache.HealthCacheManager(cache_path=self.cache_path)
        entry2 = new_mgr.get_cached_entry("/path/to/movie", key)
        self.assertIsNotNone(entry2)
        self.assertEqual(entry2["cache_key"], key)
        
        self.assertIsNone(self.cache_mgr.get_cached_entry("/path/to/movie", "1:plex"))
        
    def test_calculate_hybrid_state_movie(self):
        movie_path = os.path.join(self.temp_dir.name, "Test Movie (2026)")
        os.makedirs(movie_path)
        
        video_file = os.path.join(movie_path, "Test Movie (2026).mkv")
        with open(video_file, "w") as f:
            f.write("dummy video data")
            
        nfo_file = os.path.join(movie_path, "Test Movie (2026).nfo")
        with open(nfo_file, "w") as f:
            f.write("<movie></movie>")
            
        poster_file = os.path.join(movie_path, "poster.jpg")
        with open(poster_file, "w") as f:
            f.write("poster data")
            
        now = time.time()
        os.utime(movie_path, (now - 100, now - 100))
        os.utime(video_file, (now - 90, now - 90))
        os.utime(nfo_file, (now - 80, now - 80))
        os.utime(poster_file, (now - 70, now - 70))
        
        state = self.cache_mgr.calculate_hybrid_state(movie_path, self.validator, is_movie=True)
        
        self.assertEqual(state["folder_mtime"], os.path.getmtime(movie_path))
        self.assertEqual(state["video_mtime"], os.path.getmtime(video_file))
        self.assertEqual(state["video_size"], os.path.getsize(video_file))
        self.assertEqual(state["nfo_mtime"], os.path.getmtime(nfo_file))
        self.assertEqual(state["poster_mtime"], os.path.getmtime(poster_file))
        
    def test_calculate_hybrid_state_movie_alternative_poster(self):
        movie_path = os.path.join(self.temp_dir.name, "Test Alternative Movie")
        os.makedirs(movie_path)
        
        video_file = os.path.join(movie_path, "Test Alternative.mkv")
        with open(video_file, "w") as f:
            f.write("dummy video data")
            
        # Alternative poster name fallback (e.g. folder.jpg)
        folder_jpg = os.path.join(movie_path, "folder.jpg")
        with open(folder_jpg, "w") as f:
            f.write("alternative poster data")
            
        state = self.cache_mgr.calculate_hybrid_state(movie_path, self.validator, is_movie=True)
        self.assertIn("poster_mtime", state)
        self.assertEqual(state["poster_mtime"], os.path.getmtime(folder_jpg))
        
    def test_calculate_hybrid_state_series(self):
        show_path = os.path.join(self.temp_dir.name, "Test Show")
        os.makedirs(show_path)
        
        nfo_file = os.path.join(show_path, "tvshow.nfo")
        with open(nfo_file, "w") as f:
            f.write("<tvshow></tvshow>")
            
        poster_file = os.path.join(show_path, "poster.jpg")
        with open(poster_file, "w") as f:
            f.write("poster data")
            
        season_path = os.path.join(show_path, "Staffel 01")
        os.makedirs(season_path)
        
        now = time.time()
        os.utime(show_path, (now - 100, now - 100))
        os.utime(nfo_file, (now - 90, now - 90))
        os.utime(poster_file, (now - 80, now - 80))
        os.utime(season_path, (now - 70, now - 70))
        
        state = self.cache_mgr.calculate_hybrid_state(show_path, self.validator, is_movie=False)
        
        self.assertEqual(state["folder_mtime"], os.path.getmtime(show_path))
        self.assertEqual(state["tvshow_nfo_mtime"], os.path.getmtime(nfo_file))
        self.assertEqual(state["series_poster_mtime"], os.path.getmtime(poster_file))
        self.assertIn("Staffel 01", state["season_dirs"])
        self.assertEqual(state["season_dirs"]["Staffel 01"], os.path.getmtime(season_path))
        
    def test_calculate_deep_hash(self):
        movie_path = os.path.join(self.temp_dir.name, "Test Deep Hash")
        os.makedirs(movie_path)
        
        f1 = os.path.join(movie_path, "file1.txt")
        with open(f1, "w") as f:
            f.write("content 1")
            
        hash1 = self.cache_mgr.calculate_deep_hash(movie_path)
        
        time.sleep(0.01)
        
        with open(f1, "w") as f:
            f.write("content 2")
            
        hash2 = self.cache_mgr.calculate_deep_hash(movie_path)
        self.assertNotEqual(hash1, hash2)
        
    @unittest.mock.patch("gui.core.health.ensure_nas_mounted")
    @unittest.mock.patch("gui.core.health.walk_nas_categories")
    @unittest.mock.patch("gui.core.utils.load_settings")
    @unittest.mock.patch("gui.core.health.SMALL_FILE_BYTES", new=0)
    def test_health_scan_caching_integration(self, mock_load_settings, mock_walk, mock_ensure_nas):
        mock_load_settings.return_value = {
            "media_server": "emby",
            "nas_root": self.temp_dir.name,
            "sync_categories": []
        }
        mock_ensure_nas.return_value = True
        
        show_path = os.path.join(self.temp_dir.name, "Test Show")
        os.makedirs(show_path)
        
        with open(os.path.join(show_path, "tvshow.nfo"), "w") as f:
            f.write("<tvshow><mw_provider>tmdb</mw_provider></tvshow>")
        with open(os.path.join(show_path, "poster.jpg"), "w") as f:
            f.write("poster")
        with open(os.path.join(show_path, "fanart.jpg"), "w") as f:
            f.write("fanart")
        with open(os.path.join(show_path, "logo.png"), "w") as f:
            f.write("logo")
        with open(os.path.join(show_path, "banner.jpg"), "w") as f:
            f.write("banner")
            
        season_path = os.path.join(show_path, "Staffel 01")
        os.makedirs(season_path)
        
        with open(os.path.join(show_path, "season01.jpg"), "w") as f:
            f.write("season poster")
            
        ep_dir = os.path.join(season_path, "Test Show S01E01")
        os.makedirs(ep_dir)
        with open(os.path.join(ep_dir, "Test Show S01E01.mkv"), "w") as f:
            f.write("video content" * 5000)
        with open(os.path.join(ep_dir, "Test Show S01E01.nfo"), "w") as f:
            f.write("<episode></episode>")
        
        mock_walk.return_value = [{
            "category": "Serien",
            "name": "Test Show",
            "path": show_path,
            "type": "series"
        }]
        
        with unittest.mock.patch("gui.core.health_cache.HealthCacheManager._load_cache") as mock_load, \
             unittest.mock.patch("gui.core.health_cache.HealthCacheManager._save_cache") as mock_save:
            
            cache_store = {}
            def load_side_effect():
                import copy
                return copy.deepcopy(cache_store)
            mock_load.side_effect = load_side_effect
            def save_side_effect(data):
                cache_store.clear()
                cache_store.update(data)
            mock_save.side_effect = save_side_effect
            
            health._scan_state["status"] = "idle"
            health._run_health_scan(deep_dive=False)
            
            self.assertEqual(health._scan_state["status"], "done")
            self.assertEqual(len(health._scan_state["issues"]), 0)
            self.assertIn(os.path.realpath(show_path), cache_store)
            
            with unittest.mock.patch("gui.core.health._check_series_show") as mock_check:
                health._scan_state["status"] = "idle"
                health._run_health_scan(deep_dive=False)
                
                mock_check.assert_not_called()
                self.assertEqual(health._scan_state["status"], "done")
                self.assertEqual(len(health._scan_state["issues"]), 0)
                
            time.sleep(0.01)
            now = time.time()
            os.utime(season_path, (now + 5, now + 5))
            
            with unittest.mock.patch("gui.core.health._check_series_show") as mock_check:
                mock_check.return_value = 1
                health._scan_state["status"] = "idle"
                health._run_health_scan(deep_dive=False)
                
                mock_check.assert_called_once()

    def test_separate_hybrid_and_deep_cache_states(self):
        key = "1:emby"
        show_path = "/path/to/show"
        
        # 1. Hybrid-State setzen
        hybrid_data = {"folder_mtime": 1000.0, "tvshow_nfo_mtime": 1001.0}
        self.cache_mgr.set_cached_entry(show_path, key, [], hybrid_state=hybrid_data, files_checked=5)
        
        entry = self.cache_mgr.get_cached_entry(show_path, key)
        self.assertEqual(entry["hybrid_state"], hybrid_data)
        self.assertIsNone(entry["deep_hash"])
        
        # 2. Deep-Hash setzen, Hybrid-State darf nicht verloren gehen!
        deep_hash = "abcdef1234567890"
        self.cache_mgr.set_cached_entry(show_path, key, [], deep_hash=deep_hash, files_checked=5)
        
        entry = self.cache_mgr.get_cached_entry(show_path, key)
        self.assertEqual(entry["hybrid_state"], hybrid_data)
        self.assertEqual(entry["deep_hash"], deep_hash)

    def test_health_scan_statistics(self):
        # Simuliere stats-Erhöhung bei _check_movie_cached
        stats = {
            "cache_hits": 0,
            "cache_miss_modified": 0,
            "cache_miss_known_issues": 0,
            "cache_miss_new": 0
        }
        
        movie_path = "/path/to/movie"
        key = "1:emby"
        
        mock_validator = unittest.mock.MagicMock()
        
        # Erstmaliger Aufruf -> cache_miss_new
        with unittest.mock.patch("gui.core.health._check_movie") as mock_check:
            mock_check.return_value = 1
            health._check_movie_cached([], "Filme", movie_path, mock_validator, self.cache_mgr, key, deep_dive=False, stats=stats)
            self.assertEqual(stats["cache_miss_new"], 1)
            self.assertEqual(stats["cache_hits"], 0)
            
        # Zweiter Aufruf ohne Änderungen -> cache_hits
        stats = {"cache_hits": 0, "cache_miss_modified": 0, "cache_miss_known_issues": 0, "cache_miss_new": 0}
        with unittest.mock.patch("gui.core.health._check_movie") as mock_check:
            with unittest.mock.patch.object(self.cache_mgr, "calculate_hybrid_state", return_value={"folder_mtime": 123}):
                self.cache_mgr.set_cached_entry(movie_path, key, [], hybrid_state={"folder_mtime": 123})
                health._check_movie_cached([], "Filme", movie_path, mock_validator, self.cache_mgr, key, deep_dive=False, stats=stats)
                self.assertEqual(stats["cache_hits"], 1)
                self.assertEqual(stats["cache_miss_modified"], 0)
                mock_check.assert_not_called()
                
        # Dritter Aufruf mit Änderungen -> cache_miss_modified
        stats = {"cache_hits": 0, "cache_miss_modified": 0, "cache_miss_known_issues": 0, "cache_miss_new": 0}
        with unittest.mock.patch("gui.core.health._check_movie") as mock_check:
            mock_check.return_value = 1
            with unittest.mock.patch.object(self.cache_mgr, "calculate_hybrid_state", return_value={"folder_mtime": 999}):
                health._check_movie_cached([], "Filme", movie_path, mock_validator, self.cache_mgr, key, deep_dive=False, stats=stats)
                self.assertEqual(stats["cache_miss_modified"], 1)
                self.assertEqual(stats["cache_hits"], 0)
                mock_check.assert_called_once()

    def test_health_scan_cancel(self):
        health._cancel_event.clear()
        health._scan_state["status"] = "running"
        
        stopped = health.stop_health_scan()
        self.assertTrue(stopped)
        self.assertTrue(health._cancel_event.is_set())
        self.assertEqual(health._scan_state["status"], "cancelled")
        
        stopped_again = health.stop_health_scan()
        self.assertFalse(stopped_again)

    @unittest.mock.patch("gui.core.health.ensure_nas_mounted")
    @unittest.mock.patch("gui.core.health.walk_nas_categories")
    @unittest.mock.patch("gui.core.utils.load_settings")
    def test_health_scan_cancel_thread(self, mock_load_settings, mock_walk, mock_ensure_nas):
        mock_load_settings.return_value = {
            "media_server": "emby",
            "nas_root": self.temp_dir.name,
            "sync_categories": []
        }
        mock_ensure_nas.return_value = True
        mock_walk.return_value = [{
            "category": "Serien",
            "name": "Test Show",
            "path": "/some/path",
            "type": "series"
        }]
        
        health._cancel_event.set()
        health._scan_state["status"] = "running"
        
        health._run_health_scan(deep_dive=False)
        
        self.assertEqual(health._scan_state["status"], "cancelled")
        self.assertIn("abgebrochen", health._scan_state["message"])

    def test_default_settings_show_console(self):
        # We need to temporarily delete settings.json to force default settings to load
        settings_path = "settings.json"
        backup_path = "settings.json.bak"
        has_settings = os.path.exists(settings_path)
        if has_settings:
            shutil.move(settings_path, backup_path)
        try:
            # Clear cached settings in utils module if any
            with utils.settings_lock:
                utils._cached_settings = None
            settings = utils.load_settings()
            self.assertIn("show_console", settings)
            self.assertFalse(settings["show_console"])
        finally:
            if has_settings:
                if os.path.exists(settings_path):
                    os.remove(settings_path)
                shutil.move(backup_path, settings_path)
            with utils.settings_lock:
                utils._cached_settings = None


class TestHealthScanApi(unittest.TestCase):
    def setUp(self):
        from flask import Flask
        from gui.api.nas_api import nas_api
        self.app = Flask(__name__)
        self.app.register_blueprint(nas_api, url_prefix="/api")
        self.client = self.app.test_client()

    @unittest.mock.patch("gui.api.nas_api.ensure_nas_mounted", return_value=True)
    @unittest.mock.patch("gui.core.utils.load_settings")
    def test_health_scan_no_media_server(self, mock_load_settings, mock_nas):
        # Wenn media_server ein leerer String ist
        mock_load_settings.return_value = {
            "media_server": ""
        }
        
        response = self.client.post("/api/nas/health-scan")
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertFalse(data["started"])
        self.assertIn("Medienserver", data["error"])

    @unittest.mock.patch("gui.core.health.start_health_scan")
    @unittest.mock.patch("gui.api.nas_api.ensure_nas_mounted", return_value=True)
    @unittest.mock.patch("gui.core.utils.load_settings")
    def test_health_scan_with_media_server(self, mock_load_settings, mock_nas, mock_start):
        # Wenn media_server gesetzt ist
        mock_load_settings.return_value = {
            "media_server": "emby"
        }
        mock_start.return_value = True
        
        response = self.client.post("/api/nas/health-scan", json={"deep": True})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["started"])
        mock_start.assert_called_once_with(deep_dive=True, category_ids=None)

    @unittest.mock.patch("gui.api.nas_api.os.rename")
    @unittest.mock.patch("gui.api.nas_api.os.path.isdir")
    @unittest.mock.patch("gui.api.nas_api.os.path.exists")
    @unittest.mock.patch("gui.api.nas_api.load_settings")
    def test_health_fix_sanitize_filename(self, mock_load_settings, mock_exists, mock_isdir, mock_rename):
        mock_load_settings.return_value = {
            "nas_root": "/Volumes/Kino"
        }
        mock_isdir.return_value = True
        mock_exists.return_value = False
        
        response = self.client.post("/api/nas/health-fix", json={
            "action": "rename_folder",
            "path": "/Volumes/Kino/My Show",
            "new_name": "My: Awesome? Show"
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["ok"])
        
        mock_rename.assert_called_once()
        args = mock_rename.call_args[0]
        self.assertEqual(args[0], "/Volumes/Kino/My Show")
        self.assertEqual(os.path.basename(args[1]), "My - Awesome Show")


class TestPipelineArtworkNaming(unittest.TestCase):
    def test_series_meta_files_resolution(self):
        from gui.workers import processor
        
        # Test for Emby
        settings = {"media_server": "emby"}
        meta_files = processor._get_series_meta_files(settings)
        self.assertIn("tvshow.nfo", meta_files)
        self.assertIn("poster.jpg", meta_files)
        self.assertIn("fanart.jpg", meta_files)
        
        # Test for Plex
        settings = {"media_server": "plex"}
        meta_files = processor._get_series_meta_files(settings)
        self.assertIn("tvshow.nfo", meta_files)
        self.assertIn("poster.jpg", meta_files)
        self.assertIn("fanart.jpg", meta_files)
        
        # Test for Jellyfin
        settings = {"media_server": "jellyfin"}
        meta_files = processor._get_series_meta_files(settings)
        self.assertIn("tvshow.nfo", meta_files)
        self.assertIn("folder.jpg", meta_files)
        self.assertIn("backdrop.jpg", meta_files)

    def test_movie_artwork_lists_resolution(self):
        from gui.workers import processor
        video_filename = "My Movie (2026).mkv"
        
        # Test for Plex
        settings = {"media_server": "plex"}
        posters, backdrops = processor._get_movie_artwork_lists(settings, video_filename)
        self.assertIn("poster.jpg", posters)
        self.assertIn("My Movie (2026)-poster.jpg", posters)
        self.assertIn("fanart.jpg", backdrops)
        self.assertIn("My Movie (2026)-fanart.jpg", backdrops)
        
        # Test for Jellyfin
        settings = {"media_server": "jellyfin"}
        posters, backdrops = processor._get_movie_artwork_lists(settings, video_filename)
        self.assertIn("folder.jpg", posters)
        self.assertIn("My Movie (2026)-poster.jpg", posters)
        self.assertIn("backdrop.jpg", backdrops)
        self.assertIn("My Movie (2026)-fanart.jpg", backdrops)


if __name__ == "__main__":
    unittest.main()
