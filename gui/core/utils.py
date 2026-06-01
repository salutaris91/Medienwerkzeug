import os
import sys
import re
import json
import threading

# Ensure common Homebrew/user paths are in PATH on macOS (especially when started from Finder/.app)
if sys.platform == "darwin":
    _current_path = os.environ.get("PATH", "")
    _paths = _current_path.split(os.pathsep)
    _extra_paths = ["/opt/homebrew/bin", "/usr/local/bin"]
    _modified = False
    for _p in _extra_paths:
        if _p not in _paths:
            _paths.insert(0, _p)  # Prepend to prioritize Homebrew binaries
            _modified = True
    if _modified:
        os.environ["PATH"] = os.pathsep.join(_paths)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
PROFILES_DIR = os.path.join(DATA_DIR, "profiles")
HISTORY_FILE = os.path.join(DATA_DIR, "konv_history.json")

# Ensure directories exist
os.makedirs(PROFILES_DIR, exist_ok=True)

def clean_show_name(show_name):
    if not show_name:
        return "default"
    # Keep alphanumeric, spaces, dots, dashes, underscores
    cleaned = re.sub(r"[^a-zA-Z0-9\s._-]", "", show_name)
    # Remove trailing/leading spaces or dots
    cleaned = cleaned.strip(" .")
    return cleaned or "default"

def parse_conf_file(filepath):
    data = {}
    if not os.path.exists(filepath):
        return data
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    data[k] = v
    except Exception as e:
        print(f"Error parsing legacy conf file {filepath}: {e}")
    return data

def get_profiles_dir():
    settings = load_settings()
    default_dir = os.path.join(DATA_DIR, "profiles")
    path = settings.get("profiles_path", default_dir)
    if not path or not path.strip():
        path = default_dir
    os.makedirs(path, exist_ok=True)
    return path

def load_show_profile(show_name):
    clean_name = clean_show_name(show_name)
    local_path = os.path.join(get_profiles_dir(), f"{clean_name}.json")
    
    profile = None
    if os.path.exists(local_path):
        try:
            with open(local_path, "r", encoding="utf-8") as f:
                profile = json.load(f)
        except Exception as e:
            print(f"Error loading show profile from {local_path}: {e}")

    # Fallback to legacy config
    if not profile:
        legacy_dirs = [
            os.path.expanduser("~/.config/mediawerkzeug/profiles"),
            os.path.expanduser("~/.config/mediawerkzeug")
        ]
        
        # Try different naming variants in legacy dir
        variants = [
            show_name,
            clean_name,
            re.sub(r"\s+\[.*\]", "", show_name).strip() # strip provider suffix like [TMDB_TV]
        ]
        
        legacy_data = None
        for ldir in legacy_dirs:
            if not os.path.exists(ldir):
                continue
            for var in variants:
                if not var:
                    continue
                conf_path = os.path.join(ldir, f"{var}.conf")
                if os.path.exists(conf_path):
                    legacy_data = parse_conf_file(conf_path)
                    break
            if legacy_data:
                break
                
        if legacy_data:
            # Migrate keys
            profile = {
                "pcloud_sonstiges": legacy_data.get("PROFIL_PCLOUD_SONSTIGES", "n"),
                "auto_h265": legacy_data.get("PROFIL_AUTO_H265", "n"),
                "schema": legacy_data.get("PROFIL_SCHEMA", "staffeln"),
                "provider": legacy_data.get("PROFIL_PROVIDER", "")
            }
            # Save migrated profile locally
            save_show_profile(show_name, profile)

    if not profile:
        # Default profile
        profile = {
            "pcloud_sonstiges": "n",
            "auto_h265": "n",
            "schema": "staffeln",
            "provider": "",
            "force_absolute_season_1": False
        }
        
    # Ensure all required default values are set
    if "force_absolute_season_1" not in profile:
        profile["force_absolute_season_1"] = False
        
    return profile

def save_show_profile(show_name, profile_data):
    clean_name = clean_show_name(show_name)
    local_path = os.path.join(get_profiles_dir(), f"{clean_name}.json")
    try:
        with open(local_path, "w", encoding="utf-8") as f:
            json.dump(profile_data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving show profile to {local_path}: {e}")
        return False

def load_konv_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading conversion history from {HISTORY_FILE}: {e}")

    # Fallback to legacy history
    legacy_path = os.path.expanduser("~/.mw_konv_history")
    history = []
    if os.path.exists(legacy_path):
        try:
            with open(legacy_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split("|")
                    if len(parts) == 3:
                        try:
                            quality = int(parts[0])
                        except ValueError:
                            quality = parts[0]
                        codec = parts[1]
                        try:
                            ratio = float(parts[2])
                        except ValueError:
                            ratio = 0.5 # default fallback
                        history.append({
                            "quality": quality,
                            "codec": codec,
                            "ratio": ratio
                        })
            # Save migrated history locally
            save_konv_history(history)
            return history
        except Exception as e:
            print(f"Error migrating legacy history from {legacy_path}: {e}")
            
    return history

def save_konv_history(history_data):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history_data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving conversion history to {HISTORY_FILE}: {e}")
        return False

# ==========================================================================
# THREAD-SAFE GLOBAL SETTINGS CONFIGURATION MANAGEMENT
# ==========================================================================
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "settings.json")
settings_lock = threading.Lock()

_cached_settings = None

_MOCK_SETTINGS = None

def load_settings():
    if _MOCK_SETTINGS is not None:
        return _MOCK_SETTINGS
    global _cached_settings
    default_settings = {
        "inbox_dir": os.path.expanduser("~/Downloads/Medien Input"),
        "outbox_dir": os.path.expanduser("~/Downloads/Medien Output"),
        "nas_root": "/Volumes/Kino",
        "pcloud_dir": os.path.expanduser("~/pCloud Drive"),
        "import_sources": [os.path.expanduser("~/Documents/StreamFab/StreamFab")],
        "check_dependency_updates": False,
        "open_outbox_finder": False,
        "open_nas_finder": False,
        "open_pcloud_finder": False,
        "notify_macos": False,
                "notify_telegram": False,
        "notify_whatsapp": False,
        "folder_monitor_enabled": True,
        "folder_monitor_inbox_threshold_gb": 50.0,
        "folder_monitor_outbox_threshold_gb": 50.0,
        "folder_monitor_notify_macos": True,
        "folder_monitor_notify_telegram": False,
        "folder_monitor_notify_whatsapp": False,
        "folder_monitor_interval_minutes": 30,
        "telegram_token": "",
        "telegram_chat_id": "",
        "notify_whatsapp": False,
        "whatsapp_apikey": "",
        "whatsapp_phone": "",
        "notify_min_size": 10,
        "notify_min_size_macos": 10,
        "notify_min_size_telegram": 10,
        "notify_min_size_whatsapp": 10,
        "notify_only_end": True,
        "show_jokes": True,
        "show_quote": True,
        "app_theme": "deep-space",
        "smart_conversion_default": True,
        "storage_targets": [
            {
                "id": "nas",
                "name": "Speicherziel 1",
                "type": "nas",
                "root_path": "/Volumes/Kino",
                "rclone_remote": "",
                "nas_ip": "192.168.2.208",
                "nas_ip_backup": "100.74.187.125",
                "nas_hostname": "ALEXNAS91",
                "nas_share": "Kino",
                "enabled": True
            },
            {
                "id": "pcloud",
                "name": "Speicherziel 2",
                "type": "pcloud",
                "root_path": os.path.expanduser("~/pCloud Drive"),
                "rclone_remote": "pcloud:",
                "enabled": True
            }
        ],
        "sync_categories": [
            {"id": "1", "name": "Filme", "nas_sub": "/Filme", "pcloud_remote": "pcloud:03_Filme", "targets": {"nas": "/Filme", "pcloud": "pcloud:03_Filme"}},
            {"id": "2", "name": "Serien", "nas_sub": "/Serien", "pcloud_remote": "pcloud:04_Serien", "targets": {"nas": "/Serien", "pcloud": "pcloud:04_Serien"}},
            {"id": "3", "name": "Einzel-Dokus", "nas_sub": "/Dokus/Einzelne Dokus", "pcloud_remote": "pcloud:04a_Dokus", "targets": {"nas": "/Dokus/Einzelne Dokus", "pcloud": "pcloud:04a_Dokus"}},
            {"id": "4", "name": "Doku-Serien", "nas_sub": "/Dokus/Doku-Serien", "pcloud_remote": "pcloud:04a_Dokus", "targets": {"nas": "/Dokus/Doku-Serien", "pcloud": "pcloud:04a_Dokus"}},
            {"id": "5", "name": "Filme 3D", "nas_sub": "/Filme 3D", "pcloud_remote": "pcloud:03a_3D Filme", "targets": {"nas": "/Filme 3D", "pcloud": "pcloud:03a_3D Filme"}},
            {"id": "6", "name": "Sonstiges", "nas_sub": "/Sonstiges", "pcloud_remote": "pcloud:05_Sonstiges", "targets": {"nas": "/Sonstiges", "pcloud": "pcloud:05_Sonstiges"}}
        ],
        "youtube_subscriptions": [],
        "media_server": "emby"
    }
    
    with settings_lock:
        if _cached_settings is not None:
            import copy
            return copy.deepcopy(_cached_settings)
            
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                    
                    # Migration: if storage_targets not present in existing settings file
                    if "storage_targets" not in settings:
                        settings["storage_targets"] = [
                            {
                                "id": "nas",
                                "name": "Speicherziel 1",
                                "type": "nas",
                                "root_path": settings.get("nas_root", "/Volumes/Kino"),
                                "rclone_remote": "",
                                "nas_ip": "192.168.2.208",
                                "nas_ip_backup": "100.74.187.125",
                                "nas_hostname": "ALEXNAS91",
                                "nas_share": "Kino",
                                "enabled": True
                            },
                            {
                                "id": "pcloud",
                                "name": "Speicherziel 2",
                                "type": "pcloud",
                                "root_path": settings.get("pcloud_dir", os.path.expanduser("~/pCloud Drive")),
                                "rclone_remote": "pcloud:",
                                "enabled": True
                            }
                        ]
                    
                    # Migrate categories targets mapping
                    if "sync_categories" in settings:
                        for cat in settings["sync_categories"]:
                            if "targets" not in cat:
                                cat["targets"] = {}
                            if "nas_sub" in cat and "nas" not in cat["targets"]:
                                cat["targets"]["nas"] = cat["nas_sub"]
                            if "pcloud_remote" in cat and "pcloud" not in cat["targets"]:
                                cat["targets"]["pcloud"] = cat["pcloud_remote"]

                    # Migration of per-notification type GB thresholds
                    if "notify_min_size_macos" not in settings:
                        settings["notify_min_size_macos"] = settings.get("notify_min_size", 10)
                    if "notify_min_size_telegram" not in settings:
                        settings["notify_min_size_telegram"] = settings.get("notify_min_size", 10)
                    if "notify_min_size_whatsapp" not in settings:
                        settings["notify_min_size_whatsapp"] = settings.get("notify_min_size", 10)

                    for k, v in default_settings.items():
                        if k not in settings:
                            settings[k] = v
                            
                    # Keep legacy keys in sync with storage_targets root paths
                    for target in settings.get("storage_targets", []):
                        if target.get("id") == "nas":
                            settings["nas_root"] = target.get("root_path", settings.get("nas_root", "/Volumes/Kino"))
                        elif target.get("id") == "pcloud":
                            settings["pcloud_dir"] = target.get("root_path", settings.get("pcloud_dir", os.path.expanduser("~/pCloud Drive")))
                            
                    _cached_settings = settings
                    import copy
                    return copy.deepcopy(_cached_settings)
            except Exception:
                return default_settings
        _cached_settings = default_settings
        import copy
        return copy.deepcopy(_cached_settings)

def save_settings(settings):
    global _cached_settings
    # Synchronize legacy keys on save
    for target in settings.get("storage_targets", []):
        if target.get("id") == "nas":
            settings["nas_root"] = target.get("root_path", settings.get("nas_root", "/Volumes/Kino"))
        elif target.get("id") == "pcloud":
            settings["pcloud_dir"] = target.get("root_path", settings.get("pcloud_dir", os.path.expanduser("~/pCloud Drive")))
            
    with settings_lock:
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4, ensure_ascii=False)
            import copy
            _cached_settings = copy.deepcopy(settings)
            return True
        except Exception:
            return False
