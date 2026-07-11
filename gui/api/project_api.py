import os, sys, json, time, shutil, subprocess, urllib, threading, re
from flask import Blueprint, request, jsonify, Response, send_from_directory
from gui.core.utils import load_settings, save_settings, clean_show_name, load_show_profile, save_show_profile, load_konv_history, get_runtime_capabilities
from gui.core.helpers import *
from gui.core.helpers import log_queue
from gui.core.transfers import *
from gui.workers.processor import *
from gui.workers.youtube_worker import *
import gui.core.media as media
import gui.mw_metadata as mw_metadata

project_api = Blueprint('project_api', __name__)

# Global variables imported from processor
from gui.workers.processor import SYSTEM_STATUS


EFFICIENT_VIDEO_CODECS = {
    'hevc',
    'h265',
    'hvc1',
    'x265',
    'vp9',
    'vp09',
    'av1',
    'av01',
}


def is_efficient_video_codec(codec):
    if not codec:
        return False
    normalized = str(codec).strip().lower()
    return normalized in EFFICIENT_VIDEO_CODECS


def get_clean_search_name(folder_name):
    if not folder_name:
        return ""
    import re
    cleaned = re.sub(r'\s*\[(tvdb|tmdb|tmdb_tv|tmdb_movie|ofdb|manual)\]', '', folder_name, flags=re.IGNORECASE)
    cleaned = re.sub(r'(?i)\s*(staffel|season|episodes?|folgen?)\s*\d+.*$', '', cleaned)
    cleaned = re.sub(r'(?i)\s*s\d+.*$', '', cleaned)
    cleaned = cleaned.strip(" -._")
    return cleaned



@project_api.route('/browse-folder', methods=['GET', 'POST'])
def handle_api_browse_folder():
    caps = get_runtime_capabilities()
    if not caps["capabilities"]["open_local_folder"]:
        return jsonify({"error": "Ordnerauswahl ist im Docker-Betrieb deaktiviert."}), 403

    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    query = request.args
    default_path = request.args.get("default_path", "")
    if default_path:
        default_path = os.path.abspath(os.path.expanduser(default_path))
        
    if default_path and os.path.exists(default_path) and os.path.isdir(default_path):
        pass
    else:
        default_path = ""
        
    script = '''
    on run argv
        set defaultPath to item 1 of argv
        -- Bring osascript dialog to front directly
        activate
        try
            if defaultPath is not "" then
                set f to choose folder with prompt "Wähle einen Ordner:" default location (POSIX file defaultPath)
            else
                set f to choose folder with prompt "Wähle einen Ordner:"
            end if
            return POSIX path of f
        on error errStr
            return "ERROR:" & errStr
        end try
    end run
    '''
    try:
        result = subprocess.run(["osascript", "-", default_path], input=script, capture_output=True, text=True)
        folder_path = result.stdout.strip()
        print(f"[DEBUG-BROWSE] osascript stdout: {repr(folder_path)}", flush=True)
        if result.stderr:
            print(f"[DEBUG-BROWSE] osascript stderr: {repr(result.stderr)}", flush=True)
            
        if folder_path.startswith("ERROR:"):
            return jsonify({"status": "error", "message": folder_path})
            
        return jsonify({"status": "ok", "path": folder_path})
    except Exception as e:
        print(f"[DEBUG-BROWSE] Exception: {e}", flush=True)
        return jsonify({"status": "error", "message": str(e)})



@project_api.route('/list-subfolders', methods=['GET', 'POST'])
def handle_api_list_subfolders():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    query = request.args
    path_str = query.get("path")
    if not path_str:
        return jsonify({"error": "Pfad-Parameter fehlt."})
        
    folder_path = os.path.abspath(os.path.expanduser(path_str))
    if not os.path.exists(folder_path):
        return jsonify({"error": f"Pfad existiert nicht: {folder_path}"})
        
    if not os.path.isdir(folder_path):
        return jsonify({"error": f"Pfad ist kein Ordner: {folder_path}"})
        
    if not is_path_allowed(folder_path):
        return jsonify({"error": "Zugriff verweigert (Pfad nicht in erlaubten Verzeichnissen)."})
        
    try:
        subfolders = []
        for item in os.listdir(folder_path):
            if item.startswith('.'):
                continue
            item_path = os.path.join(folder_path, item)
            if os.path.isdir(item_path):
                subfolders.append(item)
        subfolders.sort()
        return jsonify({"status": "ok", "subfolders": subfolders})
    except Exception as e:
        return jsonify({"error": str(e)})



@project_api.route('/scan-project', methods=['GET', 'POST'])
def handle_api_scan_project():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    query = request.args
    project = query.get("project", "")
    settings = load_settings()
    inbox_root = settings.get("inbox_dir", "")
    if not inbox_root:
        return jsonify({"error": "Inbox-Verzeichnis ist nicht konfiguriert."}), 400
        
    is_recursive_inbox = (project == "__inbox_recursive__")
    if project and os.path.isabs(project):
        target_dir = os.path.abspath(project)
    elif project and not is_recursive_inbox:
        if not inbox_root:
            return jsonify({"error": "Inbox-Verzeichnis ist nicht konfiguriert."}), 400
        target_dir = os.path.abspath(os.path.join(inbox_root, project))
    else:
        if not inbox_root:
            return jsonify({"error": "Inbox-Verzeichnis ist nicht konfiguriert."}), 400
        target_dir = os.path.abspath(inbox_root)
        
    if not is_path_allowed(target_dir):
        return jsonify({"error": "Access Denied"}), 403

    if not os.path.exists(target_dir):
        return jsonify({"error": "Directory not found"}), 404

    is_single_file = os.path.isfile(target_dir)
    target_parent = os.path.dirname(target_dir) if is_single_file else target_dir

    file_list = []
    ext_counts = {}
    
    # Scannen des Verzeichnisses (nur Hauptebene für die Inbox, rekursiv für Projektordner)
    if not project:
        all_files = [f for f in os.listdir(target_dir) if os.path.isfile(os.path.join(target_dir, f)) and not f.startswith('.')]
    else:
        if is_single_file:
            all_files = [os.path.basename(target_dir)]
        else:
            all_files = find_files_recursively(target_dir)
    for f in all_files:
        file_list.append(f)
        ext = os.path.splitext(f)[1].lower()[1:]
        if not ext:
            ext = "ohne_endung"
        ext_counts[ext] = ext_counts.get(ext, 0) + 1
            
    # Count videos
    video_count = sum(ext_counts.get(ext, 0) for ext in ['mp4', 'mkv', 'avi', 'webm', 'mov'])
    
    # Check if project folder name contains doku or if any NFO file inside it contains doku keywords
    is_doku = False
    if project and ("doku" in project.lower() or "dokumentation" in project.lower()):
        is_doku = True
    
    if not is_doku:
        # Let's search for .nfo files in the target directory
        for f in all_files:
            if f.lower().endswith(".nfo"):
                nfo_path = os.path.join(target_dir, f)
                if os.path.exists(nfo_path):
                    try:
                        with open(nfo_path, 'r', encoding='utf-8', errors='ignore') as nfo_f:
                            content = nfo_f.read().lower()
                            if "doku" in content or "dokumentation" in content or "documentary" in content:
                                is_doku = True
                                break
                    except Exception as e:
                        log_message(f"Fehler beim Lesen der NFO-Datei {f}: {e}")
    
    # Get video files list
    video_extensions = {'.mp4', '.mkv', '.avi', '.webm', '.mov'}
    video_files = [os.path.join(target_parent, f) for f in all_files if os.path.splitext(f)[1].lower() in video_extensions]
    
    has_inefficient_video = False
    if video_files:
        # Check up to 10 video files to avoid huge scans
        files_to_check = video_files[:10]
        from concurrent.futures import ThreadPoolExecutor
        
        try:
            with ThreadPoolExecutor(max_workers=min(len(files_to_check), 5)) as executor:
                codecs = list(executor.map(media.get_video_codec, files_to_check))
            
            for codec in codecs:
                if codec and not is_efficient_video_codec(codec):
                    has_inefficient_video = True
                    break
        except Exception as e:
            log_message(f"Fehler bei der Codec-Erkennung: {e}")
    
    # Determine suggested search query
    folder_base = project if not is_single_file else os.path.splitext(project)[0]
    suggested_query = folder_base
    is_obfuscated = False
    if folder_base:
        # Check if there are any separators
        separators = {'.', '_', '-', ' '}
        has_separator = any(c in folder_base for c in separators)
        if not has_separator and len(folder_base) >= 10:
            is_obfuscated = True
            
    if video_files:
        # Get the first video file's base name
        first_video = video_files[0]
        video_base = os.path.basename(first_video)
        video_base_no_ext = os.path.splitext(video_base)[0]
        suggested_query = get_cleaner_suggested_query(folder_base, video_base_no_ext)

    # Clean up suggested_query from episode / season suffix patterns
    if suggested_query:
        # Replace underscores and dots with spaces for robust matching, and normalize hyphens
        normalized = suggested_query.replace("_", " ").replace(".", " ")
        normalized = re.sub(r'\s*-\s*', ' - ', normalized)
        # Collapse multiple spaces
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # S01E01 etc.
        match = re.search(r'(?i)\s+s\d+e\d+', normalized)
        if match:
            suggested_query = normalized[:match.start()].strip()
        else:
            # " - " separators
            parts = re.split(r'\s+-\s+', normalized)
            if len(parts) > 1:
                suggested_query = parts[0].strip()
            else:
                # Episode in parentheses like (587)
                match2 = re.search(r'\s+\(\d+\)', normalized)
                if match2:
                    suggested_query = normalized[:match2.start()].strip()
                else:
                    # "Folge 1" or "Staffel 1"
                    match3 = re.search(r'(?i)\s+(folge|staffel|episode)\s+\d+', normalized)
                    if match3:
                        suggested_query = normalized[:match3.start()].strip()
                    else:
                        suggested_query = normalized
    
    # Parse tvshow.nfo or movie NFO for existing metadata
    metadata_provider = None
    metadata_id = None
    metadata_name = None
    metadata_year = None
    metadata_plot = None
    file_nfo_statuses = {}
    
    metadata_source = None

    # TV Show
    nfo_file = next((f for f in all_files if os.path.basename(f).lower() == "tvshow.nfo"), None)
    nfo_path = None
    if nfo_file:
        nfo_path = os.path.join(target_dir, nfo_file)
    else:
        target_basename = os.path.basename(target_dir)
        is_season_folder = bool(re.search(r'(staffel|season|^s\d+$)', target_basename, re.IGNORECASE))
        if is_season_folder:
            parent_dir = os.path.dirname(target_dir)
            if is_path_allowed(parent_dir):
                parent_nfo_path = os.path.join(parent_dir, "tvshow.nfo")
                if os.path.exists(parent_nfo_path):
                    nfo_path = parent_nfo_path

    if nfo_path:
        if os.path.exists(nfo_path):
            try:
                import xml.etree.ElementTree as ET
                tree = ET.parse(nfo_path)
                root = tree.getroot()
                
                provider_el = root.find("mw_provider")
                showid_el = root.find("mw_showid")
                title_el = root.find("title")
                
                if provider_el is not None and provider_el.text:
                    metadata_provider = provider_el.text.strip()
                else:
                    if root.find("tvdbid") is not None:
                        metadata_provider = "tvdb"
                    elif root.find("tmdbid") is not None:
                        metadata_provider = "tmdb_tv"
                
                if showid_el is not None and showid_el.text:
                    metadata_id = showid_el.text.strip()
                else:
                    if metadata_provider == "tvdb" and root.find("tvdbid") is not None:
                        metadata_id = root.find("tvdbid").text.strip()
                    elif metadata_provider == "tmdb_tv" and root.find("tmdbid") is not None:
                        metadata_id = root.find("tmdbid").text.strip()
                        
                if title_el is not None and title_el.text:
                    metadata_name = title_el.text.strip()

                year_el = root.find("year")
                if year_el is not None and year_el.text:
                    metadata_year = year_el.text.strip()
                plot_el = root.find("plot")
                if plot_el is not None and plot_el.text:
                    metadata_plot = plot_el.text.strip()
                metadata_source = "nfo"
            except Exception as e:
                log_message(f"Fehler beim Parsen von tvshow.nfo: {e}")
                
    # Movie
    movie_nfo = next((f for f in all_files if os.path.basename(f).lower() == "movie.nfo" or (f.lower().endswith(".nfo") and os.path.basename(f).lower() != "tvshow.nfo")), None)
    if movie_nfo and not metadata_id:
        nfo_path = os.path.join(target_dir, movie_nfo)
        if os.path.exists(nfo_path):
            try:
                import xml.etree.ElementTree as ET
                tree = ET.parse(nfo_path)
                root = tree.getroot()
                if root.tag == "movie":
                    tmdb_el = root.find("tmdbid")
                    title_el = root.find("title")
                    provider_el = root.find("mw_provider")
                    
                    if provider_el is not None and provider_el.text:
                        metadata_provider = provider_el.text.strip()
                    else:
                        metadata_provider = "tmdb_movie"
                        
                    if tmdb_el is not None and tmdb_el.text:
                        metadata_id = tmdb_el.text.strip()
                    elif root.find("uniqueid") is not None:
                        metadata_id = root.find("uniqueid").text.strip()
                        
                    if title_el is not None and title_el.text:
                        metadata_name = title_el.text.strip()

                    year_el = root.find("year")
                    if year_el is not None and year_el.text:
                        metadata_year = year_el.text.strip()
                    plot_el = root.find("plot")
                    if plot_el is not None and plot_el.text:
                        metadata_plot = plot_el.text.strip()
                    metadata_source = "nfo"
            except Exception as e:
                log_message(f"Fehler beim Parsen von movie.nfo: {e}")
                
    # Profile Fallback for TV Shows if no NFO was found
    if not metadata_id:
        target_basename = os.path.basename(target_dir)
        is_season_folder = bool(re.search(r'(staffel|season|^s\d+$)', target_basename, re.IGNORECASE))
        profile_name = os.path.basename(os.path.dirname(target_dir)) if is_season_folder else target_basename
        profile_name = get_clean_search_name(profile_name)
        if profile_name:
            profile = load_show_profile(profile_name)
            if profile and not profile.get("error") and profile.get("show_id"):
                metadata_provider = profile.get("provider")
                metadata_id = profile.get("show_id")
                metadata_name = profile.get("show_name")
                metadata_source = "profile"

    # Determine suggested search name
    suggested_search_name = None
    if metadata_name:
        suggested_search_name = metadata_name
        if metadata_year and metadata_year not in metadata_name:
            suggested_search_name = f"{metadata_name} ({metadata_year})"
    else:
        target_basename = os.path.basename(target_dir)
        is_season_folder = bool(re.search(r'(staffel|season|^s\d+$)', target_basename, re.IGNORECASE))
        if is_season_folder:
            parent_dir = os.path.dirname(target_dir)
            folder_name_to_clean = os.path.basename(parent_dir)
        else:
            folder_name_to_clean = target_basename
        suggested_search_name = get_clean_search_name(folder_name_to_clean)
        
    if suggested_search_name:
        suggested_search_name = suggested_search_name.strip()

    # Check each video file's NFO status
    for f in all_files:
        if os.path.splitext(f)[1].lower() in video_extensions:
            nfo_rel = os.path.splitext(f)[0] + ".nfo"
            nfo_path = os.path.join(target_dir, nfo_rel)
            exists = os.path.exists(nfo_path)
            complete = False
            if exists:
                try:
                    import xml.etree.ElementTree as ET
                    tree = ET.parse(nfo_path)
                    root = tree.getroot()
                    title_el = root.find("title")
                    plot_el = root.find("plot")
                    title_missing = title_el is None or not title_el.text or not title_el.text.strip()
                    plot_missing = plot_el is None or not plot_el.text or not plot_el.text.strip()
                    complete = not (title_missing or plot_missing)
                except Exception:
                    complete = False
            file_nfo_statuses[f] = {"exists": exists, "complete": complete}
            
    return jsonify({
        "current_dir": target_dir,
        "files": file_list,
        "video_count": video_count,
        "ext_counts": ext_counts,
        "is_doku": is_doku,
        "has_inefficient_video": has_inefficient_video,
        "suggested_query": suggested_query,
        "is_single_file": is_single_file,
        "metadata_provider": metadata_provider,
        "metadata_id": metadata_id,
        "metadata_name": metadata_name,
        "metadata_year": metadata_year,
        "metadata_plot": metadata_plot,
        "metadata_source": metadata_source,
        "suggested_search_name": suggested_search_name,
        "file_nfo_statuses": file_nfo_statuses
    })



@project_api.route('/preview-clean', methods=['GET', 'POST'])
@project_api.route('/preview_clean', methods=['GET', 'POST'])
def handle_api_preview_clean():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    query = request.args
    project = params.get("project", "") or query.get("project", "")
    settings = load_settings()
    inbox_root = settings.get("inbox_dir", "")
    if not inbox_root:
        return jsonify({"error": "Inbox-Verzeichnis ist nicht konfiguriert."}), 400
        
    is_recursive_inbox = (project == "__inbox_recursive__")
    if project and not is_recursive_inbox:
        target_dir = os.path.abspath(os.path.join(inbox_root, project))
    else:
        target_dir = os.path.abspath(inbox_root)
        
    if not os.path.exists(target_dir):
        return jsonify({"error": "Verzeichnis nicht gefunden"})
        
    if not project:
        all_files = [f for f in os.listdir(target_dir) if os.path.isfile(os.path.join(target_dir, f)) and not f.startswith('.')]
    else:
        all_files = find_files_recursively(target_dir)
        
    video_extensions = {'.mp4', '.mkv', '.avi', '.webm', '.mov'}
    groups = {}
    for f in all_files:
        ext = os.path.splitext(f)[1].lower()
        ext_clean = ext[1:] if ext.startswith('.') else ext
        if not ext_clean:
            ext_clean = "ohne_endung"
            
        full_path = os.path.join(target_dir, f)
        file_info = {
            "name": f,
            "size_bytes": 0,
            "codec": None,
            "resolution": None
        }
        try:
            file_info["size_bytes"] = os.path.getsize(full_path)
        except OSError:
            pass
            
        if ext in video_extensions:
            try:
                m_info = media.get_media_info(full_path)
                if m_info.get("codec"):
                    file_info["codec"] = m_info["codec"]
                if m_info.get("width") and m_info.get("height"):
                    file_info["resolution"] = f"{m_info['width']}x{m_info['height']}"
            except Exception:
                pass
                
        if ext_clean not in groups:
            groups[ext_clean] = []
        groups[ext_clean].append(file_info)
        
    return jsonify({"groups": groups})



@project_api.route('/paths-preview-clean', methods=['GET', 'POST'])
@project_api.route('/paths/preview_clean', methods=['GET', 'POST'])
def handle_api_paths_preview_clean():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    query = request.args
    try:
        settings = load_settings()
        inbox_dir = settings.get("inbox_dir")
        outbox_dir = settings.get("outbox_dir")
        
        scan_inbox = params.get("inbox", False)
        scan_output = params.get("output", False)
        
        inbox_files = []
        output_files = []
        
        if scan_inbox and inbox_dir and os.path.exists(inbox_dir):
            files = find_files_recursively(inbox_dir)
            for f in files:
                full_path = os.path.join(inbox_dir, f)
                try:
                    sz = os.path.getsize(full_path)
                except Exception:
                    sz = 0
                inbox_files.append({"rel_path": f, "size_bytes": sz})
                
        if scan_output and outbox_dir and os.path.exists(outbox_dir):
            files = find_files_recursively(outbox_dir)
            for f in files:
                full_path = os.path.join(outbox_dir, f)
                try:
                    sz = os.path.getsize(full_path)
                except Exception:
                    sz = 0
                output_files.append({"rel_path": f, "size_bytes": sz})
                
        return jsonify({
            "inbox_files": inbox_files,
            "output_files": output_files
        })
    except Exception as e:
        return jsonify({"error": f"Fehler beim Scannen der Medienpfade: {e}"})



@project_api.route('/paths-clean', methods=['POST'])
@project_api.route('/paths/clean', methods=['POST'])
def handle_api_paths_clean():

    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    query = request.args
    try:
        settings = load_settings()
        inbox_dir = settings.get("inbox_dir")
        outbox_dir = settings.get("outbox_dir")
        
        inbox_files = params.get("inbox_files", [])
        output_files = params.get("output_files", [])
        
        deleted_files = []
        deleted_dirs = []
        
        # Lösche Dateien aus Inbox
        if inbox_dir and os.path.exists(inbox_dir):
            for f in inbox_files:
                path_f = os.path.join(inbox_dir, f)
                path_f = os.path.abspath(path_f)
                if not is_path_allowed(path_f) or not path_f.startswith(os.path.abspath(inbox_dir) + os.sep):
                    continue
                if os.path.exists(path_f):
                    try:
                        trash.send_to_trash(path_f, force=True)
                        deleted_files.append(f"inbox/{f}")
                    except Exception as e:
                        return jsonify({"error": f"Quarantäne-Fehler bei inbox/{f}: {e}"}), 500
                        
        # Lösche Dateien aus Output
        if outbox_dir and os.path.exists(outbox_dir):
            for f in output_files:
                path_f = os.path.join(outbox_dir, f)
                path_f = os.path.abspath(path_f)
                if not is_path_allowed(path_f) or not path_f.startswith(os.path.abspath(outbox_dir) + os.sep):
                    continue
                if os.path.exists(path_f):
                    try:
                        trash.send_to_trash(path_f, force=True)
                        deleted_files.append(f"output/{f}")
                    except Exception as e:
                        return jsonify({"error": f"Quarantäne-Fehler bei output/{f}: {e}"}), 500
                        
        # Leere Ordner aufräumen
        def cleanup_empty_dirs(base_dir):
            cleaned = []
            for root, dirs, files in os.walk(base_dir, topdown=False):
                for d in dirs:
                    dir_path = os.path.join(root, d)
                    try:
                        if not os.listdir(dir_path):
                            trash.send_to_trash(dir_path, force=True)
                            cleaned.append(os.path.relpath(dir_path, base_dir))
                    except Exception as e:
                        log_message(f"⚠️ Leerer Ordner konnte nicht in Quarantäne verschoben werden: {dir_path} ({e})")
            return cleaned

        if inbox_dir and os.path.exists(inbox_dir):
            cleaned_inbox = cleanup_empty_dirs(inbox_dir)
            deleted_dirs.extend([f"inbox/{d}" for d in cleaned_inbox])
            
        if outbox_dir and os.path.exists(outbox_dir):
            cleaned_outbox = cleanup_empty_dirs(outbox_dir)
            deleted_dirs.extend([f"output/{d}" for d in cleaned_outbox])
            
        return jsonify({
            "status": "ok",
            "deleted_files": deleted_files,
            "deleted_dirs": deleted_dirs
        })
    except Exception as e:
        return jsonify({"error": f"Fehler beim Bereinigen der Medienpfade: {e}"})



@project_api.route('/clean-project', methods=['POST'])
def handle_api_clean_project():

    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    query = request.args
    project = params.get("project", "") or query.get("project", "")
    settings = load_settings()
    inbox_root = settings.get("inbox_dir", "")
    if not inbox_root:
        return jsonify({"error": "Inbox-Verzeichnis ist nicht konfiguriert."}), 400
        
    is_recursive_inbox = (project == "__inbox_recursive__")
    if project and not is_recursive_inbox:
        target_dir = os.path.abspath(os.path.join(inbox_root, project))
    else:
        target_dir = os.path.abspath(inbox_root)
        
    if not is_path_allowed(target_dir):
        return jsonify({"error": "Access Denied"})
    deleted_files = []
    deleted_dirs = []
    
    explicit_files = params.get("explicit_files")
    
    if explicit_files is not None:
        # Neuer interaktiver Modus: Lösche nur, was der Benutzer ausgewählt hat
        for f in explicit_files:
            path_f = os.path.join(target_dir, f)
            # Security: prevent path traversal
            path_f = os.path.abspath(path_f)
            if not path_f.startswith(os.path.abspath(target_dir) + os.sep) and path_f != os.path.abspath(target_dir):
                continue
            if os.path.exists(path_f):
                try:
                    trash.send_to_trash(path_f, force=True)
                    deleted_files.append(f)
                except Exception as e:
                    log_message(f"⚠️ Datei konnte nicht in Quarantäne verschoben werden: {path_f} ({e})")
                    
        # Leere Ordner aufräumen
        for root, dirs, files in os.walk(target_dir, topdown=False):
            if root == target_dir: continue
            if not os.listdir(root):
                try:
                    trash.send_to_trash(root, force=True)
                    deleted_dirs.append(os.path.relpath(root, target_dir))
                except Exception as e:
                    log_message(f"⚠️ Leerer Ordner konnte nicht in Quarantäne verschoben werden: {root} ({e})")
    else:
        # Alter Fallback (löscht pauschal txt/url)
        for root, dirs, files in os.walk(target_dir, topdown=False):
            for f in files:
                if f.startswith("."):
                    continue
                ext = os.path.splitext(f)[1].lower()
                if ext in ['.txt', '.url']:
                    path_f = os.path.join(root, f)
                    try:
                        trash.send_to_trash(path_f, force=True)
                        deleted_files.append(os.path.relpath(path_f, target_dir))
                    except Exception as e:
                        log_message(f"⚠️ Datei konnte nicht in Quarantäne verschoben werden: {path_f} ({e})")
            for d in dirs:
                path_d = os.path.join(root, d)
                if not os.listdir(path_d):
                    try:
                        trash.send_to_trash(path_d, force=True)
                        deleted_dirs.append(os.path.relpath(path_d, target_dir))
                    except Exception as e:
                        log_message(f"⚠️ Leerer Ordner konnte nicht in Quarantäne verschoben werden: {path_d} ({e})")
                        
    return jsonify({
        "status": "ok",
        "deleted_files": deleted_files,
        "deleted_dirs": deleted_dirs
    })



@project_api.route('/delete-project', methods=['POST'])
def handle_api_delete_project():

    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    query = request.args
    project = params.get("project")
    if not project:
        return jsonify({"status": "error", "error": "Kein Ordnername angegeben."})
        
    if project == "__inbox_recursive__":
        return jsonify({"status": "error", "error": "System-Ordner kann nicht gelöscht werden."})
        
    settings = load_settings()
    inbox_root = settings.get("inbox_dir", "")
    if not inbox_root:
        return jsonify({"status": "error", "error": "Inbox-Verzeichnis ist nicht konfiguriert."})
    
    target_dir = os.path.join(inbox_root, project)
    inbox_root_abs = os.path.abspath(inbox_root)
    target_dir_abs = os.path.abspath(target_dir)
    
    # Security check: Ensure target is inside inbox_root and not the root itself
    if not target_dir_abs.startswith(inbox_root_abs + os.sep) or target_dir_abs == inbox_root_abs:
        return jsonify({"status": "error", "error": "Ungültiger oder unzulässiger Pfad."})
        
    if not os.path.exists(target_dir_abs):
        return jsonify({"status": "error", "error": "Ordner existiert nicht."})
        
    try:
        trash.send_to_trash(target_dir_abs, force=True)
        def log_message(m): print(m)
        log_message(f"🗑️ Ordner erfolgreich in Quarantäne verschoben: {project}")
        return jsonify({"status": "success"})
    except trash.TrashError as e:
        return jsonify({"status": "error", "error": str(e)})
    except Exception as e:
        def log_message(m): print(m)
        log_message(f"❌ Fehler beim Löschen des Ordners {project}: {e}")
        return jsonify({"status": "error", "error": str(e)})



@project_api.route('/merge-projects', methods=['POST'])
def handle_api_merge_projects():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
        
    source = params.get("source")
    target = params.get("target")
    
    if not source or not target:
        return jsonify({"status": "error", "error": "Quell- und Zielordner müssen angegeben werden."})
        
    if source == "__inbox_recursive__" or target == "__inbox_recursive__":
        return jsonify({"status": "error", "error": "System-Ordner können nicht zusammengeführt werden."})
        
    settings = load_settings()
    inbox_root = settings.get("inbox_dir", "")
    if not inbox_root:
        return jsonify({"status": "error", "error": "Inbox-Verzeichnis ist nicht konfiguriert."})
    inbox_root_abs = os.path.abspath(inbox_root)
    
    source_dir = os.path.join(inbox_root, source)
    source_dir_abs = os.path.abspath(source_dir)
    
    target_dir = os.path.join(inbox_root, target)
    target_dir_abs = os.path.abspath(target_dir)
    
    # Security check: Ensure both are inside inbox_root and not the root itself
    if not source_dir_abs.startswith(inbox_root_abs + os.sep) or source_dir_abs == inbox_root_abs:
        return jsonify({"status": "error", "error": "Ungültiger oder unzulässiger Pfad für den Quellordner."})
    if not target_dir_abs.startswith(inbox_root_abs + os.sep) or target_dir_abs == inbox_root_abs:
        return jsonify({"status": "error", "error": "Ungültiger oder unzulässiger Pfad für den Zielordner."})
        
    if not os.path.exists(source_dir_abs):
        return jsonify({"status": "error", "error": f"Quellordner '{source}' existiert nicht."})
    if not os.path.exists(target_dir_abs):
        return jsonify({"status": "error", "error": f"Zielordner '{target}' existiert nicht."})
        
    if source_dir_abs == target_dir_abs:
        return jsonify({"status": "error", "error": "Quell- und Zielordner müssen unterschiedlich sein."})
        
    try:
        import shutil
        # Move all contents from source_dir to target_dir
        for item in os.listdir(source_dir_abs):
            if item.startswith('.'):
                continue
            s_item = os.path.join(source_dir_abs, item)
            t_item = os.path.join(target_dir_abs, item)
            
            # If item already exists, handle collision safely by appending _1, _2...
            if os.path.exists(t_item):
                base, ext = os.path.splitext(item)
                counter = 1
                new_item = f"{base}_{counter}{ext}"
                new_t_item = os.path.join(target_dir_abs, new_item)
                while os.path.exists(new_t_item):
                    counter += 1
                    new_item = f"{base}_{counter}{ext}"
                    new_t_item = os.path.join(target_dir_abs, new_item)
                t_item = new_t_item
                
            shutil.move(s_item, t_item)
            
        # Remove source directory if empty or has only dotfiles
        remaining = [f for f in os.listdir(source_dir_abs) if not f.startswith('.')]
        if len(remaining) == 0:
            trash.send_to_trash(source_dir_abs, force=True)
            
        log_message(f"🔄 Ordner zusammengeführt: '{source}' -> '{target}'")
        return jsonify({"status": "success"})
    except Exception as e:
        log_message(f"❌ Fehler beim Zusammenführen von '{source}' in '{target}': {e}")
        return jsonify({"status": "error", "error": str(e)})



@project_api.route('/split-project-file', methods=['POST'])
def handle_api_split_project_file():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    query = request.args
    project = params.get("project", "")
    file_name = params.get("file_name")
    if not file_name:
        return jsonify({"status": "error", "error": "Kein Dateiname angegeben."})
        
    settings = load_settings()
    inbox_root = settings.get("inbox_dir", "")
    if not inbox_root:
        return jsonify({"status": "error", "error": "Inbox-Verzeichnis ist nicht konfiguriert."})
    
    inbox_root_abs = os.path.abspath(inbox_root)
    
    if project:
        source_dir = os.path.join(inbox_root, project)
    else:
        source_dir = inbox_root
        
    source_dir_abs = os.path.abspath(source_dir)
    
    # Security check: Ensure source_dir is inside inbox_root
    if not source_dir_abs.startswith(inbox_root_abs):
        return jsonify({"status": "error", "error": "Ungültiger oder unzulässiger Quell-Pfad."})
        
    # Security check: Prevent path traversal in file_name
    safe_file_name = os.path.basename(file_name)
    if safe_file_name != file_name:
        return jsonify({"status": "error", "error": "Ungültiger Dateiname."})
        
    source_file_path = os.path.join(source_dir_abs, safe_file_name)
    if not os.path.exists(source_file_path):
        return jsonify({"status": "error", "error": f"Datei {safe_file_name} existiert nicht im Projekt."})
        
    # Determine base name without extension
    base_name, _ = os.path.splitext(safe_file_name)
    if not base_name:
        base_name = safe_file_name
        
    # Find unique folder name to avoid collision
    new_project_name = base_name
    counter = 1
    while os.path.exists(os.path.join(inbox_root_abs, new_project_name)):
        new_project_name = f"{base_name}_{counter}"
        counter += 1
        
    new_project_dir = os.path.join(inbox_root_abs, new_project_name)
    
    try:
        # Find all files with the same base name
        all_entries = os.listdir(source_dir_abs)
        files_to_move = []
        for entry in all_entries:
            entry_path = os.path.join(source_dir_abs, entry)
            if os.path.isfile(entry_path):
                # Move exact match, or if it starts with base_name + "." or base_name + "-"
                if entry == safe_file_name or entry.startswith(base_name + ".") or entry.startswith(base_name + "-"):
                    files_to_move.append(entry)
                    
        if not files_to_move:
            return jsonify({"status": "error", "error": "Keine Dateien zum Verschieben gefunden."})
            
        # Create new project directory
        os.makedirs(new_project_dir, exist_ok=True)
        
        # Move files
        import shutil
        for f in files_to_move:
            src = os.path.join(source_dir_abs, f)
            dst = os.path.join(new_project_dir, f)
            shutil.move(src, dst)
            log_message(f"Moved {src} to {dst}")
            
        log_message(f"✂️ Datei {safe_file_name} erfolgreich in das Projekt {new_project_name} abgespalten (insgesamt {len(files_to_move)} Dateien).")
        
        # Delete source directory if empty and not the inbox root
        if project:
            remaining = os.listdir(source_dir_abs)
            remaining = [r for r in remaining if not r.startswith(".")]
            if not remaining:
                try:
                    trash.send_to_trash(source_dir_abs, force=True)
                    log_message(f"🗑️ Quellordner in Quarantäne verschoben, da leer: {project}")
                except Exception as e:
                    log_message(f"⚠️ Fehler beim Löschen des leeren Quellordners {project}: {e}")
                    
        return jsonify({
            "status": "success",
            "new_project": new_project_name
        })
    except Exception as e:
        log_message(f"❌ Fehler bei handle_api_split_project_file: {e}")
        return jsonify({"status": "error", "error": str(e)})



import os
import re
import time
from flask import Blueprint, request, jsonify
from gui.core.utils import load_settings, load_show_profile, clean_show_name
import gui.core.media as media
import gui.core.trash as trash

_inbox_cache = {}
_inbox_cache_time = 0

def clean_scene_tags(name):
    if not name:
        return ""

    unambiguous_keywords = {
        '1080p', '720p', '2160p', '4k', 'x264', 'x265', 'hevc', 'h264', 'bluray',
        'web-dl', 'webdl', 'hdtv', 'bdrip', 'webrip', 'brrip', 'repack', 'proper',
        'blurayrip', 'uhd', 'truehd', 'hdr', '10bit', 'fhd'
    }

    contextual_keywords = {
        'german', 'deutsch', 'french', 'english', 'eng', 'dubbed', 'subbed',
        'multi', 'dl', 'dual', 'atmos', 'dts', 'ac3', 'aac', 'dd51', 'dd5',
        'custom', 'untouched', 'patched', 'retail', 'web', 'hdtvrip', 'hq'
    }

    all_keywords = unambiguous_keywords.union(contextual_keywords)

    def is_year(w):
        w_clean = w.lower().strip("()[]{}")
        return bool(re.match(r'^(19\d\d|20\d\d)$', w_clean))

    def is_keyword(w):
        w_clean = w.lower().strip("()[]{}")
        return w_clean in all_keywords or is_year(w)

    normalized = name.replace(".", " ").replace("_", " ").replace("-", " ")
    words = normalized.split()
    cut_index = len(words)

    for i, w in enumerate(words):
        w_clean = w.lower().strip("()[]{}")

        # 1. Jahr gefunden -> Schnitt direkt nach dem Jahr, wenn alle Folgewörter ab i+1 Keywords/Jahre sind
        if is_year(w):
            all_following_are_keywords = True
            for w_next in words[i+1:]:
                if not is_keyword(w_next):
                    all_following_are_keywords = False
                    break
            if all_following_are_keywords:
                cut_index = i + 1
                break

        # 2. Eindeutiges Keyword gefunden -> Schnitt direkt hier
        if w_clean in unambiguous_keywords:
            cut_index = i
            break

        # 3. Kontextuelles Keyword gefunden -> Schnitt nur, wenn ab hier alles Keywords/Jahre sind
        if w_clean in contextual_keywords:
            all_following_are_keywords = True
            for w_next in words[i:]:
                if not is_keyword(w_next):
                    all_following_are_keywords = False
                    break
            if all_following_are_keywords:
                cut_index = i
                break

    cleaned_words = words[:cut_index]
    cleaned_name = " ".join(cleaned_words).strip()
    if len(cleaned_name) < 2:
        return name.replace(".", " ").replace("_", " ").replace("-", " ").strip()
    return cleaned_name

def get_cleaner_suggested_query(folder_name, video_name_no_ext):
    """
    Entscheidet, ob der Videodateiname (ohne Extension) ein besserer Suchbegriff ist als der Ordnername.
    Liefert den bevorzugten Namen zurück.
    """
    if not video_name_no_ext:
        return clean_scene_tags(folder_name)

    # Heuristik 0: Generische Ordnernamen immer durch Videonamen ersetzen
    generic_names = {
        'neuer ordner', 'new folder', 'downloads', 'download',
        'film', 'movie', 'video', 'unbenannt', 'untitled'
    }
    # Bereinige Ordnernamen für die Prüfung (Zahlen, Klammern und Striche entfernen)
    folder_clean = re.sub(r'[\d\(\)\[\]\{\}\-\_]', '', folder_name).lower().strip()
    if folder_clean in generic_names or not folder_clean:
        return clean_scene_tags(video_name_no_ext)

    scene_keywords = {
        '1080p', '720p', '2160p', '4k', 'x264', 'x265', 'hevc', 'h264', 'bluray',
        'web-dl', 'webdl', 'dts', 'dd5.1', 'hdtv', 'aac', 'ac3', 'bdrip', 'webrip',
        'brrip', 'multi', 'dl', 'dual', 'atmos'
    }

    # Bereinigen und in Lowercase umwandeln
    fn_lower = folder_name.lower()
    vn_lower = video_name_no_ext.lower()

    # Zähle Scene-Keywords
    fn_kw_count = sum(1 for kw in scene_keywords if kw in fn_lower)
    vn_kw_count = sum(1 for kw in scene_keywords if kw in vn_lower)

    # Prüfen, ob eine Jahreszahl (19xx oder 20xx) vorhanden ist
    year_pattern = re.compile(r'\b(19|20)\d{2}\b')
    fn_has_year = bool(year_pattern.search(folder_name))
    vn_has_year = bool(year_pattern.search(video_name_no_ext))

    # Heuristik 1: Wenn der Ordnername Scene-Keywords enthält, der Videodateiname aber keine (oder weniger)
    if fn_kw_count > vn_kw_count:
        return clean_scene_tags(video_name_no_ext)

    # Heuristik 2: Wenn der Videodateiname ein Jahr enthält, der Ordnername aber nicht
    if vn_has_year and not fn_has_year:
        return clean_scene_tags(video_name_no_ext)

    # Heuristik 3: Wenn der Videodateiname ein Jahr in Klammern wie " (2000)" enthält (sehr typisch für saubere Namen)
    if re.search(r'\(\d{4}\)', video_name_no_ext):
        return clean_scene_tags(video_name_no_ext)

    # Heuristik 4: Wenn der Ordnername extrem lang und unleserlich ist
    if len(folder_name) > 40 and len(video_name_no_ext) < len(folder_name) - 10:
        return clean_scene_tags(video_name_no_ext)

    # Fallback
    return clean_scene_tags(folder_name)

def get_inbox_suggestions():
    global _inbox_cache, _inbox_cache_time
    now = time.time()

    # 30s Cache
    if now - _inbox_cache_time < 30:
        return _inbox_cache

    settings = load_settings()
    inbox_dir = settings.get("inbox_dir")
    
    if not inbox_dir or not os.path.exists(inbox_dir):
        return []
        
    suggestions = []

    for item in os.listdir(inbox_dir):
        if item.startswith('.'):
            continue

        full_path = os.path.join(inbox_dir, item)
        is_dir = os.path.isdir(full_path)
        video_exts = {'.mp4', '.mkv', '.avi', '.mov', '.ts', '.webm'}

        if not is_dir:
            ext = os.path.splitext(item)[1].lower()
            if ext not in video_exts:
                continue

        # Count and collect all videos
        video_files = []
        nfo_files = []

        if is_dir:
            for root, dirs, files in os.walk(full_path):
                for f in files:
                    if not f.startswith('.'):
                        f_ext = os.path.splitext(f)[1].lower()
                        if f_ext in video_exts:
                            video_files.append(os.path.join(root, f))
                        elif f_ext == '.nfo':
                            nfo_files.append(os.path.join(root, f))
        else:
            video_files.append(full_path)

        video_count = len(video_files)
        if video_count == 0:
            continue
            
        # Check codecs for up to 10 video files to avoid disk overhead
        has_inefficient = False
        files_to_check = video_files[:10]
        from concurrent.futures import ThreadPoolExecutor
        try:
            with ThreadPoolExecutor(max_workers=min(len(files_to_check), 5)) as executor:
                codecs = list(executor.map(media.get_video_codec, files_to_check))
            for codec in codecs:
                if codec and not is_efficient_video_codec(codec):
                    has_inefficient = True
                    break
        except Exception as e:
            print(f"Error checking codecs in suggestions: {e}")
            
        # Check NFO files for Doku keywords
        is_doku = False
        if "doku" in item.lower() or "dokumentation" in item.lower() or "documentary" in item.lower():
            is_doku = True
            
        if not is_doku:
            for nfo_p in nfo_files:
                if os.path.exists(nfo_p):
                    try:
                        with open(nfo_p, 'r', encoding='utf-8', errors='ignore') as nfo_f:
                            content = nfo_f.read().lower()
                            if "doku" in content or "dokumentation" in content or "documentary" in content:
                                is_doku = True
                                break
                    except Exception as e:
                        log_message(f"⚠️ NFO-Datei für Doku-Erkennung nicht lesbar: {e}")
                        
        # Determine suggested search query & check obfuscation
        folder_base = item if is_dir else os.path.splitext(item)[0]
        suggested_query = folder_base
        is_obfuscated = False
        
        separators = {'.', '_', '-', ' '}
        has_separator = any(c in folder_base for c in separators)
        if not has_separator and len(folder_base) >= 10:
            is_obfuscated = True
            
        if video_files:
            video_base = os.path.basename(video_files[0])
            video_base_no_ext = os.path.splitext(video_base)[0]
            suggested_query = get_cleaner_suggested_query(folder_base, video_base_no_ext)
                    
        media_type = "movie"
        confidence = "low"
        profile_match = False
        profile = None
        
        # Determine media type via regex
        tv_pattern = re.compile(r'(?i)(s\d{1,2}e\d{1,2}|season\s*\d+|staffel\s*\d+)')
        doku_pattern = re.compile(r'(?i)(doku|documentary|dokumentation)')
        year_pattern = re.compile(r'(19|20)\d{2}')
        
        if tv_pattern.search(item):
            media_type = "tv"
            confidence = "medium"
            match = tv_pattern.search(item)
            suggested_query = item[:match.start()].strip(' ._-')
        elif doku_pattern.search(item) or is_doku:
            media_type = "doku"
            confidence = "medium"
            if doku_pattern.search(item):
                match = doku_pattern.search(item)
                suggested_query = item[:match.start()].strip(' ._-')
        elif year_pattern.search(item):
            media_type = "movie"
            confidence = "medium"
            match = year_pattern.search(item)
            suggested_query = item[:match.start()].strip(' ._-')
        elif video_count > 1:
            media_type = "tv"
            confidence = "low"
            
        # Clean up query
        clean_query = clean_show_name(suggested_query)
        if clean_query:
            suggested_query = clean_query
            
        # Profile match (try exact first)
        prof = load_show_profile(suggested_query)
        
        # Fallback to simple fuzzy match if no exact match found
        if not prof or not prof.get("show_id"):
            from gui.core.utils import get_profiles_dir
            import json
            pdir = get_profiles_dir()
            sq_lower = suggested_query.lower().replace("_", " ")
            try:
                for pf in os.listdir(pdir):
                    if not pf.endswith(".json"): continue
                    pf_name = pf[:-5].lower()
                    if len(sq_lower) >= 4 and (sq_lower in pf_name or pf_name in sq_lower):
                        with open(os.path.join(pdir, pf), "r") as f:
                            prof = json.load(f)
                            break
            except Exception as e:
                log_message(f"⚠️ Profil-Verzeichnis konnte nicht durchsucht werden: {e}")
                
        if prof and prof.get("show_id"):
            profile_match = True
            confidence = "high"
            profile = prof
            schema = str(prof.get("schema", "")).lower()
            nas_dest = str(prof.get("nas_destination_id") or prof.get("destination_id") or "")
            if "doku" in schema or nas_dest in ("3", "4"):
                media_type = "doku"
            elif schema == "anime":
                media_type = "anime"
            else:
                media_type = "tv"
                
        # Build human-readable reasons for the suggestion (shown as badges in UI)
        reasons = []
        if profile_match:
            reasons.append("Profil gefunden")
        type_labels = {
            "tv": "Serie erkannt",
            "movie": "Film erkannt",
            "doku": "Doku erkannt",
            "anime": "Anime erkannt",
        }
        if media_type in type_labels:
            reasons.append(type_labels[media_type])
        if has_inefficient:
            reasons.append("Codec ineffizient (H.265 empfohlen)")

        suggestions.append({
            "project": item,
            "media_type": media_type,
            "confidence": confidence,
            "profile_match": profile_match,
            "profile": profile,
            "suggested_query": suggested_query,
            "video_count": video_count,
            "has_inefficient_codec": has_inefficient,
            "reasons": reasons
        })
            
    _inbox_cache = suggestions
    _inbox_cache_time = now
    
    return suggestions


@project_api.route('/inbox/analyze', methods=['GET'])
def api_inbox_analyze():
    try:
        return jsonify({'suggestions': get_inbox_suggestions()})
    except Exception as e:
        import traceback
        print('Error in analyze_inbox:', traceback.format_exc())
        return jsonify({'suggestions': []})
