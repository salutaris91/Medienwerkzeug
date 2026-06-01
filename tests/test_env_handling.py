import os
import unittest
import json
import tempfile
from unittest.mock import patch
from flask import Flask

# Import the blueprint
from gui.api.system_api import system_api
from gui.core.persistence import load_env_keys, save_env_keys, is_masked, mask_credential

class TestEnvHandling(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.env_path = os.path.join(self.test_dir.name, ".env")
        self.settings_path = os.path.join(self.test_dir.name, "settings.json")
        os.environ["MW_ENV_FILE"] = self.env_path
        os.environ["MW_SETTINGS_FILE"] = self.settings_path
        
        os.environ.pop("TMDB_API_KEY", None)
        os.environ.pop("TVDB_API_KEY", None)
        
        self.app = Flask(__name__)
        self.app.register_blueprint(system_api, url_prefix='/api')
        self.client = self.app.test_client()

    def tearDown(self):
        self.test_dir.cleanup()
        os.environ.pop("MW_ENV_FILE", None)
        os.environ.pop("MW_SETTINGS_FILE", None)
        os.environ.pop("TMDB_API_KEY", None)
        os.environ.pop("TVDB_API_KEY", None)
        from gui.core.persistence import _cached_settings
        import gui.core.persistence as p
        p._cached_settings = None

    def test_env_parsing_and_saving(self):
        save_env_keys({"TMDB_API_KEY": "test1234", "FOO": "bar"})
        keys = load_env_keys()
        self.assertEqual(keys.get("TMDB_API_KEY"), "test1234")
        self.assertEqual(os.environ.get("TMDB_API_KEY"), "test1234")
        
        save_env_keys({"TMDB_API_KEY": ""})
        self.assertNotIn("TMDB_API_KEY", load_env_keys())
        self.assertNotIn("TMDB_API_KEY", os.environ)

    def test_masking_mechanisms(self):
        self.assertEqual(mask_credential("1234567890"), "****7890")
        self.assertTrue(is_masked("****7890"))
        self.assertFalse(is_masked("12345678"))
        self.assertEqual(mask_credential(""), "")
        self.assertFalse(is_masked(""))

    def test_api_protection(self):
        # 1. Post a real key
        response = self.client.post('/api/settings', json={
            "tmdb_api_key": "my_real_tmdb_key",
            "telegram_token": "my_real_tg_token"
        })
        self.assertEqual(response.status_code, 200)
        
        # Verify it's loaded in env
        self.assertEqual(os.environ.get("TMDB_API_KEY"), "my_real_tmdb_key")
        
        # 2. Get settings, should be masked
        response = self.client.get('/api/settings')
        data = response.get_json()
        self.assertTrue(data["tmdb_api_key"].startswith("****"))
        self.assertTrue(data["telegram_token"].startswith("****"))
        
        # 3. Post back the masked keys
        response = self.client.post('/api/settings', json={
            "tmdb_api_key": data["tmdb_api_key"],
            "telegram_token": data["telegram_token"],
            "dummy_setting": True # Change something else
        })
        self.assertEqual(response.status_code, 200)
        
        # Verify real keys are intact
        self.assertEqual(os.environ.get("TMDB_API_KEY"), "my_real_tmdb_key")
        
        from gui.core.persistence import load_settings
        settings = load_settings()
        self.assertEqual(settings["telegram_token"], "my_real_tg_token")
        self.assertEqual(settings["dummy_setting"], True)

    def test_metadata_reload(self):
        import gui.mw_metadata as mw
        # Initial is empty
        mw.reload_metadata_keys()
        self.assertEqual(mw.TMDB_API_KEY, "")
        
        # Save a key
        save_env_keys({"TMDB_API_KEY": "reloaded_key"})
        mw.reload_metadata_keys()
        self.assertEqual(mw.TMDB_API_KEY, "reloaded_key")

if __name__ == "__main__":
    unittest.main()
