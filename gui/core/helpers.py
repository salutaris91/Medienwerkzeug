import queue
log_queue = queue.Queue()
from gui.core.utils import load_settings, save_settings
import os
import queue, re, sys, subprocess, json, urllib.request
def read_lines_from_stream(stream):
    """
    Reads from a binary stream in chunks, decoding and yielding lines
    whenever a newline (\n) or a carriage return (\r) is encountered.
    """
    buffer = b""
    while True:
        chunk = stream.read(4096)
        if not chunk:
            if buffer:
                yield buffer.decode("utf-8", errors="ignore")
            break
            
        chunk = chunk.replace(b"\r", b"\n")
        parts = chunk.split(b"\n")
        
        if len(parts) == 1:
            buffer += parts[0]
        else:
            if buffer + parts[0]:
                yield (buffer + parts[0]).decode("utf-8", errors="ignore")
            for part in parts[1:-1]:
                if part:
                    yield part.decode("utf-8", errors="ignore")
            buffer = parts[-1]

def sanitize_filename(name):
    if not name:
        return ""
    # Replace dashes and dashes variations
    name = name.replace("–", "-").replace("—", "-")
    # Replace colons with space-dash-space
    name = re.sub(r': *', ' - ', name)
    # Replace slashes and pipes with space-dash-space
    name = re.sub(r'[|/]', ' - ', name)
    # Remove forbidden characters for filesystems (Windows/Mac/Linux/Emby/FFmpeg)
    name = re.sub(r'[?*<>"\\]', '', name)
    # Collapse multiple spaces
    name = re.sub(r' +', ' ', name)
    return name.strip()

def clean_episode_title_for_filename(show_name, episode_title):
    """
    Entfernt doppelte Seriennamen am Anfang des Episodentitels, wortgrenzen-sicher.
    """
    if not episode_title:
        return ""
    if not show_name:
        return episode_title

    ep_title_lower = episode_title.lower().strip()

    # Trenne Show-Namen an gängigen Trennern auf
    parts = [p.strip() for p in re.split(r'\s+-\s+|\s+–\s+|\s+—\s+|:\s+', show_name) if p.strip()]
    parts.append(show_name)

    # Letzte Teile ohne Klammern
    for p in list(parts):
        cleaned_part = re.sub(r'\(.*?\)', '', p).strip()
        if cleaned_part and cleaned_part != p:
            parts.append(cleaned_part)

    # Sortiere nach Länge absteigend, um die längsten Übereinstimmungen zuerst zu entfernen
    parts = sorted(list(set(parts)), key=len, reverse=True)

    cleaned_title = episode_title
    for part in parts:
        part_lower = part.lower().strip()
        if not part_lower:
            continue

        escaped_part = re.escape(part_lower)
        # Separatoren: z.B. "Serengeti - " oder "Serengeti: "
        pattern_separator = rf"^{escaped_part}\s*(?:[-:–—]\s*)+"
        # Gefolgt von Leerzeichen und bekannten Nummerierungs-Mustern via Lookahead
        pattern_numbered = rf"^{escaped_part}\s+(?=(?:tag|folge|episode|teil|part|season|staffel|show)\s+\d+)"

        match = re.match(pattern_separator, ep_title_lower)
        if not match:
            match = re.match(pattern_numbered, ep_title_lower)

        if match:
            # Schneide den gefundenen Präfix ab
            length_to_cut = match.end()
            cleaned_title = episode_title[length_to_cut:].strip()
            # Führende Bindestriche, Doppelpunkte oder Leerzeichen im bereinigten Titel nochmals abfangen
            cleaned_title = re.sub(r'^[-:–—\s]+', '', cleaned_title)
            break

    return cleaned_title

def clean_series_name_for_fs(name):
    if not name:
        return ""
    # Remove search-related suffixes in parentheses (case-insensitive)
    name = re.sub(r'\s*\((?:Mediathek\s+(?:Serie|Film)\s+aus\s+URL|Freie\s+Mediathek-Suche|fernsehserien\.de\s+URL|\d*\s*Videos?\s+via\s+URL)\)', '', name, flags=re.IGNORECASE)
    # Remove channel/bracket tags like [ARTE], [ARTE.DE], [ZDF], [TMDB_TV] (case-insensitive, optional trailing spaces/dots/chars/underscores)
    while True:
        new_name = re.sub(r'\s*\[[A-Za-z0-9\._-]+\]\s*$', '', name)
        if new_name == name:
            break
        name = new_name
    # Replace underscores with spaces
    name = name.replace('_', ' ')
    # Also strip any trailing spaces, dots, or dashes that may be left over
    return name.strip()

def is_path_allowed(target_path):
    """
    Security check: Ensure a path is within the allowed directories configured by the user.
    Prevents path traversal and symlink breakout attacks.
    """
    if not target_path:
        return False
        
    from gui.core.utils import get_allowed_roots
    allowed_roots = get_allowed_roots(check_exists=False)
    
    if not allowed_roots:
        return False

    try:
        target_real = os.path.realpath(os.path.expanduser(target_path))
    except Exception:
        return False
    
    for root_real in allowed_roots:
        try:
            # os.path.commonpath throws ValueError if paths are on different drives (Windows)
            if os.path.commonpath([target_real, root_real]) == root_real:
                return True
        except ValueError:
            continue
            
    return False

def extract_absolute_episode_number(ep_num_val, ep_data, filename):
    # 1. Check if absolute_number is explicitly provided in ep_data
    if isinstance(ep_data, dict) and ep_data.get("absolute_number"):
        try:
            return int(ep_data.get("absolute_number"))
        except (ValueError, TypeError):
            pass
            
    # 2. Check if absolute number is in the episode title, e.g., "Title (381)"
    ep_title = ""
    if isinstance(ep_data, dict):
        ep_title = ep_data.get("title", "")
    elif isinstance(ep_data, str):
        ep_title = ep_data
        
    if ep_title:
        # Search for digits in parentheses, e.g., (381) or [381] or ( Folge 381 )
        m_abs = re.search(r'(?:\(|\[)(?:Folge\s+)?(\d+)(?:\)|\])', ep_title, re.IGNORECASE)
        if m_abs:
            return int(m_abs.group(1))
            
    # 3. Check if absolute number is in the source filename, e.g., "Show_(381)_2026.mp4"
    if filename:
        m_file = re.search(r'(?:\(|_|-|\s)(\d{3,4})(?:\)|_|-|\s)', filename)
        if m_file:
            return int(m_file.group(1))
            
    # 4. Fallback: Parse the SxxExx or ep_num_val itself
    if isinstance(ep_num_val, str):
        match = re.match(r"^S(\d+)E(\d+)$", ep_num_val, re.IGNORECASE)
        if match:
            return int(match.group(2))
    elif isinstance(ep_num_val, dict):
        return ep_num_val.get("episode", 1)
        
    try:
        return int(ep_num_val)
    except (ValueError, TypeError):
        return 1

def limit_filename_length(name, max_len=160):
    if not name:
        return ""
    if len(name) > max_len:
        return name[:max_len].strip()
    return name

def normalize_series_name(name):
    if not name:
        return ""
    name = name.lower()
    # Remove year patterns like (1971) or [1971] or just 1971
    name = re.sub(r'\b\d{4}\b', '', name)
    # Remove typical metadata tags
    name = re.sub(r'\b(tvdb|tmdb|deu|ger|eng|sub|dub)\b', '', name)
    name = name.replace("(", "").replace(")", "").replace("[", "").replace("]", "")
    # German umlauts
    name = name.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    # Normalize common conjunctions to avoid mismatch with symbols like &
    name = name.replace("und", "").replace("and", "")
    # Strip leading articles
    articles = [r'^der\s+', r'^die\s+', r'^das\s+', r'^ein\s+', r'^eine\s+', r'^the\s+', r'^a\s+', r'^an\s+']
    for art in articles:
        name = re.sub(art, '', name)
    # Keep only alphanumeric characters
    name = re.sub(r'[^a-z0-9]', '', name)
    return name

def get_matched_series_name(nas_serien_path, outbox_serien_path, clean_show_name):
    normalized_target = normalize_series_name(clean_show_name)
    if not normalized_target:
        return clean_show_name
        
    candidates = set()
    # Scan NAS if mounted/exists
    if nas_serien_path and os.path.exists(nas_serien_path):
        try:
            for entry in os.listdir(nas_serien_path):
                if os.path.isdir(os.path.join(nas_serien_path, entry)) and not entry.startswith('.'):
                    candidates.add(entry)
        except Exception as e:
            log_message(f"⚠️ Serien-Ordner auf NAS konnte nicht gelistet werden: {nas_serien_path} ({e})")
            
    # Scan Outbox
    if outbox_serien_path and os.path.exists(outbox_serien_path):
        try:
            for entry in os.listdir(outbox_serien_path):
                if os.path.isdir(os.path.join(outbox_serien_path, entry)) and not entry.startswith('.'):
                    candidates.add(entry)
        except Exception as e:
            log_message(f"⚠️ Serien-Ordner in Outbox konnte nicht gelistet werden: {outbox_serien_path} ({e})")
            
    # Search for exact normalized match
    for cand in candidates:
        if normalize_series_name(cand) == normalized_target:
            log_message(f"Auto-Matching: Gefundener existierender Ordner '{cand}' für '{clean_show_name}'")
            return cand
            
    return clean_show_name

import threading
import time

_job_log_handles = {}
_job_log_lock = threading.Lock()

def get_current_task_id():
    t_name = threading.current_thread().name
    if t_name.startswith("job-"):
        rest = t_name[4:]
        # Remove suffixes like "-transfer-reader", "-transfer", "-reader"
        for suffix in ["-transfer-reader", "-transfer", "-reader"]:
            if rest.endswith(suffix):
                rest = rest[:-len(suffix)]
        return rest
    return None

def _write_job_log(task_id, msg):
    from gui.core.utils import load_settings
    settings = load_settings()
    data_dir = settings.get("data_dir")
    if not data_dir:
        settings_file = settings.get("settings_file", "")
        if settings_file:
            data_dir = os.path.dirname(settings_file)
        else:
            data_dir = "/config/data"
            
    log_dir = os.path.join(data_dir, "logs")
    
    with _job_log_lock:
        if task_id not in _job_log_handles:
            try:
                os.makedirs(log_dir, exist_ok=True)
                log_file = os.path.join(log_dir, f"job-{task_id}.log")
                _job_log_handles[task_id] = open(log_file, "a", encoding="utf-8")
            except Exception as e:
                print(f"Error opening job log for {task_id}: {e}", file=sys.stderr)
                return
        
        handle = _job_log_handles[task_id]
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        try:
            handle.write(f"[{ts}] {msg}\n")
            handle.flush()
        except Exception as e:
            print(f"Error writing to job log for {task_id}: {e}", file=sys.stderr)

def close_job_log(task_id):
    with _job_log_lock:
        if task_id in _job_log_handles:
            try:
                _job_log_handles[task_id].close()
            except Exception:
                pass
            del _job_log_handles[task_id]

def cleanup_old_job_logs(retention_days=14):
    """Deletes job log files older than retention_days."""
    from gui.core.utils import load_settings
    settings = load_settings()
    data_dir = settings.get("data_dir")
    if not data_dir:
        settings_file = settings.get("settings_file", "")
        if settings_file:
            data_dir = os.path.dirname(settings_file)
        else:
            data_dir = "/config/data"
            
    log_dir = os.path.join(data_dir, "logs")
    if not os.path.exists(log_dir):
        return
        
    now = time.time()
    cutoff = now - (retention_days * 86400)
    try:
        for f in os.listdir(log_dir):
            if f.startswith("job-") and f.endswith(".log"):
                path = os.path.join(log_dir, f)
                try:
                    if os.path.getmtime(path) < cutoff:
                        os.remove(path)
                        print(f"Removed old job log file: {f}")
                except Exception as e:
                    print(f"Error deleting log file {f}: {e}", file=sys.stderr)
    except Exception as e:
        print(f"Error listing log directory for cleanup: {e}", file=sys.stderr)

def log_message(msg):
    log_queue.put(msg)
    print(msg)
    
    task_id = get_current_task_id()
    if task_id:
        _write_job_log(task_id, msg)

def update_task_pipeline_status(task_id, step, status, progress=None):
    if not task_id:
        return
    from gui.core.jobs import update_job
    update_job(task_id, pipeline_step=step, pipeline_status=status, pipeline_progress=progress)

def get_local_version(cmd, args, version_pattern, split_line=False):
    import shutil
    import subprocess
    import re
    executable = shutil.which(cmd)
    if not executable:
        return None
    try:
        proc = subprocess.run([cmd] + args, capture_output=True, text=True, timeout=3)
        if proc.returncode == 0:
            output = proc.stdout.strip()
            if not output:
                output = proc.stderr.strip()
            if split_line:
                lines = output.splitlines()
                if lines:
                    output = lines[0]
            match = re.search(version_pattern, output)
            if match:
                version = match.group(1)
                if version.startswith("v"):
                    version = version[1:]
                return version
            return output[:30]
    except Exception as e:
        print(f"Error getting local version for {cmd}: {e}")
    return None

def fetch_latest_github_version(repo):
    import urllib.request
    import json
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    req = urllib.request.Request(url, headers={"User-Agent": "Medienwerkzeug/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                tag = data.get("tag_name", "")
                if tag.startswith("v"):
                    tag = tag[1:]
                return tag
    except Exception as e:
        print(f"Error fetching latest version for {repo}: {e}")
    return None

def fetch_latest_ffmpeg_version():
    import urllib.request
    import json
    url = "https://evermeet.cx/ffmpeg/info/ffmpeg/release"
    req = urllib.request.Request(url, headers={"User-Agent": "Medienwerkzeug/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                version = data.get("version", "")
                if version.startswith("v"):
                    version = version[1:]
                return version
    except Exception as e:
        print(f"Error fetching latest ffmpeg version: {e}")
    return None

def check_dependency_status(force_updates=False):
    import re
    from gui.core.utils import get_runtime_capabilities
    settings = load_settings()
    
    is_docker = get_runtime_capabilities().get("runtime") == "docker"
    check_updates = (settings.get("check_dependency_updates", False) or force_updates) and not is_docker
    
    deps = {
        "yt-dlp": {
            "cmd": "yt-dlp",
            "args": ["--version"],
            "version_pattern": r"([\d\.]+)",
            "split_line": False,
            "repo": "yt-dlp/yt-dlp",
            "type": "github"
        },
        "rclone": {
            "cmd": "rclone",
            "args": ["version"],
            "version_pattern": r"rclone v([\d\.]+)",
            "split_line": True,
            "repo": "rclone/rclone",
            "type": "github"
        },
        "ffmpeg": {
            "cmd": "ffmpeg",
            "args": ["-version"],
            "version_pattern": r"ffmpeg version ([^\s-]+)",
            "split_line": True,
            "type": "ffmpeg"
        },
        "deno": {
            "cmd": "deno",
            "args": ["--version"],
            "version_pattern": r"deno ([\d\.]+)",
            "split_line": True,
            "repo": "denoland/deno",
            "type": "github"
        }
    }
    
    results = {}
    for name, info in deps.items():
        local_v = get_local_version(info["cmd"], info["args"], info["version_pattern"], info["split_line"])
        latest_v = None
        
        if local_v and check_updates:
            if info["type"] == "github":
                latest_v = fetch_latest_github_version(info["repo"])
            elif info["type"] == "ffmpeg":
                latest_v = fetch_latest_ffmpeg_version()
                
        status = "unknown"
        if local_v is None:
            status = "missing"
        elif check_updates and latest_v:
            l_clean = local_v.strip()
            r_clean = latest_v.strip()
            try:
                l_parts = [int(x) for x in re.findall(r"\d+", l_clean)]
                r_parts = [int(x) for x in re.findall(r"\d+", r_clean)]
                if l_parts >= r_parts:
                    status = "up_to_date"
                else:
                    status = "update_available"
            except Exception:
                if l_clean == r_clean:
                    status = "up_to_date"
                else:
                    status = "update_available"
        elif local_v:
            status = "installed"
            
        results[name] = {
            "installed_version": local_v,
            "latest_version": latest_v,
            "status": status
        }
        
    return results

def get_dir_size_gb(directory):
    total_size = 0
    if os.path.exists(directory):
        if os.path.isdir(directory):
            for root, dirs, files in os.walk(directory):
                for f in files:
                    if f.startswith('.'): continue
                    fp = os.path.join(root, f)
                    try:
                        if os.path.exists(fp):
                            total_size += os.path.getsize(fp)
                    except Exception as e: print(f"Warning: Ignored exception {e}")
        else:
            try:
                total_size = os.path.getsize(directory)
            except Exception as e: print(f"Warning: Ignored exception {e}")
    return total_size / (1024 * 1024 * 1024)

# Global Job Queue
job_queue = queue.Queue()

def get_folder_size_bytes(path):
    import os
    total = 0
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    if not os.path.islink(fp):
                        total += os.path.getsize(fp)
                except OSError:
                    pass
    except Exception as e:
        log_message(f"⚠️ Ordnergröße konnte nicht ermittelt werden: {path} ({e})")
    return total

def folder_size_monitor():
    import time
    from gui.core.utils import load_settings
    from gui.core.notifications import send_macos_notification, send_telegram_notification, send_whatsapp_notification
    
    last_notified = {"inbox": 0, "outbox": 0}
    COOLDOWN = 6 * 3600  # 6 Stunden
    settings = {}
    
    while True:
        try:
            settings = load_settings()
            if not settings.get("folder_monitor_enabled", True):
                time.sleep(600)
                continue
                
            inbox = settings.get("inbox_dir")
            outbox = settings.get("outbox_dir")
            
            thresh_in_gb = float(settings.get("folder_monitor_inbox_threshold_gb", 50.0))
            thresh_out_gb = float(settings.get("folder_monitor_outbox_threshold_gb", 50.0))
            
            from gui.workers.processor import SYSTEM_METRICS
            
            inbox_gb = SYSTEM_METRICS.get('inbox_size_gb') or 0.0
            outbox_gb = SYSTEM_METRICS.get('outbox_size_gb') or 0.0
            
            now = time.time()
            
            if inbox_gb > thresh_in_gb:
                if now - last_notified["inbox"] > COOLDOWN:
                    msg = f"Dein Inbox-Ordner belegt {inbox_gb:.1f} GB (Schwelle: {thresh_in_gb} GB)."
                    if settings.get("folder_monitor_notify_macos"):
                        send_macos_notification("Speicherplatz-Warnung (Inbox)", msg)
                    if settings.get("folder_monitor_notify_telegram"):
                        token = settings.get("telegram_token")
                        chat_id = settings.get("telegram_chat_id")
                        if token and chat_id:
                            send_telegram_notification(token, chat_id, f"⚠️ Speicherplatz-Warnung (Inbox)\n\n{msg}")
                    if settings.get("folder_monitor_notify_whatsapp"):
                        apikey = settings.get("whatsapp_apikey")
                        phone = settings.get("whatsapp_phone")
                        if apikey and phone:
                            send_whatsapp_notification(apikey, phone, f"⚠️ Speicherplatz-Warnung (Inbox)\n\n{msg}")
                    last_notified["inbox"] = now
                    
            if outbox_gb > thresh_out_gb:
                if now - last_notified["outbox"] > COOLDOWN:
                    msg = f"Dein Outbox-Ordner belegt {outbox_gb:.1f} GB (Schwelle: {thresh_out_gb} GB). Denke daran, verarbeitete Projekte zu löschen."
                    if settings.get("folder_monitor_notify_macos"):
                        send_macos_notification("Speicherplatz-Warnung (Outbox)", msg)
                    if settings.get("folder_monitor_notify_telegram"):
                        token = settings.get("telegram_token")
                        chat_id = settings.get("telegram_chat_id")
                        if token and chat_id:
                            send_telegram_notification(token, chat_id, f"⚠️ Speicherplatz-Warnung (Outbox)\n\n{msg}")
                    if settings.get("folder_monitor_notify_whatsapp"):
                        apikey = settings.get("whatsapp_apikey")
                        phone = settings.get("whatsapp_phone")
                        if apikey and phone:
                            send_whatsapp_notification(apikey, phone, f"⚠️ Speicherplatz-Warnung (Outbox)\n\n{msg}")
                    last_notified["outbox"] = now
                    
        except Exception as e:
            print(f"[Folder Monitor] Fehler: {e}")
            
        interval_min = int(settings.get("folder_monitor_interval_minutes", 30)) if settings else 30
        time.sleep(interval_min * 60)

def open_folder_in_finder(path):
    """
    Opens a directory path. On macOS, uses AppleScript to guarantee it opens
    in a new Finder window to prevent tab/window overwrites when opening multiple folders.
    """
    if os.environ.get("MW_RUNTIME") == "docker":
        return

    if not path or not os.path.exists(path):
        return
        
    abs_path = os.path.abspath(path)
    if sys.platform == "darwin":
        try:
            # Escape path for AppleScript
            escaped_path = abs_path.replace('\\', '\\\\').replace('"', '\\"')
            script = f'tell application "Finder"\n    activate\n    make new Finder window to POSIX file "{escaped_path}"\nend tell'
            subprocess.run(["osascript", "-e", script], check=True, capture_output=True)
        except Exception as e:
            print(f"AppleScript open window failed, falling back to open command: {e}")
            try:
                subprocess.run(["open", abs_path])
            except Exception as e2:
                print(f"Open command failed: {e2}")
    elif sys.platform == "win32":
        try:
            os.startfile(abs_path)
        except Exception as e:
            print(f"win32 startfile failed: {e}")
    else:
        try:
            subprocess.run(["xdg-open", abs_path])
        except Exception as e:
            print(f"xdg-open failed: {e}")


def parse_subtitle_suffix(original_name):
    """
    Parses language codes (de, en, fr, es, it, nl, pt, ru, sv, tr, pl)
    and the 'forced' indicator from the original subtitle filename.
    Returns a combined suffix like '.de.forced', '.en', '.forced', or '' (empty string).
    """
    if not original_name:
        return ""
    
    base_name = os.path.splitext(os.path.basename(original_name))[0].lower()
    # Tokenize by replacing any non-alphanumeric chars with spaces and splitting
    tokens = re.split(r'[^a-zA-Z0-9]', base_name)
    
    # Mapping of common language tags to ISO 2-letter codes
    langs = {
        'de': 'de', 'deu': 'de', 'ger': 'de', 'deutsch': 'de', 'german': 'de',
        'en': 'en', 'eng': 'en', 'english': 'en',
        'fr': 'fr', 'fre': 'fr', 'fra': 'fr', 'french': 'fr',
        'es': 'es', 'spa': 'es', 'spanish': 'es',
        'it': 'it', 'ita': 'it', 'italian': 'it',
        'nl': 'nl', 'nld': 'nl', 'dut': 'nl', 'dutch': 'nl',
        'pt': 'pt', 'por': 'pt', 'portuguese': 'pt',
        'ru': 'ru', 'rus': 'ru', 'russian': 'ru',
        'sv': 'sv', 'swe': 'sv', 'swedish': 'sv',
        'tr': 'tr', 'tur': 'tr', 'turkish': 'tr',
        'pl': 'pl', 'pol': 'pl', 'polish': 'pl',
    }
    
    found_lang = None
    is_forced = False
    
    for token in tokens:
        if token in langs:
            found_lang = langs[token]
        if token == 'forced':
            is_forced = True
            
    # Substring fallback if not matched as exact tokens
    if not found_lang:
        for term, code in langs.items():
            if len(term) >= 3 and term in base_name:
                found_lang = code
                break
                
    if 'forced' in base_name:
        is_forced = True
        
    suffix = ""
    if found_lang:
        suffix += f".{found_lang}"
    if is_forced:
        suffix += ".forced"
        
    return suffix


