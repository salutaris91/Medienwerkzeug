import os
import time
import unittest
from unittest.mock import patch, MagicMock
from flask import Flask

from gui.core import health, utils, duplicates, transfers
from gui.api.nas_api import nas_api

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
        duplicates._scan_state = {
            "status": "idle",
            "progress": 0,
            "message": "Bereit.",
            "started_at": None,
            "finished_at": None,
            "groups": [],
            "stats": {"shows": 0, "files": 0, "duplicates": 0, "reclaimable_bytes": 0},
            "error": None,
        }

        from gui.api.system_api import system_api
        self.app = Flask(__name__)
        self.app.register_blueprint(nas_api, url_prefix="/api")
        self.app.register_blueprint(system_api, url_prefix="/api")
        self.client = self.app.test_client()

    @patch("gui.core.health.ensure_nas_mounted", return_value=True)
    @patch("gui.core.health.utils.load_settings")
    @patch("gui.core.health.walk_nas_categories")
    @patch("gui.core.transfers.validate_nas_library_preflight", return_value=(True, ""))
    def test_scan_warning_when_no_folders_found(self, mock_preflight, mock_walk, mock_load_settings, mock_mounted):
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
    @patch("gui.core.transfers.validate_nas_library_preflight", return_value=(True, ""))
    @patch("gui.core.health._check_movie_cached", return_value=10)
    @patch("gui.core.health.health_cache.HealthCacheManager")
    def test_scan_success_when_folders_found(self, mock_cache, mock_check_movie, mock_preflight, mock_walk, mock_load_settings, mock_mounted):
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

    def test_parse_nas_input_smb(self):
        # SMB-Netzwerkadresse mit und ohne Slash
        res1 = transfers.parse_nas_input("smb://192.168.2.208/kino")
        self.assertEqual(res1["host"], "192.168.2.208")
        self.assertEqual(res1["share"], "kino")
        self.assertEqual(res1["root_path"], "/Volumes/kino")

        res2 = transfers.parse_nas_input("smb://192.168.2.208/kino/")
        self.assertEqual(res2["host"], "192.168.2.208")
        self.assertEqual(res2["share"], "kino")
        self.assertEqual(res2["root_path"], "/Volumes/kino")

    def test_parse_nas_input_local_path(self):
        # Bereits eingebundener Pfad mit und ohne Slash
        res1 = transfers.parse_nas_input("/Volumes/kino")
        self.assertEqual(res1["host"], "")
        self.assertEqual(res1["share"], "kino")
        self.assertEqual(res1["root_path"], "/Volumes/kino")

        res2 = transfers.parse_nas_input("/Volumes/kino/")
        self.assertEqual(res2["host"], "")
        self.assertEqual(res2["share"], "kino")
        self.assertEqual(res2["root_path"], "/Volumes/kino")

    @patch("gui.core.duplicates.ensure_nas_mounted", return_value=True)
    @patch("gui.core.duplicates.utils.load_settings")
    @patch("gui.core.transfers.validate_nas_library_preflight")
    def test_duplicate_scan_preflight_failure(self, mock_preflight, mock_load_settings, mock_mounted):
        # Preflight schlägt fehl
        mock_preflight.return_value = (False, "Keine Bibliotheksordner gefunden.")

        duplicates._run_duplicate_scan()

        state = duplicates.get_duplicate_status()
        self.assertEqual(state["status"], "warning")
        self.assertEqual(state["error"], "no_library_folders_found")
        self.assertEqual(state["message"], "Keine Bibliotheksordner gefunden.")

    @patch("gui.core.transfers.validate_nas_library_preflight")
    @patch("gui.core.utils.load_settings")
    def test_normalize_films_endpoints_preflight_failure(self, mock_load_settings, mock_preflight):
        # Preflight schlägt fehl -> API gibt 400 zurück
        mock_preflight.return_value = (False, "Keine Bibliotheksordner gefunden.")

        res1 = self.client.get("/api/nas/normalize-films/preview")
        self.assertEqual(res1.status_code, 400)
        self.assertIn("Keine Bibliotheksordner gefunden.", res1.get_json()["error"])

        res2 = self.client.post("/api/nas/normalize-films/apply", json={"items": ["some_item"]})
        self.assertEqual(res2.status_code, 400)
        self.assertIn("Keine Bibliotheksordner gefunden.", res2.get_json()["message"])

    @patch("gui.api.system_api.os.path.isdir")
    @patch("gui.api.system_api.load_settings")
    def test_nas_test_api_local_path(self, mock_load, mock_isdir):
        mock_isdir.return_value = True
        mock_load.return_value = {
            "sync_categories": [{"id": "movies", "name": "Filme", "nas_sub": "Filme"}]
        }

        res = self.client.post("/api/nas/test", json={
            "nas_ip": "",
            "nas_ip_backup": "",
            "nas_share": "kino",
            "root_path": "/Volumes/kino"
        })

        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["server_reachable"])
        self.assertEqual(data["reachable_ip"], "Lokal gemountet (keine IP erforderlich)")
        self.assertTrue(data["local_path_exists"])

if __name__ == "__main__":
    unittest.main()
