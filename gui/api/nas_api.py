import os, sys, json, time, shutil, subprocess, urllib, threading, math
from flask import Blueprint, request, jsonify, Response, send_file, send_from_directory
from gui.core.utils import load_settings, save_settings, clean_show_name, load_show_profile, save_show_profile, load_konv_history
from gui.core.helpers import *
from gui.core.helpers import log_queue
from gui.core.transfers import *
from gui.workers.processor import *
from gui.workers.youtube_worker import *
import gui.core.media as media
import gui.mw_metadata as mw_metadata

nas_api = Blueprint('nas_api', __name__)

# Global variables imported from processor
from gui.workers.processor import JOB_QUEUE, SYSTEM_STATUS, STATUS_LOCK



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
        return
    
    try:
        ep_num = int(ep_num)
        ep_season = int(ep_season)
    except (ValueError, TypeError):
        return jsonify({"duplicate": None})
        return
    
    settings = load_settings()
    nas_root = settings.get("nas_root", "/Volumes/Kino")
    
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
        return
    
    # Also check outbox for matched series name
    outbox_root = settings.get("outbox_dir", os.path.expanduser("~/Downloads/Medien Output"))
    rel_dest = os.path.relpath(destination, nas_root)
    outbox_serien = os.path.join(outbox_root, rel_dest)
    clean_show_name = get_matched_series_name(destination, outbox_serien, limit_filename_length(sanitize_filename(clean_show_name)))
    
    show_dir = os.path.join(destination, clean_show_name)
    
    if not os.path.exists(show_dir):
        return jsonify({"duplicate": None})
        return
    
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
                return
    
    return jsonify({"duplicate": None})



@nas_api.route('/streamfab-import', methods=['GET', 'POST'])
def handle_api_streamfab_import():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
        
    if request.method == 'GET':
        preview_data = preview_streamfab_import()
        return jsonify({"status": "ok", "preview": preview_data})
        
    elif request.method == 'POST':
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
    nas_root = settings.get("nas_root", "/Volumes/Kino")
    outbox_root = settings.get("outbox_dir", os.path.expanduser("~/Downloads/Medien Output"))
    
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
        return jsonify({"seasons": [], "folder": folder_name})
        
    settings = load_settings()
    ensure_nas_mounted()
    nas_root = settings.get("nas_root", "/Volumes/Kino")
    outbox_root = settings.get("outbox_dir", os.path.expanduser("~/Downloads/Medien Output"))
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
            matched_folder = get_matched_series_name(dest_path, outbox_dest, clean_show)
        
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
        return
        
    # Security validation for paths
    settings = load_settings()
    inbox_root = settings.get("inbox_dir", os.path.expanduser("~/Downloads/Medien Input"))
    nas_root = settings.get("nas_root", "/Volumes/Kino")
    
    # Ensure we only check files in allowed directories
    abs_new = os.path.abspath(new_path)
    abs_existing = os.path.abspath(existing_path)
    
    if not (abs_new.startswith(os.path.abspath(inbox_root) + os.sep) or abs_new == os.path.abspath(inbox_root)):
        return jsonify({"error": "Forbidden new_path"}), 403
        return
        
    if not (abs_existing.startswith(os.path.abspath(nas_root) + os.sep) or abs_existing == os.path.abspath(nas_root)):
        return jsonify({"error": "Forbidden existing_path"}), 403
        return
        
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



@nas_api.route('/resolve-duplicate', methods=['GET', 'POST'])
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
        return
        
    # Security validation for paths
    settings = load_settings()
    nas_root = settings.get("nas_root", "/Volumes/Kino")
    abs_existing = os.path.abspath(existing_path)
    
    if not (abs_existing.startswith(os.path.abspath(nas_root) + os.sep) or abs_existing == os.path.abspath(nas_root)):
        return jsonify({"error": "Forbidden existing_path"}), 403
        return
        
    if action == "upgrade":
        try:
            os.remove(existing_path)
            log_message(f"🗑️ [Dubletten-Upgrade] Existierende Datei auf NAS gelöscht: {existing_path}")
            
            # Delete corresponding nfo / artwork if present
            base_path = os.path.splitext(existing_path)[0]
            for ext in [".nfo", ".srt", "-poster.jpg", "-fanart.jpg"]:
                art_file = base_path + ext
                if os.path.exists(art_file):
                    try:
                        os.remove(art_file)
                        log_message(f"  🗑️ Zugehörige Datei gelöscht: {art_file}")
                    except Exception:
                        pass
                        
            return jsonify({"status": "success", "message": "Existierende Datei gelöscht. Bereit für Upgrade."})
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

    action = params.get("action")
    path = params.get("path")
    new_name = params.get("new_name", "").strip()

    if not path or not os.path.isdir(path):
        return jsonify({"ok": False, "message": "Ordner nicht gefunden."}), 400

    settings = load_settings()
    nas_root = os.path.realpath(settings.get("nas_root", "/Volumes/Kino"))
    real_path = os.path.realpath(path)
    if not real_path.startswith(nas_root + os.sep):
        return jsonify({"ok": False, "message": "Pfad liegt außerhalb des NAS."}), 403

    try:
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
                shutil.rmtree(inner)
            log_message(f"🔧 [Health-Fix] Verschachtelung aufgelöst: {path}")
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
            return jsonify({"ok": True, "message": f"Ordner und {len(renamed)} Datei(en) umbenannt zu '{new_name}'."})

        return jsonify({"ok": False, "message": f"Unbekannte Aktion: {action}"}), 400

    except Exception as e:
        return jsonify({"ok": False, "message": f"Fehler: {e}"}), 500


# ==========================================================================
# Filme normalisieren (Genre-Ordner auflösen + lose Dateien einsammeln)
# ==========================================================================
@nas_api.route('/nas/normalize-films/preview', methods=['GET', 'POST'])
def handle_api_normalize_films_preview():
    """Liefert den Verschiebe-Plan (verschiebt nichts)."""
    import gui.core.film_normalize as fn
    try:
        return jsonify({"plan": fn.build_plan()})
    except Exception as e:
        return jsonify({"plan": [], "error": str(e)}), 500


@nas_api.route('/nas/normalize-films/apply', methods=['POST'])
def handle_api_normalize_films_apply():
    """Führt die ausgewählten Verschiebungen aus – als Job in der Warteschlange."""
    import gui.core.film_normalize as fn
    import uuid, threading
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    items = params.get("items")
    if not isinstance(items, list) or not items:
        return jsonify({"ok": False, "message": "Keine Einträge ausgewählt."}), 400

    task_id = str(uuid.uuid4())
    job_info = {
        "id": task_id,
        "type": "normalize",
        "name": f"Filme normalisieren ({len(items)})",
        "status": "running",
        "progress": 0,
        "message": "Starte Verschiebungen…",
        "timestamp": time.time(),
        "params": {},
        "pipeline": {
            "normalize": {"status": "running", "progress": 0},
        },
    }
    with active_jobs_lock:
        active_jobs[task_id] = job_info

    def _run():
        try:
            def _on_progress(idx, total, label):
                pct = int((idx / total) * 100) if total else 100
                with active_jobs_lock:
                    active_jobs[task_id]["progress"] = pct
                    active_jobs[task_id]["message"] = f"Verschiebe {idx + 1}/{total}: {label}"
                    active_jobs[task_id]["pipeline"]["normalize"]["progress"] = pct

            results = fn.apply_moves(items, on_progress=_on_progress)
            moved = results.get("moved", 0)
            skipped = results.get("skipped", 0)
            errors = results.get("errors", [])
            msg = f"{moved} verschoben, {skipped} übersprungen"
            if errors:
                msg += f", {len(errors)} Fehler"
            with active_jobs_lock:
                active_jobs[task_id]["status"] = "done"
                active_jobs[task_id]["progress"] = 100
                active_jobs[task_id]["message"] = msg
                active_jobs[task_id]["pipeline"]["normalize"]["status"] = "done"
                active_jobs[task_id]["pipeline"]["normalize"]["progress"] = 100
        except Exception as e:
            with active_jobs_lock:
                active_jobs[task_id]["status"] = "error"
                active_jobs[task_id]["message"] = f"Fehler: {e}"
                active_jobs[task_id]["pipeline"]["normalize"]["status"] = "error"

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"ok": True, "task_id": task_id, "message": "In Warteschlange eingereiht."})


