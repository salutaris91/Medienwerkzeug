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
        mock_load_settings.return_value = {
            "nas_root": self.temp_dir,
            "sync_categories": [{"name": "Filme", "nas_sub": ".", "type": "movie"}]
        }

        nfo_path = os.path.join(self.movie_dir, "My Movie (2020).nfo")
        with open(nfo_path, 'w') as f:
            f.write("<movie>\n  <title>Test</title>\n</movie>")
        with open(os.path.join(self.movie_dir, "My Movie (2020).mkv"), 'w') as f:
            f.write("dummy video")

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
        mock_load_settings.return_value = {
            "nas_root": self.temp_dir,
            "sync_categories": [{"name": "Filme", "nas_sub": ".", "type": "movie"}]
        }

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

    @patch('gui.api.nas_api.load_settings')
    def test_set_fsk_api_series(self, mock_load_settings):
        # Setup settings mock to pass NAS validation and simulate a series category
        mock_load_settings.return_value = {
            "nas_root": self.temp_dir,
            "sync_categories": [
                {
                    "name": "Serien",
                    "nas_sub": "/Serien"
                }
            ]
        }

        series_dir = os.path.join(self.temp_dir, "Serien", "My Show")
        os.makedirs(series_dir)

        # Erstelle eine tvshow.nfo
        tvshow_nfo_path = os.path.join(series_dir, "tvshow.nfo")
        with open(tvshow_nfo_path, 'w') as f:
            f.write("<tvshow>\n  <title>Test Show</title>\n</tvshow>")

        # Erstelle EINE Film-NFO (Fehlerfall: Film-NFO in einem Serienordner)
        movie_nfo_path = os.path.join(series_dir, "movie.nfo")
        with open(movie_nfo_path, 'w') as f:
            f.write("<movie>\n  <title>Test Movie</title>\n</movie>")

        # API Call - Valid
        response = self.client.post('/api/nas/health-fix', json={
            "action": "set_fsk",
            "path": series_dir,
            "new_fsk": "16"
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json['ok'])

        # Check if tvshow.nfo was modified
        with open(tvshow_nfo_path, 'r') as f:
            content = f.read()
        self.assertIn("<mpaa>FSK 16</mpaa>", content)

        # Check if movie.nfo remained untouched
        with open(movie_nfo_path, 'r') as f:
            movie_content = f.read()
        self.assertNotIn("<mpaa>", movie_content)

    @patch('gui.api.nas_api.load_settings')
    def test_set_fsk_api_nested_categories(self, mock_load_settings):
        # Setup settings mit verschachtelten Kategorien
        mock_load_settings.return_value = {
            "nas_root": self.temp_dir,
            "sync_categories": [
                {
                    "name": "Dokus",
                    "nas_sub": "/Dokus" # generic docs -> movie
                },
                {
                    "name": "Doku-Serien",
                    "nas_sub": "/Dokus/Doku-Serien" # specific docs -> series
                }
            ]
        }

        series_dir = os.path.join(self.temp_dir, "Dokus", "Doku-Serien", "My Planet")
        os.makedirs(series_dir)

        # Erstelle eine tvshow.nfo
        tvshow_nfo_path = os.path.join(series_dir, "tvshow.nfo")
        with open(tvshow_nfo_path, 'w') as f:
            f.write("<tvshow>\n  <title>Test Planet</title>\n</tvshow>")

        # Erstelle EINE Film-NFO (Fehlerfall)
        movie_nfo_path = os.path.join(series_dir, "movie.nfo")
        with open(movie_nfo_path, 'w') as f:
            f.write("<movie>\n  <title>Test Movie</title>\n</movie>")

        # API Call
        response = self.client.post('/api/nas/health-fix', json={
            "action": "set_fsk",
            "path": series_dir,
            "new_fsk": "6"
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json['ok'])

        # Check if tvshow.nfo was modified (da Doku-Serien als best_cat mit längstem Pfad matcht)
        with open(tvshow_nfo_path, 'r') as f:
            content = f.read()
        self.assertIn("<mpaa>FSK 6</mpaa>", content)

        # Check if movie.nfo remained untouched
        with open(movie_nfo_path, 'r') as f:
            movie_content = f.read()
        self.assertNotIn("<mpaa>", movie_content)


class TestFSKHealthStructureAggregation(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.nas_root = os.path.join(self.temp_dir, "nas")
        os.makedirs(self.nas_root)

        # Settings mock setup
        self.settings = {
            "nas_root": self.nas_root,
            "sync_categories": [
                {"id": "filme", "name": "Filme", "nas_sub": "/Filme", "type": "movie"},
                {"id": "serien", "name": "Serien", "nas_sub": "/Serien", "type": "series"}
            ],
            "media_server": "none"
        }
        self.patcher_settings = patch('gui.core.health.utils.load_settings', return_value=self.settings)
        self.patcher_settings.start()

        self.patcher_mount = patch('gui.core.health.ensure_nas_mounted', return_value=True)
        self.patcher_mount.start()

        self.patcher_preflight = patch('gui.core.transfers.validate_nas_library_preflight', return_value=(True, ""))
        self.patcher_preflight.start()

        # Create film and series layout
        self.movie_dir = os.path.join(self.nas_root, "Filme", "My Movie (2020)")
        os.makedirs(self.movie_dir)
        open(os.path.join(self.movie_dir, "My Movie (2020).mkv"), 'w').close()
        # Invalid FSK rating in movie.nfo
        with open(os.path.join(self.movie_dir, "movie.nfo"), 'w') as f:
            f.write("<movie><mpaa>Unrated</mpaa></movie>")

        self.show_dir = os.path.join(self.nas_root, "Serien", "My Show")
        os.makedirs(self.show_dir)
        # Missing tvshow.nfo (simulates missing NFO issue)
        self.season_dir = os.path.join(self.show_dir, "Season 1")
        os.makedirs(self.season_dir)
        open(os.path.join(self.season_dir, "My Show - S01E01.mkv"), 'w').close()
        open(os.path.join(self.season_dir, "My Show - S01E02.mkv"), 'w').close()
        # Season 1 Episode NFOs
        with open(os.path.join(self.season_dir, "My Show - S01E01.nfo"), 'w') as f:
            f.write("<episodedetails><mpaa>FSK 12</mpaa></episodedetails>")
        with open(os.path.join(self.season_dir, "My Show - S01E02.nfo"), 'w') as f:
            f.write("<episodedetails><mpaa>Keine</mpaa></episodedetails>") # invalid/missing

    def tearDown(self):
        self.patcher_preflight.stop()
        self.patcher_mount.stop()
        self.patcher_settings.stop()
        shutil.rmtree(self.temp_dir)

    def test_cache_version_upgrade(self):
        from gui.core.health_cache import HealthCacheManager
        cache_mgr = HealthCacheManager()

        # Simulate older Cache Entry (version 2) in Cache File
        cache_mgr._cache["2:none"] = {
            self.movie_dir: {
                "issues": [],
                "files_checked": 1,
                "hybrid_state": "some-hash"
            }
        }
        # Under version 3, querying version 3 should not see or hit version 2 entry
        entry = cache_mgr.get_cached_entry(self.movie_dir, "3:none")
        self.assertIsNone(entry)

    def test_run_health_scan_aggregation(self):
        # Reset scan state
        health._scan_state["media_structure"] = {"series": [], "movies": []}
        health._scan_state["issues"] = []

        # Run Scan
        health._run_health_scan()

        status = health.get_health_status()
        self.assertEqual(status["status"], "done")

        media_structure = status.get("media_structure")
        self.assertIsNotNone(media_structure)

        # Validate movie entry
        movies = media_structure.get("movies", [])
        self.assertEqual(len(movies), 1)
        movie_meta = movies[0]
        self.assertEqual(movie_meta["name"], "My Movie (2020)")
        self.assertEqual(movie_meta["path"], self.movie_dir)
        self.assertEqual(movie_meta["fsk_status"], "Ungültig: Unrated")
        self.assertEqual(movie_meta["actionable_fsk"], "Unrated")
        self.assertTrue(len(movie_meta["issue_keys"]) > 0)

        # Validate series entry
        series = media_structure.get("series", [])
        self.assertEqual(len(series), 1)
        show_meta = series[0]
        self.assertEqual(show_meta["name"], "My Show")
        self.assertEqual(show_meta["path"], self.show_dir)
        self.assertFalse(show_meta["has_nfo"]) # tvshow.nfo is missing
        self.assertEqual(show_meta["fsk_status"], "Keine")

        # Validate seasons & episodes
        seasons = show_meta.get("seasons", [])
        self.assertEqual(len(seasons), 1)
        season_meta = seasons[0]
        self.assertEqual(season_meta["name"], "Season 1")
        self.assertEqual(season_meta["path"], self.season_dir)

        episodes = season_meta.get("episodes", [])
        self.assertEqual(len(episodes), 2)

        # Ep 1: valid FSK 12
        ep1 = next(e for e in episodes if "S01E01" in e["name"])
        self.assertEqual(ep1["fsk_status"], "FSK 12")
        self.assertIsNone(ep1["actionable_fsk"])
        self.assertFalse(any("age_rating" in k for k in ep1["issue_keys"]))

        # Ep 2: invalid FSK Keine
        ep2 = next(e for e in episodes if "S01E02" in e["name"])
        self.assertEqual(ep2["fsk_status"], "Ungültig: Keine")
        self.assertEqual(ep2["actionable_fsk"], "Keine")
        self.assertTrue(any("age_rating" in k for k in ep2["issue_keys"]))


if __name__ == '__main__':
    unittest.main()
