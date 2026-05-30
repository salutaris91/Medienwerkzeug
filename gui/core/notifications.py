from gui.core.utils import load_settings, save_settings
import os, subprocess, urllib.request, urllib.parse, json
from gui.core.helpers import *
def send_macos_notification(title, message):
    try:
        script = 'on run argv\n display notification item 1 of argv with title item 2 of argv\n end run'
        subprocess.run(["osascript", "-e", script, message, title])
    except Exception as e:
        print(f"Failed to send macOS notification: {e}")

def send_telegram_notification(token, chat_id, message):
    import urllib.request
    import urllib.parse
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": message
        }).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            response.read()
    except Exception as e:
        print(f"Failed to send Telegram notification: {e}")

def send_whatsapp_notification(apikey, phone, message):
    import urllib.request
    import urllib.parse
    try:
        encoded_text = urllib.parse.quote(message)
        encoded_phone = urllib.parse.quote(phone)
        encoded_apikey = urllib.parse.quote(apikey)
        url = f"https://api.callmebot.com/whatsapp.php?phone={encoded_phone}&text={encoded_text}&apikey={encoded_apikey}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            response.read()
    except Exception as e:
        print(f"Failed to send WhatsApp notification: {e}")

def trigger_job_notifications(params, job_size_gb, is_end_of_job=False):
    settings = load_settings()
    if settings.get("notify_only_end") and not is_end_of_job:
        return
        
    media_type = params.get("media_type", "unknown")
    project_name = params.get("project_name", "Unbekannt")
    
    title = "Medienwerkzeug Job Fertig"
    message = f"Der Job '{project_name}' ({media_type}) mit einer Größe von {job_size_gb:.2f} GB wurde erfolgreich verarbeitet."
    
    if settings.get("notify_macos"):
        min_size_macos = settings.get("notify_min_size_macos", settings.get("notify_min_size", 10))
        if job_size_gb >= min_size_macos:
            send_macos_notification(title, message)
        
    if settings.get("notify_telegram"):
        min_size_telegram = settings.get("notify_min_size_telegram", settings.get("notify_min_size", 10))
        if job_size_gb >= min_size_telegram:
            token = settings.get("telegram_token")
            chat_id = settings.get("telegram_chat_id")
            if token and chat_id:
                send_telegram_notification(token, chat_id, f"🚀 {title}\n\n{message}")
            
    if settings.get("notify_whatsapp"):
        min_size_whatsapp = settings.get("notify_min_size_whatsapp", settings.get("notify_min_size", 10))
        if job_size_gb >= min_size_whatsapp:
            apikey = settings.get("whatsapp_apikey")
            phone = settings.get("whatsapp_phone")
            if apikey and phone:
                send_whatsapp_notification(apikey, phone, f"🚀 {title}\n\n{message}")

def open_folders_post_processing(params):
    settings = load_settings()
    outbox_root = settings.get("outbox_dir", os.path.expanduser("~/Downloads/Medien Output"))
    nas_root = settings.get("nas_root", "/Volumes/Kino")
    pcloud_dir = settings.get("pcloud_dir", os.path.expanduser("~/pCloud Drive"))
    
    media_type = params.get("media_type")
    
    if settings.get("open_outbox_finder"):
        if os.path.exists(outbox_root):
            try:
                subprocess.run(["open", outbox_root])
            except Exception as e: print(f"Warning: Ignored exception {e}")

    if settings.get("open_nas_finder"):
        nas_dir = None
        nas_destination_id = params.get("nas_destination_id") or params.get("destination_id")
        if nas_destination_id:
            sync_cats = settings.get("sync_categories", [])
            found_cat = None
            for cat in sync_cats:
                if cat.get("id") == str(nas_destination_id):
                    found_cat = cat
                    break
            if found_cat:
                nas_dir = os.path.join(nas_root, found_cat.get("nas_sub", "").lstrip("/"))
                
                if media_type == "tv":
                    show_name = params.get("nas_show_folder") or params.get("show_name")
                    if show_name:
                        show_dir_name = clean_series_name_for_fs(show_name)
                        nas_dir = os.path.join(nas_dir, show_dir_name)
                elif media_type == "movie":
                    movie_name = params.get("movie_name")
                    if movie_name:
                        movie_dir_name = limit_filename_length(sanitize_filename(movie_name))
                        nas_dir = os.path.join(nas_dir, movie_dir_name)
                        
        if not nas_dir:
            nas_dir = nas_root
            
        if os.path.exists(nas_dir):
            try:
                subprocess.run(["open", nas_dir])
            except Exception as e: print(f"Warning: Ignored exception {e}")
            
    if settings.get("open_pcloud_finder"):
        pcloud_target_dir = None
        pcloud_destination_id = params.get("pcloud_destination_id") or params.get("destination_id")
        if pcloud_destination_id:
            sync_cats = settings.get("sync_categories", [])
            found_cat = None
            for cat in sync_cats:
                if cat.get("id") == str(pcloud_destination_id):
                    found_cat = cat
                    break
            if found_cat:
                pcloud_remote = found_cat.get("pcloud_remote", "")
                if pcloud_remote.startswith("pcloud:"):
                    pcloud_sub = pcloud_remote.split("pcloud:", 1)[1].lstrip("/")
                else:
                    pcloud_sub = pcloud_remote.lstrip("/")
                
                pcloud_target_dir = os.path.join(pcloud_dir, pcloud_sub)
                
                if media_type == "tv":
                    show_name = params.get("nas_show_folder") or params.get("show_name")
                    if show_name:
                        show_dir_name = clean_series_name_for_fs(show_name)
                        pcloud_target_dir = os.path.join(pcloud_target_dir, show_dir_name)
                elif media_type == "movie":
                    movie_name = params.get("movie_name")
                    if movie_name:
                        movie_dir_name = limit_filename_length(sanitize_filename(movie_name))
                        pcloud_target_dir = os.path.join(pcloud_target_dir, movie_dir_name)
                        
        pcloud_open_path = pcloud_target_dir
        if pcloud_open_path and not os.path.exists(pcloud_open_path):
            parent = os.path.dirname(pcloud_open_path)
            if os.path.exists(parent):
                pcloud_open_path = parent
            else:
                pcloud_open_path = pcloud_dir
        elif not pcloud_open_path:
            pcloud_open_path = pcloud_dir
            
        if pcloud_open_path and os.path.exists(pcloud_open_path):
            try:
                subprocess.run(["open", pcloud_open_path])
            except Exception as e: print(f"Warning: Ignored exception {e}")
