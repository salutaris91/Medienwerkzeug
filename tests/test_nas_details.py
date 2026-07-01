import os
import sys
import unittest
from unittest.mock import MagicMock, patch

from flask import Flask

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gui.core import transfers
from gui.api.system_api import handle_api_nas_connect, handle_api_status, system_api

NAS_SETTINGS_ENABLED = {
    "storage_targets": [{
        "id": "nas",
        "root_path": "/Volumes/Kino",
        "nas_ip": "192.168.1.100",
        "nas_ip_backup": "100.64.0.1",
        "nas_hostname": "MEDIENSERVER",
        "nas_share": "Kino",
        "enabled": True,
    }]
}

NAS_SETTINGS_DISABLED = {
    "storage_targets": [{
        "id": "nas",
        "root_path": "/Volumes/Kino",
        "nas_ip": "192.168.1.100",
        "nas_ip_backup": "100.64.0.1",
        "nas_hostname": "MEDIENSERVER",
        "nas_share": "Kino",
        "enabled": False,
    }]
}

NAS_SETTINGS_NO_ROOT = {
    "storage_targets": [{
        "id": "nas",
        "root_path": "",
        "nas_ip": "192.168.1.100",
        "nas_ip_backup": "100.64.0.1",
        "nas_hostname": "MEDIENSERVER",
        "nas_share": "Kino",
        "enabled": True,
    }]
}


class TestNasDetails(unittest.TestCase):
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

    def _socket_mock(self, mock_instance=None):
        socket_instance = mock_instance or MagicMock()
        return patch.object(transfers.socket, "socket", return_value=socket_instance)

    @patch("gui.core.transfers.load_settings", return_value=NAS_SETTINGS_DISABLED)
    def test_details_when_disabled(self, mock_settings):
        details = transfers.check_nas_connection_details()
        self.assertEqual(details["status"], "offline")
        self.assertFalse(details["enabled"])
        self.assertTrue(details["has_root"])
        self.assertEqual(details["checked_ips"], ["192.168.1.100", "100.64.0.1"])
        self.assertIsNone(details["reachable_ip"])
        self.assertEqual(details["error_message"], "NAS-Verbindung in den Einstellungen deaktiviert.")
        self.assertEqual(details["ip_details"][0]["role"], "primary")
        self.assertEqual(details["ip_details"][1]["role"], "backup")

    @patch("gui.core.transfers.load_settings", return_value=NAS_SETTINGS_NO_ROOT)
    def test_details_when_no_root(self, mock_settings):
        details = transfers.check_nas_connection_details()
        self.assertEqual(details["status"], "offline")
        self.assertTrue(details["enabled"])
        self.assertFalse(details["has_root"])
        self.assertIsNone(details["reachable_ip"])
        self.assertEqual(details["error_message"], "Kein nas_root konfiguriert.")

    @patch("gui.core.transfers.load_settings", return_value=NAS_SETTINGS_ENABLED)
    @patch("gui.core.transfers._is_nas_root_mounted", return_value=True)
    def test_details_when_connected(self, mock_mounted, mock_settings):
        with self._socket_mock():
            details = transfers.check_nas_connection_details()
        self.assertEqual(details["status"], "connected")
        self.assertTrue(details["enabled"])
        self.assertTrue(details["has_root"])
        self.assertIsNotNone(details["reachable_ip"])
        self.assertIsNone(details["error_message"])

    @patch("gui.core.transfers.load_settings", return_value=NAS_SETTINGS_ENABLED)
    @patch("gui.core.transfers._is_nas_root_mounted", return_value=False)
    @patch("gui.core.transfers.diagnose_nas_mount", return_value=('not_mounted', "Laufwerk erreichbar, aber nicht eingehängt."))
    def test_details_when_available_not_mounted(self, mock_diagnose, mock_mounted, mock_settings):
        # Socket mock connects successfully to first IP
        socket_mock = MagicMock()
        with self._socket_mock(socket_mock):
            details = transfers.check_nas_connection_details()
        self.assertEqual(details["status"], "available_not_mounted")
        self.assertEqual(details["reachable_ip"], "192.168.1.100")
        self.assertEqual(details["error_message"], "Laufwerk erreichbar, aber nicht eingehängt.")

    @patch("gui.core.transfers.load_settings", return_value=NAS_SETTINGS_ENABLED)
    @patch("gui.core.transfers._is_nas_root_mounted", return_value=False)
    def test_details_when_offline(self, mock_mounted, mock_settings):
        # Socket mock fails to connect
        socket_mock = MagicMock()
        socket_mock.connect.side_effect = Exception("Connection timed out")
        with self._socket_mock(socket_mock):
            details = transfers.check_nas_connection_details()
        self.assertEqual(details["status"], "offline")
        self.assertIsNone(details["reachable_ip"])
        self.assertIn("primary (192.168.1.100)", details["error_message"])
        self.assertIn("backup (100.64.0.1)", details["error_message"])

    @patch("gui.api.system_api.check_nas_connection_details")
    def test_api_status_returns_details(self, mock_details):
        mock_details.return_value = {
            "status": "available_not_mounted",
            "enabled": True,
            "has_root": True,
            "checked_ips": ["192.168.1.100", "100.64.0.1"],
            "reachable_ip": "100.64.0.1"
        }
        
        # Mocking check_streamfab to avoid background thread triggers
        with patch("gui.api.system_api.check_streamfab", return_value=[]):
            response = self.client.get("/api/status")
            
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["nas_status"], "available_not_mounted")
        self.assertIn("nas_details", data)
        self.assertEqual(data["nas_details"]["reachable_ip"], "100.64.0.1")

    @patch("gui.api.system_api.check_nas_connection_details")
    def test_api_status_force_check_bypasses_cache(self, mock_details):
        mock_details.return_value = {
            "status": "connected",
            "enabled": True,
            "has_root": True,
            "checked_ips": [],
            "reachable_ip": None
        }
        
        # Reset cache on endpoint function
        if hasattr(handle_api_status, "last_nas_details"):
            delattr(handle_api_status, "last_nas_details")
            
        with patch("gui.api.system_api.check_streamfab", return_value=[]):
            # First call - populates cache
            response = self.client.get("/api/status")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(mock_details.call_count, 1)

            # Second call without force_nas_check - uses cache
            response = self.client.get("/api/status")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(mock_details.call_count, 1)

            # Third call with force_nas_check=true - bypasses cache
            response = self.client.get("/api/status?force_nas_check=true")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(mock_details.call_count, 2)

    @patch("gui.core.transfers.load_settings", return_value=NAS_SETTINGS_ENABLED)
    @patch("gui.core.transfers.get_runtime_capabilities", return_value={"runtime": "docker", "capabilities": {}})
    @patch("gui.core.transfers.os.path.isdir", return_value=True)
    def test_details_docker_connected(self, mock_isdir, mock_caps, mock_settings):
        details = transfers.check_nas_connection_details()
        self.assertEqual(details["status"], "connected")
        self.assertTrue(details["enabled"])
        self.assertTrue(details["has_root"])
        self.assertIsNone(details["reachable_ip"])
        self.assertEqual(details["checked_ips"], [])
        self.assertEqual(details["ip_details"], [])
        self.assertIsNone(details["error_message"])

    @patch("gui.core.transfers.load_settings", return_value=NAS_SETTINGS_ENABLED)
    @patch("gui.core.transfers.get_runtime_capabilities", return_value={"runtime": "docker", "capabilities": {}})
    @patch("gui.core.transfers.os.path.isdir", return_value=False)
    def test_details_docker_offline(self, mock_isdir, mock_caps, mock_settings):
        details = transfers.check_nas_connection_details()
        self.assertEqual(details["status"], "offline")
        self.assertTrue(details["enabled"])
        self.assertTrue(details["has_root"])
        self.assertIsNone(details["reachable_ip"])
        self.assertEqual(details["checked_ips"], [])
        self.assertEqual(details["ip_details"], [])
        self.assertIn("Docker-Volume nicht im Container verfügbar", details["error_message"])

    @patch("gui.core.transfers.load_settings", return_value=NAS_SETTINGS_ENABLED)
    @patch("gui.core.transfers.get_runtime_capabilities", return_value={"runtime": "docker", "capabilities": {}})
    @patch("gui.core.transfers.os.path.isdir", return_value=True)
    def test_status_docker_connected(self, mock_isdir, mock_caps, mock_settings):
        status = transfers.check_nas_status()
        self.assertEqual(status, "connected")

    @patch("gui.core.transfers.load_settings", return_value=NAS_SETTINGS_ENABLED)
    @patch("gui.core.transfers.get_runtime_capabilities", return_value={"runtime": "docker", "capabilities": {}})
    @patch("gui.core.transfers.os.path.isdir", return_value=False)
    def test_status_docker_offline(self, mock_isdir, mock_caps, mock_settings):
        status = transfers.check_nas_status()
        self.assertEqual(status, "offline")


if __name__ == "__main__":
    unittest.main()
