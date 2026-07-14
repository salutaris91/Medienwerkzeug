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
from typing import Optional

from gui.core import utils
from gui.core import media
from gui.core.transfers import ensure_nas_mounted, walk_nas_categories
from gui.core.helpers import log_message, parse_fsk_status, get_category_media_type, is_season_folder_name
from gui.core import artwork_validators
from gui.core import health_cache

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
_cancel_event = threading.Event()
_scan_state = {
    "status": "idle",       # idle | running | done | error | cancelled
    "progress": 0,
    "message": "",
    "started_at": None,
    "finished_at": None,
    "issues": [],
    "summary": {"critical": 0, "warning": 0, "info": 0},
    "scanned": {"shows": 0, "files": 0},
    "stats": {"cache_hits": 0, "cache_miss_modified": 0, "cache_miss_known_issues": 0, "cache_miss_new": 0},
    "error": None,
    "media_server_skipped": False,
    "media_structure": {"series": [], "movies": []},
}


def _set_state(**kwargs):
    with _state_lock:
        _scan_state.update(kwargs)


def _add_issue(issues, severity, issue_type, category, path, message, **kwargs):
    issue = {
        "severity": severity,
        "type": issue_type,
        "category": category,
        "path": path,
        "message": message,
        # Stabiler Schlüssel zum dauerhaften Ignorieren (typ + pfad, ohne wechselnde Texte)
        "key": f"health:{issue_type}:{path}",
    }
    issue.update(kwargs)
    issues.append(issue)


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

            # Fallbacks
            if '<tmdbid>' in content:
                if 'tvshow.nfo' in nfo_path.lower():
                    return 'tmdb_tv'
                try:
                    import xml.etree.ElementTree as ET
                    root = ET.fromstring(content)
                    if root.tag == 'movie':
                        return 'tmdb_movie'
                    elif root.tag == 'tvshow':
                        return 'tmdb_tv'
                except Exception:
                    pass
                return 'tmdb_movie'

            if '<tvdbid>' in content:
                return 'tvdb'
    except Exception as e:
        log_message(f"⚠️ [Bibliothek-Check] NFO nicht lesbar: {nfo_path} ({e})")
    return None


def check_nfo_incomplete(nfo_path, nfo_type="episode"):
    """
    Check if an NFO file is incomplete (e.g. missing title or plot).
    Returns (is_incomplete, severity, reason)
    """
    if not os.path.exists(nfo_path):
        return False, None, None
    try:
        import xml.etree.ElementTree as ET
        tree = ET.parse(nfo_path)
        root = tree.getroot()

        title_el = root.find("title")
        plot_el = root.find("plot")

        title_missing = title_el is None or not title_el.text or not title_el.text.strip()
        plot_missing = plot_el is None or not plot_el.text or not plot_el.text.strip()

        if title_missing or plot_missing:
            missing_fields = []
            if title_missing: missing_fields.append("Titel")
            if plot_missing: missing_fields.append("Plot")
            return True, "critical", f"NFO unvollständig (fehlende Felder: {', '.join(missing_fields)})"

        # Optional warnings
        if nfo_type == "episode":
            aired_el = root.find("aired")
            aired_missing = aired_el is None or not aired_el.text or not aired_el.text.strip()
            if aired_missing:
                return True, "warning", "NFO unvollständig (fehlendes Feld: Ausstrahlungsdatum)"
        elif nfo_type in ("tvshow", "movie"):
            year_el = root.find("year")
            year_missing = year_el is None or not year_el.text or not year_el.text.strip()
            if year_missing:
                return True, "warning", "NFO unvollständig (fehlendes Feld: Produktionsjahr)"

    except Exception as e:
        return True, "critical", f"NFO beschädigt oder unlesbar: {str(e)}"

    return False, None, None


def should_overwrite_nfo(overwrite_nfo, overrides, nfo_path, nfo_type):
    """
    Determine if an NFO file should be overwritten.
    """
    if not overwrite_nfo:
        return False
    if overrides:
        return True
    if not os.path.exists(nfo_path):
        return True
    is_inc, _, _ = check_nfo_incomplete(nfo_path, nfo_type)
    return is_inc


def find_primary_nfo(folder_path, is_movie=False):
    """Sucht die primäre NFO-Datei für einen Ordner (Filme oder Serien).
    Gibt bei mehrdeutigen Zuordnungen None zurück."""
    if not os.path.isdir(folder_path):
        return None
    try:
        entries = os.listdir(folder_path)
    except OSError as e:
        log_message(f"⚠️ [Bibliothek-Check] Ordner nicht lesbar: {folder_path} ({e})")
        return None

    if not is_movie:
        for e in entries:
            if e.lower() == "tvshow.nfo":
                return os.path.join(folder_path, e)
        return None

    # Für Filme
    nfos = [e for e in entries if not e.startswith('.') and e.lower().endswith('.nfo')]
    if len(nfos) == 0:
        return None

    video_extensions = {'.mkv', '.mp4', '.avi', '.m4v', '.ts', '.mov', '.wmv', '.webm', '.m2ts'}
    videos = [e for e in entries if not e.startswith('.') and os.path.splitext(e)[1].lower() in video_extensions]

    expected_nfo = None
    if len(videos) == 1:
        video_stem = os.path.splitext(videos[0])[0]
        expected_nfo = f"{video_stem}.nfo"

    # Prio 1: <videostem>.nfo
    if expected_nfo:
        for nfo in nfos:
            if nfo == expected_nfo:
                return os.path.join(folder_path, nfo)

    # Prio 2: movie.nfo
    for nfo in nfos:
        if nfo.lower() == "movie.nfo":
            return os.path.join(folder_path, nfo)

    # Im Zweifel bei unsicheren NFOs: None (nichts ändern)
    return None


def _check_fsk(issues, category, folder_path, nfo_path, **kwargs):
    if not nfo_path or not os.path.exists(nfo_path):
        return

    try:
        with open(nfo_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        m = re.search(r'<mpaa>(.*?)</mpaa>', content)
        if not m:
            _add_issue(issues, "warning", "missing_age_rating", category, folder_path,
                       f"{os.path.basename(folder_path)}: Altersfreigabe (FSK) fehlt in der NFO", **kwargs)
            return

        val = m.group(1).strip()
        if not val:
            _add_issue(issues, "warning", "missing_age_rating", category, folder_path,
                       f"{os.path.basename(folder_path)}: Altersfreigabe (FSK) ist leer in der NFO", **kwargs)
            return

        # Gültige Werte prüfen
        valid_values = {"FSK 0", "FSK 6", "FSK 12", "FSK 16", "FSK 18"}
        if val not in valid_values:
            _add_issue(issues, "info", "invalid_age_rating", category, folder_path,
                       f"{os.path.basename(folder_path)}: Ungültige Altersfreigabe in NFO ({val})", **kwargs)

    except Exception as e:
        log_message(f"⚠️ [Bibliothek-Check] FSK-Prüfung fehlgeschlagen für {nfo_path}: {e}")


def _get_fsk_info(nfo_path):
    return parse_fsk_status(nfo_path)


def _find_issue_keys_for_episode(issues, season_path, ep_video_filename, ep_nfo_path):
    keys = []
    abs_nfo_path = os.path.realpath(ep_nfo_path)
    abs_season_path = os.path.realpath(season_path)
    for it in issues:
        it_path = os.path.realpath(it.get("path"))
        if it_path == abs_nfo_path:
            keys.append(it["key"])
        elif it_path == abs_season_path:
            msg = it.get("message", "")
            if ep_video_filename in msg or os.path.basename(ep_nfo_path) in msg:
                keys.append(it["key"])
    return keys


def _find_issue_keys_for_movie(issues, movie_path, movie_nfo_path):
    keys = []
    abs_movie_path = os.path.realpath(movie_path)
    abs_nfo_path = os.path.realpath(movie_nfo_path) if movie_nfo_path else None
    for it in issues:
        it_path = os.path.realpath(it.get("path"))
        if it_path == abs_movie_path or (abs_nfo_path and it_path == abs_nfo_path):
            keys.append(it["key"])
    return keys


def _find_issue_keys_for_series(issues, show_path, show_nfo_path):
    keys = []
    abs_show_path = os.path.realpath(show_path)
    abs_nfo_path = os.path.realpath(show_nfo_path) if show_nfo_path else None
    for it in issues:
        it_path = os.path.realpath(it.get("path"))
        if it_path == abs_show_path or (abs_nfo_path and it_path == abs_nfo_path):
            keys.append(it["key"])
    return keys


def _find_issue_keys_for_season(issues, season_path):
    """Return findings that belong to the season folder itself."""
    abs_season_path = os.path.realpath(season_path)
    return [
        item["key"]
        for item in issues
        if os.path.realpath(item.get("path")) == abs_season_path
    ]


def _check_season(issues, category, show_name, season_path, validator):
    """Prüft einen einzelnen Staffel-Ordner (rekursiv). Gibt geprüfte Dateien zurück."""
    # Showname voranstellen, damit das Issue auf einen Blick zuordenbar ist
    label = f"{show_name} · {os.path.basename(season_path)}"
    videos, nfo_basenames = _collect_videos(season_path)

    try:
        child_dirs = [e for e in sorted(os.listdir(season_path))
                      if not e.startswith('.') and os.path.isdir(os.path.join(season_path, e))]
    except OSError as e:
        log_message(f"⚠️ [Bibliothek-Check] Staffel-Ordner nicht lesbar: {season_path} ({e})")
        child_dirs = []

    # Wirklich leerer Ordner (kein Video, keine Episoden-Unterordner)
    if not videos and not child_dirs:
        _add_issue(issues, "info", "empty_folder", category, season_path,
                   f"{label}: keine Videodateien", media_kind="season", agent_path=season_path)
        return 0, {"name": os.path.basename(season_path), "path": season_path, "episodes": []}

    # Episoden-Unterordner ohne fertiges Video erkennen (z. B. abgebrochener Download:
    # nur versteckte Temp-Datei + Untertitel/Thumbnail, aber kein .mkv/.mp4).
    for d in child_dirs:
        if not SXXEXX_RE.search(d):
            continue  # nur echte Episoden-Ordner (mit SxxExx im Namen)
        dpath = os.path.join(season_path, d)
        if not _dir_has_video(dpath):
            _add_issue(issues, "warning", "no_video", category, dpath,
                       f"{show_name} · {d}: kein Video im Ordner (unvollständiger Download?)", media_kind="episode", agent_path=season_path)

    # Fehlende Episoden-NFOs (gleicher Basisname im selben Ordner)
    missing_nfo = [(full, fn) for (full, fn) in videos if os.path.splitext(full)[0] not in nfo_basenames]
    for full, fn in missing_nfo:
        expected_nfo_path = os.path.splitext(full)[0] + ".nfo"
        _add_issue(
            issues,
            "warning",
            "missing_nfo",
            category,
            expected_nfo_path,
            f"{show_name} · {fn}: Episoden-NFO fehlt",
            media_kind="episode",
            agent_path=season_path,
        )

    # Check if existing episode NFOs are incomplete
    for full, fn in videos:
        ep_nfo_path = os.path.splitext(full)[0] + ".nfo"
        if os.path.exists(ep_nfo_path):
            is_inc, sev, reason = check_nfo_incomplete(ep_nfo_path, "episode")
            if is_inc:
                _add_issue(issues, sev, "incomplete_nfo", category, season_path,
                           f"{show_name} · {fn}: {reason}", media_kind="episode", agent_path=season_path)

            # FSK-Check für Episode (dateibasiert über den NFO-Pfad)
            series_path = os.path.dirname(season_path)
            season_name = os.path.basename(season_path)
            ep_label = f"{show_name} · {season_name} · {fn}"
            _check_fsk(
                issues,
                category,
                folder_path=ep_nfo_path,  # Eindeutiger Identifizierer für das Issue
                nfo_path=ep_nfo_path,
                scope_kind="episode",
                series_path=series_path,
                season_path=season_path,
                label=ep_label
            )

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
                       f"{label}: Episodenlücke ({preview})", media_kind="season", agent_path=season_path)

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
                   f"{label}: {len(small)} verdächtig kleine Videodatei(en) (< 50 MB)", media_kind="episode", agent_path=season_path)

    # Codec-Inkonsistenz (ffprobe-Stichprobe)
    if len(videos) >= 2:
        codecs = set()
        for (full, fn) in videos[:CODEC_SAMPLES_PER_SEASON]:
            c = media.get_video_codec(full)
            if c:
                codecs.add(c)
        if len(codecs) > 1:
            _add_issue(issues, "warning", "codec_inconsistency", category, season_path,
                       f"{label}: uneinheitliche Codecs in Stichprobe ({', '.join(sorted(codecs))})", media_kind="season", agent_path=season_path)

    # Season poster check
    if validator is not None:
        season_folder = os.path.basename(season_path).lower()
        season_num = 1
        if "specials" in season_folder:
            season_num = 0
        else:
            m = re.search(r'\d+', season_folder)
            if m:
                season_num = int(m.group(0))

        show_path = os.path.dirname(season_path)
        has_season_poster = validator.has_artwork_file(show_path, validator.get_season_poster_names(season_num))
        if not has_season_poster:
            preferred = validator.get_preferred_season_poster_name(season_num)
            _add_issue(issues, "warning", "missing_season_poster", category, season_path,
                       f"{label}: Season-Poster fehlt — ggf. manuell als '{preferred}' im Serienordner ablegen", media_kind="season", agent_path=season_path)

    # Episoden-Struktur sammeln
    season_episodes = []
    for full, fn in videos:
        ep_nfo_path = os.path.splitext(full)[0] + ".nfo"
        ep_fsk_status, ep_current_fsk, ep_raw_fsk, ep_actionable_fsk = _get_fsk_info(ep_nfo_path)
        ep_issue_keys = _find_issue_keys_for_episode(issues, season_path, fn, ep_nfo_path)
        season_episodes.append({
            "name": fn,
            "path": ep_nfo_path,
            "nfo_path": ep_nfo_path,
            "fsk_status": ep_fsk_status,
            "current_fsk": ep_current_fsk,
            "raw_fsk": ep_raw_fsk,
            "actionable_fsk": ep_actionable_fsk,
            "issue_keys": ep_issue_keys
        })

    season_metadata = {
        "name": os.path.basename(season_path),
        "path": season_path,
        "issue_keys": _find_issue_keys_for_season(issues, season_path),
        "episodes": sorted(season_episodes, key=lambda e: e["name"])
    }

    return len(videos), season_metadata


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
    except OSError as e:
        log_message(f"⚠️ [Bibliothek-Check] Serien-Ordner nicht lesbar: {show_path} ({e})")
        return 0, {
            "name": os.path.basename(show_path),
            "path": show_path,
            "nfo_path": None,
            "has_nfo": False,
            "fsk_status": "nfo_missing",
            "current_fsk": "Keine",
            "raw_fsk": None,
            "actionable_fsk": True,
            "seasons": []
        }
    entries_lower = {e.lower() for e in entries}

    # tvshow.nfo
    if "tvshow.nfo" not in entries_lower:
        _add_issue(issues, "warning", "missing_nfo", category, show_path,
                   f"{os.path.basename(show_path)}: tvshow.nfo fehlt", media_kind="series", agent_path=show_path)
    else:
        nfo_path = find_primary_nfo(show_path, is_movie=False)
        _check_fsk(issues, category, show_path, nfo_path)
        if nfo_path:
            is_inc, sev, reason = check_nfo_incomplete(nfo_path, "tvshow")
            if is_inc:
                _add_issue(issues, sev, "incomplete_nfo", category, show_path,
                           f"{os.path.basename(show_path)}: {reason}", media_kind="series", agent_path=show_path)

    # Fetch provider from tvshow.nfo if it exists
    provider = _get_provider_from_nfo(os.path.join(show_path, "tvshow.nfo"))
    show_dir_name = os.path.basename(show_path)

    if validator is not None:
        # 1. Poster check
        has_poster = validator.has_artwork_file(show_path, validator.get_series_poster_names())
        if not has_poster:
            preferred = validator.get_preferred_series_poster_name()
            _add_issue(issues, "warning", "missing_poster", category, show_path,
                       f"{show_dir_name}: Serienposter fehlt — ggf. manuell als '{preferred}' ablegen", media_kind="series", agent_path=show_path)

        # 2. Fanart/Backdrop check
        has_backdrop = validator.has_artwork_file(show_path, validator.get_series_backdrop_names())
        if not has_backdrop:
            preferred = validator.get_preferred_series_backdrop_name()
            _add_issue(issues, "warning", "missing_backdrop", category, show_path,
                       f"{show_dir_name}: Hintergrundbild fehlt — ggf. manuell als '{preferred}' ablegen", media_kind="series", agent_path=show_path)

        # 3. Logo check
        if validator.supports_logos:
            has_logo = validator.has_artwork_file(show_path, validator.get_series_logo_names())
            if not has_logo:
                preferred = validator.get_preferred_series_logo_name()
                msg = f"{show_dir_name}: ClearLogo fehlt — ggf. manuell als '{preferred}' ablegen"
                if provider in ("mediathek", "ytdlp", "manual"):
                    msg += f" (Metadatendienst '{provider}' unterstützt keine Logos)"
                _add_issue(issues, "info", "missing_logo", category, show_path, msg, media_kind="series", agent_path=show_path)

        # 4. Banner check
        if validator.supports_banners:
            has_banner = validator.has_artwork_file(show_path, validator.get_series_banner_names())
            if not has_banner:
                preferred = validator.get_preferred_series_banner_name()
                msg = f"{show_dir_name}: Banner fehlt — ggf. manuell als '{preferred}' ablegen"
                if provider in ("mediathek", "ytdlp", "manual"):
                    msg += f" (Metadatendienst '{provider}' unterstützt keine Banner)"
                _add_issue(issues, "info", "missing_banner", category, show_path, msg, media_kind="series", agent_path=show_path)

    # Staffeln
    season_dirs = [
        entry
        for entry in sorted(entries)
        if not entry.startswith('.')
        and os.path.isdir(os.path.join(show_path, entry))
        and is_season_folder_name(entry)
    ]
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
                   f"{show_name}: Uneinheitliche Benennung der Episodendateien (z. B. '{prefix_list[0]}' vs. '{prefix_list[1]}')", media_kind="series", agent_path=show_path)
    elif len(prefixes) == 1:
        prefix_val = list(prefixes.values())[0]
        norm_prefix = list(prefixes.keys())[0]
        norm_folder = _normalize_for_consistency_check(show_name)
        if norm_prefix != norm_folder:
            _add_issue(issues, "warning", "inconsistent_naming", category, show_path,
                       f"{show_name}: Episodendateien verwenden einen anderen Seriennamen ('{prefix_val}') als der Hauptordner", media_kind="series", agent_path=show_path)

    seasons_list = []
    for sd in season_dirs:
        files_in_season, season_metadata = _check_season(issues, category, show_name, os.path.join(show_path, sd), validator)
        files_checked += files_in_season
        seasons_list.append(season_metadata)

    # tvshow.nfo Altersfreigabe parsen
    show_nfo_path = find_primary_nfo(show_path, is_movie=False)
    show_fsk_status, show_current_fsk, show_raw_fsk, show_actionable_fsk = _get_fsk_info(show_nfo_path)

    show_issue_keys = _find_issue_keys_for_series(issues, show_path, show_nfo_path)

    media_metadata = {
        "name": os.path.basename(show_path),
        "path": show_path,
        "nfo_path": show_nfo_path,
        "has_nfo": show_nfo_path is not None,
        "fsk_status": show_fsk_status,
        "current_fsk": show_current_fsk,
        "raw_fsk": show_raw_fsk,
        "actionable_fsk": show_actionable_fsk,
        "issue_keys": show_issue_keys,
        "seasons": sorted(seasons_list, key=lambda s: s["name"])
    }

    return files_checked, media_metadata


def _check_movie(issues, category, movie_path, validator):
    name = os.path.basename(movie_path)
    try:
        entries = [e for e in os.listdir(movie_path) if not e.startswith('.')]
    except OSError as e:
        log_message(f"⚠️ [Bibliothek-Check] Film-Ordner nicht lesbar: {movie_path} ({e})")
        return 0, {
            "name": name,
            "path": movie_path,
            "nfo_path": None,
            "fsk_status": "nfo_missing",
            "current_fsk": "Keine",
            "raw_fsk": None,
            "actionable_fsk": True,
            "issue_keys": []
        }

    # --- Check: Doppelte Verschachtelung (Ordner/Ordner/video.mkv) ---
    subdirs = [e for e in entries if os.path.isdir(os.path.join(movie_path, e))]
    non_hidden_files = [e for e in entries if os.path.isfile(os.path.join(movie_path, e))]
    if len(subdirs) == 1 and not non_hidden_files:
        inner = subdirs[0]
        inner_norm = inner.lower().rstrip('. ')
        name_norm = name.lower().rstrip('. ')
        if inner_norm == name_norm:
            _add_issue(issues, "warning", "nested_duplicate", category, movie_path,
                       f"{name}: doppelt verschachtelter Ordner ({name}/{inner}/…)", media_kind="movie", agent_path=movie_path)

    # --- Check: Schlechter Ordnername (kein Jahr oder kryptischer 8.3-Kurzname) ---
    if SHORT_NAME_RE.match(name):
        _add_issue(issues, "warning", "bad_folder_name", category, movie_path,
                   f"{name}: kryptischer Kurzname (8.3-Format) – sollte umbenannt werden", media_kind="movie", agent_path=movie_path)
    elif not YEAR_RE.search(name):
        _add_issue(issues, "warning", "bad_folder_name", category, movie_path,
                   f"{name}: kein Jahr im Ordnernamen – erschwert die Zuordnung", media_kind="movie", agent_path=movie_path)

    videos, _ = _collect_videos(movie_path)
    # Für Filme: irgendeine .nfo im Ordnerbaum (movie.nfo / <name>.nfo)
    has_nfo = False
    for dirpath, _dirs, filenames in os.walk(movie_path):
        if any(f.lower().endswith('.nfo') for f in filenames):
            has_nfo = True
            break

    if not videos:
        _add_issue(issues, "info", "empty_folder", category, movie_path,
                   f"{name}: keine Videodatei im Ordner", media_kind="movie", agent_path=movie_path)
        movie_nfo_path = find_primary_nfo(movie_path, is_movie=True)
        m_status, m_curr, m_raw, m_action = _get_fsk_info(movie_nfo_path)
        m_keys = _find_issue_keys_for_movie(issues, movie_path, movie_nfo_path)
        return 0, {
            "name": name,
            "path": movie_path,
            "nfo_path": movie_nfo_path,
            "fsk_status": m_status,
            "current_fsk": m_curr,
            "raw_fsk": m_raw,
            "actionable_fsk": m_action,
            "issue_keys": m_keys
        }

    # --- Check: Name-Mismatch (Ordnername ≠ Videodateiname) ---
    if len(videos) == 1:
        video_full, video_fn = videos[0]
        video_stem = os.path.splitext(video_fn)[0]
        folder_norm = name.lower().rstrip('. ')
        video_norm = video_stem.lower().rstrip('. ')
        if folder_norm != video_norm:
            _add_issue(issues, "warning", "name_mismatch", category, movie_path,
                       f"{name}: Ordnername „{name}“ passt nicht zu Dateiname „{video_stem}“", media_kind="movie", agent_path=movie_path)

    if not has_nfo:
        _add_issue(issues, "warning", "missing_nfo", category, movie_path,
                   f"{name}: keine NFO vorhanden", media_kind="movie", agent_path=movie_path)
    else:
        nfo_path = find_primary_nfo(movie_path, is_movie=True)
        if nfo_path:
            _check_fsk(issues, category, movie_path, nfo_path, media_kind="movie", agent_path=movie_path)
            is_inc, sev, reason = check_nfo_incomplete(nfo_path, "movie")
            if is_inc:
                _add_issue(issues, sev, "incomplete_nfo", category, movie_path,
                           f"{name}: {reason}", media_kind="movie", agent_path=movie_path)

    if validator is not None:
        # Artwork checks using validator
        video_filename = videos[0][1] if videos else f"{name}.mkv"
        video_stem = os.path.splitext(video_filename)[0]
        provider = _get_provider_from_nfo(os.path.join(movie_path, f"{video_stem}.nfo"))

        # 1. Poster check
        has_poster = validator.has_artwork_file(movie_path, validator.get_movie_poster_names(video_filename))
        if not has_poster:
            preferred = validator.get_preferred_movie_poster_name(video_filename)
            _add_issue(issues, "warning", "missing_poster", category, movie_path,
                       f"{name}: Filmplakat (Poster) fehlt — ggf. manuell als '{preferred}' ablegen", media_kind="movie", agent_path=movie_path)

        # 2. Fanart/Backdrop check
        has_backdrop = validator.has_artwork_file(movie_path, validator.get_movie_backdrop_names(video_filename))
        if not has_backdrop:
            preferred = validator.get_preferred_movie_backdrop_name(video_filename)
            _add_issue(issues, "warning", "missing_backdrop", category, movie_path,
                       f"{name}: Hintergrundbild fehlt — ggf. manuell als '{preferred}' ablegen", media_kind="movie", agent_path=movie_path)

        # 3. Logo check
        if validator.supports_logos:
            has_logo = validator.has_artwork_file(movie_path, validator.get_movie_logo_names(video_filename))
            if not has_logo:
                preferred = validator.get_preferred_movie_logo_name(video_filename)
                msg = f"{name}: ClearLogo fehlt — ggf. manuell als '{preferred}' ablegen"
                if provider in ("mediathek", "ytdlp", "manual"):
                    msg += f" (Metadatendienst '{provider}' unterstützt keine Logos)"
                _add_issue(issues, "info", "missing_logo", category, movie_path, msg, media_kind="movie", agent_path=movie_path)

        # 4. Banner check
        if validator.supports_banners:
            has_banner = validator.has_artwork_file(movie_path, validator.get_movie_banner_names(video_filename))
            if not has_banner:
                preferred = validator.get_preferred_movie_banner_name(video_filename)
                msg = f"{name}: Banner fehlt — ggf. manuell als '{preferred}' ablegen"
                if provider in ("mediathek", "ytdlp", "manual"):
                    msg += f" (Metadatendienst '{provider}' unterstützt keine Banner)"
                _add_issue(issues, "info", "missing_banner", category, movie_path, msg, media_kind="movie", agent_path=movie_path)

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
                   f"{name}: {len(small)} verdächtig kleine Videodatei(en) (< 50 MB)", media_kind="movie", agent_path=movie_path)

    movie_nfo_path = find_primary_nfo(movie_path, is_movie=True)
    movie_fsk_status, movie_current_fsk, movie_raw_fsk, movie_actionable_fsk = _get_fsk_info(movie_nfo_path)
    movie_issue_keys = _find_issue_keys_for_movie(issues, movie_path, movie_nfo_path)

    media_metadata = {
        "name": name,
        "path": movie_path,
        "nfo_path": movie_nfo_path,
        "fsk_status": movie_fsk_status,
        "current_fsk": movie_current_fsk,
        "raw_fsk": movie_raw_fsk,
        "actionable_fsk": movie_actionable_fsk,
        "issue_keys": movie_issue_keys
    }

    return len(videos), media_metadata


def _check_movie_cached(issues, category, movie_path, validator, cache_mgr, key, deep_dive, stats):
    cached_entry = cache_mgr.get_cached_entry(movie_path, key)
    has_issues_in_cache = False
    if cached_entry:
        has_issues_in_cache = len(cached_entry.get("issues", [])) > 0

    if cached_entry and not has_issues_in_cache:
        if deep_dive:
            current_deep = cache_mgr.calculate_deep_hash(movie_path)
            cached_deep = cached_entry.get("deep_hash")
            if cached_deep == current_deep:
                issues.extend(cached_entry.get("issues", []))
                stats["cache_hits"] += 1
                return cached_entry.get("files_checked", 0), cached_entry.get("media_metadata")
            else:
                stats["cache_miss_modified"] += 1
        else:
            current_hybrid = cache_mgr.calculate_hybrid_state(movie_path, validator, is_movie=True)
            cached_hybrid = cached_entry.get("hybrid_state")
            if cached_hybrid is None and "state_data" in cached_entry and isinstance(cached_entry["state_data"], dict):
                cached_hybrid = cached_entry["state_data"]
            if cached_hybrid == current_hybrid:
                issues.extend(cached_entry.get("issues", []))
                stats["cache_hits"] += 1
                return cached_entry.get("files_checked", 0), cached_entry.get("media_metadata")
            else:
                stats["cache_miss_modified"] += 1
    elif cached_entry and has_issues_in_cache:
        stats["cache_miss_known_issues"] += 1
    else:
        stats["cache_miss_new"] += 1

    # Cache-Miss, Änderung oder bekannte Issues -> Vollständiger Scan
    temp_issues = []
    files_checked, media_metadata = _check_movie(temp_issues, category, movie_path, validator)

    if deep_dive:
        current_deep = cache_mgr.calculate_deep_hash(movie_path)
        cache_mgr.set_cached_entry(movie_path, key, temp_issues, deep_hash=current_deep, files_checked=files_checked, media_metadata=media_metadata)
    else:
        current_hybrid = cache_mgr.calculate_hybrid_state(movie_path, validator, is_movie=True)
        cache_mgr.set_cached_entry(movie_path, key, temp_issues, hybrid_state=current_hybrid, files_checked=files_checked, media_metadata=media_metadata)

    issues.extend(temp_issues)
    return files_checked, media_metadata


def _check_series_cached(issues, category, show_path, validator, cache_mgr, key, deep_dive, stats):
    cached_entry = cache_mgr.get_cached_entry(show_path, key)
    has_issues_in_cache = False
    if cached_entry:
        has_issues_in_cache = len(cached_entry.get("issues", [])) > 0

    if cached_entry and not has_issues_in_cache:
        if deep_dive:
            current_deep = cache_mgr.calculate_deep_hash(show_path)
            cached_deep = cached_entry.get("deep_hash")
            if cached_deep == current_deep:
                issues.extend(cached_entry.get("issues", []))
                stats["cache_hits"] += 1
                return cached_entry.get("files_checked", 0), cached_entry.get("media_metadata")
            else:
                stats["cache_miss_modified"] += 1
        else:
            current_hybrid = cache_mgr.calculate_hybrid_state(show_path, validator, is_movie=False)
            cached_hybrid = cached_entry.get("hybrid_state")
            if cached_hybrid is None and "state_data" in cached_entry and isinstance(cached_entry["state_data"], dict):
                cached_hybrid = cached_entry["state_data"]
            if cached_hybrid == current_hybrid:
                issues.extend(cached_entry.get("issues", []))
                stats["cache_hits"] += 1
                return cached_entry.get("files_checked", 0), cached_entry.get("media_metadata")
            else:
                stats["cache_miss_modified"] += 1
    elif cached_entry and has_issues_in_cache:
        stats["cache_miss_known_issues"] += 1
    else:
        stats["cache_miss_new"] += 1

    # Cache-Miss, Änderung oder bekannte Issues -> Vollständiger Scan
    temp_issues = []
    files_checked, media_metadata = _check_series_show(temp_issues, category, show_path, validator)

    if deep_dive:
        current_deep = cache_mgr.calculate_deep_hash(show_path)
        cache_mgr.set_cached_entry(show_path, key, temp_issues, deep_hash=current_deep, files_checked=files_checked, media_metadata=media_metadata)
    else:
        current_hybrid = cache_mgr.calculate_hybrid_state(show_path, validator, is_movie=False)
        cache_mgr.set_cached_entry(show_path, key, temp_issues, hybrid_state=current_hybrid, files_checked=files_checked, media_metadata=media_metadata)

    issues.extend(temp_issues)
    return files_checked, media_metadata


# ---------------------------------------------------------------------------
# Scan-Steuerung
# ---------------------------------------------------------------------------
def _handle_cancel(shows_scanned, files_checked, issues, stats, cache_mgr, media_structure=None):
    cache_mgr.flush()
    summary = {"critical": 0, "warning": 0, "info": 0}
    for it in issues:
        summary[it["severity"]] = summary.get(it["severity"], 0) + 1

    result = {
        "status": "cancelled",
        "progress": 100,
        "message": f"Scan vom Benutzer abgebrochen. Bisherige Funde: {len(issues)}.",
        "finished_at": time.time(),
        "issues": issues,
        "summary": summary,
        "scanned": {"shows": shows_scanned, "files": files_checked},
        "stats": stats,
        "error": None,
        "media_structure": media_structure or {"series": [], "movies": []},
    }
    _set_state(**result)
    _write_cache()
    log_message(f"⏹️ [Health-Scan] Vom Benutzer abgebrochen. Bisherige Funde: {len(issues)} in {shows_scanned} Ordnern.")


def _run_health_scan(deep_dive: bool = False, category_ids: Optional[list] = None):
    issues = []
    files_checked = 0
    stats = {
        "cache_hits": 0,
        "cache_miss_modified": 0,
        "cache_miss_known_issues": 0,
        "cache_miss_new": 0
    }
    try:
        if not ensure_nas_mounted():
            _set_state(status="error", message="NAS konnte nicht gemountet werden.",
                       error="nas_unavailable", finished_at=time.time())
            log_message("❌ [Health-Scan] NAS nicht verfügbar.")
            return

        settings = utils.load_settings()
        from gui.core.transfers import validate_nas_library_preflight
        success, err_msg = validate_nas_library_preflight(settings)
        if not success:
            _set_state(status="warning", message=err_msg,
                       error="no_library_folders_found", finished_at=time.time())
            log_message(f"⚠️ [Health-Scan] Preflight fehlgeschlagen: {err_msg}")
            return
        server_type = settings.get("media_server", "").strip()
        if server_type:
            validator = artwork_validators.get_validator(server_type)
            cache_key = health_cache.get_cache_key(server_type)
            media_server_skipped = False
        else:
            validator = None
            cache_key = health_cache.get_cache_key("none")
            media_server_skipped = True

        _set_state(media_server_skipped=media_server_skipped)
        cache_mgr = health_cache.HealthCacheManager()

        # Detailliertes Debug-Logging
        sync_cats = settings.get("sync_categories", [])
        nas_root = settings.get("nas_root", "")
        log_message(f"🔍 [Health-Scan] nas_root: '{nas_root}'")
        log_message(f"🔍 [Health-Scan] Konfigurierte Kategorien: {len(sync_cats)}")

        checked_paths = []
        missing_paths = []
        for cat in sync_cats:
            nas_sub = cat.get("nas_sub")
            if not nas_sub:
                continue
            cat_path = os.path.join(nas_root, nas_sub.lstrip("/"))
            checked_paths.append(cat_path)

            exists = os.path.exists(cat_path)
            isdir = os.path.isdir(cat_path)
            readable = os.access(cat_path, os.R_OK) if exists else False

            log_message(f"  - Kategorie '{cat.get('id')}': path='{cat_path}', exists={exists}, isdir={isdir}, readable={readable}")

            if not exists or not isdir or not readable:
                missing_paths.append(nas_sub)

        shows = list(walk_nas_categories(settings, category_ids=category_ids))
        total = len(shows)
        log_message(f"🔍 [Health-Scan] Starte Prüfung von {total} Ordnern (deep_dive={deep_dive})...")

        if total == 0:
            msg = "Keine Bibliotheksordner gefunden. Prüfe NAS-Pfad und Kategoriepfade."
            _set_state(
                status="warning",
                message=msg,
                error="no_library_folders_found",
                finished_at=time.time()
            )
            log_message(f"⚠️ [Health-Scan] {msg}")
            return

        media_structure = {"series": [], "movies": []}

        for idx, show in enumerate(shows):
            if _cancel_event.is_set():
                _handle_cancel(idx, files_checked, issues, stats, cache_mgr, media_structure)
                return

            _set_state(
                progress=int((idx / total) * 100) if total else 100,
                message=f"Prüfe {show['category']}: {show['name']} ({idx + 1}/{total})",
                scanned={"shows": idx, "files": files_checked},
                stats=stats,
            )
            if show["type"] == "series":
                files_in_show, show_metadata = _check_series_cached(issues, show["category"], show["path"], validator, cache_mgr, cache_key, deep_dive, stats)
                files_checked += files_in_show
                media_structure["series"].append(show_metadata)
            elif _is_genre_container(show["path"]):
                # Genre-Sammelordner (z. B. Filme/Action): nicht selbst als Film prüfen,
                # sondern die enthaltenen Film-Unterordner einzeln.
                _add_issue(issues, "warning", "genre_container", show["category"], show["path"],
                           f"{show['name']}: Sammelordner/Genre-Struktur (Filme liegen in einem Unterordner)")
                try:
                    subdirs = sorted(e for e in os.listdir(show["path"]) if not e.startswith('.'))
                except OSError as e:
                    log_message(f"⚠️ [Bibliothek-Check] Genre-Ordner nicht lesbar: {show['path']} ({e})")
                    subdirs = []
                for sd in subdirs:
                    if _cancel_event.is_set():
                        _handle_cancel(idx, files_checked, issues, stats, cache_mgr, media_structure)
                        return
                    sp = os.path.join(show["path"], sd)
                    if os.path.isdir(sp):
                        files_in_movie, movie_metadata = _check_movie_cached(issues, show["category"], sp, validator, cache_mgr, cache_key, deep_dive, stats)
                        files_checked += files_in_movie
                        media_structure["movies"].append(movie_metadata)
            else:
                files_in_movie, movie_metadata = _check_movie_cached(issues, show["category"], show["path"], validator, cache_mgr, cache_key, deep_dive, stats)
                files_checked += files_in_movie
                media_structure["movies"].append(movie_metadata)

            if (idx + 1) % 25 == 0:
                log_message(f"🔍 [Health-Scan] {idx + 1}/{total} Ordner geprüft, "
                            f"{len(issues)} Auffälligkeiten bisher...")

        # Speicher-Cache dauerhaft auf Festplatte schreiben
        cache_mgr.flush()

        summary = {"critical": 0, "warning": 0, "info": 0}
        for it in issues:
            summary[it["severity"]] = summary.get(it["severity"], 0) + 1

        result = {
            "status": "done",
            "progress": 100,
            "message": f"Scan abgeschlossen: {len(issues)} Auffälligkeiten in {total} Ordnern." if not media_server_skipped else f"Scan abgeschlossen (Medienserver-Prüfung übersprungen): {len(issues)} Auffälligkeiten in {total} Ordnern.",
            "finished_at": time.time(),
            "issues": issues,
            "summary": summary,
            "scanned": {"shows": total, "files": files_checked},
            "stats": stats,
            "error": None,
            "media_server_skipped": media_server_skipped,
            "media_structure": media_structure,
        }
        _set_state(**result)
        _write_cache()
        log_message(f"✅ [Health-Scan] Fertig: {summary['critical']} kritisch, "
                    f"{summary['warning']} Warnungen, {summary['info']} Hinweise. "
                    f"Cache-Hits: {stats['cache_hits']}, Modifiziert: {stats['cache_miss_modified']}, "
                    f"Bekannte Fehler: {stats['cache_miss_known_issues']}, Neu: {stats['cache_miss_new']}")

    except Exception as e:
        import traceback
        traceback.print_exc()
        _set_state(status="error", message=f"Fehler beim Scan: {e}",
                   error=str(e), finished_at=time.time())
        log_message(f"❌ [Health-Scan] Fehler: {e}")


def start_health_scan(deep_dive: bool = False, category_ids: Optional[list] = None):
    """Startet den Scan im Hintergrund. Gibt False zurück, wenn bereits einer läuft."""
    with _state_lock:
        if _scan_state["status"] == "running":
            return False
        _cancel_event.clear()
        _scan_state.update({
            "status": "running",
            "progress": 0,
            "message": "Scan wird gestartet...",
            "started_at": time.time(),
            "finished_at": None,
            "issues": [],
            "summary": {"critical": 0, "warning": 0, "info": 0},
            "scanned": {"shows": 0, "files": 0},
            "stats": {"cache_hits": 0, "cache_miss_modified": 0, "cache_miss_known_issues": 0, "cache_miss_new": 0},
            "error": None,
            "media_server_skipped": False,
        })
    threading.Thread(target=_run_health_scan, args=(deep_dive, category_ids), daemon=True).start()
    return True


def stop_health_scan():
    """Fordert den Abbruch eines laufenden Scans an.

    Gibt True zurück, wenn der Abbruch angefordert wurde, andernfalls False.
    """
    with _state_lock:
        if _scan_state["status"] == "running":
            _cancel_event.set()
            _scan_state["status"] = "cancelled"
            _scan_state["message"] = "Abbruch angefordert..."
            return True
        return False


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


def remove_issue(issue_path: str, issue_type: str = None, nfo_path: str = None):
    """Entfernt einen behobenen Befund aus dem State und Cache, damit er in der UI sofort verschwindet."""
    changed = False
    with _state_lock:
        # 1. target_keys bestimmen (VOR dem Filtern!)
        target_keys = set()
        issues_source = _scan_state.get("issues", [])
        if _scan_state["status"] == "idle":
            cached = _read_cache()
            if cached and "issues" in cached:
                issues_source = cached["issues"]

        for i in issues_source:
            if i.get("path") == issue_path:
                if not issue_type or i.get("type") == issue_type:
                    target_keys.add(i["key"])

        # 2. Issues filtern
        if _scan_state["status"] == "idle":
            # Wenn wir idle sind, müssen wir den Cache laden, falls _scan_state leer ist
            cached = _read_cache()
            if cached and "issues" in cached:
                original_len = len(cached["issues"])
                if issue_type:
                    cached["issues"] = [i for i in cached["issues"] if not (i.get("path") == issue_path and i.get("type") == issue_type)]
                else:
                    cached["issues"] = [i for i in cached["issues"] if i.get("path") != issue_path]
                if len(cached["issues"]) < original_len:
                    _scan_state.update(cached)
                    changed = True
        else:
            if "issues" in _scan_state:
                original_len = len(_scan_state["issues"])
                if issue_type:
                    _scan_state["issues"] = [i for i in _scan_state["issues"] if not (i.get("path") == issue_path and i.get("type") == issue_type)]
                else:
                    _scan_state["issues"] = [i for i in _scan_state["issues"] if i.get("path") != issue_path]
                if len(_scan_state["issues"]) < original_len:
                    changed = True

        # 3. Summary-Neuberechnung
        if changed and "issues" in _scan_state:
            new_sum = {"critical": 0, "warning": 0, "info": 0}
            for i in _scan_state["issues"]:
                sev = i.get("severity", "warning")
                if sev in new_sum:
                    new_sum[sev] += 1
            _scan_state["summary"] = new_sum

        # 4. media_structure in _scan_state aktualisieren
        if changed and "media_structure" in _scan_state:
            new_status, new_current_fsk, new_raw_fsk, new_actionable_fsk = parse_fsk_status(nfo_path or issue_path)

            # Löschen aus movies
            for m in _scan_state["media_structure"].get("movies", []):
                if m.get("nfo_path") == issue_path or m.get("path") == issue_path:
                    m["fsk_status"] = new_status
                    m["current_fsk"] = new_current_fsk
                    m["raw_fsk"] = new_raw_fsk
                    m["actionable_fsk"] = new_actionable_fsk
                if "issue_keys" in m:
                    m["issue_keys"] = [k for k in m["issue_keys"] if k not in target_keys]

            # Löschen aus series -> seasons -> episodes
            for s in _scan_state["media_structure"].get("series", []):
                if s.get("nfo_path") == issue_path or s.get("path") == issue_path:
                    s["fsk_status"] = new_status
                    s["current_fsk"] = new_current_fsk
                    s["raw_fsk"] = new_raw_fsk
                    s["actionable_fsk"] = new_actionable_fsk
                if "issue_keys" in s:
                    s["issue_keys"] = [k for k in s["issue_keys"] if k not in target_keys]

                for se in s.get("seasons", []):
                    for ep in se.get("episodes", []):
                        if ep.get("nfo_path") == issue_path or ep.get("path") == issue_path:
                            ep["fsk_status"] = new_status
                            ep["current_fsk"] = new_current_fsk
                            ep["raw_fsk"] = new_raw_fsk
                            ep["actionable_fsk"] = new_actionable_fsk
                        if "issue_keys" in ep:
                            ep["issue_keys"] = [k for k in ep["issue_keys"] if k not in target_keys]

        # 5. Folder-Cache-Invalidierung
        folder_to_invalidate = None
        if changed and "media_structure" in _scan_state:
            for m in _scan_state["media_structure"].get("movies", []):
                if m.get("nfo_path") == issue_path or m.get("path") == issue_path:
                    folder_to_invalidate = m["path"]
                    break
            if not folder_to_invalidate:
                for s in _scan_state["media_structure"].get("series", []):
                    if s.get("nfo_path") == issue_path or s.get("path") == issue_path:
                        folder_to_invalidate = s["path"]
                        break
                    for se in s.get("seasons", []):
                        for ep in se.get("episodes", []):
                            if ep.get("nfo_path") == issue_path or ep.get("path") == issue_path:
                                folder_to_invalidate = s["path"]
                                break
                        if folder_to_invalidate:
                            break
                    if folder_to_invalidate:
                        break

        if folder_to_invalidate:
            try:
                from gui.core.health_cache import HealthCacheManager
                cache_mgr = HealthCacheManager()
                cache_mgr.invalidate_entry(folder_to_invalidate)
            except Exception as e:
                log_message(f"⚠️ [Health-Scan] Cache-Eintrag konnte nicht invalidiert werden: {e}")

    if changed:
        _write_cache()


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
    except Exception as e:
        log_message(f"⚠️ [Health-Scan] Cache konnte nicht gelesen werden: {e}")
    return None
