import os
import unittest
import tempfile
import threading
import json
import time

class TestPersistence(unittest.TestCase):
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

        # Import persistence dynamically
        import gui.core.persistence as persistence
        self.persistence = persistence

        # Reset local cache
        self.persistence._cached_settings = None

    def tearDown(self):
        os.environ.pop("MW_SETTINGS_FILE", None)
        os.environ.pop("MW_JOBS_STATE_FILE", None)
        os.environ.pop("MW_ENV_FILE", None)
        os.environ.pop("MW_DATA_DIR", None)
        self.temp_dir.cleanup()

    def test_settings_default_fallback(self):
        """Checks if default values are loaded when file does not exist."""
        settings = self.persistence.load_settings()
        self.assertEqual(settings["version"], 1)
        self.assertEqual(settings["media_server"], "")
        self.assertEqual(settings["inbox_dir"], "")
        self.assertEqual(settings["outbox_dir"], "")

    def test_settings_save_and_load(self):
        """Verifies settings can be successfully saved and reloaded."""
        settings = self.persistence.load_settings()
        settings["media_server"] = "plex"
        settings["inbox_dir"] = "/test/inbox"
        success = self.persistence.save_settings(settings)
        self.assertTrue(success)
        self.persistence._cached_settings = None
        loaded = self.persistence.load_settings()
        self.assertEqual(loaded["media_server"], "plex")
        self.assertEqual(loaded["inbox_dir"], "/test/inbox")

    def test_backup_and_recovery_flow(self):
        """Verifies recovery of corrupted settings using backups."""
        settings = self.persistence.load_settings()
        settings["media_server"] = "jellyfin"
        self.persistence.save_settings(settings)
        settings["inbox_dir"] = "/test/validated"
        self.persistence.save_settings(settings)
        backup_path = self.settings_file + ".bak"
        self.assertTrue(os.path.exists(backup_path))
        with open(backup_path, "r", encoding="utf-8") as f:
            backup_data = json.load(f)
        self.assertEqual(backup_data["media_server"], "jellyfin")
        with open(self.settings_file, "w", encoding="utf-8") as f:
            f.write("{ INVALID JSON DATA }")
        self.persistence._cached_settings = None
        loaded = self.persistence.load_settings()
        self.assertEqual(loaded["media_server"], "jellyfin")
        with open(self.settings_file, "r", encoding="utf-8") as f:
            fixed_data = json.load(f)
        self.assertEqual(fixed_data["media_server"], "jellyfin")

    def test_backup_validation_guard(self):
        """Verifies that an invalid file does NOT overwrite a valid backup."""
        settings = self.persistence.load_settings()
        settings["media_server"] = "emby"
        self.persistence.save_settings(settings)
        self.persistence.save_settings(settings)
        backup_path = self.settings_file + ".bak"
        self.assertTrue(os.path.exists(backup_path))
        with open(self.settings_file, "w", encoding="utf-8") as f:
            f.write("{ CORRUPT }")
        res = self.persistence.backup_if_valid(self.settings_file, backup_path)
        self.assertFalse(res)
        with open(backup_path, "r", encoding="utf-8") as f:
            backup_data = json.load(f)
        self.assertEqual(backup_data["media_server"], "emby")

    def test_legacy_settings_migration(self):
        """Verifies that old settings with legacy keys are correctly migrated without path loss."""
        # Create a raw legacy settings file without version or storage_targets
        legacy_data = {
            "nas_root": "/Volumes/LegacyNAS",
            "pcloud_dir": "/Users/test/pCloudLegacy"
        }
        with open(self.settings_file, "w", encoding="utf-8") as f:
            json.dump(legacy_data, f)
        # Force fresh load
        self.persistence._cached_settings = None
        settings = self.persistence.load_settings()
        self.assertEqual(settings["version"], 1)
        self.assertEqual(settings["nas_root"], "/Volumes/LegacyNAS")
        self.assertEqual(settings["pcloud_dir"], "/Users/test/pCloudLegacy")
        # Verify it migrated into the storage_targets structure
        nas_target = next(t for t in settings["storage_targets"] if t["id"] == "nas")
        pcloud_target = next(t for t in settings["storage_targets"] if t["id"] == "pcloud")
        self.assertEqual(nas_target["root_path"], "/Volumes/LegacyNAS")
        self.assertEqual(pcloud_target["root_path"], "/Users/test/pCloudLegacy")

    def test_concurrency_locks_rmw(self):
        """Simulates parallel settings modifications via update_settings (RMW transaction)."""
        settings = self.persistence.load_settings()
        settings["counter"] = 0
        self.persistence.save_settings(settings)
        self.persistence._cached_settings = None
        num_threads = 10
        increments_per_thread = 20
        def worker():
            for _ in range(increments_per_thread):
                def mutate(data):
                    data["counter"] = data.get("counter", 0) + 1
                self.persistence.update_settings(mutate)
                time.sleep(0.01)
        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        final_settings = self.persistence.load_settings()
        self.assertEqual(final_settings["counter"], num_threads * increments_per_thread)

    def test_active_to_enabled_migration(self):
        """Verifies migration of 'active' key to 'enabled' and DEFAULT values."""
        # Create a raw settings file with active: true/false in storage_targets
        raw_settings = {
            "storage_targets": [
                {
                    "id": "nas",
                    "name": "NAS",
                    "type": "nas",
                    "root_path": "/test/nas",
                    "active": True
                },
                {
                    "id": "pcloud",
                    "name": "Cloud",
                    "type": "pcloud",
                    "root_path": "/test/pcloud",
                    "active": False
                }
            ]
        }
        with open(self.settings_file, "w", encoding="utf-8") as f:
            json.dump(raw_settings, f)
        
        # Force fresh load
        self.persistence._cached_settings = None
        settings = self.persistence.load_settings()
        
        # Verify that 'active' is removed and replaced by 'enabled'
        nas_target = next(t for t in settings["storage_targets"] if t["id"] == "nas")
        pcloud_target = next(t for t in settings["storage_targets"] if t["id"] == "pcloud")
        
        self.assertNotIn("active", nas_target)
        self.assertNotIn("active", pcloud_target)
        self.assertEqual(nas_target.get("enabled"), True)
        self.assertEqual(pcloud_target.get("enabled"), False)

if __name__ == "__main__":
    unittest.main()
