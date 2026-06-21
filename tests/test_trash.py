import os
import pytest
from unittest.mock import patch, MagicMock

from gui.core.trash import get_allowed_roots, send_to_trash, TrashError

@patch("gui.core.trash.os.path.exists", return_value=True)
@patch("gui.core.trash.os.path.realpath", side_effect=lambda x: x)
def test_get_allowed_roots_uses_correct_keys(mock_realpath, mock_exists, monkeypatch):
    """Testfall 1: Es prüft, dass get_allowed_roots() die echten Settings-Keys verwendet"""
    import gui.core.persistence as persistence
    import gui.core.utils as utils
    mock_val = {
        "inbox_dir": "/mock/inbox",
        "outbox_dir": "/mock/outbox",
        "nas_root": "/mock/nas",
        "import_sources": [{"path": "/mock/import"}]
    }
    monkeypatch.setattr(persistence, "_MOCK_SETTINGS", mock_val)
    monkeypatch.setattr(utils, "_MOCK_SETTINGS", mock_val)
    
    roots = get_allowed_roots()
    
    assert "/mock/inbox" in roots
    assert "/mock/outbox" in roots
    assert "/mock/nas" in roots
    assert "/mock/import" in roots

@patch("gui.core.trash.os.path.exists", return_value=True)
@patch("gui.core.trash.os.path.realpath", side_effect=lambda x: x)
def test_get_allowed_roots_with_mixed_sources(mock_realpath, mock_exists, monkeypatch):
    """Testfall: Es prüft, dass get_allowed_roots() mit Strings und Dicts in import_sources umgehen kann"""
    import gui.core.persistence as persistence
    import gui.core.utils as utils
    mock_val = {
        "inbox_dir": "/mock/inbox",
        "import_sources": [{"path": "/mock/dict_import"}, "/mock/string_import"]
    }
    monkeypatch.setattr(persistence, "_MOCK_SETTINGS", mock_val)
    monkeypatch.setattr(utils, "_MOCK_SETTINGS", mock_val)
    
    roots = get_allowed_roots()
    
    assert "/mock/inbox" in roots
    assert "/mock/dict_import" in roots
    assert "/mock/string_import" in roots


@patch("gui.core.trash.os.path.exists", return_value=True)
@patch("gui.core.trash.os.path.realpath", side_effect=lambda x: x)
@patch("gui.core.trash.get_allowed_roots", return_value=["/allowed"])
def test_desktop_mode_uses_send2trash(mock_roots, mock_realpath, mock_exists, monkeypatch):
    """Testfall 2: Es prüft, dass Desktop-Modus send2trash verwendet"""
    monkeypatch.setenv("MW_RUNTIME", "desktop")
    
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
def test_docker_mode_moves_to_trash_folder(mock_access, mock_makedirs, mock_move, mock_stat, mock_roots, mock_realpath, mock_exists, monkeypatch):
    """Testfall 4: Es prüft, dass Docker-Modus Dateien innerhalb desselben Mountpoints verschiebt"""
    monkeypatch.setenv("MW_RUNTIME", "docker")
    
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
        
        assert mock_move.call_count == 1
        src_arg, dest_arg = mock_move.call_args[0]
        assert src_arg == "/allowed/file.txt"
        assert dest_arg.startswith("/allowed/.medienwerkzeug-trash/")
        assert dest_arg.endswith("/allowed/file.txt")


@patch("gui.core.trash.os.path.exists", return_value=True)
@patch("gui.core.trash.os.path.realpath", side_effect=lambda x: x)
@patch("gui.core.trash.get_allowed_roots", return_value=["/allowed"])
@patch("gui.core.trash.os.stat")
def test_docker_fails_on_root_fallback(mock_stat, mock_roots, mock_realpath, mock_exists, monkeypatch):
    """Testfall 5: Es prüft, dass Docker bei verbotenem /-Fallback oder ungültigem Mountpoint sichtbar mit TrashError abbricht"""
    monkeypatch.setenv("MW_RUNTIME", "docker")
    
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
def test_docker_mode_collision_avoidance(mock_time, mock_access, mock_makedirs, mock_move, mock_stat, mock_roots, mock_realpath, mock_exists, monkeypatch):
    """Testfall 7: Es prüft, dass Kollisionen im Trash-Ordner vermieden werden"""
    monkeypatch.setenv("MW_RUNTIME", "docker")
    
    def stat_side_effect(path):
        m = MagicMock()
        m.st_dev = 0 if path == "/" else 1
        return m
    mock_stat.side_effect = stat_side_effect
    
    def exists_side_effect(path):
        # The source file exists
        if path == "/allowed/file.txt": return True
        # If it's the expected destination path without renaming, return True to force rename
        if ".medienwerkzeug-trash" in path and path.endswith("/file.txt"): return True
        # The root path exists
        if path == "/allowed": return True
        return False
    mock_exists.side_effect = exists_side_effect
    
    with patch("gui.core.trash.os.path.isfile", return_value=True):
        send_to_trash("/allowed/file.txt")
        
        assert mock_move.call_count == 1
        src_arg, dest_arg = mock_move.call_args[0]
        assert src_arg == "/allowed/file.txt"
        assert dest_arg.startswith("/allowed/.medienwerkzeug-trash/")
        assert dest_arg.endswith("/allowed/file_1.txt")

@pytest.fixture
def test_client():
    from flask import Flask
    from gui.api.project_api import project_api
    app = Flask(__name__)
    app.register_blueprint(project_api, url_prefix='/api/project')
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_project_api_returns_500_on_trash_error(test_client):
    """Testfall: Es prüft, dass API bulk delete bei Quarantäne-Fehler einen 500er Fehler liefert"""
    with patch("gui.api.project_api.load_settings") as mock_settings:
        mock_settings.return_value = {"inbox_dir": "/mock/inbox"}
        with patch("gui.api.project_api.os.path.exists", return_value=True), \
             patch("gui.api.project_api.is_path_allowed", return_value=True), \
             patch("gui.api.project_api.os.path.abspath", side_effect=lambda x: x), \
             patch("gui.api.project_api.trash.send_to_trash") as mock_trash:
             
            mock_trash.side_effect = Exception("API Trash Error")
            
            response = test_client.post("/api/project/paths-clean", json={
                "action": "delete",
                "inbox_files": ["file1.mp4"],
                "output_files": []
            })
            
            assert response.status_code == 500
            data = response.get_json()
            assert "Quarantäne-Fehler bei inbox/file1.mp4: API Trash Error" in data["error"]

def test_processor_propagates_trash_error():
    """Testfall: Es prüft, dass processor.py bei Quarantäne-Fehler eine Exception wirft"""
    from gui.workers.processor import execute_streamfab_import
    with patch("gui.workers.processor.trash.send_to_trash") as mock_trash, \
         patch("gui.workers.processor.os.makedirs"), \
         patch("gui.workers.processor.os.path.exists", return_value=True), \
         patch("gui.workers.processor.shutil.move"):
         
        mock_trash.side_effect = Exception("Simulated Trash Error")
        
        with pytest.raises(Exception, match="Quarantäne-Fehler bei test_file: Simulated Trash Error"):
            execute_streamfab_import({}, ["/some/path/test_file"])
