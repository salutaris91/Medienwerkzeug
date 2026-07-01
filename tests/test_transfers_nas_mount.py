import os
import sys
import unittest
from unittest.mock import MagicMock, call, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gui.core import transfers


NAS_SETTINGS = {
    "storage_targets": [{
        "id": "nas",
        "root_path": "/Volumes/Kino",
        "nas_ip": "192.168.1.100",
        "nas_ip_backup": "100.64.0.1",
        "nas_hostname": "ALEXNAS91",
        "nas_share": "Kino",
        "enabled": True,
    }]
}


class TestNasMountFallback(unittest.TestCase):
    def _socket_mock(self):
        socket_instance = MagicMock()
        return patch.object(transfers.socket, "socket", return_value=socket_instance)

    @patch("gui.core.transfers.load_settings", return_value=NAS_SETTINGS)
    @patch("gui.core.transfers.check_nas_status", return_value="available_not_mounted")
    @patch("gui.core.transfers._wait_for_nas_mount", return_value=True)
    @patch("gui.core.transfers.subprocess.run")
    def test_direct_mount_success_does_not_open_finder(self, mock_run, mock_wait, mock_status, mock_settings):
        mock_run.return_value = MagicMock(returncode=0, stdout="file Kino:", stderr="")

        with self._socket_mock():
            self.assertTrue(transfers.ensure_nas_mounted())

        self.assertEqual(mock_run.call_count, 1)
        self.assertEqual(mock_run.call_args.args[0][0], "osascript")

    @patch("gui.core.transfers.load_settings", return_value=NAS_SETTINGS)
    @patch("gui.core.transfers.check_nas_status", return_value="available_not_mounted")
    @patch("gui.core.transfers._wait_for_nas_mount", return_value=True)
    @patch("gui.core.transfers.subprocess.run")
    @patch("gui.core.transfers.os.path.exists", return_value=False)
    def test_applescript_error_skips_finder_fallback_by_default(self, mock_exists, mock_run, mock_wait, mock_status, mock_settings):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="AppleScript mount failed")

        with self._socket_mock():
            self.assertFalse(transfers.ensure_nas_mounted())

        self.assertEqual(mock_run.call_count, 1)
        self.assertEqual(mock_run.call_args.args[0][0], "osascript")

    @patch("gui.core.transfers.load_settings", return_value=NAS_SETTINGS)
    @patch("gui.core.transfers.check_nas_status", return_value="available_not_mounted")
    @patch("gui.core.transfers._wait_for_nas_mount", return_value=True)
    @patch("gui.core.transfers.subprocess.run")
    def test_applescript_error_opens_finder_fallback_when_allowed(self, mock_run, mock_wait, mock_status, mock_settings):
        mock_run.side_effect = [
            MagicMock(returncode=1, stdout="", stderr="AppleScript mount failed"),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]

        with self._socket_mock():
            self.assertTrue(transfers.ensure_nas_mounted(allow_finder_fallback=True))

        self.assertEqual(mock_run.call_args_list[1], call(
            ["open", "smb://ALEXNAS91/Kino"],
            capture_output=True,
            text=True,
            timeout=5
        ))

    @patch("gui.core.transfers.load_settings", return_value=NAS_SETTINGS)
    @patch("gui.core.transfers.check_nas_status", return_value="available_not_mounted")
    @patch("gui.core.transfers._wait_for_nas_mount", side_effect=[False, True])
    @patch("gui.core.transfers.subprocess.run")
    @patch("gui.core.transfers.os.path.exists", return_value=False)
    def test_delayed_direct_mount_skips_finder_fallback_by_default(self, mock_exists, mock_run, mock_wait, mock_status, mock_settings):
        mock_run.return_value = MagicMock(returncode=0, stdout="file Kino:", stderr="")

        with self._socket_mock():
            self.assertFalse(transfers.ensure_nas_mounted())

        self.assertEqual(mock_run.call_count, 1)

    @patch("gui.core.transfers.load_settings", return_value=NAS_SETTINGS)
    @patch("gui.core.transfers.check_nas_status", return_value="available_not_mounted")
    @patch("gui.core.transfers._wait_for_nas_mount", side_effect=[False, True])
    @patch("gui.core.transfers.subprocess.run")
    def test_delayed_direct_mount_opens_finder_fallback_when_allowed(self, mock_run, mock_wait, mock_status, mock_settings):
        mock_run.return_value = MagicMock(returncode=0, stdout="file Kino:", stderr="")

        with self._socket_mock():
            self.assertTrue(transfers.ensure_nas_mounted(allow_finder_fallback=True))

        self.assertEqual(mock_run.call_args_list[1].args[0], ["open", "smb://ALEXNAS91/Kino"])

    @patch("gui.core.transfers.load_settings", return_value=NAS_SETTINGS)
    @patch("gui.core.transfers.check_nas_status", return_value="available_not_mounted")
    @patch("gui.core.transfers._wait_for_nas_mount", return_value=True)
    @patch("gui.core.transfers.os.path.exists", return_value=False)
    @patch("gui.core.transfers.log_message")
    @patch("gui.core.transfers.subprocess.run")
    def test_applescript_error_is_logged(self, mock_run, mock_log, mock_exists, mock_wait, mock_status, mock_settings):
        mock_run.side_effect = [
            MagicMock(returncode=1, stdout="", stderr="AppleScript mount failed"),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]

        with self._socket_mock():
            self.assertFalse(transfers.ensure_nas_mounted())

        mock_log.assert_any_call("⚠️ Automatisches SMB-Mounting fehlgeschlagen: AppleScript mount failed")


class TestIsNasRootMounted(unittest.TestCase):
    @patch("gui.core.transfers.subprocess.check_output")
    @patch("gui.core.transfers.os.path.isdir")
    def test_direct_mount_exact(self, mock_isdir, mock_check_output):
        mock_check_output.return_value = "//alex@NAS/Kino on /Volumes/Kino (smbfs, nodev)"
        mock_isdir.return_value = True
        
        self.assertTrue(transfers._is_nas_root_mounted("/Volumes/Kino"))
        self.assertTrue(transfers._is_nas_root_mounted("/Volumes/Kino/"))

    @patch("gui.core.transfers.subprocess.check_output")
    @patch("gui.core.transfers.os.path.isdir")
    def test_direct_mount_subdirectory(self, mock_isdir, mock_check_output):
        mock_check_output.return_value = "//alex@NAS/Kino on /Volumes/Kino (smbfs, nodev)"
        mock_isdir.return_value = True
        
        self.assertTrue(transfers._is_nas_root_mounted("/Volumes/Kino/Serien"))
        self.assertTrue(transfers._is_nas_root_mounted("/Volumes/Kino/Serien/"))

    @patch("gui.core.transfers.subprocess.check_output")
    @patch("gui.core.transfers.os.path.isdir")
    def test_suffix_mount_subdirectory(self, mock_isdir, mock_check_output):
        mock_check_output.return_value = "//alex@NAS/Kino on /Volumes/Kino-1 (smbfs, nodev)"
        
        def isdir_mock(path):
            return path == "/Volumes/Kino-1/Serien"
        mock_isdir.side_effect = isdir_mock
        
        self.assertTrue(transfers._is_nas_root_mounted("/Volumes/Kino/Serien"))

    @patch("gui.core.transfers.subprocess.check_output")
    @patch("gui.core.transfers.os.path.isdir")
    def test_no_false_match_with_similar_names(self, mock_isdir, mock_check_output):
        mock_check_output.return_value = "//alex@NAS/Kino on /Volumes/Kino-1 (smbfs, nodev)"
        mock_isdir.return_value = True
        
        self.assertFalse(transfers._is_nas_root_mounted("/Volumes/Kino2/Serien"))


if __name__ == "__main__":
    unittest.main()
