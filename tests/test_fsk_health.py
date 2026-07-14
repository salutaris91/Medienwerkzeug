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
        self.client = app.test_client()

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
        self.assertEqual(movie_meta["fsk_status"], "invalid_fsk")
        self.assertEqual(movie_meta["current_fsk"], "Ungültig: Unrated")
        self.assertEqual(movie_meta["raw_fsk"], "Unrated")
        self.assertTrue(movie_meta["actionable_fsk"])
        self.assertTrue(len(movie_meta["issue_keys"]) > 0)

        # Validate series entry
        series = media_structure.get("series", [])
        self.assertEqual(len(series), 1)
        show_meta = series[0]
        self.assertEqual(show_meta["name"], "My Show")
        self.assertEqual(show_meta["path"], self.show_dir)
        self.assertFalse(show_meta["has_nfo"]) # tvshow.nfo is missing
        self.assertEqual(show_meta["fsk_status"], "nfo_missing")

        # Validate seasons & episodes
        seasons = show_meta.get("seasons", [])
        self.assertEqual(len(seasons), 1)
        season_meta = seasons[0]
        self.assertEqual(season_meta["name"], "Season 1")
        self.assertEqual(season_meta["path"], self.season_dir)
        season_issue_keys = {
            issue["key"] for issue in status["issues"]
            if os.path.realpath(issue["path"]) == os.path.realpath(self.season_dir)
        }
        self.assertEqual(set(season_meta["issue_keys"]), season_issue_keys)

        episodes = season_meta.get("episodes", [])
        self.assertEqual(len(episodes), 2)

        # Ep 1: valid FSK 12
        ep1 = next(e for e in episodes if "S01E01" in e["name"])
        self.assertEqual(ep1["fsk_status"], "healthy")
        self.assertEqual(ep1["current_fsk"], "FSK 12")
        self.assertEqual(ep1["raw_fsk"], "FSK 12")
        self.assertFalse(ep1["actionable_fsk"])
        self.assertFalse(any("age_rating" in k for k in ep1["issue_keys"]))

        # Ep 2: invalid FSK Keine
        ep2 = next(e for e in episodes if "S01E02" in e["name"])
        self.assertEqual(ep2["fsk_status"], "invalid_fsk")
        self.assertEqual(ep2["current_fsk"], "Ungültig: Keine")
        self.assertEqual(ep2["raw_fsk"], "Keine")
        self.assertTrue(ep2["actionable_fsk"])
        self.assertTrue(any("age_rating" in k for k in ep2["issue_keys"]))

    def test_health_scan_excludes_backup_folder_and_maps_missing_episode_nfo(self):
        missing_video = os.path.join(self.season_dir, "My Show - S01E03.mkv")
        open(missing_video, "w").close()
        backup_dir = os.path.join(self.show_dir, "Staffel Backup")
        os.makedirs(backup_dir)
        open(os.path.join(backup_dir, "My Show Bonus.mkv"), "w").close()

        health._scan_state["media_structure"] = {"series": [], "movies": []}
        health._scan_state["issues"] = []
        health._run_health_scan()

        status = health.get_health_status()
        show = status["media_structure"]["series"][0]
        self.assertEqual([season["name"] for season in show["seasons"]], ["Season 1"])
        episodes = show["seasons"][0]["episodes"]
        self.assertEqual(len(episodes), 3)

        missing_episode = next(ep for ep in episodes if "S01E03" in ep["name"])
        expected_nfo = os.path.splitext(missing_video)[0] + ".nfo"
        self.assertEqual(missing_episode["path"], expected_nfo)
        self.assertEqual(missing_episode["fsk_status"], "nfo_missing")
        self.assertTrue(any("missing_nfo" in key for key in missing_episode["issue_keys"]))

        missing_issue = next(issue for issue in status["issues"] if issue["path"] == expected_nfo)
        self.assertEqual(missing_issue["agent_path"], self.season_dir)
        self.assertFalse(any("Staffel Backup" in issue.get("path", "") for issue in status["issues"]))

    @patch('gui.api.nas_api.write_fsk_to_nfo')
    @patch('gui.core.health.remove_issue')
    @patch('gui.api.nas_api.load_settings')
    def test_health_fix_issue_removal_args(self, mock_load_settings, mock_remove_issue, mock_write_fsk):
        mock_load_settings.return_value = {
            "nas_root": self.temp_dir,
            "nas_paths": {"Filme": self.temp_dir, "Serien": self.temp_dir},
            "sync_categories": [{"name": "Filme", "nas_sub": "/"}]
        }
        mock_write_fsk.return_value = (True, "")
        import os
        movie_dir = os.path.join(self.temp_dir, "Ein Film")
        os.makedirs(movie_dir, exist_ok=True)
        nfo_path = os.path.join(movie_dir, "movie.nfo")
        with open(nfo_path, 'w') as f:
            f.write("<movie></movie>")
        with open(os.path.join(movie_dir, "Ein Film.mkv"), 'w') as f:
            f.write("video")

        res = self.client.post('/api/nas/health-fix', json={
            "action": "set_fsk",
            "path": nfo_path,
            "new_fsk": "12"
        })
        self.assertEqual(res.status_code, 200)

        # Überprüfen, ob remove_issue mit nfo_path Argument für das Verzeichnis (real_path) gerufen wurde
        real_movie_dir = os.path.realpath(movie_dir)
        real_nfo_path = os.path.realpath(nfo_path)
        mock_remove_issue.assert_any_call(real_movie_dir, "missing_age_rating", nfo_path=real_nfo_path)
        mock_remove_issue.assert_any_call(real_movie_dir, "invalid_age_rating", nfo_path=real_nfo_path)
        mock_remove_issue.reset_mock()

        res = self.client.post('/api/nas/health-fix', json={
            "action": "set_fsk",
            "path": nfo_path,
            "new_fsk": "16"
        })
        self.assertEqual(res.status_code, 200)
        # remove_issue sollte für den Verzeichnis-Issue-Pfad aufgerufen werden (da movie.nfo)
        mock_remove_issue.assert_any_call(real_movie_dir, "missing_age_rating", nfo_path=real_nfo_path)

if __name__ == '__main__':
    unittest.main()
