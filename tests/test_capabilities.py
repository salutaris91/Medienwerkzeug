import os
import pytest
from unittest import mock
from gui.core.utils import get_runtime_capabilities

@pytest.fixture
def client():
    os.environ["TESTING"] = "1"
    from gui.main import app
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_capabilities_default_desktop():
    with mock.patch.dict(os.environ, {}, clear=True):
        caps = get_runtime_capabilities()
        assert caps["runtime"] == "desktop"
        assert caps["capabilities"]["open_local_folder"] is True

def test_capabilities_docker_profile():
    with mock.patch.dict(os.environ, {"MW_RUNTIME": "docker"}, clear=True):
        caps = get_runtime_capabilities()
        assert caps["runtime"] == "docker"
        assert caps["capabilities"]["open_local_folder"] is False

def test_api_capabilities_endpoint(client):
    with mock.patch.dict(os.environ, {"MW_RUNTIME": "docker"}, clear=True):
        res = client.get('/api/system/capabilities')
        assert res.status_code == 200
        data = res.get_json()
        assert data["runtime"] == "docker"
        assert data["capabilities"]["open_local_folder"] is False

def test_api_browse_folder_docker(client):
    with mock.patch.dict(os.environ, {"MW_RUNTIME": "docker"}, clear=True):
        res = client.get('/api/browse-folder')
        assert res.status_code == 403

def test_api_system_open_folder_docker(client):
    with mock.patch.dict(os.environ, {"MW_RUNTIME": "docker"}, clear=True):
        res = client.post('/api/system-open-folder', json={"path": "/tmp"})
        assert res.status_code == 403

@mock.patch('gui.core.transfers.os.path.isdir')
@mock.patch('gui.core.transfers.load_settings')
def test_ensure_nas_mounted_docker(mock_load_settings, mock_isdir):
    from gui.core.transfers import ensure_nas_mounted
    with mock.patch.dict(os.environ, {"MW_RUNTIME": "docker"}, clear=True):
        mock_load_settings.return_value = {"nas_root": "/mock/nas"}
        mock_isdir.return_value = True
        result = ensure_nas_mounted()
        assert result is True
        mock_isdir.assert_called_once_with("/mock/nas")
