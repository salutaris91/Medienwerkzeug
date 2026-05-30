"""Feature 3: Media Health Dashboard.

Scannt die NAS-Bibliothek auf typische Pflegeprobleme:
- fehlende Episoden-/Film-NFOs
- fehlendes Poster/Fanart
- Episodenlücken innerhalb einer Staffel
- leere bzw. video-lose Ordner
- uneinheitliche Codecs innerhalb einer Staffel (ffprobe-Stichprobe)
- verdächtig kleine Videodateien

Läuft als Hintergrund-Thread; Fortschritt + Ergebnis werden in einem
modulglobalen State gehalten und zusätzlich in eine Cache-Datei geschrieben.
"""

import os
import re
import json
import time
import threading

from gui.core import utils
from gui.core import media
from gui.core.transfers import ensure_nas_mounted, walk_nas_categories
from gui.core.helpers import log_message

# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------
VIDEO_EXTENSIONS = {'.mkv', '.mp4', '.avi', '.m4v', '.ts', '.mov', '.wmv'}
SMALL_FILE_BYTES = 50 * 1024 * 1024          # < 50 MB gilt als verdächtig klein
CODEC_SAMPLES_PER_SEASON = 3                 # max. ffprobe-Aufrufe pro Staffel
EFFICIENT_CODECS = {'hevc', 'h265', 'av1', 'vp9'}

CACHE_FILE = os.path.join(utils.DATA_DIR, "health_scan_cache.json")

SXXEXX_RE = re.compile(r'[Ss](\d{1,3})[Ee](\d{1,4})')

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png'}

# ---------------------------------------------------------------------------
# Thread-sicherer State
# ---------------------------------------------------------------------------
_state_lock = threading.Lock()
_scan_state = {
    "status": "idle",       # idle | running | done | error
    "progress": 0,
    "message": "",
    "started_at": None,
    "finished_at": None,
    "issues": [],
    "summary": {"critical": 0, "warning": 0, "info": 0},
    "scanned": {"shows": 0, "files": 0},
    "error": None,
}


def _set_state(**kwargs):
    with _state_lock:
        _scan_state.update(kwargs)


def _add_issue(issues, severity, issue_type, category, path, message):
    issues.append({
        "severity": severity,
        "type": issue_type,
        "category": category,
        "path": path,
        "message": message,
    })


# ---------------------------------------------------------------------------
# Einzel-Checks
# ---------------------------------------------------------------------------
def _episode_numbers(filenames):
    nums = []
    for f in filenames:
        m = SXXEXX_RE.search(f)
        if m:
            nums.append(int(m.group(2)))
    return sorted(set(nums))


def _has_any_artwork(entries):
    """True, wenn der Ordner mindestens eine Bilddatei enthält.

    Die Bibliothek nutzt unterschiedliche Konventionen (poster/fanart/banner/
    clearlogo/discart ...). Wir flaggen daher nur Ordner ganz OHNE Artwork.
    """
    return any(os.path.splitext(e)[1].lower() in IMAGE_EXTENSIONS for e in entries)


def _collect_videos(root):
    """Sammelt Videodateien und NFO-Basisnamen rekursiv unter 'root'.

    Die NAS-Struktur legt Episoden in eigene Unterordner
    (Staffel N/<Episoden-Ordner>/<video>+<nfo>), daher rekursiv.

    Rückgabe: (videos, nfo_basenames)
      videos        -> Liste von (full_path, filename)
      nfo_basenames -> Set aus full_path-ohne-Endung der .nfo-Dateien
    """
    videos = []
    nfo_basenames = set()
    for dirpath, dirnames, filenames in os.walk(root):
        for f in filenames:
            if f.startswith('.'):
                continue
            full = os.path.join(dirpath, f)
            ext = os.path.splitext(f)[1].lower()
            if ext in VIDEO_EXTENSIONS:
                videos.append((full, f))
            elif ext == '.nfo' and f.lower() != 'tvshow.nfo':
                nfo_basenames.add(os.path.splitext(full)[0])
    return videos, nfo_basenames


def _check_season(issues, category, show_name, season_path):
    """Prüft einen einzelnen Staffel-Ordner (rekursiv). Gibt geprüfte Dateien zurück."""
    # Showname voranstellen, damit das Issue auf einen Blick zuordenbar ist
    label = f"{show_name} · {os.path.basename(season_path)}"
    videos, nfo_basenames = _collect_videos(season_path)

    # Leerer / video-loser Ordner
    if not videos:
        _add_issue(issues, "info", "empty_folder", category, season_path,
                   f"{label}: keine Videodateien")
        return 0

    # Fehlende Episoden-NFOs (gleicher Basisname im selben Ordner)
    missing_nfo = [fn for (full, fn) in videos if os.path.splitext(full)[0] not in nfo_basenames]
    if missing_nfo:
        _add_issue(issues, "warning", "missing_nfo", category, season_path,
                   f"{label}: {len(missing_nfo)} von {len(videos)} Episoden ohne NFO")

    # Episodenlücken (nur innerhalb des beobachteten Bereichs min..max)
    nums = _episode_numbers(fn for (full, fn) in videos)
    if len(nums) >= 2:
        full_range = set(range(nums[0], nums[-1] + 1))
        missing = sorted(full_range - set(nums))
        if missing:
            preview = ", ".join(f"E{n:02d}" for n in missing[:10])
            if len(missing) > 10:
                preview += " …"
            _add_issue(issues, "critical", "episode_gap", category, season_path,
                       f"{label}: Episodenlücke ({preview})")

    # Verdächtig kleine Dateien
    small = []
    for (full, fn) in videos:
        try:
            if os.path.getsize(full) < SMALL_FILE_BYTES:
                small.append(fn)
        except OSError:
            pass
    if small:
        _add_issue(issues, "warning", "small_file", category, season_path,
                   f"{label}: {len(small)} verdächtig kleine Videodatei(en) (< 50 MB)")

    # Codec-Inkonsistenz (ffprobe-Stichprobe)
    if len(videos) >= 2:
        codecs = set()
        for (full, fn) in videos[:CODEC_SAMPLES_PER_SEASON]:
            c = media.get_video_codec(full)
            if c:
                codecs.add(c)
        if len(codecs) > 1:
            _add_issue(issues, "warning", "codec_inconsistency", category, season_path,
                       f"{label}: uneinheitliche Codecs in Stichprobe ({', '.join(sorted(codecs))})")

    return len(videos)


def _check_series_show(issues, category, show_path):
    files_checked = 0
    try:
        entries = os.listdir(show_path)
    except OSError:
        return 0
    entries_lower = {e.lower() for e in entries}

    # tvshow.nfo
    if "tvshow.nfo" not in entries_lower:
        _add_issue(issues, "warning", "missing_nfo", category, show_path,
                   f"{os.path.basename(show_path)}: tvshow.nfo fehlt")

    # Artwork (nur flaggen, wenn gar kein Bild vorhanden)
    if not _has_any_artwork(entries):
        _add_issue(issues, "info", "missing_artwork", category, show_path,
                   f"{os.path.basename(show_path)}: kein Artwork vorhanden")

    # Staffeln
    season_dirs = [e for e in sorted(entries)
                   if not e.startswith('.') and os.path.isdir(os.path.join(show_path, e))
                   and (e.lower().startswith("staffel ") or e.lower().startswith("season ")
                        or e.lower().startswith("specials"))]
    show_name = os.path.basename(show_path)
    for sd in season_dirs:
        files_checked += _check_season(issues, category, show_name, os.path.join(show_path, sd))

    return files_checked


def _check_movie(issues, category, movie_path):
    name = os.path.basename(movie_path)
    try:
        entries = os.listdir(movie_path)
    except OSError:
        return 0

    videos, _ = _collect_videos(movie_path)
    # Für Filme: irgendeine .nfo im Ordnerbaum (movie.nfo / <name>.nfo)
    has_nfo = False
    for dirpath, _dirs, filenames in os.walk(movie_path):
        if any(f.lower().endswith('.nfo') for f in filenames):
            has_nfo = True
            break

    if not videos:
        _add_issue(issues, "info", "empty_folder", category, movie_path,
                   f"{name}: keine Videodatei im Ordner")
        return 0

    if not has_nfo:
        _add_issue(issues, "warning", "missing_nfo", category, movie_path,
                   f"{name}: keine NFO vorhanden")

    # Artwork (nur flaggen, wenn gar kein Bild vorhanden)
    if not _has_any_artwork(entries):
        _add_issue(issues, "info", "missing_artwork", category, movie_path,
                   f"{name}: kein Artwork vorhanden")

    # Kleine Dateien
    small = []
    for (full, fn) in videos:
        try:
            if os.path.getsize(full) < SMALL_FILE_BYTES:
                small.append(fn)
        except OSError:
            pass
    if small:
        _add_issue(issues, "warning", "small_file", category, movie_path,
                   f"{name}: {len(small)} verdächtig kleine Videodatei(en) (< 50 MB)")

    return len(videos)


# ---------------------------------------------------------------------------
# Scan-Steuerung
# ---------------------------------------------------------------------------
def _run_health_scan():
    issues = []
    files_checked = 0
    try:
        if not ensure_nas_mounted():
            _set_state(status="error", message="NAS konnte nicht gemountet werden.",
                       error="nas_unavailable", finished_at=time.time())
            log_message("❌ [Health-Scan] NAS nicht verfügbar.")
            return

        settings = utils.load_settings()
        shows = list(walk_nas_categories(settings))
        total = len(shows)
        log_message(f"🔍 [Health-Scan] Starte Prüfung von {total} Ordnern...")

        for idx, show in enumerate(shows):
            _set_state(
                progress=int((idx / total) * 100) if total else 100,
                message=f"Prüfe {show['category']}: {show['name']} ({idx + 1}/{total})",
                scanned={"shows": idx, "files": files_checked},
            )
            if show["type"] == "series":
                files_checked += _check_series_show(issues, show["category"], show["path"])
            else:
                files_checked += _check_movie(issues, show["category"], show["path"])

            if (idx + 1) % 25 == 0:
                log_message(f"🔍 [Health-Scan] {idx + 1}/{total} Ordner geprüft, "
                            f"{len(issues)} Auffälligkeiten bisher...")

        summary = {"critical": 0, "warning": 0, "info": 0}
        for it in issues:
            summary[it["severity"]] = summary.get(it["severity"], 0) + 1

        result = {
            "status": "done",
            "progress": 100,
            "message": f"Scan abgeschlossen: {len(issues)} Auffälligkeiten in {total} Ordnern.",
            "finished_at": time.time(),
            "issues": issues,
            "summary": summary,
            "scanned": {"shows": total, "files": files_checked},
            "error": None,
        }
        _set_state(**result)
        _write_cache()
        log_message(f"✅ [Health-Scan] Fertig: {summary['critical']} kritisch, "
                    f"{summary['warning']} Warnungen, {summary['info']} Hinweise.")

    except Exception as e:
        import traceback
        traceback.print_exc()
        _set_state(status="error", message=f"Fehler beim Scan: {e}",
                   error=str(e), finished_at=time.time())
        log_message(f"❌ [Health-Scan] Fehler: {e}")


def start_health_scan():
    """Startet den Scan im Hintergrund. Gibt False zurück, wenn bereits einer läuft."""
    with _state_lock:
        if _scan_state["status"] == "running":
            return False
        _scan_state.update({
            "status": "running",
            "progress": 0,
            "message": "Scan wird gestartet...",
            "started_at": time.time(),
            "finished_at": None,
            "issues": [],
            "summary": {"critical": 0, "warning": 0, "info": 0},
            "scanned": {"shows": 0, "files": 0},
            "error": None,
        })
    threading.Thread(target=_run_health_scan, daemon=True).start()
    return True


def get_health_status():
    """Liefert den aktuellen State. Lädt bei idle ein evtl. vorhandenes Cache-Ergebnis."""
    with _state_lock:
        if _scan_state["status"] == "idle":
            cached = _read_cache()
            if cached:
                return cached
        import copy
        return copy.deepcopy(_scan_state)


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
        log_message(f"⚠️ [Health-Scan] Cache konnte nicht geschrieben werden: {e}")


def _read_cache():
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return None
