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

def test_trash_guard_and_quarantine(tmp_path):
    import os
    import pytest
    import gui.core.utils as utils
    from gui.core.trash import send_to_trash, TrashError
    
    # 1. Setup mock folders
    nas_dir = tmp_path / "nas"
    nas_dir.mkdir()
    inbox_dir = tmp_path / "inbox"
    inbox_dir.mkdir()
    
    utils._MOCK_SETTINGS = {
        "nas_root": str(nas_dir),
        "inbox_dir": str(inbox_dir),
        "outbox_dir": str(tmp_path / "outbox")
    }
    
    # Create files
    tvshow_nfo = nas_dir / "tvshow.nfo"
    tvshow_nfo.write_text("<tvshow></tvshow>", encoding="utf-8")
    
    season_nfo = nas_dir / "season.nfo"
    season_nfo.write_text("<season></season>", encoding="utf-8")
    
    regular_file = nas_dir / "S01E01.mp4"
    regular_file.write_text("video content", encoding="utf-8")
    
    # Enable docker runtime to test quarantine
    old_runtime = os.environ.get("MW_RUNTIME")
    os.environ["MW_RUNTIME"] = "docker"
    
    from unittest.mock import patch, MagicMock
    
    orig_os_stat = os.stat
    nas_dir_str = os.path.realpath(str(nas_dir))
    def stat_side_effect(path):
        r = orig_os_stat(path)
        path_str = os.path.abspath(str(path))
        new_dev = 123 if path_str.startswith(nas_dir_str) else 456
        # Construct real os.stat_result tuple
        stat_tuple = (
            r.st_mode,
            r.st_ino,
            new_dev,
            r.st_nlink,
            r.st_uid,
            r.st_gid,
            r.st_size,
            r.st_atime,
            r.st_mtime,
            r.st_ctime
        )
        return os.stat_result(stat_tuple)
        
    try:
        with patch("gui.core.trash.os.stat", side_effect=stat_side_effect):
            # 2. Test block for tvshow.nfo and season.nfo with force=False
            with pytest.raises(TrashError, match="Löschen von Metadaten-Datei.*blockiert"):
                send_to_trash(str(tvshow_nfo), force=False)
                
            with pytest.raises(TrashError, match="Löschen von Metadaten-Datei.*blockiert"):
                send_to_trash(str(season_nfo), force=False)
                
            # Verify they were not deleted
            assert tvshow_nfo.exists()
            assert season_nfo.exists()
            
            # 3. Test that regular files can be trashed without force=True
            assert send_to_trash(str(regular_file), force=False)
            assert not regular_file.exists()
            
            # Verify the quarantined structure
            trash_dir = nas_dir / ".medienwerkzeug-trash"
            assert trash_dir.exists()
            
            # Under trash_dir, there should be a timestamp directory, then parent directory (nas), then the file
            timestamp_folders = [f for f in os.listdir(trash_dir) if not f.startswith(".")]
            assert len(timestamp_folders) == 1
            ts_folder = timestamp_folders[0]
            
            parent_folder = trash_dir / ts_folder / "nas"
            assert parent_folder.exists()
            assert (parent_folder / "S01E01.mp4").exists()
            
            # 4. Test that tvshow.nfo can be trashed with force=True
            assert send_to_trash(str(tvshow_nfo), force=True)
            assert not tvshow_nfo.exists()
    finally:
        # Clean up mock settings and env
        utils._MOCK_SETTINGS = None
        if old_runtime is not None:
            os.environ["MW_RUNTIME"] = old_runtime
        else:
            os.environ.pop("MW_RUNTIME", None)



