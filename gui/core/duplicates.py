"""Feature 4: NAS-weite Duplikat-Erkennung.

Findet doppelte Serien-Episoden auf dem NAS (gleiche SxxExx innerhalb einer
Show, z.B. eine alte H.264- und eine neue H.265-Fassung). Reichert die
Duplikat-Gruppen per ffprobe an (Codec/Auflösung/Größe) und empfiehlt, welche
Datei behalten werden sollte.

Läuft als Hintergrund-Thread; State + Cache analog zum Health-Scan.
"""

import os
import re
import json
import time
import threading
from collections import defaultdict

from gui.core import utils
from gui.core import media
from gui.core.transfers import ensure_nas_mounted, walk_nas_categories
from gui.core.helpers import log_message

VIDEO_EXTENSIONS = {'.mkv', '.mp4', '.avi', '.m4v', '.ts', '.mov', '.wmv'}
EFFICIENT_CODECS = {'hevc', 'h265', 'av1', 'vp9'}
SIDECAR_SUFFIXES = ['.nfo', '.srt', '-thumb.jpg', '-poster.jpg', '-fanart.jpg']

SXXEXX_RE = re.compile(r'[Ss](\d{1,3})[Ee](\d{1,4})')

CACHE_FILE = os.path.join(utils.DATA_DIR, "duplicate_scan_cache.json")

_state_lock = threading.Lock()
_scan_state = {
    "status": "idle",       # idle | running | done | error
    "progress": 0,
    "message": "",
    "started_at": None,
    "finished_at": None,
    "groups": [],
    "summary": {"groups": 0, "files": 0, "reclaimable_bytes": 0},
    "error": None,
}


def _set_state(**kwargs):
    with _state_lock:
        _scan_state.update(kwargs)


def _resolution_label(width, height):
    if not height:
        return "unbekannt"
    h = int(height)
    if h >= 2000:
        return "2160p"
    if h >= 1000:
        return "1080p"
    if h >= 700:
        return "720p"
    if h >= 500:
        return "576p"
    return f"{h}p"


def _keep_rank(info):
    """Höher = eher behalten: effizienter Codec, dann höhere Auflösung, dann kleinere Datei."""
    eff = 1 if (info.get("codec") in EFFICIENT_CODECS) else 0
    res = (info.get("width") or 0) * (info.get("height") or 0)
    size = info.get("size") or 0
    return (eff, res, -size)


def _build_group(show, season, episode, paths):
    files = []
    for p in paths:
        mi = media.get_media_info(p)
        files.append({
            "path": p,
            "filename": os.path.basename(p),
            "size": mi.get("size"),
            "codec": mi.get("codec"),
            "width": mi.get("width"),
            "height": mi.get("height"),
            "duration": mi.get("duration"),
            "resolution": _resolution_label(mi.get("width"), mi.get("height")),
        })

    # Empfehlung bestimmen
    files.sort(key=lambda f: _keep_rank(f), reverse=True)
    reclaimable = 0
    for idx, f in enumerate(files):
        if idx == 0:
            f["recommended"] = "keep"
        else:
            f["recommended"] = "remove"
            reclaimable += f.get("size") or 0

    keep = files[0]
    reasons = []
    if keep.get("codec") in EFFICIENT_CODECS:
        reasons.append(f"effizienter Codec ({keep['codec']})")
    reasons.append(f"Auflösung {keep['resolution']}")
    keep["reason"] = ", ".join(reasons)

    return {
        "id": f"{show}|S{int(season):02d}|E{int(episode):02d}",
        "category": None,  # wird vom Aufrufer gesetzt
        "show": show,
        "season": int(season),
        "episode": int(episode),
        "files": files,
        "reclaimable_bytes": reclaimable,
    }


def _run_duplicate_scan():
    try:
        if not ensure_nas_mounted():
            _set_state(status="error", message="NAS konnte nicht gemountet werden.",
                       error="nas_unavailable", finished_at=time.time())
            log_message("❌ [Duplikat-Scan] NAS nicht verfügbar.")
            return

        settings = utils.load_settings()
        series_shows = [x for x in walk_nas_categories(settings) if x["type"] == "series"]
        total = len(series_shows)
        log_message(f"🔍 [Duplikat-Scan] Prüfe {total} Serien auf doppelte Episoden...")

        groups = []
        for idx, show in enumerate(series_shows):
            _set_state(
                progress=int((idx / total) * 100) if total else 100,
                message=f"Prüfe {show['name']} ({idx + 1}/{total})",
            )
            # Episoden sammeln und nach (Staffel, Episode) gruppieren
            by_ep = defaultdict(list)
            for dirpath, _dirs, filenames in os.walk(show["path"]):
                for f in filenames:
                    if f.startswith('.'):
                        continue
                    if os.path.splitext(f)[1].lower() not in VIDEO_EXTENSIONS:
                        continue
                    m = SXXEXX_RE.search(f)
                    if m:
                        by_ep[(int(m.group(1)), int(m.group(2)))].append(os.path.join(dirpath, f))

            for (season, episode), paths in by_ep.items():
                if len(paths) >= 2:
                    grp = _build_group(show["name"], season, episode, paths)
                    grp["category"] = show["category"]
                    groups.append(grp)

        # Sortiere Gruppen nach rückgewinnbarem Platz (absteigend)
        groups.sort(key=lambda g: g.get("reclaimable_bytes", 0), reverse=True)

        total_reclaim = sum(g["reclaimable_bytes"] for g in groups)
        total_files = sum(len(g["files"]) for g in groups)
        result = {
            "status": "done",
            "progress": 100,
            "message": f"Scan abgeschlossen: {len(groups)} Duplikat-Gruppen gefunden.",
            "finished_at": time.time(),
            "groups": groups,
            "summary": {
                "groups": len(groups),
                "files": total_files,
                "reclaimable_bytes": total_reclaim,
            },
            "error": None,
        }
        _set_state(**result)
        _write_cache()
        log_message(f"✅ [Duplikat-Scan] Fertig: {len(groups)} Gruppen, "
                    f"{round(total_reclaim / (1024**3), 2)} GB rückgewinnbar.")

    except Exception as e:
        import traceback
        traceback.print_exc()
        _set_state(status="error", message=f"Fehler beim Scan: {e}",
                   error=str(e), finished_at=time.time())
        log_message(f"❌ [Duplikat-Scan] Fehler: {e}")


def start_duplicate_scan():
    with _state_lock:
        if _scan_state["status"] == "running":
            return False
        _scan_state.update({
            "status": "running",
            "progress": 0,
            "message": "Scan wird gestartet...",
            "started_at": time.time(),
            "finished_at": None,
            "groups": [],
            "summary": {"groups": 0, "files": 0, "reclaimable_bytes": 0},
            "error": None,
        })
    threading.Thread(target=_run_duplicate_scan, daemon=True).start()
    return True


def get_duplicate_status():
    with _state_lock:
        if _scan_state["status"] == "idle":
            cached = _read_cache()
            if cached:
                return cached
        import copy
        return copy.deepcopy(_scan_state)


def resolve_duplicate(file_path):
    """Löscht eine als Duplikat gewählte Videodatei inkl. Begleitdateien.

    Sicherheitsprüfungen:
    - Pfad muss unterhalb der NAS-Root liegen.
    - Datei muss eine existierende Videodatei sein.

    Gibt (ok: bool, message: str) zurück.
    """
    settings = utils.load_settings()
    nas_root = os.path.realpath(settings.get("nas_root", "/Volumes/Kino"))
    target = os.path.realpath(file_path)

    # Containment-Check: nur innerhalb der NAS-Root löschen
    if os.path.commonpath([nas_root, target]) != nas_root:
        return False, "Pfad liegt außerhalb der NAS-Root – Löschen abgelehnt."

    if os.path.splitext(target)[1].lower() not in VIDEO_EXTENSIONS:
        return False, "Kein Videodatei-Pfad – Löschen abgelehnt."

    if not os.path.isfile(target):
        return False, "Datei nicht gefunden (evtl. bereits gelöscht)."

    deleted = []
    try:
        os.remove(target)
        deleted.append(os.path.basename(target))
    except Exception as e:
        return False, f"Fehler beim Löschen: {e}"

    # Begleitdateien mit gleichem Basisnamen entfernen
    base = os.path.splitext(target)[0]
    for suffix in SIDECAR_SUFFIXES:
        sidecar = base + suffix
        if os.path.isfile(sidecar):
            try:
                os.remove(sidecar)
                deleted.append(os.path.basename(sidecar))
            except Exception:
                pass

    # Leeren Episoden-Unterordner aufräumen (falls die Datei in eigenem Ordner lag)
    parent = os.path.dirname(target)
    try:
        if os.path.realpath(parent) != nas_root and not os.listdir(parent):
            os.rmdir(parent)
    except Exception:
        pass

    log_message(f"🗑️ [Duplikat] Gelöscht: {', '.join(deleted)}")
    return True, f"Gelöscht: {', '.join(deleted)}"


# ---------------------------------------------------------------------------
# Cache I/O
# ---------------------------------------------------------------------------
def _write_cache():
    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        with _state_lock:
            import copy
            data = copy.deepcopy(_scan_state)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log_message(f"⚠️ [Duplikat-Scan] Cache konnte nicht geschrieben werden: {e}")


def _read_cache():
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return None
