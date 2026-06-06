import pytest
import os
import sys

@pytest.fixture(autouse=True)
def reset_global_states():
    # Sichern der ursprünglichen MW_RUNTIME Umgebungsvariable
    orig_runtime = os.environ.get("MW_RUNTIME")
    # Aktiv neutralisieren für den Test
    os.environ.pop("MW_RUNTIME", None)
    
    # Lokale Imports erst im Fixture, um Import-Seiteneffekte zu vermeiden
    persistence = sys.modules.get("gui.core.persistence")
    if persistence is None:
        try:
            import gui.core.persistence as persistence
        except ImportError:
            pass

    utils = sys.modules.get("gui.core.utils")
    if utils is None:
        try:
            import gui.core.utils as utils
        except ImportError:
            pass

    # Vor dem Test: Cache und Mocks neutralisieren
    if persistence is not None:
        persistence._cached_settings = None
        persistence._MOCK_SETTINGS = None
    if utils is not None:
        utils._MOCK_SETTINGS = None
        
    yield
    
    # Nach dem Test: Mocks und Caches erneut neutralisieren
    if persistence is not None:
        persistence._cached_settings = None
        persistence._MOCK_SETTINGS = None
    if utils is not None:
        utils._MOCK_SETTINGS = None
        
    # Umgebungsvariable MW_RUNTIME wiederherstellen
    if orig_runtime is not None:
        os.environ["MW_RUNTIME"] = orig_runtime
    else:
        os.environ.pop("MW_RUNTIME", None)
