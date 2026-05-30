"""Dauerhaft ignorierte Befunde (Health-Check & Duplikat-Erkennung).

Speichert eine Liste stabiler Schlüssel in gui/data/ignored_findings.json.
Ein Befund-Schlüssel ist z. B. "health:episode_gap:<pfad>" oder "dup:<gruppen-id>".
Wird von health.py und duplicates.py genutzt, um ignorierte Einträge auszufiltern.
"""

import os
import json
import threading

from gui.core import utils

IGNORE_FILE = os.path.join(utils.DATA_DIR, "ignored_findings.json")
_lock = threading.Lock()


def _load():
    try:
        if os.path.exists(IGNORE_FILE):
            with open(IGNORE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return set(data)
    except Exception:
        pass
    return set()


def _save(keys):
    try:
        os.makedirs(os.path.dirname(IGNORE_FILE), exist_ok=True)
        with open(IGNORE_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(keys), f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def get_ignored():
    """Set aller ignorierten Schlüssel."""
    with _lock:
        return _load()


def add_ignore(key):
    if not key:
        return False
    with _lock:
        keys = _load()
        keys.add(key)
        return _save(keys)


def remove_ignore(key):
    if not key:
        return False
    with _lock:
        keys = _load()
        keys.discard(key)
        return _save(keys)
