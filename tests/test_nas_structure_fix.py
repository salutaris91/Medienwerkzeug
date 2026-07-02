import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from gui.api.nas_api import nas_api
from flask import Flask

app = Flask(__name__)
app.register_blueprint(nas_api, url_prefix='/api')

class TestNasStructureFix(unittest.TestCase):
    def setUp(self):
        self.temp_dir = os.path.realpath(tempfile.mkdtemp())
        self.nas_root = os.path.join(self.temp_dir, "nas")
        os.makedirs(self.nas_root)

        self.movie_dir = os.path.join(self.nas_root, "Filme")
        os.makedirs(self.movie_dir)

        self.client = app.test_client()

        # Mock settings
        self.settings = {
            "nas_root": self.nas_root,
            "sync_categories": [
                {
                    "id": "movies",
                    "name": "Filme",
                    "nas_sub": "/Filme"
                }
            ]
        }
        self.patcher_settings = patch('gui.api.nas_api.load_settings', return_value=self.settings)
        self.patcher_settings.start()

    def tearDown(self):
        self.patcher_settings.stop()
        shutil.rmtree(self.temp_dir)

    def test_preview_simple_success(self):
        # Setup: Filme/Afterburn (2025)/Afterburn (2025)/Afterburn.mkv
        outer_dir = os.path.join(self.movie_dir, "Afterburn (2025)")
        inner_dir = os.path.join(outer_dir, "Afterburn (2025)")
        os.makedirs(inner_dir)

        video_file = os.path.join(inner_dir, "Afterburn.mkv")
        open(video_file, 'w').close()

        nfo_file = os.path.join(inner_dir, "movie.nfo")
        open(nfo_file, 'w').close()

        # POST Request an Preview-Endpoint
        resp = self.client.post('/api/nas/structure-fix/preview', json={"path": outer_dir})
        self.assertEqual(resp.status_code, 200)

        data = resp.get_json()
        self.assertTrue(data["ok"])
        self.assertTrue(data["safe"])
        self.assertEqual(data["outer_name"], "Afterburn (2025)")
        self.assertEqual(data["inner_name"], "Afterburn (2025)")
        self.assertEqual(len(data["files_to_move"]), 2)

        # Check relative paths
        rel_dsts = [f["rel_dst"] for f in data["files_to_move"]]
        self.assertIn("Afterburn.mkv", rel_dsts)
        self.assertIn("movie.nfo", rel_dsts)

        # Check trees
        self.assertIn("Afterburn (2025)/", data["current_tree"])
        self.assertIn("Afterburn (2025)/Afterburn (2025)/Afterburn.mkv", data["current_tree"])
        self.assertIn("Afterburn (2025)/Afterburn.mkv", data["target_tree"])

    def test_apply_simple_success(self):
        # Setup: Filme/Afterburn (2025)/Afterburn (2025)/Afterburn.mkv
        outer_dir = os.path.join(self.movie_dir, "Afterburn (2025)")
        inner_dir = os.path.join(outer_dir, "Afterburn (2025)")
        os.makedirs(inner_dir)

        video_file = os.path.join(inner_dir, "Afterburn.mkv")
        open(video_file, 'w').close()

        # Mock trash.send_to_trash, da wir keine echte Quarantäne im Test wollen
        with patch('gui.api.nas_api.trash.send_to_trash') as mock_trash:
            # POST Request an Apply-Endpoint
            resp = self.client.post('/api/nas/structure-fix/apply', json={"path": outer_dir})
            self.assertEqual(resp.status_code, 200)

            data = resp.get_json()
            self.assertTrue(data["ok"])
            self.assertEqual(len(data["moved_files"]), 1)
            self.assertIn("Afterburn.mkv", data["moved_files"])

            # Verifizieren, dass die Datei verschoben wurde
            self.assertTrue(os.path.exists(os.path.join(outer_dir, "Afterburn.mkv")))
            # Der innere Ordner sollte quarantänisiert worden sein
            mock_trash.assert_called_once_with(inner_dir, force=True)

    def test_prevent_fix_if_target_file_exists(self):
        # Setup: Filme/Afterburn (2025)/Afterburn (2025)/Afterburn.mkv
        # Aber im äußeren Ordner existiert Afterburn.mkv bereits!
        outer_dir = os.path.join(self.movie_dir, "Afterburn (2025)")
        inner_dir = os.path.join(outer_dir, "Afterburn (2025)")
        os.makedirs(inner_dir)

        open(os.path.join(inner_dir, "Afterburn.mkv"), 'w').close()
        open(os.path.join(outer_dir, "Afterburn.mkv"), 'w').close() # Kollision

        # Preview
        resp = self.client.post('/api/nas/structure-fix/preview', json={"path": outer_dir})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertFalse(data["safe"])
        self.assertTrue(any("existiert bereits" in c for c in data["conflicts"]))

        # Apply must fail
        resp = self.client.post('/api/nas/structure-fix/apply', json={"path": outer_dir})
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data["ok"])
        self.assertIn("Sicherheitsprüfung fehlgeschlagen", data["message"])

    def test_prevent_fix_if_outer_folder_has_own_media(self):
        # Setup: Filme/Afterburn (2025)/Afterburn (2025)/Afterburn.mkv
        # Und im äußeren Ordner liegt eine andere Videodatei: Filme/Afterburn (2025)/other.mkv
        outer_dir = os.path.join(self.movie_dir, "Afterburn (2025)")
        inner_dir = os.path.join(outer_dir, "Afterburn (2025)")
        os.makedirs(inner_dir)

        open(os.path.join(inner_dir, "Afterburn.mkv"), 'w').close()
        open(os.path.join(outer_dir, "other.mkv"), 'w').close() # Andere Mediendatei im äußeren Ordner

        # Preview
        resp = self.client.post('/api/nas/structure-fix/preview', json={"path": outer_dir})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertFalse(data["safe"])
        self.assertTrue(any("eigene Mediendateien" in c for c in data["conflicts"]))

        # Apply must fail
        resp = self.client.post('/api/nas/structure-fix/apply', json={"path": outer_dir})
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data["ok"])

    def test_prevent_fix_outside_allowed_roots(self):
        # Setup in temp_dir, das NICHT unter nas_root liegt
        external_dir = os.path.join(self.temp_dir, "External Movie")
        inner_dir = os.path.join(external_dir, "External Movie")
        os.makedirs(inner_dir)
        open(os.path.join(inner_dir, "movie.mkv"), 'w').close()

        # Preview
        resp = self.client.post('/api/nas/structure-fix/preview', json={"path": external_dir})
        self.assertEqual(resp.status_code, 403)
        data = resp.get_json()
        self.assertFalse(data["ok"])
        self.assertIn("Pfad liegt außerhalb des NAS", data["message"])

        # Apply must fail
        resp = self.client.post('/api/nas/structure-fix/apply', json={"path": external_dir})
        self.assertEqual(resp.status_code, 403)
        data = resp.get_json()
        self.assertFalse(data["ok"])

    def test_preview_genre_container_success(self):
        # Setup: Filme/Action/Film A (2024)/Film A.mkv
        # und Filme/Action/Film B (2023)/Film B.mkv
        action_dir = os.path.join(self.movie_dir, "Action")
        film_a_dir = os.path.join(action_dir, "Film A (2024)")
        film_b_dir = os.path.join(action_dir, "Film B (2023)")
        os.makedirs(film_a_dir)
        os.makedirs(film_b_dir)

        open(os.path.join(film_a_dir, "Film A.mkv"), 'w').close()
        open(os.path.join(film_b_dir, "Film B.mkv"), 'w').close()

        # Preview
        resp = self.client.post('/api/nas/structure-fix/preview', json={"path": action_dir})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["ok"])
        self.assertTrue(data["safe"])
        self.assertEqual(data["type_id"], "genre_container")
        self.assertEqual(len(data["items_to_move"]), 2)

        # Überprüfe die relativen Pfade
        rel_dsts = [f["rel_dst"] for f in data["items_to_move"]]
        self.assertIn("Film A (2024)", rel_dsts)
        self.assertIn("Film B (2023)", rel_dsts)

        # Überprüfe die Tree-Visualisierung
        self.assertIn("Action/", data["current_tree"])
        self.assertIn("Action/Film A (2024)/", data["current_tree"])
        self.assertIn("Film A (2024)/", data["target_tree"])

    def test_apply_genre_container_success(self):
        # Setup: Filme/Action/Film A (2024)/Film A.mkv
        action_dir = os.path.join(self.movie_dir, "Action")
        film_a_dir = os.path.join(action_dir, "Film A (2024)")
        os.makedirs(film_a_dir)
        open(os.path.join(film_a_dir, "Film A.mkv"), 'w').close()

        with patch('gui.api.nas_api.trash.send_to_trash') as mock_trash:
            # Apply
            resp = self.client.post('/api/nas/structure-fix/apply', json={"path": action_dir})
            self.assertEqual(resp.status_code, 200)

            data = resp.get_json()
            self.assertTrue(data["ok"])
            self.assertIn("Film A (2024)", data["moved_files"])

            # Verifizieren, dass Film A (2024) jetzt in Filme/ liegt
            self.assertTrue(os.path.exists(os.path.join(self.movie_dir, "Film A (2024)", "Film A.mkv")))
            # Der Action-Sammelordner selbst sollte quarantänisiert worden sein
            mock_trash.assert_called_once_with(action_dir, force=True)

    def test_prevent_genre_fix_in_series_category(self):
        # Setup: Ein Sammelordner in einer Serien-Kategorie
        series_dir = os.path.join(self.nas_root, "Serien")
        os.makedirs(series_dir)
        action_series_dir = os.path.join(series_dir, "Action")
        show_dir = os.path.join(action_series_dir, "Show A")
        os.makedirs(show_dir)
        open(os.path.join(show_dir, "S01E01.mkv"), 'w').close()

        # Update settings to include a series category
        self.settings["sync_categories"].append({
            "id": "series",
            "name": "Serien",
            "nas_sub": "/Serien"
        })

        # Preview
        resp = self.client.post('/api/nas/structure-fix/preview', json={"path": action_series_dir})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertFalse(data["safe"])
        self.assertTrue(any("Serien-Kategorien nicht unterstützt" in c for c in data["conflicts"]))

    def test_prevent_genre_fix_if_target_exists(self):
        # Setup: Filme/Action/Film A (2024)/Film A.mkv
        # Aber im Ziel Filme/Film A (2024) existiert bereits ein Ordner!
        action_dir = os.path.join(self.movie_dir, "Action")
        film_a_dir = os.path.join(action_dir, "Film A (2024)")
        os.makedirs(film_a_dir)
        open(os.path.join(film_a_dir, "Film A.mkv"), 'w').close()

        # Kollidierender Zielordner
        os.makedirs(os.path.join(self.movie_dir, "Film A (2024)"))

        # Preview
        resp = self.client.post('/api/nas/structure-fix/preview', json={"path": action_dir})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertFalse(data["safe"])
        self.assertTrue(any("existiert bereits" in c for c in data["conflicts"]))

    def test_prevent_genre_fix_if_outer_has_videos(self):
        # Setup: Filme/Action/Film A (2024)/Film A.mkv
        # Aber im Sammelordner Action liegt direkt ein Video!
        action_dir = os.path.join(self.movie_dir, "Action")
        film_a_dir = os.path.join(action_dir, "Film A (2024)")
        os.makedirs(film_a_dir)
        open(os.path.join(film_a_dir, "Film A.mkv"), 'w').close()

        open(os.path.join(action_dir, "loose.mkv"), 'w').close()

        # Preview
        resp = self.client.post('/api/nas/structure-fix/preview', json={"path": action_dir})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertFalse(data["safe"])
        self.assertTrue(any("eigene Mediendateien" in c for c in data["conflicts"]))

        # Apply must fail
        resp = self.client.post('/api/nas/structure-fix/apply', json={"path": action_dir})
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data["ok"])
        self.assertIn("Sicherheitsprüfung fehlgeschlagen", data["message"])

    def test_prevent_genre_fix_if_non_movie_subdir_exists(self):
        # Setup: Filme/Action/Film A (2024)/Film A.mkv
        # und zusätzlich ein nicht-medialer Unterordner Action/Extras
        action_dir = os.path.join(self.movie_dir, "Action")
        film_a_dir = os.path.join(action_dir, "Film A (2024)")
        extras_dir = os.path.join(action_dir, "Extras")
        os.makedirs(film_a_dir)
        os.makedirs(extras_dir)

        open(os.path.join(film_a_dir, "Film A.mkv"), 'w').close()

        # Preview
        resp = self.client.post('/api/nas/structure-fix/preview', json={"path": action_dir})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertFalse(data["safe"])
        self.assertTrue(any("keine Videodateien" in c for c in data["conflicts"]))

        # Apply must fail
        resp = self.client.post('/api/nas/structure-fix/apply', json={"path": action_dir})
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data["ok"])

    def test_apply_genre_container_warning_if_not_empty(self):
        # Setup: Filme/Action/Film A (2024)/Film A.mkv
        # Und zusätzlich eine übrig bleibende Datei im Sammelordner: Filme/Action/readme.txt
        action_dir = os.path.join(self.movie_dir, "Action")
        film_a_dir = os.path.join(action_dir, "Film A (2024)")
        os.makedirs(film_a_dir)
        open(os.path.join(film_a_dir, "Film A.mkv"), 'w').close()

        # readme.txt direkt im Sammelordner (kein Video, aber wir legen es an)
        open(os.path.join(action_dir, "readme.txt"), 'w').close()

        with patch('gui.api.nas_api.trash.send_to_trash') as mock_trash:
            # Apply
            resp = self.client.post('/api/nas/structure-fix/apply', json={"path": action_dir})
            self.assertEqual(resp.status_code, 200)

            data = resp.get_json()
            self.assertTrue(data["ok"])
            self.assertTrue(any("nicht in Quarantäne verschoben" in w for w in data["warnings"]))
            self.assertIn("readme.txt", data["message"])

            # Quarantäne sollte nicht aufgerufen worden sein, da readme.txt noch existiert
            mock_trash.assert_not_called()
