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
NAS_CONNECT_COOLDOWN_SECONDS = 5

# Global variables imported from processor
from gui.workers.processor import JOB_QUEUE, SYSTEM_STATUS, STATUS_LOCK



@system_api.route('/settings', methods=['GET', 'POST'])
def handle_api_settings():
    from gui.core.persistence import update_settings, save_env_keys, load_env_keys, mask_credential, is_masked
    import gui.mw_metadata as mw_metadata

    if request.method == 'POST':
        try:
            params = request.get_json() or {}
        except Exception:
            params = {}

        # Extract env variables from params
        env_updates = {}
        if "tmdb_api_key" in params:
            val = params.pop("tmdb_api_key")
            if not is_masked(val):
                env_updates["TMDB_API_KEY"] = val
        if "tvdb_api_key" in params:
            val = params.pop("tvdb_api_key")
            if not is_masked(val):
                env_updates["TVDB_API_KEY"] = val

        # Save env variables if changed
        if "TMDB_API_KEY" in env_updates or "TVDB_API_KEY" in env_updates:
            # Only pass keys that were unmasked to save_env_keys
            save_env_keys(env_updates)
            mw_metadata.reload_metadata_keys()

        # Protect masked regular settings
        def mutate(data):
            for k, v in params.items():
                if k in ["telegram_token", "telegram_chat_id", "whatsapp_apikey", "whatsapp_phone"] and is_masked(v):
                    continue # Preserve existing value
                data[k] = v

        if update_settings(mutate):
            return jsonify({"status": "success"})
        else:
            return jsonify({"error": "Failed to save settings"})
    else:
        settings = load_settings()

        # Mask credentials instead of popping them blindly
        settings["telegram_token"] = mask_credential(settings.get("telegram_token", ""))
        settings["telegram_chat_id"] = mask_credential(settings.get("telegram_chat_id", ""))
        settings["whatsapp_apikey"] = mask_credential(settings.get("whatsapp_apikey", ""))
        settings["whatsapp_phone"] = mask_credential(settings.get("whatsapp_phone", ""))

        # Also append masked env keys
        env_keys = load_env_keys()
        settings["tmdb_api_key"] = mask_credential(env_keys.get("TMDB_API_KEY", ""))
        settings["tvdb_api_key"] = mask_credential(env_keys.get("TVDB_API_KEY", ""))

        return jsonify(settings)



@system_api.route('/check-dependencies', methods=['GET', 'POST'])
def handle_api_check_dependencies():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    query = request.args
    force = query.get("force", "false").lower() == "true"
    results = check_dependency_status(force_updates=force)
    return jsonify(results)





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
    active_count = 0
    from gui.core.jobs import get_all_jobs
    for job in get_all_jobs():
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


@system_api.route('/nas/connect', methods=['POST'])
def handle_api_nas_connect():
    """Try to mount the configured NAS immediately and refresh the cached status."""
    now = time.time()
    last_attempt = getattr(handle_api_nas_connect, "last_attempt", 0)
    if now - last_attempt < NAS_CONNECT_COOLDOWN_SECONDS:
        return jsonify({
            "ok": False,
            "nas_status": getattr(handle_api_status, "last_nas_status", "offline"),
            "message": "Bitte warte kurz, bevor du erneut eine NAS-Verbindung startest."
        }), 429
    handle_api_nas_connect.last_attempt = now

    try:
        ensure_nas_mounted()
        nas_status = check_nas_status()
        handle_api_status.last_nas_status = nas_status
        handle_api_status.last_nas_check = now

        if nas_status == "connected":
            return jsonify({
                "ok": True,
                "nas_status": nas_status,
                "message": "NAS wurde erfolgreich verbunden."
            })

        if nas_status == "available_not_mounted":
            message = (
                "NAS ist erreichbar, konnte aber nicht eingebunden werden. "
                "Bitte prüfe die SMB-Zugangsdaten im macOS-Schlüsselbund."
            )
        else:
            message = (
                "NAS konnte nicht erreicht werden. Bitte prüfe Netzwerk, "
                "Tailscale und die SMB-Einstellungen."
            )

        return jsonify({"ok": False, "nas_status": nas_status, "message": message}), 503
    except Exception as e:
        log_message(f"❌ Manueller NAS-Verbindungsversuch fehlgeschlagen: {e}")
        handle_api_status.last_nas_status = "offline"
        handle_api_status.last_nas_check = now
        return jsonify({
            "ok": False,
            "nas_status": "offline",
            "message": f"NAS-Verbindung fehlgeschlagen: {e}"
        }), 500



@system_api.route('/system-open-folder', methods=['GET', 'POST'])
def handle_api_system_open_folder():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    query = request.args
    # Flask liefert request.args.get() als String (nicht als Liste wie das frühere
    # parse_qs). Daher direkt verwenden – früher wurde fälschlich [0] genommen, was
    # nur das erste Zeichen des Pfades lieferte ("/").
    path = query.get("path") or params.get("path")
    category_id = query.get("category_id") or params.get("category_id")

    folder_path = None

    if path:
        folder_path = path
    elif category_id:
        folder_name = query.get("folder_name") or params.get("folder_name") or ""

        settings = load_settings()
        nas_root = settings.get("nas_root", "")
        if not nas_root:
            return jsonify({"error": "NAS-Root ist nicht konfiguriert."}), 400
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
        open_folder_in_finder(folder_path)
        return jsonify({"success": True, "msg": f"Ordner {folder_path} im Finder geöffnet."})
    except Exception as e:
        return jsonify({"error": f"Fehler beim Öffnen des Ordners: {str(e)}"})



# Cache für rclone-about-Abfragen (Cloud-Speicher), um wiederholte Netzaufrufe zu vermeiden
_rclone_about_cache = {}      # remote -> (timestamp, data|None)
_RCLONE_ABOUT_TTL = 300       # 5 Minuten


def _rclone_about(remote):
    """Liefert {total,used,free} eines rclone-Remotes via 'rclone about --json' (gecacht)."""
    now = time.time()
    cached = _rclone_about_cache.get(remote)
    if cached and now - cached[0] < _RCLONE_ABOUT_TTL:
        return cached[1]
    data = None
    try:
        out = subprocess.check_output(["rclone", "about", remote, "--json"], text=True, timeout=20)
        parsed = json.loads(out)
        if parsed.get("total"):
            data = {"total": parsed.get("total"), "used": parsed.get("used"), "free": parsed.get("free")}
    except Exception:
        data = None
    _rclone_about_cache[remote] = (now, data)
    return data


def _read_target_storage(target):
    """Speicher-Infos eines Speicherziels.

    Ist ein rclone_remote gesetzt -> Cloud-Ziel: zuverlässige Werte via 'rclone about'.
    Sonst lokales/NAS-Ziel: shutil.disk_usage mit Netzlaufwerk-Guard (frei > gesamt
    -> Belegung nicht verwertbar, nur freien Platz anzeigen).
    """
    info = {
        "name": target.get("name", ""),
        "type": target.get("type", ""),
        "available": False,
        "total": None, "used": None, "free": None, "used_percent": None,
        "path": target.get("root_path", ""),
    }
    remote = (target.get("rclone_remote") or "").strip()
    if remote:
        about = _rclone_about(remote)
        if about and about.get("total"):
            info["available"] = True
            info["path"] = remote
            info["total"] = about["total"]
            info["used"] = about.get("used")
            info["free"] = about.get("free")
            if about["total"] > 0 and about.get("used") is not None:
                info["used_percent"] = round((about["used"] / about["total"]) * 100, 2)
        return info

    root_path = target.get("root_path")
    if root_path and os.path.exists(root_path):
        try:
            usage = shutil.disk_usage(root_path)
            info["available"] = True
            info["total"] = usage.total
            info["free"] = usage.free
            if usage.free > usage.total or usage.used < 0:
                info["usage_unreliable"] = True
            else:
                info["used"] = usage.used
                info["used_percent"] = round((usage.used / usage.total) * 100, 2) if usage.total > 0 else 0.0
        except Exception as e:
            info["error"] = str(e)
    return info


@system_api.route('/stats', methods=['GET', 'POST'])
def handle_api_stats():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    query = request.args
    try:
        settings = load_settings()

        # Aktives Speicherziel ermitteln: Speicherziele der Reihe nach durchgehen,
        # das erste erreichbare gewinnt (Speicherziel 1 -> 2 -> 3 ... als Fallback).
        # So funktioniert die Anzeige mit NAS, nur Cloud oder beidem.
        targets = [t for t in settings.get("storage_targets", []) if t.get("enabled", True)]
        nas_info = None
        for target in targets:
            candidate = _read_target_storage(target)
            if candidate["available"]:
                nas_info = candidate
                break
        if nas_info is None:
            nas_info = {
                "name": targets[0]["name"] if targets else "",
                "type": targets[0].get("type", "") if targets else "",
                "available": False,
                "total": None, "used": None, "free": None, "used_percent": None,
                "path": targets[0].get("root_path", "") if targets else "",
                "error": "Kein Speicherziel verbunden.",
            }

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
