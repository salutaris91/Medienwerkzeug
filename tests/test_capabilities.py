import os
import pytest
from unittest import mock
from gui.core.utils import get_runtime_capabilities

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("TESTING", "1")
    import gui.core.persistence as persistence
    
    # Sauberen Standard-State für Settings im Test-Client garantieren
    mock_settings = persistence.DEFAULT_SETTINGS.copy()
    mock_settings["onboarded"] = True
    mock_settings["password_hash"] = ""
    monkeypatch.setattr(persistence, "_MOCK_SETTINGS", mock_settings)
    
    from gui.main import app
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_capabilities_default_desktop(monkeypatch):
    monkeypatch.delenv("MW_RUNTIME", raising=False)
    caps = get_runtime_capabilities()
    assert caps["runtime"] == "desktop"
    assert caps["capabilities"]["open_local_folder"] is True

def test_capabilities_invalid_fallback(monkeypatch):
    monkeypatch.setenv("MW_RUNTIME", "invalid_value")
    caps = get_runtime_capabilities()
    assert caps["runtime"] == "desktop"
    assert caps["capabilities"]["open_local_folder"] is True

def test_capabilities_docker_profile(monkeypatch):
    monkeypatch.setenv("MW_RUNTIME", "docker")
    caps = get_runtime_capabilities()
    assert caps["runtime"] == "docker"
    assert caps["capabilities"]["open_local_folder"] is False

def test_api_capabilities_endpoint(client, monkeypatch):
    monkeypatch.setenv("MW_RUNTIME", "docker")
    res = client.get('/api/system/capabilities')
    assert res.status_code == 200
    data = res.get_json()
    assert data["runtime"] == "docker"
    assert data["capabilities"]["open_local_folder"] is False

def test_api_browse_folder_docker(client, monkeypatch):
    monkeypatch.setenv("MW_RUNTIME", "docker")
    res = client.get('/api/browse-folder')
    assert res.status_code == 403

def test_api_system_open_folder_docker(client, monkeypatch):
    monkeypatch.setenv("MW_RUNTIME", "docker")
    res = client.post('/api/system-open-folder', json={"path": "/tmp"})
    assert res.status_code == 403

@mock.patch('gui.core.transfers.os.path.isdir')
@mock.patch('gui.core.transfers.load_settings')
def test_ensure_nas_mounted_docker(mock_load_settings, mock_isdir, monkeypatch):
    from gui.core.transfers import ensure_nas_mounted
    monkeypatch.setenv("MW_RUNTIME", "docker")
    mock_load_settings.return_value = {"nas_root": "/mock/nas"}
    mock_isdir.return_value = True
    result = ensure_nas_mounted()
    assert result is True
    mock_isdir.assert_called_once_with("/mock/nas")

@mock.patch('gui.api.system_api.load_settings')
@mock.patch('gui.core.helpers.load_settings')
@mock.patch('gui.core.utils.load_settings')
def test_system_folder_contents_allowed(mock_utils_load, mock_helper_load, mock_api_load, client, tmp_path):
    mock_utils_load.return_value = {"inbox_dir": str(tmp_path)}
    mock_helper_load.return_value = {"inbox_dir": str(tmp_path)}
    mock_api_load.return_value = {"inbox_dir": str(tmp_path)}
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello")
    
    res = client.post('/api/system-folder-contents', json={"path": str(tmp_path)})
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert len(data["files"]) == 1
    assert data["files"][0]["name"] == "test.txt"
    assert data["files"][0]["is_dir"] is False
    assert data["files"][0]["size_bytes"] == 5
    assert data["files"][0]["is_error"] is False

@mock.patch('gui.api.system_api.load_settings')
@mock.patch('gui.core.helpers.load_settings')
@mock.patch('gui.core.utils.load_settings')
def test_system_folder_contents_denied(mock_utils_load, mock_helper_load, mock_api_load, client, tmp_path):
    mock_utils_load.return_value = {"inbox_dir": str(tmp_path)}
    mock_helper_load.return_value = {"inbox_dir": str(tmp_path)}
    mock_api_load.return_value = {"inbox_dir": str(tmp_path)}
    
    res = client.post('/api/system-folder-contents', json={"path": "/etc"})
    assert res.status_code == 403
    assert "Access Denied" in res.get_json()["error"]

@mock.patch('gui.api.system_api.load_settings')
@mock.patch('gui.core.helpers.load_settings')
@mock.patch('gui.core.utils.load_settings')
def test_system_folder_contents_file_instead_of_dir(mock_utils_load, mock_helper_load, mock_api_load, client, tmp_path):
    mock_utils_load.return_value = {"inbox_dir": str(tmp_path)}
    mock_helper_load.return_value = {"inbox_dir": str(tmp_path)}
    mock_api_load.return_value = {"inbox_dir": str(tmp_path)}
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello")
    
    # Durch die automatische Pfad-Auflösung für Dateien wird nun der Parent-Ordner geladen
    res = client.post('/api/system-folder-contents', json={"path": str(test_file)})
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert len(data["files"]) == 1
    assert data["files"][0]["name"] == "test.txt"

@mock.patch('gui.core.helpers.load_settings')
@mock.patch('gui.core.utils.load_settings')
def test_is_path_allowed_symlink_breakout(mock_utils_load, mock_load, tmp_path):
    from gui.core.helpers import is_path_allowed
    import os
    allowed_dir = tmp_path / "allowed"
    allowed_dir.mkdir()
    
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    outside_file = outside_dir / "secret.txt"
    outside_file.write_text("secret")
    
    mock_utils_load.return_value = {"inbox_dir": str(allowed_dir)}
    mock_load.return_value = {"inbox_dir": str(allowed_dir)}
    
    # Create symlink inside allowed_dir pointing outside
    symlink_path = allowed_dir / "breakout_link"
    try:
        os.symlink(str(outside_dir), str(symlink_path))
        
        # Ensure allowed_dir itself is allowed
        assert is_path_allowed(str(allowed_dir)) is True
        
        # Ensure the symlink resolving to outside is denied
        assert is_path_allowed(str(symlink_path)) is False
    except OSError:
        pytest.skip("Symlinks not supported on this OS/filesystem")

def test_capabilities_dev_mode(monkeypatch):
    # Default (unset) -> False
    monkeypatch.delenv("MW_DEV_MODE", raising=False)
    caps = get_runtime_capabilities()
    assert caps["dev_mode"] is False

    # True values
    for val in ("true", "1", "yes", "on", "TRUE", "Yes", " true ", "  yes\n"):
        monkeypatch.setenv("MW_DEV_MODE", val)
        caps = get_runtime_capabilities()
        assert caps["dev_mode"] is True

    # False values
    for val in ("false", "0", "no", "off", "anything"):
        monkeypatch.setenv("MW_DEV_MODE", val)
        caps = get_runtime_capabilities()
        assert caps["dev_mode"] is False
