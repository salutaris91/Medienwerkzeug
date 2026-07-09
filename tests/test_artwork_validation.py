import sys
import os
import unittest
import unittest.mock
import json

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gui.core import artwork_validators
from gui.core import health
from gui.mw_metadata import fetch_tmdb_images

class TestArtworkValidation(unittest.TestCase):

    def test_factory_and_names(self):
        # Factory
        emby_val = artwork_validators.get_validator("emby")
        self.assertEqual(emby_val.server_name, "emby")
        self.assertTrue(emby_val.supports_banners)

        jelly_val = artwork_validators.get_validator("jellyfin")
        self.assertEqual(jelly_val.server_name, "jellyfin")

        plex_val = artwork_validators.get_validator("plex")
        self.assertEqual(plex_val.server_name, "plex")

        # Preferred names
        self.assertEqual(emby_val.get_preferred_movie_backdrop_name("movie.mkv"), "fanart.jpg")
        self.assertEqual(jelly_val.get_preferred_movie_backdrop_name("movie.mkv"), "backdrop.jpg")
        self.assertEqual(plex_val.get_preferred_movie_backdrop_name("movie.mkv"), "fanart.jpg")

        # Season posters
        self.assertEqual(emby_val.get_preferred_season_poster_name(1), "season01.jpg")
        self.assertIn("specials/folder.jpg", [x.lower() for x in emby_val.get_season_poster_names(0)])

    @unittest.mock.patch("urllib.request.urlopen")
    def test_fetch_tmdb_images_german_selection(self, mock_urlopen):
        # Setup mock TMDB images response
        mock_resp = unittest.mock.Mock()
        mock_resp.status = 200
        mock_data = {
            "posters": [
                {"file_path": "/eng_poster.jpg", "iso_639_1": "en"},
                {"file_path": "/ger_poster.jpg", "iso_639_1": "de"}
            ],
            "backdrops": [
                {"file_path": "/neutral_backdrop.jpg", "iso_639_1": None}
            ],
            "logos": [
                {"file_path": "/ger_logo.png", "iso_639_1": "de"},
                {"file_path": "/eng_logo.png", "iso_639_1": "en"}
            ]
        }
        mock_resp.read.return_value = json_bytes = json_str = bytes(json.dumps(mock_data), encoding="utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        # Temporarily set key so it runs
        with unittest.mock.patch("gui.mw_metadata.TMDB_API_KEY", "a" * 32):
            images = fetch_tmdb_images("movie", 123)

            # Assert German posters/logos and neutral backdrops are preferred
            self.assertEqual(images.get("poster"), "https://image.tmdb.org/t/p/original/ger_poster.jpg")
            self.assertEqual(images.get("backdrop"), "https://image.tmdb.org/t/p/original/neutral_backdrop.jpg")
            self.assertEqual(images.get("logo"), "https://image.tmdb.org/t/p/original/ger_logo.png")

    @unittest.mock.patch("os.path.exists")
    def test_get_provider_from_nfo(self, mock_exists):
        mock_exists.return_value = True
        mock_content = "<movie><title>Test</title><mw_provider>mediathek</mw_provider></movie>"

        with unittest.mock.patch("builtins.open", unittest.mock.mock_open(read_data=mock_content)):
            provider = health._get_provider_from_nfo("test.nfo")
            self.assertEqual(provider, "mediathek")

    @unittest.mock.patch("os.path.exists")
    @unittest.mock.patch("os.listdir")
    @unittest.mock.patch("os.walk")
    def test_check_movie_artwork_warnings(self, mock_walk, mock_listdir, mock_exists):
        # We test Emby validator missing logo & banner warnings
        issues = []
        val = artwork_validators.get_validator("emby")

        mock_listdir.return_value = ["movie.mkv", "movie.nfo"]
        mock_walk.return_value = [("/path/to/movie", [], ["movie.mkv", "movie.nfo"])]

        # Simulate: only movie.mkv and movie.nfo exist, NO poster, NO fanart, NO logo, NO banner
        # Also return True for NFO read mock
        mock_exists.side_effect = lambda path: path.endswith("movie.nfo") or path.endswith("movie.mkv")

        mock_content = "<movie><mw_provider>tmdb</mw_provider></movie>"
        with unittest.mock.patch("builtins.open", unittest.mock.mock_open(read_data=mock_content)):
            health._check_movie(issues, "Filme", "/path/to/movie", val)

            # Extract types of issues
            types = [i["type"] for i in issues]
            severities = {i["type"]: i["severity"] for i in issues}
            messages = {i["type"]: i["message"] for i in issues}

            self.assertIn("missing_poster", types)
            self.assertIn("missing_backdrop", types)
            self.assertIn("missing_logo", types)
            self.assertIn("missing_banner", types)

            self.assertEqual(severities["missing_poster"], "warning")
            self.assertEqual(severities["missing_logo"], "info")
            self.assertNotIn("unterstützt keine Logos", messages["missing_logo"])

    @unittest.mock.patch("os.path.exists")
    @unittest.mock.patch("os.listdir")
    @unittest.mock.patch("os.walk")
    def test_check_movie_artwork_warnings_suppressed_for_mediathek(self, mock_walk, mock_listdir, mock_exists):
        # We test Emby validator missing logo warnings with mediathek provider -> should add notice in message
        issues = []
        val = artwork_validators.get_validator("emby")

        mock_listdir.return_value = ["movie.mkv", "movie.nfo"]
        mock_walk.return_value = [("/path/to/movie", [], ["movie.mkv", "movie.nfo"])]
        mock_exists.side_effect = lambda path: path.endswith("movie.nfo") or path.endswith("movie.mkv")

        mock_content = "<movie><mw_provider>mediathek</mw_provider></movie>"
        with unittest.mock.patch("builtins.open", unittest.mock.mock_open(read_data=mock_content)):
            health._check_movie(issues, "Filme", "/path/to/movie", val)

            messages = {i["type"]: i["message"] for i in issues}
            self.assertIn("missing_logo", messages)
            self.assertIn("unterstützt keine Logos", messages["missing_logo"])

    def test_artwork_validators_regex(self):
        plex = artwork_validators.get_validator("plex")
        emby = artwork_validators.get_validator("emby")

        # Plex
        self.assertTrue(plex.matches_artwork_name("fanart-1.jpg", "fanart.jpg"))
        self.assertTrue(plex.matches_artwork_name("fanart.jpg", "fanart.jpg"))
        self.assertFalse(plex.matches_artwork_name("fanart1.jpg", "fanart.jpg"))
        self.assertFalse(plex.matches_artwork_name("fanart-.jpg", "fanart.jpg"))

        # Emby / Jellyfin
        self.assertTrue(emby.matches_artwork_name("fanart-1.jpg", "fanart.jpg"))
        self.assertTrue(emby.matches_artwork_name("fanart1.jpg", "fanart.jpg"))
        self.assertTrue(emby.matches_artwork_name("fanart_1.jpg", "fanart.jpg"))
        self.assertTrue(emby.matches_artwork_name("fanart.jpg", "fanart.jpg"))
        self.assertFalse(emby.matches_artwork_name("fanart-.jpg", "fanart.jpg"))
        self.assertFalse(emby.matches_artwork_name("fanart_.jpg", "fanart.jpg"))

    def test_emby_only_generates_one_backdrop(self):
        emby_val = artwork_validators.get_validator("emby")
        self.assertEqual(emby_val.get_preferred_movie_backdrop_name("movie.mkv"), "fanart.jpg")
        self.assertEqual(emby_val.get_preferred_series_backdrop_name(), "fanart.jpg")

    def test_jellyfin_prefers_backdrop(self):
        jelly_val = artwork_validators.get_validator("jellyfin")
        self.assertEqual(jelly_val.get_preferred_movie_backdrop_name("movie.mkv"), "backdrop.jpg")
        self.assertEqual(jelly_val.get_preferred_series_backdrop_name(), "backdrop.jpg")

    def test_existing_backdrop_recognized_by_emby(self):
        emby_val = artwork_validators.get_validator("emby")
        # If we have backdrop.jpg, has_artwork_file should return True for series backdrops
        with unittest.mock.patch("os.path.isdir", return_value=True), \
             unittest.mock.patch("os.listdir", return_value=["backdrop.jpg"]):
            has_backdrop = emby_val.has_artwork_file("/some/path", emby_val.get_series_backdrop_names())
            self.assertTrue(has_backdrop)

    def test_queue_import_whitelist(self):
        allowed_names = artwork_validators.get_all_allowed_metadata_names()
        self.assertIn("backdrop.jpg", allowed_names)
        self.assertIn("backdrop.png", allowed_names)
        self.assertIn("poster.jpg", allowed_names)
        self.assertIn("fanart.jpg", allowed_names)
        self.assertIn("folder.jpg", allowed_names)

    def test_sidecar_suffixes_list_contains_only_basename_bound(self):
        suffixes = artwork_validators.get_basename_sidecar_suffixes()
        # Should contain basename-bound suffixes
        self.assertIn("-fanart.jpg", suffixes)
        self.assertIn("-backdrop.jpg", suffixes)
        self.assertIn("-poster.jpg", suffixes)
        self.assertIn(".nfo", suffixes)

        # Should NOT contain standalone/folder-level names
        self.assertNotIn("fanart.jpg", suffixes)
        self.assertNotIn("backdrop.jpg", suffixes)
        self.assertNotIn("poster.jpg", suffixes)
        self.assertNotIn("folder.jpg", suffixes)

    @unittest.mock.patch("os.path.exists")
    @unittest.mock.patch("os.listdir")
    @unittest.mock.patch("os.walk")
    def test_check_movie_without_validator(self, mock_walk, mock_listdir, mock_exists):
        issues = []
        mock_listdir.return_value = ["movie.mkv", "movie.nfo"]
        mock_walk.return_value = [("/path/to/movie", [], ["movie.mkv", "movie.nfo"])]
        mock_exists.side_effect = lambda path: path.endswith("movie.nfo") or path.endswith("movie.mkv")

        mock_content = "<movie><mw_provider>tmdb</mw_provider></movie>"
        with unittest.mock.patch("builtins.open", unittest.mock.mock_open(read_data=mock_content)):
            health._check_movie(issues, "Filme", "/path/to/movie", None)

            # Es dürfen KEINE Artwork-Befunde entstehen, wenn validator=None ist
            types = [i["type"] for i in issues]
            self.assertNotIn("missing_poster", types)
            self.assertNotIn("missing_backdrop", types)
            self.assertNotIn("missing_logo", types)
            self.assertNotIn("missing_banner", types)

    @unittest.mock.patch("os.path.isdir")
    @unittest.mock.patch("os.path.exists")
    @unittest.mock.patch("os.listdir")
    @unittest.mock.patch("os.walk")
    def test_check_series_without_validator(self, mock_walk, mock_listdir, mock_exists, mock_isdir):
        issues = []

        def my_listdir(path):
            if "Staffel 01" in path:
                return ["episode1.mkv", "episode1.nfo"]
            return ["tvshow.nfo", "Staffel 01"]
        mock_listdir.side_effect = my_listdir

        mock_walk.return_value = [
            ("/path/to/series", ["Staffel 01"], ["tvshow.nfo"]),
            ("/path/to/series/Staffel 01", [], ["episode1.mkv", "episode1.nfo"])
        ]

        mock_exists.return_value = True
        mock_isdir.side_effect = lambda path: "Staffel 01" in path or path.endswith("series")

        mock_content = "<tvshow><mw_provider>tmdb</mw_provider></tvshow>"
        with unittest.mock.patch("builtins.open", unittest.mock.mock_open(read_data=mock_content)):
            health._check_series_show(issues, "Serien", "/path/to/series", None)

            # Es dürfen KEINE Artwork-Befunde entstehen, wenn validator=None ist
            types = [i["type"] for i in issues]
            self.assertNotIn("missing_poster", types)
            self.assertNotIn("missing_backdrop", types)
            self.assertNotIn("missing_logo", types)
            self.assertNotIn("missing_banner", types)
            self.assertNotIn("missing_season_poster", types)



if __name__ == "__main__":
    unittest.main()
