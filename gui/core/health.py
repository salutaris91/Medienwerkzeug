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
from gui.core import artwork_validators

# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------
VIDEO_EXTENSIONS = {'.mkv', '.mp4', '.avi', '.m4v', '.ts', '.mov', '.wmv'}
SMALL_FILE_BYTES = 50 * 1024 * 1024          # < 50 MB gilt als verdächtig klein
CODEC_SAMPLES_PER_SEASON = 3                 # max. ffprobe-Aufrufe pro Staffel
EFFICIENT_CODECS = {'hevc', 'h265', 'av1', 'vp9'}

CACHE_FILE = os.path.join(utils.DATA_DIR, "health_scan_cache.json")

SXXEXX_RE = re.compile(r'[Ss](\d{1,3})[Ee](\d{1,4})')
SHORT_NAME_RE = re.compile(r'^[A-Z0-9]{6}~[A-Z0-9]$')
YEAR_RE = re.compile(r'(19|20)\d{2}')

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
        # Stabiler Schlüssel zum dauerhaften Ignorieren (typ + pfad, ohne wechselnde Texte)
        "key": f"health:{issue_type}:{path}",
    })


def _dir_has_video(directory):
    """True, wenn unterhalb von 'directory' eine (nicht versteckte) Videodatei liegt."""
    for dirpath, _dirs, filenames in os.walk(directory):
        for f in filenames:
            if not f.startswith('.') and os.path.splitext(f)[1].lower() in VIDEO_EXTENSIONS:
                return True
    return False


def _is_genre_container(path):
    """True, wenn 'path' ein Genre-Sammelordner ist (z. B. Filme/Action): kein Jahr im
    Namen, kein eigenes Video, aber mind. ein Film-Unterordner mit Video. Dann sind die
    Unterordner die eigentlichen Filme und sollten einzeln geprüft werden."""
    name = os.path.basename(path)
    if re.search(r'(19|20)\d{2}', name):
        return False  # Jahr im Namen -> Film, kein Genre-Ordner
    try:
        entries = [e for e in os.listdir(path) if not e.startswith('.')]
    except OSError:
        return False
    if any(os.path.splitext(e)[1].lower() in VIDEO_EXTENSIONS for e in entries):
        return False  # eigenes Video -> Film
    subdirs = [e for e in entries if os.path.isdir(os.path.join(path, e))]
    return any(_dir_has_video(os.path.join(path, sd)) for sd in subdirs)


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


def _has_any_artwork(path):
    """True, wenn irgendwo unterhalb von 'path' mindestens eine Bilddatei liegt.

    Rekursiv (wie _collect_videos), weil Artwork je nach Struktur eine Ebene
    tiefer liegen kann (z. B. bei doppelt verschachtelten Filmordnern
    Filme/<Film>/<Film>/<Dateien>). Versteckte Dateien werden ignoriert.

    Die Bibliothek nutzt unterschiedliche Konventionen (poster/fanart/banner/
    clearlogo/discart ...). Wir flaggen daher nur Ordner ganz OHNE Artwork.
    """
    for dirpath, _dirs, filenames in os.walk(path):
        for f in filenames:
            if not f.startswith('.') and os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS:
                return True
    return False


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


def _get_provider_from_nfo(nfo_path):
    if not os.path.exists(nfo_path):
        return None
    try:
        with open(nfo_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            m = re.search(r'<mw_provider>(.*?)</mw_provider>', content)
            if m:
                return m.group(1).strip()
    except Exception:
        pass
    return None


def _check_season(issues, category, show_name, season_path, validator):
    """Prüft einen einzelnen Staffel-Ordner (rekursiv). Gibt geprüfte Dateien zurück."""
    # Showname voranstellen, damit das Issue auf einen Blick zuordenbar ist
    label = f"{show_name} · {os.path.basename(season_path)}"
    videos, nfo_basenames = _collect_videos(season_path)

    try:
        child_dirs = [e for e in sorted(os.listdir(season_path))
                      if not e.startswith('.') and os.path.isdir(os.path.join(season_path, e))]
    except OSError:
        child_dirs = []

    # Wirklich leerer Ordner (kein Video, keine Episoden-Unterordner)
    if not videos and not child_dirs:
        _add_issue(issues, "info", "empty_folder", category, season_path,
                   f"{label}: keine Videodateien")
        return 0

    # Episoden-Unterordner ohne fertiges Video erkennen (z. B. abgebrochener Download:
    # nur versteckte Temp-Datei + Untertitel/Thumbnail, aber kein .mkv/.mp4).
    for d in child_dirs:
        if not SXXEXX_RE.search(d):
            continue  # nur echte Episoden-Ordner (mit SxxExx im Namen)
        dpath = os.path.join(season_path, d)
        if not _dir_has_video(dpath):
            _add_issue(issues, "warning", "no_video", category, dpath,
                       f"{show_name} · {d}: kein Video im Ordner (unvollständiger Download?)")

    # Fehlende Episoden-NFOs (gleicher Basisname im selben Ordner)
    missing_nfo = [fn for (full, fn) in videos if os.path.splitext(full)[0] not in nfo_basenames]
    if missing_nfo:
        _add_issue(issues, "warning", "missing_nfo", category, season_path,
                   f"{label}: {len(missing_nfo)} von {len(videos)} Episoden ohne NFO")

    # Episodenlücken: Nummern aus Dateinamen UND Ordnernamen (ein Ordner kann existieren,
    # auch wenn das Video noch fehlt -> sonst falsche "Episode fehlt"-Meldungen).
    ep_nums = set(_episode_numbers(fn for (full, fn) in videos))
    ep_nums |= set(_episode_numbers(child_dirs))
    nums = sorted(ep_nums)
    if len(nums) >= 2:
        full_range = set(range(nums[0], nums[-1] + 1))
        missing = sorted(full_range - ep_nums)
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

    # Season poster check
    season_folder = os.path.basename(season_path).lower()
    season_num = 1
    if "specials" in season_folder:
        season_num = 0
    else:
        m = re.search(r'\d+', season_folder)
        if m:
            season_num = int(m.group(0))

    show_path = os.path.dirname(season_path)
    has_season_poster = False
    for name in validator.get_season_poster_names(season_num):
        full_path = os.path.join(show_path, name)
        if os.path.exists(full_path):
            has_season_poster = True
            break
        fn = os.path.basename(name)
        if os.path.exists(os.path.join(season_path, fn)):
            has_season_poster = True
            break

    if not has_season_poster:
        _add_issue(issues, "warning", "missing_season_poster", category, season_path,
                   f"{label}: Season-Poster fehlt")

    return len(videos)


def _normalize_for_consistency_check(name):
    if not name:
        return ""
    name = name.lower()
    name = re.sub(r'\(\d{4}\)', '', name)
    name = re.sub(r'\[.*?\]', '', name)
    name = re.sub(r'\(.*?\)', '', name)
    name = name.replace("&", "und")
    return re.sub(r'[^a-z0-9]', '', name).strip()


def _check_series_show(issues, category, show_path, validator):
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

    # Fetch provider from tvshow.nfo if it exists
    provider = _get_provider_from_nfo(os.path.join(show_path, "tvshow.nfo"))
    show_dir_name = os.path.basename(show_path)

    # 1. Poster check
    has_poster = False
    for name in validator.get_series_poster_names():
        if os.path.exists(os.path.join(show_path, name)):
            has_poster = True
            break
    if not has_poster:
        _add_issue(issues, "warning", "missing_poster", category, show_path,
                   f"{show_dir_name}: Serienposter fehlt")

    # 2. Fanart/Backdrop check
    has_backdrop = False
    for name in validator.get_series_backdrop_names():
        if os.path.exists(os.path.join(show_path, name)):
            has_backdrop = True
            break
    if not has_backdrop:
        _add_issue(issues, "warning", "missing_backdrop", category, show_path,
                   f"{show_dir_name}: Hintergrundbild (Fanart) fehlt")

    # 3. Logo check
    if validator.supports_logos:
        has_logo = False
        for name in validator.get_series_logo_names():
            if os.path.exists(os.path.join(show_path, name)):
                has_logo = True
                break
        if not has_logo:
            severity = "info"
            msg = f"{show_dir_name}: ClearLogo fehlt"
            if provider in ("mediathek", "ytdlp", "manual"):
                msg += f" (Metadatendienst '{provider}' unterstützt keine Logos)"
            _add_issue(issues, severity, "missing_logo", category, show_path, msg)

    # 4. Banner check
    if validator.supports_banners:
        has_banner = False
        for name in validator.get_series_banner_names():
            if os.path.exists(os.path.join(show_path, name)):
                has_banner = True
                break
        if not has_banner:
            severity = "info"
            msg = f"{show_dir_name}: Banner fehlt"
            if provider in ("mediathek", "ytdlp", "manual"):
                msg += f" (Metadatendienst '{provider}' unterstützt keine Banner)"
            _add_issue(issues, severity, "missing_banner", category, show_path, msg)

    # Staffeln
    season_dirs = [e for e in sorted(entries)
                   if not e.startswith('.') and os.path.isdir(os.path.join(show_path, e))
                   and (e.lower().startswith("staffel ") or e.lower().startswith("season ")
                        or e.lower().startswith("specials"))]
    show_name = os.path.basename(show_path)

    # Collect all video files to check naming consistency
    all_videos = []
    for sd in season_dirs:
        videos, _ = _collect_videos(os.path.join(show_path, sd))
        all_videos.extend(videos)

    prefixes = {}
    for full_path, filename in all_videos:
        m = SXXEXX_RE.search(filename)
        if m:
            prefix = filename[:m.start()].strip(" -_")
            if prefix:
                norm = _normalize_for_consistency_check(prefix)
                if norm not in prefixes:
                    prefixes[norm] = prefix

    if len(prefixes) > 1:
        prefix_list = sorted(list(prefixes.values()))
        _add_issue(issues, "warning", "inconsistent_naming", category, show_path,
                   f"{show_name}: Uneinheitliche Benennung der Episodendateien (z. B. '{prefix_list[0]}' vs. '{prefix_list[1]}')")
    elif len(prefixes) == 1:
        prefix_val = list(prefixes.values())[0]
        norm_prefix = list(prefixes.keys())[0]
        norm_folder = _normalize_for_consistency_check(show_name)
        if norm_prefix != norm_folder:
            _add_issue(issues, "warning", "inconsistent_naming", category, show_path,
                       f"{show_name}: Episodendateien verwenden einen anderen Seriennamen ('{prefix_val}') als der Hauptordner")

    for sd in season_dirs:
        files_checked += _check_season(issues, category, show_name, os.path.join(show_path, sd), validator)

    return files_checked


def _check_movie(issues, category, movie_path, validator):
    name = os.path.basename(movie_path)
    try:
        entries = [e for e in os.listdir(movie_path) if not e.startswith('.')]
    except OSError:
        return 0

    # --- Check: Doppelte Verschachtelung (Ordner/Ordner/video.mkv) ---
    subdirs = [e for e in entries if os.path.isdir(os.path.join(movie_path, e))]
    non_hidden_files = [e for e in entries if os.path.isfile(os.path.join(movie_path, e))]
    if len(subdirs) == 1 and not non_hidden_files:
        inner = subdirs[0]
        inner_norm = inner.lower().rstrip('. ')
        name_norm = name.lower().rstrip('. ')
        if inner_norm == name_norm:
            _add_issue(issues, "warning", "nested_duplicate", category, movie_path,
                       f"{name}: doppelt verschachtelter Ordner ({name}/{inner}/…)")

    # --- Check: Schlechter Ordnername (kein Jahr oder kryptischer 8.3-Kurzname) ---
    if SHORT_NAME_RE.match(name):
        _add_issue(issues, "warning", "bad_folder_name", category, movie_path,
                   f"{name}: kryptischer Kurzname (8.3-Format) – sollte umbenannt werden")
    elif not YEAR_RE.search(name):
        _add_issue(issues, "warning", "bad_folder_name", category, movie_path,
                   f"{name}: kein Jahr im Ordnernamen – erschwert die Zuordnung")

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

    # --- Check: Name-Mismatch (Ordnername ≠ Videodateiname) ---
    if len(videos) == 1:
        video_full, video_fn = videos[0]
        video_stem = os.path.splitext(video_fn)[0]
        folder_norm = name.lower().rstrip('. ')
        video_norm = video_stem.lower().rstrip('. ')
        if folder_norm != video_norm:
            _add_issue(issues, "warning", "name_mismatch", category, movie_path,
                       f"{name}: Ordnername „{name}“ passt nicht zu Dateiname „{video_stem}“")

    if not has_nfo:
        _add_issue(issues, "warning", "missing_nfo", category, movie_path,
                   f"{name}: keine NFO vorhanden")

    # Artwork checks using validator
    video_filename = videos[0][1] if videos else f"{name}.mkv"
    video_stem = os.path.splitext(video_filename)[0]
    provider = _get_provider_from_nfo(os.path.join(movie_path, f"{video_stem}.nfo"))

    # 1. Poster check
    has_poster = False
    for p_name in validator.get_movie_poster_names(video_filename):
        if os.path.exists(os.path.join(movie_path, p_name)):
            has_poster = True
            break
    if not has_poster:
        _add_issue(issues, "warning", "missing_poster", category, movie_path,
                   f"{name}: Filmplakat (Poster) fehlt")

    # 2. Fanart/Backdrop check
    has_backdrop = False
    for b_name in validator.get_movie_backdrop_names(video_filename):
        if os.path.exists(os.path.join(movie_path, b_name)):
            has_backdrop = True
            break
    if not has_backdrop:
        _add_issue(issues, "warning", "missing_backdrop", category, movie_path,
                   f"{name}: Hintergrundbild (Fanart) fehlt")

    # 3. Logo check
    if validator.supports_logos:
        has_logo = False
        for l_name in validator.get_movie_logo_names(video_filename):
            if os.path.exists(os.path.join(movie_path, l_name)):
                has_logo = True
                break
        if not has_logo:
            severity = "info"
            msg = f"{name}: ClearLogo fehlt"
            if provider in ("mediathek", "ytdlp", "manual"):
                msg += f" (Metadatendienst '{provider}' unterstützt keine Logos)"
            _add_issue(issues, severity, "missing_logo", category, movie_path, msg)

    # 4. Banner check
    if validator.supports_banners:
        has_banner = False
        for bn_name in validator.get_movie_banner_names(video_filename):
            if os.path.exists(os.path.join(movie_path, bn_name)):
                has_banner = True
                break
        if not has_banner:
            severity = "info"
            msg = f"{name}: Banner fehlt"
            if provider in ("mediathek", "ytdlp", "manual"):
                msg += f" (Metadatendienst '{provider}' unterstützt keine Banner)"
            _add_issue(issues, severity, "missing_banner", category, movie_path, msg)

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
        server_type = settings.get("media_server", "emby")
        validator = artwork_validators.get_validator(server_type)
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
                files_checked += _check_series_show(issues, show["category"], show["path"], validator)
            elif _is_genre_container(show["path"]):
                # Genre-Sammelordner (z. B. Filme/Action): nicht selbst als Film prüfen,
                # sondern die enthaltenen Film-Unterordner einzeln.
                try:
                    subdirs = sorted(e for e in os.listdir(show["path"]) if not e.startswith('.'))
                except OSError:
                    subdirs = []
                for sd in subdirs:
                    sp = os.path.join(show["path"], sd)
                    if os.path.isdir(sp):
                        files_checked += _check_movie(issues, show["category"], sp, validator)
            else:
                files_checked += _check_movie(issues, show["category"], show["path"], validator)

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


def _apply_ignores(result):
    """Filtert ignorierte Issues heraus, berechnet Summary neu und ergänzt ignored_count."""
    from gui.core import ignores
    ignored_keys = ignores.get_ignored()
    issues = result.get("issues", []) or []
    kept = [i for i in issues if i.get("key") not in ignored_keys]
    ignored_count = len(issues) - len(kept)
    summary = {"critical": 0, "warning": 0, "info": 0}
    for i in kept:
        summary[i.get("severity", "info")] = summary.get(i.get("severity", "info"), 0) + 1
    result["issues"] = kept
    result["summary"] = summary
    result["ignored_count"] = ignored_count
    return result


def get_health_status():
    """Liefert den aktuellen State (ignorierte Befunde herausgefiltert).
    Lädt bei idle ein evtl. vorhandenes Cache-Ergebnis."""
    import copy
    with _state_lock:
        if _scan_state["status"] == "idle":
            cached = _read_cache()
            if cached:
                return _apply_ignores(cached)
        snapshot = copy.deepcopy(_scan_state)
    return _apply_ignores(snapshot)


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
