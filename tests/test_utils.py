import sys
import os
import shutil
import tempfile
import unittest
import unittest.mock
import json

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gui.core import utils, media
from gui import mw_metadata
import gui.api.endpoints as endpoints
import gui.core.helpers as helpers
import gui.core.transfers as transfers

class TestMediawerkzeugLogic(unittest.TestCase):
    def setUp(self):
        # Create temp environment
        self.test_dir = tempfile.mkdtemp()
        self.temp_home = os.path.join(self.test_dir, "fake_home")
        os.makedirs(self.temp_home, exist_ok=True)
        
        # Backup original variables and functions
        self.orig_data_dir = utils.DATA_DIR
        self.orig_profiles_dir = utils.PROFILES_DIR
        self.orig_history_file = utils.HISTORY_FILE
        self.orig_expanduser = os.path.expanduser
        self.orig_tmdb_key = mw_metadata.TMDB_API_KEY
        mw_metadata.TMDB_API_KEY = "a" * 32
        
        # Override paths to use temp dir
        utils.DATA_DIR = os.path.join(self.test_dir, "gui_data")
        utils.PROFILES_DIR = os.path.join(utils.DATA_DIR, "profiles")
        utils.HISTORY_FILE = os.path.join(utils.DATA_DIR, "konv_history.json")
        os.makedirs(utils.PROFILES_DIR, exist_ok=True)
        
        # Mock os.path.expanduser to redirect ~ to fake_home
        def mock_expanduser(path):
            if path.startswith("~"):
                return path.replace("~", self.temp_home)
            return self.orig_expanduser(path)
        os.path.expanduser = mock_expanduser

        # Mock send2trash to perform direct deletion to avoid macOS permission issues
        from unittest.mock import patch
        def mock_s2t_action(path):
            if os.path.exists(path):
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
        self.s2t_patcher = patch("send2trash.send2trash", side_effect=mock_s2t_action)
        self.s2t_patcher.start()

    def tearDown(self):
        # Stop send2trash patcher
        self.s2t_patcher.stop()

        # Restore original variables and functions
        utils.DATA_DIR = self.orig_data_dir
        utils.PROFILES_DIR = self.orig_profiles_dir
        utils.HISTORY_FILE = self.orig_history_file
        os.path.expanduser = self.orig_expanduser
        mw_metadata.TMDB_API_KEY = self.orig_tmdb_key

        # Modul-Cache des TVDb-Tokens zurücksetzen, damit ein in test_fetch_all_seasons
        # gesetztter Mock-Token nicht in andere Tests leakt.
        mw_metadata.tvdb_token = None
        mw_metadata.tvdb_token_time = 0

        # Clean up temp files
        shutil.rmtree(self.test_dir)

    def test_clean_show_name(self):
        # clean_show_name behält seit der Profil-Refaktorierung Groß-/Kleinschreibung und
        # Leerzeichen bei (Profil-Dateinamen sind im Title-Case-Format, z.B. "Heroes 2006.json").
        self.assertEqual(utils.clean_show_name("Breaking Bad [TMDB_TV]"), "Breaking Bad TMDB_TV")
        self.assertEqual(utils.clean_show_name("Kill Bill: Vol. 1"), "Kill Bill Vol. 1")
        self.assertEqual(utils.clean_show_name(""), "default")
        self.assertEqual(utils.clean_show_name(None), "default")

    def test_clean_series_name_for_fs(self):
        from gui import server
        self.assertEqual(server.clean_series_name_for_fs("Geheimnisse Asiens - Die schönsten Nationalparks (Mediathek Serie aus URL)"), "Geheimnisse Asiens - Die schönsten Nationalparks")
        self.assertEqual(server.clean_series_name_for_fs("Sendung mit der Maus (Freie Mediathek-Suche)"), "Sendung mit der Maus")
        self.assertEqual(server.clean_series_name_for_fs("Doctor Who (fernsehserien.de URL)"), "Doctor Who")
        self.assertEqual(server.clean_series_name_for_fs("Doku - Geheimnisse Asiens [ARTE]"), "Doku - Geheimnisse Asiens")
        self.assertEqual(server.clean_series_name_for_fs("Wildkatzen und Wildhunde (2022) [FR] [TMDB_TV]"), "Wildkatzen und Wildhunde (2022)")
        self.assertEqual(server.clean_series_name_for_fs("Heroes [US] [TMDB_TV]"), "Heroes")
        self.assertEqual(server.clean_series_name_for_fs("Wildkatzen_und_Wildhunde (Freie Mediathek-Suche)"), "Wildkatzen und Wildhunde")
        self.assertEqual(server.clean_series_name_for_fs("Wildkatzen & Wildhunde (4 Videos via URL)"), "Wildkatzen & Wildhunde")
        self.assertEqual(server.clean_series_name_for_fs("Wildkatzen & Wildhunde (Video via URL)"), "Wildkatzen & Wildhunde")
        self.assertEqual(server.clean_series_name_for_fs("Dokus (Mediathek Film aus URL)"), "Dokus")
        self.assertEqual(server.clean_series_name_for_fs("Some Show"), "Some Show")
        self.assertEqual(server.clean_series_name_for_fs(""), "")
        self.assertEqual(server.clean_series_name_for_fs(None), "")

    def test_clean_episode_title_for_filename(self):
        from gui.core.helpers import clean_episode_title_for_filename
        self.assertEqual(clean_episode_title_for_filename("Serengeti", "Serengeti - Wilde Geschichten"), "Wilde Geschichten")
        self.assertEqual(clean_episode_title_for_filename("Serengeti", "Serengeti: Wilde Geschichten"), "Wilde Geschichten")
        self.assertEqual(clean_episode_title_for_filename("Serengeti", "Serengeti Tag 1"), "Tag 1")
        self.assertEqual(clean_episode_title_for_filename("Serengeti", "Serengetis Löwen"), "Serengetis Löwen")
        self.assertEqual(clean_episode_title_for_filename("Entdeckung der Welt (Natur und Tiere) - Serengeti", "Serengeti - Wilde Geschichten"), "Wilde Geschichten")
        self.assertEqual(clean_episode_title_for_filename("Dark", "Dark Matter"), "Dark Matter")
        self.assertEqual(clean_episode_title_for_filename("Lost", "Lost and Found"), "Lost and Found")
        self.assertEqual(clean_episode_title_for_filename("", "Serengeti"), "Serengeti")
        self.assertEqual(clean_episode_title_for_filename("Serengeti", ""), "")
        self.assertEqual(clean_episode_title_for_filename(None, "Serengeti"), "Serengeti")
        self.assertEqual(clean_episode_title_for_filename("Serengeti", None), "")

    def test_filename_sanitization_and_length_limit(self):
        from gui import server
        self.assertEqual(server.sanitize_filename("A - B: C"), "A - B - C")
        self.assertEqual(server.sanitize_filename("A/B|C?D*E"), "A - B - CDE")
        long_name = "a" * 200
        truncated = server.limit_filename_length(long_name, 160)
        self.assertEqual(len(truncated), 160)
        self.assertTrue(truncated.endswith("a"))
        self.assertEqual(server.limit_filename_length("short name", 160), "short name")

    def test_series_name_normalization(self):
        from gui import server
        self.assertEqual(server.normalize_series_name("Die Sendung mit der Maus (1971)"), "sendungmitdermaus")
        self.assertEqual(server.normalize_series_name("The Simpsons [1989]"), "simpsons")

    def test_profile_load_save(self):
        profile = {
            "pcloud_sonstiges": "j",
            "auto_h265": "n",
            "schema": "absolut",
            "provider": "tmdb_tv"
        }
        success = utils.save_show_profile("Breaking Bad", profile)
        self.assertTrue(success)
        
        loaded = utils.load_show_profile("Breaking Bad")
        self.assertEqual(loaded["pcloud_sonstiges"], "j")
        self.assertEqual(loaded["auto_h265"], "n")
        self.assertEqual(loaded["schema"], "absolut")
        self.assertEqual(loaded["provider"], "tmdb_tv")
        self.assertTrue(loaded["is_custom"])

    def test_profile_migration(self):
        # Profil-Verzeichnis in die Test-Sandbox legen, damit der Test nicht in die
        # echten gui/data/profiles/ schreibt.
        profiles_dir = os.path.join(self.temp_home, "profiles")
        os.makedirs(profiles_dir, exist_ok=True)
        utils._MOCK_SETTINGS = {"profiles_path": profiles_dir}
        try:
            # Setup legacy directory
            legacy_dir = os.path.join(self.temp_home, ".config/mediawerkzeug/profiles")
            os.makedirs(legacy_dir, exist_ok=True)

            # Write legacy config file
            legacy_conf = os.path.join(legacy_dir, "Breaking Bad.conf")
            with open(legacy_conf, "w", encoding="utf-8") as f:
                f.write('PROFIL_PCLOUD_SONSTIGES="j"\n')
                f.write('PROFIL_AUTO_H265="j"\n')
                f.write('PROFIL_SCHEMA="absolut"\n')
                f.write('PROFIL_PROVIDER="tvdb"\n')

            # Load profile and verify it was migrated
            loaded = utils.load_show_profile("Breaking Bad")
            self.assertEqual(loaded["pcloud_sonstiges"], "j")
            self.assertEqual(loaded["auto_h265"], "j")
            self.assertEqual(loaded["schema"], "absolut")
            self.assertEqual(loaded["provider"], "tvdb")
            self.assertTrue(loaded["is_custom"])

            # Check that it saved locally as JSON. clean_show_name behält Groß-/Kleinschreibung
            # und Leerzeichen bei -> Dateiname "Breaking Bad.json".
            local_json_path = os.path.join(profiles_dir, "Breaking Bad.json")
            self.assertTrue(os.path.exists(local_json_path))
            with open(local_json_path, "r", encoding="utf-8") as f:
                local_data = json.load(f)
            self.assertEqual(local_data["provider"], "tvdb")
        finally:
            utils._MOCK_SETTINGS = None

    def test_profile_fallback_is_not_custom(self):
        # Profil-Verzeichnis in die Test-Sandbox legen
        profiles_dir = os.path.join(self.temp_home, "profiles")
        os.makedirs(profiles_dir, exist_ok=True)
        utils._MOCK_SETTINGS = {"profiles_path": profiles_dir}
        try:
            loaded = utils.load_show_profile("NonExistentShowName123")
            self.assertFalse(loaded["is_custom"])
        finally:
            utils._MOCK_SETTINGS = None

    def test_history_load_save(self):
        history = [
            {"quality": 22, "codec": "hevc", "ratio": 0.45},
            {"quality": 24, "codec": "hevc", "ratio": 0.38}
        ]
        success = utils.save_konv_history(history)
        self.assertTrue(success)
        
        loaded = utils.load_konv_history()
        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded[0]["quality"], 22)
        self.assertEqual(loaded[1]["ratio"], 0.38)

    def test_history_migration(self):
        # Write legacy history file
        legacy_file = os.path.join(self.temp_home, ".mw_konv_history")
        with open(legacy_file, "w", encoding="utf-8") as f:
            f.write("22|hevc|0.4500\n")
            f.write("24|hevc|0.3800\n")
            
        # Load history and verify it was migrated
        loaded = utils.load_konv_history()
        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded[0]["quality"], 22)
        self.assertEqual(loaded[0]["codec"], "hevc")
        self.assertEqual(loaded[0]["ratio"], 0.45)
        
        # Check local JSON path
        self.assertTrue(os.path.exists(utils.HISTORY_FILE))

    def test_clean_search_query(self):
        self.assertEqual(
            mw_metadata.clean_search_query("Breaking.Bad.S01.German.DD51.DL.1080p.BluRay.x264-TvR"),
            "Breaking Bad"
        )
        self.assertEqual(
            mw_metadata.clean_search_query("The.Simpsons.S30.German.1080p.HEVC.x265"),
            "The Simpsons"
        )
        self.assertEqual(
            mw_metadata.clean_search_query("Kill Bill The Whole Bloody Affair (2011)"),
            "Kill Bill The Whole Bloody Affair"
        )
        self.assertEqual(
            mw_metadata.clean_search_query("tt1234567"),
            "tt1234567"
        )
        self.assertEqual(
            mw_metadata.clean_search_query("tmdb:9876"),
            "tmdb:9876"
        )
        self.assertEqual(
            mw_metadata.clean_search_query("Das.A.Team.Der.Film.EXTENDED.2010.German.DL.AC3.1080p.BluRay.x265-FuN.mkv"),
            "Das A Team Der Film"
        )
        self.assertEqual(
            mw_metadata.clean_search_query("Das.A.Team.Der.Film.EXTENDED.2010.German.DL.AC3.1080p.BluRay.x265-FuN"),
            "Das A Team Der Film"
        )
        self.assertEqual(
            mw_metadata.clean_search_query("Spider-Man.No.Way.Home.2021.UHD.HDR.Dolby.Vision.10bit.dovi.mkv"),
            "Spider Man No Way Home"
        )
        self.assertEqual(
            mw_metadata.clean_search_query("sh-Immortal Combat - Kampf der Legenden 2026 German 1080p WEB H264-SiXTYNiNE"),
            "Immortal Combat Kampf der Legenden"
        )
        self.assertEqual(
            mw_metadata.clean_search_query("He-Man"),
            "He Man"
        )
        self.assertEqual(
            mw_metadata.clean_search_query("X-Men"),
            "X Men"
        )

    def test_calculate_match_score(self):
        # High match score (same titles and years)
        score1 = mw_metadata.calculate_match_score(
            "Kill Bill (2003)",
            "Kill Bill (2003) [TMDB]"
        )
        # Year mismatch penalty
        score2 = mw_metadata.calculate_match_score(
            "Kill Bill (2003)",
            "Kill Bill (2004) [TMDB]"
        )
        # Partial match
        score3 = mw_metadata.calculate_match_score(
            "Kill Bill",
            "Kill Bill Vol 1 (2003)"
        )
        self.assertTrue(score1 > score2)
        self.assertTrue(score1 > score3)
        self.assertEqual(score2, 0.0) # Year mismatch results in a heavy penalty

    def test_conversion_estimation_fallbacks(self):
        # With no history, quality 60 should return 0.50
        ratio = media.konvertierung_schaetzen("nonexistent_file.mkv", 60)
        self.assertEqual(ratio, 0.50)
        
        # Quality <= 50 should return 0.40
        self.assertEqual(media.konvertierung_schaetzen("nonexistent_file.mkv", 50), 0.40)
        # Quality <= 70 should return 0.65
        self.assertEqual(media.konvertierung_schaetzen("nonexistent_file.mkv", 70), 0.65)
        # Quality > 70 should return 0.80
        self.assertEqual(media.konvertierung_schaetzen("nonexistent_file.mkv", 80), 0.80)

    def test_historical_ratio_median(self):
        # Let's add some mock history entries
        history = [
            {"quality": 60, "codec": "hevc", "ratio": 0.40},
            {"quality": 60, "codec": "hevc", "ratio": 0.50},
            {"quality": 60, "codec": "hevc", "ratio": 0.60}
        ]
        utils.save_konv_history(history)
        
        with unittest.mock.patch("sys.platform", "linux"):
            with unittest.mock.patch.dict(os.environ, {"MW_RUNTIME": "docker"}):
                # Median of [0.40, 0.50, 0.60] is 0.50
                self.assertEqual(media.konvertierung_schaetzen("nonexistent_file.mkv", 60), 0.50)
                
                # Add another to make it even: [0.40, 0.45, 0.50, 0.60] -> median is (0.45 + 0.50) / 2 = 0.475
                # The legacy entries ("hevc") map to "hevc_libx265"
                media.add_conversion_to_history(60, "hevc_libx265", 0.45)
                self.assertEqual(media.konvertierung_schaetzen("nonexistent_file.mkv", 60), 0.475)

    def test_conversion_estimation_test_encode(self):
        import subprocess
        video_path = os.path.join(self.test_dir, "test_mock_video.mkv")
        try:
            subprocess.run([
                "ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=2:size=320x240:rate=25",
                "-c:v", "h264", "-t", "2", video_path
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            
            ratio = media.konvertierung_schaetzen(video_path, 60)
            self.assertTrue(isinstance(ratio, float))
            self.assertTrue(0.01 <= ratio <= 5.0)
        finally:
            if os.path.exists(video_path):
                os.remove(video_path)

    def test_rclone_progress_regex(self):
        import re
        rclone_pattern = re.compile(r'Transferred:\s+[\d.]+(?:\s*[a-zA-Z]+)?\s+/\s+[\d.]+\s*[a-zA-Z]+,\s+(\d+)%')
        
        # Should match bytes-based lines
        line1 = "Transferred:   \t    1.821 GiB / 5.927 GiB, 30%, 15.421 MiB/s, ETA 4m33s"
        match1 = rclone_pattern.search(line1)
        self.assertIsNotNone(match1)
        self.assertEqual(match1.group(1), "30")
        
        line2 = "Transferred:   \t   13.235 MiB / 15.918 MiB, 83%, 1.259 MiB/s, ETA 2s"
        match2 = rclone_pattern.search(line2)
        self.assertIsNotNone(match2)
        self.assertEqual(match2.group(1), "83")

        line3 = "Transferred:            0 / 100 B, 0%, 0 B/s, ETA -"
        match3 = rclone_pattern.search(line3)
        self.assertIsNotNone(match3)
        self.assertEqual(match3.group(1), "0")

        # Should NOT match file-count percentage lines
        line4 = "Transferred:            5 / 6, 83%"
        match4 = rclone_pattern.search(line4)
        self.assertIsNone(match4)

        line5 = "Transferred:            0 / 1, 0%"
        match5 = rclone_pattern.search(line5)
        self.assertIsNone(match5)

    def test_delete_project_security(self):
        from gui.server import GUIRequestHandler
        
        # Create a mock/dummy handler
        class DummyHandler:
            def __init__(self):
                self.sent_json = None
                self.logged_messages = []
            def send_json(self, data):
                self.sent_json = data
            
        # We need to mock settings and log_message
        import gui.server as server
        orig_load_settings = endpoints.load_settings
        orig_log_message = helpers.log_message
        
        test_inbox = os.path.join(self.test_dir, "test_inbox")
        os.makedirs(test_inbox, exist_ok=True)
        
        utils._MOCK_SETTINGS = {"inbox_dir": test_inbox}
        
        # Mock log_message to capture it
        dummy = DummyHandler()
        helpers.log_message = lambda msg: dummy.logged_messages.append(msg)
        
        try:
            # 1. Valid folder deletion
            valid_folder = os.path.join(test_inbox, "valid_proj")
            os.makedirs(valid_folder, exist_ok=True)
            self.assertTrue(os.path.exists(valid_folder))
            
            GUIRequestHandler.handle_api_delete_project(dummy, {"project": "valid_proj"})
            self.assertEqual(dummy.sent_json, {"status": "success"})
            self.assertFalse(os.path.exists(valid_folder))
            
            # 2. Path traversal attempt (parent dir deletion)
            parent_traversal = "../outside_proj"
            dummy.sent_json = None
            GUIRequestHandler.handle_api_delete_project(dummy, {"project": parent_traversal})
            self.assertEqual(dummy.sent_json["status"], "error")
            self.assertIn("Ungültiger", dummy.sent_json["error"])
            
            # 3. Root folder deletion attempt
            dummy.sent_json = None
            GUIRequestHandler.handle_api_delete_project(dummy, {"project": "."})
            self.assertEqual(dummy.sent_json["status"], "error")
            self.assertIn("Ungültiger", dummy.sent_json["error"])

            # 4. Empty project param
            dummy.sent_json = None
            GUIRequestHandler.handle_api_delete_project(dummy, {})
            self.assertEqual(dummy.sent_json["status"], "error")
            
        finally:
            utils._MOCK_SETTINGS = None
            helpers.log_message = orig_log_message

    def test_tv_processing_skip_original_on_convert(self):
        import subprocess
        import gui.server as server
        from gui import mw_metadata
        
        # Setup mock directories
        test_inbox = os.path.join(self.test_dir, "inbox")
        test_outbox = os.path.join(self.test_dir, "outbox")
        test_nas = os.path.join(self.test_dir, "nas")
        
        os.makedirs(test_inbox)
        os.makedirs(test_outbox)
        os.makedirs(test_nas)
        
        # Create a mock series project folder
        project_dir = os.path.join(test_inbox, "Maus_Project")
        os.makedirs(project_dir)
        
        # Create a mock original video file in the project
        orig_video = os.path.join(project_dir, "maus_s56e01.mp4")
        with open(orig_video, "w") as f:
            f.write("mock video content")
            
        # Create a mock subtitle file
        subtitle_file = os.path.join(project_dir, "maus_s56e01.srt")
        with open(subtitle_file, "w") as f:
            f.write("mock subtitle")

        # Mock server functions. WICHTIG: process_worker läuft im Namensraum von
        # gui.workers.processor, daher müssen dort die Funktionen gepatcht werden
        # (ein Patch auf gui.server wirkt nicht auf die Aufrufe im Worker).
        import gui.workers.processor as processor
        orig_load_settings = endpoints.load_settings
        orig_ensure_nas = processor.ensure_nas_mounted
        orig_run_rsync = processor.run_rsync_with_progress
        orig_run_ffmpeg = processor.run_ffmpeg_with_progress
        orig_subprocess_run = subprocess.run
        orig_subprocess_check_output = subprocess.check_output
        
        orig_fetch_tmdb = server.mw_metadata.fetch_tmdb_tv
        orig_gen_show_nfo = server.mw_metadata.generate_tvshow_nfo
        orig_gen_ep_nfo = server.mw_metadata.generate_episode_nfo
        
        utils._MOCK_SETTINGS = {
            "inbox_dir": test_inbox,
            "outbox_dir": test_outbox,
            "nas_root": test_nas,
            # Die neue Architektur entscheidet anhand von storage_targets, wohin kopiert
            # wird. _MOCK_SETTINGS umgeht die Defaults, daher hier explizit setzen.
            "storage_targets": [
                {"id": "nas", "type": "nas", "root_path": test_nas, "enabled": True}
            ],
            "sync_categories": [
                {"id": "2", "name": "Serien", "nas_sub": "/Serien", "pcloud_remote": "pcloud:04_Serien"}
            ]
        }
        
        processor.ensure_nas_mounted = lambda: True

        # Mock rsync to copy files (since process_worker expects rsync to do the copy)
        def mock_rsync(src, dst, task_id=None, move=False, *args, **kwargs):
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy(src, dst)
            return True
        processor.run_rsync_with_progress = mock_rsync
        
        # Mock ffmpeg to simulate converting: creates .mkv and doesn't crash
        def mock_ffmpeg(cmd, filepath, task_id=None, log_queue=None):
            # cmd is [..., temp_output]
            temp_out = cmd[-1]
            with open(temp_out, "w") as f:
                f.write("mock converted video content")
            return True
        processor.run_ffmpeg_with_progress = mock_ffmpeg
        
        # Mock subprocess.run to prevent Finder from opening
        def mock_run(cmd, *args, **kwargs):
            if isinstance(cmd, list) and cmd[0] == "open":
                return subprocess.CompletedProcess(cmd, 0)
            return orig_subprocess_run(cmd, *args, **kwargs)
        subprocess.run = mock_run
        def mock_check_output(cmd, *args, **kwargs):
            if cmd[0] == 'ffprobe':
                return "1500"
            return orig_subprocess_check_output(cmd, *args, **kwargs)
        subprocess.check_output = mock_check_output
        
        # Mock metadata calls
        server.mw_metadata.fetch_tmdb_tv = lambda show_id, season, lang: {
            "1": {"title": "Die Maus wird 50"}
        }
        server.mw_metadata.generate_tvshow_nfo = lambda provider, show_id, path, *args, **kwargs: "success"
        server.mw_metadata.generate_episode_nfo = lambda provider, show_id, season, ep, path, title, *args, **kwargs: "success"
        
        params = {
            "media_type": "tv",
            "project_name": "Maus_Project",
            "show_name": "Die Sendung mit der Maus",
            "show_id": "12345",
            "provider": "tmdb_tv",
            "season": "56",
            "mappings": {"maus_s56e01.mp4": 1},
            "convert": True,
            "quality": 60,
            "delete_original": False,  # Keep original file in input
            "copy_to_nas": True,
            "nas_destination_id": "2",
            "explicit_renames": [
                {"old": "maus_s56e01.mp4", "new": "Die Sendung mit der Maus - S56E01 - Die Maus wird 50.mp4"},
                {"old": "maus_s56e01.srt", "new": "Die Sendung mit der Maus - S56E01 - Die Maus wird 50.srt"}
            ],
            "explicit_subs": [],
            "explicit_junk": []
        }
        
        try:
            server.process_worker(params)
            
            # Now verify output structure
            # Episode folder in Outbox:
            # outbox/Serien/Die Sendung mit der Maus/Staffel 56/Die Sendung mit der Maus - S56E01 - Die Maus wird 50/
            ep_dir_outbox = os.path.join(
                test_outbox, "Serien", "Die Sendung mit der Maus", "Staffel 56", 
                "Die Sendung mit der Maus - S56E01 - Die Maus wird 50"
            )
            self.assertTrue(os.path.exists(ep_dir_outbox))
            
            # Converted video file .mkv exists
            self.assertTrue(os.path.exists(os.path.join(ep_dir_outbox, "Die Sendung mit der Maus - S56E01 - Die Maus wird 50.mkv")))
            # Subtitle file exists
            self.assertTrue(os.path.exists(os.path.join(ep_dir_outbox, "Die Sendung mit der Maus - S56E01 - Die Maus wird 50.srt")))
            
            # Original unconverted video file is NOT in the outbox
            self.assertFalse(os.path.exists(os.path.join(ep_dir_outbox, "Die Sendung mit der Maus - S56E01 - Die Maus wird 50.mp4")))
            
            # Episode folder on NAS:
            # nas/Serien/Die Sendung mit der Maus/Staffel 56/Die Sendung mit der Maus - S56E01 - Die Maus wird 50/
            ep_dir_nas = os.path.join(
                test_nas, "Serien", "Die Sendung mit der Maus", "Staffel 56",
                "Die Sendung mit der Maus - S56E01 - Die Maus wird 50"
            )
            self.assertTrue(os.path.exists(ep_dir_nas))
            self.assertTrue(os.path.exists(os.path.join(ep_dir_nas, "Die Sendung mit der Maus - S56E01 - Die Maus wird 50.mkv")))
            self.assertTrue(os.path.exists(os.path.join(ep_dir_nas, "Die Sendung mit der Maus - S56E01 - Die Maus wird 50.srt")))
            self.assertFalse(os.path.exists(os.path.join(ep_dir_nas, "Die Sendung mit der Maus - S56E01 - Die Maus wird 50.mp4")))
            
            # Original file remains in inbox/project directory (since delete_original=False)
            self.assertTrue(os.path.exists(os.path.join(project_dir, "Die Sendung mit der Maus - S56E01 - Die Maus wird 50.mp4")))
            
        finally:
            utils._MOCK_SETTINGS = None
            processor.ensure_nas_mounted = orig_ensure_nas
            processor.run_rsync_with_progress = orig_run_rsync
            processor.run_ffmpeg_with_progress = orig_run_ffmpeg
            subprocess.run = orig_subprocess_run
            subprocess.check_output = orig_subprocess_check_output

            server.mw_metadata.fetch_tmdb_tv = orig_fetch_tmdb
            server.mw_metadata.generate_tvshow_nfo = orig_gen_show_nfo
            server.mw_metadata.generate_episode_nfo = orig_gen_ep_nfo

    def test_process_worker_force_absolute_season_1(self):
        import gui.server as server
        import subprocess
        
        # Setup directories
        test_inbox = os.path.join(self.test_dir, "inbox_worker_force")
        test_outbox = os.path.join(self.test_dir, "outbox_worker_force")
        test_nas = os.path.join(self.test_dir, "nas_worker_force")
        
        project_dir = os.path.join(test_inbox, "Elefant_Project")
        os.makedirs(project_dir, exist_ok=True)
        os.makedirs(test_outbox, exist_ok=True)
        os.makedirs(test_nas, exist_ok=True)
        
        # Create input file
        filename = "Elefant_Tiger_Co_(381)_2026.mp4"
        with open(os.path.join(project_dir, filename), "w") as f:
            f.write("dummy video data")
            
        # Mock load_settings
        orig_load_settings = endpoints.load_settings
        utils._MOCK_SETTINGS = {
            "inbox_dir": test_inbox,
            "outbox_dir": test_outbox,
            "nas_root": test_nas,
            # storage_targets steuert in der neuen Architektur das Kopierziel.
            "storage_targets": [
                {"id": "nas", "type": "nas", "root_path": test_nas, "enabled": True}
            ],
            "sync_categories": [
                {"id": "2", "name": "Serien", "nas_sub": "/Serien"}
            ]
        }
        
        # Save original imports/functions to restore later. process_worker läuft im
        # Namensraum von gui.workers.processor -> dort patchen, nicht auf gui.server.
        import gui.workers.processor as processor
        orig_ensure_nas = processor.ensure_nas_mounted
        orig_run_rsync = processor.run_rsync_with_progress
        orig_run_ffmpeg = processor.run_ffmpeg_with_progress
        orig_subprocess_run = subprocess.run
        orig_subprocess_check_output = subprocess.check_output
        orig_fetch_tvdb = server.mw_metadata.fetch_tvdb
        orig_gen_show_nfo = server.mw_metadata.generate_tvshow_nfo
        orig_gen_ep_nfo = server.mw_metadata.generate_episode_nfo
        
        # Mock dependencies
        processor.ensure_nas_mounted = lambda: True
        
        def mock_run_rsync(src, dest, *args, **kwargs):
            # Simulate rsync copying
            if os.path.isdir(src):
                import shutil
                shutil.copytree(src, dest, dirs_exist_ok=True)
            else:
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(dest, "w") as out:
                    out.write("copied")
            return True
        processor.run_rsync_with_progress = mock_run_rsync
        
        def mock_run_ffmpeg(cmd, filepath, *args, **kwargs):
            # cmd is list. find output filename and touch it
            # ffmpeg -i input -c:v libx265 -crf 28 output.mkv
            out_file = cmd[-1]
            os.makedirs(os.path.dirname(out_file), exist_ok=True)
            with open(out_file, "w") as f:
                f.write("converted x265")
            return True
        processor.run_ffmpeg_with_progress = mock_run_ffmpeg
        
        # Mock subprocess run for ffprobe
        def mock_run(cmd, *args, **kwargs):
            class MockCompletedProcess:
                def __init__(self):
                    self.returncode = 0
                    self.stdout = b"1000000" # Dummy size
                    self.stderr = b""
            return MockCompletedProcess()
        subprocess.run = mock_run
        def mock_check_output(cmd, *args, **kwargs):
            if cmd[0] == 'ffprobe':
                return "1500"
            return orig_subprocess_check_output(cmd, *args, **kwargs)
        subprocess.check_output = mock_check_output
        
        # Mock metadata calls
        server.mw_metadata.fetch_tvdb = lambda show_id, season, lang: {
            "1": {"title": "In der Ruhe liegt die Kraft", "date": "2026-01-01", "absolute_number": 381}
        }
        server.mw_metadata.generate_tvshow_nfo = lambda provider, show_id, path, *args, **kwargs: "success"
        
        nfo_calls = []
        def track_gen_nfo(provider, show_id, season, episode, target_folder, filename_base, force_season=None, force_episode=None, *args, **kwargs):
            nfo_calls.append({
                "season": season, "episode": episode,
                "force_season": force_season, "force_episode": force_episode
            })
            # create dummy nfo file so verification passes
            nfo_path = os.path.join(target_folder, f"{filename_base}.nfo")
            with open(nfo_path, "w") as f:
                f.write("<episodedetails></episodedetails>")
            return "success"
        server.mw_metadata.generate_episode_nfo = track_gen_nfo
        
        params = {
            "media_type": "tv",
            "project_name": "Elefant_Project",
            "show_name": "Elefant, Tiger und Co.",
            "show_id": "249482",
            "provider": "tvdb",
            "season": "2026",
            "mappings": {
                "Elefant_Tiger_Co_(381)_2026.mp4": "1"
            },
            "convert": True,
            "quality": 60,
            "delete_original": False,
            "copy_to_nas": True,
            "nas_destination_id": "2",
            "force_absolute_season_1": True,
            "explicit_renames": [
                {"old": "Elefant_Tiger_Co_(381)_2026.mp4", "new": "Elefant, Tiger und Co. - S01E381 - In der Ruhe liegt die Kraft.mp4"}
            ],
            "explicit_subs": [],
            "explicit_junk": []
        }
        
        try:
            server.process_worker(params)
            
            # Now verify output structure - season folder should be "Staffel 1"
            ep_dir_nas = os.path.join(
                test_nas, "Serien", "Elefant, Tiger und Co.", "Staffel 1",
                "Elefant, Tiger und Co. - S01E381 - In der Ruhe liegt die Kraft"
            )
            self.assertTrue(os.path.exists(ep_dir_nas))
            self.assertTrue(os.path.exists(os.path.join(ep_dir_nas, "Elefant, Tiger und Co. - S01E381 - In der Ruhe liegt die Kraft.mkv")))
            self.assertTrue(os.path.exists(os.path.join(ep_dir_nas, "Elefant, Tiger und Co. - S01E381 - In der Ruhe liegt die Kraft.nfo")))
            
            # Verify nfo generator parameters
            self.assertEqual(len(nfo_calls), 1)
            # Original S2026E1 lookup is still used for TVDb, but forced S01E381 is passed as force_* parameters to write to XML
            self.assertEqual(nfo_calls[0]["season"], "2026")
            self.assertEqual(nfo_calls[0]["episode"], "1")
            self.assertEqual(nfo_calls[0]["force_season"], 1)
            self.assertEqual(nfo_calls[0]["force_episode"], 381)
        finally:
            utils._MOCK_SETTINGS = None
            processor.ensure_nas_mounted = orig_ensure_nas
            processor.run_rsync_with_progress = orig_run_rsync
            processor.run_ffmpeg_with_progress = orig_run_ffmpeg
            subprocess.run = orig_subprocess_run
            subprocess.check_output = orig_subprocess_check_output
            server.mw_metadata.fetch_tvdb = orig_fetch_tvdb
            server.mw_metadata.generate_tvshow_nfo = orig_gen_show_nfo
            server.mw_metadata.generate_episode_nfo = orig_gen_ep_nfo

    @unittest.mock.patch('urllib.request.urlopen')
    def test_fetch_all_seasons(self, mock_urlopen):
        import json

        def side_effect(req, *args, **kwargs):
            # *args/**kwargs, weil der Produktivcode urlopen(req, timeout=10) aufruft.
            url = req.full_url if hasattr(req, 'full_url') else req
            
            # Helper to return a mock response
            class MockResponse:
                def __init__(self, data):
                    self.data = json.dumps(data).encode('utf-8')
                def read(self):
                    return self.data
                def __enter__(self):
                    return self
                def __exit__(self, exc_type, exc_val, exc_tb):
                    pass
            
            if "login" in url:
                return MockResponse({"data": {"token": "mock_token"}})
            elif "episodes/default" in url:
                if "page=0" in url:
                    return MockResponse({
                        "data": {
                            "episodes": [
                                {"seasonNumber": 1, "number": 1, "name": "Ep1", "aired": "2020-01-01"},
                                {"seasonNumber": 2, "number": 3, "name": "Ep3", "aired": "2020-02-02"}
                            ]
                        },
                        "links": {"next": "http://mock-next-page"}
                    })
                else:
                    return MockResponse({"data": {"episodes": []}})
            elif "tvmaze.com/shows" in url:
                return MockResponse([
                    {"season": 1, "number": 1, "name": "MazeEp1", "airdate": "2020-01-01"},
                    {"season": 2, "number": 2, "name": "MazeEp2", "airdate": "2020-02-02"}
                ])
            elif "/tv/12345?api_key=" in url:
                return MockResponse({
                    "seasons": [
                        {"season_number": 1},
                        {"season_number": 2}
                    ]
                })
            elif "/tv/12345/season/1" in url:
                return MockResponse({
                    "episodes": [
                        {"episode_number": 1, "name": "TmdbS1E1", "air_date": "2020-01-01"}
                    ]
                })
            elif "/tv/12345/season/2" in url:
                return MockResponse({
                    "episodes": [
                        {"episode_number": 5, "name": "TmdbS2E5", "air_date": "2020-02-02"}
                    ]
                })
            return MockResponse({})
            
        mock_urlopen.side_effect = side_effect
        
        # Test TVDB season='all'
        tvdb_res = mw_metadata.fetch_tvdb("12345", "all")
        self.assertEqual(tvdb_res, {
            "S01E01": {"title": "Ep1", "date": "2020-01-01", "absolute_number": None},
            "S02E03": {"title": "Ep3", "date": "2020-02-02", "absolute_number": None}
        })
        
        # Test TVMaze season='all'
        tvmaze_res = mw_metadata.fetch_tvmaze("12345", "all")
        self.assertEqual(tvmaze_res, {
            "S01E01": {"title": "MazeEp1", "date": "2020-01-01"},
            "S02E02": {"title": "MazeEp2", "date": "2020-02-02"}
        })
        
        # Test TMDb season='all'
        tmdb_res = mw_metadata.fetch_tmdb_tv("12345", "all")
        self.assertEqual(tmdb_res, {
            "S01E01": {"title": "TmdbS1E1", "date": "2020-01-01"},
            "S02E05": {"title": "TmdbS2E5", "date": "2020-02-02"}
        })

    @unittest.mock.patch('urllib.request.urlopen')
    def test_tvdb_search_relevance(self, mock_urlopen):
        import json

        def side_effect(req, *args, **kwargs):
            url = req.full_url if hasattr(req, 'full_url') else req

            class MockResponse:
                def __init__(self, data):
                    self.data = json.dumps(data).encode('utf-8')
                def read(self):
                    return self.data
                def __enter__(self):
                    return self
                def __exit__(self, exc_type, exc_val, exc_tb):
                    pass

            if "login" in url:
                return MockResponse({"data": {"token": "mock_token"}})
            elif "api4.thetvdb.com/v4/search" in url:
                items = []
                # First 10 noise/fan projects
                for i in range(10):
                    items.append({
                        "tvdb_id": f"fan_{i}",
                        "name": f"Dragon Ball Fan Project {i}",
                        "year": "2020",
                        "country": "USA",
                        "translations": {}
                    })
                # 11th item (index 10) is the official Japanese series with German translation
                items.append({
                    "tvdb_id": "76666",
                    "name": "ドラゴンボール",
                    "year": "1986",
                    "country": "JPN",
                    "translations": {
                        "deu": "Dragon Ball"
                    }
                })
                # Additional trailing items
                for i in range(5):
                    items.append({
                        "tvdb_id": f"other_{i}",
                        "name": f"Other DB Show {i}",
                        "year": "2021",
                        "country": "USA",
                        "translations": {}
                    })
                return MockResponse({"data": items})
            elif "api.themoviedb.org" in url:
                return MockResponse({"results": []})
            elif "api.tvmaze.com" in url:
                return MockResponse([])
            return MockResponse({})

        mock_urlopen.side_effect = side_effect

        # Run search
        results = mw_metadata.search_all_db("Dragon Ball")

        # Must find the official series
        self.assertTrue(len(results) > 0)
        first_result = results[0]
        self.assertEqual(first_result["id"], "76666")
        self.assertEqual(first_result["provider"], "tvdb")
        self.assertIn("Dragon Ball (1986)", first_result["name"])
        self.assertIn("[TVDB]", first_result["name"])

    @unittest.mock.patch('urllib.request.urlopen')
    @unittest.mock.patch('tempfile.gettempdir')
    def test_tvdb_episode_nfo_empty_overrides(self, mock_gettempdir, mock_urlopen):
        import xml.etree.ElementTree as ET
        mock_gettempdir.return_value = self.test_dir
        mw_metadata.tvdb_token = None

        def side_effect(req, *args, **kwargs):
            url = req.full_url if hasattr(req, 'full_url') else req

            class MockResponse:
                def __init__(self, data):
                    self.data = json.dumps(data).encode('utf-8')
                def read(self):
                    return self.data
                def __enter__(self):
                    return self
                def __exit__(self, exc_type, exc_val, exc_tb):
                    pass

            if "login" in url:
                return MockResponse({"data": {"token": "mocked_tvdb_token"}})
            elif "episodes/default/deu" in url:
                return MockResponse({
                    "data": {
                        "episodes": [
                            {
                                "id": 123456,
                                "name": "Soll-Titel auf Deutsch",
                                "overview": "Soll-Plot auf Deutsch",
                                "seasonNumber": 1,
                                "number": 1,
                                "aired": "1986-02-26",
                                "score": 8.5
                            }
                        ]
                    }
                })
            return MockResponse({})

        mock_urlopen.side_effect = side_effect

        nfo_overrides = {
            "title": "",
            "plot": "",
            "aired": ""
        }

        res = mw_metadata.generate_episode_nfo(
            provider="tvdb",
            show_id="76666",
            season=1,
            episode=1,
            target_folder=self.test_dir,
            filename_base="Dragon Ball - S01E01",
            nfo_overrides=nfo_overrides
        )

        self.assertTrue(res["nfo"])

        nfo_path = os.path.join(self.test_dir, "Dragon Ball - S01E01.nfo")
        self.assertTrue(os.path.exists(nfo_path))

        tree = ET.parse(nfo_path)
        root = tree.getroot()

        title_el = root.find("title")
        plot_el = root.find("plot")
        aired_el = root.find("aired")

        self.assertEqual(title_el.text, "Soll-Titel auf Deutsch")
        self.assertEqual(plot_el.text, "Soll-Plot auf Deutsch")
        self.assertEqual(aired_el.text, "1986-02-26")

    def test_manual_mode_metadata(self):
        # Test generate_tvshow_nfo in manual mode
        import xml.etree.ElementTree as ET
        target_dir = self.test_dir
        
        meta = {
            "title": "Meine Doku-Reihe",
            "plot": "Eine interessante Dokumentation über die Natur.",
            "year": "2026"
        }
        meta_json = json.dumps(meta)
        
        # Test NFO generation
        res = mw_metadata.generate_tvshow_nfo("manual", meta_json, target_dir)
        self.assertTrue(res["nfo"])
        
        tvshow_nfo_path = os.path.join(target_dir, "tvshow.nfo")
        self.assertTrue(os.path.exists(tvshow_nfo_path))
        
        # Parse XML to verify content
        tree = ET.parse(tvshow_nfo_path)
        root = tree.getroot()
        self.assertEqual(root.find("title").text, "Meine Doku-Reihe")
        self.assertEqual(root.find("plot").text, "Eine interessante Dokumentation über die Natur.")
        self.assertEqual(root.find("year").text, "2026")
        self.assertEqual(root.find("mw_provider").text, "manual")
        
        # Test generate_episode_nfo in manual mode
        ep_meta = {
            "title": "Die Wüste",
            "episode": 1,
            "plot": "Über das Leben in kargen Landschaften."
        }
        
        res_ep = mw_metadata.generate_episode_nfo("manual", "unused_show_id", 1, ep_meta, target_dir, "ep1_cleaned")
        self.assertTrue(res_ep["nfo"])
        
        ep_nfo_path = os.path.join(target_dir, "ep1_cleaned.nfo")
        self.assertTrue(os.path.exists(ep_nfo_path))
        
        tree_ep = ET.parse(ep_nfo_path)
        root_ep = tree_ep.getroot()
        self.assertEqual(root_ep.find("title").text, "Die Wüste")
        self.assertEqual(root_ep.find("season").text, "1")
        self.assertEqual(root_ep.find("episode").text, "1")
        self.assertEqual(root_ep.find("plot").text, "Über das Leben in kargen Landschaften.")

    def test_generate_episode_nfo_fallback(self):
        import xml.etree.ElementTree as ET
        target_dir = os.path.join(self.test_dir, "fallback_nfo_test")
        os.makedirs(target_dir, exist_ok=True)
        
        # Test Case 1: TMDB failure fallback (404/Exception)
        res = mw_metadata.generate_episode_nfo("tmdb_tv", "999999", 1, 4, target_dir, "ep4_tmdb_fallback")
        self.assertTrue(res.get("nfo"))
        self.assertFalse(res.get("thumb"))
        self.assertIn("Fallback", res.get("msg", ""))
        
        ep_nfo_path = os.path.join(target_dir, "ep4_tmdb_fallback.nfo")
        self.assertTrue(os.path.exists(ep_nfo_path))
        
        tree_ep = ET.parse(ep_nfo_path)
        root_ep = tree_ep.getroot()
        self.assertEqual(root_ep.find("title").text, "Folge 4")
        self.assertEqual(root_ep.find("season").text, "1")
        self.assertEqual(root_ep.find("episode").text, "4")
        self.assertTrue("Details konnten nicht geladen werden" in root_ep.find("plot").text)

        # Test Case 2: TVDB failure fallback (not found)
        orig_get_token = mw_metadata.get_tvdb_token
        mw_metadata.get_tvdb_token = lambda: "fake_token"
        
        res_tvdb = mw_metadata.generate_episode_nfo("tvdb", "nonexistent_show_id", 1, 4, target_dir, "ep4_tvdb_fallback")
        self.assertTrue(res_tvdb.get("nfo"))
        self.assertIn("nicht gefunden", res_tvdb.get("msg", ""))
        
        ep_nfo_path_tvdb = os.path.join(target_dir, "ep4_tvdb_fallback.nfo")
        self.assertTrue(os.path.exists(ep_nfo_path_tvdb))
        
        tree_ep_tvdb = ET.parse(ep_nfo_path_tvdb)
        root_ep_tvdb = tree_ep_tvdb.getroot()
        self.assertEqual(root_ep_tvdb.find("title").text, "Folge 4")
        self.assertEqual(root_ep_tvdb.find("season").text, "1")
        self.assertEqual(root_ep_tvdb.find("episode").text, "4")
        self.assertTrue("Episode online bei TVDB nicht gefunden" in root_ep_tvdb.find("plot").text)
        
        mw_metadata.get_tvdb_token = orig_get_token

    def test_nfo_overrides(self):
        import xml.etree.ElementTree as ET
        target_dir = os.path.join(self.test_dir, "overrides_nfo_test")
        os.makedirs(target_dir, exist_ok=True)
        
        # 1. Test generate_tvshow_nfo with overrides
        overrides = {
            "title": "Custom Show Title",
            "plot": "Custom Show Plot",
            "year": "2024"
        }
        res_show = mw_metadata.generate_tvshow_nfo("manual", "unused", target_dir, nfo_overrides=overrides)
        self.assertTrue(res_show["nfo"])
        
        show_nfo_path = os.path.join(target_dir, "tvshow.nfo")
        self.assertTrue(os.path.exists(show_nfo_path))
        tree_show = ET.parse(show_nfo_path)
        root_show = tree_show.getroot()
        self.assertEqual(root_show.find("title").text, "Custom Show Title")
        self.assertEqual(root_show.find("plot").text, "Custom Show Plot")
        self.assertEqual(root_show.find("year").text, "2024")
        
        # 2. Test generate_episode_nfo with overrides
        ep_overrides = {
            "title": "Custom Episode Title",
            "plot": "Custom Episode Plot",
            "aired": "2024-05-23"
        }
        res_ep = mw_metadata.generate_episode_nfo("manual", "unused", 1, 2, target_dir, "episode_custom", nfo_overrides=ep_overrides)
        self.assertTrue(res_ep["nfo"])
        
        ep_nfo_path = os.path.join(target_dir, "episode_custom.nfo")
        self.assertTrue(os.path.exists(ep_nfo_path))
        tree_ep = ET.parse(ep_nfo_path)
        root_ep = tree_ep.getroot()
        self.assertEqual(root_ep.find("title").text, "Custom Episode Title")
        self.assertEqual(root_ep.find("plot").text, "Custom Episode Plot")
        self.assertEqual(root_ep.find("aired").text, "2024-05-23")
        
        # 3. Test generate_movie_nfo with overrides
        movie_overrides = {
            "title": "Custom Movie Title",
            "plot": "Custom Movie Plot",
            "year": "2023"
        }
        res_movie = mw_metadata.generate_movie_nfo("manual", target_dir, "movie_custom", nfo_overrides=movie_overrides)
        self.assertTrue(res_movie["nfo"])
        
        movie_nfo_path = os.path.join(target_dir, "movie_custom.nfo")
        self.assertTrue(os.path.exists(movie_nfo_path))
        tree_movie = ET.parse(movie_nfo_path)
        root_movie = tree_movie.getroot()
        self.assertEqual(root_movie.find("title").text, "Custom Movie Title")
        self.assertEqual(root_movie.find("plot").text, "Custom Movie Plot")
        self.assertEqual(root_movie.find("year").text, "2023")

    def test_scan_project_absolute_path(self):
        import xml.etree.ElementTree as ET
        from gui.api.project_api import handle_api_scan_project
        from flask import Flask
        
        app = Flask(__name__)
        
        nas_dir = os.path.join(self.test_dir, "mock_nas_folder")
        os.makedirs(nas_dir, exist_ok=True)
        
        nfo_content = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <tvshow>
            <title>Mock Show</title>
            <plot>Mock Plot</plot>
            <year>1986</year>
            <mw_provider>tvdb</mw_provider>
            <mw_showid>76666</mw_showid>
        </tvshow>"""
        with open(os.path.join(nas_dir, "tvshow.nfo"), "w", encoding="utf-8") as f:
            f.write(nfo_content)
            
        video_path = os.path.join(nas_dir, "Mock Show - S01E01.mp4")
        with open(video_path, "w") as f:
            f.write("")
            
        ep_nfo_content = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <episodedetails>
            <title>Episode Title</title>
            <plot>Episode Plot</plot>
        </episodedetails>"""
        with open(os.path.join(nas_dir, "Mock Show - S01E01.nfo"), "w", encoding="utf-8") as f:
            f.write(ep_nfo_content)
            
        from unittest.mock import patch
        with app.test_request_context(query_string=f"project={nas_dir}"):
            with patch("gui.api.project_api.is_path_allowed", return_value=True):
                with patch("gui.api.project_api.load_settings", return_value={"inbox_dir": self.test_dir}):
                    resp = handle_api_scan_project()
                    data = json.loads(resp.get_data(as_text=True))
                    
                    self.assertEqual(data["metadata_provider"], "tvdb")
                    self.assertEqual(data["metadata_id"], "76666")
                    self.assertEqual(data["metadata_name"], "Mock Show")
                    self.assertEqual(data["metadata_year"], "1986")
                    self.assertEqual(data["metadata_plot"], "Mock Plot")
                    self.assertIn("Mock Show - S01E01.mp4", data["file_nfo_statuses"])
                    self.assertTrue(data["file_nfo_statuses"]["Mock Show - S01E01.mp4"]["exists"])
                    self.assertTrue(data["file_nfo_statuses"]["Mock Show - S01E01.mp4"]["complete"])

    def test_scan_project_absolute_path_denied(self):
        from gui.api.project_api import handle_api_scan_project
        from flask import Flask
        
        app = Flask(__name__)
        
        from unittest.mock import patch
        with app.test_request_context(query_string="project=/etc"):
            with patch("gui.api.project_api.load_settings", return_value={"inbox_dir": "/tmp/inbox"}):
                resp = handle_api_scan_project()
                self.assertEqual(resp[1], 403)
                data = json.loads(resp[0].get_data(as_text=True))
                self.assertIn("error", data)
                self.assertIn("Access Denied", data["error"])

    def test_nfo_incomplete_detection(self):
        from gui.core.health import _check_nfo_incomplete
        
        nfo_path = os.path.join(self.test_dir, "complete.nfo")
        with open(nfo_path, "w", encoding="utf-8") as f:
            f.write("<movie><title>Test Title</title><plot>Test Plot</plot><year>2026</year></movie>")
        is_inc, sev, reason = _check_nfo_incomplete(nfo_path, "movie")
        self.assertFalse(is_inc)
        
        nfo_path_inc = os.path.join(self.test_dir, "incomplete.nfo")
        with open(nfo_path_inc, "w", encoding="utf-8") as f:
            f.write("<movie><title></title><plot>Test Plot</plot></movie>")
        is_inc, sev, reason = _check_nfo_incomplete(nfo_path_inc, "movie")
        self.assertTrue(is_inc)
        self.assertEqual(sev, "critical")
        self.assertIn("Titel", reason)
        
        nfo_path_warn = os.path.join(self.test_dir, "warn.nfo")
        with open(nfo_path_warn, "w", encoding="utf-8") as f:
            f.write("<movie><title>Test Title</title><plot>Test Plot</plot><year></year></movie>")
        is_inc, sev, reason = _check_nfo_incomplete(nfo_path_warn, "movie")
        self.assertTrue(is_inc)
        self.assertEqual(sev, "warning")
        self.assertIn("Produktionsjahr", reason)

    def test_nfo_generation_overwrite_parameter(self):
        ep_meta = {"title": "Test Ep", "episode": 1, "plot": "Test Plot"}
        nfo_path = os.path.join(self.test_dir, "ep_overwrite_test.nfo")
        if os.path.exists(nfo_path):
            os.remove(nfo_path)
            
        res = mw_metadata.generate_episode_nfo("manual", "unused", 1, ep_meta, self.test_dir, "ep_overwrite_test")
        self.assertTrue(res["nfo"])
        self.assertTrue(os.path.exists(nfo_path))
        
        with open(nfo_path, "w", encoding="utf-8") as f:
            f.write("<episodedetails><title>Handgepflegt</title><plot>Plot</plot></episodedetails>")
            
        res2 = mw_metadata.generate_episode_nfo("manual", "unused", 1, ep_meta, self.test_dir, "ep_overwrite_test", overwrite=False)
        self.assertFalse(res2["nfo"])
        with open(nfo_path, "r", encoding="utf-8") as f:
            self.assertIn("Handgepflegt", f.read())
            
        res3 = mw_metadata.generate_episode_nfo("manual", "unused", 1, ep_meta, self.test_dir, "ep_overwrite_test", overwrite=True)
        self.assertTrue(res3["nfo"])
        with open(nfo_path, "r", encoding="utf-8") as f:
            self.assertNotIn("Handgepflegt", f.read())

    def test_show_and_movie_nfo_overwrite_protection(self):
        from gui.core.health import should_overwrite_nfo
        
        nfo_path = os.path.join(self.test_dir, "tvshow.nfo")
        if os.path.exists(nfo_path):
            os.remove(nfo_path)
            
        # 1. overwrite_nfo = False -> always False
        self.assertFalse(should_overwrite_nfo(False, {}, nfo_path, "tvshow"))
        self.assertFalse(should_overwrite_nfo(False, {"title": "New"}, nfo_path, "tvshow"))
        
        # 2. overwrite_nfo = True, missing file -> True
        self.assertTrue(should_overwrite_nfo(True, {}, nfo_path, "tvshow"))
        
        # 3. overwrite_nfo = True, existing but incomplete file -> True
        with open(nfo_path, "w", encoding="utf-8") as f:
            f.write("<tvshow><title></title><plot>Plot</plot></tvshow>")
        self.assertTrue(should_overwrite_nfo(True, {}, nfo_path, "tvshow"))
        
        # 4. overwrite_nfo = True, existing complete file, no overrides -> False
        with open(nfo_path, "w", encoding="utf-8") as f:
            f.write("<tvshow><title>Good Show</title><plot>Plot</plot><year>2026</year></tvshow>")
        self.assertFalse(should_overwrite_nfo(True, {}, nfo_path, "tvshow"))
        
        # 5. overwrite_nfo = True, existing complete file, has overrides -> True
        self.assertTrue(should_overwrite_nfo(True, {"title": "New Title"}, nfo_path, "tvshow"))

    def test_import_streamfab_files_grouping(self):
        from gui import server
        orig_load_settings = endpoints.load_settings
        
        # Setup temporary directories for testing
        test_inbox = os.path.join(self.test_dir, "import_inbox")
        test_sf_dir = os.path.join(self.test_dir, "import_sf")
        os.makedirs(test_inbox, exist_ok=True)
        os.makedirs(test_sf_dir, exist_ok=True)
        
        utils._MOCK_SETTINGS = {
            "inbox_dir": test_inbox,
            "import_sources": [test_sf_dir]
        }
        
        try:
            # 1. Create single video file in sf
            single_video = os.path.join(test_sf_dir, "SingleVideo.mp4")
            with open(single_video, 'w') as f:
                f.write("dummy video")
                
            # 2. Create group with identical base name
            grp_video = os.path.join(test_sf_dir, "AwesomeMovie.mkv")
            grp_srt = os.path.join(test_sf_dir, "AwesomeMovie.srt")
            grp_jpg = os.path.join(test_sf_dir, "AwesomeMovie.jpg")
            for fp in [grp_video, grp_srt, grp_jpg]:
                with open(fp, 'w') as f:
                    f.write("dummy group")
                    
            # 3. Create case-insensitive group
            case_video = os.path.join(test_sf_dir, "CaseTest.mp4")
            case_srt = os.path.join(test_sf_dir, "casetest.SRT")
            for fp in [case_video, case_srt]:
                with open(fp, 'w') as f:
                    f.write("dummy case")

            # 4. Create group with illegal characters in base name
            dirty_video = os.path.join(test_sf_dir, "My Movie: A.mp4")
            dirty_srt = os.path.join(test_sf_dir, "My Movie: A.srt")
            for fp in [dirty_video, dirty_srt]:
                with open(fp, 'w') as f:
                    f.write("dummy dirty")

            # Run import
            count = server.import_streamfab_files()
            self.assertEqual(count, 8)
            
            # Check single file is in a folder (project folder)
            self.assertFalse(os.path.exists(os.path.join(test_inbox, "SingleVideo.mp4")))
            self.assertTrue(os.path.exists(os.path.join(test_inbox, "SingleVideo", "SingleVideo.mp4")))
            
            # Check AwesomeMovie group is in a folder
            self.assertTrue(os.path.exists(os.path.join(test_inbox, "AwesomeMovie", "AwesomeMovie.mkv")))
            self.assertTrue(os.path.exists(os.path.join(test_inbox, "AwesomeMovie", "AwesomeMovie.srt")))
            self.assertTrue(os.path.exists(os.path.join(test_inbox, "AwesomeMovie", "AwesomeMovie.jpg")))
            
            # Check CaseTest group (case-insensitive) is in a folder
            inbox_dirs = [d for d in os.listdir(test_inbox) if os.path.isdir(os.path.join(test_inbox, d))]
            self.assertIn("AwesomeMovie", inbox_dirs)
            case_folder = next((d for d in inbox_dirs if d.lower() == "casetest"), None)
            self.assertIsNotNone(case_folder)
            self.assertTrue(os.path.exists(os.path.join(test_inbox, case_folder, "CaseTest.mp4")))
            self.assertTrue(os.path.exists(os.path.join(test_inbox, case_folder, "casetest.SRT")))

            # Check My Movie: A group is in a sanitized folder name
            self.assertTrue(os.path.exists(os.path.join(test_inbox, "My Movie - A", "My Movie: A.mp4")))
            self.assertTrue(os.path.exists(os.path.join(test_inbox, "My Movie - A", "My Movie: A.srt")))
            
            # Check that empty source folder is cleaned up (as top-level test_sf_dir is not deleted, but subdirs might be.
            # Wait, the code deletes subdirectories inside sf_dir, but does it delete sf_dir itself?
            # Let's check: sf_dir has all files moved, so it is empty now.
            # But the code walks sf_dir and deletes empty dirs. Since sf_dir itself is not a subdirectory inside sf_dir,
            # sf_dir itself might remain, but it should be empty. Let's check that test_sf_dir is empty or does not exist.
            self.assertTrue(os.path.exists(test_sf_dir))
            self.assertEqual(len(os.listdir(test_sf_dir)), 0)
            
        finally:
            utils._MOCK_SETTINGS = None

    def test_queue_clear(self):
        import gui.server as server
        from gui.server import GUIRequestHandler
        
        # Mock/dummy handler
        class DummyHandler:
            def __init__(self):
                self.sent_json = None
            def send_json(self, data):
                self.sent_json = data
                
        dummy = DummyHandler()
        
        # Save original active_jobs
        with server.active_jobs_lock:
            orig_jobs = dict(server.active_jobs)
            server.active_jobs.clear()
            
            # Setup test jobs
            server.active_jobs["job1"] = {"id": "job1", "status": "done", "timestamp": 1.0}
            server.active_jobs["job2"] = {"id": "job2", "status": "error", "timestamp": 2.0}
            server.active_jobs["job3"] = {"id": "job3", "status": "running", "timestamp": 3.0}
            server.active_jobs["job4"] = {"id": "job4", "status": "queued", "timestamp": 4.0}
            
        try:
            GUIRequestHandler.handle_api_queue_clear(dummy)
            
            self.assertEqual(dummy.sent_json, {"status": "success"})
            
            with server.active_jobs_lock:
                self.assertEqual(len(server.active_jobs), 1)
                self.assertIn("job3", server.active_jobs)
                self.assertNotIn("job1", server.active_jobs)
                self.assertNotIn("job2", server.active_jobs)
                self.assertNotIn("job4", server.active_jobs)
                
        finally:
            with server.active_jobs_lock:
                server.active_jobs.clear()
                server.active_jobs.update(orig_jobs)

    def test_preview_destination_formatting(self):
        import gui.server as server
        from gui.server import GUIRequestHandler
        
        inbox_dir = os.path.join(self.test_dir, "inbox")
        outbox_dir = os.path.join(self.test_dir, "outbox")
        nas_root = os.path.join(self.test_dir, "nas")
        os.makedirs(inbox_dir)
        os.makedirs(outbox_dir)
        os.makedirs(nas_root)
        
        orig_load_settings = endpoints.load_settings
        def mock_load_settings():
            return {
                "inbox_dir": inbox_dir,
                "outbox_dir": outbox_dir,
                "nas_root": nas_root,
                "sync_categories": [
                    {"id": "4", "name": "Doku-Serien", "nas_sub": "/Dokus/Doku-Serien", "pcloud_remote": "pcloud:04a_Dokus"}
                ]
            }
        utils._MOCK_SETTINGS = mock_load_settings()
        
        project_dir = os.path.join(inbox_dir, "Geheimnisse_Asiens")
        os.makedirs(project_dir)
        video_path = os.path.join(project_dir, "episode1.mp4")
        with open(video_path, "w") as f:
            f.write("dummy video data")
            
        class DummyHandler:
            def __init__(self):
                self.sent_json = None
            def send_json(self, data):
                self.sent_json = data
                
        dummy = DummyHandler()
        
        params = {
            "media_type": "tv",
            "project_name": "Geheimnisse_Asiens",
            "show_name": "Geheimnisse Asiens - Die schönsten Nationalparks",
            "show_id": "123",
            "provider": "tmdb_tv",
            "season": "1",
            "destination_id": "4",
            "copy_to_nas": True,
            "copy_to_pcloud": True,
            "mappings": {
                "episode1.mp4": {
                    "season": "1",
                    "episode": 1,
                    "title": "Chinas wilde Berge"
                }
            }
        }
        
        try:
            GUIRequestHandler.handle_api_preview_process(dummy, params)
            
            result = dummy.sent_json
            self.assertIsNotNone(result)
            dest = result.get("destination", "")
            expected_nas = "NAS: " + nas_root + "/Dokus/Doku-Serien/Geheimnisse Asiens - Die schönsten Nationalparks/Staffel 1/Geheimnisse Asiens - Die schönsten Nationalparks - S01E01 - Chinas wilde Berge"
            self.assertIn(expected_nas, dest)
            self.assertIn("☁️ pCloud: pcloud:04a_Dokus/Geheimnisse Asiens - Die schönsten Nationalparks", dest)
            
            params["mappings"] = {}
            GUIRequestHandler.handle_api_preview_process(dummy, params)
            
            result = dummy.sent_json
            dest = result.get("destination", "")
            self.assertIn("[Episoden-Unterordner]", dest)
            
            # Test "all" seasons mode with string mappings
            params["season"] = "all"
            params["mappings"] = {
                "episode1.mp4": "S02E03"
            }
            
            # Mock the fetch_tmdb_tv to return metadata for S02E03
            orig_fetch = server.mw_metadata.fetch_tmdb_tv
            def mock_fetch(show_id, season, lang="de-DE"):
                return {
                    "S02E03": {"title": "Kopfeck", "date": "2026-05-22"}
                }
            server.mw_metadata.fetch_tmdb_tv = mock_fetch
            
            try:
                GUIRequestHandler.handle_api_preview_process(dummy, params)
                result = dummy.sent_json
                self.assertIsNotNone(result)
                dest = result.get("destination", "")
                expected_nas = "NAS: " + nas_root + "/Dokus/Doku-Serien/Geheimnisse Asiens - Die schönsten Nationalparks/Staffel 2/Geheimnisse Asiens - Die schönsten Nationalparks - S02E03 - Kopfeck"
                self.assertIn(expected_nas, dest)
                
                # Test fallback when mappings are empty in "all" seasons mode
                params["mappings"] = {}
                GUIRequestHandler.handle_api_preview_process(dummy, params)
                result = dummy.sent_json
                dest = result.get("destination", "")
                self.assertIn("[Staffeln]/[Episoden-Unterordner]", dest)
            finally:
                server.mw_metadata.fetch_tmdb_tv = orig_fetch
            
        finally:
            utils._MOCK_SETTINGS = None

    def test_preview_skipped_episodes_are_not_junk(self):
        import gui.server as server
        from gui.server import GUIRequestHandler
        
        inbox_dir = os.path.join(self.test_dir, "inbox_skipped_test")
        outbox_dir = os.path.join(self.test_dir, "outbox_skipped_test")
        nas_root = os.path.join(self.test_dir, "nas_skipped_test")
        os.makedirs(inbox_dir)
        os.makedirs(outbox_dir)
        os.makedirs(nas_root)
        
        orig_load_settings = endpoints.load_settings
        def mock_load_settings():
            return {
                "inbox_dir": inbox_dir,
                "outbox_dir": outbox_dir,
                "nas_root": nas_root,
                "sync_categories": []
            }
        utils._MOCK_SETTINGS = mock_load_settings()
        
        project_dir = os.path.join(inbox_dir, "MyShow")
        os.makedirs(project_dir)
        
        # episode1 is mapped, episode2 is unmapped (skipped)
        video1 = os.path.join(project_dir, "episode1.mp4")
        video2 = os.path.join(project_dir, "episode2.mp4")
        sub2 = os.path.join(project_dir, "episode2.srt")
        junk_txt = os.path.join(project_dir, "streamfab.log")
        
        for p in [video1, video2, sub2, junk_txt]:
            with open(p, "w") as f:
                f.write("dummy content")
                
        class DummyHandler:
            def __init__(self):
                self.sent_json = None
            def send_json(self, data):
                self.sent_json = data
                
        dummy = DummyHandler()
        
        params = {
            "media_type": "tv",
            "project_name": "MyShow",
            "show_name": "MyShow",
            "show_id": "123",
            "provider": "tmdb_tv",
            "season": "1",
            "copy_to_nas": False,
            "mappings": {
                "episode1.mp4": {
                    "season": "1",
                    "episode": 1,
                    "title": "Welcome"
                }
            }
        }
        
        try:
            GUIRequestHandler.handle_api_preview_process(dummy, params)
            result = dummy.sent_json
            self.assertIsNotNone(result)
            
            renames = result.get("renames", [])
            junk = result.get("junk", [])
            subs = result.get("subs", [])
            
            # episode1.mp4 should be renamed
            self.assertEqual(len(renames), 1)
            self.assertEqual(renames[0]["old"], "episode1.mp4")
            
            # streamfab.log should be junk
            self.assertIn("streamfab.log", junk)
            
            # episode2.mp4 (unmapped video) and episode2.srt (unmapped sub) should NOT be in junk
            self.assertNotIn("episode2.mp4", junk)
            self.assertNotIn("episode2.srt", junk)
            self.assertNotIn("episode2.mp4", [r["old"] for r in renames])
            self.assertNotIn("episode2.srt", [s["old"] for s in subs])
            
        finally:
            utils._MOCK_SETTINGS = None

    def test_preview_force_absolute_season_1(self):
        import gui.server as server
        from gui.server import GUIRequestHandler
        
        inbox_dir = os.path.join(self.test_dir, "inbox_force_abs_test")
        nas_root = os.path.join(self.test_dir, "nas_force_abs_test")
        os.makedirs(inbox_dir, exist_ok=True)
        os.makedirs(nas_root, exist_ok=True)
        
        # Write dummy file with absolute number in name
        ep_file_path = os.path.join(inbox_dir, "Elefant_Tiger_Co_(381)_2026.mp4")
        with open(ep_file_path, "w") as f:
            f.write("")
            
        orig_load_settings = endpoints.load_settings
        utils._MOCK_SETTINGS = {
            "inbox_dir": inbox_dir,
            "outbox_dir": os.path.join(self.test_dir, "outbox_force_abs_test"),
            "nas_root": nas_root,
            "sync_categories": [
                {"id": "2", "name": "Serien", "nas_sub": "/Serien"}
            ]
        }
        
        class DummyHandler:
            def __init__(self):
                self.sent_json = None
            def send_json(self, data):
                self.sent_json = data
                
        dummy = DummyHandler()
        
        params = {
            "media_type": "tv",
            "project_name": "",
            "show_name": "Elefant, Tiger und Co.",
            "show_id": "249482",
            "provider": "tvdb",
            "season": "2026",
            "copy_to_nas": True,
            "force_absolute_season_1": True,
            "mappings": {
                "Elefant_Tiger_Co_(381)_2026.mp4": "1"
            }
        }
        
        # Mock TVDB fetching
        orig_fetch = server.mw_metadata.fetch_tvdb
        server.mw_metadata.fetch_tvdb = lambda show_id, season, lang: {
            "1": {"title": "In der Ruhe liegt die Kraft", "date": "2026-01-01", "absolute_number": 381}
        }
        
        try:
            GUIRequestHandler.handle_api_preview_process(dummy, params)
            result = dummy.sent_json
            self.assertIsNotNone(result)
            
            # Warning about high season should NOT be present (suppressed)
            self.assertNotIn("warning", result)
            
            renames = result.get("renames", [])
            self.assertEqual(len(renames), 1)
            self.assertEqual(os.path.basename(renames[0]["old"]), "Elefant_Tiger_Co_(381)_2026.mp4")
            # Should be mapped to S01E381 since force_absolute_season_1 is True
            self.assertEqual(renames[0]["new"], "Elefant, Tiger und Co. - S01E381 - In der Ruhe liegt die Kraft.mp4")
            
            dest = result.get("destination", "")
            self.assertIn("Serien/Elefant, Tiger und Co./Staffel 1/Elefant, Tiger und Co. - S01E381 - In der Ruhe liegt die Kraft", dest)
        finally:
            utils._MOCK_SETTINGS = None
            server.mw_metadata.fetch_tvdb = orig_fetch

    def test_api_nas_series_get(self):
        import gui.server as server
        from gui.server import GUIRequestHandler
        
        nas_root = os.path.join(self.test_dir, "nas_get_test")
        outbox_dir = os.path.join(self.test_dir, "outbox_get_test")
        os.makedirs(nas_root, exist_ok=True)
        os.makedirs(outbox_dir, exist_ok=True)
        
        # Create folders (including a case-insensitive duplicate)
        os.makedirs(os.path.join(nas_root, "Serien", "Simpsonspedia"), exist_ok=True)
        os.makedirs(os.path.join(outbox_dir, "Serien", "Simpsonspedia Outbox"), exist_ok=True)
        os.makedirs(os.path.join(outbox_dir, "Serien", "simpsonspedia"), exist_ok=True)
        
        orig_load_settings = endpoints.load_settings
        utils._MOCK_SETTINGS = {
            "nas_root": nas_root,
            "outbox_dir": outbox_dir,
            "sync_categories": [
                {"id": "2", "name": "Serien", "nas_sub": "/Serien", "pcloud_remote": ""}
            ]
        }
        
        # ensure_nas_mounted im kanonischen Endpoint-Modul (gui.api.nas_api) patchen.
        import gui.api.nas_api as nas_api
        orig_ensure = nas_api.ensure_nas_mounted
        nas_api.ensure_nas_mounted = lambda: True

        class DummyHandler:
            def __init__(self):
                self.sent_json = None
            def send_json(self, data):
                self.sent_json = data

        dummy = DummyHandler()

        try:
            # Query format of parse_qs: values are lists
            params = {"destination_id": ["2"]}
            GUIRequestHandler.handle_api_nas_series(dummy, params)
            
            result = dummy.sent_json
            self.assertIsNotNone(result)
            self.assertTrue(result.get("connected"))
            
            folders = result.get("folders", [])
            self.assertIn("Simpsonspedia", folders)
            self.assertIn("Simpsonspedia Outbox", folders)
            self.assertNotIn("simpsonspedia", folders)
            self.assertEqual(len(folders), 2)

        finally:
            utils._MOCK_SETTINGS = None
            nas_api.ensure_nas_mounted = orig_ensure

    def test_api_nas_series_get_all(self):
        import gui.server as server
        from gui.server import GUIRequestHandler
        
        nas_root = os.path.join(self.test_dir, "nas_get_all_test")
        outbox_dir = os.path.join(self.test_dir, "outbox_get_all_test")
        os.makedirs(nas_root, exist_ok=True)
        os.makedirs(outbox_dir, exist_ok=True)
        
        # Create folders in two different categories
        os.makedirs(os.path.join(nas_root, "Serien", "Simpsonspedia"), exist_ok=True)
        os.makedirs(os.path.join(nas_root, "Dokus/Doku-Serien", "Modern Marvels"), exist_ok=True)
        os.makedirs(os.path.join(outbox_dir, "Serien", "Simpsonspedia Outbox"), exist_ok=True)
        
        orig_load_settings = endpoints.load_settings
        utils._MOCK_SETTINGS = {
            "nas_root": nas_root,
            "outbox_dir": outbox_dir,
            "sync_categories": [
                {"id": "2", "name": "Serien", "nas_sub": "/Serien", "pcloud_remote": ""},
                {"id": "3", "name": "Dokus", "nas_sub": "/Dokus/Doku-Serien", "pcloud_remote": ""}
            ]
        }

        import gui.api.nas_api as nas_api
        orig_ensure = nas_api.ensure_nas_mounted
        nas_api.ensure_nas_mounted = lambda: True
        
        class DummyHandler:
            def __init__(self):
                self.sent_json = None
            def send_json(self, data):
                self.sent_json = data
                
        dummy = DummyHandler()
        
        try:
            params = {"destination_id": ["all"]}
            GUIRequestHandler.handle_api_nas_series(dummy, params)
            
            result = dummy.sent_json
            self.assertIsNotNone(result)
            self.assertTrue(result.get("connected"))
            
            folders = result.get("folders", [])
            self.assertIn("Simpsonspedia", folders)
            self.assertIn("Modern Marvels", folders)
            self.assertIn("Simpsonspedia Outbox", folders)
            self.assertEqual(len(folders), 3)
            
            folder_destinations = result.get("folder_destinations", {})
            self.assertEqual(folder_destinations.get("simpsonspedia"), os.path.join(nas_root, "Serien"))
            self.assertEqual(folder_destinations.get("modern marvels"), os.path.join(nas_root, "Dokus/Doku-Serien"))
            self.assertEqual(folder_destinations.get("simpsonspedia outbox"), os.path.join(nas_root, "Serien"))

        finally:
            utils._MOCK_SETTINGS = None
            nas_api.ensure_nas_mounted = orig_ensure

    def test_api_match_episodes(self):
        import gui.server as server
        from gui.server import GUIRequestHandler
        
        class DummyHandler:
            def __init__(self):
                self.sent_json = None
            def send_json(self, data):
                self.sent_json = data
                
        dummy = DummyHandler()
        
        # Test case 1: TVDB year-based keys with absolute number matching
        params = {
            "provider": "tvdb",
            "show_id": "249482",
            "season": "all",
            "filenames": [
                "Elefant,_Tiger_&_Co._In_der_Ruhe_liegt_die_Kraft_(381)_2026.mp4",
                "Elefant_Tiger_Co_S01E05_Test.mp4"
            ]
        }
        
        orig_fetch = server.mw_metadata.fetch_tvdb
        # Mock fetch_tvdb to return episodes including absolute numbers
        server.mw_metadata.fetch_tvdb = lambda show_id, season, lang: {
            "S2010E39": {"title": "In der Ruhe liegt die Kraft", "date": "2010-01-01", "absolute_number": 381},
            "S01E05": {"title": "Anderer Titel", "date": "2003-05-01", "absolute_number": 5}
        }
        
        try:
            GUIRequestHandler.handle_api_match_episodes(dummy, params)
            result = dummy.sent_json
            self.assertIsNotNone(result)
            matches = result.get("matches", {})
            
            # File with (381) should match S2010E39 based on absolute number 381
            self.assertEqual(matches.get("Elefant,_Tiger_&_Co._In_der_Ruhe_liegt_die_Kraft_(381)_2026.mp4"), "S2010E39")
            
            # File with S01E05 should match S01E05 suffix
            self.assertEqual(matches.get("Elefant_Tiger_Co_S01E05_Test.mp4"), "S01E05")
        finally:
            server.mw_metadata.fetch_tvdb = orig_fetch

    def test_api_series_detect(self):
        import gui.server as server
        from gui.server import GUIRequestHandler
        
        nas_root = os.path.join(self.test_dir, "nas_detect_test")
        outbox_dir = os.path.join(self.test_dir, "outbox_detect_test")
        os.makedirs(nas_root, exist_ok=True)
        os.makedirs(outbox_dir, exist_ok=True)
        
        # Create folder structure for a show with a tvshow.nfo
        show_dir = os.path.join(nas_root, "Serien", "Simpsonspedia (1989)")
        os.makedirs(show_dir, exist_ok=True)
        nfo_path = os.path.join(show_dir, "tvshow.nfo")
        with open(nfo_path, "w", encoding="utf-8") as f:
            f.write("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<tvshow>
  <mw_provider>ytdlp</mw_provider>
  <mw_showid>https://youtube.com/playlist?list=some_id</mw_showid>
</tvshow>""")
            
        orig_load_settings = endpoints.load_settings
        utils._MOCK_SETTINGS = {
            "nas_root": nas_root,
            "outbox_dir": outbox_dir,
            "sync_categories": [
                {"id": "2", "name": "Serien", "nas_sub": "/Serien", "pcloud_remote": ""}
            ]
        }
        
        # series-detect liegt in gui.api.search_api -> dort ensure_nas_mounted patchen.
        import gui.api.search_api as search_api
        orig_ensure = search_api.ensure_nas_mounted
        search_api.ensure_nas_mounted = lambda: True

        class DummyHandler:
            def __init__(self):
                self.sent_json = None
            def send_json(self, data):
                self.sent_json = data

        dummy = DummyHandler()

        try:
            # Query format of parse_qs: values are lists.
            # 1. Exact match (cleaned)
            query = {
                "project_name": ["Simpsonspedia 1989"],
                "nas_destination_id": ["2"]
            }
            GUIRequestHandler.handle_api_series_detect(dummy, query)
            result = dummy.sent_json
            print("DEBUG DETECT:", result); self.assertTrue(result.get("found"))
            self.assertEqual(result.get("provider"), "ytdlp")
            self.assertEqual(result.get("show_id"), "https://youtube.com/playlist?list=some_id")
            self.assertEqual(result.get("show_name"), "Simpsonspedia (1989)")
            
            # 2. Normalized alphanumeric match
            query_norm = {
                "project_name": ["simpsonspedia-1989"],
                "nas_destination_id": ["2"]
            }
            GUIRequestHandler.handle_api_series_detect(dummy, query_norm)
            result_norm = dummy.sent_json
            self.assertTrue(result_norm.get("found"))
            self.assertEqual(result_norm.get("show_name"), "Simpsonspedia (1989)")
            
            # 3. All destinations search (searching across multiple directories)
            doku_dir = os.path.join(nas_root, "Dokus", "Doku-Serien", "Geheimnisse Asiens")
            os.makedirs(doku_dir, exist_ok=True)
            with open(os.path.join(doku_dir, "tvshow.nfo"), "w", encoding="utf-8") as f:
                f.write("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<tvshow>
  <mw_provider>tmdb_tv</mw_provider>
  <mw_showid>12345</mw_showid>
</tvshow>""")
                
            utils._MOCK_SETTINGS = {
                "nas_root": nas_root,
                "outbox_dir": outbox_dir,
                "sync_categories": [
                    {"id": "2", "name": "Serien", "nas_sub": "/Serien", "pcloud_remote": ""},
                    {"id": "4", "name": "Doku-Serien", "nas_sub": "/Dokus/Doku-Serien", "pcloud_remote": ""}
                ]
            }
            
            query_all = {
                "project_name": ["Geheimnisse Asiens"],
                "nas_destination_id": ["all"]
            }
            GUIRequestHandler.handle_api_series_detect(dummy, query_all)
            result_all = dummy.sent_json
            self.assertTrue(result_all.get("found"))
            self.assertEqual(result_all.get("provider"), "tmdb_tv")
            self.assertEqual(result_all.get("show_id"), "12345")
            self.assertEqual(result_all.get("show_name"), "Geheimnisse Asiens")

        finally:
            utils._MOCK_SETTINGS = None
            search_api.ensure_nas_mounted = orig_ensure

    def test_api_scan_project_detect_doku(self):
        import gui.server as server
        from gui.server import GUIRequestHandler
        import gui.core.persistence as persistence
        from gui.core import utils
        
        inbox_root = os.path.join(self.temp_home, "Downloads", "Medien Input")
        os.makedirs(inbox_root, exist_ok=True)
        
        orig_mock_persistence = persistence._MOCK_SETTINGS
        orig_mock_utils = utils._MOCK_SETTINGS
        persistence._MOCK_SETTINGS = {
            "inbox_dir": inbox_root
        }
        utils._MOCK_SETTINGS = persistence._MOCK_SETTINGS
        
        try:
            # Test Case 1: Folder name contains "doku"
            doku_folder_path = os.path.join(inbox_root, "Planet Erde Doku-Serie")
            os.makedirs(doku_folder_path, exist_ok=True)
            # Create a video file
            with open(os.path.join(doku_folder_path, "episode1.mp4"), "w") as f:
                f.write("")
                
            class DummyHandler:
                def __init__(self):
                    self.sent_json = None
                def send_json(self, data):
                    self.sent_json = data
                def send_error(self, code, message=None):
                    pass
                    
            dummy = DummyHandler()
            
            GUIRequestHandler.handle_api_scan_project(dummy, {"project": ["Planet Erde Doku-Serie"]})
            self.assertIsNotNone(dummy.sent_json)
            self.assertTrue(dummy.sent_json.get("is_doku"))
            self.assertEqual(dummy.sent_json.get("video_count"), 1)
            
            # Test Case 2: Folder name does NOT contain "doku", but NFO file contains documentary keywords
            normal_folder_path = os.path.join(inbox_root, "Some Movie Title")
            os.makedirs(normal_folder_path, exist_ok=True)
            with open(os.path.join(normal_folder_path, "movie.mp4"), "w") as f:
                f.write("")
            # Create NFO file with documentary keyword
            with open(os.path.join(normal_folder_path, "movie.nfo"), "w", encoding="utf-8") as f:
                f.write("This is a fascinating documentary about wildlife.")
                
            dummy2 = DummyHandler()
            GUIRequestHandler.handle_api_scan_project(dummy2, {"project": ["Some Movie Title"]})
            self.assertIsNotNone(dummy2.sent_json)
            self.assertTrue(dummy2.sent_json.get("is_doku"))
            
            # Test Case 3: Folder name and NFO files have no doku keywords
            clean_folder_path = os.path.join(inbox_root, "Pure Fiction Movie")
            os.makedirs(clean_folder_path, exist_ok=True)
            with open(os.path.join(clean_folder_path, "movie.mp4"), "w") as f:
                f.write("")
            with open(os.path.join(clean_folder_path, "movie.nfo"), "w", encoding="utf-8") as f:
                f.write("A cool action movie about heroes.")
                
            dummy3 = DummyHandler()
            GUIRequestHandler.handle_api_scan_project(dummy3, {"project": ["Pure Fiction Movie"]})
            self.assertIsNotNone(dummy3.sent_json)
            self.assertFalse(dummy3.sent_json.get("is_doku"))
        finally:
            persistence._MOCK_SETTINGS = orig_mock_persistence
            utils._MOCK_SETTINGS = orig_mock_utils

    def test_api_split_project_file(self):
        import gui.server as server
        from gui.server import GUIRequestHandler
        
        # Create a temp settings file to mock load_settings
        temp_dir = self.temp_dirs[0] if hasattr(self, 'temp_dirs') else tempfile.mkdtemp()
        if not hasattr(self, 'temp_dirs'):
            self.temp_dirs = [temp_dir]
            
        inbox_root = os.path.join(temp_dir, "Medien Input")
        os.makedirs(inbox_root, exist_ok=True)
        
        # Mock load_settings to return our temp inbox_root
        original_load_settings = server.load_settings
        utils._MOCK_SETTINGS = {"inbox_dir": inbox_root}
        
        try:
            # Create a source project folder with multiple files
            project_name = "Mixed Project"
            project_path = os.path.join(inbox_root, project_name)
            os.makedirs(project_path, exist_ok=True)
            
            # File to split and its sidecars
            movie_file = "Entdeckung_der_Welt_-_Natur_und_Tiere-Das_Tote_Gebirge.mp4"
            movie_srt = "Entdeckung_der_Welt_-_Natur_und_Tiere-Das_Tote_Gebirge.srt"
            movie_nfo = "Entdeckung_der_Welt_-_Natur_und_Tiere-Das_Tote_Gebirge.nfo"
            movie_poster = "Entdeckung_der_Welt_-_Natur_und_Tiere-Das_Tote_Gebirge-poster.jpg"
            
            # Other file that should remain in the original project
            other_file = "Entdeckung_der_Welt_-_Natur_und_Tiere-Wildkatzen.mp4"
            
            for name in [movie_file, movie_srt, movie_nfo, movie_poster, other_file]:
                with open(os.path.join(project_path, name), "w") as f:
                    f.write("content")
                    
            class DummyHandler:
                def __init__(self):
                    self.sent_json = None
                def send_json(self, data):
                    self.sent_json = data
                def send_error(self, code, message=None):
                    pass
                    
            dummy = DummyHandler()
            
            # Split the movie file
            params = {
                "project": project_name,
                "file_name": movie_file
            }
            
            GUIRequestHandler.handle_api_split_project_file(dummy, params)
            
            self.assertIsNotNone(dummy.sent_json)
            self.assertEqual(dummy.sent_json.get("status"), "success")
            
            new_project = dummy.sent_json.get("new_project")
            self.assertEqual(new_project, "Entdeckung_der_Welt_-_Natur_und_Tiere-Das_Tote_Gebirge")
            
            # Check files in new project directory
            new_project_path = os.path.join(inbox_root, new_project)
            self.assertTrue(os.path.exists(new_project_path))
            self.assertTrue(os.path.exists(os.path.join(new_project_path, movie_file)))
            self.assertTrue(os.path.exists(os.path.join(new_project_path, movie_srt)))
            self.assertTrue(os.path.exists(os.path.join(new_project_path, movie_nfo)))
            self.assertTrue(os.path.exists(os.path.join(new_project_path, movie_poster)))
            
            # Original project folder should still exist and contain the other file
            self.assertTrue(os.path.exists(project_path))
            self.assertTrue(os.path.exists(os.path.join(project_path, other_file)))
            
            # Movie files should no longer be in the original project folder
            self.assertFalse(os.path.exists(os.path.join(project_path, movie_file)))
            self.assertFalse(os.path.exists(os.path.join(project_path, movie_srt)))
            
            # Now let's test that splitting the other file leaves the original folder empty, which should delete it
            dummy2 = DummyHandler()
            params2 = {
                "project": project_name,
                "file_name": other_file
            }
            GUIRequestHandler.handle_api_split_project_file(dummy2, params2)
            self.assertIsNotNone(dummy2.sent_json)
            self.assertEqual(dummy2.sent_json.get("status"), "success")
            
            # Original project directory should now be deleted since it's empty
            self.assertFalse(os.path.exists(project_path))
            
        finally:
            utils._MOCK_SETTINGS = None

    def test_single_video_url_series_recognition(self):
        import gui.server as server
        from gui.server import GUIRequestHandler
        import gui.mw_metadata as mw_metadata
        import tempfile
        
        # Mock fetch_ytdlp_url_metadata
        original_fetch = mw_metadata.fetch_ytdlp_url_metadata
        mw_metadata.fetch_ytdlp_url_metadata = lambda url: [
            {
                "title": "Wildkatzen und Wildhunde",
                "description": "Eine Doku über wilde Tiere.",
                "thumbnail": "http://example.com/thumb.jpg",
                "playlist_title": None,
                "playlist": None
            }
        ]
        
        class DummyHandler:
            def __init__(self):
                self.sent_json = None
            def send_json(self, data):
                self.sent_json = data
                
        dummy = DummyHandler()
        
        try:
            # 1. Test search with type="tv" -> should classify as tv
            query_tv = {
                "q": ["https://www.arte.tv/de/videos/094408-002-F/wildkatzen-und-wildhunde/"],
                "type": ["tv"]
            }
            GUIRequestHandler.handle_api_search(dummy, query_tv)
            res_tv = dummy.sent_json
            self.assertEqual(len(res_tv), 1)
            self.assertEqual(res_tv[0]["media_type"], "tv")
            self.assertEqual(res_tv[0]["provider"], "ytdlp")
            
            # 2. Test search with type="doku" -> should classify as doku
            query_doku = {
                "q": ["https://www.arte.tv/de/videos/094408-002-F/wildkatzen-und-wildhunde/"],
                "type": ["doku"]
            }
            GUIRequestHandler.handle_api_search(dummy, query_doku)
            res_doku = dummy.sent_json
            self.assertEqual(len(res_doku), 1)
            self.assertEqual(res_doku[0]["media_type"], "doku")
            
            # 3. Test search with type="movie" -> should classify as movie
            query_movie = {
                "q": ["https://www.arte.tv/de/videos/094408-002-F/wildkatzen-und-wildhunde/"],
                "type": ["movie"]
            }
            GUIRequestHandler.handle_api_search(dummy, query_movie)
            res_movie = dummy.sent_json
            self.assertEqual(len(res_movie), 1)
            self.assertEqual(res_movie[0]["media_type"], "movie")
            
            # 4. Test search with fernsehserien.de URL -> should always classify as tv
            query_fs = {
                "q": ["https://www.fernsehserien.de/wildkatzen"],
                "type": ["tv"]
            }
            GUIRequestHandler.handle_api_search(dummy, query_fs)
            res_fs = dummy.sent_json
            self.assertEqual(len(res_fs), 1)
            self.assertEqual(res_fs[0]["media_type"], "tv")
            self.assertEqual(res_fs[0]["provider"], "fernsehserien")
            
            # 5. Test generate_episode_nfo when mapping to episode 4
            temp_dir = self.temp_dirs[0] if hasattr(self, 'temp_dirs') else tempfile.mkdtemp()
            if not hasattr(self, 'temp_dirs'):
                self.temp_dirs = [temp_dir]
            
            # This should use entries[0] from the mock because len(entries) == 1
            nfo_res = mw_metadata.generate_episode_nfo(
                provider="ytdlp",
                show_id="https://www.arte.tv/de/videos/094408-002-F/wildkatzen-und-wildhunde/",
                season=1,
                episode=4,
                target_folder=temp_dir,
                filename_base="Wildkatzen_S01E04"
            )
            
            self.assertTrue(nfo_res.get("nfo"))
            nfo_file = os.path.join(temp_dir, "Wildkatzen_S01E04.nfo")
            self.assertTrue(os.path.exists(nfo_file))
            
            with open(nfo_file, "r", encoding="utf-8") as f:
                nfo_content = f.read()
                
            self.assertIn("<title>Wildkatzen und Wildhunde</title>", nfo_content)
            self.assertIn("<season>1</season>", nfo_content)
            self.assertIn("<episode>4</episode>", nfo_content)
            self.assertIn("<plot>Eine Doku über wilde Tiere.</plot>", nfo_content)
            
        finally:
            mw_metadata.fetch_ytdlp_url_metadata = original_fetch

    def test_normalize_title_and_episode_naming(self):
        # 1. Test basic normalization
        self.assertEqual(mw_metadata.normalize_title("Wildkatzen & Wildhunde"), "wildkatzenundwildhunde")
        self.assertEqual(mw_metadata.normalize_title("Wildkatzen und Wildhunde"), "wildkatzenundwildhunde")
        self.assertEqual(mw_metadata.normalize_title("Wildkatzen: und Wildhunde!"), "wildkatzenundwildhunde")
        self.assertEqual(mw_metadata.normalize_title("   Wildkatzen & Wildhunde   "), "wildkatzenundwildhunde")
        self.assertEqual(mw_metadata.normalize_title(None), "")
        self.assertEqual(mw_metadata.normalize_title(""), "")

        # 2. Test equivalence matching
        title_a = "Wildkatzen & Wildhunde"
        title_b = "Wildkatzen und Wildhunde"
        self.assertEqual(mw_metadata.normalize_title(title_a), mw_metadata.normalize_title(title_b))

    def test_paths_clean_api(self):
        from gui.server import GUIRequestHandler
        
        class DummyHandler:
            def __init__(self):
                self.sent_json = None
            def send_json(self, data):
                self.sent_json = data

        import gui.server as server
        orig_load_settings = endpoints.load_settings
        
        # Setup paths
        test_inbox = os.path.join(self.test_dir, "test_inbox")
        test_outbox = os.path.join(self.test_dir, "test_outbox")
        os.makedirs(test_inbox, exist_ok=True)
        os.makedirs(test_outbox, exist_ok=True)
        
        # Create some files in inbox
        inbox_sub = os.path.join(test_inbox, "SubFolder")
        os.makedirs(inbox_sub, exist_ok=True)
        
        with open(os.path.join(test_inbox, "file1.mp4"), "w") as f:
            f.write("video content") # 13 bytes
        with open(os.path.join(inbox_sub, "junk.txt"), "w") as f:
            f.write("junk data") # 9 bytes
            
        # Create some files in outbox
        outbox_sub = os.path.join(test_outbox, "AnotherSub")
        os.makedirs(outbox_sub, exist_ok=True)
        with open(os.path.join(test_outbox, "file2.mkv"), "w") as f:
            f.write("video content 2") # 15 bytes
        with open(os.path.join(outbox_sub, "info.nfo"), "w") as f:
            f.write("info") # 4 bytes
            
        utils._MOCK_SETTINGS = {
            "inbox_dir": test_inbox,
            "outbox_dir": test_outbox
        }
        
        dummy = DummyHandler()
        try:
            # 1. Preview clean for both
            GUIRequestHandler.handle_api_paths_preview_clean(dummy, {"inbox": True, "output": True})
            res = dummy.sent_json
            self.assertIsNotNone(res)
            self.assertIn("inbox_files", res)
            self.assertIn("output_files", res)
            
            # Check inbox files list
            inbox_paths = {item["rel_path"]: item["size_bytes"] for item in res["inbox_files"]}
            self.assertEqual(inbox_paths.get("file1.mp4"), 13)
            self.assertEqual(inbox_paths.get("SubFolder/junk.txt"), 9)
            
            # Check outbox files list
            outbox_paths = {item["rel_path"]: item["size_bytes"] for item in res["output_files"]}
            self.assertEqual(outbox_paths.get("file2.mkv"), 15)
            self.assertEqual(outbox_paths.get("AnotherSub/info.nfo"), 4)
            
            # 2. Execute clean for SubFolder/junk.txt and AnotherSub/info.nfo
            dummy.sent_json = None
            params = {
                "inbox_files": ["SubFolder/junk.txt"],
                "output_files": ["AnotherSub/info.nfo"]
            }
            GUIRequestHandler.handle_api_paths_clean(dummy, params)
            clean_res = dummy.sent_json
            self.assertEqual(clean_res.get("status"), "ok")
            self.assertIn("inbox/SubFolder/junk.txt", clean_res.get("deleted_files", []))
            self.assertIn("output/AnotherSub/info.nfo", clean_res.get("deleted_files", []))
            
            # Check that files were actually removed
            self.assertFalse(os.path.exists(os.path.join(inbox_sub, "junk.txt")))
            self.assertFalse(os.path.exists(os.path.join(outbox_sub, "info.nfo")))
            
            # Check that empty sub directories were cleaned up
            self.assertFalse(os.path.exists(inbox_sub))
            self.assertFalse(os.path.exists(outbox_sub))
            
            # Check that non-selected files and main dirs are still there
            self.assertTrue(os.path.exists(os.path.join(test_inbox, "file1.mp4")))
            self.assertTrue(os.path.exists(os.path.join(test_outbox, "file2.mkv")))
            
        finally:
            utils._MOCK_SETTINGS = None

    def test_api_estimate_conversion_optimization(self):
        import gui.server as server
        from gui.server import GUIRequestHandler
        import gui.core.media as media
        
        inbox_dir = os.path.join(self.test_dir, "test_estimate_inbox")
        os.makedirs(inbox_dir, exist_ok=True)
        
        # Create 3 dummy video files
        filenames = ["ep1.mp4", "ep2.mp4", "ep3.mp4"]
        for f in filenames:
            with open(os.path.join(inbox_dir, f), "w") as file:
                file.write("dummy video data")
                
        orig_load_settings = endpoints.load_settings
        utils._MOCK_SETTINGS = {"inbox_dir": inbox_dir}
        
        # Track calls to server.media.konvertierung_schaetzen
        call_count = 0
        original_konvertierung_schaetzen = server.media.konvertierung_schaetzen
        
        def mock_konvertierung_schaetzen(filepath, quality, codec="hevc"):
            nonlocal call_count
            call_count += 1
            return 0.45
            
        server.media.konvertierung_schaetzen = mock_konvertierung_schaetzen
        
        class DummyHandler:
            def __init__(self):
                self.sent_json = None
            def send_json(self, data):
                self.sent_json = data
                
        dummy = DummyHandler()
        
        try:
            params = {
                "project_name": "",
                "filenames": filenames,
                "quality": 60
            }
            GUIRequestHandler.handle_api_estimate_conversion(dummy, params)
            
            res = dummy.sent_json
            self.assertIsNotNone(res)
            estimates = res.get("estimates", {})
            self.assertEqual(len(estimates), 3)
            
            # Verify media.konvertierung_schaetzen was called exactly ONCE
            self.assertEqual(call_count, 1)
            
            # Verify all estimates have the same ratio 0.45
            for f in filenames:
                self.assertIn(f, estimates)
                self.assertEqual(estimates[f]["ratio"], 0.45)
                
        finally:
            utils._MOCK_SETTINGS = None
            server.media.konvertierung_schaetzen = original_konvertierung_schaetzen

    def test_api_subscriptions_approve_and_ignore(self):
        import gui.server as server
        from gui.server import GUIRequestHandler
        
        import gui.api.youtube_api as youtube_api
        import gui.workers.processor as processor
        orig_load_settings = endpoints.load_settings
        # save_settings/active_jobs müssen im kanonischen Modul gepatcht werden,
        # in dem der Endpoint sie aufruft (gui.api.youtube_api bzw. gui.workers.processor).
        orig_save_settings = youtube_api.save_settings

        saved_settings = []
        mock_subs = [
            {
                "id": "sub_1",
                "name": "My Subscription",
                "url": "https://youtube.com/channel/abc",
                "destination_id": "1",
                "nas_destination_id": "1",
                "pcloud_destination_id": "2",
                "local_destination_id": "__inbox__",
                "copy_to_nas": True,
                "copy_to_pcloud": True,
                "copy_to_local": True,
                "enabled": True,
                "auto_download": False,
                "pending_videos": [
                    {
                        "id": "vid_123",
                        "title": "Amazing Video",
                        "url": "https://youtube.com/watch?v=vid_123",
                        "thumbnail": "thumb.jpg",
                        "channel": "Awesome Channel",
                        "published_at": "2026-05-24"
                    }
                ],
                "downloaded_ids": []
            }
        ]
        
        utils._MOCK_SETTINGS = {"youtube_subscriptions": mock_subs}
        def mock_save(sett):
            saved_settings.append(sett)
        youtube_api.save_settings = mock_save
        
        class DummyHandler:
            def __init__(self):
                self.sent_json = None
                self.sent_error = None
            def send_json(self, data):
                self.sent_json = data
            def send_error(self, code, message=None):
                self.sent_error = (code, message)
                
        dummy = DummyHandler()
        
        try:
            # 1. Test approve
            params = {
                "subscription_id": "sub_1",
                "video_id": "vid_123"
            }
            
            # Mock job queue and active jobs (kanonisches Dict in processor leeren,
            # nicht neu binden, sonst sieht der Endpoint ein anderes Objekt).
            orig_active_jobs = dict(processor.active_jobs)
            processor.active_jobs.clear()
            
            GUIRequestHandler.handle_api_subscriptions_approve(dummy, params)
            
            self.assertIsNotNone(dummy.sent_json)
            self.assertEqual(dummy.sent_json.get("status"), "success")
            
            # Verify saved settings
            self.assertEqual(len(saved_settings), 1)
            updated_subs = saved_settings[0]["youtube_subscriptions"]
            self.assertEqual(len(updated_subs[0]["pending_videos"]), 0)
            self.assertIn("vid_123", updated_subs[0]["downloaded_ids"])
            
            # Verify job is queued
            self.assertEqual(len(processor.active_jobs), 1)
            queued_job = list(processor.active_jobs.values())[0]
            self.assertEqual(queued_job["params"]["yt_url"], "https://youtube.com/watch?v=vid_123")
            self.assertEqual(queued_job["params"]["destination_id"], "1")
            self.assertEqual(queued_job["params"]["nas_destination_id"], "1")
            self.assertEqual(queued_job["params"]["pcloud_destination_id"], "2")
            self.assertEqual(queued_job["params"]["local_destination_id"], "__inbox__")
            self.assertTrue(queued_job["params"]["copy_to_nas"])
            self.assertTrue(queued_job["params"]["copy_to_pcloud"])
            self.assertTrue(queued_job["params"]["copy_to_local"])
            
            # 2. Test ignore (re-adding pending video first)
            mock_subs[0]["pending_videos"] = [{
                "id": "vid_123",
                "title": "Amazing Video",
                "url": "https://youtube.com/watch?v=vid_123",
                "thumbnail": "thumb.jpg",
                "channel": "Awesome Channel",
                "published_at": "2026-05-24"
            }]
            mock_subs[0]["downloaded_ids"] = []
            saved_settings.clear()
            
            dummy = DummyHandler()
            GUIRequestHandler.handle_api_subscriptions_ignore(dummy, params)
            
            self.assertIsNotNone(dummy.sent_json)
            self.assertEqual(dummy.sent_json.get("status"), "success")
            self.assertEqual(len(saved_settings), 1)
            updated_subs = saved_settings[0]["youtube_subscriptions"]
            self.assertEqual(len(updated_subs[0]["pending_videos"]), 0)
            self.assertIn("vid_123", updated_subs[0]["downloaded_ids"])
            
        finally:
            utils._MOCK_SETTINGS = None
            youtube_api.save_settings = orig_save_settings
            processor.active_jobs.clear()
            processor.active_jobs.update(orig_active_jobs)

    def test_preview_show_metadata_warning_on_nas(self):
        import gui.server as server
        from gui.server import GUIRequestHandler
        
        inbox_dir = os.path.join(self.test_dir, "inbox_warn_test")
        nas_root = os.path.join(self.test_dir, "nas_warn_test")
        os.makedirs(inbox_dir, exist_ok=True)
        os.makedirs(nas_root, exist_ok=True)
        
        # Create a series directory on NAS with metadata
        nas_show_dir = os.path.join(nas_root, "Serien", "My Existing Show")
        os.makedirs(nas_show_dir, exist_ok=True)
        with open(os.path.join(nas_show_dir, "tvshow.nfo"), "w") as f:
            f.write("existing show metadata")
            
        # Create folder in inbox
        project_dir = os.path.join(inbox_dir, "My Existing Show")
        os.makedirs(project_dir, exist_ok=True)
        with open(os.path.join(project_dir, "episode1.mp4"), "w") as f:
            f.write("video content")
            
        orig_load_settings = endpoints.load_settings
        utils._MOCK_SETTINGS = {
            "inbox_dir": inbox_dir,
            "outbox_dir": os.path.join(self.test_dir, "outbox_warn_test"),
            "nas_root": nas_root,
            "sync_categories": [
                {"id": "2", "name": "Serien", "nas_sub": "/Serien"}
            ]
        }
        
        class DummyHandler:
            def __init__(self):
                self.sent_json = None
            def send_json(self, data):
                self.sent_json = data
                
        dummy = DummyHandler()
        
        params = {
            "media_type": "tv",
            "project_name": "My Existing Show",
            "show_name": "My Existing Show",
            "show_id": "123",
            "provider": "tmdb_tv",
            "season": "1",
            "copy_to_nas": True,
            "mappings": {
                "episode1.mp4": "1"
            }
        }
        
        try:
            GUIRequestHandler.handle_api_preview_process(dummy, params)
            result = dummy.sent_json
            self.assertIsNotNone(result)
            
            dest = result.get("destination", "")
            self.assertIn("⚠️ Serie existiert bereits auf NAS mit vorhandenen Metadaten", dest)
            self.assertIn("tvshow.nfo", dest)
        finally:
            utils._MOCK_SETTINGS = None

    def test_check_duplicate_bugfix(self):
        import gui.server as server
        from gui.server import GUIRequestHandler
        
        inbox_dir = os.path.join(self.test_dir, "inbox_dup_test")
        nas_root = os.path.join(self.test_dir, "nas_dup_test")
        os.makedirs(inbox_dir, exist_ok=True)
        os.makedirs(nas_root, exist_ok=True)
        
        # Create a series directory on NAS with a non-video file and a video file
        nas_show_dir = os.path.join(nas_root, "Serien", "My Show")
        os.makedirs(nas_show_dir, exist_ok=True)
        
        # Create non-video duplicate (should NOT be flagged)
        with open(os.path.join(nas_show_dir, "fanart.jpg"), "w") as f:
            f.write("image data")
            
        # Create video duplicate (should be flagged)
        with open(os.path.join(nas_show_dir, "My Show - S01E01.mp4"), "w") as f:
            f.write("video content")
            
        orig_load_settings = endpoints.load_settings
        utils._MOCK_SETTINGS = {
            "inbox_dir": inbox_dir,
            "outbox_dir": os.path.join(self.test_dir, "outbox_dup_test"),
            "nas_root": nas_root,
            "sync_categories": [
                {"id": "2", "name": "Serien", "nas_sub": "/Serien"}
            ]
        }
        
        class DummyHandler:
            def __init__(self):
                self.sent_json = None
            def send_json(self, data):
                self.sent_json = data
                
        dummy = DummyHandler()
        
        orig_fetch = server.mw_metadata.fetch_tvdb
        server.mw_metadata.fetch_tvdb = lambda show_id, season, lang: {
            "1": {"title": "Episode 1", "absolute_number": 1},
            "2": {"title": "Episode 2", "absolute_number": 2}
        }
        
        params = {
            "provider": "tvdb",
            "show_id": "12345",
            "season": "1",
            "show_name": "My Show",
            "filenames": [
                "episode1.mp4",
                "episode2.mp4"
            ]
        }
        
        try:
            GUIRequestHandler.handle_api_match_episodes(dummy, params)
            result = dummy.sent_json
            self.assertIsNotNone(result)
            
            duplicates = result.get("duplicates", {})
            self.assertIn("episode1.mp4", duplicates)
            self.assertEqual(duplicates["episode1.mp4"]["filename"], "My Show - S01E01.mp4")
            
            self.assertNotIn("episode2.mp4", duplicates)
        finally:
            server.mw_metadata.fetch_tvdb = orig_fetch
            utils._MOCK_SETTINGS = None

    def test_preview_process_overrides_and_warning(self):
        import gui.server as server
        from gui.server import GUIRequestHandler
        
        inbox_dir = os.path.join(self.test_dir, "inbox_override_test")
        nas_root = os.path.join(self.test_dir, "nas_override_test")
        os.makedirs(inbox_dir, exist_ok=True)
        os.makedirs(nas_root, exist_ok=True)
        
        # Create folder in inbox
        project_dir = os.path.join(inbox_dir, "Show Override")
        os.makedirs(project_dir, exist_ok=True)
        with open(os.path.join(project_dir, "episode1.mp4"), "w") as f:
            f.write("video content")
            
        orig_load_settings = endpoints.load_settings
        utils._MOCK_SETTINGS = {
            "inbox_dir": inbox_dir,
            "outbox_dir": os.path.join(self.test_dir, "outbox_override_test"),
            "nas_root": nas_root,
            "sync_categories": [
                {"id": "2", "name": "Serien", "nas_sub": "/Serien"}
            ]
        }
        
        class DummyHandler:
            def __init__(self):
                self.sent_json = None
            def send_json(self, data):
                self.sent_json = data
                
        dummy = DummyHandler()
        
        params = {
            "media_type": "tv",
            "project_name": "Show Override",
            "show_name": "Show Override",
            "show_id": "123",
            "provider": "tmdb_tv",
            "season": "1",
            "copy_to_nas": True,
            "mappings": {
                "episode1.mp4": {
                    "season": 2,
                    "episode": 10,
                    "metadata_ep_num": "1"
                }
            }
        }
        
        orig_fetch = server.mw_metadata.fetch_tmdb_tv
        server.mw_metadata.fetch_tmdb_tv = lambda show_id, season, lang: {
            "1": {"title": "First Episode"}
        }
        
        try:
            GUIRequestHandler.handle_api_preview_process(dummy, params)
            result = dummy.sent_json
            self.assertIsNotNone(result)
            
            renames = result.get("renames", [])
            self.assertEqual(len(renames), 1)
            self.assertEqual(renames[0]["new"], "Show Override - S02E10 - First Episode.mp4")
            
            nas_show_dir = os.path.join(nas_root, "Serien", "Show Override")
            os.makedirs(os.path.join(nas_show_dir, "Staffel 2026"), exist_ok=True)
            
            dummy2 = DummyHandler()
            GUIRequestHandler.handle_api_preview_process(dummy2, params)
            result2 = dummy2.sent_json
            self.assertIsNotNone(result2)
            self.assertIn("warning", result2)
            self.assertIn("Abweichung der Nummerierung", result2["warning"])
            
        finally:
            server.mw_metadata.fetch_tmdb_tv = orig_fetch
            utils._MOCK_SETTINGS = None

    def test_find_folder_by_id_and_name_mismatch(self):
        import gui.server as server
        from gui.server import GUIRequestHandler
        
        nas_root = os.path.join(self.test_dir, "nas_find_id_test")
        inbox_dir = os.path.join(self.test_dir, "inbox_find_id_test")
        os.makedirs(nas_root, exist_ok=True)
        os.makedirs(inbox_dir, exist_ok=True)
        
        # Create folder on NAS that matches ID but has a different name
        nas_show_dir = os.path.join(nas_root, "Serien", "Yu-Gi-Oh! (2000)")
        os.makedirs(nas_show_dir, exist_ok=True)
        with open(os.path.join(nas_show_dir, "tvshow.nfo"), "w") as f:
            f.write("<tvshow><tmdbid>12345</tmdbid><title>Yu-Gi-Oh! (2000)</title></tvshow>")
            
        orig_load_settings = endpoints.load_settings
        utils._MOCK_SETTINGS = {
            "inbox_dir": inbox_dir,
            "outbox_dir": os.path.join(self.test_dir, "outbox_find_id_test"),
            "nas_root": nas_root,
            "sync_categories": [
                {"id": "2", "name": "Serien", "nas_sub": "/Serien"}
            ]
        }
        
        # Test 1: find-folder-by-id API
        from gui.api.search_api import find_existing_series_folder_by_id
        folder = find_existing_series_folder_by_id(os.path.join(nas_root, "Serien"), "tmdb_tv", "12345")
        self.assertEqual(folder, "Yu-Gi-Oh! (2000)")
        
        # Test 2: Preview show name mismatch
        class DummyHandler:
            def __init__(self):
                self.sent_json = None
            def send_json(self, data):
                self.sent_json = data
                
        dummy = DummyHandler()
        
        # Create temporary project files so preview scanner works
        project_dir = os.path.join(inbox_dir, "Yu-Gi-Oh!")
        os.makedirs(project_dir, exist_ok=True)
        with open(os.path.join(project_dir, "ep1.mp4"), "w") as f:
            f.write("content")
            
        params = {
            "media_type": "tv",
            "project_name": "Yu-Gi-Oh!",
            "show_name": "Yu-Gi-Oh! Duel Monsters",
            "show_id": "12345",
            "provider": "tmdb_tv",
            "season": "1",
            "copy_to_nas": True,
            "mappings": {
                "ep1.mp4": "1"
            }
        }
        
        orig_fetch = server.mw_metadata.fetch_tmdb_tv
        server.mw_metadata.fetch_tmdb_tv = lambda show_id, season, lang: {
            "1": {"title": "First Episode"}
        }
        
        try:
            GUIRequestHandler.handle_api_preview_process(dummy, params)
            result = dummy.sent_json
            self.assertIsNotNone(result)
            
            mismatch = result.get("show_name_mismatch")
            self.assertIsNotNone(mismatch)
            self.assertEqual(mismatch["nas_name"], "Yu-Gi-Oh! (2000)")
            self.assertEqual(mismatch["metadata_name"], "Yu-Gi-Oh! Duel Monsters")
        finally:
            server.mw_metadata.fetch_tmdb_tv = orig_fetch
            utils._MOCK_SETTINGS = None

    def test_false_positive_show_name_mismatch_with_different_years(self):
        import gui.server as server
        from gui.server import GUIRequestHandler
        import gui.core.series_helper as series_helper
        nas_root = os.path.join(self.test_dir, "nas_find_id_avatar_test")
        inbox_dir = os.path.join(self.test_dir, "inbox_find_id_avatar_test")
        os.makedirs(nas_root, exist_ok=True)
        os.makedirs(inbox_dir, exist_ok=True)
        nas_show_dir_2005 = os.path.join(nas_root, "Serien", "Avatar - Der Herr der Elemente (2005)")
        os.makedirs(nas_show_dir_2005, exist_ok=True)
        with open(os.path.join(nas_show_dir_2005, "tvshow.nfo"), "w") as f:
            f.write("<tvshow><tmdbid>246</tmdbid><title>Avatar - Der Herr der Elemente (2005)</title></tvshow>")
        utils._MOCK_SETTINGS = {
            "inbox_dir": inbox_dir,
            "outbox_dir": os.path.join(self.test_dir, "outbox_find_id_avatar_test"),
            "nas_root": nas_root,
            "sync_categories": [
                {"id": "2", "name": "Serien", "nas_sub": "/Serien"}
            ]
        }
        orig_find_folder = series_helper.find_existing_series_folder_by_id
        series_helper.find_existing_series_folder_by_id = lambda path, prov, sid: (
            "Avatar - Der Herr der Elemente (2024)" if sid == "82452" else orig_find_folder(path, prov, sid)
        )
        class DummyHandler:
            def __init__(self):
                self.sent_json = None
            def send_json(self, data):
                self.sent_json = data
        dummy = DummyHandler()
        project_dir = os.path.join(inbox_dir, "Avatar")
        os.makedirs(project_dir, exist_ok=True)
        with open(os.path.join(project_dir, "ep1.mp4"), "w") as f:
            f.write("content")
        params = {
            "media_type": "tv",
            "project_name": "Avatar",
            "show_name": "Avatar - Der Herr der Elemente (2024)",
            "show_id": "82452",
            "provider": "tmdb_tv",
            "season": "2",
            "copy_to_nas": True,
            "mappings": {
                "ep1.mp4": "1"
            }
        }
        orig_fetch = server.mw_metadata.fetch_tmdb_tv
        server.mw_metadata.fetch_tmdb_tv = lambda show_id, season, lang: {
            "1": {"title": "First Episode"}
        }
        try:
            GUIRequestHandler.handle_api_preview_process(dummy, params)
            result = dummy.sent_json
            self.assertIsNotNone(result)
            self.assertNotIn("show_name_mismatch", result)
        finally:
            server.mw_metadata.fetch_tmdb_tv = orig_fetch
            series_helper.find_existing_series_folder_by_id = orig_find_folder
            utils._MOCK_SETTINGS = None

    def test_inconsistent_naming_health_check(self):
        from gui.core.health import _check_series_show
        from gui.core import artwork_validators
        val = artwork_validators.get_validator("emby")
        
        nas_root = os.path.join(self.test_dir, "nas_health_naming_test")
        os.makedirs(nas_root, exist_ok=True)
        
        show_path = os.path.join(nas_root, "Yu-Gi-Oh! (2000)")
        season1_path = os.path.join(show_path, "Staffel 1")
        season2_path = os.path.join(show_path, "Staffel 2")
        os.makedirs(season1_path, exist_ok=True)
        os.makedirs(season2_path, exist_ok=True)
        
        # Scenario A: Inconsistent naming between files in different seasons
        with open(os.path.join(season1_path, "Yu-Gi-Oh! Duel Monsters - S01E01.mp4"), "w") as f:
            f.write("video")
        with open(os.path.join(season2_path, "Yu-Gi-Oh! - S02E01.mp4"), "w") as f:
            f.write("video")
            
        issues = []
        _check_series_show(issues, "Serien", show_path, val)
        
        naming_issues = [i for i in issues if i["type"] == "inconsistent_naming"]
        self.assertTrue(len(naming_issues) > 0)
        self.assertIn("Uneinheitliche Benennung", naming_issues[0]["message"])
        
        # Clean up files for Scenario B
        os.remove(os.path.join(season1_path, "Yu-Gi-Oh! Duel Monsters - S01E01.mp4"))
        os.remove(os.path.join(season2_path, "Yu-Gi-Oh! - S02E01.mp4"))
        
        # Scenario B: Consistent naming but differs from folder name
        with open(os.path.join(season1_path, "Yu-Gi-Oh! Duel Monsters - S01E01.mp4"), "w") as f:
            f.write("video")
        with open(os.path.join(season2_path, "Yu-Gi-Oh! Duel Monsters - S02E01.mp4"), "w") as f:
            f.write("video")
            
        issues = []
        _check_series_show(issues, "Serien", show_path, val)
        naming_issues = [i for i in issues if i["type"] == "inconsistent_naming"]
        self.assertTrue(len(naming_issues) > 0)
        self.assertIn("anderen Seriennamen", naming_issues[0]["message"])

    def test_local_pcloud_mount_path_fix(self):
        from unittest.mock import patch, MagicMock
        from gui.core.transfers import copy_to_cloud_target

        with patch("gui.core.transfers.load_settings") as mock_load_settings, \
             patch("gui.core.transfers.os.path.isdir", return_value=True) as mock_isdir, \
             patch("gui.core.transfers.subprocess.run") as mock_run, \
             patch("gui.core.transfers.run_rsync_with_progress", return_value=True) as mock_rsync:

            mock_load_settings.return_value = {
                "pcloud_dir": "/Volumes/pCloud",
                "open_pcloud_finder": False,
                "nas_root": "/Volumes/Kino",
                "storage_targets": [
                    {
                        "id": "nas",
                        "name": "NAS",
                        "type": "nas",
                        "root_path": "/Volumes/Kino",
                        "enabled": True
                    },
                    {
                        "id": "pcloud",
                        "name": "pCloud",
                        "type": "cloud",
                        "rclone_remote": "",
                        "root_path": "/Volumes/pCloud",
                        "enabled": True
                    }
                ],
                "sync_categories": [
                    {
                        "id": "1",
                        "nas_sub": "/Serien",
                        "pcloud_remote": "pcloud:04a_Dokus",
                        "targets": {
                            "pcloud": "pcloud:04a_Dokus"
                        }
                    }
                ]
            }

            success = copy_to_cloud_target(
                source_dir="/tmp/outbox/Serienname",
                nas_target_dir="/Volumes/Kino/Serien",
                target_id="pcloud",
                task_id="test_task",
                explicit_remote_base="pcloud:04a_Dokus"
            )

            self.assertTrue(success)
            mock_rsync.assert_called_once()
            called_args = mock_rsync.call_args[0]
            self.assertEqual(called_args[0], "/tmp/outbox/Serienname")
            self.assertEqual(called_args[1], "/Volumes/pCloud/04a_Dokus/Serienname")

    def test_resolve_category_target_path(self):
        from unittest.mock import patch
        from gui.core.transfers import resolve_category_target_path

        with patch("gui.core.transfers.load_settings") as mock_load_settings:
            mock_load_settings.return_value = {
                "storage_targets": [
                    {
                        "id": "pcloud",
                        "name": "pCloud",
                        "type": "cloud",
                        "rclone_remote": "pcloud:"
                    }
                ],
                "sync_categories": [
                    {
                        "id": "1",
                        "nas_sub": "/Serien",
                        "pcloud_remote": "pcloud:04a_Dokus",
                        "targets": {
                            "pcloud": "pcloud:04a_Dokus"
                        }
                    }
                ]
            }

            # Resolve by category ID
            path_by_id = resolve_category_target_path("1", "pcloud", "tv")
            self.assertEqual(path_by_id, "pcloud:04a_Dokus")

            # Resolve by nas_sub
            path_by_sub = resolve_category_target_path("/Serien", "pcloud", "tv")
            self.assertEqual(path_by_sub, "pcloud:04a_Dokus")

            # Test empty target mapping fallback to pcloud_remote
            mock_load_settings.return_value = {
                "storage_targets": [
                    {
                        "id": "pcloud",
                        "name": "pCloud",
                        "type": "cloud",
                        "rclone_remote": "pcloud:"
                    }
                ],
                "sync_categories": [
                    {
                        "id": "4",
                        "nas_sub": "/Serien",
                        "pcloud_remote": "pcloud:04a_Dokus",
                        "targets": {
                            "pcloud": ""
                        }
                    }
                ]
            }
            path_empty_target = resolve_category_target_path("4", "pcloud", "tv")
            self.assertEqual(path_empty_target, "pcloud:04a_Dokus")

    def test_nfo_agent_job_series(self):
        # Create temp folder for project
        proj_dir = os.path.join(self.test_dir, "nfo_agent_series_project")
        os.makedirs(proj_dir, exist_ok=True)
        
        # Create mock episode file
        ep_file = "Show - S01E01.mp4"
        with open(os.path.join(proj_dir, ep_file), "w") as f:
            f.write("mock video content")
            
        params = {
            "media_type": "tool_nfo_agent",
            "nfo_type": "tvshow",
            "project_name": proj_dir,
            "provider": "manual",
            "show_id": "manual",
            "season": 1,
            "mappings": {
                ep_file: "S01E01"
            },
            "nfo_overrides": {
                "show": {
                    "title": "NFO Agent Show",
                    "year": "2026",
                    "plot": "Show Plot Override"
                },
                "episodes": {
                    ep_file: {
                        "title": "Ep 1 Override",
                        "plot": "Ep 1 Plot Override"
                    }
                }
            },
            "overwrite_nfo": True
        }
        
        from gui.workers.processor import process_worker
        from unittest.mock import patch
        
        # Patch load_settings and is_path_allowed
        with patch("gui.workers.processor.load_settings", return_value={
            "inbox_dir": self.test_dir,
            "nas_root": os.path.join(self.test_dir, "nas_root"),
            "outbox_dir": os.path.join(self.test_dir, "outbox_dir")
        }):
            with patch("gui.core.helpers.is_path_allowed", return_value=True):
                process_worker(params)
                
        # Asserts: NFOs generated
        show_nfo = os.path.join(proj_dir, "tvshow.nfo")
        ep_nfo = os.path.join(proj_dir, "Show - S01E01.nfo")
        self.assertTrue(os.path.exists(show_nfo))
        self.assertTrue(os.path.exists(ep_nfo))
        
        # Verify content
        import xml.etree.ElementTree as ET
        tree_show = ET.parse(show_nfo)
        self.assertEqual(tree_show.find("title").text, "NFO Agent Show")
        self.assertEqual(tree_show.find("plot").text, "Show Plot Override")
        
        tree_ep = ET.parse(ep_nfo)
        self.assertEqual(tree_ep.find("title").text, "Ep 1 Override")
        self.assertEqual(tree_ep.find("plot").text, "Ep 1 Plot Override")
        
        # Safety asserts: NO files moved/deleted/converted
        # The video file must still exist in proj_dir
        self.assertTrue(os.path.exists(os.path.join(proj_dir, ep_file)))
        # No files should exist in outbox or nas
        nas_root = os.path.join(self.test_dir, "nas_root")
        self.assertFalse(os.path.exists(nas_root))

    def test_nfo_agent_job_movie(self):
        proj_dir = os.path.join(self.test_dir, "nfo_agent_movie_project")
        os.makedirs(proj_dir, exist_ok=True)
        
        movie_file = "Movie (2026).mp4"
        with open(os.path.join(proj_dir, movie_file), "w") as f:
            f.write("mock video content")
            
        params = {
            "media_type": "tool_nfo_agent",
            "nfo_type": "movie",
            "project_name": proj_dir,
            "provider": "manual",
            "movie_id": "manual",
            "nfo_overrides": {
                "movie": {
                    "title": "NFO Agent Movie",
                    "year": "2026",
                    "plot": "Movie Plot Override"
                }
            },
            "overwrite_nfo": True
        }
        
        from gui.workers.processor import process_worker
        from unittest.mock import patch
        
        with patch("gui.workers.processor.load_settings", return_value={
            "inbox_dir": self.test_dir,
            "nas_root": os.path.join(self.test_dir, "nas_root"),
            "outbox_dir": os.path.join(self.test_dir, "outbox_dir")
        }):
            with patch("gui.core.helpers.is_path_allowed", return_value=True):
                process_worker(params)
                
        # Asserts: movie NFO generated in proj_dir
        movie_nfo = os.path.join(proj_dir, "nfo_agent_movie_project.nfo")
        self.assertTrue(os.path.exists(movie_nfo))
        
        import xml.etree.ElementTree as ET
        tree = ET.parse(movie_nfo)
        self.assertEqual(tree.find("title").text, "NFO Agent Movie")
        self.assertEqual(tree.find("plot").text, "Movie Plot Override")
        
        # Safety asserts: video file still in project dir, not moved/converted
        self.assertTrue(os.path.exists(os.path.join(proj_dir, movie_file)))

    def test_nfo_agent_job_path_denied(self):
        from gui.workers.processor import process_worker
        from unittest.mock import patch
        
        params = {
            "media_type": "tool_nfo_agent",
            "nfo_type": "tvshow",
            "project_name": "/forbidden_path",
            "provider": "manual"
        }
        
        with patch("gui.workers.processor.load_settings", return_value={
            "inbox_dir": self.test_dir,
            "nas_root": os.path.join(self.test_dir, "nas_root"),
            "outbox_dir": os.path.join(self.test_dir, "outbox_dir")
        }):
            with patch("gui.core.helpers.is_path_allowed", return_value=False):
                with self.assertRaises(RuntimeError) as context:
                    process_worker(params)
                self.assertIn("Access Denied", str(context.exception))

if __name__ == "__main__":
    unittest.main()
