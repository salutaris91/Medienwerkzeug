import sys
import os
import unittest
import unittest.mock
import json

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gui.core.helpers as helpers

class TestDependencyChecking(unittest.TestCase):
    @unittest.mock.patch("shutil.which")
    def test_get_local_version_missing(self, mock_which):
        mock_which.return_value = None
        ver = helpers.get_local_version("nonexistent-cmd", ["--version"], r"([\d\.]+)")
        self.assertIsNone(ver)

    @unittest.mock.patch("shutil.which")
    @unittest.mock.patch("subprocess.run")
    def test_get_local_version_error(self, mock_run, mock_which):
        mock_which.return_value = "/usr/bin/somecmd"
        mock_run.side_effect = Exception("execution error")
        ver = helpers.get_local_version("somecmd", ["--version"], r"([\d\.]+)")
        self.assertIsNone(ver)

    @unittest.mock.patch("shutil.which")
    @unittest.mock.patch("subprocess.run")
    def test_get_local_version_success_simple(self, mock_run, mock_which):
        mock_which.return_value = "/usr/bin/somecmd"
        mock_proc = unittest.mock.Mock()
        mock_proc.returncode = 0
        mock_proc.stdout = "somecmd version 2.3.4\n"
        mock_run.return_value = mock_proc

        ver = helpers.get_local_version("somecmd", ["--version"], r"version ([\d\.]+)")
        self.assertEqual(ver, "2.3.4")

    @unittest.mock.patch("shutil.which")
    @unittest.mock.patch("subprocess.run")
    def test_get_local_version_strips_v(self, mock_run, mock_which):
        mock_which.return_value = "/usr/bin/somecmd"
        mock_proc = unittest.mock.Mock()
        mock_proc.returncode = 0
        mock_proc.stdout = "v1.2.3-beta\n"
        mock_run.return_value = mock_proc

        ver = helpers.get_local_version("somecmd", ["--version"], r"(v[\d\.]+)")
        self.assertEqual(ver, "1.2.3")  # strips 'v'

    @unittest.mock.patch("urllib.request.urlopen")
    def test_fetch_latest_github_version_success(self, mock_urlopen):
        mock_resp = unittest.mock.Mock()
        mock_resp.status = 200
        mock_resp.read.return_value = b'{"tag_name": "v3.1.2"}'
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        ver = helpers.fetch_latest_github_version("foo/bar")
        self.assertEqual(ver, "3.1.2")

    @unittest.mock.patch("urllib.request.urlopen")
    def test_fetch_latest_ffmpeg_version_success(self, mock_urlopen):
        mock_resp = unittest.mock.Mock()
        mock_resp.status = 200
        mock_resp.read.return_value = b'{"version": "7.0.1"}'
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        ver = helpers.fetch_latest_ffmpeg_version()
        self.assertEqual(ver, "7.0.1")

    @unittest.mock.patch("gui.core.helpers.get_local_version")
    @unittest.mock.patch("gui.core.helpers.fetch_latest_github_version")
    @unittest.mock.patch("gui.core.helpers.fetch_latest_ffmpeg_version")
    @unittest.mock.patch("gui.core.helpers.load_settings")
    def test_check_dependency_status_up_to_date(self, mock_settings, mock_ffmpeg, mock_github, mock_local):
        mock_settings.return_value = {"check_dependency_updates": True}
        mock_local.side_effect = lambda cmd, *args, **kwargs: {
            "yt-dlp": "2026.03.17",
            "rclone": "1.65.0",
            "ffmpeg": "7.0",
            "deno": "1.42.0"
        }.get(cmd)
        
        mock_github.side_effect = lambda repo: {
            "yt-dlp/yt-dlp": "2026.03.17",
            "rclone/rclone": "1.65.0",
            "denoland/deno": "1.42.0"
        }.get(repo)
        
        mock_ffmpeg.return_value = "7.0"

        res = helpers.check_dependency_status(force_updates=False)
        self.assertEqual(res["yt-dlp"]["status"], "up_to_date")
        self.assertEqual(res["rclone"]["status"], "up_to_date")
        self.assertEqual(res["ffmpeg"]["status"], "up_to_date")
        self.assertEqual(res["deno"]["status"], "up_to_date")

    @unittest.mock.patch("gui.core.helpers.get_local_version")
    @unittest.mock.patch("gui.core.helpers.fetch_latest_github_version")
    @unittest.mock.patch("gui.core.helpers.fetch_latest_ffmpeg_version")
    @unittest.mock.patch("gui.core.helpers.load_settings")
    def test_check_dependency_status_update_available(self, mock_settings, mock_ffmpeg, mock_github, mock_local):
        mock_settings.return_value = {"check_dependency_updates": True}
        mock_local.side_effect = lambda cmd, *args, **kwargs: {
            "yt-dlp": "2026.02.17",  # older
            "rclone": "1.64.0",     # older
            "ffmpeg": "6.1",        # older
            "deno": "1.40.0"        # older
        }.get(cmd)
        
        mock_github.side_effect = lambda repo: {
            "yt-dlp/yt-dlp": "2026.03.17",
            "rclone/rclone": "1.65.0",
            "denoland/deno": "1.42.0"
        }.get(repo)
        
        mock_ffmpeg.return_value = "7.0"

        res = helpers.check_dependency_status(force_updates=False)
        self.assertEqual(res["yt-dlp"]["status"], "update_available")
        self.assertEqual(res["rclone"]["status"], "update_available")
        self.assertEqual(res["ffmpeg"]["status"], "update_available")
        self.assertEqual(res["deno"]["status"], "update_available")

    @unittest.mock.patch("gui.core.helpers.get_local_version")
    @unittest.mock.patch("gui.core.helpers.load_settings")
    def test_check_dependency_status_disabled_without_force(self, mock_settings, mock_local):
        # When update checks are disabled, we shouldn't attempt to fetch from GitHub or FFMpeg endpoint
        mock_settings.return_value = {"check_dependency_updates": False}
        mock_local.side_effect = lambda cmd, *args, **kwargs: "1.0.0"

        with unittest.mock.patch("gui.core.helpers.fetch_latest_github_version") as mock_github:
            res = helpers.check_dependency_status(force_updates=False)
            mock_github.assert_not_called()
            self.assertEqual(res["yt-dlp"]["status"], "installed")
            self.assertEqual(res["yt-dlp"]["installed_version"], "1.0.0")
            self.assertIsNone(res["yt-dlp"]["latest_version"])

if __name__ == "__main__":
    unittest.main()
