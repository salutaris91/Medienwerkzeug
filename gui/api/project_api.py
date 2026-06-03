import os, sys, json, time, shutil, subprocess, urllib, threading, math
from flask import Blueprint, request, jsonify, Response, send_file, send_from_directory
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
from gui.workers.processor import JOB_QUEUE, SYSTEM_STATUS, STATUS_LOCK



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
        tell application "System Events"
            activate
            try
                if defaultPath is not "" then
                    set f to choose folder with prompt "Wähle einen Zielordner für die Werkzeuge:" default location (POSIX file defaultPath)
                else
                    set f to choose folder with prompt "Wähle einen Zielordner für die Werkzeuge:"
                end if
                POSIX path of f
            on error
                return ""
            end try
        end tell
    end run
    '''
    try:
        result = subprocess.run(["osascript", "-", default_path], input=script, capture_output=True, text=True)
        folder_path = result.stdout.strip()
        return jsonify({"status": "ok", "path": folder_path})
    except Exception as e:
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
    if project and not is_recursive_inbox:
        target_dir = os.path.abspath(os.path.join(inbox_root, project))
    else:
        target_dir = os.path.abspath(inbox_root)
        
    if not is_path_allowed(target_dir):
        return jsonify({"error": "Access Denied"}), 403
        return
        
    if not os.path.exists(target_dir):
        return jsonify({"error": "Directory not found"}), 404
        return
    file_list = []
    ext_counts = {}
    
    # Scannen des Verzeichnisses (nur Hauptebene für die Inbox, rekursiv für Projektordner)
    if not project:
        all_files = [f for f in os.listdir(target_dir) if os.path.isfile(os.path.join(target_dir, f)) and not f.startswith('.')]
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
    video_files = [os.path.join(target_dir, f) for f in all_files if os.path.splitext(f)[1].lower() in video_extensions]
    
    has_inefficient_video = False
    if video_files:
        # Check up to 10 video files to avoid huge scans
        files_to_check = video_files[:10]
        from concurrent.futures import ThreadPoolExecutor
        
        try:
            with ThreadPoolExecutor(max_workers=min(len(files_to_check), 5)) as executor:
                codecs = list(executor.map(media.get_video_codec, files_to_check))
            
            for codec in codecs:
                if codec and codec not in ('hevc', 'h265', 'vp9', 'av1'):
                    has_inefficient_video = True
                    break
        except Exception as e:
            log_message(f"Fehler bei der Codec-Erkennung: {e}")
    
    # Determine suggested search query
    suggested_query = project
    is_obfuscated = False
    if project:
        # Check if there are any separators
        separators = {'.', '_', '-', ' '}
        has_separator = any(c in project for c in separators)
        if not has_separator and len(project) >= 10:
            is_obfuscated = True
            
    if video_files:
        # Get the first video file's base name
        first_video = video_files[0]
        video_base = os.path.basename(first_video)
        video_base_no_ext = os.path.splitext(video_base)[0]
        
        if is_obfuscated:
            suggested_query = video_base_no_ext
        else:
            # Compare number of word separators
            project_seps = sum(1 for c in project if c in {'.', '_', '-'})
            video_seps = sum(1 for c in video_base_no_ext if c in {'.', '_', '-'})
            if video_seps > project_seps + 2:
                suggested_query = video_base_no_ext

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
    
    return jsonify({
        "current_dir": target_dir,
        "files": file_list,
        "video_count": video_count,
        "ext_counts": ext_counts,
        "is_doku": is_doku,
        "has_inefficient_video": has_inefficient_video,
        "suggested_query": suggested_query
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
        return
        
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
                        trash.send_to_trash(path_f)
                        deleted_files.append(f"inbox/{f}")
                    except trash.TrashError as e:
                        print(f"TrashError removing {path_f}: {e}")
                    except Exception as e:
                        print(f"Error removing {path_f}: {e}")
                        
        # Lösche Dateien aus Output
        if outbox_dir and os.path.exists(outbox_dir):
            for f in output_files:
                path_f = os.path.join(outbox_dir, f)
                path_f = os.path.abspath(path_f)
                if not is_path_allowed(path_f) or not path_f.startswith(os.path.abspath(outbox_dir) + os.sep):
                    continue
                if os.path.exists(path_f):
                    try:
                        trash.send_to_trash(path_f)
                        deleted_files.append(f"output/{f}")
                    except trash.TrashError as e:
                        print(f"TrashError removing {path_f}: {e}")
                    except Exception as e:
                        print(f"Error removing {path_f}: {e}")
                        
        # Leere Ordner aufräumen
        def cleanup_empty_dirs(base_dir):
            cleaned = []
            for root, dirs, files in os.walk(base_dir, topdown=False):
                for d in dirs:
                    dir_path = os.path.join(root, d)
                    try:
                        if not os.listdir(dir_path):
                            trash.send_to_trash(dir_path)
                            cleaned.append(os.path.relpath(dir_path, base_dir))
                    except Exception:
                        pass
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
        return
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
                    trash.send_to_trash(path_f)
                    deleted_files.append(f)
                except Exception:
                    pass
                    
        # Leere Ordner aufräumen
        for root, dirs, files in os.walk(target_dir, topdown=False):
            if root == target_dir: continue
            if not os.listdir(root):
                try:
                    trash.send_to_trash(root)
                    deleted_dirs.append(os.path.relpath(root, target_dir))
                except Exception:
                    pass
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
                        trash.send_to_trash(path_f)
                        deleted_files.append(os.path.relpath(path_f, target_dir))
                    except Exception:
                        pass
            for d in dirs:
                path_d = os.path.join(root, d)
                if not os.listdir(path_d):
                    try:
                        trash.send_to_trash(path_d)
                        deleted_dirs.append(os.path.relpath(path_d, target_dir))
                    except Exception:
                        pass
                        
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
        return
        
    if not os.path.exists(target_dir_abs):
        return jsonify({"status": "error", "error": "Ordner existiert nicht."})
        return
        
    try:
        trash.send_to_trash(target_dir_abs)
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
            trash.send_to_trash(source_dir_abs)
            
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
        return
        
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
        return
        
    # Security check: Prevent path traversal in file_name
    safe_file_name = os.path.basename(file_name)
    if safe_file_name != file_name:
        return jsonify({"status": "error", "error": "Ungültiger Dateiname."})
        return
        
    source_file_path = os.path.join(source_dir_abs, safe_file_name)
    if not os.path.exists(source_file_path):
        return jsonify({"status": "error", "error": f"Datei {safe_file_name} existiert nicht im Projekt."})
        return
        
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
            return
            
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
                    trash.send_to_trash(source_dir_abs)
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
        if not os.path.isdir(full_path):
            continue
            
        # Count and collect all videos
        video_files = []
        nfo_files = []
        video_exts = {'.mp4', '.mkv', '.avi', '.mov', '.ts', '.webm'}
        
        for root, dirs, files in os.walk(full_path):
            for f in files:
                if not f.startswith('.'):
                    ext = os.path.splitext(f)[1].lower()
                    if ext in video_exts:
                        video_files.append(os.path.join(root, f))
                    elif ext == '.nfo':
                        nfo_files.append(os.path.join(root, f))
                        
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
                if codec and codec not in ('hevc', 'h265', 'vp9', 'av1'):
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
                    except Exception:
                        pass
                        
        # Determine suggested search query & check obfuscation
        suggested_query = item
        is_obfuscated = False
        
        separators = {'.', '_', '-', ' '}
        has_separator = any(c in item for c in separators)
        if not has_separator and len(item) >= 10:
            is_obfuscated = True
            
        if video_files:
            video_base = os.path.basename(video_files[0])
            video_base_no_ext = os.path.splitext(video_base)[0]
            
            if is_obfuscated:
                suggested_query = video_base_no_ext
            else:
                project_seps = sum(1 for c in item if c in {'.', '_', '-'})
                video_seps = sum(1 for c in video_base_no_ext if c in {'.', '_', '-'})
                if video_seps > project_seps + 2:
                    suggested_query = video_base_no_ext
                    
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
            except Exception:
                pass
                
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

