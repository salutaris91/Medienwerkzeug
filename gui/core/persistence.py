import os
import json
import threading
import shutil
import sys

# APP_ROOT dynamic determination (two levels up from this file)
APP_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Global locks for file concurrency
settings_lock = threading.Lock()
jobs_state_lock = threading.Lock()
action_log_lock = threading.Lock()

# Support mocking settings in legacy unit tests
_MOCK_SETTINGS = None

# Injectable path configurations via environment variables (with APP-Root fallback)
def get_settings_file_path():
    return os.environ.get("MW_SETTINGS_FILE", os.path.join(APP_ROOT, "gui", "settings.json"))

def get_jobs_state_file_path():
    return os.environ.get("MW_JOBS_STATE_FILE", os.path.join(APP_ROOT, "gui", "jobs_state.json"))

def get_action_log_file_path():
    return os.environ.get("MW_ACTION_LOG_FILE", os.path.join(APP_ROOT, "gui", "data", "action_log.jsonl"))

def get_data_dir_path():
    return os.environ.get("MW_DATA_DIR", os.path.join(APP_ROOT, "gui", "data"))

def get_env_file_path():
    # Keep env default path compatible with application and README (gui/.env)
    return os.environ.get("MW_ENV_FILE", os.path.join(APP_ROOT, "gui", ".env"))

# Neutralized default settings (no private folders, IPs, or hostnames)
DEFAULT_SETTINGS = {
    "inbox_dir": "",
    "outbox_dir": "",
    "nas_root": "",
    "pcloud_dir": "",
    "import_sources": [],
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
            "name": "Speicherziel 1 (NAS)",
            "type": "nas",
            "root_path": "",
            "rclone_remote": "",
            "nas_ip": "",
            "nas_ip_backup": "",
            "nas_hostname": "",
            "nas_share": "",
            "enabled": True
        },
        {
            "id": "pcloud",
            "name": "Speicherziel 2 (Cloud)",
            "type": "pcloud",
            "root_path": "",
            "rclone_remote": "",
            "enabled": True
        }
    ],
    "sync_categories": [
        {"id": "1", "name": "Filme", "nas_sub": "", "pcloud_remote": "", "targets": {"nas": "", "pcloud": ""}},
        {"id": "2", "name": "Serien", "nas_sub": "", "pcloud_remote": "", "targets": {"nas": "", "pcloud": ""}},
        {"id": "3", "name": "Einzel-Dokus", "nas_sub": "", "pcloud_remote": "", "targets": {"nas": "", "pcloud": ""}},
        {"id": "4", "name": "Doku-Serien", "nas_sub": "", "pcloud_remote": "", "targets": {"nas": "", "pcloud": ""}},
        {"id": "5", "name": "Filme 3D", "nas_sub": "", "pcloud_remote": "", "targets": {"nas": "", "pcloud": ""}},
        {"id": "6", "name": "Sonstiges", "nas_sub": "", "pcloud_remote": "", "targets": {"nas": "", "pcloud": ""}}
    ],
    "youtube_subscriptions": [],
    "media_server": "",
    "show_console": False,
    "password_hash": "",
    "version": 1
}

def backup_if_valid(file_path, backup_path):
    """
    Creates a backup copy of a JSON file, but only if the file currently on disk
    is syntactically valid JSON. This prevents overwriting a good backup with corrupted data.
    """
    if not os.path.exists(file_path):
        return False
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            json.load(f) # Validate JSON format
        shutil.copy2(file_path, backup_path)
        return True
    except Exception as e:
        print(f"[Persistence] Skipping backup: {file_path} is invalid: {e}", file=sys.stderr)
        return False

def read_json_file(file_path, lock, default_data=None):
    """
    Reads a JSON file thread-safely.
    Falls back to backup (.bak) if parsing fails, and then to default_data.
    """
    backup_path = file_path + ".bak"
    with lock:
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[Persistence] Error reading {file_path}: {e}. Trying backup...", file=sys.stderr)
                if os.path.exists(backup_path):
                    try:
                        with open(backup_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        try:
                            shutil.copy2(backup_path, file_path)
                            print(f"[Persistence] Restored {file_path} from backup.", file=sys.stderr)
                        except Exception as restore_err:
                            print(f"[Persistence] Failed to restore file from backup: {restore_err}", file=sys.stderr)
                        return data
                    except Exception as backup_err:
                        print(f"[Persistence] Error reading backup {backup_path}: {backup_err}", file=sys.stderr)
                else:
                    print(f"[Persistence] No backup file found for {file_path}", file=sys.stderr)
        import copy
        return copy.deepcopy(default_data) if default_data is not None else {}


def write_json_file(file_path, lock, data):
    """
    Writes data to a JSON file thread-safely and atomically.
    Validates data, copies current file to backup if valid, and does temp-write + replace + fsync.
    """
    backup_path = file_path + ".bak"
    temp_path = file_path + ".tmp"
    parent_dir = os.path.dirname(file_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    with lock:
        if os.path.exists(file_path):
            backup_if_valid(file_path, backup_path)
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except OSError:
                    pass
            os.replace(temp_path, file_path)
            return True
        except Exception as e:
            print(f"[Persistence] Failed to write atomically to {file_path}: {e}", file=sys.stderr)
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
            return False

def update_json_file(file_path, lock, update_fn, default_data=None):
    """
    Performs a thread-safe and atomic Read-Modify-Write (RMW) operation.
    Locks the file for the entire duration of reading, modifying, and writing back.
    """
    backup_path = file_path + ".bak"
    temp_path = file_path + ".tmp"
    parent_dir = os.path.dirname(file_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    with lock:
        data = None
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                print(f"[Persistence] RMW load error for {file_path}: {e}. Trying backup...", file=sys.stderr)
                if os.path.exists(backup_path):
                    try:
                        with open(backup_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                    except Exception as backup_err:
                        print(f"[Persistence] RMW backup load error: {backup_err}", file=sys.stderr)
        if data is None:
            import copy
            data = copy.deepcopy(default_data) if default_data is not None else {}
        try:
            update_fn(data)
        except Exception as e:
            print(f"[Persistence] Mutation callback failed during RMW on {file_path}: {e}", file=sys.stderr)
            raise e
        if os.path.exists(file_path):
            backup_if_valid(file_path, backup_path)
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except OSError:
                    pass
            os.replace(temp_path, file_path)
            return True
        except Exception as e:
            print(f"[Persistence] RMW write error for {file_path}: {e}", file=sys.stderr)
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
            return False

# ==========================================================================
# ENV FILE HANDLING
# ==========================================================================

def load_env_keys():
    env_path = get_env_file_path()
    keys = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip()
                    if v.startswith('"') and v.endswith('"'):
                        v = v[1:-1]
                    elif v.startswith("'") and v.endswith("'"):
                        v = v[1:-1]
                    keys[k] = v
    return keys

def save_env_keys(updates):
    env_path = get_env_file_path()
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    updated_keys = set()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            new_lines.append(line)
            continue

        k, v = stripped.split("=", 1)
        k = k.strip()
        if k in updates:
            updated_keys.add(k)
            val = updates[k]
            if val is None or val == "":
                # Remove from environ explicitly
                os.environ.pop(k, None)
                continue # do not append to new_lines (remove from file)
            else:
                new_lines.append(f'{k}="{val}"\n')
                os.environ[k] = val
        else:
            new_lines.append(line)

    for k, val in updates.items():
        if k not in updated_keys and val:
            new_lines.append(f'{k}="{val}"\n')
            os.environ[k] = val

    parent_dir = os.path.dirname(env_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    temp_path = env_path + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
        f.flush()
        try:
            os.fsync(f.fileno())
        except OSError:
            pass
    os.replace(temp_path, env_path)
    ensure_env_example()
    ensure_env_gitignore()

def ensure_env_gitignore():
    env_path = get_env_file_path()
    try:
        rel_path = os.path.relpath(env_path, APP_ROOT)
        if rel_path.startswith("..") or os.path.isabs(rel_path):
            return
    except ValueError:
        return

    gitignore_path = os.path.join(APP_ROOT, ".gitignore")
    env_filename = rel_path.replace(os.sep, "/")

    lines = []
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    if not any(env_filename == line.strip() for line in lines):
        with open(gitignore_path, "a", encoding="utf-8") as f:
            if lines and not lines[-1].endswith("\n"):
                f.write("\n")
            f.write(f"{env_filename}\n")

def ensure_env_example():
    example_path = os.path.join(APP_ROOT, "gui", ".env.example")
    keys_to_ensure = ["TMDB_API_KEY", "TVDB_API_KEY"]

    existing_lines = []
    if os.path.exists(example_path):
        with open(example_path, "r", encoding="utf-8") as f:
            existing_lines = f.readlines()

    existing_keys = set()
    for line in existing_lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        existing_keys.add(line.split("=")[0].strip())

    new_lines = []
    for key in keys_to_ensure:
        if key not in existing_keys:
            new_lines.append(f'{key}=""\n')

    if new_lines:
        with open(example_path, "a", encoding="utf-8") as f:
            f.writelines(new_lines)

def mask_credential(val):
    if not val:
        return ""
    if len(val) <= 8:
        return "****"
    return "****" + val[-4:]

def is_masked(val):
    return val.startswith("****") if val else False

# ==========================================================================
# SETTINGS PERSISTENCE WRAPPERS WITH MIGRATION
# ==========================================================================
_cached_settings = None

def load_settings():
    global _cached_settings
    if _MOCK_SETTINGS is not None:
        import copy
        return copy.deepcopy(_MOCK_SETTINGS)
    if _cached_settings is not None:
        import copy
        return copy.deepcopy(_cached_settings)
    settings_path = get_settings_file_path()
    settings = read_json_file(settings_path, settings_lock, DEFAULT_SETTINGS)
    migrated = False
    # Migration: Ensure storage_targets is populated and preserve legacy configs
    if "storage_targets" not in settings or not settings["storage_targets"]:
        import copy
        settings["storage_targets"] = copy.deepcopy(DEFAULT_SETTINGS["storage_targets"])
        # Crucial fix: Migrate old root paths into new target models to avoid data loss
        for target in settings["storage_targets"]:
            if target["id"] == "nas" and "nas_root" in settings:
                target["root_path"] = settings["nas_root"]
            elif target["id"] == "pcloud" and "pcloud_dir" in settings:
                target["root_path"] = settings["pcloud_dir"]
        migrated = True
    # Migration: Ensure sync_categories is populated
    if "sync_categories" not in settings or not settings["sync_categories"]:
        settings["sync_categories"] = DEFAULT_SETTINGS["sync_categories"]
        migrated = True
    # Migration: Ensure sync_categories target mappings are set
    if "sync_categories" in settings:
        for cat in settings["sync_categories"]:
            if "targets" not in cat:
                cat["targets"] = {}
                migrated = True
            if "nas_sub" in cat and "nas" not in cat["targets"]:
                cat["targets"]["nas"] = cat["nas_sub"]
                migrated = True
            if "pcloud_remote" in cat and "pcloud" not in cat["targets"]:
                cat["targets"]["pcloud"] = cat["pcloud_remote"]
                migrated = True
    # Migration: Ensure min size notifications are set
    for target_key in ["notify_min_size_macos", "notify_min_size_telegram", "notify_min_size_whatsapp"]:
        if target_key not in settings:
            settings[target_key] = settings.get("notify_min_size", 10)
            migrated = True
    # Migration: Ensure version field exists
    if "version" not in settings:
        settings["version"] = 1
        migrated = True
    # Ensure all DEFAULT_SETTINGS keys are present
    for k, v in DEFAULT_SETTINGS.items():
        if k not in settings:
            settings[k] = v
            migrated = True
    # Sync legacy keys
    for target in settings.get("storage_targets", []):
        if target.get("id") == "nas":
            settings["nas_root"] = target.get("root_path", settings.get("nas_root", ""))
        elif target.get("id") == "pcloud":
            settings["pcloud_dir"] = target.get("root_path", settings.get("pcloud_dir", ""))
    # Save back if migrations occurred
    if migrated:
        write_json_file(settings_path, settings_lock, settings)
    _cached_settings = settings
    import copy
    return copy.deepcopy(_cached_settings)

def save_settings(settings):
    global _cached_settings
    # Synchronize legacy keys
    for target in settings.get("storage_targets", []):
        if target.get("id") == "nas":
            settings["nas_root"] = target.get("root_path", settings.get("nas_root", ""))
        elif target.get("id") == "pcloud":
            settings["pcloud_dir"] = target.get("root_path", settings.get("pcloud_dir", ""))
    settings_path = get_settings_file_path()
    success = write_json_file(settings_path, settings_lock, settings)
    if success:
        import copy
        _cached_settings = copy.deepcopy(settings)
    return success

def update_settings(update_fn):
    """
    Thread-safe and atomic settings mutation (RMW).
    Invalidates settings cache on successful write.
    """
    global _cached_settings
    settings_path = get_settings_file_path()
    def rmw_callback(data):
        update_fn(data)
        # Re-sync legacy keys inside RMW transaction lock
        for target in data.get("storage_targets", []):
            if target.get("id") == "nas":
                data["nas_root"] = target.get("root_path", data.get("nas_root", ""))
            elif target.get("id") == "pcloud":
                data["pcloud_dir"] = target.get("root_path", data.get("pcloud_dir", ""))
    success = update_json_file(settings_path, settings_lock, rmw_callback, DEFAULT_SETTINGS)
    if success:
        _cached_settings = None
    return success

def set_password(password):
    from werkzeug.security import generate_password_hash
    pw_hash = generate_password_hash(password, method='pbkdf2:sha256')
    def mutate(data):
        data["password_hash"] = pw_hash
    return update_settings(mutate)

def check_password(password):
    from werkzeug.security import check_password_hash
    settings = load_settings()
    pw_hash = settings.get("password_hash", "")
    if not pw_hash:
        return False
    return check_password_hash(pw_hash, password)

def clear_password():
    def mutate(data):
        data["password_hash"] = ""
    return update_settings(mutate)

