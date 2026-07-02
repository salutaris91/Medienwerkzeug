import os, sys, json, time, shutil, subprocess, urllib, threading
from flask import Blueprint, request, jsonify, Response, send_from_directory
from gui.core.utils import load_settings, save_settings, clean_show_name, load_show_profile, save_show_profile, load_konv_history
from gui.core.helpers import *
from gui.core.helpers import log_queue
from gui.core.transfers import *
from gui.workers.processor import *
from gui.workers.youtube_worker import *
import gui.core.media as media
import gui.mw_metadata as mw_metadata
import gui.core.trash as trash

nas_api = Blueprint('nas_api', __name__)

# Global variables imported from processor
from gui.workers.processor import SYSTEM_STATUS



@nas_api.route('/check-nas-duplicate', methods=['GET', 'POST'])
def handle_api_check_nas_duplicate():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    query = request.args
    """Check if a specific episode already exists on NAS."""
    ep_num = params.get("episode")
    ep_season = params.get("season")
    show_name = params.get("show_name")
    nas_show_folder = params.get("nas_show_folder")
    nas_destination_id = params.get("nas_destination_id")

    if ep_num is None or ep_season is None:
        return jsonify({"duplicate": None})

    try:
        ep_num = int(ep_num)
        ep_season = int(ep_season)
    except (ValueError, TypeError):
        return jsonify({"duplicate": None})

    settings = load_settings()
    nas_root = settings.get("nas_root", "")
    if not nas_root:
        return jsonify({"duplicate": None})

    destination = None
    if nas_destination_id:
        sync_cats = settings.get("sync_categories", [])
        for cat in sync_cats:
            if cat.get("id") == str(nas_destination_id):
                destination = os.path.join(nas_root, cat.get("nas_sub", "").lstrip("/"))
                break
    if not destination:
        destination = os.path.join(nas_root, "Serien")

    clean_show_name = clean_series_name_for_fs(nas_show_folder or show_name or "")
    if not clean_show_name:
        return jsonify({"duplicate": None})

    # Also check outbox for matched series name
    outbox_root = settings.get("outbox_dir", "")
    if not outbox_root:
        return jsonify({"duplicate": None})
    rel_dest = os.path.relpath(destination, nas_root)
    outbox_serien = os.path.join(outbox_root, rel_dest)
    from gui.core.series_helper import resolve_series_folder_name
    clean_show_name = resolve_series_folder_name(destination, outbox_serien, None, None, clean_show_name, log_reason=False)

    show_dir = os.path.join(destination, clean_show_name)

    if not os.path.exists(show_dir):
        return jsonify({"duplicate": None})

    # Search for matching episode files
    pats = [
        f"s{ep_season:02d}e{ep_num:02d}",
        f"s{ep_season:02d}e{ep_num:03d}",
        f"s{ep_season}e{ep_num:02d}",
        f"s{ep_season:02d}e{ep_num}",
    ]
    for root, _, files in os.walk(show_dir):
        for f in files:
            if f.startswith('.'):
                continue
            fl = f.lower()
            matched = False
            for pat in pats:
                if pat in fl:
                    matched = True
                    break
            if not matched and ep_season == 1:
                for suffix in [f" - {ep_num:02d} ", f" - {ep_num:02d}.", f" - {ep_num:03d} ", f" - {ep_num:03d}."]:
                    if suffix in fl:
                        matched = True
                        break
            if matched:
                # Only count video files as duplicates
                ext = os.path.splitext(f)[1].lower()
                if ext not in ('.mp4', '.mkv', '.avi', '.webm', '.mov', '.ts', '.m2ts'):
                    continue
                filepath = os.path.join(root, f)
                details = {"filename": f, "path": filepath}
                try:
                    size_bytes = os.path.getsize(filepath)
                    details["size_gb"] = size_bytes / (1024 * 1024 * 1024)
                    cmd = [
                        "ffprobe", "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=width,height", "-of", "csv=p=0",
                        filepath
                    ]
                    res = subprocess.run(cmd, capture_output=True, text=True, timeout=2.0)
                    if res.returncode == 0:
                        dimensions = res.stdout.strip().split(',')
                        if len(dimensions) == 2:
                            details["resolution"] = f"{dimensions[0]}x{dimensions[1]}"
                except Exception:
                    pass
                return jsonify({"duplicate": details})

    return jsonify({"duplicate": None})



@nas_api.route('/streamfab-import/preview', methods=['GET'])
def handle_api_streamfab_preview():
    preview_data = preview_streamfab_import()
    return jsonify({"status": "ok", "preview": preview_data})


@nas_api.route('/streamfab-import', methods=['POST'])
def handle_api_streamfab_import():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}

    import_items = params.get("import_items", {})
    delete_items = params.get("delete_items", [])
    count = execute_streamfab_import(import_items, delete_items)
    return jsonify({"status": "ok", "moved_count": count})


@nas_api.route('/nas-series', methods=['GET', 'POST'])
def handle_api_nas_series():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    query = request.args
    settings = load_settings()
    nas_root = settings.get("nas_root", "")
    outbox_root = settings.get("outbox_dir", "")
    if not nas_root or not outbox_root:
        return jsonify([])

    # Das Frontend ruft diesen Endpoint per GET mit ?destination_id=... auf, daher
    # zusätzlich die Query-Args lesen (nicht nur den JSON-Body).
    nas_destination_id = (params.get("nas_destination_id") or params.get("destination_id")
                          or query.get("nas_destination_id") or query.get("destination_id") or "2")
    if isinstance(nas_destination_id, list) and len(nas_destination_id) > 0:
        nas_destination_id = nas_destination_id[0]

    sync_cats = settings.get("sync_categories", [])
    categories_to_scan = []

    if nas_destination_id == "all":
        categories_to_scan = sync_cats
    else:
        found_cat = None
        for cat in sync_cats:
            if cat.get("id") == str(nas_destination_id):
                found_cat = cat
                break
        if not found_cat:
            for cat in sync_cats:
                nas_sub = cat.get("nas_sub", "")
                if nas_sub and (nas_sub in str(nas_destination_id)):
                    found_cat = cat
                    break
        if found_cat:
            categories_to_scan = [found_cat]
        else:
            categories_to_scan = [{"id": "2", "name": "Serien", "nas_sub": "/Serien"}]

    connected = ensure_nas_mounted()

    folders = set()
    folder_to_dest = {}

    for cat in categories_to_scan:
        nas_sub = cat.get("nas_sub")
        if not nas_sub:
            continue
        destination = f"{nas_root}{nas_sub}"
        cat_folders = set()

        if connected and os.path.exists(destination):
            try:
                for entry in os.listdir(destination):
                    if os.path.isdir(os.path.join(destination, entry)) and not entry.startswith('.'):
                        cat_folders.add(entry)
            except Exception as e:
                print(f"Fehler beim Scannen von NAS {destination}: {e}")

        rel_dest = os.path.relpath(destination, nas_root)
        outbox_dest = os.path.join(outbox_root, rel_dest)
        if os.path.exists(outbox_dest):
            try:
                for entry in os.listdir(outbox_dest):
                    if os.path.isdir(os.path.join(outbox_dest, entry)) and not entry.startswith('.'):
                        cat_folders.add(entry)
            except Exception as e:
                print(f"Fehler beim Scannen von Outbox {outbox_dest}: {e}")

        for folder in cat_folders:
            folder_clean = folder.strip()
            if not folder_clean:
                continue
            lower_folder = folder_clean.lower()
            folders.add(folder_clean)
            folder_to_dest[lower_folder] = destination

    # Case-insensitive deduplication
    deduped = {}
    for entry in folders:
        name = entry.strip()
        if not name:
            continue
        lowered = name.lower()
        if lowered in deduped:
            # Keep the one with better casing (more uppercase letters)
            existing = deduped[lowered]
            existing_caps = sum(1 for c in existing if c.isupper())
            entry_caps = sum(1 for c in name if c.isupper())
            if entry_caps > existing_caps:
                deduped[lowered] = name
        else:
            deduped[lowered] = name

    return jsonify({
        "connected": connected,
        "folders": sorted(list(deduped.values()), key=lambda s: s.lower()),
        "folder_destinations": {k: folder_to_dest[k] for k in deduped.keys() if k in folder_to_dest}
    })



@nas_api.route('/nas-seasons', methods=['GET', 'POST'])
def handle_api_nas_seasons():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    query = request.args
    """Return existing season folders and episode counts for a show on the NAS."""
    folder_name = query.get("folder", [""])[0] if isinstance(query.get("folder"), list) else query.get("folder", "")
    destination_id = query.get("destination_id", [""])[0] if isinstance(query.get("destination_id"), list) else query.get("destination_id", "")
    exact_match = query.get("exact", "0") == "1"

    if not folder_name:
        return jsonify({"seasons": [], "folder": folder_name, "connected": False})

    settings = load_settings()
    nas_root = settings.get("nas_root", "")
    outbox_root = settings.get("outbox_dir", "")
    if not nas_root or not outbox_root:
        return jsonify({"seasons": [], "folder": folder_name, "connected": False})
    connected = ensure_nas_mounted()
    sync_cats = settings.get("sync_categories", [])

    # Resolve which NAS destinations to scan
    destinations = []
    matched_dest_id = destination_id

    if destination_id and destination_id != "all":
        for cat in sync_cats:
            if cat.get("id") == str(destination_id):
                nas_sub = cat.get("nas_sub", "")
                if nas_sub:
                    destinations.append(f"{nas_root}{nas_sub}")
                break
    else:
        for cat in sync_cats:
            nas_sub = cat.get("nas_sub", "")
            if nas_sub:
                destinations.append(f"{nas_root}{nas_sub}")

    if not destinations:
        destinations = [os.path.join(nas_root, "Serien")]

    video_extensions = {'.mkv', '.mp4', '.avi', '.m4v', '.ts', '.mov', '.wmv'}

    def scan_dest(dest_path):
        local_seasons = []
        rel_dest = os.path.relpath(dest_path, nas_root)
        outbox_dest = os.path.join(outbox_root, rel_dest)

        # Use fuzzy matching to resolve existing folder name, unless exact match requested
        clean_show = clean_series_name_for_fs(folder_name)
        if exact_match:
            matched_folder = clean_show
        else:
            from gui.core.series_helper import resolve_series_folder_name
            matched_folder = resolve_series_folder_name(dest_path, outbox_dest, None, None, clean_show, log_reason=False)

        show_path = os.path.join(dest_path, matched_folder)
        outbox_show_path = os.path.join(outbox_dest, matched_folder)

        for base_path in [show_path, outbox_show_path]:
            if not os.path.isdir(base_path):
                continue
            try:
                for entry in sorted(os.listdir(base_path)):
                    entry_path = os.path.join(base_path, entry)
                    if not os.path.isdir(entry_path) or entry.startswith('.'):
                        continue
                    # Match "Staffel X" pattern
                    if entry.lower().startswith("staffel ") or entry.lower().startswith("season ") or entry.lower().startswith("specials"):
                        # Count video files in this season dir (including subdirs)
                        episode_count = 0
                        for root, dirs, files in os.walk(entry_path):
                            for f in files:
                                ext = os.path.splitext(f)[1].lower()
                                if ext in video_extensions and not f.startswith('.'):
                                    episode_count += 1

                        # Check if this season is already in our list
                        existing = next((s for s in local_seasons if s["name"] == entry), None)
                        if existing:
                            existing["episodes"] = max(existing["episodes"], episode_count)
                            if "NAS" not in existing["source"]:
                                existing["source"] += " + NAS" if base_path == show_path else ""
                        else:
                            source = "NAS" if base_path == show_path else "Outbox"
                            local_seasons.append({
                                "name": entry,
                                "episodes": episode_count,
                                "source": source
                            })
            except Exception as e:
                print(f"Error scanning seasons in {base_path}: {e}")
        return local_seasons

    # 1. Scan the initially selected destinations
    seasons = []
    for dest in destinations:
        seasons.extend(scan_dest(dest))

    # Check if empty or 0 episodes overall
    total_episodes = sum(s["episodes"] for s in seasons)
    if not seasons or total_episodes == 0:
        # Fallback: scan all other categories in sync_categories
        fallback_seasons = []
        fallback_best_episodes = -1
        fallback_cat_id = None

        for cat in sync_cats:
            cat_id = cat.get("id")
            nas_sub = cat.get("nas_sub", "")
            if not nas_sub:
                continue
            cat_dest = f"{nas_root}{nas_sub}"
            # Skip if we already scanned this destination
            if cat_dest in destinations:
                continue

            cat_seasons = scan_dest(cat_dest)
            cat_episodes = sum(s["episodes"] for s in cat_seasons)

            if cat_seasons:
                # We prefer a category that has episodes, but any non-empty season structure is better than nothing
                if cat_episodes > fallback_best_episodes:
                    fallback_seasons = cat_seasons
                    fallback_best_episodes = cat_episodes
                    fallback_cat_id = cat_id

        if fallback_seasons:
            seasons = fallback_seasons
            if fallback_cat_id:
                matched_dest_id = fallback_cat_id

    # Sort seasons naturally
    def season_sort_key(s):
        import re
        match = re.search(r'(\d+)', s["name"])
        return int(match.group(1)) if match else 999

    seasons.sort(key=season_sort_key)

    return jsonify({
        "connected": connected,
        "seasons": seasons,
        "folder": folder_name,
        "matched_destination_id": matched_dest_id
    })



@nas_api.route('/media-compare', methods=['GET', 'POST'])
def handle_api_media_compare():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    query = request.args
    new_paths = query.get("new_path", [])
    existing_paths = query.get("existing_path", [])

    new_path = new_paths[0] if new_paths else ""
    existing_path = existing_paths[0] if existing_paths else ""

    if not new_path or not existing_path:
        return jsonify({"error": "Missing new_path or existing_path"}), 400

    # Security validation for paths
    settings = load_settings()
    inbox_root = settings.get("inbox_dir", "")
    nas_root = settings.get("nas_root", "")
    if not inbox_root or not nas_root:
        return jsonify({"error": "Inbox oder NAS-Root ist nicht konfiguriert."}), 400

    # Ensure we only check files in allowed directories
    abs_new = os.path.abspath(new_path)
    abs_existing = os.path.abspath(existing_path)

    if not (abs_new.startswith(os.path.abspath(inbox_root) + os.sep) or abs_new == os.path.abspath(inbox_root)):
        return jsonify({"error": "Forbidden new_path"}), 403

    if not (abs_existing.startswith(os.path.abspath(nas_root) + os.sep) or abs_existing == os.path.abspath(nas_root)):
        return jsonify({"error": "Forbidden existing_path"}), 403

    def get_media_compare_details(filepath):
        details = {
            "path": filepath,
            "filename": os.path.basename(filepath),
            "size_bytes": 0,
            "size_readable": "0 B",
            "resolution": "Unbekannt",
            "video_codec": "Unbekannt",
            "audio_codec": "Unbekannt",
            "bitrate_kbps": "Unbekannt",
            "duration_str": "Unbekannt"
        }
        if not filepath or not os.path.exists(filepath):
            return details
        try:
            size_bytes = os.path.getsize(filepath)
            details["size_bytes"] = size_bytes
            if size_bytes >= 1024**3:
                details["size_readable"] = f"{size_bytes / (1024**3):.2f} GB"
            elif size_bytes >= 1024**2:
                details["size_readable"] = f"{size_bytes / (1024**2):.1f} MB"
            else:
                details["size_readable"] = f"{size_bytes / 1024:.1f} KB"

            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "stream=width,height,codec_name,codec_type:format=duration,bit_rate",
                "-of", "json",
                filepath
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=3.0)
            if res.returncode == 0:
                info = json.loads(res.stdout)
                streams = info.get("streams", [])
                format_info = info.get("format", {})
                for s in streams:
                    codec_type = s.get("codec_type")
                    if codec_type == "video":
                        details["video_codec"] = s.get("codec_name", "Unbekannt").upper()
                        w = s.get("width")
                        h = s.get("height")
                        if w and h:
                            details["resolution"] = f"{w}x{h}"
                    elif codec_type == "audio":
                        details["audio_codec"] = s.get("codec_name", "Unbekannt").upper()

                duration = format_info.get("duration")
                if duration:
                    try:
                        dur_secs = float(duration)
                        mins, secs = divmod(int(dur_secs), 60)
                        hours, mins = divmod(mins, 60)
                        if hours > 0:
                            details["duration_str"] = f"{hours}h {mins}m {secs}s"
                        else:
                            details["duration_str"] = f"{mins}m {secs}s"
                    except Exception:
                        pass

                bitrate = format_info.get("bit_rate")
                if bitrate:
                    try:
                        details["bitrate_kbps"] = f"{int(bitrate) / 1000:.0f} kbps"
                    except Exception:
                        pass
        except Exception:
            pass
        return details

    new_details = get_media_compare_details(new_path)
    existing_details = get_media_compare_details(existing_path)

    return jsonify({
        "new_file": new_details,
        "existing_file": existing_details
    })



@nas_api.route('/resolve-duplicate', methods=['POST'])
def handle_api_resolve_duplicate():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    query = request.args
    action = params.get("action")
    new_path = params.get("new_path")
    existing_path = params.get("existing_path")

    if not existing_path or not os.path.exists(existing_path):
        return jsonify({"error": "Invalid existing_path"}), 400

    # Security validation for paths
    settings = load_settings()
    nas_root = settings.get("nas_root", "")
    if not nas_root:
        return jsonify({"error": "NAS-Root ist nicht konfiguriert."}), 400
    abs_existing = os.path.abspath(existing_path)

    if not (abs_existing.startswith(os.path.abspath(nas_root) + os.sep) or abs_existing == os.path.abspath(nas_root)):
        return jsonify({"error": "Forbidden existing_path"}), 403

    if action == "upgrade":
        try:
            trash.send_to_trash(existing_path, force=True)
            log_message(f"🗑️ [Dubletten-Upgrade] Existierende Datei auf NAS in Quarantäne verschoben: {existing_path}")

            # Delete corresponding nfo / artwork if present
            base_path = os.path.splitext(existing_path)[0]
            from gui.core.artwork_validators import get_basename_sidecar_suffixes
            for ext in get_basename_sidecar_suffixes():
                art_file = base_path + ext
                if os.path.exists(art_file):
                    try:
                        trash.send_to_trash(art_file, force=True)
                        log_message(f"  🗑️ Zugehörige Datei in Quarantäne verschoben: {art_file}")
                    except Exception as e:
                        log_message(f"⚠️ Zugehörige Datei konnte nicht in Quarantäne verschoben werden: {art_file} ({e})")

            return jsonify({"status": "success", "message": "Existierende Datei in Quarantäne verschoben. Bereit für Upgrade."})
        except trash.TrashError as e:
            return jsonify({"error": str(e)}), 500
        except Exception as e:
            return jsonify({"error": f"Error deleting file: {e}"}), 500
    else:
        return jsonify({"status": "success", "message": "Keine Aktion ausgeführt."})


# ==========================================================================
# Feature 3: Media Health Dashboard
# ==========================================================================
@nas_api.route('/nas/health-scan', methods=['POST'])
def handle_api_nas_health_scan():
    """Startet einen Bibliotheks-Health-Scan im Hintergrund."""
    import gui.core.health as health
    try:
        from gui.core import utils
        settings = utils.load_settings()
        media_server = settings.get("media_server", "").strip()
        if not media_server:
            return jsonify({
                "started": False,
                "error": "Bitte wähle zuerst einen Medienserver (Emby/Jellyfin/Plex) in den Einstellungen aus."
            }), 400

        if not ensure_nas_mounted():
            return jsonify({"started": False, "error": "NAS ist offline"}), 503

        params = request.get_json(silent=True) or {}
        deep_dive = params.get("deep", False)
        if not deep_dive:
            deep_dive = request.args.get("deep", "false").lower() == "true"

        category_ids = params.get("category_ids", None)
        if category_ids is None:
            cat_ids_str = request.args.get("category_ids", "")
            if cat_ids_str:
                category_ids = [x.strip() for x in cat_ids_str.split(",") if x.strip()]

        started = health.start_health_scan(deep_dive=deep_dive, category_ids=category_ids)
        if not started:
            return jsonify({"started": False, "message": "Ein Scan läuft bereits."})
        return jsonify({"started": True, "message": "Scan gestartet."})
    except Exception as e:
        return jsonify({"started": False, "error": f"Scan konnte nicht gestartet werden: {e}"}), 500


@nas_api.route('/nas/health-status', methods=['GET'])
def handle_api_nas_health_status():
    """Liefert Fortschritt und Ergebnis des Health-Scans (gecacht)."""
    import gui.core.health as health
    try:
        return jsonify(health.get_health_status())
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@nas_api.route('/nas/health-cancel', methods=['POST'])
def handle_api_nas_health_cancel():
    """Bricht den laufenden Health-Scan ab."""
    import gui.core.health as health
    try:
        stopped = health.stop_health_scan()
        return jsonify({"stopped": stopped})
    except Exception as e:
        return jsonify({"stopped": False, "error": str(e)}), 500


# ==========================================================================
# Feature 4: NAS-weite Duplikat-Erkennung
# ==========================================================================
@nas_api.route('/nas/scan-duplicates', methods=['POST'])
def handle_api_nas_scan_duplicates():
    """Startet die Duplikat-Erkennung im Hintergrund."""
    import gui.core.duplicates as duplicates
    if not ensure_nas_mounted():
        return jsonify({"started": False, "error": "NAS ist offline"}), 503
    try:
        started = duplicates.start_duplicate_scan()
        if not started:
            return jsonify({"started": False, "message": "Ein Scan läuft bereits."})
        return jsonify({"started": True, "message": "Scan gestartet."})
    except Exception as e:
        return jsonify({"started": False, "error": f"Scan konnte nicht gestartet werden: {e}"}), 500


@nas_api.route('/nas/duplicates', methods=['GET'])
def handle_api_nas_duplicates():
    """Liefert Fortschritt und Ergebnis der Duplikat-Erkennung (gecacht)."""
    import gui.core.duplicates as duplicates
    try:
        return jsonify(duplicates.get_duplicate_status())
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@nas_api.route('/nas/resolve-duplicate-global', methods=['POST'])
def handle_api_nas_resolve_duplicate_global():
    """Löscht eine als Duplikat gewählte Datei (mit Pfad-Validierung unter NAS-Root)."""
    import gui.core.duplicates as duplicates
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    file_path = params.get("path")
    if not file_path:
        return jsonify({"ok": False, "message": "Kein Pfad angegeben."}), 400
    try:
        ok, message = duplicates.resolve_duplicate(file_path)
        status = 200 if ok else 400
        return jsonify({"ok": ok, "message": message}), status
    except Exception as e:
        return jsonify({"ok": False, "message": f"Fehler: {e}"}), 500


# ==========================================================================
# Befunde dauerhaft ignorieren (Health-Check & Duplikat-Erkennung)
# ==========================================================================
@nas_api.route('/findings/ignore', methods=['POST'])
def handle_api_findings_ignore():
    """Fügt einen Befund-Schlüssel zur Ignorier-Liste hinzu."""
    import gui.core.ignores as ignores
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    key = params.get("key")
    if not key:
        return jsonify({"ok": False, "message": "Kein Schlüssel angegeben."}), 400
    ok = ignores.add_ignore(key)
    return jsonify({"ok": ok})


@nas_api.route('/findings/unignore', methods=['POST'])
def handle_api_findings_unignore():
    """Entfernt einen Befund-Schlüssel aus der Ignorier-Liste (wieder einblenden)."""
    import gui.core.ignores as ignores
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    key = params.get("key")
    if not key:
        return jsonify({"ok": False, "message": "Kein Schlüssel angegeben."}), 400
    ok = ignores.remove_ignore(key)
    return jsonify({"ok": ok})


@nas_api.route('/findings/ignored', methods=['GET'])
def handle_api_findings_ignored():
    """Liefert die Liste aller ignorierten Befund-Schlüssel."""
    import gui.core.ignores as ignores
    return jsonify({"ignored": sorted(ignores.get_ignored())})


# ==========================================================================
# Quick-Fix: Ordner/Datei umbenennen (Health-Check name_mismatch + bad_folder_name + nested_duplicate)
# ==========================================================================
@nas_api.route('/nas/health-fix', methods=['POST'])
def handle_api_health_fix():
    """Benennt Ordner oder Datei um, um Health-Issues zu beheben.

    Actions:
        rename_folder  – Ordner zum angegebenen Namen umbenennen
        rename_file    – Videodatei (+ Begleitdateien) zum angegebenen Namen umbenennen
        flatten        – Doppelt verschachtelten Ordner auflösen (Inhalt hoch verschieben)
    """
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}

    import gui.core.health as health

    action = params.get("action")
    path = params.get("path")
    from gui.core.helpers import sanitize_filename
    new_name = sanitize_filename(params.get("new_name", "").strip())

    if not path or not os.path.isdir(path):
        return jsonify({"ok": False, "message": "Ordner nicht gefunden."}), 400

    settings = load_settings()
    nas_root = settings.get("nas_root", "")
    if not nas_root:
        return jsonify({"ok": False, "message": "NAS-Root ist nicht konfiguriert."}), 400
    nas_root = os.path.realpath(nas_root)
    real_path = os.path.realpath(path)
    if not real_path.startswith(nas_root + os.sep) and real_path != nas_root:
        return jsonify({"ok": False, "message": "Pfad liegt außerhalb des NAS."}), 403

    try:
        if action == "set_fsk":
            new_fsk = params.get("new_fsk")
            valid_fsks = ["0", "6", "12", "16", "18", 0, 6, 12, 16, 18]
            if new_fsk not in valid_fsks:
                return jsonify({"ok": False, "message": f"Ungültiger FSK-Wert: {new_fsk}"}), 400

            fsk_str = f"FSK {new_fsk}"

            settings = load_settings()
            nas_root_setting = os.path.realpath(settings.get("nas_root", ""))

            is_movie = True
            real_path = os.path.realpath(path)

            best_cat = None
            best_cat_len = -1

            for cat in settings.get("sync_categories", []):
                nas_sub = cat.get("nas_sub")
                if not nas_sub: continue

                cat_path = os.path.realpath(os.path.join(nas_root_setting, nas_sub.lstrip("/")))
                try:
                    if os.path.commonpath([real_path, cat_path]) == cat_path:
                        if len(cat_path) > best_cat_len:
                            best_cat_len = len(cat_path)
                            best_cat = cat
                except ValueError:
                    continue

            if best_cat:
                cat_name = best_cat.get("name", "")
                if "serie" in cat_name.lower():
                    is_movie = False
                else:
                    try:
                        if any(os.path.isdir(os.path.join(real_path, e)) and (e.lower().startswith("staffel ") or e.lower().startswith("season ") or e.lower().startswith("specials")) for e in os.listdir(real_path)):
                            is_movie = False
                    except OSError:
                        pass

            nfo_path = health.find_primary_nfo(path, is_movie=is_movie)

            if not nfo_path or not os.path.exists(nfo_path):
                return jsonify({"ok": False, "message": "NFO-Datei konnte nicht eindeutig bestimmt werden."}), 400

            import xml.etree.ElementTree as ET
            import tempfile
            import time
            import re

            try:
                with open(nfo_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception as e:
                return jsonify({"ok": False, "message": f"NFO lesefehler: {e}"}), 500

            # Plausibilitätscheck 1 und Tag-Zählung
            try:
                tree = ET.fromstring(content)
            except Exception as e:
                return jsonify({"ok": False, "message": f"Original-XML fehlerhaft: {e}"}), 400

            if tree.tag not in ["movie", "tvshow", "episodedetails"]:
                return jsonify({"ok": False, "message": f"Ungültiges NFO Root-Tag: {tree.tag}"}), 400

            mpaa_elements = tree.findall('.//mpaa')
            if len(mpaa_elements) > 1:
                return jsonify({"ok": False, "message": "Mehrere <mpaa>-Tags gefunden. Bitte manuell bereinigen."}), 400

            if len(mpaa_elements) == 1:
                new_content = re.sub(r'<mpaa[\s>].*?</mpaa>', f'<mpaa>{fsk_str}</mpaa>', content, count=1, flags=re.DOTALL|re.IGNORECASE)
            else:
                # Insert before closing tag
                closing_tag = f"</{tree.tag}>"
                if closing_tag not in content:
                    return jsonify({"ok": False, "message": f"NFO-Datei ist unvollständig (End-Tag {closing_tag} fehlt)."}), 400
                new_content = content.replace(closing_tag, f"  <mpaa>{fsk_str}</mpaa>\n{closing_tag}")

            # Plausibilitätscheck 2
            try:
                ET.fromstring(new_content)
            except Exception as e:
                return jsonify({"ok": False, "message": f"Generiertes XML fehlerhaft: {e}"}), 500

            temp_path = None
            try:
                # Backup anlegen
                ts = time.strftime("%Y%m%d_%H%M%S")
                bak_path = f"{nfo_path}.bak.{ts}"
                suffix = 1
                while os.path.exists(bak_path):
                    bak_path = f"{nfo_path}.bak.{ts}_{suffix}"
                    suffix += 1
                shutil.copy2(nfo_path, bak_path)

                # Temp file schreiben
                fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(nfo_path), text=True)
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(new_content)

                os.replace(temp_path, nfo_path)
                temp_path = None # Set to None after successful replace so finally doesn't delete it
                log_message(f"🔧 [Health-Fix] FSK aktualisiert auf {fsk_str} in {os.path.basename(nfo_path)}")
                health.remove_issue(path, "missing_age_rating")
                health.remove_issue(path, "invalid_age_rating")
                return jsonify({"ok": True, "message": f"FSK aktualisiert auf {fsk_str}."})
            except Exception as e:
                return jsonify({"ok": False, "message": f"Fehler beim Speichern: {e}"}), 500
            finally:
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except OSError:
                        pass

        if action == "flatten":
            entries = [e for e in os.listdir(path) if not e.startswith('.')]
            subdirs = [e for e in entries if os.path.isdir(os.path.join(path, e))]
            if len(subdirs) != 1:
                return jsonify({"ok": False, "message": "Ordner hat nicht genau einen Unterordner."}), 400
            inner = os.path.join(path, subdirs[0])
            for item in os.listdir(inner):
                if item.startswith('.'):
                    continue
                src = os.path.join(inner, item)
                dst = os.path.join(path, item)
                if os.path.exists(dst):
                    return jsonify({"ok": False, "message": f"Ziel existiert bereits: {item}"}), 409
                shutil.move(src, dst)
            rest = [e for e in os.listdir(inner) if not e.startswith('.')]
            if not rest:
                try:
                    trash.send_to_trash(inner, force=True)
                except Exception as e:
                    log_message(f"⚠️ [Health-Fix] Konnte leeren Ordner {inner} nicht in Quarantäne verschieben: {e}")
            log_message(f"🔧 [Health-Fix] Verschachtelung aufgelöst: {path}")
            health.remove_issue(path, "nested_duplicate")
            return jsonify({"ok": True, "message": "Verschachtelung aufgelöst."})

        if action == "rename_folder":
            if not new_name:
                return jsonify({"ok": False, "message": "Kein neuer Name angegeben."}), 400
            parent = os.path.dirname(path)
            dst = os.path.join(parent, new_name)
            if os.path.exists(dst):
                return jsonify({"ok": False, "message": f"Zielordner existiert bereits: {new_name}"}), 409
            os.rename(path, dst)
            log_message(f"🔧 [Health-Fix] Ordner umbenannt: {os.path.basename(path)} → {new_name}")
            health.remove_issue(path)
            return jsonify({"ok": True, "message": f"Ordner umbenannt zu '{new_name}'."})

        # Hilfsfunktion: Videodatei + Begleitdateien finden
        def _find_video_and_companions(folder):
            video_exts = {'.mkv', '.mp4', '.avi', '.m4v', '.ts', '.mov', '.wmv'}
            companion_exts = {'.nfo', '.srt', '.vtt', '.ass', '.sub', '.idx'}
            videos = []
            for dp, _ds, fns in os.walk(folder):
                for f in fns:
                    if not f.startswith('.') and os.path.splitext(f)[1].lower() in video_exts:
                        videos.append((dp, f))
            return videos, video_exts, companion_exts

        def _rename_files(folder, old_stem, target_name, video_exts, companion_exts):
            renamed = []
            for dp, _ds, fns in os.walk(folder):
                for f in fns:
                    if f.startswith('.'):
                        continue
                    stem, ext = os.path.splitext(f)
                    ext_low = ext.lower()
                    if stem == old_stem and (ext_low in video_exts or ext_low in companion_exts):
                        new_fn = target_name + ext
                        src = os.path.join(dp, f)
                        dst = os.path.join(dp, new_fn)
                        if src != dst:
                            if os.path.exists(dst):
                                return None, f"Zieldatei existiert bereits: {new_fn}"
                            os.rename(src, dst)
                            renamed.append(f"{f} → {new_fn}")
            return renamed, None

        if action == "rename_file":
            if not new_name:
                return jsonify({"ok": False, "message": "Kein neuer Name angegeben."}), 400
            videos, video_exts, companion_exts = _find_video_and_companions(path)
            if len(videos) != 1:
                return jsonify({"ok": False, "message": "Ordner enthält nicht genau eine Videodatei."}), 400
            old_stem = os.path.splitext(videos[0][1])[0]
            renamed, err = _rename_files(path, old_stem, new_name, video_exts, companion_exts)
            if err:
                return jsonify({"ok": False, "message": err}), 409
            log_message(f"🔧 [Health-Fix] Dateien umbenannt in {path}: {', '.join(renamed)}")
            health.remove_issue(path)
            return jsonify({"ok": True, "message": f"{len(renamed)} Datei(en) umbenannt."})

        if action == "rename_folder_to_file":
            videos, video_exts, companion_exts = _find_video_and_companions(path)
            if len(videos) != 1:
                return jsonify({"ok": False, "message": "Ordner enthält nicht genau eine Videodatei."}), 400
            video_stem = os.path.splitext(videos[0][1])[0]
            folder_name = os.path.basename(path)
            if folder_name == video_stem:
                return jsonify({"ok": True, "message": "Ordner und Datei stimmen bereits überein."})
            parent = os.path.dirname(path)
            dst = os.path.join(parent, video_stem)
            if os.path.exists(dst):
                return jsonify({"ok": False, "message": f"Zielordner existiert bereits: {video_stem}"}), 409
            os.rename(path, dst)
            log_message(f"🔧 [Health-Fix] Ordner an Datei angeglichen: {folder_name} → {video_stem}")
            health.remove_issue(path)
            return jsonify({"ok": True, "message": f"Ordner umbenannt zu '{video_stem}'."})

        if action == "rename_file_to_folder":
            videos, video_exts, companion_exts = _find_video_and_companions(path)
            if len(videos) != 1:
                return jsonify({"ok": False, "message": "Ordner enthält nicht genau eine Videodatei."}), 400
            old_stem = os.path.splitext(videos[0][1])[0]
            folder_name = os.path.basename(path)
            if old_stem == folder_name:
                return jsonify({"ok": True, "message": "Ordner und Datei stimmen bereits überein."})
            renamed, err = _rename_files(path, old_stem, folder_name, video_exts, companion_exts)
            if err:
                return jsonify({"ok": False, "message": err}), 409
            log_message(f"🔧 [Health-Fix] Datei an Ordner angeglichen: {old_stem} → {folder_name}")
            health.remove_issue(path)
            return jsonify({"ok": True, "message": f"{len(renamed)} Datei(en) umbenannt."})

        if action == "rename_both":
            if not new_name:
                return jsonify({"ok": False, "message": "Kein neuer Name angegeben."}), 400
            videos, video_exts, companion_exts = _find_video_and_companions(path)
            if len(videos) != 1:
                return jsonify({"ok": False, "message": "Ordner enthält nicht genau eine Videodatei."}), 400
            old_stem = os.path.splitext(videos[0][1])[0]
            renamed, err = _rename_files(path, old_stem, new_name, video_exts, companion_exts)
            if err:
                return jsonify({"ok": False, "message": err}), 409
            parent = os.path.dirname(path)
            dst = os.path.join(parent, new_name)
            if os.path.exists(dst):
                return jsonify({"ok": False, "message": f"Zielordner existiert bereits: {new_name}"}), 409
            os.rename(path, dst)
            log_message(f"🔧 [Health-Fix] Ordner + Dateien umbenannt: {os.path.basename(path)} → {new_name}")
            health.remove_issue(path)
            return jsonify({"ok": True, "message": f"Ordner und {len(renamed)} Datei(en) umbenannt zu '{new_name}'."})

        return jsonify({"ok": False, "message": f"Unbekannte Aktion: {action}"}), 400

    except Exception as e:
        return jsonify({"ok": False, "message": f"Fehler: {e}"}), 500


# ==========================================================================
# Doppelte Verschachtelung auflösen (Vorschau & Anwenden)
# ==========================================================================

def are_folder_names_equivalent(name1: str, name2: str) -> bool:
    n1 = name1.lower().strip()
    n2 = name2.lower().strip()
    if n1 == n2:
        return True
    import re
    # Entferne Jahreszahl-Klammern wie (2025)
    def clean(s):
        s = re.sub(r'\(\d{4}\)', '', s)
        s = re.sub(r'[\s\.\-\(\)\[\]_]', '', s)
        return s.strip()
    return clean(n1) == clean(n2)


def _get_structure_fix_preview(path: str):
    settings = load_settings()
    nas_root = settings.get("nas_root", "")
    if not nas_root:
        return None, "NAS-Root ist nicht konfiguriert.", 400
    nas_root = os.path.realpath(nas_root)
    real_path = os.path.realpath(path)

    if not os.path.exists(real_path):
        return None, "Der angegebene Ordner existiert nicht.", 404
    if not os.path.isdir(real_path):
        return None, "Der Pfad ist kein Ordner.", 400
    if not real_path.startswith(nas_root + os.sep) and real_path != nas_root:
        return None, "Pfad liegt außerhalb des NAS.", 403

    try:
        entries = [e for e in os.listdir(real_path) if not e.startswith('.')]
    except OSError as e:
        return None, f"Ordner kann nicht gelesen werden: {e}", 500

    subdirs = [e for e in entries if os.path.isdir(os.path.join(real_path, e))]

    # 1. Bestimme, ob es eine Serienkategorie ist
    is_series_dir = False
    for cat in settings.get("sync_categories", []):
        nas_sub = cat.get("nas_sub", "")
        if not nas_sub: continue
        cat_path = os.path.realpath(os.path.join(nas_root, nas_sub.lstrip("/")))
        if real_path.startswith(cat_path + os.sep) or real_path == cat_path:
            if "serie" in cat.get("name", "").lower():
                is_series_dir = True
                break

    video_exts = {'.mkv', '.mp4', '.avi', '.m4v', '.ts', '.mov', '.wmv', '.iso', '.img'}

    def dir_has_video(dpath):
        for dp, dn, filenames in os.walk(dpath):
            if any(os.path.splitext(f)[1].lower() in video_exts for f in filenames):
                return True
        return False

    outer_name = os.path.basename(real_path)
    has_year = bool(re.search(r'(19|20)\d{2}', outer_name))

    outer_files = [e for e in entries if os.path.isfile(os.path.join(real_path, e))]
    outer_media_files = [f for f in outer_files if os.path.splitext(f)[1].lower() in video_exts]

    # Sammelordner-Bedingungen prüfen
    looks_like_genre = not has_year and len(subdirs) > 0 and any(dir_has_video(os.path.join(real_path, sd)) for sd in subdirs)

    type_id = None
    if looks_like_genre:
        type_id = "genre_container"
    elif len(subdirs) == 1:
        inner_name = subdirs[0]
        if are_folder_names_equivalent(outer_name, inner_name):
            type_id = "nested_duplicate"

    if not type_id:
        return None, "Der Ordner entspricht keiner automatisch auflösbaren Struktur (doppelte Verschachtelung oder Sammelordner).", 400

    conflicts = []
    warnings = []
    items_to_move = []
    folders_to_delete = []
    current_tree = []
    target_tree = []

    if type_id == "nested_duplicate":
        inner_name = subdirs[0]
        inner_path = os.path.join(real_path, inner_name)

        if outer_media_files:
            conflicts.append(f"Äußerer Ordner enthält bereits eigene Mediendateien: {', '.join(outer_media_files)}")

        move_source_path = inner_path
        move_source_rel_parts = [inner_name]
        while True:
            try:
                source_entries = [e for e in os.listdir(move_source_path) if not e.startswith('.')]
            except OSError as e:
                return None, f"Unterordner kann nicht gelesen werden: {e}", 500

            source_subdirs = [e for e in source_entries if os.path.isdir(os.path.join(move_source_path, e))]
            if len(source_entries) == 1 and len(source_subdirs) == 1 and are_folder_names_equivalent(outer_name, source_subdirs[0]):
                next_inner = source_subdirs[0]
                move_source_path = os.path.join(move_source_path, next_inner)
                move_source_rel_parts.append(next_inner)
                continue
            break

        folders_to_delete = [{"path": inner_path, "rel_path": inner_name}]

        for item in source_entries:
            if item.startswith('.'):
                continue
            item_src = os.path.join(move_source_path, item)
            item_dst = os.path.join(real_path, item)
            rel_src = os.path.join(*move_source_rel_parts, item)

            items_to_move.append({
                "src": item_src,
                "dst": item_dst,
                "rel_src": rel_src,
                "rel_dst": item
            })

            if os.path.exists(item_dst):
                conflicts.append(f"Zieldatei/-ordner existiert bereits im Hauptordner: {item}")

            real_src = os.path.realpath(item_src)
            real_dst = os.path.realpath(item_dst)
            if not real_src.startswith(nas_root + os.sep) or not real_dst.startswith(nas_root + os.sep):
                conflicts.append(f"Pfad liegt außerhalb des erlaubten NAS-Verzeichnisses: {item}")

        current_tree.append(outer_name + "/")
        for dp, dn, fn in os.walk(real_path):
            for d in dn:
                if d.startswith('.'): continue
                rp = os.path.relpath(os.path.join(dp, d), real_path)
                current_tree.append(f"{outer_name}/{rp}/")
            for f in fn:
                if f.startswith('.'): continue
                rp = os.path.relpath(os.path.join(dp, f), real_path)
                current_tree.append(f"{outer_name}/{rp}")

        target_tree.append(outer_name + "/")
        for item in entries:
            if item == inner_name or item.startswith('.'):
                continue
            if os.path.isdir(os.path.join(real_path, item)):
                target_tree.append(f"{outer_name}/{item}/")
            else:
                target_tree.append(f"{outer_name}/{item}")

        for item in source_entries:
            if item.startswith('.'):
                continue
            item_src = os.path.join(move_source_path, item)
            if os.path.isdir(item_src):
                target_tree.append(f"{outer_name}/{item}/")
                for sub_dp, sub_dn, sub_fn in os.walk(item_src):
                    for sd in sub_dn:
                        if sd.startswith('.'): continue
                        rp = os.path.relpath(os.path.join(sub_dp, sd), move_source_path)
                        target_tree.append(f"{outer_name}/{rp}/")
                    for sf in sub_fn:
                        if sf.startswith('.'): continue
                        rp = os.path.relpath(os.path.join(sub_dp, sf), move_source_path)
                        target_tree.append(f"{outer_name}/{rp}")
            else:
                target_tree.append(f"{outer_name}/{item}")

    elif type_id == "genre_container":
        parent_path = os.path.dirname(real_path)

        if is_series_dir:
            conflicts.append("Sammelordner-Strukturen werden in Serien-Kategorien nicht unterstützt.")

        if outer_media_files:
            conflicts.append(f"Sammelordner enthält eigene Mediendateien direkt im Hauptordner: {', '.join(outer_media_files)}")

        folders_to_delete = [{"path": real_path, "rel_path": outer_name}]

        for sd in subdirs:
            item_src = os.path.join(real_path, sd)
            item_dst = os.path.join(parent_path, sd)

            # Plausibilitätsprüfung für Filmordner
            has_video = dir_has_video(item_src)
            has_year_in_subdir = bool(re.search(r'(19|20)\d{2}', sd))
            if not has_video and not has_year_in_subdir:
                conflicts.append(f"Unterordner '{sd}' enthält keine Videodateien und sieht nicht wie ein Filmordner aus (keine Jahreszahl im Namen).")

            items_to_move.append({
                "src": item_src,
                "dst": item_dst,
                "rel_src": os.path.join(outer_name, sd),
                "rel_dst": sd
            })

            if os.path.exists(item_dst):
                conflicts.append(f"Zielordner '{sd}' existiert bereits in '{os.path.basename(parent_path)}'.")

            real_src = os.path.realpath(item_src)
            real_dst = os.path.realpath(item_dst)
            if not real_src.startswith(nas_root + os.sep) or not real_dst.startswith(nas_root + os.sep) and real_dst != nas_root:
                conflicts.append(f"Pfad liegt außerhalb des erlaubten NAS-Verzeichnisses: {sd}")

        current_tree.append(outer_name + "/")
        for sd in subdirs:
            current_tree.append(f"{outer_name}/{sd}/")
            for dp, dn, fn in os.walk(os.path.join(real_path, sd)):
                for d in dn:
                    if d.startswith('.'): continue
                    rp = os.path.relpath(os.path.join(dp, d), real_path)
                    current_tree.append(f"{outer_name}/{rp}/")
                for f in fn:
                    if f.startswith('.'): continue
                    rp = os.path.relpath(os.path.join(dp, f), real_path)
                    current_tree.append(f"{outer_name}/{rp}")

        for sd in subdirs:
            target_tree.append(sd + "/")
            for dp, dn, fn in os.walk(os.path.join(real_path, sd)):
                for d in dn:
                    if d.startswith('.'): continue
                    rp = os.path.relpath(os.path.join(dp, d), os.path.join(real_path, sd))
                    target_tree.append(f"{sd}/{rp}/")
                for f in fn:
                    if f.startswith('.'): continue
                    rp = os.path.relpath(os.path.join(dp, f), os.path.join(real_path, sd))
                    target_tree.append(f"{sd}/{rp}")

    current_tree.sort()
    target_tree.sort()

    safe = len(conflicts) == 0

    data = {
        "ok": True,
        "type_id": type_id,
        "path": real_path,
        "outer_name": outer_name,
        "items_to_move": items_to_move,
        "files_to_move": items_to_move, # abwärtskompatibel
        "folders_to_delete": folders_to_delete,
        "current_tree": current_tree,
        "target_tree": target_tree,
        "conflicts": conflicts,
        "warnings": warnings,
        "safe": safe
    }
    if type_id == "nested_duplicate":
        data["inner_name"] = subdirs[0]

    return data, None, 200


@nas_api.route('/nas/structure-fix/preview', methods=['POST'])
def handle_api_structure_fix_preview():
    """Generiert eine detaillierte Vorher/Nachher-Vorschau ohne Änderungen am Dateisystem."""
    try:
        params = request.get_json() or {}
        path = params.get("path")
        if not path:
            return jsonify({"ok": False, "message": "Pfad fehlt."}), 400

        data, err_msg, status_code = _get_structure_fix_preview(path)
        if err_msg:
            return jsonify({"ok": False, "message": err_msg}), status_code
        return jsonify(data)
    except Exception as e:
        return jsonify({"ok": False, "message": f"Fehler bei der Vorschau: {e}"}), 500


@nas_api.route('/nas/structure-fix/apply', methods=['POST'])
def handle_api_structure_fix_apply():
    """Führt das Auflösen der verschachtelten Struktur nach erneuter Validierung aus."""
    try:
        params = request.get_json() or {}
        path = params.get("path")
        if not path:
            return jsonify({"ok": False, "message": "Pfad fehlt."}), 400

        data, err_msg, status_code = _get_structure_fix_preview(path)
        if err_msg:
            return jsonify({"ok": False, "message": err_msg}), status_code

        if not data["safe"]:
            return jsonify({
                "ok": False,
                "message": "Sicherheitsprüfung fehlgeschlagen.",
                "conflicts": data["conflicts"]
            }), 400

        moved_files = []
        skipped_files = []

        # Führe Moves aus
        for f in data["files_to_move"]:
            src = f["src"]
            dst = f["dst"]
            try:
                shutil.move(src, dst)
                moved_files.append(f["rel_dst"])
            except Exception as e:
                log_message(f"❌ [Structure-Fix] Fehler beim Verschieben von {src} nach {dst}: {e}")
                return jsonify({
                    "ok": False,
                    "message": f"Fehler beim Verschieben einer Datei: {e}",
                    "moved_files": moved_files
                }), 500

        # Quarantänisiere/Lösche den nun leeren Unterordner
        inner_path = data["folders_to_delete"][0]["path"]
        removed_folders = []
        warnings = []

        def has_visible_files(folder_path):
            for _, _, filenames in os.walk(folder_path):
                if any(not filename.startswith('.') for filename in filenames):
                    return True
            return False

        try:
            remaining = [e for e in os.listdir(inner_path) if not e.startswith('.')]
            if not remaining or not has_visible_files(inner_path):
                trash.send_to_trash(inner_path, force=True)
                removed_folders.append(data["folders_to_delete"][0]["rel_path"])
            else:
                msg = f"Ordner wurde nicht in Quarantäne verschoben, da er noch andere Dateien enthält: {', '.join(remaining)}"
                warnings.append(msg)
                log_message(f"⚠️ [Structure-Fix] {msg}")
        except Exception as e:
            log_message(f"⚠️ [Structure-Fix] Konnte Ordner {inner_path} nicht in Quarantäne verschieben: {e}")

        # Update Health Issues im Cache
        import gui.core.health as health
        health.remove_issue(path, data["type_id"])

        log_message(f"🔧 [Structure-Fix] Struktur aufgelöst ({data['type_id']}): {path}")
        return jsonify({
            "ok": True,
            "message": "Struktur erfolgreich aufgelöst." if not warnings else f"Struktur aufgelöst. Warnung: {warnings[0]}",
            "moved_files": moved_files,
            "skipped_files": skipped_files,
            "conflicts": [],
            "warnings": warnings,
            "removed_folders": removed_folders
        })

    except Exception as e:
        return jsonify({"ok": False, "message": f"Fehler bei der Ausführung: {e}"}), 500


# ==========================================================================
# Filme normalisieren (Genre-Ordner auflösen + lose Dateien einsammeln)
# ==========================================================================
@nas_api.route('/nas/normalize-films/preview', methods=['GET', 'POST'])
def handle_api_normalize_films_preview():
    """Liefert den Verschiebe-Plan (verschiebt nichts)."""
    import gui.core.film_normalize as fn
    from gui.core.transfers import validate_nas_library_preflight
    from gui.core.utils import load_settings
    settings = load_settings()
    success, err_msg = validate_nas_library_preflight(settings)
    if not success:
        return jsonify({"plan": [], "error": err_msg}), 400
    try:
        return jsonify({"plan": fn.build_plan()})
    except Exception as e:
        return jsonify({"plan": [], "error": str(e)}), 500


@nas_api.route('/nas/normalize-films/apply', methods=['POST'])
def handle_api_normalize_films_apply():
    """Führt die ausgewählten Verschiebungen aus – als Job in der Warteschlange."""
    import gui.core.film_normalize as fn
    import uuid, threading
    from gui.core.transfers import validate_nas_library_preflight
    from gui.core.utils import load_settings
    settings = load_settings()
    success, err_msg = validate_nas_library_preflight(settings)
    if not success:
        return jsonify({"ok": False, "message": err_msg}), 400

    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    items = params.get("items")
    if not isinstance(items, list) or not items:
        return jsonify({"ok": False, "message": "Keine Einträge ausgewählt."}), 400

    task_id = str(uuid.uuid4())
    from gui.core.jobs import create_job, update_job
    pipeline = {
        "normalize": {"status": "running", "progress": 0},
    }
    create_job(
        job_id=task_id,
        name=f"Filme normalisieren ({len(items)})",
        job_type="normalize",
        params={},
        pipeline=pipeline,
        status="running"
    )

    def _run():
        try:
            def _on_progress(idx, total, label):
                pct = int((idx / total) * 100) if total else 100
                update_job(task_id, progress=pct, message=f"Verschiebe {idx + 1}/{total}: {label}",
                           pipeline_step="normalize", pipeline_progress=pct)

            results = fn.apply_moves(items, on_progress=_on_progress)
            moved = results.get("moved", 0)
            skipped = results.get("skipped", 0)
            errors = results.get("errors", [])
            msg = f"{moved} verschoben, {skipped} übersprungen"
            if errors:
                msg += f", {len(errors)} Fehler"
            update_job(task_id, status="done", progress=100, message=msg,
                       pipeline_step="normalize", pipeline_status="done", pipeline_progress=100)
        except Exception as e:
            update_job(task_id, status="error", message=f"Fehler: {e}",
                       pipeline_step="normalize", pipeline_status="error")

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"ok": True, "task_id": task_id, "message": "In Warteschlange eingereiht."})
