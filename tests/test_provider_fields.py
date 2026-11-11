"""Tests for unmerged multi-provider metadata comparison (E4-AK1) and partial-failure resilience (E4-AK2)."""

import unittest
from unittest.mock import patch

from flask import Flask

from gui import mw_metadata
from gui.api.search_api import search_api


class TestProviderFields(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.register_blueprint(search_api, url_prefix="/api")
        self.client = self.app.test_client()

    def test_e4_ak1_fetch_movie_comparison_data_returns_unmerged_fields_per_provider(self):
        """E4-AK1: Provider fetch returns fields per provider instead of pre-merged (TMDb without FSK, OFDb without Plot)."""
        def fake_fetch_movie_nfo_data(provider, movie_id):
            if provider == "tmdb":
                return {
                    "title": "Killing Faith",
                    "year": "2025",
                    "plot": "Ein Arzt begleitet eine Mutter durch die Wüste.",
                    "fsk": "",
                    "genres": ["Western", "Drama"],
                }
            if provider == "ofdb":
                return {
                    "title": "Killing Faith - Die letzte Versuchung",
                    "year": "2025",
                    "plot": "",
                    "fsk": "16",
                    "genres": ["Thriller", "Drama"],
                }
            raise AssertionError(f"Unexpected provider: {provider}")

        with patch.object(mw_metadata, "fetch_movie_nfo_data", side_effect=fake_fetch_movie_nfo_data):
            response = self.client.post(
                "/api/metadata/fetch?media_type=movie&provider=tmdb&movie_id=1200320",
                json={
                    "media_type": "movie",
                    "providers": [
                        {"provider": "tmdb", "movie_id": "1200320"},
                        {"provider": "ofdb", "movie_id": "ofdb_391234_Killing-Faith"},
                    ],
                },
            )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["provider_order"], ["tmdb", "ofdb"])
        self.assertIn("tmdb", data["providers"])
        self.assertIn("ofdb", data["providers"])

        tmdb_entry = data["providers"]["tmdb"]
        self.assertEqual(tmdb_entry["status"], "ok")
        self.assertIsNone(tmdb_entry["error"])
        self.assertEqual(tmdb_entry["fields"], {
            "title": "Killing Faith",
            "year": "2025",
            "plot": "Ein Arzt begleitet eine Mutter durch die Wüste.",
            "fsk": "",
            "genres": ["Western", "Drama"],
        })

        ofdb_entry = data["providers"]["ofdb"]
        self.assertEqual(ofdb_entry["status"], "ok")
        self.assertIsNone(ofdb_entry["error"])
        self.assertEqual(ofdb_entry["fields"], {
            "title": "Killing Faith - Die letzte Versuchung",
            "year": "2025",
            "plot": "",
            "fsk": "16",
            "genres": ["Thriller", "Drama"],
        })

    def test_e4_ak2_partial_provider_failure_keeps_other_provider_selectable(self):
        """E4-AK2: Failure of one provider marks only that provider as error while keeping the other provider's fields intact."""
        def fake_fetch_movie_nfo_data(provider, movie_id):
            if provider == "tmdb":
                return {
                    "title": "Matrix",
                    "year": "1999",
                    "plot": "Neo entdeckt die Matrix.",
                    "fsk": "16",
                    "genres": ["Action", "Science Fiction"],
                }
            if provider == "ofdb":
                return {
                    "title": "",
                    "year": "",
                    "plot": "",
                    "fsk": "",
                    "genres": [],
                    "error": "OFDb-Filmmetadaten konnten nicht geladen werden: timed out",
                }
            raise AssertionError(f"Unexpected provider: {provider}")

        with patch.object(mw_metadata, "fetch_movie_nfo_data", side_effect=fake_fetch_movie_nfo_data):
            response = self.client.post(
                "/api/metadata/fetch",
                json={
                    "media_type": "movie",
                    "providers": [
                        {"provider": "tmdb_movie", "id": "603"},
                        {"provider": "ofdb", "id": "ofdb_154_Die-Matrix"},
                    ],
                },
            )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["provider_order"], ["tmdb", "ofdb"])
        self.assertEqual(data["providers"]["tmdb"]["status"], "ok")
        self.assertEqual(data["providers"]["tmdb"]["fields"]["title"], "Matrix")
        self.assertEqual(data["providers"]["tmdb"]["fields"]["fsk"], "16")

        self.assertEqual(data["providers"]["ofdb"]["status"], "error")
        self.assertIn("OFDb-Filmmetadaten konnten nicht geladen werden", data["providers"]["ofdb"]["error"])
        self.assertEqual(data["providers"]["ofdb"]["fields"], {
            "title": "",
            "year": "",
            "plot": "",
            "fsk": "",
            "genres": [],
        })

    def test_single_provider_legacy_endpoint_remains_backwards_compatible(self):
        """Option 3A: Calling /api/metadata/fetch without 'providers' returns the flat single-provider dict."""
        fake_single = {
            "title": "Blade Runner",
            "year": "1982",
            "plot": "Replikanten in Los Angeles.",
            "fsk": "16",
            "genres": ["Sci-Fi", "Thriller"],
        }
        with patch.object(mw_metadata, "fetch_movie_nfo_data", return_value=fake_single) as mock_fn:
            response = self.client.get("/api/metadata/fetch?media_type=movie&provider=tmdb&movie_id=78")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), fake_single)
        mock_fn.assert_called_once_with("tmdb", "78")


if __name__ == "__main__":
    unittest.main()
