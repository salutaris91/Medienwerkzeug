import unittest
from unittest.mock import patch
import urllib.request
import urllib.parse

from gui.mw_metadata import check_tmdb_auth_method, make_tmdb_request, MetadataProviderUnavailable
import gui.mw_metadata

class TestTmdBAuth(unittest.TestCase):
    def setUp(self):
        # Save original API Key value
        self.original_key = gui.mw_metadata.TMDB_API_KEY

    def tearDown(self):
        # Restore original API Key value
        gui.mw_metadata.TMDB_API_KEY = self.original_key

    def test_v3_hex_key_detection(self):
        # A valid v3 key is a 32-character hex string
        fake_v3 = "1234567890abcdef1234567890abcdef"
        gui.mw_metadata.TMDB_API_KEY = fake_v3
        
        method, key = check_tmdb_auth_method()
        self.assertEqual(method, 'v3')
        self.assertEqual(key, fake_v3)

    def test_v4_jwt_key_detection(self):
        # A valid v4 key starts with eyJ, contains dots, and is long
        fake_v4 = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJhM2Q5..." + "a" * 20
        gui.mw_metadata.TMDB_API_KEY = fake_v4
        
        method, key = check_tmdb_auth_method()
        self.assertEqual(method, 'v4')
        self.assertEqual(key, fake_v4)

    def test_empty_key_error(self):
        gui.mw_metadata.TMDB_API_KEY = ""
        with self.assertRaises(MetadataProviderUnavailable) as ctx:
            check_tmdb_auth_method()
        self.assertIn("ist nicht konfiguriert", str(ctx.exception))
        self.assertEqual(ctx.exception.status_code, 502)

    def test_invalid_key_format_error(self):
        # Not empty, but not 32 chars hex, and not containing dots/length > 50
        gui.mw_metadata.TMDB_API_KEY = "short_invalid"
        with self.assertRaises(MetadataProviderUnavailable) as ctx:
            check_tmdb_auth_method()
        self.assertIn("Ungueltiges Format", str(ctx.exception))
        self.assertEqual(ctx.exception.status_code, 502)

    def test_make_tmdb_request_v3(self):
        fake_v3 = "a" * 32
        gui.mw_metadata.TMDB_API_KEY = fake_v3
        url = "https://api.themoviedb.org/3/movie/123?api_key=original_param&language=de-DE"
        
        req = make_tmdb_request(url)
        self.assertIsInstance(req, urllib.request.Request)
        
        # Verify URL is unmodified regarding api_key (since it's v3, we keep original URL with param)
        self.assertEqual(req.full_url, url)
        # Verify no Authorization header is added
        self.assertNotIn('Authorization', req.headers)

    def test_make_tmdb_request_v4(self):
        fake_v4 = "eyJ.fake.payload.signature" + "a" * 50
        gui.mw_metadata.TMDB_API_KEY = fake_v4
        url = "https://api.themoviedb.org/3/movie/123?api_key=to_be_stripped&language=de-DE&append_to_response=credits"
        
        req = make_tmdb_request(url)
        self.assertIsInstance(req, urllib.request.Request)
        
        # Parse the output URL to verify api_key query param is removed, but others are kept
        parsed = urllib.parse.urlparse(req.full_url)
        params = dict(urllib.parse.parse_qsl(parsed.query))
        
        self.assertNotIn('api_key', params)
        self.assertEqual(params.get('language'), 'de-DE')
        self.assertEqual(params.get('append_to_response'), 'credits')
        
        # Verify Authorization header is set correctly
        self.assertEqual(req.headers.get('Authorization'), f'Bearer {fake_v4}')

if __name__ == "__main__":
    unittest.main()
