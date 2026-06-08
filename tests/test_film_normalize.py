import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

import gui.core.film_normalize as fn
import gui.core.trash as trash

class TestFilmNormalize(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.nas_root = os.path.join(self.temp_dir, "nas")
        os.makedirs(self.nas_root)
        
        # Erstelle eine Kategorie-Struktur
        self.movie_dir = os.path.join(self.nas_root, "Filme")
        os.makedirs(self.movie_dir)

        # Mocks für Settings und NAS Mount
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
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    @patch('gui.core.film_normalize.utils.load_settings')
    @patch('gui.core.film_normalize.ensure_nas_mounted')
    def test_build_plan_and_apply_moves(self, mock_mount, mock_settings):
        mock_mount.return_value = True
        mock_settings.return_value = self.settings

        # 1. Setup normaler Genre-Ordner: Filme/Action/Another Movie/Another Movie.mkv
        genre_dir = os.path.join(self.movie_dir, "Action")
        movie_genre_dir = os.path.join(genre_dir, "Another Movie")
        os.makedirs(movie_genre_dir)
        open(os.path.join(movie_genre_dir, "Another Movie.mkv"), 'w').close()

        # 2. Setup doppelt verschachtelter Ordner: Filme/My Movie/My Movie/My Movie.mkv + NFO
        nested_parent = os.path.join(self.movie_dir, "My Movie")
        nested_child = os.path.join(nested_parent, "My Movie")
        os.makedirs(nested_child)
        open(os.path.join(nested_child, "My Movie.mkv"), 'w').close()
        open(os.path.join(nested_child, "My Movie.nfo"), 'w').close()

        # Plan erstellen
        plan = fn.build_plan(self.settings)
        
        # Es sollten 2 Einträge im Plan sein
        self.assertEqual(len(plan), 2)
        
        # Finde nested und genre Einträge
        nested_item = next(it for it in plan if "Verschachtelung auflösen" in it["label"])
        genre_item = next(it for it in plan if "Action" in it["label"])
        
        self.assertIsNotNone(nested_item)
        self.assertIsNotNone(genre_item)
        
        # nested_item darf keinen Konflikt haben, obwohl der Elternpfad bereits existiert
        self.assertFalse(nested_item["conflict"])
        self.assertEqual(nested_item["dst"], nested_parent)
        
        # Mute trash.send_to_trash, da wir im Test kein echtes OS-Trash haben wollen,
        # wir leiten es einfach auf os.remove / rmtree um
        with patch('gui.core.film_normalize.trash.send_to_trash') as mock_trash:
            def fake_trash(path):
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
            mock_trash.side_effect = fake_trash

            # Moves anwenden
            results = fn.apply_moves(plan)
            
            self.assertEqual(results["moved"], 2)
            self.assertEqual(len(results["errors"]), 0)

        # Überprüfen, dass die Verschachtelung gelöst wurde
        self.assertTrue(os.path.exists(os.path.join(nested_parent, "My Movie.mkv")))
        self.assertTrue(os.path.exists(os.path.join(nested_parent, "My Movie.nfo")))
        # Der innere Ordner My Movie/My Movie sollte weg sein
        self.assertFalse(os.path.exists(nested_child))

        # Überprüfen, dass der Genre-Ordner Action verschoben wurde
        self.assertTrue(os.path.exists(os.path.join(self.movie_dir, "Another Movie", "Another Movie.mkv")))
        # Der leere Genre-Ordner Action sollte weg sein
        self.assertFalse(os.path.exists(genre_dir))

if __name__ == '__main__':
    unittest.main()
