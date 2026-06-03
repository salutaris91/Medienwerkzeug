import os
import pytest
from unittest.mock import patch, MagicMock

from gui.core.trash import get_allowed_roots, send_to_trash, TrashError


@patch("gui.core.trash.os.path.exists", return_value=True)
@patch("gui.core.trash.os.path.realpath", side_effect=lambda x: x)
def test_get_allowed_roots_uses_correct_keys(mock_realpath, mock_exists):
    """Testfall 1: Es prüft, dass get_allowed_roots() die echten Settings-Keys verwendet"""
    with patch("gui.core.utils.load_settings") as mock_load:
        mock_load.return_value = {
            "inbox_dir": "/mock/inbox",
            "outbox_dir": "/mock/outbox",
            "nas_root": "/mock/nas",
            "import_sources": [{"path": "/mock/import"}]
        }
        
        roots = get_allowed_roots()
        
        assert "/mock/inbox" in roots
        assert "/mock/outbox" in roots
        assert "/mock/nas" in roots
        assert "/mock/import" in roots


@patch("gui.core.trash.os.path.exists", return_value=True)
@patch("gui.core.trash.os.path.realpath", side_effect=lambda x: x)
@patch("gui.core.trash.get_allowed_roots", return_value=["/allowed"])
def test_desktop_mode_uses_send2trash(mock_roots, mock_realpath, mock_exists):
    """Testfall 2: Es prüft, dass Desktop-Modus send2trash verwendet"""
    with patch("gui.core.utils.get_runtime_capabilities") as mock_caps:
        mock_caps.return_value = {"runtime": "desktop", "capabilities": {"safe_delete": True}}
        
        with patch("send2trash.send2trash") as mock_send2trash:
            result = send_to_trash("/allowed/file.txt")
            assert result is True
            mock_send2trash.assert_called_once_with("/allowed/file.txt")


@patch("gui.core.trash.os.path.exists", return_value=True)
@patch("gui.core.trash.os.path.realpath", side_effect=lambda x: x)
@patch("gui.core.trash.get_allowed_roots", return_value=["/allowed"])
def test_boundary_check(mock_roots, mock_realpath, mock_exists):
    """Testfall 3: Es prüft, dass der Boundary-Check greift (außerhalb erlaubter Roots)"""
    with pytest.raises(TrashError, match="außerhalb der erlaubten Lösch-Zonen"):
        send_to_trash("/not/allowed/file.txt")


@patch("gui.core.trash.os.path.exists", return_value=True)
@patch("gui.core.trash.os.path.realpath", side_effect=lambda x: x)
@patch("gui.core.trash.get_allowed_roots", return_value=["/allowed"])
@patch("gui.core.trash.os.stat")
@patch("gui.core.trash.shutil.move")
@patch("gui.core.trash.os.makedirs")
@patch("gui.core.trash.os.access", return_value=True)
def test_docker_mode_moves_to_trash_folder(mock_access, mock_makedirs, mock_move, mock_stat, mock_roots, mock_realpath, mock_exists):
    """Testfall 4: Es prüft, dass Docker-Modus Dateien innerhalb desselben Mountpoints verschiebt"""
    with patch("gui.core.utils.get_runtime_capabilities") as mock_caps:
        mock_caps.return_value = {"runtime": "docker", "capabilities": {"safe_delete": True}}
        
        # Simulate that /allowed and its contents have st_dev = 1, but / has st_dev = 0
        def stat_side_effect(path):
            m = MagicMock()
            m.st_dev = 0 if path == "/" else 1
            return m
        mock_stat.side_effect = stat_side_effect
        
        # When checking exists for the destination, say it doesn't exist to avoid timestamp
        def exists_side_effect(path):
            if path.endswith("file.txt") and ".medienwerkzeug-trash" in path:
                return False
            return True
        mock_exists.side_effect = exists_side_effect
        
        with patch("gui.core.trash.os.path.isfile", return_value=True):
            send_to_trash("/allowed/file.txt")
            
            # Should have moved to /allowed/.medienwerkzeug-trash/file.txt
            mock_move.assert_called_once_with("/allowed/file.txt", "/allowed/.medienwerkzeug-trash/file.txt")


@patch("gui.core.trash.os.path.exists", return_value=True)
@patch("gui.core.trash.os.path.realpath", side_effect=lambda x: x)
@patch("gui.core.trash.get_allowed_roots", return_value=["/allowed"])
@patch("gui.core.trash.os.stat")
def test_docker_fails_on_root_fallback(mock_stat, mock_roots, mock_realpath, mock_exists):
    """Testfall 5: Es prüft, dass Docker bei verbotenem /-Fallback oder ungültigem Mountpoint sichtbar mit TrashError abbricht"""
    with patch("gui.core.utils.get_runtime_capabilities") as mock_caps:
        mock_caps.return_value = {"runtime": "docker", "capabilities": {"safe_delete": True}}
        
        # Simulate different partitions:
        # /allowed/dir has st_dev=3, /allowed has st_dev=2, / has st_dev=1
        # We want it to traverse to / and see that it's on a different partition,
        # wait, if /allowed is the root, then mount_point is /allowed.
        # To test fallback to '/', we need the loop to reach '/' with the SAME partition
        # as the file, meaning it couldn't find a sub-mountpoint.
        def stat_side_effect(path):
            m = MagicMock()
            m.st_dev = 1 # Everything is on partition 1
            return m
        mock_stat.side_effect = stat_side_effect
        
        with patch("gui.core.trash.os.path.isfile", return_value=True):
            with pytest.raises(TrashError, match="Fallback auf '/' verboten"):
                send_to_trash("/allowed/dir/file.txt")


@patch("gui.core.trash.os.path.exists", return_value=True)
@patch("gui.core.trash.os.path.realpath")
@patch("gui.core.trash.get_allowed_roots", return_value=["/allowed"])
def test_symlink_resolution(mock_roots, mock_realpath, mock_exists):
    """Testfall 6: Es prüft, dass Symlinks sicher aufgelöst werden"""
    # The file is a symlink pointing OUTSIDE the allowed roots
    mock_realpath.return_value = "/outside/real/path/file.txt"
    
    with pytest.raises(TrashError, match="außerhalb der erlaubten Lösch-Zonen"):
        send_to_trash("/allowed/symlink_to_outside")


@patch("gui.core.trash.os.path.exists")
@patch("gui.core.trash.os.path.realpath", side_effect=lambda x: x)
@patch("gui.core.trash.get_allowed_roots", return_value=["/allowed"])
@patch("gui.core.trash.os.stat")
@patch("gui.core.trash.shutil.move")
@patch("gui.core.trash.os.makedirs")
@patch("gui.core.trash.os.access", return_value=True)
@patch("gui.core.trash.time.time", return_value=1234567890.0)
def test_docker_mode_collision_avoidance(mock_time, mock_access, mock_makedirs, mock_move, mock_stat, mock_roots, mock_realpath, mock_exists):
    """Testfall 7: Es prüft, dass Kollisionen im Trash-Ordner vermieden werden"""
    with patch("gui.core.utils.get_runtime_capabilities") as mock_caps:
        mock_caps.return_value = {"runtime": "docker", "capabilities": {"safe_delete": True}}
        def stat_side_effect(path):
            m = MagicMock()
            m.st_dev = 0 if path == "/" else 1
            return m
        mock_stat.side_effect = stat_side_effect
        
        def exists_side_effect(path):
            # The source file exists
            if path == "/allowed/file.txt": return True
            # The destination already exists, forcing a rename
            if path == "/allowed/.medienwerkzeug-trash/file.txt": return True
            # The root path exists
            if path == "/allowed": return True
            return False
        mock_exists.side_effect = exists_side_effect
        
        with patch("gui.core.trash.os.path.isfile", return_value=True):
            send_to_trash("/allowed/file.txt")
            
            # Should have moved with timestamp added
            mock_move.assert_called_once_with("/allowed/file.txt", "/allowed/.medienwerkzeug-trash/file_1234567890.txt")
