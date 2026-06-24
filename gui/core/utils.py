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
    # Remove existing instances to guarantee correct ordering and avoid duplicates
    _paths = [_p for _p in _paths if _p not in _extra_paths]
    _paths = _extra_paths + _paths
    os.environ["PATH"] = os.pathsep.join(_paths)

from gui.core.persistence import load_settings, save_settings, get_data_dir_path, settings_lock
DATA_DIR = get_data_dir_path()
PROFILES_DIR = os.path.join(DATA_DIR, "profiles")
HISTORY_FILE = os.path.join(DATA_DIR, "konv_history.json")
MW_APP_VERSION = os.environ.get("MW_APP_VERSION", "1.2.0")

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

# settings management is now delegated to gui.core.persistence
import gui.core.persistence as persistence

_MOCK_SETTINGS = None

def load_settings():
    if _MOCK_SETTINGS is not None:
        return _MOCK_SETTINGS
    if persistence._MOCK_SETTINGS is not None:
        return persistence._MOCK_SETTINGS
    return persistence.load_settings()

def save_settings(settings):
    # Sync mock settings if it's set
    global _MOCK_SETTINGS
    if _MOCK_SETTINGS is not None:
        _MOCK_SETTINGS = settings
        return True
    return persistence.save_settings(settings)

def get_runtime_capabilities():
    runtime = os.environ.get("MW_RUNTIME", "desktop").lower()
    if runtime not in ("desktop", "docker"):
        runtime = "desktop"
    
    is_docker = (runtime == "docker")
    
    return {
        "runtime": runtime,
        "capabilities": {
            "open_local_folder": not is_docker,
            "mount_nas": not is_docker,
            "native_notifications": not is_docker,
            "import_sources": True,
            "browser_upload": False,
            "safe_delete": True
        }
    }

def get_allowed_roots(check_exists=True):
    settings = load_settings()
    roots = []
    
    def add_root(p):
        if p and isinstance(p, str):
            p = p.strip()
            if p:
                try:
                    roots.append(os.path.realpath(os.path.expanduser(p)))
                except Exception:
                    pass

    add_root(settings.get("inbox_dir"))
    add_root(settings.get("outbox_dir"))
    add_root(settings.get("nas_root"))
    
    for t in settings.get("storage_targets", []):
        if isinstance(t, dict):
            add_root(t.get("root_path") or t.get("path"))
            
    for s in settings.get("import_sources", []):
        if isinstance(s, str):
            add_root(s)
        elif isinstance(s, dict):
            add_root(s.get("path"))
            
    for f in settings.get("local_download_folders", []):
        if isinstance(f, str):
            add_root(f)
        elif isinstance(f, dict):
            add_root(f.get("path"))
            
    # Remove duplicates and return directories
    unique_roots = []
    for r in roots:
        if r not in unique_roots:
            if not check_exists:
                unique_roots.append(r)
            else:
                try:
                    if os.path.exists(r):
                        unique_roots.append(r)
                except Exception:
                    pass
    return unique_roots
