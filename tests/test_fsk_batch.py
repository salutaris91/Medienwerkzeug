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
        self.assertEqual(res.status_code, 400)
        self.assertIn("Kategorieordner oder NAS-Hauptroot", res.json["message"])

        # Case 2: NAS root as target (Forbidden)
        res = self.client.post('/api/nas/fsk-batch/preview', json={
            "paths": [self.nas_root],
            "scope": "series",
            "new_fsk": "12"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("Kategorieordner oder NAS-Hauptroot", res.json["message"])

        # Case 3: Invalid FSK value
        res = self.client.post('/api/nas/fsk-batch/preview', json={
            "paths": [os.path.join(self.series_dir, "ShowA")],
            "scope": "series",
            "new_fsk": "99"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("Ungültiger FSK-Wert", res.json["message"])

        # Case 4: Invalid Scope
        res = self.client.post('/api/nas/fsk-batch/preview', json={
            "paths": [os.path.join(self.series_dir, "ShowA")],
            "scope": "invalid_scope",
            "new_fsk": "12"
        })
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
        with open(os.path.join(movie_dir, "Avatar (2009).mkv"), 'w') as f:
            f.write("dummy video")

        # 1. Vorschau anfordern, um Fingerprints zu bekommen
        preview_res = self.client.post('/api/nas/fsk-batch/preview', json={
            "paths": [movie_dir],
            "scope": "single",
            "new_fsk": "16"
        })
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
        self.assertEqual(apply_res.status_code, 200)
        self.assertTrue(apply_res.json["ok"])
        self.assertEqual(apply_res.json["summary"]["success"], 1)

        # Inhalt prüfen
        with open(nfo_path, 'r') as f:
            content = f.read()
        self.assertIn("<mpaa>FSK 16</mpaa>", content)

        # Prüfen, ob Cache invalidiert und Issues gelöscht wurden
        mock_invalidate.assert_called_with(os.path.realpath(movie_dir))
        mock_remove_issue.assert_any_call(os.path.realpath(movie_dir), "missing_age_rating", nfo_path=os.path.realpath(nfo_path))
        mock_remove_issue.assert_any_call(os.path.realpath(movie_dir), "invalid_age_rating", nfo_path=os.path.realpath(nfo_path))

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


    @patch('gui.api.nas_api.load_settings')
    def test_movie_ohne_video(self, mock_load_settings):
        mock_load_settings.return_value = self.mock_settings
        import os
        movie_dir = os.path.join(self.movies_dir, "No Video Movie")
        os.makedirs(movie_dir)
        nfo_path = os.path.join(movie_dir, "movie.nfo")
        with open(nfo_path, 'w') as f_nfo:
            f_nfo.write("<movie></movie>")
        res = self.client.post('/api/nas/fsk-batch/preview', json={
            "paths": [movie_dir], "scope": "single", "new_fsk": "12"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("Gefundene NFO-Datei ist unzulässig", res.json["message"])

    @patch('gui.api.nas_api.load_settings')
    def test_gueltige_tvshow_nfo(self, mock_load_settings):
        mock_load_settings.return_value = self.mock_settings
        import os
        series_dir = os.path.join(self.series_dir, "Gueltige Serie")
        os.makedirs(series_dir)
        nfo_path = os.path.join(series_dir, "tvshow.nfo")
        with open(nfo_path, 'w') as f_nfo:
            f_nfo.write("<tvshow></tvshow>")
        res = self.client.post('/api/nas/fsk-batch/preview', json={
            "paths": [series_dir], "scope": "series", "new_fsk": "12"
        })
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json["summary"]["ready"], 1)

    @patch('gui.api.nas_api.load_settings')
    def test_season_nfo_ausschluss(self, mock_load_settings):
        mock_load_settings.return_value = self.mock_settings
        import os
        series_dir = os.path.join(self.series_dir, "Season NFO Serie")
        os.makedirs(series_dir)
        with open(os.path.join(series_dir, "tvshow.nfo"), 'w') as f_nfo:
            f_nfo.write("<tvshow></tvshow>")
        season_dir = os.path.join(series_dir, "Staffel 1")
        os.makedirs(season_dir)
        with open(os.path.join(season_dir, "season.nfo"), 'w') as f_nfo:
            f_nfo.write("<season></season>")
        res = self.client.post('/api/nas/fsk-batch/preview', json={
            "paths": [season_dir], "scope": "season", "new_fsk": "12"
        })
        self.assertEqual(res.status_code, 200)
        files = [f["path"] for f in res.json["files"]]
        self.assertTrue(any("season.nfo" in f for f in files))

    @patch('gui.api.nas_api.load_settings')
    def test_episodenlayouts(self, mock_load_settings):
        mock_load_settings.return_value = self.mock_settings
        import os
        series_dir = os.path.join(self.series_dir, "Ep Layout Serie")
        os.makedirs(series_dir)
        with open(os.path.join(series_dir, "tvshow.nfo"), 'w') as f_nfo:
            f_nfo.write("<tvshow></tvshow>")
        season_dir = os.path.join(series_dir, "Staffel 1")
        os.makedirs(season_dir)
        with open(os.path.join(season_dir, "Ep1.mkv"), 'w') as f_vid:
            f_vid.write("vid")
        with open(os.path.join(season_dir, "Ep1.nfo"), 'w') as f_nfo:
            f_nfo.write("<episode></episode>")
        ep_dir = os.path.join(season_dir, "Ep2")
        os.makedirs(ep_dir)
        with open(os.path.join(ep_dir, "Ep2.mkv"), 'w') as f_vid:
            f_vid.write("vid")
        with open(os.path.join(ep_dir, "Ep2.nfo"), 'w') as f_nfo:
            f_nfo.write("<episode></episode>")
        res = self.client.post('/api/nas/fsk-batch/preview', json={
            "paths": [season_dir], "scope": "season", "new_fsk": "12"
        })
        self.assertEqual(res.json["summary"]["ready"], 2)

    @patch('gui.api.nas_api.load_settings')
    def test_strenge_regex(self, mock_load_settings):
        mock_load_settings.return_value = self.mock_settings
        import os
        series_dir = os.path.join(self.series_dir, "Regex Serie")
        os.makedirs(series_dir)
        with open(os.path.join(series_dir, "tvshow.nfo"), 'w') as f_nfo:
            f_nfo.write("<tvshow></tvshow>")
        invalid_dir = os.path.join(series_dir, "Staffel Backup")
        os.makedirs(invalid_dir)
        res = self.client.post('/api/nas/fsk-batch/preview', json={
            "paths": [invalid_dir], "scope": "season", "new_fsk": "12"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("Pfad ist kein gültiger Staffelordner", res.json["message"])

    @patch('gui.api.nas_api.load_settings')
    def test_symlink_ausbruch(self, mock_load_settings):
        mock_load_settings.return_value = self.mock_settings
        import os
        series_dir = os.path.join(self.series_dir, "Symlink Serie")
        os.makedirs(series_dir)
        with open(os.path.join(series_dir, "tvshow.nfo"), 'w') as f_nfo:
            f_nfo.write("<tvshow></tvshow>")

        outside_dir = tempfile.mkdtemp()
        try:
            with open(os.path.join(outside_dir, "outside.mkv"), 'w') as f_vid:
                f_vid.write("vid")
            symlink_dir = os.path.join(series_dir, "Staffel 1")
            try:
                os.symlink(outside_dir, symlink_dir)
            except Exception:
                pass
            if os.path.exists(symlink_dir):
                res = self.client.post('/api/nas/fsk-batch/preview', json={
                    "paths": [symlink_dir], "scope": "season", "new_fsk": "12"
                })
                self.assertEqual(res.status_code, 403)
        finally:
            shutil.rmtree(outside_dir)

    @patch('gui.core.health_cache.HealthCacheManager.invalidate_entry')
    @patch('gui.core.health.remove_issue')
    @patch('gui.api.nas_api.load_settings')
    def test_deterministischer_teilerfolg(self, mock_load_settings, mock_remove, mock_inv):
        mock_load_settings.return_value = self.mock_settings
        import os
        movie1_dir = os.path.join(self.movies_dir, "Movie 1")
        os.makedirs(movie1_dir)
        with open(os.path.join(movie1_dir, "movie.nfo"), 'w') as f_nfo:
            f_nfo.write("<movie></movie>")
        with open(os.path.join(movie1_dir, "Movie 1.mkv"), 'w') as f_vid:
            f_vid.write("vid")
        movie2_dir = os.path.join(self.movies_dir, "Movie 2")
        os.makedirs(movie2_dir)
        with open(os.path.join(movie2_dir, "movie.nfo"), 'w') as f_nfo:
            f_nfo.write("<movie></movie>")
        with open(os.path.join(movie2_dir, "Movie 2.mkv"), 'w') as f_vid:
            f_vid.write("vid")

        res_prev = self.client.post('/api/nas/fsk-batch/preview', json={
            "paths": [movie1_dir, movie2_dir], "scope": "single", "new_fsk": "12"
        })
        files = res_prev.json["files"]

        def side_effect_write(nfo, fsk_str):
            if "Movie 2" in nfo:
                return False, "Fehler simuliert"
            return True, "Erfolg"

        with patch('gui.api.nas_api.write_fsk_to_nfo', side_effect=side_effect_write):
            res_app = self.client.post('/api/nas/fsk-batch/apply', json={
                "root_paths": [movie1_dir, movie2_dir], "scope": "single", "new_fsk": "12", "files": files
            })
            self.assertEqual(res_app.status_code, 200)
            self.assertTrue(res_app.json["ok"])
            self.assertEqual(res_app.json["status"], "partial")
            self.assertEqual(res_app.json["summary"]["success"], 1)
            self.assertEqual(res_app.json["summary"]["failed"], 1)

    @patch('gui.core.health_cache.HealthCacheManager.invalidate_entry')
    @patch('gui.core.health.remove_issue')
    @patch('gui.api.nas_api.load_settings')
    def test_vollstaendiger_fehlschlag(self, mock_load_settings, mock_remove, mock_inv):
        mock_load_settings.return_value = self.mock_settings
        import os
        movie1_dir = os.path.join(self.movies_dir, "Movie 3")
        os.makedirs(movie1_dir)
        with open(os.path.join(movie1_dir, "movie.nfo"), 'w') as f_nfo:
            f_nfo.write("<movie></movie>")
        with open(os.path.join(movie1_dir, "Movie 3.mkv"), 'w') as f_vid:
            f_vid.write("vid")

        res_prev = self.client.post('/api/nas/fsk-batch/preview', json={
            "paths": [movie1_dir], "scope": "single", "new_fsk": "12"
        })
        files = res_prev.json["files"]

        with patch('gui.api.nas_api.write_fsk_to_nfo', return_value=(False, "Fehler simuliert")):
            res_app = self.client.post('/api/nas/fsk-batch/apply', json={
                "root_paths": [movie1_dir], "scope": "single", "new_fsk": "12", "files": files
            })
            self.assertEqual(res_app.status_code, 200)
            self.assertFalse(res_app.json["ok"])
            self.assertEqual(res_app.json["status"], "failed")
            self.assertEqual(res_app.json["summary"]["success"], 0)
            self.assertEqual(res_app.json["summary"]["failed"], 1)

    @patch('gui.api.nas_api.load_settings')
    def test_mtime_ns_string_roundtrip_and_pure_mtime_change(self, mock_load_settings):
        mock_load_settings.return_value = self.mock_settings
        movie_dir = os.path.join(self.movies_dir, "Movie String Mtime")
        os.makedirs(movie_dir)
        nfo_path = os.path.join(movie_dir, "movie.nfo")
        with open(nfo_path, 'wb') as f:
            f.write(b"<movie><mpaa>FSK 6</mpaa></movie>")
        with open(os.path.join(movie_dir, "video.mkv"), 'w') as f:
            f.write("video")

        # 1. Vorschau anfordern
        res_prev = self.client.post('/api/nas/fsk-batch/preview', json={
            "paths": [movie_dir], "scope": "single", "new_fsk": "12"
        })
        self.assertEqual(res_prev.status_code, 200)
        client_files = res_prev.json["files"]

        # Sicherstellen, dass mtime_ns ein String ist
        self.assertIsInstance(client_files[0]["fingerprint"]["mtime_ns"], str)

        # 2. Reine mtime-Änderung (Inhalt gleich) simulieren
        # Wir ändern den mtime_ns Wert im Client-Plan leicht ab (wie bei Rundung)
        client_files_rounded = [dict(f) for f in client_files]
        orig_mtime = client_files_rounded[0]["fingerprint"]["mtime_ns"]
        client_files_rounded[0]["fingerprint"]["mtime_ns"] = str(int(orig_mtime) + 10)

        # Apply ausführen -> darf NICHT fehlschlagen (reine mtime-Toleranz)
        res_app = self.client.post('/api/nas/fsk-batch/apply', json={
            "root_paths": [movie_dir], "scope": "single", "new_fsk": "12", "files": client_files_rounded
        })
        self.assertEqual(res_app.status_code, 200)
        self.assertTrue(res_app.json["ok"])
        self.assertEqual(res_app.json["summary"]["success"], 1)

    @patch('gui.api.nas_api.load_settings')
    def test_real_content_change_triggers_409(self, mock_load_settings):
        mock_load_settings.return_value = self.mock_settings
        movie_dir = os.path.join(self.movies_dir, "Movie Content Change")
        os.makedirs(movie_dir)
        nfo_path = os.path.join(movie_dir, "movie.nfo")
        with open(nfo_path, 'wb') as f:
            f.write(b"<movie><mpaa>FSK 6</mpaa></movie>")
        with open(os.path.join(movie_dir, "video.mkv"), 'w') as f:
            f.write("video")

        res_prev = self.client.post('/api/nas/fsk-batch/preview', json={
            "paths": [movie_dir], "scope": "single", "new_fsk": "12"
        })
        client_files = res_prev.json["files"]

        # Datei inhaltlich modifizieren (SHA-256 ändert sich)
        with open(nfo_path, 'wb') as f:
            f.write(b"<movie><title>Modified Plot</title><mpaa>FSK 6</mpaa></movie>")

        res_app = self.client.post('/api/nas/fsk-batch/apply', json={
            "root_paths": [movie_dir], "scope": "single", "new_fsk": "12", "files": client_files
        })
        self.assertEqual(res_app.status_code, 409)
        self.assertIn("extern modifiziert", res_app.json["message"])

    @patch('gui.api.nas_api.load_settings')
    @patch('gui.api.nas_api.calculate_nfo_hash')
    def test_hash_read_error_triggers_409(self, mock_hash, mock_load_settings):
        mock_load_settings.return_value = self.mock_settings
        mock_hash.side_effect = IOError("Berechtigungsfehler beim Lesen")

        movie_dir = os.path.join(self.movies_dir, "Movie Hash Error")
        os.makedirs(movie_dir)
        nfo_path = os.path.join(movie_dir, "movie.nfo")
        with open(nfo_path, 'wb') as f:
            f.write(b"<movie><mpaa>FSK 6</mpaa></movie>")
        with open(os.path.join(movie_dir, "video.mkv"), 'w') as f:
            f.write("video")

        # In der Vorschau führt mock_hash.side_effect zum Abbruch
        res_prev = self.client.post('/api/nas/fsk-batch/preview', json={
            "paths": [movie_dir], "scope": "single", "new_fsk": "12"
        })
        self.assertEqual(res_prev.status_code, 500)
        self.assertIn("Fehler bei der Vorschau-Erstellung", res_prev.json["message"])

    @patch('gui.api.nas_api.load_settings')
    def test_missing_nfo_validation_rules(self, mock_load_settings):
        mock_load_settings.return_value = self.mock_settings
        show_dir = os.path.join(self.series_dir, "Missing NFO Show")
        os.makedirs(show_dir)
        # NFO fehlt physisch, aber Video existiert
        with open(os.path.join(show_dir, "tvshow.nfo"), 'w') as f:
            f.write("<tvshow></tvshow>")
        with open(os.path.join(show_dir, "episode_without_nfo.mkv"), 'w') as f:
            f.write("video")

        # 1. Vorschau abfragen
        res_prev = self.client.post('/api/nas/fsk-batch/preview', json={
            "paths": [show_dir], "scope": "series", "new_fsk": "12"
        })
        self.assertEqual(res_prev.status_code, 200)

        # Suchen nach der fehlenden Episode-NFO
        missing_nfo_entry = None
        for f in res_prev.json["files"]:
            if "episode_without_nfo.nfo" in f["path"]:
                missing_nfo_entry = f
                break

        self.assertIsNotNone(missing_nfo_entry)
        self.assertEqual(missing_nfo_entry["status"], "skipped_missing")
        self.assertIsNone(missing_nfo_entry["fingerprint"])
        self.assertEqual(missing_nfo_entry["media_kind"], "episode")

        # 2. Ausführung mit korrekten fingerprint=null und status=skipped_missing -> muss klappen (wird übersprungen)
        res_app = self.client.post('/api/nas/fsk-batch/apply', json={
            "root_paths": [show_dir], "scope": "series", "new_fsk": "12", "files": res_prev.json["files"]
        })
        self.assertEqual(res_app.status_code, 200)
        self.assertTrue(res_app.json["ok"])
        self.assertEqual(res_app.json["summary"]["success"], 1) # Nur tvshow.nfo geändert

        # 3. Manipulation: Wenn wir den Client-Plan manipulieren (z. B. fälschlicherweise status='ready' eintragen) -> muss 409 geben
        res_prev2 = self.client.post('/api/nas/fsk-batch/preview', json={
            "paths": [show_dir], "scope": "series", "new_fsk": "12"
        })
        self.assertEqual(res_prev2.status_code, 200)

        manipulated_files = [dict(f) for f in res_prev2.json["files"]]
        for f in manipulated_files:
            if "episode_without_nfo.nfo" in f["path"]:
                f["status"] = "ready"
                f["fingerprint"] = {"size": 12, "mtime_ns": "123", "hash": "abc"}

        res_app_manip = self.client.post('/api/nas/fsk-batch/apply', json={
            "root_paths": [show_dir], "scope": "series", "new_fsk": "12", "files": manipulated_files
        })
        self.assertEqual(res_app_manip.status_code, 409)
        self.assertIn("fehlt plötzlich", res_app_manip.json["message"])

        # 4. Wenn wir den Eintrag der fehlenden NFO komplett aus dem Clientplan entfernen -> muss 409 geben
        removed_files = [f for f in res_prev2.json["files"] if "episode_without_nfo.nfo" not in f["path"]]
        res_app_rem = self.client.post('/api/nas/fsk-batch/apply', json={
            "root_paths": [show_dir], "scope": "series", "new_fsk": "12", "files": removed_files
        })
        self.assertEqual(res_app_rem.status_code, 409)
        self.assertIn("Zielmenge hat sich seit der Vorschau verändert", res_app_rem.json["message"])

    @patch('gui.api.nas_api.load_settings')
    def test_missing_tvshow_nfo_is_skipped_and_never_fsk_actionable(self, mock_load_settings):
        mock_load_settings.return_value = self.mock_settings
        show_dir = os.path.join(self.series_dir, "Serie ohne tvshow")
        season_dir = os.path.join(show_dir, "Staffel 1")
        os.makedirs(season_dir)
        with open(os.path.join(season_dir, "S01E01.mkv"), "w") as video_file:
            video_file.write("video")
        with open(os.path.join(season_dir, "S01E01.nfo"), "w") as nfo_file:
            nfo_file.write("<episodedetails><mpaa>FSK 12</mpaa></episodedetails>")

        response = self.client.post('/api/nas/fsk-batch/preview', json={
            "paths": [show_dir], "scope": "series", "new_fsk": "12"
        })

        self.assertEqual(response.status_code, 200)
        tvshow_entry = next(
            item for item in response.json["files"]
            if item["path"] == os.path.join(show_dir, "tvshow.nfo")
        )
        self.assertEqual(tvshow_entry["status"], "skipped_missing")
        self.assertIsNone(tvshow_entry["fingerprint"])
        self.assertEqual(tvshow_entry["media_kind"], "series")
        self.assertEqual(tvshow_entry["agent_path"], show_dir)

    @patch('gui.api.nas_api.load_settings')
    def test_season_nfo_is_rejected_in_movie_folder(self, mock_load_settings):
        mock_load_settings.return_value = self.mock_settings
        movie_dir = os.path.join(self.movies_dir, "Film mit season.nfo")
        os.makedirs(movie_dir)
        season_nfo = os.path.join(movie_dir, "season.nfo")
        with open(season_nfo, "w") as nfo_file:
            nfo_file.write("<season></season>")

        response = self.client.post('/api/nas/fsk-batch/preview', json={
            "paths": [season_nfo], "scope": "single", "new_fsk": "12"
        })

        self.assertEqual(response.status_code, 400)
        self.assertIn("NFO-Datei ist unzulässig", response.json["message"])

    @patch('gui.api.nas_api.write_fsk_to_nfo')
    @patch('gui.api.nas_api.load_settings')
    def test_same_count_race_condition_uses_same_season_root(
        self, mock_load_settings, mock_write_fsk
    ):
        mock_load_settings.return_value = self.mock_settings
        series_dir = os.path.join(self.series_dir, "Same Count Race Serie")
        season_dir = os.path.join(series_dir, "Staffel 1")
        os.makedirs(season_dir)
        with open(os.path.join(series_dir, "tvshow.nfo"), "w") as nfo_file:
            nfo_file.write("<tvshow></tvshow>")

        for episode in ("A", "B"):
            episode_dir = os.path.join(season_dir, episode)
            os.makedirs(episode_dir)
            for extension, content in ((".mkv", "video"), (".nfo", "<episode></episode>")):
                with open(os.path.join(episode_dir, episode + extension), "w") as media_file:
                    media_file.write(content)

        preview = self.client.post('/api/nas/fsk-batch/preview', json={
            "paths": [season_dir], "scope": "season", "new_fsk": "12"
        })
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(len(preview.json["files"]), 2)

        shutil.rmtree(os.path.join(season_dir, "A"))
        episode_c_dir = os.path.join(season_dir, "C")
        os.makedirs(episode_c_dir)
        with open(os.path.join(episode_c_dir, "C.mkv"), "w") as video_file:
            video_file.write("video")
        with open(os.path.join(episode_c_dir, "C.nfo"), "w") as nfo_file:
            nfo_file.write("<episode></episode>")

        apply_response = self.client.post('/api/nas/fsk-batch/apply', json={
            "root_paths": [season_dir],
            "scope": "season",
            "new_fsk": "12",
            "files": preview.json["files"],
        })

        self.assertEqual(apply_response.status_code, 409)
        mock_write_fsk.assert_not_called()

    def test_is_valid_series_root_uses_explicit_category_type(self):
        anime_root = os.path.join(self.nas_root, "Anime")
        anime_series = os.path.join(anime_root, "Ein Anime")
        os.makedirs(anime_series)
        settings = {
            "nas_root": self.nas_root,
            "sync_categories": [
                {"name": "Anime", "nas_sub": "/Anime", "type": "series"}
            ],
        }

        from gui.api.nas_api import is_valid_series_root

        self.assertTrue(is_valid_series_root(anime_series, settings))

    @patch('gui.api.nas_api.load_settings')
    def test_agent_path_for_flat_missing_episode_is_series_root(self, mock_load_settings):
        mock_load_settings.return_value = self.mock_settings
        series_dir = os.path.join(self.series_dir, "Flache Serie")
        os.makedirs(series_dir)
        with open(os.path.join(series_dir, "tvshow.nfo"), "w") as nfo_file:
            nfo_file.write("<tvshow></tvshow>")
        with open(os.path.join(series_dir, "S01E01.mkv"), "w") as video_file:
            video_file.write("video")

        response = self.client.post('/api/nas/fsk-batch/preview', json={
            "paths": [series_dir], "scope": "series", "new_fsk": "12"
        })

        self.assertEqual(response.status_code, 200)
        episode = next(
            item for item in response.json["files"]
            if item["path"].endswith("S01E01.nfo")
        )
        self.assertEqual(episode["status"], "skipped_missing")
        self.assertEqual(episode["agent_path"], series_dir)

    @patch('gui.api.nas_api.load_settings')
    def test_agent_path_for_nested_missing_episode_is_season_root(self, mock_load_settings):
        mock_load_settings.return_value = self.mock_settings
        series_dir = os.path.join(self.series_dir, "Verschachtelte Serie")
        season_dir = os.path.join(series_dir, "Staffel 2")
        episode_dir = os.path.join(season_dir, "S02E01")
        os.makedirs(episode_dir)
        with open(os.path.join(series_dir, "tvshow.nfo"), "w") as nfo_file:
            nfo_file.write("<tvshow></tvshow>")
        with open(os.path.join(episode_dir, "S02E01.mkv"), "w") as video_file:
            video_file.write("video")

        response = self.client.post('/api/nas/fsk-batch/preview', json={
            "paths": [season_dir], "scope": "season", "new_fsk": "12"
        })

        self.assertEqual(response.status_code, 200)
        episode = next(
            item for item in response.json["files"]
            if item["path"].endswith("S02E01.nfo")
        )
        self.assertEqual(episode["status"], "skipped_missing")
        self.assertEqual(episode["agent_path"], season_dir)

    @patch('gui.api.nas_api.load_settings')
    def test_existing_season_nfo_is_classified_without_agent_action(self, mock_load_settings):
        mock_load_settings.return_value = self.mock_settings
        series_dir = os.path.join(self.series_dir, "Serie mit season.nfo")
        season_dir = os.path.join(series_dir, "Season 03")
        os.makedirs(season_dir)
        with open(os.path.join(series_dir, "tvshow.nfo"), "w") as nfo_file:
            nfo_file.write("<tvshow></tvshow>")
        season_nfo = os.path.join(season_dir, "season.nfo")
        with open(season_nfo, "w") as nfo_file:
            nfo_file.write("<season></season>")

        response = self.client.post('/api/nas/fsk-batch/preview', json={
            "paths": [season_dir], "scope": "season", "new_fsk": "12"
        })

        self.assertEqual(response.status_code, 200)
        season_entry = next(
            item for item in response.json["files"]
            if item["path"] == season_nfo
        )
        self.assertEqual(season_entry["media_kind"], "season")
        self.assertNotIn("agent_path", season_entry)

    @patch('gui.api.nas_api.load_settings')
    def test_agent_path_never_climbs_above_series_root(self, mock_load_settings):
        mock_load_settings.return_value = self.mock_settings
        series_dir = os.path.join(self.series_dir, "Season 99")
        os.makedirs(series_dir)
        with open(os.path.join(series_dir, "tvshow.nfo"), "w") as nfo_file:
            nfo_file.write("<tvshow></tvshow>")
        with open(os.path.join(series_dir, "Episode.mkv"), "w") as video_file:
            video_file.write("video")

        response = self.client.post('/api/nas/fsk-batch/preview', json={
            "paths": [series_dir], "scope": "series", "new_fsk": "12"
        })

        self.assertEqual(response.status_code, 200)
        episode = next(
            item for item in response.json["files"]
            if item["path"].endswith("Episode.nfo")
        )
        self.assertEqual(episode["status"], "skipped_missing")
        self.assertEqual(episode["agent_path"], series_dir)

    @patch('gui.api.nas_api.load_settings')
    def test_agent_path_rejects_path_outside_category(self, mock_load_settings):
        mock_load_settings.return_value = self.mock_settings
        outside_dir = os.path.join(self.nas_root, "Outside")
        os.makedirs(outside_dir)
        outside_nfo = os.path.join(outside_dir, "Outside.nfo")
        with open(outside_nfo, "w") as nfo_file:
            nfo_file.write("<episode></episode>")
        with open(os.path.join(outside_dir, "Outside.mkv"), "w") as video_file:
            video_file.write("video")

        response = self.client.post('/api/nas/fsk-batch/preview', json={
            "paths": [outside_nfo], "scope": "single", "new_fsk": "12"
        })

        self.assertEqual(response.status_code, 400)
        self.assertNotIn("files", response.json)

    @patch('gui.api.nas_api.load_settings')
    def test_agent_path_rejects_symlink_breakout(self, mock_load_settings):
        mock_load_settings.return_value = self.mock_settings
        series_dir = os.path.join(self.series_dir, "Symlink Serie")
        os.makedirs(series_dir)
        outside_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, outside_dir, True)
        outside_nfo = os.path.join(outside_dir, "Outside.nfo")
        with open(outside_nfo, "w") as nfo_file:
            nfo_file.write("<episode></episode>")
        with open(os.path.join(outside_dir, "Outside.mkv"), "w") as video_file:
            video_file.write("video")
        symlink_dir = os.path.join(series_dir, "Staffel 1")
        os.symlink(outside_dir, symlink_dir)

        response = self.client.post('/api/nas/fsk-batch/preview', json={
            "paths": [os.path.join(symlink_dir, "Outside.nfo")],
            "scope": "single",
            "new_fsk": "12",
        })

        self.assertEqual(response.status_code, 403)
        self.assertNotIn("files", response.json)

if __name__ == '__main__':
    unittest.main()
