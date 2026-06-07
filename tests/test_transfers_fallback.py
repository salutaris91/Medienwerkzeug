import os
import unittest
import tempfile
import shutil
from unittest.mock import patch

from gui.core.transfers import run_rsync_with_progress, run_copy_fallback

class TestTransfersFallback(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.src_dir = os.path.join(self.temp_dir.name, "src")
        self.dst_dir = os.path.join(self.temp_dir.name, "dst")
        os.makedirs(self.src_dir, exist_ok=True)
        os.makedirs(self.dst_dir, exist_ok=True)
        
        # Erstelle ein paar Testdateien in src
        self.file1 = os.path.join(self.src_dir, "file1.txt")
        with open(self.file1, "w") as f:
            f.write("Inhalt von Datei 1")
            
        self.nested_dir = os.path.join(self.src_dir, "subdir")
        os.makedirs(self.nested_dir, exist_ok=True)
        self.file2 = os.path.join(self.nested_dir, "file2.txt")
        with open(self.file2, "w") as f:
            f.write("Inhalt von Datei 2")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_run_copy_fallback_file(self):
        """Kopieren einer einzelnen Datei mit run_copy_fallback."""
        target_file = os.path.join(self.dst_dir, "copied_file.txt")
        progress_calls = []
        
        def progress_cb(percent, msg):
            progress_calls.append((percent, msg))
            
        success = run_copy_fallback(self.file1, target_file, task_id=progress_cb)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(target_file))
        with open(target_file, "r") as f:
            self.assertEqual(f.read(), "Inhalt von Datei 1")
            
        # Prüfen, ob Fortschrittsmeldung aufgerufen wurde (mindestens einmal mit 100%)
        self.assertTrue(len(progress_calls) > 0)
        self.assertEqual(progress_calls[-1][0], 100)

    def test_run_copy_fallback_directory_contents(self):
        """Kopieren des Inhalts eines Ordners mit run_copy_fallback (keine Verschachtelung)."""
        target_sub = os.path.join(self.dst_dir, "target_sub")
        
        success = run_copy_fallback(self.src_dir, target_sub)
        self.assertTrue(success)
        
        # Verifizieren, dass die Dateien direkt im Zielordner liegen (rsync-Semantik)
        self.assertTrue(os.path.exists(os.path.join(target_sub, "file1.txt")))
        self.assertTrue(os.path.exists(os.path.join(target_sub, "subdir", "file2.txt")))
        
        # Sicherstellen, dass kein zusätzlicher "src"-Ordner im Ziel liegt
        self.assertFalse(os.path.exists(os.path.join(target_sub, "src")))

    @patch("subprocess.Popen")
    def test_run_rsync_fallback_trigger(self, mock_popen):
        """run_rsync_with_progress fängt FileNotFoundError ab und nutzt Fallback."""
        # subprocess.Popen wirft FileNotFoundError
        mock_popen.side_effect = FileNotFoundError("[Errno 2] No such file or directory: 'rsync'")
        
        target_sub = os.path.join(self.dst_dir, "target_rsync_fallback")
        
        # Versuche rsync zu nutzen
        success = run_rsync_with_progress(self.src_dir, target_sub)
        self.assertTrue(success)
        
        # Prüfen, ob die Dateien dank Fallback kopiert wurden
        self.assertTrue(os.path.exists(os.path.join(target_sub, "file1.txt")))
        self.assertTrue(os.path.exists(os.path.join(target_sub, "subdir", "file2.txt")))
        
        # Popen wurde versucht aufzurufen
        self.assertTrue(mock_popen.call_count >= 1)

if __name__ == "__main__":
    unittest.main()
