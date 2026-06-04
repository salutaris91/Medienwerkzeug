import os
import unittest
import tempfile
import json
import time
from unittest.mock import patch, MagicMock
from flask import session

class TestOnboarding(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.settings_file = os.path.join(self.temp_dir.name, "settings.json")
        self.jobs_state_file = os.path.join(self.temp_dir.name, "jobs_state.json")
        self.env_file = os.path.join(self.temp_dir.name, ".env")

        # Inject environment variables to force isolation
        os.environ["MW_SETTINGS_FILE"] = self.settings_file
        os.environ["MW_JOBS_STATE_FILE"] = self.jobs_state_file
        os.environ["MW_ENV_FILE"] = self.env_file
        os.environ["MW_DATA_DIR"] = self.temp_dir.name
        os.environ["FLASK_SECRET_KEY"] = "test-secret-key-onboarding"
        os.environ["MW_ONBOARDING_TEST"] = "1"

        # Import persistence and reset cache
        import gui.core.persistence as persistence
        self.persistence = persistence
        self.persistence._cached_settings = None

        # Load dynamic flask app
        from gui.main import app
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key-onboarding'
        self.app = app
        self.client = app.test_client()

    def tearDown(self):
        os.environ.pop("MW_SETTINGS_FILE", None)
        os.environ.pop("MW_JOBS_STATE_FILE", None)
        os.environ.pop("MW_ENV_FILE", None)
        os.environ.pop("MW_DATA_DIR", None)
        os.environ.pop("FLASK_SECRET_KEY", None)
        os.environ.pop("MW_ONBOARDING_TEST", None)
        self.temp_dir.cleanup()

    def test_migration_logic(self):
        """Verifies settings migration for onboarding on new vs existing setups."""
        # Case A: Fresh setup (file does not exist)
        self.persistence._cached_settings = None
        settings = self.persistence.load_settings()
        self.assertFalse(settings["onboarded"])
        self.assertIsNone(settings["onboarding_completed_at"])

        # Case B: Existing setup (file exists without onboarded flag)
        self.persistence._cached_settings = None
        with open(self.settings_file, "w", encoding="utf-8") as f:
            json.dump({"media_server": "plex", "inbox_dir": "/some/path"}, f)

        settings = self.persistence.load_settings()
        self.assertTrue(settings["onboarded"])
        self.assertEqual(settings["media_server"], "plex")

    def test_middleware_blocking(self):
        """Checks that non-setup endpoints are blocked when onboarded is false."""
        # Set onboarded to False
        settings = self.persistence.load_settings()
        settings["onboarded"] = False
        self.persistence.save_settings(settings)

        # GET /api/settings should block with 403 Setup erforderlich
        res = self.client.get("/api/settings")
        self.assertEqual(res.status_code, 403)

        # GET /api/onboarding/status should pass
        res = self.client.get("/api/onboarding/status")
        self.assertEqual(res.status_code, 200)

        # GET /api/keys should pass
        res = self.client.get("/api/keys")
        self.assertEqual(res.status_code, 200)

        # GET /api/system/capabilities should pass so the frontend can detect Docker before setup
        res = self.client.get("/api/system/capabilities")
        self.assertEqual(res.status_code, 200)

        # GET /api/check-dependencies should pass
        res = self.client.get("/api/check-dependencies")
        self.assertEqual(res.status_code, 200)

        # Capabilities must also pass after a password was set but before onboarding is complete.
        # Otherwise the frontend falls back to desktop mode during Docker setup.
        settings = self.persistence.load_settings()
        settings["password_hash"] = "pbkdf2:sha256:1000000$test$hash"
        self.persistence.save_settings(settings)
        res = self.client.get("/api/system/capabilities")
        self.assertEqual(res.status_code, 200)

    def test_onboarding_status_endpoint(self):
        """Verifies GET /api/onboarding/status endpoint values."""
        res = self.client.get("/api/onboarding/status")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertFalse(data["onboarded"])
        self.assertEqual(data["newsletter_registration_status"], "none")

    def test_setup_settings_endpoint(self):
        """Verifies POST /api/onboarding/setup-settings works and updates files."""
        payload = {
            "inbox_dir": "/new/inbox",
            "outbox_dir": "/new/outbox",
            "media_server": "emby"
        }
        res = self.client.post("/api/onboarding/setup-settings", json=payload)
        self.assertEqual(res.status_code, 200)

        # Read settings and verify
        settings = self.persistence.load_settings()
        self.assertEqual(settings["inbox_dir"], "/new/inbox")
        self.assertEqual(settings["outbox_dir"], "/new/outbox")
        self.assertEqual(settings["media_server"], "emby")

    def test_set_password_and_csrf_handshake(self):
        """Verifies set-password sets credentials and returns CSRF token, allowing subsequent requests."""
        # 1. Set password in onboarding
        res = self.client.post("/api/onboarding/set-password", json={"password": "wizard-secure-pin"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        csrf_token = data.get("csrf_token")
        self.assertIsNotNone(csrf_token)

        # 2. Subsequent POST calls (e.g. setup-settings) must present CSRF token to pass the auth middleware CSRF check
        # Since password is now set, middleware requires CSRF validation
        res_fail = self.client.post("/api/onboarding/setup-settings", json={"media_server": "jellyfin"})
        self.assertEqual(res_fail.status_code, 400) # Bad request: CSRF validation failed

        res_success = self.client.post(
            "/api/onboarding/setup-settings",
            json={"media_server": "jellyfin"},
            headers={"X-CSRF-Token": csrf_token}
        )
        self.assertEqual(res_success.status_code, 200)

    def test_complete_and_skip_endpoints(self):
        """Verifies complete validation and skip flows."""
        # 1. Complete should fail if minimal options are missing
        res = self.client.post("/api/onboarding/complete", json={})
        self.assertEqual(res.status_code, 400)
        self.assertIn("error", res.get_json())

        # Set values
        settings = self.persistence.load_settings()
        settings["inbox_dir"] = "/in"
        settings["outbox_dir"] = "/out"
        settings["media_server"] = "plex"
        self.persistence.save_settings(settings)

        # Complete should now succeed
        res = self.client.post("/api/onboarding/complete", json={"telemetry_enabled": True})
        self.assertEqual(res.status_code, 200)

        # Verify status
        settings = self.persistence.load_settings()
        self.assertTrue(settings["onboarded"])
        self.assertTrue(settings["telemetry_enabled"])
        self.assertIsNotNone(settings["onboarding_completed_at"])

        # Reset onboarded to False
        self.persistence._cached_settings = None
        settings = self.persistence.load_settings()
        settings["onboarded"] = False
        settings["onboarding_completed_at"] = None
        self.persistence.save_settings(settings)

        # Skip should succeed immediately (expert mode)
        res = self.client.post("/api/onboarding/skip")
        self.assertEqual(res.status_code, 200)

        settings = self.persistence.load_settings()
        self.assertTrue(settings["onboarded"])
        self.assertIsNotNone(settings["onboarding_skipped_at"])

    @patch("gui.core.telemetry.send_newsletter_registration")
    def test_newsletter_registration(self, mock_send):
        """Verifies registration endpoints sets pending status and transfers correctly."""
        mock_send.return_value = True

        res = self.client.post("/api/onboarding/register-email", json={"email": "alex@mediawerkzeug.xyz"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["status"], "success")

        settings = self.persistence.load_settings()
        self.assertEqual(settings["newsletter_registration_status"], "registered")
        self.assertIsNotNone(settings["newsletter_registered_at"])
        mock_send.assert_called_once_with("alex@mediawerkzeug.xyz")

    def test_keys_api_endpoint(self):
        """Verifies keys saving in dotenv and mask retrieval."""
        # Save keys
        res = self.client.post("/api/keys", json={"TMDB_API_KEY": "super-secret-tmdb-12345"})
        self.assertEqual(res.status_code, 200)

        # Load keys (GET should show masked version)
        res_get = self.client.get("/api/keys")
        self.assertEqual(res_get.status_code, 200)
        data = res_get.get_json()
        self.assertEqual(data["TMDB_API_KEY"], "****2345")

    @patch("subprocess.run")
    @patch("socket.socket")
    def test_test_nas_connection(self, mock_socket, mock_run):
        """Verifies test nas connection endpoint mock checks."""
        # Mock port 445 connectable
        mock_s = MagicMock()
        mock_socket.return_value = mock_s
        mock_run.return_value.returncode = 0

        res = self.client.post("/api/onboarding/test-nas-connection", json={
            "nas_ip": "192.168.2.208",
            "nas_share": "Kino",
            "root_path": self.temp_dir.name # existiert real, da temp_dir
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["ok"])

    def test_settings_telemetry_opt_out(self):
        """Verifies settings API allows modifying telemetry_enabled."""
        # 1. First onboard the setup so we can access /api/settings
        settings = self.persistence.load_settings()
        settings["onboarded"] = True
        settings["telemetry_enabled"] = True
        self.persistence.save_settings(settings)

        # 2. POST to /api/settings to turn telemetry_enabled off
        res = self.client.post("/api/settings", json={"telemetry_enabled": False})
        self.assertEqual(res.status_code, 200)

        # 3. Verify it was written to settings
        settings = self.persistence.load_settings()
        self.assertFalse(settings["telemetry_enabled"])
    @patch("gui.api.onboarding_api.get_runtime_capabilities")
    @patch("os.path.exists")
    @patch("os.access")
    def test_test_nas_connection_docker_mode_success(self, mock_access, mock_exists, mock_caps):
        mock_caps.return_value = {"runtime": "docker"}
        mock_exists.return_value = True
        mock_access.return_value = True
        
        res = self.client.post("/api/onboarding/test-nas-connection", json={
            "root_path": "/media"
        })
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["ok"])

    @patch("gui.api.onboarding_api.get_runtime_capabilities")
    @patch("os.path.exists")
    @patch("os.access")
    def test_test_nas_connection_docker_mode_no_write_access(self, mock_access, mock_exists, mock_caps):
        mock_caps.return_value = {"runtime": "docker"}
        mock_exists.return_value = True
        mock_access.return_value = False
        
        res = self.client.post("/api/onboarding/test-nas-connection", json={
            "root_path": "/media"
        })
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.get_json()["ok"])
        self.assertIn("fehlen die Schreibrechte", res.get_json()["message"])

if __name__ == "__main__":
    unittest.main()
