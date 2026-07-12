import os
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import gui.core.health as health
from gui.api.nas_api import nas_api

from flask import Flask
app = Flask(__name__)
app.register_blueprint(nas_api, url_prefix='/api')

class TestFSKBatchEndpoints(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.nas_root = os.path.realpath(self.temp_dir)
        
        # Kategorien einrichten: Filme und Serien
        self.movies_dir = os.path.join(self.nas_root, "Filme")
        self.series_dir = os.path.join(self.nas_root, "Serien")
        os.makedirs(self.movies_dir)
        os.makedirs(self.series_dir)
        
        # Test-Client
        self.client = app.test_client()

        # Mock settings
        self.mock_settings = {
            "nas_root": self.nas_root,
            "sync_categories": [
                {
                    "name": "Filme",
                    "nas_sub": "/Filme"
                },
                {
                    "name": "Serien",
                    "nas_sub": "/Serien"
                }
            ]
        }

        # Active patcher for allowed roots
        self.patcher_roots = patch('gui.core.utils.get_allowed_roots', return_value=[self.nas_root])
        self.patcher_roots.start()

    def tearDown(self):
        self.patcher_roots.stop()
        shutil.rmtree(self.temp_dir)

    @patch('gui.api.nas_api.load_settings')
    def test_preview_validation_errors(self, mock_load_settings):
        mock_load_settings.return_value = self.mock_settings
        
        # Case 1: Category root as target (Forbidden)
        res = self.client.post('/api/nas/fsk-batch/preview', json={
            "paths": [self.series_dir],
            "scope": "series",
            "new_fsk": "12"
        })
        print("CASE 1 JSON:", res.json)
        self.assertEqual(res.status_code, 400)
        self.assertIn("Kategorieordner oder NAS-Hauptroot", res.json["message"])

        # Case 2: NAS root as target (Forbidden)
        res = self.client.post('/api/nas/fsk-batch/preview', json={
            "paths": [self.nas_root],
            "scope": "series",
            "new_fsk": "12"
        })
        if res.status_code != 400:
            print("CASE 2 FAIL JSON:", res.json)
        self.assertEqual(res.status_code, 400)
        self.assertIn("Kategorieordner oder NAS-Hauptroot", res.json["message"])

        # Case 3: Invalid FSK value
        res = self.client.post('/api/nas/fsk-batch/preview', json={
            "paths": [os.path.join(self.series_dir, "ShowA")],
            "scope": "series",
            "new_fsk": "99"
        })
        if res.status_code != 400:
            print("CASE 3 FAIL JSON:", res.json)
        self.assertEqual(res.status_code, 400)
        self.assertIn("Ungültiger FSK-Wert", res.json["message"])

        # Case 4: Invalid Scope
        res = self.client.post('/api/nas/fsk-batch/preview', json={
            "paths": [os.path.join(self.series_dir, "ShowA")],
            "scope": "invalid_scope",
            "new_fsk": "12"
        })
        if res.status_code != 400:
            print("CASE 4 FAIL JSON:", res.json)
        self.assertEqual(res.status_code, 400)
        self.assertIn("Ungültiger Scope", res.json["message"])

    @patch('gui.api.nas_api.load_settings')
    def test_preview_season_scope_validation(self, mock_load_settings):
        mock_load_settings.return_value = self.mock_settings
        
        # Erstelle eine Serie und einen Staffelordner
        show_dir = os.path.join(self.series_dir, "Dracula")
        season_dir = os.path.join(show_dir, "Staffel 1")
        os.makedirs(season_dir)
        
        # Test 1: Scope=season auf Serienordner aufrufen (Fehler)
        res = self.client.post('/api/nas/fsk-batch/preview', json={
            "paths": [show_dir],
            "scope": "season",
            "new_fsk": "12"
        })
        if res.status_code != 400:
            print("SEASON TEST 1 FAIL JSON:", res.json)
        self.assertEqual(res.status_code, 400)
        self.assertIn("kein gültiger Staffelordner", res.json["message"])

        # Test 2: Scope=season auf echten Staffelordner aufrufen (Erfolg)
        # Erstelle eine Video-Datei und eine NFO im Staffelordner
        video_path = os.path.join(season_dir, "S01E01.mkv")
        nfo_path = os.path.join(season_dir, "S01E01.nfo")
        open(video_path, 'w').close()
        with open(nfo_path, 'w') as f:
            f.write("<episode><mpaa>FSK 6</mpaa></episode>")

        res = self.client.post('/api/nas/fsk-batch/preview', json={
            "paths": [season_dir],
            "scope": "season",
            "new_fsk": "12"
        })
        if res.status_code != 200:
            print("SEASON TEST 2 FAIL JSON:", res.json)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json["ok"])
        self.assertEqual(res.json["summary"]["ready"], 1)
        self.assertEqual(res.json["files"][0]["path"], os.path.realpath(nfo_path))

    @patch('gui.api.nas_api.load_settings')
    @patch('gui.core.health_cache.HealthCacheManager.invalidate_entry')
    @patch('gui.core.health.remove_issue')
    def test_apply_and_race_condition(self, mock_remove_issue, mock_invalidate, mock_load_settings):
        mock_load_settings.return_value = self.mock_settings
        
        # Erstelle Film-Struktur
        movie_dir = os.path.join(self.movies_dir, "Avatar (2009)")
        os.makedirs(movie_dir)
        nfo_path = os.path.join(movie_dir, "movie.nfo")
        with open(nfo_path, 'w') as f:
            f.write("<movie><mpaa>FSK 12</mpaa></movie>")
            
        # 1. Vorschau anfordern, um Fingerprints zu bekommen
        preview_res = self.client.post('/api/nas/fsk-batch/preview', json={
            "paths": [movie_dir],
            "scope": "single",
            "new_fsk": "16"
        })
        if preview_res.status_code != 200:
            print("APPLY TEST PREVIEW FAIL JSON:", preview_res.json)
        self.assertEqual(preview_res.status_code, 200)
        self.assertEqual(preview_res.json["summary"]["ready"], 1)
        
        preview_data = preview_res.json
        expected_files = preview_data["files"]
        
        # 2. Erfolgreiches Anwenden (apply)
        apply_res = self.client.post('/api/nas/fsk-batch/apply', json={
            "root_paths": [movie_dir],
            "scope": "single",
            "new_fsk": "16",
            "files": expected_files
        })
        if apply_res.status_code != 200:
            print("APPLY TEST APPLY FAIL JSON:", apply_res.json)
        self.assertEqual(apply_res.status_code, 200)
        self.assertTrue(apply_res.json["ok"])
        self.assertEqual(apply_res.json["summary"]["success"], 1)
        
        # Inhalt prüfen
        with open(nfo_path, 'r') as f:
            content = f.read()
        self.assertIn("<mpaa>FSK 16</mpaa>", content)
        
        # Prüfen, ob Cache invalidiert und Issues gelöscht wurden
        mock_invalidate.assert_called_with(os.path.realpath(movie_dir))
        mock_remove_issue.assert_any_call(os.path.realpath(nfo_path), "missing_age_rating")
        mock_remove_issue.assert_any_call(os.path.realpath(nfo_path), "invalid_age_rating")

        # 3. Race Condition erzeugen: mtime/hash manipulieren und apply aufrufen
        # Wir ändern den Inhalt der Datei physisch
        with open(nfo_path, 'w') as f:
            f.write("<movie><mpaa>FSK 0</mpaa></movie>")
            
        # Apply mit alten Fingerprints aufrufen -> muss 409 zurückgeben
        apply_res = self.client.post('/api/nas/fsk-batch/apply', json={
            "root_paths": [movie_dir],
            "scope": "single",
            "new_fsk": "16",
            "files": expected_files # alte Fingerprints
        })
        self.assertEqual(apply_res.status_code, 409)
        self.assertIn("Race Condition", apply_res.json["message"])

if __name__ == '__main__':
    unittest.main()
