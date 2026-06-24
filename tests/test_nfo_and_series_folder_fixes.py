import os
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# 1. resolve_series_folder_name
from gui.core.series_helper import resolve_series_folder_name
from gui.api.search_api import search_api
from gui.core.nas_renamer import apply_renames
from gui.core.nfo_helper import update_nfo_mw_data, read_nfo_metadata
from gui.mw_metadata import generate_episode_nfo

class TestNfoAndSeriesFolderFixes(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.nas_dir = os.path.join(self.temp_dir, "NAS")
        self.outbox_dir = os.path.join(self.temp_dir, "Outbox")
        os.makedirs(self.nas_dir)
        os.makedirs(self.outbox_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    # 1. resolve_series_folder_name
    @patch("gui.core.series_helper.find_existing_series_folder_by_id")
    @patch("gui.core.helpers.get_matched_series_name")
    def test_resolve_series_folder_name(self, mock_get_matched, mock_find_by_id):
        # A) Explicit nas_show_folder wins
        res = resolve_series_folder_name(self.nas_dir, self.outbox_dir, "tvdb", "123", "Fallback", nas_show_folder="Explicit Folder!")
        self.assertEqual(res, "Explicit Folder!")

        # B) ID Match NAS
        mock_find_by_id.side_effect = lambda dest, prov, sid: "IDMatchNAS" if dest == self.nas_dir else None
        res = resolve_series_folder_name(self.nas_dir, self.outbox_dir, "tvdb", "123", "Fallback")
        self.assertEqual(res, "IDMatchNAS")

        # C) ID Match Outbox
        mock_find_by_id.side_effect = lambda dest, prov, sid: "IDMatchOutbox" if dest == self.outbox_dir else None
        res = resolve_series_folder_name(self.nas_dir, self.outbox_dir, "tvdb", "123", "Fallback")
        self.assertEqual(res, "IDMatchOutbox")

        # D) Fuzzy Fallback
        mock_find_by_id.side_effect = lambda dest, prov, sid: None
        mock_get_matched.return_value = "Die Sendung (2024)"
        res = resolve_series_folder_name(self.nas_dir, self.outbox_dir, "tvdb", "123", "Sendung")
        self.assertEqual(res, "Die Sendung (2024)")

    # 2. series-detect
    def test_series_detect_no_bias(self):
        from gui.api.search_api import handle_api_series_detect
        from flask import Flask
        app = Flask(__name__)

        # We need to mock os.path.exists and os.listdir to simulate multiple destinations
        with patch('gui.api.search_api.os.path.exists') as mock_exists, \
             patch('gui.api.search_api.os.listdir') as mock_listdir, \
             patch('gui.api.search_api.os.path.isdir') as mock_isdir, \
             patch('gui.api.search_api.ensure_nas_mounted') as mock_ensure, \
             patch('gui.api.search_api.load_settings') as mock_settings:

            mock_settings.return_value = {
                "nas_root": "/nas",
                "outbox_dir": "/outbox",
                "sync_categories": [{"nas_sub": "/Serien"}, {"nas_sub": "/Dokus"}]
            }
            mock_exists.return_value = True
            mock_isdir.return_value = True
            mock_ensure.return_value = True

            def listdir_side_effect(path):
                if path == "/nas/Serien":
                    return ["Other"]
                elif path == "/nas/Dokus":
                    return ["TheProject"]
                return []
            mock_listdir.side_effect = listdir_side_effect

            with app.test_request_context('/api/series-detect?project_name=TheProject&nas_destination_id=all'):
                resp = handle_api_series_detect()
                data = resp.get_json()
                self.assertEqual(data.get("show_name"), "TheProject")

    # 3. nas_renamer.apply_renames
    def test_nas_renamer_collision(self):
        target_dir = os.path.join(self.temp_dir, "RenameTarget")
        os.makedirs(target_dir)

        rename_plan = [
            {"rel_path": "file1.mkv", "proposed_rel_path": "A:B.mkv"},
            {"rel_path": "file2.mkv", "proposed_rel_path": "A - B.mkv"}
        ]

        # sanitize_filename will make A:B into A - B (or something similar depending on implementation)
        # Assuming sanitize_filename removes/replaces colons.
        res = apply_renames(target_dir, rename_plan)
        self.assertEqual(res["status"], "error")
        self.assertIn("Kollision", res["message"])

    # 4. generate_episode_nfo
    @patch("gui.mw_metadata.urllib.request.urlopen")
    def test_generate_episode_nfo_without_overrides(self, mock_urlopen):
        import json

        def urlopen_side_effect(req, *args, **kwargs):
            url = req.full_url if hasattr(req, 'full_url') else req
            mock_resp = MagicMock()
            mock_resp.status = 200
            if "login" in str(url):
                mock_resp.read.return_value = json.dumps({"data": {"token": "dummy_token"}}).encode('utf-8')
            else:
                mock_resp.read.return_value = json.dumps({
                    "data": {
                        "episodes": [
                            {"seasonNumber": 1, "number": 1, "name": "Pilot", "overview": "Plot...", "aired": "2020-01-01"}
                        ]
                    }
                }).encode('utf-8')
            mock_cm = MagicMock()
            mock_cm.__enter__.return_value = mock_resp
            return mock_cm

        mock_urlopen.side_effect = urlopen_side_effect

        target_folder = self.temp_dir
        filename_base = "S01E01"

        # call WITHOUT nfo_overrides
        res = generate_episode_nfo("tvdb", "123", 1, 1, target_folder, filename_base, nfo_overrides=None)

        self.assertTrue(res.get("nfo"))
        nfo_path = os.path.join(self.temp_dir, "S01E01.nfo")
        self.assertTrue(os.path.exists(nfo_path))
        with open(nfo_path, "r") as f:
            content = f.read()
            self.assertIn("<title>Pilot</title>", content)

    # 5. update_nfo_mw_data
    def test_update_nfo_mw_data_provider_inconsistency(self):
        nfo_path = os.path.join(self.temp_dir, "tvshow.nfo")
        initial_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<tvshow>
  <title>Test Show</title>
  <mw_data>
    <provider>tvdb</provider>
    <show_id>123</show_id>
    <source_url>http://tvdb/123</source_url>
    <resolved_topic>Test Show</resolved_topic>
    <last_sync>2000-01-01T00:00:00</last_sync>
  </mw_data>
</tvshow>'''
        with open(nfo_path, "w") as f:
            f.write(initial_xml)

        # Update with different provider
        update_nfo_mw_data(nfo_path, provider="tmdb_tv", show_id="999", source_url="http://tmdb", resolved_topic="Other")

        # Read back
        meta = read_nfo_metadata(nfo_path)
        mw = meta.get("mw_data", {})

        # Provider and ID should remain the old ones
        self.assertEqual(mw.get("provider"), "tvdb")
        self.assertEqual(mw.get("show_id"), "123")
        self.assertEqual(mw.get("source_url"), "http://tvdb/123")
        self.assertEqual(mw.get("resolved_topic"), "Test Show")

        # last_sync must be updated (not 2000-01-01)
        self.assertNotEqual(mw.get("last_sync"), "2000-01-01T00:00:00")
        self.assertTrue(len(mw.get("last_sync", "")) > 10)

if __name__ == "__main__":
    unittest.main()
