import os
import unittest
import tempfile
import json
import shutil
import sys

class TestMigration(unittest.TestCase):
    def setUp(self):
        # Wir erstellen ein temporäres Verzeichnis als simuliertes APP_ROOT
        self.temp_app_root = tempfile.TemporaryDirectory()
        self.app_root = self.temp_app_root.name

        # Wir mocken APP_ROOT in persistence
        import gui.core.persistence as persistence
        self.persistence = persistence
        self.original_app_root = persistence.APP_ROOT
        persistence.APP_ROOT = self.app_root
        
        # Reset local cache and migration states
        self.persistence._cached_settings = None
        self.persistence._migration_done = False

    def tearDown(self):
        # Mock zurücksetzen
        self.persistence.APP_ROOT = self.original_app_root
        self.temp_app_root.cleanup()
        
        # Env-Vars aufräumen
        os.environ.pop("MW_SETTINGS_FILE", None)
        os.environ.pop("MW_JOBS_STATE_FILE", None)
        os.environ.pop("MW_ENV_FILE", None)
        os.environ.pop("MW_DATA_DIR", None)
        os.environ.pop("MW_ACTION_LOG_FILE", None)

    def test_migrate_legacy_data_copies_files(self):
        """Prüft, ob migrate_legacy_data() Altdaten kopiert (nicht löscht) und neue anlegt."""
        # 1. Altdaten-Verzeichnisse erstellen
        legacy_gui_dir = os.path.join(self.app_root, "gui")
        legacy_data_dir = os.path.join(legacy_gui_dir, "data")
        os.makedirs(legacy_data_dir, exist_ok=True)

        # 2. Alte Test-Dateien anlegen
        old_settings_content = {"version": 1, "inbox_dir": "/old/inbox"}
        old_jobs_content = {"jobs": []}
        old_env_content = "TVDB_API_KEY=12345\n"
        old_log_content = "some log line\n"

        with open(os.path.join(legacy_gui_dir, "settings.json"), "w", encoding="utf-8") as f:
            json.dump(old_settings_content, f)
        with open(os.path.join(legacy_gui_dir, "jobs_state.json"), "w", encoding="utf-8") as f:
            json.dump(old_jobs_content, f)
        with open(os.path.join(legacy_gui_dir, ".env"), "w", encoding="utf-8") as f:
            f.write(old_env_content)
        with open(os.path.join(legacy_data_dir, "action_log.jsonl"), "w", encoding="utf-8") as f:
            f.write(old_log_content)
            
        # Alte Caches anlegen
        with open(os.path.join(legacy_data_dir, "health_scan_cache.json"), "w", encoding="utf-8") as f:
            json.dump({"cache": "data"}, f)
            
        # Profile anlegen
        legacy_profiles_dir = os.path.join(legacy_data_dir, "profiles")
        os.makedirs(legacy_profiles_dir, exist_ok=True)
        with open(os.path.join(legacy_profiles_dir, "test_profile.json"), "w", encoding="utf-8") as f:
            json.dump({"profile_name": "test"}, f)

        # Quarantäne anlegen
        legacy_quarantine_dir = os.path.join(legacy_data_dir, "quarantine")
        os.makedirs(legacy_quarantine_dir, exist_ok=True)
        with open(os.path.join(legacy_quarantine_dir, "quarantine_item.txt"), "w", encoding="utf-8") as f:
            f.write("deleted movie")

        # 3. Migration ausführen
        self.persistence.migrate_legacy_data()

        # 4. Verifizieren, dass die Daten am neuen Ort liegen
        new_settings_path = os.path.join(self.app_root, "data", "settings.json")
        new_jobs_path = os.path.join(self.app_root, "data", "jobs_state.json")
        new_env_path = os.path.join(self.app_root, ".env")
        new_log_path = os.path.join(self.app_root, "data", "action_log.jsonl")
        new_cache_path = os.path.join(self.app_root, "data", "health_scan_cache.json")
        new_profiles_path = os.path.join(self.app_root, "data", "profiles", "test_profile.json")
        new_quarantine_path = os.path.join(self.app_root, "data", "quarantine", "quarantine_item.txt")

        self.assertTrue(os.path.exists(new_settings_path))
        self.assertTrue(os.path.exists(new_jobs_path))
        self.assertTrue(os.path.exists(new_env_path))
        self.assertTrue(os.path.exists(new_log_path))
        self.assertTrue(os.path.exists(new_cache_path))
        self.assertTrue(os.path.exists(new_profiles_path))
        self.assertTrue(os.path.exists(new_quarantine_path))

        # Verifizieren, dass Inhalte identisch sind
        with open(new_settings_path, "r", encoding="utf-8") as f:
            self.assertEqual(json.load(f)["inbox_dir"], "/old/inbox")
        with open(new_env_path, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), old_env_content)
        with open(new_quarantine_path, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "deleted movie")

        # Verifizieren, dass alte Dateien NICHT gelöscht wurden
        self.assertTrue(os.path.exists(os.path.join(legacy_gui_dir, "settings.json")))
        self.assertTrue(os.path.exists(os.path.join(legacy_gui_dir, "jobs_state.json")))
        self.assertTrue(os.path.exists(os.path.join(legacy_gui_dir, ".env")))
        self.assertTrue(os.path.exists(os.path.join(legacy_data_dir, "action_log.jsonl")))

    def test_migrate_legacy_data_respects_env_overrides(self):
        """Prüft, ob migrate_legacy_data() übersprungen wird, wenn Env-Overrides vorhanden sind."""
        legacy_gui_dir = os.path.join(self.app_root, "gui")
        os.makedirs(legacy_gui_dir, exist_ok=True)
        
        # Alte Test-Settings anlegen
        with open(os.path.join(legacy_gui_dir, "settings.json"), "w", encoding="utf-8") as f:
            json.dump({"version": 1}, f)

        # Env-Override setzen
        custom_settings_path = os.path.join(self.app_root, "custom_settings.json")
        os.environ["MW_SETTINGS_FILE"] = custom_settings_path

        # Migration ausführen
        self.persistence.migrate_legacy_data()

        # Verifizieren, dass keine Migration nach data/settings.json stattgefunden hat
        default_new_settings_path = os.path.join(self.app_root, "data", "settings.json")
        self.assertFalse(os.path.exists(default_new_settings_path))
        self.assertFalse(os.path.exists(custom_settings_path))

    def test_migration_not_triggered_on_path_getter_but_on_io(self):
        """Prüft, ob Pfad-Getter keine Migration auslösen, I/O-Funktionen wie load_settings aber schon."""
        self.persistence._migration_done = False
        
        legacy_gui_dir = os.path.join(self.app_root, "gui")
        os.makedirs(legacy_gui_dir, exist_ok=True)
        with open(os.path.join(legacy_gui_dir, "settings.json"), "w", encoding="utf-8") as f:
            json.dump({"version": 1}, f)
            
        new_settings_path = os.path.join(self.app_root, "data", "settings.json")
        self.assertFalse(os.path.exists(new_settings_path))
        
        # 1. Aufrufen des Pfad-Getters darf KEINE Migration auslösen!
        path = self.persistence.get_settings_file_path()
        self.assertFalse(os.path.exists(new_settings_path))
        
        # 2. Aufrufen einer I/O-Funktion (load_settings) MUSS die Migration triggern!
        self.persistence.load_settings()
        self.assertTrue(os.path.exists(new_settings_path))

    def test_jokes_fallback(self):
        """Prüft, ob get_random_joke auf die Ressource zurückgreift, wenn DATA_DIR leer ist."""
        # DATA_DIR auf leeres temporäres Verzeichnis setzen
        temp_data_dir = tempfile.TemporaryDirectory()
        os.environ["MW_DATA_DIR"] = temp_data_dir.name
        
        from gui.workers.youtube_worker import get_random_joke
        
        # Witz sollte aus der getrackten Resource-Datei geladen werden
        joke = get_random_joke()
        self.assertIsNotNone(joke)
        self.assertTrue(len(joke) > 0)
        
        temp_data_dir.cleanup()

    def test_ensure_env_example_relocation(self):
        """Prüft, ob ensure_env_example() die .env.example im Root anlegt."""
        self.persistence.ensure_env_example()
        
        new_example_path = os.path.join(self.app_root, ".env.example")
        self.assertTrue(os.path.exists(new_example_path))
        with open(new_example_path, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("TMDB_API_KEY", content)
            self.assertIn("TVDB_API_KEY", content)

if __name__ == "__main__":
    unittest.main()
