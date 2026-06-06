import os
import sys
import unittest
from unittest.mock import patch

from flask import Flask

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gui.api.system_api import handle_api_nas_connect, handle_api_status, system_api


class TestNasConnectApi(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.register_blueprint(system_api, url_prefix="/api")
        self.client = self.app.test_client()

    def tearDown(self):
        for attribute in ("last_nas_status", "last_nas_details", "last_nas_check"):
            if hasattr(handle_api_status, attribute):
                delattr(handle_api_status, attribute)
        if hasattr(handle_api_nas_connect, "last_attempt"):
            delattr(handle_api_nas_connect, "last_attempt")

    @patch("gui.api.system_api.check_nas_connection_details")
    @patch("gui.api.system_api.check_nas_status", return_value="connected")
    @patch("gui.api.system_api.ensure_nas_mounted", return_value=True)
    def test_connect_reports_success_and_refreshes_status_cache(self, mock_mount, mock_status, mock_details):
        mock_details.return_value = {
            "status": "connected",
            "enabled": True,
            "has_root": True,
            "checked_ips": ["192.168.2.208"],
            "reachable_ip": "192.168.2.208"
        }
        response = self.client.post("/api/nas/connect")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["ok"])
        self.assertEqual(handle_api_status.last_nas_status, "connected")
        self.assertEqual(handle_api_status.last_nas_details["status"], "connected")
        mock_mount.assert_called_once_with()
        mock_details.assert_called_once_with()

    @patch("gui.api.system_api.check_nas_connection_details")
    @patch("gui.api.system_api.check_nas_status", return_value="offline")
    @patch("gui.api.system_api.ensure_nas_mounted", return_value=False)
    def test_connect_reports_unreachable_nas(self, mock_mount, mock_status, mock_details):
        mock_details.return_value = {
            "status": "offline",
            "enabled": True,
            "has_root": True,
            "checked_ips": ["192.168.2.208", "100.74.187.125"],
            "reachable_ip": None
        }
        response = self.client.post("/api/nas/connect")

        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.get_json()["ok"])
        self.assertIn("nicht erreicht", response.get_json()["message"])

    @patch("gui.api.system_api.check_nas_connection_details")
    @patch("gui.api.system_api.check_nas_status", return_value="available_not_mounted")
    @patch("gui.api.system_api.ensure_nas_mounted", return_value=False)
    def test_connect_reports_missing_smb_mount(self, mock_mount, mock_status, mock_details):
        mock_details.return_value = {
            "status": "available_not_mounted",
            "enabled": True,
            "has_root": True,
            "checked_ips": ["192.168.2.208", "100.74.187.125"],
            "reachable_ip": "192.168.2.208"
        }
        response = self.client.post("/api/nas/connect")

        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.get_json()["ok"])
        self.assertIn("Schlüsselbund", response.get_json()["message"])

    @patch("gui.api.system_api.check_nas_connection_details")
    @patch("gui.api.system_api.check_nas_status", return_value="connected")
    @patch("gui.api.system_api.ensure_nas_mounted", return_value=True)
    def test_connect_limits_repeated_mount_attempts(self, mock_mount, mock_status, mock_details):
        mock_details.return_value = {
            "status": "connected",
            "enabled": True,
            "has_root": True,
            "checked_ips": ["192.168.2.208"],
            "reachable_ip": "192.168.2.208"
        }
        first_response = self.client.post("/api/nas/connect")
        second_response = self.client.post("/api/nas/connect")

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 429)
        data = second_response.get_json()
        self.assertFalse(data["ok"])
        self.assertIn("nas_details", data)
        self.assertEqual(data["nas_details"]["status"], "connected")
        mock_mount.assert_called_once_with()

    @patch("gui.api.system_api.check_nas_connection_details")
    @patch("gui.api.system_api.get_runtime_capabilities")
    def test_connect_docker_mode_returns_403_with_details(self, mock_caps, mock_details):
        mock_caps.return_value = {
            "runtime": "docker",
            "capabilities": {
                "mount_nas": False
            }
        }
        mock_details.return_value = {
            "status": "offline",
            "enabled": True,
            "has_root": True,
            "checked_ips": ["192.168.2.208"],
            "reachable_ip": None,
            "error_message": "Some error"
        }
        response = self.client.post("/api/nas/connect")
        self.assertEqual(response.status_code, 403)
        data = response.get_json()
        self.assertFalse(data["ok"])
        self.assertEqual(data["nas_status"], "offline")
        self.assertIn("nas_details", data)
        self.assertEqual(data["nas_details"]["error_message"], "Some error")


if __name__ == "__main__":
    unittest.main()
