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

def test_job_logging_routing_and_cleanup(tmp_path):
    import gui.core.utils as utils
    from gui.core.helpers import log_message, close_job_log, cleanup_old_job_logs, _job_log_handles
    import threading
    import time
    
    # 1. Setup mock settings
    utils._MOCK_SETTINGS = {"data_dir": str(tmp_path)}
    
    # Ensure starting clean
    from gui.core.helpers import _job_log_lock
    with _job_log_lock:
        _job_log_handles.clear()
    
    # 2. Test logging in a job thread
    def run_job_thread():
        log_message("Message from worker")
        
    t = threading.Thread(target=run_job_thread, name="job-test-task-123")
    t.start()
    t.join()
    
    log_file = tmp_path / "logs" / "job-test-task-123.log"
    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "Message from worker" in content
    
    # 3. Test logging in child threads
    def run_transfer_thread():
        log_message("Message from transfer")
        
    t2 = threading.Thread(target=run_transfer_thread, name="job-test-task-123-transfer")
    t2.start()
    t2.join()
    
    content = log_file.read_text(encoding="utf-8")
    assert "Message from transfer" in content

    def run_reader_thread():
        log_message("Message from reader")
        
    t3 = threading.Thread(target=run_reader_thread, name="job-test-task-123-reader")
    t3.start()
    t3.join()
    
    content = log_file.read_text(encoding="utf-8")
    assert "Message from reader" in content
    
    # Verify the handle is cached
    assert "test-task-123" in _job_log_handles
    
    # 4. Test closing the log
    close_job_log("test-task-123")
    assert "test-task-123" not in _job_log_handles
    
    # 5. Test retention cleanup
    old_log_file = tmp_path / "logs" / "job-old-task.log"
    old_log_file.write_text("Old log message", encoding="utf-8")
    
    # Set back modification time of old_log_file to 15 days ago
    fifteen_days_ago = time.time() - (15 * 86400)
    os.utime(str(old_log_file), (fifteen_days_ago, fifteen_days_ago))
    
    cleanup_old_job_logs(14)
    
    assert not old_log_file.exists()
    assert log_file.exists()
    
    # Reset mock settings
    utils._MOCK_SETTINGS = None

