import os
import shutil
import pytest
import xml.etree.ElementTree as ET
from gui.core.nfo_helper import update_or_insert_nfo_element

def test_nfo_helper_update_and_insert(tmp_path):
    # 1. Create a dummy tvshow.nfo
    nfo_file = tmp_path / "tvshow.nfo"
    original_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<tvshow>
  <title>Old Title</title>
  <plot>Old Plot</plot>
</tvshow>
"""
    nfo_file.write_text(original_xml, encoding="utf-8")
    
    # 2. Test updating existing element
    update_or_insert_nfo_element(str(nfo_file), "title", "New Title")
    
    # Check that it updated the file and created a backup
    updated_content = nfo_file.read_text(encoding="utf-8")
    assert "<title>New Title</title>" in updated_content
    assert "<plot>Old Plot</plot>" in updated_content
    
    # Verify backup exists
    backups = [f for f in os.listdir(tmp_path) if f.startswith("tvshow.nfo.bak.")]
    assert len(backups) == 1
    
    # 3. Test inserting new element
    update_or_insert_nfo_element(str(nfo_file), "mpaa", "FSK 12")
    updated_content = nfo_file.read_text(encoding="utf-8")
    assert "<mpaa>FSK 12</mpaa>" in updated_content
    
    # 4. Test inserting XML block element
    mw_data_xml = "<provider>mediathek</provider><showid>12345</showid>"
    update_or_insert_nfo_element(str(nfo_file), "mw_data", mw_data_xml, is_xml_block=True)
    updated_content = nfo_file.read_text(encoding="utf-8")
    assert "<mw_data><provider>mediathek</provider><showid>12345</showid></mw_data>" in updated_content

def test_nfo_helper_invalid_xml(tmp_path):
    nfo_file = tmp_path / "tvshow.nfo"
    # Invalid XML
    nfo_file.write_text("<tvshow><title>Unclosed Tag</tvshow>", encoding="utf-8")
    
    with pytest.raises(ValueError, match="Original-XML fehlerhaft"):
        update_or_insert_nfo_element(str(nfo_file), "title", "New")

def test_nfo_helper_invalid_root(tmp_path):
    nfo_file = tmp_path / "tvshow.nfo"
    # Root tag not allowed
    nfo_file.write_text("<invalid_root><title>Title</title></invalid_root>", encoding="utf-8")
    
    with pytest.raises(ValueError, match="Ungültiges NFO Root-Tag"):
        update_or_insert_nfo_element(str(nfo_file), "title", "New")
