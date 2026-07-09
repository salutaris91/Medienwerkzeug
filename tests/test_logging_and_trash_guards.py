import os
import shutil
import threading
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

def test_nfo_helper_hardening(tmp_path):
    nfo_file = tmp_path / "tvshow.nfo"
    nfo_file.write_text("<tvshow></tvshow>", encoding="utf-8")
    
    # 1. Test tag name validation
    with pytest.raises(ValueError, match="Ungültiger XML-Tag-Name"):
        update_or_insert_nfo_element(str(nfo_file), "invalid tag", "val")
        
    with pytest.raises(ValueError, match="Ungültiger XML-Tag-Name"):
        update_or_insert_nfo_element(str(nfo_file), "mpaa/>", "val")

    # 2. Test self-closing tags
    original_xml = """<?xml version="1.0" encoding="UTF-8"?>
<tvshow>
  <title>Title</title>
  <mpaa />
</tvshow>
"""
    nfo_file.write_text(original_xml, encoding="utf-8")
    update_or_insert_nfo_element(str(nfo_file), "mpaa", "FSK 12")
    
    updated_content = nfo_file.read_text(encoding="utf-8")
    assert "<mpaa>FSK 12</mpaa>" in updated_content
    assert "<title>Title</title>" in updated_content

    # Self-closing tag without space
    original_xml_2 = """<?xml version="1.0" encoding="UTF-8"?>
<tvshow>
  <mpaa/>
</tvshow>
"""
    nfo_file.write_text(original_xml_2, encoding="utf-8")
    update_or_insert_nfo_element(str(nfo_file), "mpaa", "FSK 16")
    updated_content_2 = nfo_file.read_text(encoding="utf-8")
    assert "<mpaa>FSK 16</mpaa>" in updated_content_2

    # 3. Test strict encoding (invalid bytes)
    with open(str(nfo_file), "wb") as f:
        f.write(b"<tvshow>\xff\xfe\xfd</tvshow>")
        
    with pytest.raises(IOError, match="NFO lesefehler"):
        update_or_insert_nfo_element(str(nfo_file), "title", "val")


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
    def stat_side_effect(path, *args, **kwargs):
        r = orig_os_stat(path, *args, **kwargs)
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
        with patch("gui.core.trash.os.stat", side_effect=stat_side_effect), \
             patch("gui.core.trash.time.strftime", return_value="2026-06-21_22-00-00"):
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
            
            parent_folder = trash_dir / "2026-06-21_22-00-00" / "nas"
            assert parent_folder.exists()
            assert (parent_folder / "S01E01.mp4").exists()
            
            # Test collision avoidance (same file trashed again in same second)
            regular_file_2 = nas_dir / "S01E01.mp4"
            regular_file_2.write_text("another video", encoding="utf-8")
            assert send_to_trash(str(regular_file_2), force=False)
            assert (parent_folder / "S01E01_1.mp4").exists()
            
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


def test_nfo_helper_read_metadata_and_mw_data(tmp_path):
    from gui.core.nfo_helper import read_nfo_metadata, update_nfo_mw_data
    nfo_file = tmp_path / "tvshow.nfo"
    
    # 1. Test empty / missing NFO
    assert read_nfo_metadata(str(nfo_file)) == {}
    
    # 2. Test reading valid XML NFO
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<tvshow>
  <title>Serengeti</title>
  <year>2020</year>
  <plot>Amazing documentary about nature.</plot>
  <mw_provider>ytdlp</mw_provider>
  <mw_showid>https://www.youtube.com/playlist?list=PL123</mw_showid>
  <mw_data>
    <provider>ytdlp</provider>
    <show_id>https://www.youtube.com/playlist?list=PL123</show_id>
    <source_url>https://www.youtube.com/playlist?list=PL123</source_url>
    <resolved_topic>Serengeti</resolved_topic>
    <last_sync>2026-06-22T07:00:00</last_sync>
  </mw_data>
</tvshow>
"""
    nfo_file.write_text(xml_content, encoding="utf-8")
    meta = read_nfo_metadata(str(nfo_file))
    
    assert meta["title"] == "Serengeti"
    assert meta["year"] == "2020"
    assert meta["plot"] == "Amazing documentary about nature."
    assert meta["mw_provider"] == "ytdlp"
    assert meta["mw_showid"] == "https://www.youtube.com/playlist?list=PL123"
    assert meta["mw_data"]["provider"] == "ytdlp"
    assert meta["mw_data"]["source_url"] == "https://www.youtube.com/playlist?list=PL123"
    assert meta["mw_data"]["resolved_topic"] == "Serengeti"
    assert meta["mw_data"]["last_sync"] == "2026-06-22T07:00:00"

    # 3. Test reading invalid XML (Regex Fallback)
    invalid_xml = """<tvshow>
  <title>Invalid XML Show
  <mw_provider>mediathek</mw_provider>
  <mw_showid>url_mediathek:Arte</mw_showid>
  <mw_data>
    <provider>mediathek</provider>
    <source_url>http://arte.tv/show</source_url>
    <resolved_topic>Arte</resolved_topic>
  </mw_data>
</tvshow>"""
    nfo_file.write_text(invalid_xml, encoding="utf-8")
    meta2 = read_nfo_metadata(str(nfo_file))
    assert meta2["mw_provider"] == "mediathek"
    assert meta2["mw_showid"] == "url_mediathek:Arte"
    assert meta2["mw_data"]["source_url"] == "http://arte.tv/show"
    assert meta2["mw_data"]["resolved_topic"] == "Arte"


def test_nfo_helper_update_mw_data_strict(tmp_path):
    from gui.core.nfo_helper import update_nfo_mw_data, read_nfo_metadata
    nfo_file = tmp_path / "tvshow.nfo"
    
    # 1. Create a valid tvshow.nfo
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<tvshow>
  <title>Serengeti</title>
  <plot>Amazing nature.</plot>
  <mw_provider>mediathek</mw_provider>
  <mw_showid>url_mediathek:Serengeti</mw_showid>
</tvshow>
"""
    nfo_file.write_text(xml_content, encoding="utf-8")
    
    # 2. Test successful update of mw_data
    update_nfo_mw_data(
        str(nfo_file), 
        provider="mediathek", 
        show_id="url_mediathek:Serengeti", 
        source_url="https://www.arte.tv/serengeti", 
        resolved_topic="Serengeti"
    )
    
    meta = read_nfo_metadata(str(nfo_file))
    assert meta["mw_data"]["provider"] == "mediathek"
    assert meta["mw_data"]["source_url"] == "https://www.arte.tv/serengeti"
    assert meta["mw_data"]["resolved_topic"] == "Serengeti"
    assert meta["mw_data"]["last_sync"] is not None
    # Verify title & plot did not change
    assert meta["title"] == "Serengeti"
    assert meta["plot"] == "Amazing nature."

    # 3. Test strict validation: writing to invalid XML should raise Exception
    nfo_file.write_text("<tvshow><title>Broken XML", encoding="utf-8")
    with pytest.raises(ValueError, match="Original-XML fehlerhaft"):
        update_nfo_mw_data(str(nfo_file), "mediathek", "url_mediathek:Serengeti")

    # 4. Test manual provider filtering: ignore if no useful fields are there
    valid_xml = "<tvshow><title>Manual Show</title><mw_provider>manual</mw_provider><mw_showid>JSON_DUMMY</mw_showid></tvshow>"
    nfo_file.write_text(valid_xml, encoding="utf-8")
    
    # JSON-like show_id and no source_url/resolved_topic -> should skip writing mw_data
    update_nfo_mw_data(str(nfo_file), "manual", '{"title": "JSON Show"}', source_url=None, resolved_topic=None)
    meta_manual = read_nfo_metadata(str(nfo_file))
    assert "mw_data" not in meta_manual or not meta_manual["mw_data"]


def test_generate_tvshow_nfo_with_url_id(tmp_path):
    from gui.mw_metadata import generate_tvshow_nfo
    from gui.core.nfo_helper import read_nfo_metadata
    
    # 1. Test ytdlp with URL containing & and other query params
    url_id = "https://www.youtube.com/playlist?list=PL123&index=5&foo=bar"
    
    from unittest.mock import patch
    with patch("gui.mw_metadata.fetch_ytdlp_url_metadata", return_value=[{"playlist_title": "Nature Docs"}]):
        res = generate_tvshow_nfo("ytdlp", url_id, str(tmp_path))
        
    assert res["nfo"] is True
    nfo_file = tmp_path / "tvshow.nfo"
    assert nfo_file.exists()
    
    meta = read_nfo_metadata(str(nfo_file))
    assert meta["mw_provider"] == "ytdlp"
    assert meta["mw_showid"] == url_id
    assert meta["mw_data"]["source_url"] == url_id

    # 2. Test mediathek with URL ID containing &
    mediathek_url_id = "https://www.ardmediathek.de/sendung/serengeti?id=123&test=1"
    
    os.remove(str(nfo_file))
    res2 = generate_tvshow_nfo("mediathek", mediathek_url_id, str(tmp_path))
    assert res2["nfo"] is True
    assert nfo_file.exists()
    
    meta2 = read_nfo_metadata(str(nfo_file))
    assert meta2["mw_provider"] == "mediathek"
    assert meta2["mw_showid"] == mediathek_url_id
    assert meta2["mw_data"]["source_url"] == mediathek_url_id


def test_find_existing_series_folder_by_id_only_in_mw_data(tmp_path):
    from gui.api.search_api import find_existing_series_folder_by_id
    
    show_dir = tmp_path / "Serengeti"
    show_dir.mkdir()
    nfo_file = show_dir / "tvshow.nfo"
    
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<tvshow>
  <title>Serengeti</title>
  <mw_data>
    <provider>ytdlp</provider>
    <show_id>https://www.youtube.com/playlist?list=PL123</show_id>
    <source_url>https://www.youtube.com/playlist?list=PL123</source_url>
  </mw_data>
</tvshow>
"""
    nfo_file.write_text(xml_content, encoding="utf-8")
    
    match = find_existing_series_folder_by_id(
        str(tmp_path), 
        provider="ytdlp", 
        show_id="https://www.youtube.com/playlist?list=PL123"
    )
    assert match == "Serengeti"


def test_transfer_nfo_mw_data_sync_end_to_end(tmp_path):
    from gui.workers.processor import _handle_transfer_task
    from gui.core.nfo_helper import read_nfo_metadata
    
    outbox_dir = tmp_path / "outbox"
    outbox_dir.mkdir()
    outbox_nfo = outbox_dir / "tvshow.nfo"
    
    outbox_xml = """<?xml version="1.0" encoding="UTF-8"?>
<tvshow>
  <title>Serengeti</title>
  <mw_provider>ytdlp</mw_provider>
  <mw_showid>https://www.youtube.com/playlist?list=PL123</mw_showid>
  <mw_data>
    <provider>ytdlp</provider>
    <show_id>https://www.youtube.com/playlist?list=PL123</show_id>
    <source_url>https://www.youtube.com/playlist?list=PL123</source_url>
    <resolved_topic>Serengeti</resolved_topic>
    <last_sync>2026-06-20T12:00:00</last_sync>
  </mw_data>
</tvshow>
"""
    outbox_nfo.write_text(outbox_xml, encoding="utf-8")
    
    nas_dir = tmp_path / "nas"
    nas_dir.mkdir()
    nas_nfo = nas_dir / "tvshow.nfo"
    
    nas_xml = """<?xml version="1.0" encoding="UTF-8"?>
<tvshow>
  <title>Curated Serengeti Title</title>
  <plot>Curated manual plot that must be preserved.</plot>
  <mw_provider>ytdlp</mw_provider>
  <mw_showid>https://www.youtube.com/playlist?list=PL123</mw_showid>
</tvshow>
"""
    nas_nfo.write_text(nas_xml, encoding="utf-8")
    
    task = {
        "type": "show_metadata_nas_transfer",
        "dest_show_dir_outbox": str(outbox_dir),
        "dest_show_dir_nas": str(nas_dir),
        "provider": "ytdlp",
        "show_id": "https://www.youtube.com/playlist?list=PL123",
        "source_url": "https://www.youtube.com/playlist?list=PL123",
        "resolved_topic": "Serengeti"
    }
    
    from unittest.mock import MagicMock
    log_mock = MagicMock()
    
    _handle_transfer_task(
        task=task,
        task_id="test_task",
        target_progresses={},
        target_speeds={},
        progress_lock=None,
        N=1,
        log_message=log_mock,
        update_global_job_progress=MagicMock()
    )
    
    assert nas_nfo.exists()
    meta = read_nfo_metadata(str(nas_nfo))
    
    assert meta["title"] == "Curated Serengeti Title"
    assert meta["plot"] == "Curated manual plot that must be preserved."
    
    assert meta["mw_data"]["provider"] == "ytdlp"
    assert meta["mw_data"]["source_url"] == "https://www.youtube.com/playlist?list=PL123"
    assert meta["mw_data"]["resolved_topic"] == "Serengeti"
    assert meta["mw_data"]["last_sync"] is not None


def test_movie_nas_transfer_marks_pipeline_step_done(tmp_path, monkeypatch):
    import gui.core.jobs as jobs
    import gui.workers.processor as processor
    from gui.workers.processor import _handle_transfer_task
    from unittest.mock import MagicMock

    job_id = "test-movie-nas-done"
    monkeypatch.setattr(jobs, "save_jobs_to_disk", lambda: True)
    monkeypatch.setattr(processor, "run_rsync_with_progress", lambda *args, **kwargs: True)

    with jobs.active_jobs_lock:
        jobs.active_jobs[job_id] = {
            "id": job_id,
            "status": "running",
            "progress": 0,
            "message": "Verarbeitung läuft...",
            "pipeline": {
                "nas": {"status": "pending", "progress": 0},
                "pcloud": {"status": "pending", "progress": 0}
            }
        }

    outbox_dir = tmp_path / "outbox" / "Movie (2026)"
    outbox_dir.mkdir(parents=True)
    target_dir = tmp_path / "nas" / "Movie (2026)"

    _handle_transfer_task(
        task={
            "type": "movie_nas_transfer",
            "target_id": "nas",
            "file_idx": 0,
            "dest_movie_dir_outbox": str(outbox_dir),
            "dest_movie_dir_nas": str(target_dir),
            "final_filename": "Movie (2026).mkv"
        },
        task_id=job_id,
        target_progresses={"nas": [0]},
        target_speeds={"nas": [""]},
        progress_lock=threading.RLock(),
        N=1,
        log_message=MagicMock(),
        update_global_job_progress=MagicMock()
    )

    job = jobs.get_job(job_id)
    assert job["pipeline"]["nas"]["status"] == "done"
    assert job["pipeline"]["nas"]["progress"] == 100
    assert job["pipeline"]["nas"]["message"] == "Auf NAS gespeichert"
    assert job["pipeline"]["pcloud"]["status"] == "pending"

    with jobs.active_jobs_lock:
        jobs.active_jobs.pop(job_id, None)


def test_movie_cloud_transfer_is_visible_before_progress_callback(tmp_path, monkeypatch):
    import gui.core.jobs as jobs
    import gui.workers.processor as processor
    from gui.workers.processor import _handle_transfer_task
    from unittest.mock import MagicMock

    job_id = "test-movie-cloud-start"
    observed = {}
    monkeypatch.setattr(jobs, "save_jobs_to_disk", lambda: True)
    monkeypatch.setattr(
        processor,
        "load_settings",
        lambda: {
            "storage_targets": [
                {"id": "pcloud", "name": "pCloud", "type": "cloud", "enabled": True}
            ]
        }
    )

    def fake_copy_to_cloud_target(*args, **kwargs):
        job = jobs.get_job(job_id)
        observed["during_upload"] = job["pipeline"]["pcloud"].copy()
        observed["job_message"] = job["message"]
        return True

    monkeypatch.setattr(processor, "copy_to_cloud_target", fake_copy_to_cloud_target)

    with jobs.active_jobs_lock:
        jobs.active_jobs[job_id] = {
            "id": job_id,
            "status": "running",
            "progress": 0,
            "message": "Verarbeitung läuft...",
            "pipeline": {
                "nas": {"status": "done", "progress": 100},
                "pcloud": {"status": "pending", "progress": 0}
            }
        }

    outbox_dir = tmp_path / "outbox" / "Movie (2026)"
    outbox_dir.mkdir(parents=True)

    _handle_transfer_task(
        task={
            "type": "movie_cloud_transfer",
            "target_id": "pcloud",
            "file_idx": 0,
            "dest_movie_dir_outbox": str(outbox_dir),
            "dest_movies": "pcloud:Movies",
            "clean_movie_name": "Movie (2026)"
        },
        task_id=job_id,
        target_progresses={"pcloud": 0},
        target_speeds={"pcloud": ""},
        progress_lock=threading.RLock(),
        N=1,
        log_message=MagicMock(),
        update_global_job_progress=MagicMock()
    )

    assert observed["during_upload"]["status"] == "running"
    assert observed["during_upload"]["progress"] == 0
    assert observed["during_upload"]["message"] == "Upload nach pCloud gestartet..."
    assert observed["job_message"] == "Upload nach pCloud gestartet..."

    job = jobs.get_job(job_id)
    assert job["pipeline"]["pcloud"]["status"] == "done"
    assert job["pipeline"]["pcloud"]["progress"] == 100
    assert job["pipeline"]["pcloud"]["message"] == "Upload nach pCloud abgeschlossen"

    with jobs.active_jobs_lock:
        jobs.active_jobs.pop(job_id, None)
