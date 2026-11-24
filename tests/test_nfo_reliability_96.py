import os
import shutil
import tempfile
import unittest
import urllib.error
import xml.etree.ElementTree as ET
from unittest.mock import patch

import gui.core.persistence as persistence
import gui.mw_metadata as mw_metadata
import gui.workers.processor as processor
from gui.core.jobs import active_jobs, active_jobs_lock


class TestNfoReliability96(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.orig_env = {
            k: os.environ.get(k)
            for k in (
                "MW_SETTINGS_FILE",
                "MW_JOBS_STATE_FILE",
                "MW_ENV_FILE",
                "MW_DATA_DIR",
                "FLASK_SECRET_KEY",
            )
        }
        os.environ["MW_SETTINGS_FILE"] = os.path.join(self.temp_dir.name, "settings.json")
        os.environ["MW_JOBS_STATE_FILE"] = os.path.join(self.temp_dir.name, "jobs_state.json")
        os.environ["MW_ENV_FILE"] = os.path.join(self.temp_dir.name, ".env")
        os.environ["MW_DATA_DIR"] = self.temp_dir.name
        os.environ["FLASK_SECRET_KEY"] = "test-secret"

        persistence._cached_settings = None
        persistence._cached_env = None

        self.inbox_dir = os.path.join(self.temp_dir.name, "inbox")
        self.outbox_dir = os.path.join(self.temp_dir.name, "outbox")
        self.nas_root = os.path.join(self.temp_dir.name, "nas")
        self.trash_dir = os.path.join(self.temp_dir.name, "_trash")
        os.makedirs(self.inbox_dir, exist_ok=True)
        os.makedirs(self.outbox_dir, exist_ok=True)
        os.makedirs(self.nas_root, exist_ok=True)
        os.makedirs(self.trash_dir, exist_ok=True)

        persistence.save_settings(
            {
                "inbox_dir": self.inbox_dir,
                "outbox_dir": self.outbox_dir,
                "nas_root": self.nas_root,
                "media_server": "emby",
                "storage_targets": [
                    {"id": "nas", "type": "nas", "root_path": self.nas_root, "enabled": True}
                ],
            }
        )

        self.trashed_items = []
        self._trash_counter = 0

        def _fake_send_to_trash(path, *args, **kwargs):
            if path and os.path.exists(path):
                self._trash_counter += 1
                dest_name = f"{self._trash_counter}_{os.path.basename(os.path.normpath(path))}"
                dest_path = os.path.join(self.trash_dir, dest_name)
                shutil.move(path, dest_path)
                self.trashed_items.append((path, dest_path))
                return True
            return False

        self.patcher_trash = patch("gui.core.trash.send_to_trash", side_effect=_fake_send_to_trash)
        self.patcher_nas = patch("gui.workers.processor.ensure_nas_mounted", return_value=True)
        self.patcher_rsync = patch("gui.workers.processor.run_rsync_with_progress", return_value=True)
        self.patcher_trash.start()
        self.patcher_nas.start()
        self.patcher_rsync.start()

    def tearDown(self):
        self.patcher_trash.stop()
        self.patcher_nas.stop()
        self.patcher_rsync.stop()
        for k, v in self.orig_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        persistence._cached_settings = None
        persistence._cached_env = None
        self.temp_dir.cleanup()

    def _make_movie_project(self, folder_name, video_name, stale_nfo_name=None, stale_nfo_content=None):
        proj_dir = os.path.join(self.inbox_dir, folder_name)
        os.makedirs(proj_dir, exist_ok=True)
        with open(os.path.join(proj_dir, video_name), "wb") as f:
            f.write(b"video-data")
        if stale_nfo_name:
            with open(os.path.join(proj_dir, stale_nfo_name), "w", encoding="utf-8") as f:
                f.write(stale_nfo_content or "<movie><title>Alt-NFO</title></movie>")
        return proj_dir

    def test_1_roadmap_96_movie_fresh_nfo_survives_explicit_junk(self):
        """ROADMAP #96: Fresh movie NFO sharing name with trashed explicit_junk entry is moved to outbox."""
        proj_dir = self._make_movie_project(
            "Die Odyssee (2026)",
            "Die Odyssee (2026).mkv",
            stale_nfo_name="Die Odyssee (2026).nfo",
            stale_nfo_content="<movie><title>Veraltete Alt-NFO</title></movie>",
        )

        def fake_generate_movie_nfo(mid, folder, base, **kwargs):
            nfo_file = os.path.join(folder, f"{base}.nfo")
            with open(nfo_file, "w", encoding="utf-8") as f:
                f.write(
                    '<?xml version="1.0" encoding="UTF-8"?>\n'
                    "<movie><title>Provider Titel</title><year>2026</year><mpaa>FSK 6</mpaa></movie>\n"
                )
            return {"nfo": True}

        params = {
            "project_name": "Die Odyssee (2026)",
            "media_type": "movie",
            "movie_name": "Die Odyssee (2026)",
            "movie_id": "99901",
            "provider": "tmdb",
            "convert": False,
            "copy_to_nas": False,
            "copy_to_pcloud": False,
            "delete_original": False,
            "overwrite_nfo": False,
            "wizard_overrides": True,
            "nfo_overrides": {"movie": {"title": "Die Odyssee", "year": "2026", "fsk": "12"}},
            "explicit_renames": [{"old": "Die Odyssee (2026).mkv", "new": "Die Odyssee (2026).mkv"}],
            "explicit_junk": ["Die Odyssee (2026).nfo"],
        }

        with patch("gui.mw_metadata.generate_movie_nfo", side_effect=fake_generate_movie_nfo):
            processor.process_worker(params)

        stale_nfo_orig = os.path.join(proj_dir, "Die Odyssee (2026).nfo")
        trashed_stale = [dest for orig, dest in self.trashed_items if orig == stale_nfo_orig]
        self.assertEqual(len(trashed_stale), 1)
        with open(trashed_stale[0], "r", encoding="utf-8") as f:
            self.assertIn("Veraltete Alt-NFO", f.read())

        outbox_nfo = os.path.join(self.outbox_dir, "Filme", "Die Odyssee (2026)", "Die Odyssee (2026).nfo")
        self.assertTrue(os.path.isfile(outbox_nfo), "Neu erzeugte NFO muss in Outbox ankommen")
        tree = ET.parse(outbox_nfo)
        self.assertEqual(tree.findtext("title"), "Die Odyssee")
        self.assertEqual(tree.findtext("year"), "2026")
        self.assertEqual(tree.findtext("mpaa"), "FSK 12")

    def test_2_safe_move_recursive_protected_paths_isolation(self):
        """safe_move_recursive moves only exact protected_paths while still filtering same-named subfolder junk."""
        src_dir = os.path.join(self.temp_dir.name, "safe_move_src")
        dest_dir = os.path.join(self.temp_dir.name, "safe_move_dest")
        sub_dir = os.path.join(src_dir, "Sub")
        os.makedirs(sub_dir, exist_ok=True)
        os.makedirs(dest_dir, exist_ok=True)

        main_nfo = os.path.join(src_dir, "Die Odyssee (2026).nfo")
        sub_same_nfo = os.path.join(sub_dir, "Die Odyssee (2026).nfo")
        sub_sample_nfo = os.path.join(sub_dir, "sample.nfo")
        release_txt = os.path.join(src_dir, "release.txt")

        for p, content in (
            (main_nfo, "FRESH_MAIN"),
            (sub_same_nfo, "SUBFOLDER_JUNK"),
            (sub_sample_nfo, "SAMPLE_JUNK"),
            (release_txt, "RELEASE_JUNK"),
        ):
            with open(p, "w", encoding="utf-8") as f:
                f.write(content)

        processor.safe_move_recursive(
            src_dir,
            dest_dir,
            junk_list=["Die Odyssee (2026).nfo", "Sub/sample.nfo", "release.txt"],
            protected_paths=[main_nfo],
        )

        moved_main = os.path.join(dest_dir, "Die Odyssee (2026).nfo")
        self.assertTrue(os.path.isfile(moved_main))
        with open(moved_main, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "FRESH_MAIN")
        self.assertFalse(os.path.exists(main_nfo))

        # Subfolder file with identical basename and other junk files must stay skipped
        self.assertTrue(os.path.isfile(sub_same_nfo))
        self.assertTrue(os.path.isfile(sub_sample_nfo))
        self.assertTrue(os.path.isfile(release_txt))
        self.assertFalse(os.path.exists(os.path.join(dest_dir, "sample.nfo")))
        self.assertFalse(os.path.exists(os.path.join(dest_dir, "release.txt")))

    def test_3_roadmap_96_tv_episode_fresh_nfo_survives_explicit_junk(self):
        """ROADMAP #96 (TV): Fresh episode NFO sharing name with trashed explicit_junk entry arrives in outbox."""
        proj_dir = os.path.join(self.inbox_dir, "TestSerie")
        os.makedirs(proj_dir, exist_ok=True)
        with open(os.path.join(proj_dir, "raw_ep1.mkv"), "wb") as f:
            f.write(b"video-ep1")

        ep_clean_title = "TestSerie - S01E01 - Pilot"
        stale_ep_nfo = os.path.join(proj_dir, f"{ep_clean_title}.nfo")
        with open(stale_ep_nfo, "w", encoding="utf-8") as f:
            f.write("<episodedetails><title>Veraltete Episoden-NFO</title></episodedetails>")

        def fake_generate_episode_nfo(provider, show_id, season, episode, target_folder, filename_base, **kwargs):
            nfo_path = os.path.join(target_folder, f"{filename_base}.nfo")
            with open(nfo_path, "w", encoding="utf-8") as f:
                f.write("<episodedetails><title>Frischer Episoden-Titel</title></episodedetails>")
            return {"nfo": True}

        params = {
            "project_name": "TestSerie",
            "media_type": "tv",
            "show_name": "TestSerie",
            "show_id": "555",
            "provider": "tmdb_tv",
            "season": 1,
            "convert": False,
            "copy_to_nas": False,
            "copy_to_pcloud": False,
            "delete_original": False,
            "overwrite_nfo": False,
            "explicit_renames": [{"old": "raw_ep1.mkv", "new": f"{ep_clean_title}.mkv"}],
            "explicit_junk": [f"{ep_clean_title}.nfo"],
            "mappings": {
                f"{ep_clean_title}.mkv": {"season": 1, "episode": 1, "title": "Pilot"},
            },
        }

        with patch("gui.mw_metadata.fetch_tmdb_tv", return_value={"S01E01": {"title": "Pilot"}}), \
             patch("gui.mw_metadata.generate_tvshow_nfo", return_value={"nfo": True}), \
             patch("gui.mw_metadata.generate_episode_nfo", side_effect=fake_generate_episode_nfo):
            processor.process_worker(params)

        trashed_stale = [dest for orig, dest in self.trashed_items if orig == stale_ep_nfo]
        self.assertEqual(len(trashed_stale), 1)
        with open(trashed_stale[0], "r", encoding="utf-8") as f:
            self.assertIn("Veraltete Episoden-NFO", f.read())

        outbox_ep_nfo = os.path.join(
            self.outbox_dir, "Serien", "TestSerie", "Staffel 1", ep_clean_title, f"{ep_clean_title}.nfo"
        )
        self.assertTrue(os.path.isfile(outbox_ep_nfo), "Frisch erzeugte Episoden-NFO muss in Outbox ankommen")
        with open(outbox_ep_nfo, "r", encoding="utf-8") as f:
            self.assertIn("Frischer Episoden-Titel", f.read())

    def test_4_generate_ofdb_nfo_reports_errors_visibly(self):
        """generate_ofdb_nfo returns structured error dict and logs via log_message on invalid ID and network error."""
        target_dir = os.path.join(self.temp_dir.name, "ofdb_err")
        os.makedirs(target_dir, exist_ok=True)

        with patch("gui.mw_metadata.log_message") as mock_log:
            res_invalid = mw_metadata.generate_ofdb_nfo("ofdb_ungueltig", target_dir, "Testfilm (2025)")

        self.assertIs(res_invalid.get("nfo"), False)
        self.assertTrue(isinstance(res_invalid.get("error"), str) and len(res_invalid["error"]) > 0)
        logged_invalid = "\n".join(str(c.args[0]) for c in mock_log.call_args_list if c.args)
        self.assertIn("Ungültige OFDb-ID", logged_invalid)

        with patch("gui.mw_metadata.time.sleep", lambda s: None), \
             patch("gui.mw_metadata.fetch_html_with_retry", side_effect=urllib.error.URLError("timeout")), \
             patch("gui.mw_metadata.log_message") as mock_log:
            res_net = mw_metadata.generate_ofdb_nfo("ofdb_154_Die-Matrix", target_dir, "Matrix (1999)")

        self.assertIs(res_net.get("nfo"), False)
        self.assertIn("timeout", res_net.get("error", ""))
        logged_net = "\n".join(str(c.args[0]) for c in mock_log.call_args_list if c.args)
        self.assertIn("nicht abrufbar", logged_net)

        sample_html = "<html><head><title>OFDb - Matrix (1999)</title></head><body></body></html>"
        with patch("gui.mw_metadata.fetch_html_with_retry", return_value=sample_html), \
             patch("builtins.open", side_effect=OSError("disk full")), \
             patch("gui.mw_metadata.log_message") as mock_log:
            res_write = mw_metadata.generate_ofdb_nfo("ofdb_154_Die-Matrix", target_dir, "Matrix (1999)")

        self.assertIs(res_write.get("nfo"), False)
        self.assertIn("disk full", res_write.get("error", ""))
        logged_write = "\n".join(str(c.args[0]) for c in mock_log.call_args_list if c.args)
        self.assertIn("Schreibfehler", logged_write)

    def test_5_wizard_and_nfo_agent_provider_error_vs_local_patch(self):
        """Wizard & NFO agent abort loudly on provider failure (even with stale NFO), while NFO agent patch warns locally."""
        # (a) Wizard movie job with un-deleted stale NFO and provider error aborts without patching or moving
        stale_bytes = "<movie><title>Unberührte Alt-NFO</title><mpaa>FSK 6</mpaa></movie>"
        proj_fail = self._make_movie_project(
            "WizardFail",
            "WizardFail (2025).mkv",
            stale_nfo_name="WizardFail (2025).nfo",
            stale_nfo_content=stale_bytes,
        )
        task_id = "task-wizard-provider-fail"
        with active_jobs_lock:
            active_jobs[task_id] = {
                "id": task_id,
                "status": "running",
                "pipeline": {"metadata": {"status": "running", "progress": 0}},
            }

        params_fail = {
            "task_id": task_id,
            "project_name": "WizardFail",
            "media_type": "movie",
            "movie_name": "WizardFail (2025)",
            "movie_id": "12345",
            "provider": "tmdb",
            "convert": False,
            "copy_to_nas": False,
            "copy_to_pcloud": False,
            "delete_original": False,
            "overwrite_nfo": False,
            "wizard_overrides": True,
            "nfo_overrides": {"movie": {"fsk": "18"}},
        }
        try:
            with patch("gui.mw_metadata.generate_movie_nfo", return_value={"nfo": False, "error": "API Timeout"}):
                with self.assertRaises(RuntimeError):
                    processor.process_worker(params_fail)

            with active_jobs_lock:
                self.assertEqual(active_jobs[task_id]["status"], "error")
                self.assertEqual(active_jobs[task_id]["pipeline"]["metadata"]["status"], "failed")
        finally:
            with active_jobs_lock:
                active_jobs.pop(task_id, None)

        with open(os.path.join(proj_fail, "WizardFail (2025).nfo"), "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), stale_bytes)
        self.assertFalse(os.path.exists(os.path.join(self.outbox_dir, "Filme", "WizardFail (2025)")))

        # (b) Wizard movie job with empty movie_overrides ({}) still enters protected wizard branch (overwrite=True)
        proj_empty = self._make_movie_project(
            "WizardEmptyOverrides",
            "WizardEmpty (2025).mkv",
            stale_nfo_name="WizardEmpty (2025).nfo",
            stale_nfo_content=stale_bytes,
        )
        seen_overwrite = []

        def fake_tmdb_capture(mid, folder, base, nfo_overrides=None, overwrite=False, **kwargs):
            seen_overwrite.append(overwrite)
            if overwrite:
                with open(os.path.join(folder, f"{base}.nfo"), "w", encoding="utf-8") as nf:
                    nf.write("<movie><title>Neu Vom Provider</title></movie>")
                return {"nfo": True}
            return {"nfo": False}

        params_empty_ok = {
            "project_name": "WizardEmptyOverrides",
            "media_type": "movie",
            "movie_name": "WizardEmpty (2025)",
            "movie_id": "12345",
            "provider": "tmdb",
            "convert": False,
            "copy_to_nas": False,
            "copy_to_pcloud": False,
            "delete_original": False,
            "overwrite_nfo": False,
            "wizard_overrides": True,
            "nfo_overrides": {"movie": {}},
        }
        with patch("gui.mw_metadata.generate_movie_nfo", side_effect=fake_tmdb_capture):
            processor.process_worker(params_empty_ok)

        self.assertEqual(seen_overwrite, [True])
        outbox_empty_nfo = os.path.join(self.outbox_dir, "Filme", "WizardEmpty (2025)", "WizardEmpty (2025).nfo")
        with open(outbox_empty_nfo, "r", encoding="utf-8") as f:
            self.assertIn("Neu Vom Provider", f.read())

        # Empty movie_overrides ({}) + provider error must also abort loudly
        self._make_movie_project(
            "WizardEmptyFail",
            "WizardEmptyFail (2025).mkv",
            stale_nfo_name="WizardEmptyFail (2025).nfo",
            stale_nfo_content=stale_bytes,
        )
        params_empty_fail = dict(params_empty_ok)
        params_empty_fail["project_name"] = "WizardEmptyFail"
        params_empty_fail["movie_name"] = "WizardEmptyFail (2025)"
        with patch("gui.mw_metadata.generate_ofdb_nfo", return_value={"nfo": False, "error": "OFDb down"}):
            params_empty_fail["provider"] = "ofdb"
            params_empty_fail["movie_id"] = "ofdb_154_Die-Matrix"
            with self.assertRaises(RuntimeError):
                processor.process_worker(params_empty_fail)

        # (c) tool_nfo_agent (movie): replace + provider error raises RuntimeError; patch + provider error warns & patches
        agent_dir = os.path.join(self.inbox_dir, "AgentMovie (2025)")
        os.makedirs(agent_dir, exist_ok=True)
        agent_nfo = os.path.join(agent_dir, "AgentMovie (2025).nfo")
        with open(agent_nfo, "w", encoding="utf-8") as f:
            f.write("<movie><title>Bestandstitel</title><mpaa>FSK 6</mpaa></movie>\n")

        agent_replace_params = {
            "media_type": "tool_nfo_agent",
            "nfo_type": "movie",
            "project_name": agent_dir,
            "provider": "tmdb",
            "movie_id": "12345",
            "nfo_write_mode": "replace",
            "nfo_overrides": {"movie": {"fsk": "16"}},
        }
        with patch("gui.core.helpers.is_path_allowed", return_value=True), \
             patch("gui.mw_metadata.generate_movie_nfo", return_value={"nfo": False, "error": "TMDb offline"}):
            with self.assertRaisesRegex(RuntimeError, "TMDb offline"):
                processor.process_worker(agent_replace_params)

        with open(agent_nfo, "r", encoding="utf-8") as f:
            self.assertIn("<mpaa>FSK 6</mpaa>", f.read())

        agent_patch_params = dict(agent_replace_params)
        agent_patch_params["nfo_write_mode"] = "patch"
        with patch("gui.core.helpers.is_path_allowed", return_value=True), \
             patch("gui.mw_metadata.generate_movie_nfo", return_value={"nfo": False, "error": "TMDb offline"}), \
             patch("gui.workers.processor.log_message") as mock_log:
            processor.process_worker(agent_patch_params)

        logged_agent = "\n".join(str(c.args[0]) for c in mock_log.call_args_list if c.args)
        self.assertIn("TMDb offline", logged_agent)
        with open(agent_nfo, "r", encoding="utf-8") as f:
            patched_content = f.read()
        self.assertIn("<mpaa>FSK 16</mpaa>", patched_content)
        self.assertIn("<title>Bestandstitel</title>", patched_content)

        # (d) tool_nfo_agent (tvshow): replace + provider error raises RuntimeError; patch + provider error warns & patches
        show_dir = os.path.join(self.inbox_dir, "AgentShow")
        os.makedirs(show_dir, exist_ok=True)
        show_nfo = os.path.join(show_dir, "tvshow.nfo")
        with open(show_nfo, "w", encoding="utf-8") as f:
            f.write("<tvshow><title>Bestandsserie</title><mpaa>FSK 6</mpaa></tvshow>\n")

        show_replace_params = {
            "media_type": "tool_nfo_agent",
            "nfo_type": "tvshow",
            "project_name": show_dir,
            "provider": "tmdb_tv",
            "show_id": "555",
            "nfo_write_mode": "replace",
            "nfo_overrides": {"show": {"fsk": "12"}},
            "mappings": {},
        }
        with patch("gui.core.helpers.is_path_allowed", return_value=True), \
             patch("gui.mw_metadata.generate_tvshow_nfo", return_value={"nfo": False, "error": "TVDb offline"}):
            with self.assertRaisesRegex(RuntimeError, "TVDb offline"):
                processor.process_worker(show_replace_params)

        show_patch_params = dict(show_replace_params)
        show_patch_params["nfo_write_mode"] = "patch"
        with patch("gui.core.helpers.is_path_allowed", return_value=True), \
             patch("gui.mw_metadata.generate_tvshow_nfo", return_value={"nfo": False, "error": "TVDb offline"}), \
             patch("gui.workers.processor.log_message") as mock_log:
            processor.process_worker(show_patch_params)

        logged_show = "\n".join(str(c.args[0]) for c in mock_log.call_args_list if c.args)
        self.assertIn("TVDb offline", logged_show)
        with open(show_nfo, "r", encoding="utf-8") as f:
            show_patched = f.read()
        self.assertIn("<mpaa>FSK 12</mpaa>", show_patched)
        self.assertIn("<title>Bestandsserie</title>", show_patched)


if __name__ == "__main__":
    unittest.main()
