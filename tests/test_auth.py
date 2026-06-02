import os
import unittest
import tempfile
import json
import time
from werkzeug.security import generate_password_hash
from flask import session

class TestAuth(unittest.TestCase):
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
        os.environ["FLASK_SECRET_KEY"] = "test-secret-key-12345"

        # Import persistence and reset cache
        import gui.core.persistence as persistence
        self.persistence = persistence
        self.persistence._cached_settings = None

        # Reset in-memory rate limiting dictionary if it exists yet
        try:
            from gui.api.system_api import failed_attempts
            failed_attempts.clear()
        except ImportError:
            pass

        # Load dynamic flask app
        from gui.main import app
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key-12345'
        self.app = app
        self.client = app.test_client()

    def tearDown(self):
        os.environ.pop("MW_SETTINGS_FILE", None)
        os.environ.pop("MW_JOBS_STATE_FILE", None)
        os.environ.pop("MW_ENV_FILE", None)
        os.environ.pop("MW_DATA_DIR", None)
        os.environ.pop("FLASK_SECRET_KEY", None)
        self.temp_dir.cleanup()

    def test_unlocked_access_no_password(self):
        """Test 1: If no password is configured, APIs should be accessible without session or CSRF."""
        settings = self.persistence.load_settings()
        self.assertEqual(settings.get("password_hash", ""), "")

        # Try to read settings (GET)
        res = self.client.get("/api/settings")
        self.assertEqual(res.status_code, 200)

        # Try to write settings (POST) without session or CSRF header
        payload = {"media_server": "plex"}
        res = self.client.post("/api/settings", json=payload)
        self.assertEqual(res.status_code, 200)

    def test_locked_access_with_password(self):
        """Test 2: Protected API endpoints block unauthenticated requests with HTTP 401 when password is set."""
        # Set a password
        self.persistence.set_password("my-test-password")

        # Try to access settings (GET)
        res = self.client.get("/api/settings")
        self.assertEqual(res.status_code, 401)

        # Try to access settings (POST)
        res = self.client.post("/api/settings", json={})
        self.assertEqual(res.status_code, 401)

    def test_login_success(self):
        """Test 3: Correct credentials log in successfully, set session, and set CSRF cookie."""
        self.persistence.set_password("my-test-password")

        # Login POST
        res = self.client.post("/api/auth/login", json={"password": "my-test-password"})
        self.assertEqual(res.status_code, 200)

        # Verify response JSON contains a success message
        data = res.get_json()
        self.assertEqual(data.get("status"), "success")

        # Check that session cookie exists
        headers = res.headers.getlist("Set-Cookie")
        cookie_names = [c.split("=")[0].strip() for c in headers]
        self.assertTrue(any("session" in name for name in cookie_names))
        self.assertTrue(any("mw_csrf_token" in name for name in cookie_names))

    def test_login_brute_force_lockout(self):
        """Test 4: Failures lead to lockout (HTTP 429) after 5 fails from same IP, but other IP is fine."""
        self.persistence.set_password("my-test-password")

        # Make 5 failed attempts from IP 1.1.1.1
        for i in range(5):
            res = self.client.post("/api/auth/login", json={"password": "wrong-password"}, environ_base={'REMOTE_ADDR': '1.1.1.1'})
            self.assertEqual(res.status_code, 401)

        # 6th attempt from same IP should get locked out
        res = self.client.post("/api/auth/login", json={"password": "my-test-password"}, environ_base={'REMOTE_ADDR': '1.1.1.1'})
        self.assertEqual(res.status_code, 429)

        # Attempt from different IP should work
        res = self.client.post("/api/auth/login", json={"password": "my-test-password"}, environ_base={'REMOTE_ADDR': '2.2.2.2'})
        self.assertEqual(res.status_code, 200)

    def test_csrf_token_validation(self):
        """Test 5: State-changing APIs (POST) return HTTP 400 if CSRF token is missing/incorrect, but work with correct token."""
        self.persistence.set_password("my-test-password")

        # 1. Login to establish authenticated session
        login_res = self.client.post("/api/auth/login", json={"password": "my-test-password"})
        self.assertEqual(login_res.status_code, 200)

        # 2. Extract CSRF token from Cookie
        cookies = self.client.get_cookie("mw_csrf_token")
        self.assertIsNotNone(cookies)
        csrf_token = cookies.value

        # 3. Request without CSRF Header -> should fail with 400
        res = self.client.post("/api/settings", json={"media_server": "emby"})
        self.assertEqual(res.status_code, 400)

        # 4. Request with wrong CSRF Header -> should fail with 400
        headers = {"X-CSRF-Token": "wrong-token-value"}
        res = self.client.post("/api/settings", json={"media_server": "emby"}, headers=headers)
        self.assertEqual(res.status_code, 400)

        # 5. Request with correct CSRF Header -> should succeed with 200
        headers = {"X-CSRF-Token": csrf_token}
        res = self.client.post("/api/settings", json={"media_server": "emby"}, headers=headers)
        self.assertEqual(res.status_code, 200)

    def test_password_change_requires_confirmation(self):
        """Test 6: Changing or disabling password requires correct old password."""
        self.persistence.set_password("my-test-password")

        # Login and get CSRF token
        self.client.post("/api/auth/login", json={"password": "my-test-password"})
        csrf_token = self.client.get_cookie("mw_csrf_token").value
        headers = {"X-CSRF-Token": csrf_token}

        # Try to change password with missing current_password
        payload = {"new_password": "new-secure-password"}
        res = self.client.post("/api/settings/password", json=payload, headers=headers)
        self.assertEqual(res.status_code, 403)

        # Try to change password with wrong current_password
        payload = {"current_password": "wrong-password", "new_password": "new-secure-password"}
        res = self.client.post("/api/settings/password", json=payload, headers=headers)
        self.assertEqual(res.status_code, 403)

        # Change password with correct current_password
        payload = {"current_password": "my-test-password", "new_password": "new-secure-password"}
        res = self.client.post("/api/settings/password", json=payload, headers=headers)
        self.assertEqual(res.status_code, 200)

        # Verify old password no longer works for login
        res = self.client.post("/api/auth/login", json={"password": "my-test-password"})
        self.assertEqual(res.status_code, 401)

        # Verify new password works
        res = self.client.post("/api/auth/login", json={"password": "new-secure-password"})
        self.assertEqual(res.status_code, 200)

    def test_emergency_reset_via_file(self):
        """Test 7: Removing password_hash from settings immediately disables authentication on settings load."""
        self.persistence.set_password("my-test-password")

        # API should be locked
        res = self.client.get("/api/settings")
        self.assertEqual(res.status_code, 401)

        # Clear password hash manually in file
        settings = self.persistence.load_settings()
        settings["password_hash"] = ""
        self.persistence.save_settings(settings)
        self.persistence._cached_settings = None # Clear cache

        # API should now be unlocked immediately
        res = self.client.get("/api/settings")
        self.assertEqual(res.status_code, 200)

    def test_mutating_get_routes_rejected(self):
        """Test 8: Mutating routes from the migration list reject GET requests and require POST."""
        # Check that GET requests to state-changing endpoints return HTTP 405 or 404
        res = self.client.get("/api/clean-project")
        self.assertIn(res.status_code, (404, 405))

        res = self.client.get("/api/delete-project")
        self.assertIn(res.status_code, (404, 405))

        res = self.client.get("/api/paths/clean")
        self.assertIn(res.status_code, (404, 405))

if __name__ == "__main__":
    unittest.main()
