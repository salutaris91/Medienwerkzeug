import os
import re
import json

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
    # Convert spaces/dots/dashes to underscores and lower case
    cleaned = re.sub(r"[\s._-]+", "_", cleaned).lower().strip("_")
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

def load_show_profile(show_name):
    clean_name = clean_show_name(show_name)
    local_path = os.path.join(PROFILES_DIR, f"{clean_name}.json")
    
    if os.path.exists(local_path):
        try:
            with open(local_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading show profile from {local_path}: {e}")

    # Fallback to legacy config
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
        return profile

    # Default profile
    return {
        "pcloud_sonstiges": "n",
        "auto_h265": "n",
        "schema": "staffeln",
        "provider": ""
    }

def save_show_profile(show_name, profile_data):
    clean_name = clean_show_name(show_name)
    local_path = os.path.join(PROFILES_DIR, f"{clean_name}.json")
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
