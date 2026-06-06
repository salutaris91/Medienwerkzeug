import pytest
import os
import sys

@pytest.fixture(autouse=True)
def reset_global_states():
    # Sichern der ursprünglichen MW_RUNTIME Umgebungsvariable
    orig_runtime = os.environ.get("MW_RUNTIME")
    # Aktiv neutralisieren für den Test
    os.environ.pop("MW_RUNTIME", None)
    
    # Greife defensiv auf bereits geladene Module in sys.modules zu.
    # Wir importieren sie hier NICHT aktiv, um Import-Seiteneffekte auf Modulebene zu vermeiden.
    persistence = sys.modules.get("gui.core.persistence")
    utils = sys.modules.get("gui.core.utils")

    # Vor dem Test: Cache und Mocks neutralisieren, falls geladen
    if persistence is not None:
        persistence._cached_settings = None
        persistence._MOCK_SETTINGS = None
    if utils is not None:
        utils._MOCK_SETTINGS = None
        
    yield
    
    # Nach dem Test: Mocks und Caches erneut neutralisieren, falls geladen
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
