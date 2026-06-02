import os
import pytest
from unittest import mock
from gui.core.utils import get_runtime_capabilities

def test_capabilities_default_desktop():
    with mock.patch.dict(os.environ, {}, clear=True):
        caps = get_runtime_capabilities()
        assert caps["runtime"] == "desktop"
        assert caps["capabilities"]["open_local_folder"] is True
        assert caps["capabilities"]["mount_nas"] is True
        assert caps["capabilities"]["native_notifications"] is True
        assert caps["capabilities"]["import_sources"] is True
        assert caps["capabilities"]["safe_delete"] is True

def test_capabilities_invalid_fallback():
    with mock.patch.dict(os.environ, {"MW_RUNTIME": "invalid_value"}, clear=True):
        caps = get_runtime_capabilities()
        assert caps["runtime"] == "desktop"

def test_capabilities_docker_profile():
    with mock.patch.dict(os.environ, {"MW_RUNTIME": "docker"}, clear=True):
        caps = get_runtime_capabilities()
        assert caps["runtime"] == "docker"
        assert caps["capabilities"]["open_local_folder"] is False
        assert caps["capabilities"]["mount_nas"] is False
        assert caps["capabilities"]["native_notifications"] is False
        assert caps["capabilities"]["safe_delete"] is False
