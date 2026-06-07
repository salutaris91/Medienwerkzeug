import os
import unittest
import tempfile
import json
import time
from werkzeug.security import generate_password_hash
from flask import session
from unittest.mock import patch, MagicMock

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

        # Set up test folder paths in temporary settings
        settings = self.persistence.load_settings()
        settings["inbox_dir"] = os.path.join(self.temp_dir.name, "inbox")
        settings["outbox_dir"] = os.path.join(self.temp_dir.name, "outbox")
        settings["nas_root"] = os.path.join(self.temp_dir.name, "nas")
        self.persistence.save_settings(settings)

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

    def test_root_page_loads_with_password(self):
        """Test 2b: The root page must load when locked so the login UI can render."""
        self.persistence.set_password("my-test-password")

        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)

    def test_healthz_bypasses_auth_when_password_is_set(self):
        """Test 2c: Health checks must stay public so startup can detect healthy servers."""
        self.persistence.set_password("my-test-password")

        res = self.client.get("/api/healthz")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json(), {"ok": True})

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

    def test_logout_invalidates_session(self):
        """Test 9: Logout POST clears session and deletes CSRF cookie, blocking subsequent requests."""
        self.persistence.set_password("my-test-password")

        # 1. Login
        self.client.post("/api/auth/login", json={"password": "my-test-password"})
        csrf_token = self.client.get_cookie("mw_csrf_token").value
        headers = {"X-CSRF-Token": csrf_token}

        # Verify access works
        res = self.client.get("/api/settings")
        self.assertEqual(res.status_code, 200)

        # 2. Logout
        res_logout = self.client.post("/api/auth/logout", headers=headers)
        self.assertEqual(res_logout.status_code, 200)

        # Verify access is blocked now
        res = self.client.get("/api/settings")
        self.assertEqual(res.status_code, 401)

    def test_password_rotation_invalidates_old_sessions(self):
        """Test 10: Changing password rotates the hash fingerprint and invalidates all other devices' sessions."""
        self.persistence.set_password("old-password")

        # Client A logs in
        client_a = self.app.test_client()
        res = client_a.post("/api/auth/login", json={"password": "old-password"})
        self.assertEqual(res.status_code, 200)

        # Client B logs in
        client_b = self.app.test_client()
        client_b.post("/api/auth/login", json={"password": "old-password"})
        csrf_token = client_b.get_cookie("mw_csrf_token").value

        # Client B changes password
        res_change = client_b.post("/api/settings/password", json={
            "current_password": "old-password",
            "new_password": "new-secure-password"
        }, headers={"X-CSRF-Token": csrf_token})
        self.assertEqual(res_change.status_code, 200)

        # Client A (old session) should now be blocked with HTTP 401
        res = client_a.get("/api/settings")
        self.assertEqual(res.status_code, 401)

        # Client B (current session who did the change) should still be authenticated
        res = client_b.get("/api/settings")
        self.assertEqual(res.status_code, 200)

    def test_system_open_folder_post_only(self):
        """Test 11: /api/system-open-folder accepts only POST and rejects GET."""
        self.persistence.set_password("my-test-password")

        # Login
        self.client.post("/api/auth/login", json={"password": "my-test-password"})
        csrf_token = self.client.get_cookie("mw_csrf_token").value
        headers = {"X-CSRF-Token": csrf_token}

        # GET should be rejected with 404 or 405 Method Not Allowed
        res = self.client.get("/api/system-open-folder")
        self.assertIn(res.status_code, (404, 405))

        nonexistent_allowed_path = os.path.join(self.temp_dir.name, "inbox", "nonexistent-folder-12345")

        # POST with missing CSRF should fail with 400
        res = self.client.post("/api/system-open-folder", json={"path": nonexistent_allowed_path})
        self.assertEqual(res.status_code, 400)

        # POST with valid CSRF should pass the auth/csrf check and return 200 (with error message inside JSON) instead of 401/400 CSRF
        res = self.client.post("/api/system-open-folder", json={"path": nonexistent_allowed_path}, headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertIn("existiert nicht", res.get_json().get("error", ""))

    @patch("subprocess.run")
    def test_youtube_fetch_post_only(self, mock_run):
        """Test 12: /api/yt/fetch accepts only POST and rejects GET."""
        self.persistence.set_password("my-test-password")

        # Login
        self.client.post("/api/auth/login", json={"password": "my-test-password"})
        csrf_token = self.client.get_cookie("mw_csrf_token").value
        headers = {"X-CSRF-Token": csrf_token}

        # GET should be rejected with 404 or 405 Method Not Allowed
        res = self.client.get("/api/yt/fetch")
        self.assertIn(res.status_code, (404, 405))

        # Mock successful subprocess execution
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = json.dumps({
            "title": "Mock Video",
            "uploader": "Mock Channel",
            "thumbnail": "mock.jpg",
            "duration": 120,
            "formats": [{"format_note": "1080p", "height": 1080, "vcodec": "av01"}]
        })
        mock_run.return_value = mock_proc

        # POST with valid CSRF should succeed
        res = self.client.post("/api/yt/fetch", json={"url": "https://youtube.com/watch?v=abc"}, headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json().get("title"), "Mock Video")

    def test_streamfab_preview_and_import_separated(self):
        """Test 13: StreamFab routes are correctly separated into GET (preview) and POST (import)."""
        self.persistence.set_password("my-test-password")

        # Login
        self.client.post("/api/auth/login", json={"password": "my-test-password"})
        csrf_token = self.client.get_cookie("mw_csrf_token").value
        headers = {"X-CSRF-Token": csrf_token}

        # GET on preview should succeed without CSRF headers
        res = self.client.get("/api/streamfab-import/preview")
        self.assertEqual(res.status_code, 200)

        # POST on preview without CSRF should fail with 400 (due to global CSRF middleware check)
        res = self.client.post("/api/streamfab-import/preview")
        self.assertEqual(res.status_code, 400)

        # POST on preview with CSRF should fail with 405 Method Not Allowed
        res = self.client.post("/api/streamfab-import/preview", headers=headers)
        self.assertEqual(res.status_code, 405)

        # GET on import should be rejected with 404 or 405
        res = self.client.get("/api/streamfab-import")
        self.assertIn(res.status_code, (404, 405))

        # POST on import without CSRF should fail (400)
        res = self.client.post("/api/streamfab-import", json={})
        self.assertEqual(res.status_code, 400)

        # POST on import with CSRF should succeed (200)
        res = self.client.post("/api/streamfab-import", json={}, headers=headers)
        self.assertEqual(res.status_code, 200)

    def test_auth_status_updates_on_password_rotation(self):
        """Test 14: /api/auth/status reflects authentication status immediately after password rotation."""
        self.persistence.set_password("first-password")

        # Login
        res = self.client.post("/api/auth/login", json={"password": "first-password"})
        self.assertEqual(res.status_code, 200)

        # Check status (should be authenticated)
        res = self.client.get("/api/auth/status")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json().get("authenticated"))

        # Rotate password
        self.persistence.set_password("second-password")

        # Check status (should be unauthenticated and cleared)
        res = self.client.get("/api/auth/status")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.get_json().get("authenticated"))


if __name__ == "__main__":
    unittest.main()
