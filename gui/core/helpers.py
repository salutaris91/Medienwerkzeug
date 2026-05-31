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
    Prevents path traversal attacks.
    """
    if not target_path:
        return False
        
    settings = load_settings()
    allowed_roots = [
        os.path.abspath(os.path.expanduser("~/Downloads/Medien Input")),
        os.path.abspath(os.path.expanduser("~/Downloads/Medien Output")),
        os.path.abspath(settings.get("inbox_dir", "")),
        os.path.abspath(settings.get("outbox_dir", "")),
        os.path.abspath(settings.get("nas_root", "/Volumes/Kino")),
    ]
    for t in settings.get("storage_targets", []):
        t_path = t.get("path")
        if t_path:
            allowed_roots.append(os.path.abspath(os.path.expanduser(t_path)))
            
    for s in settings.get("import_sources", []):
        if s:
            allowed_roots.append(os.path.abspath(os.path.expanduser(s)))
            
    allowed_roots = [r for r in allowed_roots if r]
    target_abs = os.path.abspath(os.path.expanduser(target_path))
    
    for root in allowed_roots:
        if target_abs == root or target_abs.startswith(root + os.sep):
            return True
            
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
        return name[:max_len - 3] + "..."
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
        except Exception:
            pass
            
    # Scan Outbox
    if outbox_serien_path and os.path.exists(outbox_serien_path):
        try:
            for entry in os.listdir(outbox_serien_path):
                if os.path.isdir(os.path.join(outbox_serien_path, entry)) and not entry.startswith('.'):
                    candidates.add(entry)
        except Exception:
            pass
            
    # Search for exact normalized match
    for cand in candidates:
        if normalize_series_name(cand) == normalized_target:
            log_message(f"Auto-Matching: Gefundener existierender Ordner '{cand}' für '{clean_show_name}'")
            return cand
            
    return clean_show_name

def log_message(msg):
    log_queue.put(msg)
    print(msg)

def update_task_pipeline_status(task_id, step, status, progress=None):
    if not task_id:
        return
    with active_jobs_lock:
        if task_id in active_jobs and "pipeline" in active_jobs[task_id]:
            if step in active_jobs[task_id]["pipeline"]:
                active_jobs[task_id]["pipeline"][step]["status"] = status
                if progress is not None:
                    active_jobs[task_id]["pipeline"][step]["progress"] = progress

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
    settings = load_settings()
    check_updates = settings.get("check_dependency_updates", False) or force_updates
    
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
    except Exception:
        pass
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
            
            inbox_bytes = get_folder_size_bytes(inbox) if inbox else 0
            outbox_bytes = get_folder_size_bytes(outbox) if outbox else 0
            
            inbox_gb = inbox_bytes / (1024**3)
            outbox_gb = outbox_bytes / (1024**3)
            
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
            subprocess.run(["open", abs_path])
    elif sys.platform == "win32":
        os.startfile(abs_path)
    else:
        subprocess.run(["xdg-open", abs_path])

