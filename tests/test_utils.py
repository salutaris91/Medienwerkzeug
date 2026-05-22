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

    def tearDown(self):
        # Restore original variables and functions
        utils.DATA_DIR = self.orig_data_dir
        utils.PROFILES_DIR = self.orig_profiles_dir
        utils.HISTORY_FILE = self.orig_history_file
        os.path.expanduser = self.orig_expanduser
        
        # Clean up temp files
        shutil.rmtree(self.test_dir)

    def test_clean_show_name(self):
        self.assertEqual(utils.clean_show_name("Breaking Bad [TMDB_TV]"), "breaking_bad_tmdb_tv")
        self.assertEqual(utils.clean_show_name("Kill Bill: Vol. 1"), "kill_bill_vol_1")
        self.assertEqual(utils.clean_show_name(""), "default")
        self.assertEqual(utils.clean_show_name(None), "default")

    def test_clean_series_name_for_fs(self):
        from gui import server
        self.assertEqual(server.clean_series_name_for_fs("Geheimnisse Asiens - Die schönsten Nationalparks (Mediathek Serie aus URL)"), "Geheimnisse Asiens - Die schönsten Nationalparks")
        self.assertEqual(server.clean_series_name_for_fs("Sendung mit der Maus (Freie Mediathek-Suche)"), "Sendung mit der Maus")
        self.assertEqual(server.clean_series_name_for_fs("Doctor Who (fernsehserien.de URL)"), "Doctor Who")
        self.assertEqual(server.clean_series_name_for_fs("Doku - Geheimnisse Asiens [ARTE]"), "Doku - Geheimnisse Asiens")
        self.assertEqual(server.clean_series_name_for_fs("Entdeckung der Welt - Wunder der Tiefsee [ARTE.DE]"), "Entdeckung der Welt - Wunder der Tiefsee")
        self.assertEqual(server.clean_series_name_for_fs("Some Show"), "Some Show")
        self.assertEqual(server.clean_series_name_for_fs(""), "")
        self.assertEqual(server.clean_series_name_for_fs(None), "")

    def test_filename_sanitization_and_length_limit(self):
        from gui import server
        self.assertEqual(server.sanitize_filename("A - B: C"), "A - B - C")
        self.assertEqual(server.sanitize_filename("A/B|C?D*E"), "A - B - CDE")
        long_name = "a" * 200
        truncated = server.limit_filename_length(long_name, 160)
        self.assertEqual(len(truncated), 160)
        self.assertTrue(truncated.endswith("..."))
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

    def test_profile_migration(self):
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
        
        # Check that it saved locally as JSON
        local_json_path = os.path.join(utils.PROFILES_DIR, "breaking_bad.json")
        self.assertTrue(os.path.exists(local_json_path))
        with open(local_json_path, "r", encoding="utf-8") as f:
            local_data = json.load(f)
        self.assertEqual(local_data["provider"], "tvdb")

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
        
        # Median of [0.40, 0.50, 0.60] is 0.50
        self.assertEqual(media.konvertierung_schaetzen("nonexistent_file.mkv", 60), 0.50)
        
        # Add another to make it even: [0.40, 0.45, 0.50, 0.60] -> median is (0.45 + 0.50) / 2 = 0.475
        media.add_conversion_to_history(60, "hevc", 0.45)
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
        orig_load_settings = server.load_settings
        orig_log_message = server.log_message
        
        test_inbox = os.path.join(self.test_dir, "test_inbox")
        os.makedirs(test_inbox, exist_ok=True)
        
        server.load_settings = lambda: {"inbox_dir": test_inbox}
        
        # Mock log_message to capture it
        dummy = DummyHandler()
        server.log_message = lambda msg: dummy.logged_messages.append(msg)
        
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
            server.load_settings = orig_load_settings
            server.log_message = orig_log_message

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

        # Mock server functions
        orig_load_settings = server.load_settings
        orig_ensure_nas = server.ensure_nas_mounted
        orig_run_rsync = server.run_rsync_with_progress
        orig_run_ffmpeg = server.run_ffmpeg_with_progress
        orig_subprocess_run = subprocess.run
        
        orig_fetch_tmdb = server.mw_metadata.fetch_tmdb_tv
        orig_gen_show_nfo = server.mw_metadata.generate_tvshow_nfo
        orig_gen_ep_nfo = server.mw_metadata.generate_episode_nfo
        
        server.load_settings = lambda: {
            "inbox_dir": test_inbox,
            "outbox_dir": test_outbox,
            "nas_root": test_nas,
            "sync_categories": [
                {"id": "2", "name": "Serien", "nas_sub": "/Serien", "pcloud_remote": "pcloud:04_Serien"}
            ]
        }
        
        server.ensure_nas_mounted = lambda: True
        
        # Mock rsync to copy files (since process_worker expects rsync to do the copy)
        def mock_rsync(src, dst, task_id=None, move=False):
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy(src, dst)
            return True
        server.run_rsync_with_progress = mock_rsync
        
        # Mock ffmpeg to simulate converting: creates .mkv and doesn't crash
        def mock_ffmpeg(cmd, filepath, task_id=None, log_queue=None):
            # cmd is [..., temp_output]
            temp_out = cmd[-1]
            with open(temp_out, "w") as f:
                f.write("mock converted video content")
            return True
        server.run_ffmpeg_with_progress = mock_ffmpeg
        
        # Mock subprocess.run to prevent Finder from opening
        def mock_run(cmd, *args, **kwargs):
            if isinstance(cmd, list) and cmd[0] == "open":
                return subprocess.CompletedProcess(cmd, 0)
            return orig_subprocess_run(cmd, *args, **kwargs)
        subprocess.run = mock_run
        
        # Mock metadata calls
        server.mw_metadata.fetch_tmdb_tv = lambda show_id, season, lang: {
            "1": {"title": "Die Maus wird 50"}
        }
        server.mw_metadata.generate_tvshow_nfo = lambda provider, show_id, path: "success"
        server.mw_metadata.generate_episode_nfo = lambda provider, show_id, season, ep, path, title: "success"
        
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
            server.load_settings = orig_load_settings
            server.ensure_nas_mounted = orig_ensure_nas
            server.run_rsync_with_progress = orig_run_rsync
            server.run_ffmpeg_with_progress = orig_run_ffmpeg
            subprocess.run = orig_subprocess_run
            
            server.mw_metadata.fetch_tmdb_tv = orig_fetch_tmdb
            server.mw_metadata.generate_tvshow_nfo = orig_gen_show_nfo
            server.mw_metadata.generate_episode_nfo = orig_gen_ep_nfo

    @unittest.mock.patch('urllib.request.urlopen')
    def test_fetch_all_seasons(self, mock_urlopen):
        import json

        def side_effect(req):
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
            "S01E01": {"title": "Ep1", "date": "2020-01-01"},
            "S02E03": {"title": "Ep3", "date": "2020-02-02"}
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

    def test_import_streamfab_files_grouping(self):
        from gui import server
        orig_load_settings = server.load_settings
        
        # Setup temporary directories for testing
        test_inbox = os.path.join(self.test_dir, "import_inbox")
        test_sf_dir = os.path.join(self.test_dir, "import_sf")
        os.makedirs(test_inbox, exist_ok=True)
        os.makedirs(test_sf_dir, exist_ok=True)
        
        server.load_settings = lambda: {
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
            
            # Check single file is in root of inbox
            self.assertTrue(os.path.exists(os.path.join(test_inbox, "SingleVideo.mp4")))
            self.assertFalse(os.path.exists(os.path.join(test_inbox, "SingleVideo", "SingleVideo.mp4")))
            
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
            server.load_settings = orig_load_settings

if __name__ == "__main__":
    unittest.main()

