import os
import time
import pytest
import shutil
from unittest.mock import patch, MagicMock
from gui.core.trash import (
    TrashError,
    get_trash_dirs,
    get_trash_stats,
    empty_trash_async,
    _empty_trash_core,
    TRASH_CLEANUP_STATUS
)
from gui.core.utils import get_allowed_roots
from gui.workers.storage_probe import measure_trash_stats_bytes


def test_get_trash_dirs(monkeypatch):
    """Testfall: get_trash_dirs findet alle .medienwerkzeug-trash Verzeichnisse an den Mountpoints"""
    # Mock allowed roots
    mock_roots = ["/mock/inbox", "/mock/outbox"]
    
    # Mock exists und stats
    def mock_exists(path):
        if path in ("/mock/inbox", "/mock/outbox", "/mock/inbox/.medienwerkzeug-trash", "/mock/outbox/.medienwerkzeug-trash"):
            return True
        return False
        
    def mock_stat(path):
        m = MagicMock()
        # inbox is on dev=1, outbox is on dev=2, parent /mock is on dev=0
        if path == "/mock/inbox":
            m.st_dev = 1
        elif path == "/mock/outbox":
            m.st_dev = 2
        else:
            m.st_dev = 0
        return m
        
    with patch("gui.core.trash.get_allowed_roots", return_value=mock_roots), \
         patch("gui.core.trash.os.path.exists", side_effect=mock_exists), \
         patch("gui.core.trash.os.path.isdir", return_value=True), \
         patch("gui.core.trash.os.path.isfile", return_value=False), \
         patch("gui.core.trash.os.stat", side_effect=mock_stat), \
         patch("gui.core.trash.os.path.realpath", side_effect=lambda x: x):
         
        dirs = get_trash_dirs()
        assert len(dirs) == 2
        assert "/mock/inbox/.medienwerkzeug-trash" in dirs
        assert "/mock/outbox/.medienwerkzeug-trash" in dirs


def test_measure_trash_stats_bytes_probe(tmp_path):
    """Testfall: storage_probe trash_stats ermittelt die korrekten Statistik-Daten"""
    trash_dir = tmp_path / ".medienwerkzeug-trash"
    trash_dir.mkdir()
    
    # 1. Normal file
    timestamp_folder = trash_dir / "2026-06-22_12-00-00"
    timestamp_folder.mkdir()
    file_dir = timestamp_folder / "Inbox"
    file_dir.mkdir()
    
    normal_file = file_dir / "movie.mp4"
    normal_file.write_text("Hello World") # 11 bytes
    
    # 2. Symlink file pointing to a target
    target_file = tmp_path / "outside_target.txt"
    target_file.write_text("This is outside")
    symlink_file = file_dir / "symlink_movie.mp4"
    symlink_file.symlink_to(target_file)
    
    # Call probe function
    res = measure_trash_stats_bytes(str(trash_dir))
    
    assert res["bytes"] == 11 # Symlink size must NOT be added
    assert res["count"] == 2 # 1 normal file + 1 symlink


def test_empty_trash_core_retention_and_dry_run(tmp_path):
    """Testfall: _empty_trash_core beachtet die Retention-Dauer und dry_run"""
    trash_dir = tmp_path / "mock-trash"
    trash_dir.mkdir()
    
    # Subdir 1: Old folder (expired, 10 days ago)
    old_folder = trash_dir / "2026-06-12_12-00-00"
    old_folder.mkdir()
    old_file = old_folder / "old.mp4"
    old_file.write_text("old file content")
    
    # Subdir 2: New folder (not expired, created now)
    now_str = time.strftime("%Y-%m-%d_%H-%M-%S")
    new_folder = trash_dir / now_str
    new_folder.mkdir()
    new_file = new_folder / "new.mp4"
    new_file.write_text("new file content")
    
    with patch("gui.core.trash.get_trash_dirs", return_value=[str(trash_dir)]):
        # 1. Dry Run check
        deleted, errors = _empty_trash_core(retention_days=7, dry_run=True)
        assert len(errors) == 0
        assert str(old_file) in deleted
        assert str(old_folder) in deleted
        assert str(new_file) not in deleted
        
        # Files should still exist
        assert old_file.exists()
        
        # 2. Real deletion check
        deleted, errors = _empty_trash_core(retention_days=7, dry_run=False)
        assert len(errors) == 0
        assert str(old_file) in deleted
        
        # Old files must be gone
        assert not old_file.exists()
        assert not old_folder.exists()
        
        # New files must still exist
        assert new_file.exists()
        assert new_folder.exists()


def test_empty_trash_core_symlink_safety(tmp_path):
    """Testfall: Ein Symlink im Trash darf beim Löschen nicht sein Ziel mitreißen"""
    trash_dir = tmp_path / "mock-trash"
    trash_dir.mkdir()
    
    # Target outside trash
    outside_dir = tmp_path / "outside_dir"
    outside_dir.mkdir()
    outside_file = outside_dir / "important_media.mp4"
    outside_file.write_text("DO NOT DELETE THIS TARGET")
    
    # Trash folder
    old_folder = trash_dir / "2026-06-12_12-00-00"
    old_folder.mkdir()
    
    # Symlink file pointing to outside file
    symlink_file = old_folder / "symlink_file.mp4"
    symlink_file.symlink_to(outside_file)
    
    # Symlink directory pointing to outside directory
    symlink_dir = old_folder / "symlink_dir"
    symlink_dir.symlink_to(outside_dir)
    
    with patch("gui.core.trash.get_trash_dirs", return_value=[str(trash_dir)]):
        deleted, errors = _empty_trash_core(retention_days=7, dry_run=False)
        
        assert len(errors) == 0
        # Symlink file and dir in trash must be unlinked
        assert not symlink_file.exists()
        assert not symlink_dir.exists()
        assert not old_folder.exists()
        
        # TARGETS OUTSIDE MUST STILL EXIST!
        assert outside_file.exists()
        assert outside_dir.exists()


def test_empty_trash_core_boundary_check(tmp_path):
    """Testfall: Blockiert Pfade außerhalb des Quarantäne-Ordners"""
    trash_dir = tmp_path / "mock-trash"
    trash_dir.mkdir()
    
    # Old folder containing symlinks or paths that we inject
    old_folder = trash_dir / "2026-06-12_12-00-00"
    old_folder.mkdir()
    
    # We mock os.walk to return paths outside the trash directory
    # to simulate path manipulation or security breakout
    mock_walk_res = [
        (str(old_folder), [], ["normal.mp4", "../../outside_hacked.mp4"])
    ]
    
    with patch("gui.core.trash.get_trash_dirs", return_value=[str(trash_dir)]), \
         patch("gui.core.trash.os.walk", return_value=mock_walk_res):
         
        deleted, errors = _empty_trash_core(retention_days=7, dry_run=False)
        
        # The outside file delete attempt must be blocked and recorded as error
        assert len(errors) > 0
        error_item, error_msg = errors[0]
        assert "outside_hacked.mp4" in error_item
        assert "Sicherheits-Check fehlgeschlagen" in error_msg


def test_empty_trash_async_concurrency():
    """Testfall: Verhindert die parallele Ausführung von zwei Cleanup-Prozessen"""
    global TRASH_CLEANUP_STATUS
    
    # Force state to running
    TRASH_CLEANUP_STATUS["running"] = True
    
    try:
        with pytest.raises(TrashError, match="Bereinigungsprozess läuft bereits"):
            empty_trash_async(retention_days=7, dry_run=False)
    finally:
        # Reset state
        TRASH_CLEANUP_STATUS["running"] = False


def test_empty_trash_async_success():
    """Testfall: Startet die asynchrone Bereinigung und setzt den Cleanup-Status"""
    global TRASH_CLEANUP_STATUS
    
    assert TRASH_CLEANUP_STATUS["running"] is False
    
    # Mock core cleanup
    with patch("gui.core.trash._empty_trash_core", return_value=(["/mock/file"], [])) as mock_core, \
         patch("gui.core.trash.get_trash_stats"):
         
        res = empty_trash_async(retention_days=7, dry_run=False)
        assert res == {"status": "started"}
        
        # Wait up to 1 second for thread to execute
        for _ in range(10):
            if not TRASH_CLEANUP_STATUS["running"]:
                break
            time.sleep(0.1)
            
        assert TRASH_CLEANUP_STATUS["running"] is False
        assert TRASH_CLEANUP_STATUS["deleted_count"] == 1
        assert TRASH_CLEANUP_STATUS["error_count"] == 0
        assert TRASH_CLEANUP_STATUS["last_error"] is None
        assert TRASH_CLEANUP_STATUS["finished_at"] is not None


def test_empty_trash_core_top_level_symlink(tmp_path):
    """Testfall: Ein Top-Level-Symlink im Trash (als Timestamp-Ordner getarnt)
    wird direkt als Symlink per unlink gelöscht, ohne dem Link-Ziel zu folgen."""
    trash_dir = tmp_path / "mock-trash"
    trash_dir.mkdir()
    
    # Target outside trash
    outside_dir = tmp_path / "outside_victim"
    outside_dir.mkdir()
    outside_file = outside_dir / "victim.txt"
    outside_file.write_text("DO NOT DELETE")
    
    # Symlink timestamp folder pointing to the outside directory
    # name format must match timestamp pattern: YYYY-MM-DD_HH-MM-SS
    symlink_timestamp_folder = trash_dir / "2026-06-12_12-00-00"
    symlink_timestamp_folder.symlink_to(outside_dir)
    
    with patch("gui.core.trash.get_trash_dirs", return_value=[str(trash_dir)]):
        deleted, errors = _empty_trash_core(retention_days=7, dry_run=False)
        
        assert len(errors) == 0
        assert str(symlink_timestamp_folder) in deleted
        
        # The symlink itself must be gone
        assert not symlink_timestamp_folder.exists()
        assert not os.path.lexists(symlink_timestamp_folder)
        
        # The target directory and file outside MUST STILL EXIST!
        assert outside_dir.exists()
        assert outside_file.exists()
        assert outside_file.read_text() == "DO NOT DELETE"


def test_empty_trash_core_zero_days_retention(tmp_path):
    """Testfall: retention_days=0 löscht sofort alle Ordner (auch gerade erst erstellte)
    und fällt nicht auf den Standardwert 7 zurück."""
    trash_dir = tmp_path / "mock-trash"
    trash_dir.mkdir()
    
    # Fresh folder (created "now")
    now_str = time.strftime("%Y-%m-%d_%H-%M-%S")
    fresh_folder = trash_dir / now_str
    fresh_folder.mkdir()
    fresh_file = fresh_folder / "fresh.mp4"
    fresh_file.write_text("fresh content")
    
    with patch("gui.core.trash.get_trash_dirs", return_value=[str(trash_dir)]):
        # With retention_days=0, it should delete the fresh folder immediately
        deleted, errors = _empty_trash_core(retention_days=0, dry_run=False)
        
        assert len(errors) == 0
        assert str(fresh_folder) in deleted
        assert str(fresh_file) in deleted
        
        # Folders and files must be deleted
        assert not fresh_file.exists()
        assert not fresh_folder.exists()

