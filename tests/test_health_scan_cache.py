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

if __name__ == "__main__":
    unittest.main()
