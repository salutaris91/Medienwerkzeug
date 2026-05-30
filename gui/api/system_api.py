from gui.core.helpers import get_folder_size_bytes
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

system_api = Blueprint('system_api', __name__)

# Global variables imported from processor
from gui.workers.processor import JOB_QUEUE, SYSTEM_STATUS, STATUS_LOCK



@system_api.route('/settings', methods=['GET', 'POST'])
def handle_api_settings():
    settings = load_settings()
    if request.method == 'POST':
        try:
            params = request.get_json() or {}
        except Exception:
            params = {}
        for k, v in params.items():
            settings[k] = v
        if save_settings(settings):
            return jsonify({"status": "success"})
        else:
            return jsonify({"error": "Failed to save settings"})
    else:
        for key in ["telegram_token", "telegram_chat_id", "whatsapp_apikey", "whatsapp_phone"]:
            settings.pop(key, None)
        return jsonify(settings)



@system_api.route('/check-dependencies', methods=['GET', 'POST'])
def handle_api_check_dependencies():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    query = request.args
    force = query.get("force", ["false"])[0].lower() == "true"
    results = check_dependency_status(force_updates=force)
    return jsonify(results)



@system_api.route('/post-settings-legacy', methods=['GET', 'POST'])
def handle_api_post_settings_legacy():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    query = request.args
    settings = load_settings()
    for k, v in params.items():
        settings[k] = v
    if save_settings(settings):
        return jsonify({"status": "success"})
    else:
        return jsonify({"error": "Failed to save settings"})



@system_api.route('/profile', methods=['GET', 'POST'])
@system_api.route('/get-profile', methods=['GET', 'POST'])
@system_api.route('/post-profile', methods=['GET', 'POST'])
def handle_api_profile():
    if request.method == 'GET' or (request.method == 'POST' and not request.is_json):
        show_name = request.args.get("show_name", "").strip()
        if not show_name:
            try:
                params = request.get_json() or {}
            except Exception:
                params = {}
            show_name = params.get("show_name", "").strip()
        if not show_name:
            return jsonify({"error": "show_name parameter is missing"}), 400
        profile = load_show_profile(show_name)
        return jsonify(profile)
    else: # POST with JSON
        try:
            params = request.get_json() or {}
        except Exception:
            params = {}
        show_name = params.get("show_name")
        profile_data = params.get("profile")
        if not show_name or not profile_data:
            return jsonify({"error": "show_name or profile parameter is missing"}), 400
        success = save_show_profile(show_name, profile_data)
        return jsonify({"success": success})



@system_api.route('/system-restart', methods=['GET', 'POST'])
@system_api.route('/system/restart', methods=['GET', 'POST'])
def handle_api_system_restart():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    query = request.args
    # Check active background tasks
    active_count = 0
    with active_jobs_lock:
        for job in active_jobs.values():
            if job.get("status") not in ("done", "error"):
                active_count += 1
                
    if active_count > 0:
        return jsonify({
            "status": "busy",
            "message": "Der Server kann nicht neu gestartet werden, da aktuell noch Konvertierungen oder Dateiübertragungen laufen!"
        })
        return
        
    # Schedule restart in a separate thread to allow response to send
    def do_restart():
        time.sleep(1.0)
        print("Restarting server process via subprocess...")
        import subprocess
        # Get absolute path to main.py
        main_py = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "main.py"))
        env = os.environ.copy()
        # Set PYTHONPATH to the parent directory of gui/
        project_root = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".."))
        env["PYTHONPATH"] = project_root
        
        args = [sys.executable, main_py]
        if "--restarted" not in args:
            args.append("--restarted")
            
        try:
            subprocess.Popen(args, env=env, close_fds=True, start_new_session=True)
        except Exception as e:
            print(f"Error spawning restart process: {e}")
        os._exit(0)
        
    threading.Thread(target=do_restart, daemon=True).start()
    return jsonify({"status": "restarting"})



@system_api.route('/status', methods=['GET', 'POST'])
def handle_api_status():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    query = request.args
    settings = load_settings()
    inbox = settings.get("inbox_dir")
    if not inbox:
        inbox = os.path.expanduser("~/Downloads/Medien Input")
    outbox = settings.get("outbox_dir")
    if not outbox:
        outbox = os.path.expanduser("~/Downloads/Medien Output")
        
    os.makedirs(inbox, exist_ok=True)
    os.makedirs(outbox, exist_ok=True)
    
    projects = []
    for d in os.listdir(inbox):
        if os.path.isdir(os.path.join(inbox, d)) and not d.startswith("."):
            projects.append(d)
            
    import time
    # Cache NAS status for 30 seconds to avoid P5 pinging constantly
    if not hasattr(handle_api_status, "last_nas_status") or time.time() - getattr(handle_api_status, "last_nas_check", 0) > 30:
        handle_api_status.last_nas_status = check_nas_status()
        handle_api_status.last_nas_check = time.time()

    # Cache folder sizes for 60 seconds
    now = time.time()
    if not hasattr(handle_api_status, "cached_inbox_size") or now - getattr(handle_api_status, "last_size_check", 0) > 60:
        inbox_bytes = get_folder_size_bytes(inbox)
        outbox_bytes = get_folder_size_bytes(outbox)
        handle_api_status.cached_inbox_size = round(inbox_bytes / (1024**3), 2)
        handle_api_status.cached_outbox_size = round(outbox_bytes / (1024**3), 2)
        handle_api_status.last_size_check = now

    status = {
        "nas_status": handle_api_status.last_nas_status,
        "inbox_path": inbox,
        "outbox_path": outbox,
        "streamfab_downloads": check_streamfab(),
        "projects": sorted(projects),
        "inbox_size_gb": handle_api_status.cached_inbox_size,
        "outbox_size_gb": handle_api_status.cached_outbox_size
    }
    
    return jsonify(status)



@system_api.route('/system-open-folder', methods=['GET', 'POST'])
def handle_api_system_open_folder():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    query = request.args
    path_list = query.get("path")
    category_id_list = query.get("category_id")
    
    folder_path = None
    
    if path_list:
        folder_path = path_list[0]
    elif category_id_list:
        category_id = category_id_list[0]
        folder_name = query.get("folder_name", [""])[0]
        
        settings = load_settings()
        nas_root = settings.get("nas_root", "/Volumes/Kino")
        sync_categories = settings.get("sync_categories", [])
        
        category = None
        for cat in sync_categories:
            if str(cat.get("id")) == str(category_id):
                category = cat
                break
                
        if not category:
            return jsonify({"error": f"Kategorie mit ID {category_id} nicht gefunden."})
            return
            
        nas_sub = category.get("nas_sub", "").lstrip("/")
        cat_path = os.path.join(nas_root, nas_sub)
        
        if folder_name:
            specific_path = os.path.join(cat_path, folder_name)
            if os.path.exists(specific_path):
                folder_path = specific_path
            else:
                folder_path = cat_path
        else:
            folder_path = cat_path
            
    if not folder_path:
        return jsonify({"error": "Pfad oder Kategorie-Parameter fehlt."})
        return
        
    folder_path = os.path.abspath(folder_path)
    if not is_path_allowed(folder_path):
        return jsonify({"error": "Access Denied"})
        return
        
    if not os.path.exists(folder_path):
        return jsonify({"error": f"Pfad existiert nicht: {folder_path}. Ist das NAS gemountet?"})
        return
        
    # Security: verify path is a directory, not an executable
    if not os.path.isdir(folder_path):
        return jsonify({"error": f"Pfad ist kein Ordner: {folder_path}"})
        return
        
    try:
        subprocess.run(["open", folder_path], check=True)
        return jsonify({"success": True, "msg": f"Ordner {folder_path} im Finder geöffnet."})
    except Exception as e:
        return jsonify({"error": f"Fehler beim Öffnen des Ordners: {str(e)}"})



@system_api.route('/stats', methods=['GET', 'POST'])
def handle_api_stats():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    query = request.args
    try:
        settings = load_settings()
        nas_root = settings.get("nas_root", "/Volumes/Kino")
        
        # NAS Storage Info
        nas_info = {
            "path": nas_root,
            "total": 0,
            "used": 0,
            "free": 0,
            "used_percent": 0.0,
            "available": False
        }
        if os.path.exists(nas_root):
            try:
                usage = shutil.disk_usage(nas_root)
                nas_info["total"] = usage.total
                nas_info["free"] = usage.free
                nas_info["available"] = True
                # Netzlaufwerke (SMB) liefern via statvfs teils inkonsistente Werte
                # (z. B. frei > gesamt -> negative Belegung). In dem Fall ist die
                # Prozent-Belegung nicht verwertbar; wir zeigen nur den freien Platz.
                if usage.free > usage.total or usage.used < 0:
                    nas_info["usage_unreliable"] = True
                    nas_info["used"] = None
                    nas_info["used_percent"] = None
                else:
                    nas_info["used"] = usage.used
                    nas_info["used_percent"] = round((usage.used / usage.total) * 100, 2) if usage.total > 0 else 0.0
            except Exception as e:
                nas_info["error"] = str(e)
        else:
            nas_info["error"] = "NAS Pfad existiert nicht oder ist nicht eingehängt."

        # Conversion savings calculations
        history = load_konv_history()
        
        total_files = len(history)
        size_in_total = 0
        size_out_total = 0
        ratios = []
        cleaned_history = []

        # Nur Einträge mit ECHTEN Größendaten fließen in die Ersparnis-/Ratio-Statistik
        # ein. Alt-Einträge ohne Größe würden sonst geschätzt werden müssen, was die
        # Zahlen verfälscht (frühere Schätzung erzeugte negative Ersparnis).
        for entry in history:
            size_in = entry.get("size_in")
            size_out = entry.get("size_out")
            ratio = entry.get("ratio")

            has_real_sizes = (
                isinstance(size_in, (int, float)) and isinstance(size_out, (int, float))
                and size_in > 1000
            )
            if not has_real_sizes:
                continue

            size_in_total += size_in
            size_out_total += size_out
            if isinstance(ratio, (int, float)) and ratio > 0:
                ratios.append(ratio)

            cleaned_history.append({
                "quality": entry.get("quality", "Unbekannt"),
                "codec": entry.get("codec", "hevc"),
                "ratio": ratio if isinstance(ratio, (int, float)) else (size_out / size_in),
                "size_in": size_in,
                "size_out": size_out,
                "timestamp": entry.get("timestamp", 0)
            })

        saved_bytes = max(0, size_in_total - size_out_total)
        # Durchschnittliche Rate über die tatsächlichen Gesamtgrößen (robust & konsistent
        # zur angezeigten Ersparnis).
        avg_ratio = (size_out_total / size_in_total) if size_in_total > 0 else 0.0
        
        # Sort history by timestamp descending
        cleaned_history.sort(key=lambda x: x["timestamp"], reverse=True)
        
        response = {
            "nas": nas_info,
            "stats": {
                "total_files": total_files,
                "size_in_total": size_in_total,
                "size_out_total": size_out_total,
                "saved_bytes": saved_bytes,
                "average_ratio": round(avg_ratio, 4),
                "ratio_percent": round((1 - avg_ratio) * 100, 2) if avg_ratio <= 1 else 0.0
            },
            "history": cleaned_history[:50]
        }
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": f"Error generating stats: {e}"}), 500



@system_api.route('/logs', methods=['GET', 'POST'])
def handle_api_logs():
    def generate():
        yield "data: Konsole verbunden. Log-Streaming aktiv...\n\n"
        while True:
            try:
                line = log_queue.get(timeout=2.0)
                yield f"data: {line.strip()}\n\n"
            except queue.Empty:
                yield ": keep-alive\n\n"
                
    return Response(generate(), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive'
    })


@system_api.route('/conversion/recommendations', methods=['GET'])
def api_conversion_recommendations():
    import gui.core.media as media
    return jsonify(media.get_conversion_recommendations())

@system_api.route('/profiles', methods=['GET', 'POST'])
def api_profiles():
    import os
    import json
    from flask import request, jsonify
    from gui.core.utils import load_settings
    
    settings = load_settings()
    default_profiles_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'profiles')
    profiles_dir = settings.get("profiles_path", default_profiles_dir)
    
    # If the configured path doesn't exist, we fallback to default to avoid errors
    if not os.path.exists(profiles_dir):
        try:
            os.makedirs(profiles_dir, exist_ok=True)
        except:
            profiles_dir = default_profiles_dir
            os.makedirs(profiles_dir, exist_ok=True)

    
    if request.method == 'GET':
        profiles = []
        for f in os.listdir(profiles_dir):
            if f.endswith('.json'):
                try:
                    with open(os.path.join(profiles_dir, f), 'r') as file:
                        data = json.load(file)
                        profiles.append({"filename": f, "data": data})
                except Exception as e:
                    pass
        return jsonify({"profiles": profiles})
        
    elif request.method == 'POST':
        action = request.json.get("action")
        filename = request.json.get("filename")
        if not filename or not filename.endswith('.json'):
            return jsonify({"status": "error", "message": "Ungültiger Dateiname."}), 400
            
        filepath = os.path.join(profiles_dir, filename)
        
        if action == "delete":
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({"status": "success"})
            
        elif action == "save":
            data = request.json.get("data")
            if not data:
                return jsonify({"status": "error", "message": "Keine Daten übergeben."}), 400
            with open(filepath, 'w') as file:
                json.dump(data, file, indent=2)
            return jsonify({"status": "success"})
            
        return jsonify({"status": "error", "message": "Unbekannte Aktion."}), 400
