import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

import gui.core.persistence as persistence
import gui.workers.processor as processor
from gui.core.health import should_overwrite_nfo
from gui.core.jobs import active_jobs, active_jobs_lock


PROVIDER_NFO_BYTES = (
    b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    b'<movie>\n'
    b'  <lockdata>true</lockdata>\n'
    b'  <title>Provider Titel</title>\n'
    b'  <plot>Provider Plot</plot>\n'
    b'  <mpaa>FSK 12</mpaa>\n'
    b'  <year>2020</year>\n'
    b'  <genre>Drama</genre>\n'
    b'</movie>\n'
)


class TestInboxMovieOverrides(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.orig_env = {
            k: os.environ.get(k)
            for k in ("MW_SETTINGS_FILE", "MW_JOBS_STATE_FILE", "MW_ENV_FILE", "MW_DATA_DIR")
        }
        os.environ["MW_SETTINGS_FILE"] = os.path.join(self.temp_dir.name, "settings.json")
        os.environ["MW_JOBS_STATE_FILE"] = os.path.join(self.temp_dir.name, "jobs_state.json")
        os.environ["MW_ENV_FILE"] = os.path.join(self.temp_dir.name, ".env")
        os.environ["MW_DATA_DIR"] = self.temp_dir.name

        persistence._cached_settings = None
        persistence._cached_env = None

        self.inbox_dir = os.path.join(self.temp_dir.name, "inbox")
        self.outbox_dir = os.path.join(self.temp_dir.name, "outbox")
        self.nas_root = os.path.join(self.temp_dir.name, "nas")
        os.makedirs(self.inbox_dir, exist_ok=True)
        os.makedirs(self.outbox_dir, exist_ok=True)
        os.makedirs(self.nas_root, exist_ok=True)

        persistence.save_settings({
            "inbox_dir": self.inbox_dir,
            "outbox_dir": self.outbox_dir,
            "nas_root": self.nas_root,
            "media_server": "emby",
            "storage_targets": [
                {"id": "nas", "type": "nas", "root_path": self.nas_root, "enabled": True}
            ],
        })

        self.patcher_trash = patch("gui.core.trash.send_to_trash", return_value=True)
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

    def _make_movie_project(self, folder_name="Inception", video_name="raw.mkv"):
        proj_dir = os.path.join(self.inbox_dir, folder_name)
        os.makedirs(proj_dir, exist_ok=True)
        with open(os.path.join(proj_dir, video_name), "wb") as f:
            f.write(b"video")
        return proj_dir

    def _base_params(
        self,
        folder_name="Inception",
        provider="tmdb",
        movie_id="12345",
        overrides=None,
        wizard_overrides=True,
    ):
        params = {
            "project_name": folder_name,
            "media_type": "movie",
            "movie_name": "Inception (2010)",
            "movie_id": movie_id,
            "provider": provider,
            "convert": False,
            "copy_to_nas": False,
            "copy_to_pcloud": False,
            "delete_original": False,
            "overwrite_nfo": False,
        }
        if overrides is not None:
            params["nfo_overrides"] = {"movie": overrides}
            if wizard_overrides:
                params["wizard_overrides"] = True
        return params

    def test_e1_ak3_patches_tmdb_and_ofdb_into_clean_movie_name_nfo(self):
        """E1-AK3: Both TMDb and OFDb branches write overrides (incl. fsk & genres) into <clean_movie_name>.nfo."""
        for provider in ("tmdb", "ofdb"):
            with self.subTest(provider=provider):
                folder_name = f"Proj_{provider}"
                proj_dir = self._make_movie_project(folder_name)
                # Decoy movie.nfo that find_primary_nfo would return first
                decoy_nfo = os.path.join(proj_dir, "movie.nfo")
                with open(decoy_nfo, "wb") as f:
                    f.write(b"<movie><title>Decoy</title></movie>")

                def fake_tmdb(mid, folder, base, fallback_json=None, nfo_overrides=None, overwrite=False):
                    if overwrite or not os.path.exists(os.path.join(folder, f"{base}.nfo")):
                        with open(os.path.join(folder, f"{base}.nfo"), "wb") as nf:
                            nf.write(PROVIDER_NFO_BYTES)
                    return {"nfo": True}

                def fake_ofdb(mid, folder, base):
                    with open(os.path.join(folder, f"{base}.nfo"), "wb") as nf:
                        nf.write(PROVIDER_NFO_BYTES)
                    return {"nfo": True}

                overrides = {
                    "title": "Manueller Titel",
                    "year": "2010",
                    "plot": "Manueller Plot",
                    "fsk": "16",
                    "genres": ["Sci-Fi", "Thriller"],
                }
                with patch("gui.mw_metadata.generate_movie_nfo", side_effect=fake_tmdb), \
                     patch("gui.mw_metadata.generate_ofdb_nfo", side_effect=fake_ofdb):
                    processor.process_worker(self._base_params(folder_name, provider, "99", overrides))

                outbox_nfo = os.path.join(self.outbox_dir, "Filme", "Inception (2010)", "Inception (2010).nfo")
                self.assertTrue(os.path.isfile(outbox_nfo))
                with open(outbox_nfo, "r", encoding="utf-8") as f:
                    xml = f.read()
                self.assertIn("<title>Manueller Titel</title>", xml)
                self.assertIn("<year>2010</year>", xml)
                self.assertIn("<plot>Manueller Plot</plot>", xml)
                self.assertIn("<mpaa>FSK 16</mpaa>", xml)
                self.assertIn("<genre>Sci-Fi</genre>", xml)
                self.assertIn("<genre>Thriller</genre>", xml)
                self.assertNotIn("<genre>Drama</genre>", xml)

    def test_e1_ak4_byte_identical_without_overrides_and_partial_overrides(self):
        """E1-AK4: Without overrides NFO is byte-identical; omitted fields stay unchanged."""
        proj_dir = self._make_movie_project("NoOverrides")

        def fake_tmdb(mid, folder, base, **kwargs):
            with open(os.path.join(folder, f"{base}.nfo"), "wb") as nf:
                nf.write(PROVIDER_NFO_BYTES)
            return {"nfo": True}

        with patch("gui.mw_metadata.generate_movie_nfo", side_effect=fake_tmdb):
            processor.process_worker(self._base_params("NoOverrides", "tmdb", "1", overrides=None))

        outbox_nfo = os.path.join(self.outbox_dir, "Filme", "Inception (2010)", "Inception (2010).nfo")
        with open(outbox_nfo, "rb") as f:
            self.assertEqual(f.read(), PROVIDER_NFO_BYTES)

        # Partial override: only fsk provided -> title, plot, year, genre remain unchanged
        shutil.rmtree(os.path.join(self.outbox_dir, "Filme"))
        self._make_movie_project("PartialOverrides")
        with patch("gui.mw_metadata.generate_movie_nfo", side_effect=fake_tmdb):
            processor.process_worker(self._base_params("PartialOverrides", "tmdb", "1", overrides={"fsk": "18"}))

        with open(outbox_nfo, "r", encoding="utf-8") as f:
            xml = f.read()
        self.assertIn("<title>Provider Titel</title>", xml)
        self.assertIn("<plot>Provider Plot</plot>", xml)
        self.assertIn("<genre>Drama</genre>", xml)
        self.assertIn("<mpaa>FSK 18</mpaa>", xml)

    def test_e1_ak4_patch_error_aborts_job_before_convert_and_transfer(self):
        """E1-AK4 (D6a): patch_nfo_fields failure logs error, sets job error, and aborts before H.265/transfer."""
        self._make_movie_project("PatchFail")
        task_id = "test-task-patch-fail"
        with active_jobs_lock:
            active_jobs[task_id] = {
                "id": task_id,
                "status": "running",
                "pipeline": {"metadata": {"status": "running", "progress": 0}},
            }

        def fake_tmdb_corrupt(mid, folder, base, **kwargs):
            with open(os.path.join(folder, f"{base}.nfo"), "wb") as nf:
                nf.write(b"<movie><title>Unclosed XML")
            return {"nfo": True}

        params = self._base_params("PatchFail", "tmdb", "1", overrides={"fsk": "16"})
        params["task_id"] = task_id
        params["convert"] = True
        params["copy_to_nas"] = True

        with patch("gui.mw_metadata.generate_movie_nfo", side_effect=fake_tmdb_corrupt), \
             patch("gui.core.media.execute_video_conversion") as mock_conv, \
             patch("gui.workers.processor.log_message") as mock_log:
            with self.assertRaises(RuntimeError):
                processor.process_worker(params)

            mock_conv.assert_not_called()
            logged = "\n".join(str(c.args[0]) for c in mock_log.call_args_list if c.args)
            self.assertIn("❌", logged)

        with active_jobs_lock:
            self.assertEqual(active_jobs[task_id]["status"], "error")
            active_jobs.pop(task_id, None)

        outbox_movie_dir = os.path.join(self.outbox_dir, "Filme", "Inception (2010)")
        self.assertFalse(os.path.exists(outbox_movie_dir))

        # Fingerprint conflict on existing NFO aborts BEFORE provider mutation so protected file stays unchanged
        conflict_dir = self._make_movie_project("FingerprintConflict")
        protected_nfo = os.path.join(conflict_dir, "Inception (2010).nfo")
        protected_bytes = b"<movie><title>Geschuetzter Bestand</title><mpaa>FSK 6</mpaa></movie>"
        with open(protected_nfo, "wb") as f:
            f.write(protected_bytes)

        fp_params = self._base_params("FingerprintConflict", "tmdb", "1", overrides={"fsk": "12"})
        fp_params["main_nfo_fingerprint"] = {
            "path": os.path.realpath(protected_nfo),
            "size": 999,
            "hash": "0" * 64,
        }

        def fake_tmdb_ok(mid, folder, base, **kw):
            with open(os.path.join(folder, f"{base}.nfo"), "wb") as nf:
                nf.write(PROVIDER_NFO_BYTES)
            return {"nfo": True}

        with patch("gui.mw_metadata.generate_movie_nfo", side_effect=fake_tmdb_ok) as mock_gen:
            with self.assertRaises(RuntimeError) as ctx:
                processor.process_worker(fp_params)
            self.assertIn("seit der Vorschau verändert", str(ctx.exception))
            mock_gen.assert_not_called()
        with open(protected_nfo, "rb") as f:
            self.assertEqual(f.read(), protected_bytes)
        self.assertFalse(os.path.exists(outbox_movie_dir))

        # Valid fingerprint of existing NFO succeeds even when provider writes different content
        from gui.core.nfo_mutation import make_nfo_fingerprint
        valid_fp_dir = self._make_movie_project("FingerprintValidExisting")
        existing_nfo = os.path.join(valid_fp_dir, "Inception (2010).nfo")
        with open(existing_nfo, "wb") as f:
            f.write(protected_bytes)
        valid_fp_params = self._base_params(
            "FingerprintValidExisting", "tmdb", "1", overrides={"title": "Neuer Wizard Titel", "fsk": "16"}
        )
        valid_fp_params["main_nfo_fingerprint"] = make_nfo_fingerprint(existing_nfo)
        with patch("gui.mw_metadata.generate_movie_nfo", side_effect=fake_tmdb_ok):
            processor.process_worker(valid_fp_params)
        outbox_nfo = os.path.join(outbox_movie_dir, "Inception (2010).nfo")
        with open(outbox_nfo, "r", encoding="utf-8") as f:
            patched_xml = f.read()
        self.assertIn("<title>Neuer Wizard Titel</title>", patched_xml)
        self.assertIn("<mpaa>FSK 16</mpaa>", patched_xml)
        shutil.rmtree(os.path.join(self.outbox_dir, "Filme"))

        # Provider error WITHOUT overrides continues as before (logs and does not abort)
        self._make_movie_project("ProviderFailNoOverrides")
        with patch("gui.mw_metadata.generate_movie_nfo", side_effect=RuntimeError("API down")):
            processor.process_worker(self._base_params("ProviderFailNoOverrides", "tmdb", "1", overrides=None))
        self.assertTrue(os.path.isdir(outbox_movie_dir))

    def test_e1_ak5_non_wizard_film_and_doku_preserve_existing_nfo(self):
        """E1-AK5: Non-Wizard Film and Doku calls with existing NFO do not force overwrite or clear tags."""
        existing_bytes = (
            b'<?xml version="1.0" encoding="UTF-8"?>\n'
            b'<movie>\n'
            b'  <title>Bestandstitel</title>\n'
            b'  <plot>Bestandsplot</plot>\n'
            b'  <mpaa>FSK 12</mpaa>\n'
            b'  <genre>Dokumentation</genre>\n'
            b'</movie>\n'
        )
        for case_name, movie_name in (("LegacyFilm", "Inception (2010)"), ("LegacyDoku", "Unsere Erde Doku (2010)")):
            with self.subTest(case=case_name):
                proj_dir = self._make_movie_project(case_name)
                existing_nfo = os.path.join(proj_dir, f"{movie_name}.nfo")
                with open(existing_nfo, "wb") as f:
                    f.write(existing_bytes)

                def fake_tmdb_respect_overwrite(mid, folder, base, fallback_json=None, nfo_overrides=None, overwrite=False):
                    target = os.path.join(folder, f"{base}.nfo")
                    if overwrite or not os.path.exists(target):
                        with open(target, "wb") as nf:
                            nf.write(PROVIDER_NFO_BYTES)
                        return {"nfo": True}
                    return {"nfo": False, "msg": "skipped (already exists)"}

                params = self._base_params(
                    case_name,
                    "tmdb",
                    "1",
                    overrides={"title": "Ignorierter Legacy-Override", "year": "2010", "plot": ""},
                    wizard_overrides=False,
                )
                params["movie_name"] = movie_name
                with patch("gui.mw_metadata.generate_movie_nfo", side_effect=fake_tmdb_respect_overwrite):
                    processor.process_worker(params)

                outbox_nfo = os.path.join(self.outbox_dir, "Filme", movie_name, f"{movie_name}.nfo")
                with open(outbox_nfo, "rb") as f:
                    self.assertEqual(f.read(), existing_bytes)

    def test_e1_ak7_existing_nfo_overwritten_when_wizard_overrides_present(self):
        """E1-AK7 (D6b): Existing NFO in current_dir with overwrite_nfo=False is overwritten when Wizard overrides exist."""
        proj_dir = self._make_movie_project("ExistingNfo")
        stale_nfo = os.path.join(proj_dir, "Inception (2010).nfo")
        with open(stale_nfo, "wb") as f:
            f.write(b"<movie><title>Altbestand</title><mpaa>FSK 6</mpaa></movie>")

        def fake_tmdb(mid, folder, base, fallback_json=None, nfo_overrides=None, overwrite=False):
            target = os.path.join(folder, f"{base}.nfo")
            if overwrite or not os.path.exists(target):
                with open(target, "wb") as nf:
                    nf.write(PROVIDER_NFO_BYTES)
                return {"nfo": True}
            return {"nfo": False, "msg": "skipped (already exists)"}

        overrides = {"title": "Wizard Gewinnt", "fsk": "16", "genres": ["Action"]}
        with patch("gui.mw_metadata.generate_movie_nfo", side_effect=fake_tmdb):
            processor.process_worker(self._base_params("ExistingNfo", "tmdb", "1", overrides=overrides))

        outbox_nfo = os.path.join(self.outbox_dir, "Filme", "Inception (2010)", "Inception (2010).nfo")
        with open(outbox_nfo, "r", encoding="utf-8") as f:
            xml = f.read()
        self.assertIn("<title>Wizard Gewinnt</title>", xml)
        self.assertIn("<mpaa>FSK 16</mpaa>", xml)
        self.assertIn("<genre>Action</genre>", xml)
        self.assertNotIn("Altbestand", xml)

        # Other callers of should_overwrite_nfo remain unchanged
        self.assertFalse(should_overwrite_nfo(False, {"title": "X"}, outbox_nfo, "movie"))

    def test_e1_ak8_clearing_fields_removes_provider_tags_in_inbox_import(self):
        """E1-AK8 (D6c): Explicitly empty fsk/genres/plot in Wizard overrides remove provider tags from NFO."""
        self._make_movie_project("ClearFields")

        def fake_tmdb(mid, folder, base, **kwargs):
            with open(os.path.join(folder, f"{base}.nfo"), "wb") as nf:
                nf.write(PROVIDER_NFO_BYTES)
            return {"nfo": True}

        overrides = {"title": "Behalten", "year": "2020", "plot": "", "fsk": "", "genres": []}
        with patch("gui.mw_metadata.generate_movie_nfo", side_effect=fake_tmdb):
            processor.process_worker(self._base_params("ClearFields", "tmdb", "1", overrides=overrides))

        outbox_nfo = os.path.join(self.outbox_dir, "Filme", "Inception (2020)", "Inception (2020).nfo")
        with open(outbox_nfo, "r", encoding="utf-8") as f:
            xml = f.read()
        self.assertIn("<title>Behalten</title>", xml)
        self.assertIn("<year>2020</year>", xml)
        self.assertNotIn("<plot>", xml)
        self.assertNotIn("<mpaa>", xml)
        self.assertNotIn("<genre>", xml)


if __name__ == "__main__":
    unittest.main()
