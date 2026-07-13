import os
import shutil
import tempfile
import unittest
import stat
from unittest.mock import patch

from gui.api.nas_api import write_fsk_to_nfo

class TestNFOWriteBinary(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_t1_preserves_umlauts_and_encoding(self):
        # UTF-8 NFO mit Umlauten und XML-Kommentaren außerhalb mpaa
        nfo_path = os.path.join(self.temp_dir, "test1.nfo")
        original_bytes = (
            b'<?xml version="1.0" encoding="UTF-8"?>\n'
            b'<!-- Ein XML Kommentar -->\n'
            b'<movie>\n'
            b'  <title>M\xc3\xa4nner und B\xc3\xa4ume</title>\n'
            b'  <mpaa>FSK 6</mpaa>\n'
            b'</movie>'
        )
        with open(nfo_path, "wb") as f:
            f.write(original_bytes)

        ok, msg = write_fsk_to_nfo(nfo_path, "FSK 12")
        self.assertTrue(ok)
        self.assertIn("erfolgreich", msg)

        # Kontrollieren, dass Umlaut und Kommentar bytegenau erhalten sind
        with open(nfo_path, "rb") as f:
            written_bytes = f.read()

        expected_bytes = (
            b'<?xml version="1.0" encoding="UTF-8"?>\n'
            b'<!-- Ein XML Kommentar -->\n'
            b'<movie>\n'
            b'  <title>M\xc3\xa4nner und B\xc3\xa4ume</title>\n'
            b'  <mpaa>FSK 12</mpaa>\n'
            b'</movie>'
        )
        self.assertEqual(written_bytes, expected_bytes)

    def test_t2_preserves_mpaa_attributes(self):
        # MPAA Tag mit Attributen
        nfo_path = os.path.join(self.temp_dir, "test2.nfo")
        original_bytes = (
            b'<movie>\n'
            b'  <mpaa default="true" country="de">FSK 6</mpaa>\n'
            b'</movie>'
        )
        with open(nfo_path, "wb") as f:
            f.write(original_bytes)

        ok, msg = write_fsk_to_nfo(nfo_path, "FSK 16")
        self.assertTrue(ok)

        with open(nfo_path, "rb") as f:
            written_bytes = f.read()

        self.assertEqual(
            written_bytes,
            b'<movie>\n'
            b'  <mpaa default="true" country="de">FSK 16</mpaa>\n'
            b'</movie>'
        )

    def test_t3_inserts_before_closing_root_tag(self):
        # Fehlendes mpaa-Tag
        nfo_path = os.path.join(self.temp_dir, "test3.nfo")
        original_bytes = (
            b'<movie>\n'
            b'  <title>Testmovie</title>\n'
            b'</movie>'
        )
        with open(nfo_path, "wb") as f:
            f.write(original_bytes)

        ok, msg = write_fsk_to_nfo(nfo_path, "FSK 18")
        self.assertTrue(ok)

        with open(nfo_path, "rb") as f:
            written_bytes = f.read()

        expected = (
            b'<movie>\n'
            b'  <title>Testmovie</title>\n'
            b'  <mpaa>FSK 18</mpaa>\n'
            b'</movie>'
        )
        self.assertEqual(written_bytes, expected)

    def test_t4_validation_rejections(self):
        # Case A: Ungültiges XML
        nfo_path = os.path.join(self.temp_dir, "test4_invalid.nfo")
        with open(nfo_path, "wb") as f:
            f.write(b'<movie><title>Broken XML')
        ok, msg = write_fsk_to_nfo(nfo_path, "FSK 12")
        self.assertFalse(ok)
        self.assertIn("fehlerhaft", msg)

        # Case B: Mehrere mpaa-Tags
        nfo_path2 = os.path.join(self.temp_dir, "test4_multiple.nfo")
        with open(nfo_path2, "wb") as f:
            f.write(b'<movie><mpaa>FSK 6</mpaa><mpaa>FSK 12</mpaa></movie>')
        ok, msg = write_fsk_to_nfo(nfo_path2, "FSK 16")
        self.assertFalse(ok)
        self.assertIn("Mehrere <mpaa>-Tags", msg)

        # Case C: Falsches Root-Tag
        nfo_path3 = os.path.join(self.temp_dir, "test4_root.nfo")
        with open(nfo_path3, "wb") as f:
            f.write(b'<actors><actor>Dracula</actor></actors>')
        ok, msg = write_fsk_to_nfo(nfo_path3, "FSK 12")
        self.assertFalse(ok)
        self.assertIn("Ung\xc3\xbcltiges NFO Root-Tag", msg)

        # Case D: Namespaces ablehnen
        nfo_path4 = os.path.join(self.temp_dir, "test4_namespace.nfo")
        with open(nfo_path4, "wb") as f:
            f.write(b'<movie xmlns:n="http://example.com"><n:mpaa>FSK 12</n:mpaa></movie>')
        ok, msg = write_fsk_to_nfo(nfo_path4, "FSK 6")
        self.assertFalse(ok)
        self.assertIn("Namespaces", msg)

    def test_t5_backup_creation(self):
        nfo_path = os.path.join(self.temp_dir, "test5.nfo")
        original_bytes = b'<movie><mpaa>FSK 6</mpaa></movie>'
        with open(nfo_path, "wb") as f:
            f.write(original_bytes)

        ok, msg = write_fsk_to_nfo(nfo_path, "FSK 12")
        self.assertTrue(ok)

        # Prüfen, ob eine .bak.-Datei existiert
        files = os.listdir(self.temp_dir)
        bak_files = [f for f in files if f.startswith("test5.nfo.bak.")]
        self.assertEqual(len(bak_files), 1)

        bak_path = os.path.join(self.temp_dir, bak_files[0])
        with open(bak_path, "rb") as f:
            self.assertEqual(f.read(), original_bytes)

    @patch('os.replace')
    def test_t6_atomic_write_leaves_original_on_error(self, mock_replace):
        mock_replace.side_effect = IOError("Simulierter Plattenfehler")

        nfo_path = os.path.join(self.temp_dir, "test6.nfo")
        original_bytes = b'<movie><mpaa>FSK 6</mpaa></movie>'
        with open(nfo_path, "wb") as f:
            f.write(original_bytes)

        ok, msg = write_fsk_to_nfo(nfo_path, "FSK 12")
        self.assertFalse(ok)
        self.assertIn("Fehler beim Speichern", msg)

        # Originaldatei muss unangetastet sein
        with open(nfo_path, "rb") as f:
            self.assertEqual(f.read(), original_bytes)

    def test_t7_preserves_file_permissions(self):
        nfo_path = os.path.join(self.temp_dir, "test7.nfo")
        original_bytes = b'<movie><mpaa>FSK 6</mpaa></movie>'
        with open(nfo_path, "wb") as f:
            f.write(original_bytes)

        # Rechte gezielt auf 0o644 setzen
        os.chmod(nfo_path, 0o644)
        original_mode = stat.S_IMODE(os.stat(nfo_path).st_mode)

        ok, msg = write_fsk_to_nfo(nfo_path, "FSK 12")
        self.assertTrue(ok)

        new_mode = stat.S_IMODE(os.stat(nfo_path).st_mode)
        self.assertEqual(new_mode, original_mode)

    def test_t8_t9_bom_and_post_root_comments(self):
        # BOM + Kommentare nach Root-Tag
        nfo_path = os.path.join(self.temp_dir, "test8.nfo")
        original_bytes = (
            b'\xef\xbb\xbf<?xml version="1.0" encoding="UTF-8"?>\n'
            b'<movie>\n'
            b'  <title>BOM Test</title>\n'
            b'</movie>\n'
            b'<!-- Nachgelagerter Kommentar -->'
        )
        with open(nfo_path, "wb") as f:
            f.write(original_bytes)

        ok, msg = write_fsk_to_nfo(nfo_path, "FSK 16")
        self.assertTrue(ok)

        with open(nfo_path, "rb") as f:
            written_bytes = f.read()

        expected = (
            b'\xef\xbb\xbf<?xml version="1.0" encoding="UTF-8"?>\n'
            b'<movie>\n'
            b'  <title>BOM Test</title>\n'
            b'  <mpaa>FSK 16</mpaa>\n'
            b'</movie>\n'
            b'<!-- Nachgelagerter Kommentar -->'
        )
        self.assertEqual(written_bytes, expected)
