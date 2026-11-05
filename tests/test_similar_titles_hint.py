"""Backend-Tests für den Ähnliche-Titel-Hinweis (Etappe E1: AK1–AK7, AK10, AK11–AK14, AK16, AK19)."""

from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch

import gui.core.persistence as persistence
import gui.core.utils as core_utils
from gui.core.similar_titles import (
    find_movie_folders_by_id,
    find_similar_movie_folders_by_name,
)


def _write_nfo(folder_path: Path, content: str, filename: str = "movie.nfo") -> None:
    folder_path.mkdir(parents=True, exist_ok=True)
    (folder_path / filename).write_text(content, encoding="utf-8")


class TestSimilarTitlesHint(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.tmp_path = Path(self.temp_dir.name)

        self.inbox_dir = self.tmp_path / "inbox"
        self.outbox_dir = self.tmp_path / "outbox"
        self.nas_root = self.tmp_path / "nas"
        self.movies_dir = self.nas_root / "Filme"
        self.series_dir = self.nas_root / "Serien"
        for directory in (self.inbox_dir, self.outbox_dir, self.movies_dir, self.series_dir):
            directory.mkdir(parents=True, exist_ok=True)

        env_patcher = patch.dict(
            os.environ,
            {
                "MW_SETTINGS_FILE": str(self.tmp_path / "settings.json"),
                "MW_JOBS_STATE_FILE": str(self.tmp_path / "jobs_state.json"),
                "MW_ENV_FILE": str(self.tmp_path / ".env"),
                "MW_DATA_DIR": str(self.tmp_path),
                "FLASK_SECRET_KEY": "test-secret-key-similar-titles",
            },
        )
        env_patcher.start()
        self.addCleanup(env_patcher.stop)

        for target_mod, attr_name in (
            (persistence, "_cached_settings"),
            (persistence, "_cached_settings_path"),
            (persistence, "_MOCK_SETTINGS"),
            (core_utils, "_MOCK_SETTINGS"),
        ):
            attr_patcher = patch.object(target_mod, attr_name, None)
            attr_patcher.start()
            self.addCleanup(attr_patcher.stop)

        persistence.save_settings(
            {
                "inbox_dir": str(self.inbox_dir),
                "outbox_dir": str(self.outbox_dir),
                "nas_root": str(self.nas_root),
                "media_server": "emby",
                "storage_targets": [
                    {"id": "nas", "type": "nas", "root_path": str(self.nas_root), "enabled": True}
                ],
                "sync_categories": [
                    {"id": "1", "name": "Filme", "nas_sub": "/Filme"},
                    {"id": "2", "name": "Serien", "nas_sub": "/Serien"},
                ],
            }
        )

        from gui.main import app

        cfg_patcher = patch.dict(
            app.config,
            {"TESTING": True, "SECRET_KEY": "test-secret-key-similar-titles"},
        )
        cfg_patcher.start()
        self.addCleanup(cfg_patcher.stop)

        self.client = app.test_client()
        persistence.set_password("test-password")
        login_res = self.client.post("/api/auth/login", json={"password": "test-password"})
        self.assertEqual(login_res.status_code, 200)
        cookie = self.client.get_cookie("mw_csrf_token")
        self.csrf_token = cookie.value if cookie else None
        self.assertIsNotNone(self.csrf_token)

    def _post_preview(self, payload: dict):
        return self.client.post(
            "/api/preview-process",
            json=payload,
            headers={"X-CSRF-Token": self.csrf_token},
        )

    def _create_inbox_movie(self, project: str = "Proj", filename: str = "film.mkv") -> Path:
        proj_dir = self.inbox_dir / project
        proj_dir.mkdir(parents=True, exist_ok=True)
        (proj_dir / filename).write_bytes(b"video-content")
        return proj_dir

    def test_ak1_stage1_id_match_and_nfo_variants(self):
        """AK1: Findet Ordner mit gleicher TMDb-ID unabhängig vom Ordnernamen und NFO-Dateinamen."""
        self._create_inbox_movie()
        cases = [
            ("tmdb", "movie.nfo", False),
            ("tmdb_movie", "X-Men - Der Film.nfo", False),
            ("tmdb", "xmen_cut.nfo", True),
        ]
        for provider, nfo_filename, with_video in cases:
            with self.subTest(provider=provider, nfo_filename=nfo_filename):
                nas_folder = self.movies_dir / "X-Men - Der Film"
                for existing in list(nas_folder.glob("*")) if nas_folder.exists() else []:
                    existing.unlink()
                _write_nfo(nas_folder, "<movie><tmdbid>3409</tmdbid></movie>", filename=nfo_filename)
                if with_video:
                    (nas_folder / "xmen_cut.mkv").write_bytes(b"vid")

                res = self._post_preview(
                    {
                        "media_type": "movie",
                        "project_name": "Proj",
                        "movie_name": "X-Men (2000)",
                        "movie_id": 3409,
                        "provider": provider,
                        "destination_id": "1",
                    }
                )
                self.assertEqual(res.status_code, 200)
                exact = res.get_json()["similar_existing"]["exact"]
                self.assertEqual(
                    exact,
                    [{"folder": "X-Men - Der Film", "relative_path": "X-Men - Der Film"}],
                )

    def test_ak2_excludes_target_folder_and_keeps_collision_warning(self):
        """AK2: Zielordner selbst bleibt in warning und wird aus exact ausgeschlossen."""
        self._create_inbox_movie()
        same_folder = self.movies_dir / "X-Men (2000)"
        _write_nfo(same_folder, "<movie><tmdbid>3409</tmdbid></movie>")
        (same_folder / "existing.mkv").write_bytes(b"existing-video")

        res = self._post_preview(
            {
                "media_type": "movie",
                "project_name": "Proj",
                "movie_name": "X-Men (2000)",
                "movie_id": "3409",
                "provider": "tmdb",
                "destination_id": "1",
                "copy_to_nas": True,
            }
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("warning", data)
        self.assertIn("X-Men (2000)", data["warning"])
        self.assertEqual(data["similar_existing"], {"exact": [], "similar": []})

    def test_ak3_no_matches_preserves_existing_preview_fields(self):
        """AK3: Ohne Treffer sind exact/similar leer und renames/subs/junk/destination intakt."""
        proj_dir = self._create_inbox_movie()
        (proj_dir / "film.srt").write_text("sub", encoding="utf-8")
        (proj_dir / "readme.txt").write_text("junk", encoding="utf-8")
        _write_nfo(self.movies_dir / "Matrix (1999)", "<movie><tmdbid>603</tmdbid></movie>")

        res = self._post_preview(
            {
                "media_type": "movie",
                "project_name": "Proj",
                "movie_name": "X-Men (2000)",
                "movie_id": "3409",
                "provider": "tmdb",
                "destination_id": "1",
            }
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["similar_existing"], {"exact": [], "similar": []})
        self.assertTrue(any(r.get("new") == "X-Men (2000).mkv" for r in data["renames"]))
        self.assertTrue(any(s.get("new") == "X-Men (2000).srt" for s in data["subs"]))
        self.assertIn("readme.txt", data["junk"])
        self.assertIn("X-Men (2000)", data["destination"])

    def test_ak4_skip_providers_and_missing_movie_id(self):
        """AK4: Nicht-TMDb-Provider oder fehlende movie_id überspringen Stufe 1 mit Log, Stufe 2 läuft."""
        self._create_inbox_movie()
        _write_nfo(self.movies_dir / "X-Men 2", "<movie><tmdbid>3409</tmdbid></movie>")

        cases = [
            ("manual", "3409"),
            ("mediathek", "3409"),
            ("ytdlp", "3409"),
            ("ytdlp_movie", "3409"),
            ("ofdb", "3409"),
            ("tmdb", None),
            ("tmdb", ""),
        ]
        for provider, movie_id in cases:
            with self.subTest(provider=provider, movie_id=movie_id):
                logs = []
                with patch("gui.core.similar_titles.log_message", side_effect=logs.append):
                    res = self._post_preview(
                        {
                            "media_type": "movie",
                            "project_name": "Proj",
                            "movie_name": "X-Men (2000)",
                            "movie_id": movie_id,
                            "provider": provider,
                            "destination_id": "1",
                        }
                    )
                self.assertEqual(res.status_code, 200)
                sim = res.get_json()["similar_existing"]
                self.assertEqual(sim["exact"], [])
                self.assertEqual([item["folder"] for item in sim["similar"]], ["X-Men 2"])
                self.assertTrue(any("Stufe-1-ID-Abgleich übersprungen" in entry for entry in logs))

    def test_ak5_genre_subfolder_depth_limit(self):
        """AK5: Treffer in 2. Ebene (Filme/Action/...) wird gefunden, 3. Ebene wird ignoriert."""
        _write_nfo(self.movies_dir / "Action" / "X-Men (2000)", "<movie><tmdbid>3409</tmdbid></movie>")
        _write_nfo(self.movies_dir / "Action" / "Marvel" / "X-Men Deep", "<movie><tmdbid>3409</tmdbid></movie>")
        (self.movies_dir / "SciFi" / "X-Men 2").mkdir(parents=True, exist_ok=True)
        (self.movies_dir / "SciFi" / "Deep" / "X-Men 3").mkdir(parents=True, exist_ok=True)

        exact = find_movie_folders_by_id(str(self.movies_dir), "tmdb", "3409", exclude_folder="X-Men Neu")
        self.assertEqual(exact, [{"folder": "X-Men (2000)", "relative_path": "Action/X-Men (2000)"}])

        similar = find_similar_movie_folders_by_name(
            str(self.movies_dir), "X-Men Neu", exclude_folders={"X-Men Neu", "X-Men (2000)"}
        )
        self.assertEqual([m["relative_path"] for m in similar], ["SciFi/X-Men 2"])

    def test_ak6_defective_nfo_is_skipped_and_scan_continues(self):
        """AK6: Defekte NFO bricht den Scan nicht ab, schreibt Log und liefert HTTP 200."""
        self._create_inbox_movie()
        _write_nfo(self.movies_dir / "Broken Movie", "<<<not valid xml and no tags>>>")
        _write_nfo(self.movies_dir / "X-Men - Der Film", "<movie><tmdbid>3409</tmdbid></movie>")

        logs = []
        with patch("gui.core.similar_titles.log_message", side_effect=logs.append):
            res = self._post_preview(
                {
                    "media_type": "movie",
                    "project_name": "Proj",
                    "movie_name": "X-Men (2000)",
                    "movie_id": "3409",
                    "provider": "tmdb",
                    "destination_id": "1",
                }
            )
        self.assertEqual(res.status_code, 200)
        exact = res.get_json()["similar_existing"]["exact"]
        self.assertEqual(exact, [{"folder": "X-Men - Der Film", "relative_path": "X-Men - Der Film"}])
        self.assertTrue(any("Broken Movie" in msg for msg in logs))

    def test_ak7_missing_nas_category_root_returns_empty_lists(self):
        """AK7: Nicht existenter Kategorie-Ordner liefert leere Listen und HTTP 200."""
        self._create_inbox_movie()
        missing_dir = self.tmp_path / "non_existent_nas"

        self.assertEqual(find_movie_folders_by_id(str(missing_dir), "tmdb", "3409"), [])
        self.assertEqual(find_similar_movie_folders_by_name(str(missing_dir), "X-Men"), [])

        res = self._post_preview(
            {
                "media_type": "movie",
                "project_name": "Proj",
                "movie_name": "X-Men (2000)",
                "movie_id": "3409",
                "provider": "tmdb",
                "destination": str(missing_dir / "Filme"),
            }
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["similar_existing"], {"exact": [], "similar": []})

    def test_ak10_tv_preview_remains_untouched(self):
        """AK10: Bei media_type == 'tv' wird similar_existing nicht gesetzt; TV-Warnungen bleiben intakt."""
        proj_dir = self.inbox_dir / "ShowProj"
        proj_dir.mkdir(parents=True, exist_ok=True)
        (proj_dir / "ep1.mkv").write_bytes(b"ep")

        show_dir = self.series_dir / "Show Alt"
        (show_dir / "Staffel 2024").mkdir(parents=True, exist_ok=True)
        _write_nfo(show_dir, "<tvshow><tmdbid>999</tmdbid><title>Show Alt</title></tvshow>", "tvshow.nfo")

        with patch(
            "gui.mw_metadata.fetch_tmdb_tv",
            side_effect=lambda show_id, season, lang: {"1": {"title": "Pilot"}},
        ):
            res = self._post_preview(
                {
                    "media_type": "tv",
                    "project_name": "ShowProj",
                    "show_name": "Show Neu",
                    "show_id": "999",
                    "provider": "tmdb_tv",
                    "season": "1",
                    "destination_id": "2",
                    "mappings": {"ep1.mkv": "1"},
                }
            )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertNotIn("similar_existing", data)
        self.assertIn("Abweichung der Nummerierung", data.get("warning", ""))
        self.assertEqual(data.get("show_name_mismatch"), {"nas_name": "Show Alt", "metadata_name": "Show Neu"})

    def test_ak11_caps_and_sorting(self):
        """AK11: 12 Namenstreffer werden auf 10 gekappt (sortiert nach overlap), 7 ID-Treffer auf 5."""
        self._create_inbox_movie()
        for idx in range(1, 8):
            _write_nfo(self.movies_dir / f"Exact Match {idx:02d}", "<movie><tmdbid>3409</tmdbid></movie>")
        for idx in range(1, 13):
            (self.movies_dir / f"Hobbit SpinOff {idx:02d}").mkdir(parents=True, exist_ok=True)
        (self.movies_dir / "Hobbit Abenteuer Reise").mkdir(parents=True, exist_ok=True)
        (self.movies_dir / "Unrelated Movie").mkdir(parents=True, exist_ok=True)

        logs = []
        with patch("gui.api.queue_api.log_message", side_effect=logs.append):
            res = self._post_preview(
                {
                    "media_type": "movie",
                    "project_name": "Proj",
                    "movie_name": "Hobbit Abenteuer (2012)",
                    "movie_id": "3409",
                    "provider": "tmdb",
                    "destination_id": "1",
                }
            )
        self.assertEqual(res.status_code, 200)
        sim = res.get_json()["similar_existing"]
        self.assertEqual(len(sim["exact"]), 5)
        self.assertEqual(len(sim["similar"]), 10)
        self.assertEqual(sim["similar"][0]["folder"], "Hobbit Abenteuer Reise")
        self.assertEqual(sim["similar"][0]["overlap"], 2)
        self.assertTrue(all(m["folder"] != "Unrelated Movie" for m in sim["similar"]))
        self.assertTrue(any("kappe auf 5" in entry for entry in logs))

    def test_ak12_ak13_ak14_name_heuristics(self):
        """AK12/AK13/AK14: Prüft Wortregel, Präfixregel, Leer-Guard, Allgemeinwörter und Release-Tags."""
        cases = [
            ("X-Men (2000)", "X-Men 2", True),
            ("X-Men Origins", "X-Men First Class", True),
            ("Hobbit", "Hobbits", True),
            ("300", "300 (2006)", True),
            ("Der Hobbit (2012) [1080p][GERMAN]", "Hobbit - Eine unerwartete Reise", True),
            ("Die X-Men Origins", "Iron Man", False),
            ("Night", "Nightcrawler", False),
            ("Nightcrawler", "Night", False),
            ("X-Men (2000)", "Teil 2", False),
            ("Teil 2", "X-Men (2000)", False),
        ]
        for idx, (query_title, folder_name, should_match) in enumerate(cases):
            with self.subTest(query_title=query_title, folder_name=folder_name):
                cat_dir = self.tmp_path / f"heur_{idx}"
                (cat_dir / folder_name).mkdir(parents=True, exist_ok=True)
                result = find_similar_movie_folders_by_name(str(cat_dir), query_title)
                self.assertEqual([item["folder"] for item in result], [folder_name] if should_match else [])

    def test_ak16_stage1_folder_excluded_from_stage2(self):
        """AK16: Ein Stufe-1-Treffer erscheint weder direkt noch im Endpoint zusätzlich in Stufe 2."""
        self._create_inbox_movie()
        _write_nfo(self.movies_dir / "X-Men - Der Film", "<movie><tmdbid>3409</tmdbid></movie>")
        (self.movies_dir / "X-Men 2").mkdir(parents=True, exist_ok=True)

        direct_similar = find_similar_movie_folders_by_name(
            str(self.movies_dir),
            "X-Men (2000)",
            exclude_folders={"X-Men (2000)", "X-Men - Der Film"},
        )
        self.assertEqual([m["folder"] for m in direct_similar], ["X-Men 2"])

        res = self._post_preview(
            {
                "media_type": "movie",
                "project_name": "Proj",
                "movie_name": "X-Men (2000)",
                "movie_id": "3409",
                "provider": "tmdb",
                "destination_id": "1",
            }
        )
        self.assertEqual(res.status_code, 200)
        sim = res.get_json()["similar_existing"]
        self.assertEqual([m["folder"] for m in sim["exact"]], ["X-Men - Der Film"])
        self.assertEqual([m["folder"] for m in sim["similar"]], ["X-Men 2"])

    def test_ak19_nfo_label_whitelist_skips_tvdb_labeled_nfo(self):
        """AK19: Ordner mit <tvdbid> (Label 'tvdb') wird trotz gleicher ID nicht als Stufe-1-Treffer gewertet."""
        _write_nfo(self.movies_dir / "TVDB Labeled Folder", "<movie><tvdbid>3409</tvdbid><tmdbid>3409</tmdbid></movie>")
        _write_nfo(self.movies_dir / "Valid TMDb Folder", "<movie><tmdbid>3409</tmdbid></movie>")

        logs = []
        with patch("gui.core.similar_titles.log_message", side_effect=logs.append):
            exact = find_movie_folders_by_id(str(self.movies_dir), "tmdb", "3409")
        self.assertEqual(exact, [{"folder": "Valid TMDb Folder", "relative_path": "Valid TMDb Folder"}])
        self.assertTrue(any("tvdb" in entry and "nicht in TMDb-Whitelist" in entry for entry in logs))

    def test_fix_ak1_expanded_stop_words_suppress_noise(self):
        """Es prüft, dass 'Men in Black 3 (2012)' Funktionswort-Rauschen ignoriert, aber 'Pitch.Black.2000' findet."""
        cat_dir = self.tmp_path / "mib_check"
        for name in ("In the Grey (2026)", "Doctor.Strange.in.the.Multiverse.of.Madness.2022", "Pitch.Black.2000"):
            (cat_dir / name).mkdir(parents=True, exist_ok=True)
        self.assertEqual(
            [m["folder"] for m in find_similar_movie_folders_by_name(str(cat_dir), "Men in Black 3 (2012)")],
            ["Pitch.Black.2000"],
        )

        stop_cases = [
            ("Men on Fire at Noon", "Girl on the Train at Night", False),
            ("Train to Busan for Men", "Road to Perdition for All", False),
            ("Dances with Wolves from Home", "Gone with Wind from Here", False),
            ("Stand by Me im Sommer", "Manchester by Sea im Winter", False),
            ("Auf der Flucht mit Stil", "Mord auf Ex mit Plan", False),
            ("Von Mäusen zu Menschen", "Mann von nebenan zu Gast", False),
            ("Für eine Handvoll Dollar", "Fuer immer Adaline", False),
            ("X-Men (2000)", "X-Men Apocalypse", True),
        ]
        for idx, (query_title, folder_name, should_match) in enumerate(stop_cases):
            with self.subTest(query_title=query_title, folder_name=folder_name):
                sub_dir = self.tmp_path / f"stop_{idx}"
                (sub_dir / folder_name).mkdir(parents=True, exist_ok=True)
                matches = find_similar_movie_folders_by_name(str(sub_dir), query_title)
                self.assertEqual([m["folder"] for m in matches], [folder_name] if should_match else [])

    def test_fix_ak2_special_unicode_cleaned_in_results_and_excludes(self):
        """Es prüft, dass Co/Cc/Cf/Cs-Sonderzeichen für Anzeige, Vergleich und Excludes bereinigt werden."""
        cat_dir = self.tmp_path / "unicode_check"
        raw_lvl1 = "Pitch Black (2000)\uf022"
        _write_nfo(cat_dir / raw_lvl1, "<movie><tmdbid>2787</tmdbid></movie>", filename="Pitch Black (2000).nfo")
        _write_nfo(cat_dir / "SciFi\u200b" / "Men in Black\uf022\x07", "<movie><tmdbid>607</tmdbid></movie>")

        self.assertEqual(
            find_movie_folders_by_id(str(cat_dir), "tmdb", "2787"),
            [{"folder": "Pitch Black (2000)", "relative_path": "Pitch Black (2000)"}],
        )
        self.assertEqual(
            find_movie_folders_by_id(str(cat_dir), "tmdb", "607"),
            [{"folder": "Men in Black", "relative_path": "SciFi/Men in Black"}],
        )
        similar = find_similar_movie_folders_by_name(str(cat_dir), "Men in Black 3 (2012)")
        self.assertEqual(
            [(m["folder"], m["relative_path"]) for m in similar],
            [("Men in Black", "SciFi/Men in Black"), ("Pitch Black (2000)", "Pitch Black (2000)")],
        )

        for excl in ("Pitch Black (2000)", raw_lvl1):
            with self.subTest(exclude=excl):
                self.assertEqual(find_movie_folders_by_id(str(cat_dir), "tmdb", "2787", exclude_folder=excl), [])
                sim_excl = find_similar_movie_folders_by_name(
                    str(cat_dir), "Men in Black 3 (2012)", exclude_folders={excl}
                )
                self.assertEqual([m["folder"] for m in sim_excl], ["Men in Black"])

    def test_fix_ak3_ak4_movie_subfolders_ignored_and_genre_folders_searched(self):
        """Es prüft, dass Unterordner von Filmordnern (Video/NFO) ignoriert und Genre-Ordner durchsucht werden."""
        for marker_file in ("Men in Black (1997).mkv", "movie.nfo"):
            with self.subTest(marker_file=marker_file):
                cat_dir = self.tmp_path / f"sub_check_{marker_file}"
                movie_dir = cat_dir / "Men in Black (1997)"
                sub_dir = movie_dir / "Men in Black (1997) Bonus"
                sub_dir.mkdir(parents=True, exist_ok=True)
                if marker_file.endswith(".nfo"):
                    _write_nfo(movie_dir, "<movie><tmdbid>607</tmdbid></movie>", filename=marker_file)
                else:
                    (movie_dir / marker_file).write_bytes(b"video")
                _write_nfo(sub_dir, "<movie><tmdbid>607</tmdbid></movie>")

                genre_movie = cat_dir / "Action" / "Pitch Black (2000)"
                _write_nfo(genre_movie, "<movie><tmdbid>2787</tmdbid></movie>")
                (genre_movie / "pitch_black.mp4").write_bytes(b"video")

                similar = find_similar_movie_folders_by_name(str(cat_dir), "Men in Black 3 (2012)")
                self.assertEqual(
                    [(m["folder"], m["relative_path"]) for m in similar],
                    [("Men in Black (1997)", "Men in Black (1997)"), ("Pitch Black (2000)", "Action/Pitch Black (2000)")],
                )
                expected_exact = (
                    [{"folder": "Men in Black (1997)", "relative_path": "Men in Black (1997)"}]
                    if marker_file.endswith(".nfo")
                    else []
                )
                self.assertEqual(find_movie_folders_by_id(str(cat_dir), "tmdb", "607"), expected_exact)
                self.assertEqual(
                    find_movie_folders_by_id(str(cat_dir), "tmdb", "2787"),
                    [{"folder": "Pitch Black (2000)", "relative_path": "Action/Pitch Black (2000)"}],
                )


if __name__ == "__main__":
    unittest.main()
