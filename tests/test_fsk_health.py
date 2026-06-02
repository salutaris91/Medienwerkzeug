import os
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import gui.core.health as health
from gui.api.nas_api import nas_api

# Wir importieren die App, um den Blueprint zu testen
from flask import Flask
app = Flask(__name__)
app.register_blueprint(nas_api, url_prefix='/api')

class TestFSKHealthCheck(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.movie_dir = os.path.join(self.temp_dir, "My Movie (2020)")
        os.makedirs(self.movie_dir)
        
        # Fake movie file
        open(os.path.join(self.movie_dir, "My Movie (2020).mkv"), 'w').close()

        # Dummy Flask app for request context
        self.client = app.test_client()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_find_primary_nfo_movie(self):
        # Case: no NFO
        self.assertIsNone(health.find_primary_nfo(self.movie_dir, is_movie=True))
        
        # Case: exactly 1 NFO
        nfo_path = os.path.join(self.movie_dir, "movie.nfo")
        open(nfo_path, 'w').close()
        self.assertEqual(health.find_primary_nfo(self.movie_dir, is_movie=True), nfo_path)
        
        # Case: multiple NFOs, fallback via video stem
        specific_nfo = os.path.join(self.movie_dir, "My Movie (2020).nfo")
        open(specific_nfo, 'w').close()
        self.assertEqual(health.find_primary_nfo(self.movie_dir, is_movie=True), specific_nfo)

    def test_fsk_health_issues(self):
        issues = []
        nfo_path = os.path.join(self.movie_dir, "My Movie (2020).nfo")
        
        # Missing rating
        with open(nfo_path, 'w') as f:
            f.write("<movie><title>Test</title></movie>")
        health._check_fsk(issues, "Filme", self.movie_dir, nfo_path)
        self.assertTrue(any(i['type'] == 'missing_age_rating' for i in issues))
        
        # Invalid rating
        issues.clear()
        with open(nfo_path, 'w') as f:
            f.write("<movie><mpaa>Unrated</mpaa></movie>")
        health._check_fsk(issues, "Filme", self.movie_dir, nfo_path)
        self.assertTrue(any(i['type'] == 'invalid_age_rating' for i in issues))
        
        # Valid rating
        issues.clear()
        with open(nfo_path, 'w') as f:
            f.write("<movie><mpaa>FSK 16</mpaa></movie>")
        health._check_fsk(issues, "Filme", self.movie_dir, nfo_path)
        self.assertFalse(any(i['type'] == 'invalid_age_rating' for i in issues))
        self.assertFalse(any(i['type'] == 'missing_age_rating' for i in issues))

    @patch('gui.api.nas_api.load_settings')
    def test_set_fsk_api(self, mock_load_settings):
        # Setup settings mock to pass NAS validation
        mock_load_settings.return_value = {"nas_root": self.temp_dir}
        
        nfo_path = os.path.join(self.movie_dir, "My Movie (2020).nfo")
        with open(nfo_path, 'w') as f:
            f.write("<movie>\n  <title>Test</title>\n</movie>")

        # API Call - Valid
        response = self.client.post('/api/nas/health-fix', json={
            "action": "set_fsk",
            "path": self.movie_dir,
            "new_fsk": "12"
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json['ok'])
        with open(nfo_path, 'r') as f:
            content = f.read()
        self.assertIn("<mpaa>FSK 12</mpaa>", content)
        bak_files = [f for f in os.listdir(self.movie_dir) if f.endswith('.bak')]
        self.assertTrue(any(".bak." in f for f in os.listdir(self.movie_dir)))

        # API Call - Invalid value
        response = self.client.post('/api/nas/health-fix', json={
            "action": "set_fsk",
            "path": self.movie_dir,
            "new_fsk": "99"
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("Ungültiger FSK-Wert", response.json['message'])

        # API Call - Path outside NAS
        mock_load_settings.return_value = {"nas_root": "/some/other/fake/nas"}
        response = self.client.post('/api/nas/health-fix', json={
            "action": "set_fsk",
            "path": self.movie_dir,
            "new_fsk": "12"
        })
        self.assertEqual(response.status_code, 403)
        self.assertIn("außerhalb des NAS", response.json['message'])
        
        # Restore mock for further tests
        mock_load_settings.return_value = {"nas_root": self.temp_dir}

        # API Call - Multiple mpaa tags
        with open(nfo_path, 'w') as f:
            f.write("<movie><mpaa>FSK 12</mpaa><mpaa>FSK 16</mpaa></movie>")
        response = self.client.post('/api/nas/health-fix', json={
            "action": "set_fsk",
            "path": self.movie_dir,
            "new_fsk": "16"
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("Mehrere", response.json['message'])

        # API Call - Broken XML
        with open(nfo_path, 'w') as f:
            f.write("<movie><title>broken</title>")
        response = self.client.post('/api/nas/health-fix', json={
            "action": "set_fsk",
            "path": self.movie_dir,
            "new_fsk": "16"
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("Original-XML fehlerhaft", response.json['message'])

if __name__ == '__main__':
    unittest.main()
