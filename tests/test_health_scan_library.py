import os
import time
import unittest
from unittest.mock import patch, MagicMock

from gui.core import health, utils

class TestHealthScanLibrary(unittest.TestCase):
    def setUp(self):
        # Scan-Zustand zurücksetzen
        health._scan_state = {
            "status": "idle",
            "progress": 0,
            "message": "Scan bereit.",
            "started_at": None,
            "finished_at": None,
            "issues": [],
            "summary": {"critical": 0, "warning": 0, "info": 0},
            "scanned": {"shows": 0, "files": 0},
            "stats": {"cache_hits": 0, "cache_miss_modified": 0, "cache_miss_known_issues": 0, "cache_miss_new": 0},
            "error": None,
        }

    @patch("gui.core.health.ensure_nas_mounted", return_value=True)
    @patch("gui.core.health.utils.load_settings")
    @patch("gui.core.health.walk_nas_categories")
    def test_scan_warning_when_no_folders_found(self, mock_walk, mock_load_settings, mock_mounted):
        mock_load_settings.return_value = {
            "nas_root": "/Volumes/Kino",
            "sync_categories": [{"id": "movies", "name": "Filme", "nas_sub": "Filme"}]
        }
        # Keine Medienordner gefunden (total = 0)
        mock_walk.return_value = []

        health._run_health_scan(deep_dive=False, category_ids=None)

        state = health.get_health_status()
        self.assertEqual(state["status"], "warning")
        self.assertEqual(state["error"], "no_library_folders_found")
        self.assertIn("Keine Bibliotheksordner gefunden", state["message"])

    @patch("gui.core.health.ensure_nas_mounted", return_value=True)
    @patch("gui.core.health.utils.load_settings")
    @patch("gui.core.health.walk_nas_categories")
    @patch("gui.core.health._check_movie_cached", return_value=10)
    @patch("gui.core.health.health_cache.HealthCacheManager")
    def test_scan_success_when_folders_found(self, mock_cache, mock_check_movie, mock_walk, mock_load_settings, mock_mounted):
        mock_load_settings.return_value = {
            "nas_root": "/Volumes/Kino",
            "sync_categories": [{"id": "movies", "name": "Filme", "nas_sub": "Filme"}]
        }
        # 1 Filmordner gefunden
        mock_walk.return_value = [{
            "category": "Filme",
            "category_id": "movies",
            "type": "movie",
            "name": "Inception",
            "path": "/Volumes/Kino/Filme/Inception"
        }]

        health._run_health_scan(deep_dive=False, category_ids=None)

        state = health.get_health_status()
        self.assertEqual(state["status"], "done")
        self.assertEqual(state["scanned"]["shows"], 1)
        self.assertEqual(state["scanned"]["files"], 10)
        self.assertIsNone(state["error"])

if __name__ == "__main__":
    unittest.main()
