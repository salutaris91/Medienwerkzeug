#!/usr/bin/env python3
import os
import sys
import re
import json
import socket
import urllib.parse
import subprocess
import threading
import queue
import time
import shutil
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# Ensure /usr/local/bin and /opt/homebrew/bin are in PATH for subprocesses (yt-dlp, ffmpeg)
for p in ["/usr/local/bin", "/opt/homebrew/bin"]:
    if p not in os.environ.get("PATH", ""):
        os.environ["PATH"] = p + os.pathsep + os.environ.get("PATH", "")


try:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import mw_metadata
except ImportError:
    print("WARNING: Could not import local mw_metadata.py")

try:
    from core import utils
    from core import media
    from core.utils import load_settings, save_settings
except ImportError:
    print("WARNING: Could not import core.utils/media")

import webview

import uuid

# Thread-safe log queue for console log streaming
log_queue = queue.Queue()

# --- Job Queue System ---
job_queue = queue.Queue()
active_jobs = {}  # Stores job status: id -> dict
active_jobs_lock = threading.Lock()

# settings management imported from core.utils

# Thread-safe active YouTube download task tracking
active_yt_tasks = {}
active_yt_tasks_lock = threading.Lock()

def read_lines_from_stream(stream):
    """
    Reads from a binary stream byte-by-byte, decoding and yielding lines
    whenever a newline (\n) or a carriage return (\r) is encountered.
    """
    buffer = bytearray()
    while True:
        b = stream.read(1)
        if not b:
            if buffer:
                yield buffer.decode('utf-8', errors='ignore')
            break
        if b in (b'\n', b'\r'):
            if buffer:
                yield buffer.decode('utf-8', errors='ignore')
                buffer = bytearray()
        else:
            buffer.extend(b)

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
    name = name.strip()
    return name

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
    # Remove year patterns like (1971) or [1971] or just 1971 at the end/inside
    name = re.sub(r'\b\d{4}\b', '', name)
    name = name.replace("(", "").replace(")", "").replace("[", "").replace("]", "")
    # German umlauts
    name = name.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
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

def check_nas_status():
    settings = load_settings()
    nas_root = settings.get("nas_root", "/Volumes/Kino")
    nas_host = "192.168.2.208"
    nas_host_ts = "100.74.187.125"
    
    # 1. Check if mounted
    mounted = False
    try:
        out = subprocess.check_output(["mount"], text=True)
        if f"on {nas_root}" in out:
            mounted = True
    except Exception:
        pass
        
    # 2. Check ping/nc
    pingable = False
    for ip in [nas_host, nas_host_ts]:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.3)
            s.connect((ip, 445))
            s.close()
            pingable = True
            break
        except Exception:
            pass
            
    if mounted:
        return "connected"
    elif pingable:
        return "available_not_mounted"
    else:
        return "offline"

def ensure_nas_mounted():
    settings = load_settings()
    nas_root = settings.get("nas_root", "/Volumes/Kino")
    status = check_nas_status()
    if status == "connected":
        return True
        
    if status == "offline":
        try:
            log_message("🌐 Starte Tailscale...")
            subprocess.run(["tailscale", "up"], capture_output=True, timeout=5)
            status = check_nas_status()
        except Exception:
            pass
            
    if status == "connected":
        return True
        
    if status in ["available_not_mounted", "offline"]:
        nas_host = "192.168.2.208"
        nas_host_ts = "100.74.187.125"
        nas_share = "Kino"
        
        chosen_ip = None
        for ip in [nas_host, nas_host_ts]:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.5)
                s.connect((ip, 445))
                s.close()
                chosen_ip = ip
                break
            except Exception:
                pass
                
        if not chosen_ip:
            log_message("❌ NAS-Host ist offline oder nicht erreichbar.")
            return False
            
        try:
            log_message(f"🔗 Mounte smb://{chosen_ip}/{nas_share}...")
            cmd = ["osascript", "-e", f'mount volume "smb://{chosen_ip}/{nas_share}"']
            subprocess.run(cmd, capture_output=True, timeout=10)
            
            for _ in range(10):
                out = subprocess.check_output(["mount"], text=True)
                if f"on {nas_root}" in out:
                    log_message("✅ NAS erfolgreich gemountet!")
                    return True
                time.sleep(1)
        except Exception as e:
            log_message(f"❌ Fehler beim Einhängen des NAS: {e}")
            
    return os.path.exists(nas_root)

_rsync_progress_flag = None

def get_rsync_progress_flag():
    global _rsync_progress_flag
    if _rsync_progress_flag is not None:
        return _rsync_progress_flag
    
    import subprocess
    try:
        proc = subprocess.Popen(["rsync", "--help"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, _ = proc.communicate()
        if "--info=progress2" in stdout:
            _rsync_progress_flag = "--info=progress2"
            log_message("rsync: Verwende --info=progress2 (Modernes rsync vorhanden)")
        else:
            _rsync_progress_flag = "--progress"
            log_message("rsync: Verwende --progress (macOS openrsync Kompatibilitätsmodus)")
    except Exception as e:
        _rsync_progress_flag = "--progress"
        log_message(f"rsync: Fehler bei Erkennung der rsync-Hilfe ({e}). Verwende --progress")
    return _rsync_progress_flag

def run_rsync_with_progress(src, dst, task_id=None, move=False):
    import subprocess
    import re
    import shutil
    
    os.makedirs(os.path.dirname(dst) if not os.path.isdir(dst) else dst, exist_ok=True)
    
    cmd = ["rsync", "-a", get_rsync_progress_flag()]
    if move:
        cmd.append("--remove-source-files")
        
    src_path = src
    if os.path.isdir(src) and not src.endswith('/'):
        src_path += '/'
        
    cmd.extend([src_path, dst])
    
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0)
    progress_pattern = re.compile(r'(\d+)%')
    
    output_lines = []
    last_logged_pct = -1
    for line in read_lines_from_stream(process.stdout):
        output_lines.append(line.strip())
        match = progress_pattern.search(line)
        if match:
            percent = int(match.group(1))
            if task_id:
                if callable(task_id):
                    task_id(percent, f"Übertragung: {percent}%")
                else:
                    with active_jobs_lock:
                        if task_id in active_jobs:
                            active_jobs[task_id]["progress"] = percent
                            active_jobs[task_id]["message"] = f"Übertragung: {percent}%"
            # Throttle logging: only print to log_message at multiples of 10%
            if percent % 10 == 0 and percent != last_logged_pct:
                log_message(f"Übertragung: {percent}%")
                last_logged_pct = percent
                        
    process.wait()
    success = (process.returncode == 0)
    
    if not success:
        log_message(f"❌ rsync Fehler (Code {process.returncode}):")
        for line in output_lines:
            if not progress_pattern.search(line) and line:
                log_message(f"   rsync: {line}")
                
    if success and move and os.path.isdir(src):
        try:
            shutil.rmtree(src)
        except:
            pass
            
    return success

def run_ffmpeg_with_progress(cmd, filepath, task_id=None, log_queue=None):
    import subprocess
    import re
    
    duration = None
    try:
        duration = media.get_video_duration(filepath)
    except Exception as e:
        log_message(f"Fehler bei get_video_duration: {e}")
        
    if not duration:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in proc.stdout:
            if log_queue:
                log_queue.put(line)
        proc.wait()
        return proc.returncode == 0

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    time_pattern = re.compile(r'time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})')
    time_pattern_sec = re.compile(r'time=(\d+)\.(\d+)')
    
    for line in proc.stdout:
        if log_queue:
            log_queue.put(line)
        
        match = time_pattern.search(line)
        current_time = None
        if match:
            h, m, s, ms = match.groups()
            current_time = int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 100.0
        else:
            match_sec = time_pattern_sec.search(line)
            if match_sec:
                s, ms = match_sec.groups()
                current_time = int(s) + int(ms) / 100.0
                
        if current_time is not None and duration > 0:
            percent = min(99, int((current_time / duration) * 100))
            if task_id:
                if callable(task_id):
                    task_id(percent, f"Konvertierung: {percent}%")
                else:
                    with active_jobs_lock:
                        if task_id in active_jobs:
                            active_jobs[task_id]["progress"] = percent
                            active_jobs[task_id]["message"] = f"Konvertierung: {percent}%"
                        
    proc.wait()
    return proc.returncode == 0

def run_ytdlp_with_progress(cmd, task_id=None, log_queue=None):
    import subprocess
    import re
    
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    progress_pattern = re.compile(r'\[download\]\s+(\d+(?:\.\d+)?)%')
    
    for line in iter(proc.stdout.readline, ''):
        if log_queue:
            log_queue.put(line)
            
        match = progress_pattern.search(line)
        if match:
            percent = int(float(match.group(1)))
            if task_id:
                with active_jobs_lock:
                    if task_id in active_jobs:
                        active_jobs[task_id]["progress"] = percent
                        active_jobs[task_id]["message"] = f"Download: {percent}%"
                        
    proc.wait()
    return proc.returncode == 0

def copy_to_pcloud(source_dir, nas_target_dir, task_id=None, explicit_remote_base=None):
    """
    Kopiert den source_dir in die pCloud. 
    Verwendet den lokalen FUSE-Mount, wenn verfügbar, sonst rclone.
    nas_target_dir wird nach rclone gemappt (z.B. /Volumes/Kino/Serien -> pcloud:04_Serien).
    """
    import shutil
    settings = load_settings()
    nas_root = settings.get("nas_root", "/Volumes/Kino")
    pcloud_local = settings.get("pcloud_dir", os.path.expanduser("~/pCloud Drive"))
    
    if explicit_remote_base:
        remote_base = explicit_remote_base
    else:
        sync_cats = settings.get("sync_categories", [])
        mapping = {}
        for cat in sync_cats:
            mapping[f"{nas_root}{cat['nas_sub']}"] = cat['pcloud_remote']
        
        remote_base = mapping.get(nas_target_dir)
        if not remote_base:
            log_message(f"⚠️ Warnung: Kein pCloud-Mapping für {nas_target_dir} gefunden. Nutze 'pcloud:04b Sonstiges'")
            remote_base = "pcloud:04b Sonstiges"
        
    folder_name = os.path.basename(source_dir.rstrip('/'))
    remote_target = f"{remote_base}/{folder_name}"
    
    log_message("☁️ pCloud-Upload wird vorbereitet...")
    
    fuse_ok = False
    if os.path.isdir(pcloud_local):
        try:
            subprocess.run(["ls", pcloud_local], capture_output=True, timeout=2, check=True)
            fuse_ok = True
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            log_message("⚠️ pCloud Drive antwortet nicht (Zombie-Mount). Bereinige...")
            subprocess.run(["diskutil", "unmount", "force", pcloud_local], capture_output=True)
            log_message("   Starte pCloud App neu oder falle auf rclone zurück.")
            
    if fuse_ok:
        local_target = remote_target.replace("pcloud:", pcloud_local + "/")
        log_message(f"☁️ pCloud Drive (Lokal): Kopiere nach {local_target}")
        try:
            success = run_rsync_with_progress(source_dir, local_target, task_id)
            if success:
                log_message(f"✅ pCloud: Erfolgreich übertragen nach {local_target}")
                return True
            else:
                log_message(f"❌ pCloud Drive Fehler bei der Übertragung.")
        except Exception as e:
            log_message(f"❌ Fehler bei lokalem pCloud-Kopieren: {e}")
            
    log_message(f"☁️ pCloud (rclone Fallback): {remote_target}")
    if not shutil.which("rclone"):
        log_message("⚠️ Warnung: rclone nicht gefunden. Upload abgebrochen.")
        return False
        
    try:
        cmd = ["rclone", "copy", source_dir, remote_target, "--transfers", "2", "--retries", "3", "--stats", "1s", "--stats-one-line"]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0)
        rclone_pattern = re.compile(r'(\d+)%,')
        
        last_logged_pct = -1
        for line in read_lines_from_stream(process.stdout):
            match = rclone_pattern.search(line)
            if match:
                percent = int(match.group(1))
                if task_id:
                    if callable(task_id):
                        task_id(percent, f"Upload: {percent}%")
                    else:
                        with active_jobs_lock:
                            if task_id in active_jobs:
                                active_jobs[task_id]["progress"] = percent
                                active_jobs[task_id]["message"] = f"Upload: {percent}%"
                if percent % 10 == 0 and percent != last_logged_pct:
                    log_message(f"Upload: {percent}%")
                    last_logged_pct = percent
                        
        process.wait()
        if process.returncode == 0:
            log_message(f"✅ pCloud: Rclone-Upload abgeschlossen nach {remote_target}")
            return True
        else:
            log_message(f"❌ pCloud Rclone Fehler.")
    except Exception as e:
        log_message(f"❌ Fehler bei pCloud Rclone: {e}")
        
    return False

def check_streamfab():
    settings = load_settings()
    sources = settings.get("import_sources", [])
    videos = []
    for sf_dir in sources:
        if not os.path.exists(sf_dir):
            continue
        for root, _, files in os.walk(sf_dir):
            for f in files:
                if f.lower().endswith(('.mp4', '.mkv', '.avi', '.webm')):
                    videos.append(f)
    return videos

def import_streamfab_files():
    settings = load_settings()
    sources = settings.get("import_sources", [])
    inbox = settings.get("inbox_dir", os.path.expanduser("~/Downloads/Medien Input"))
    
    os.makedirs(inbox, exist_ok=True)
    count = 0
    
    # 1. Collect all candidates
    all_files_to_import = []
    for sf_dir in sources:
        if not os.path.exists(sf_dir):
            continue
        for root, dirs, files in os.walk(sf_dir):
            for f in files:
                if f.lower().endswith(('.mp4', '.mkv', '.avi', '.webm', '.srt', '.nfo', '.vtt', '.jpg', '.png')):
                    src = os.path.join(root, f)
                    all_files_to_import.append((src, f))
                    
    # 2. Group by base name case-insensitively
    groups = {} # lowercase_base_name -> list of (src, original_filename)
    for src, f in all_files_to_import:
        base_name, _ = os.path.splitext(f)
        key = base_name.lower()
        if key not in groups:
            groups[key] = []
        groups[key].append((src, f))
        
    # 3. Process each group
    for key, file_list in groups.items():
        # Always group into a project folder named after the base name
        first_filename = file_list[0][1]
        folder_name, _ = os.path.splitext(first_filename)
        safe_folder_name = limit_filename_length(sanitize_filename(folder_name))
        project_dir = os.path.join(inbox, safe_folder_name)
        os.makedirs(project_dir, exist_ok=True)
        for src, f in file_list:
            dst = os.path.join(project_dir, f)
            try:
                shutil.move(src, dst)
                count += 1
            except Exception as e:
                print(f"Error moving {f} to project dir {safe_folder_name}: {e}")
                
    # 4. Clean empty directories in sources
    for sf_dir in sources:
        if not os.path.exists(sf_dir):
            continue
        for root, dirs, files in os.walk(sf_dir, topdown=False):
            for d in dirs:
                dir_path = os.path.join(root, d)
                if not os.listdir(dir_path):
                    try:
                        os.rmdir(dir_path)
                    except Exception:
                        pass
    return count

def find_files_recursively(directory, extensions=None):
    found = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for f in files:
            if f.startswith('.'): continue
            if extensions is None or f.lower().endswith(extensions):
                # Return path relative to the base directory
                found.append(os.path.relpath(os.path.join(root, f), directory))
    return found

def fetch_online_jokes_async():
    def target():
        url = "https://raw.githubusercontent.com/salutaris91/Mediawerkzeug/main/gui/data/jokes.json"
        import urllib.request
        import json
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                if isinstance(data, list) and len(data) > 0:
                    local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "jokes.json")
                    os.makedirs(os.path.dirname(local_path), exist_ok=True)
                    with open(local_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    print(f"Jokes successfully updated from GitHub. Total jokes: {len(data)}")
        except Exception as e:
            print(f"Failed to fetch jokes from GitHub (using cached/local copy): {e}")
            
    threading.Thread(target=target, daemon=True).start()

def get_random_joke():
    import random
    import json
    local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "jokes.json")
    try:
        if os.path.exists(local_path):
            with open(local_path, "r", encoding="utf-8") as f:
                jokes = json.load(f)
                if isinstance(jokes, list) and len(jokes) > 0:
                    return random.choice(jokes)
    except Exception as e:
        print(f"Error loading joke: {e}")
        
    return "Was ist gelb und kann nicht schwimmen? Ein Bagger!"

def check_single_subscription(sub):
    import uuid
    import time
    url = sub.get("url")
    search_filter = sub.get("search_filter", "").lower().strip()
    downloaded_ids = sub.get("downloaded_ids", [])
    destination_id = sub.get("destination_id")
    
    if not url:
        return
        
    cmd = ["yt-dlp", "--flat-playlist", "--playlist-end", "10", "--dump-json", url]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if res.returncode != 0:
            print(f"[YouTube Abo-Überwachung] yt-dlp Fehler für {sub.get('name')}: {res.stderr}")
            return
            
        lines = res.stdout.strip().split('\n')
        new_downloads = 0
        
        settings = load_settings()
        sub_in_settings = None
        for s in settings.get("youtube_subscriptions", []):
            if s.get("id") == sub.get("id"):
                sub_in_settings = s
                break
                
        if not sub_in_settings:
            return
            
        for line in lines:
            if not line.strip():
                continue
            try:
                video_data = json.loads(line)
                v_id = video_data.get("id")
                v_title = video_data.get("title", "")
                v_url = video_data.get("url") or f"https://www.youtube.com/watch?v={v_id}"
                
                if not v_id or v_id in downloaded_ids:
                    continue
                    
                # Search filter check
                if search_filter:
                    if search_filter not in v_title.lower():
                        continue
                        
                print(f"[YouTube Abo-Überwachung]: Neuer Treffer für Abo '{sub.get('name')}': {v_title} ({v_url})")
                
                # Start job!
                task_id = str(uuid.uuid4())
                job_params = {
                    "media_type": "youtube",
                    "yt_url": v_url,
                    "yt_format": "best",
                    "yt_embed_thumbnail": True,
                    "copy_to_nas": True,
                    "destination_id": destination_id,
                    "project_name": "",
                    "task_id": task_id
                }
                
                job_info = {
                    "id": task_id,
                    "type": "youtube",
                    "name": f"Abo: {v_title[:40]}",
                    "status": "queued",
                    "progress": 0,
                    "message": "Automatisch gestartet...",
                    "timestamp": time.time(),
                    "params": job_params,
                    "pipeline": {
                        "metadata": {"status": "pending", "progress": 0},
                        "convert": {"status": "pending", "progress": 0},
                        "nas": {"status": "pending", "progress": 0},
                        "pcloud": {"status": "pending", "progress": 0}
                    }
                }
                
                with active_jobs_lock:
                    active_jobs[task_id] = job_info
                    
                job_queue.put(job_info)
                
                # Mark as downloaded
                downloaded_ids.append(v_id)
                new_downloads += 1
                
            except Exception as ex:
                print(f"[YouTube Abo-Überwachung] Fehler bei Video-Verarbeitung: {ex}")
                
        if new_downloads > 0:
            sub_in_settings["downloaded_ids"] = downloaded_ids
            sub_in_settings["last_checked"] = time.time()
            save_settings(settings)
            
    except Exception as e:
        print(f"[YouTube Abo-Überwachung] Fehler bei Check für {sub.get('name')}: {e}")

def check_youtube_subscriptions_loop():
    # Delay initial check slightly
    time.sleep(10)
    while True:
        try:
            settings = load_settings()
            subs = settings.get("youtube_subscriptions", [])
            active_subs = [s for s in subs if s.get("enabled")]
            if active_subs:
                print(f"[YouTube Abo-Überwachung]: Starte turnusmäßigen Check für {len(active_subs)} Abos...")
                for sub in active_subs:
                    check_single_subscription(sub)
        except Exception as e:
            print(f"[YouTube Abo-Überwachung] Fehler: {e}")
        time.sleep(3600)  # Check every hour

def trigger_youtube_subscriptions_check():
    def target():
        try:
            settings = load_settings()
            subs = settings.get("youtube_subscriptions", [])
            active_subs = [s for s in subs if s.get("enabled")]
            if active_subs:
                print(f"[YouTube Abo-Überwachung]: Starte manuell getriggerten Check für {len(active_subs)} Abos...")
                for sub in active_subs:
                    check_single_subscription(sub)
        except Exception as e:
            print(f"[YouTube Abo-Überwachung] Manuelle Überwachung Fehler: {e}")
            
    threading.Thread(target=target, daemon=True).start()

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
                    except: pass
        else:
            try:
                total_size = os.path.getsize(directory)
            except: pass
    return total_size / (1024 * 1024 * 1024)

def send_macos_notification(title, message):
    try:
        t = title.replace('"', '\\"')
        m = message.replace('"', '\\"')
        cmd = f'display notification "{m}" with title "{t}"'
        subprocess.run(["osascript", "-e", cmd])
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
    min_size = settings.get("notify_min_size", 10)
    if job_size_gb < min_size:
        return
    if settings.get("notify_only_end") and not is_end_of_job:
        return
        
    media_type = params.get("media_type", "unknown")
    project_name = params.get("project_name", "Unbekannt")
    
    title = "Medienwerkzeug Job Fertig"
    message = f"Der Job '{project_name}' ({media_type}) mit einer Größe von {job_size_gb:.2f} GB wurde erfolgreich verarbeitet."
    
    if settings.get("notify_macos"):
        send_macos_notification(title, message)
        
    if settings.get("notify_telegram"):
        token = settings.get("telegram_token")
        chat_id = settings.get("telegram_chat_id")
        if token and chat_id:
            send_telegram_notification(token, chat_id, f"🚀 {title}\n\n{message}")
            
    if settings.get("notify_whatsapp"):
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
            except: pass

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
            except: pass
            
    if settings.get("open_pcloud_finder"):
        if os.path.exists(pcloud_dir):
            try:
                subprocess.run(["open", pcloud_dir])
            except: pass

def process_worker(params):
    media_type = params.get("media_type")
    project_name = params.get("project_name", "")
    show_id = params.get("show_id")
    movie_id = params.get("movie_id")
    provider = params.get("provider")
    season = params.get("season")
    mappings = params.get("mappings", {})
    convert = params.get("convert", False)
    quality = params.get("quality", 60)
    delete_original = params.get("delete_original", False)
    copy_to_nas = params.get("copy_to_nas", True)
    nas_destination_id = params.get("nas_destination_id") or params.get("destination_id")
    pcloud_destination_id = params.get("pcloud_destination_id") or params.get("destination_id")
    task_id = params.get("task_id")
    nfo_overrides = params.get("nfo_overrides", {})

    settings = load_settings()
    inbox_root = settings.get("inbox_dir", os.path.expanduser("~/Downloads/Medien Input"))
    nas_root = settings.get("nas_root", "/Volumes/Kino")
    outbox_root = settings.get("outbox_dir", os.path.expanduser("~/Downloads/Medien Output"))
    
    destination = None
    # Resolve NAS destination path
    if nas_destination_id:
        sync_cats = settings.get("sync_categories", [])
        found_cat = None
        for cat in sync_cats:
            if cat.get("id") == str(nas_destination_id):
                found_cat = cat
                break
        if not found_cat:
            for cat in sync_cats:
                nas_sub = cat.get("nas_sub", "")
                if nas_sub and (nas_sub in str(nas_destination_id)):
                    found_cat = cat
                    break
        if found_cat:
            destination = f"{nas_root}{found_cat.get('nas_sub')}"

    # Resolve pCloud destination remote base
    explicit_pcloud_base = None
    if pcloud_destination_id:
        sync_cats = settings.get("sync_categories", [])
        found_cat = None
        for cat in sync_cats:
            if cat.get("id") == str(pcloud_destination_id):
                found_cat = cat
                break
        if not found_cat:
            for cat in sync_cats:
                nas_sub = cat.get("nas_sub", "")
                if nas_sub and (nas_sub in str(pcloud_destination_id)):
                    found_cat = cat
                    break
        if found_cat:
            explicit_pcloud_base = found_cat.get('pcloud_remote')

    
    if project_name:
        current_dir = os.path.join(inbox_root, project_name)
    else:
        current_dir = inbox_root
        
    job_size_gb = 0.0
    try:
        if project_name:
            job_size_gb = get_dir_size_gb(current_dir)
        else:
            if media_type == "tv" and mappings:
                total_bytes = 0
                for f in mappings.keys():
                    fp = os.path.join(current_dir, f)
                    if os.path.exists(fp):
                        total_bytes += os.path.getsize(fp)
                job_size_gb = total_bytes / (1024 * 1024 * 1024)
            elif media_type == "movie":
                total_bytes = 0
                explicit_renames_check = params.get("explicit_renames")
                if explicit_renames_check is not None:
                    v_files = [r["old"] for r in explicit_renames_check]
                else:
                    v_files = [f for f in os.listdir(current_dir) if f.lower().endswith(('.mp4', '.mkv', '.avi', '.webm', '.mov')) and not f.startswith(".")]
                for f in v_files:
                    fp = os.path.join(current_dir, f)
                    if os.path.exists(fp):
                        total_bytes += os.path.getsize(fp)
                job_size_gb = total_bytes / (1024 * 1024 * 1024)
            else:
                job_size_gb = get_dir_size_gb(current_dir)
    except Exception as e:
        print(f"Fehler bei der Berechnung der Jobgröße: {e}")
        
    log_message(f"=== STARTE VERARBEITUNG IN: {current_dir} (Groesse: {job_size_gb:.2f} GB) ===")
    
    explicit_renames = params.get("explicit_renames")
    explicit_subs = params.get("explicit_subs")
    explicit_junk = params.get("explicit_junk")
    
    # 0. Apply explicit user choices from preview if provided
    if explicit_renames is not None:
        log_message("Wende exakte Benutzer-Zuweisungen aus Vorschau an...")
        if explicit_junk:
            for j in explicit_junk:
                jp = os.path.join(current_dir, j)
                if os.path.exists(jp):
                    os.remove(jp)
                    log_message(f"Gelöscht (Junk): {j}")
                    
        if explicit_renames:
            for r in explicit_renames:
                old_path = os.path.join(current_dir, r["old"])
                new_path = os.path.join(current_dir, r["new"])
                if os.path.exists(old_path) and old_path != new_path:
                    os.rename(old_path, new_path)
                    log_message(f"Umbenannt/Hochgezogen: {r['old']} -> {r['new']}")
                    
        if explicit_subs:
            for s in explicit_subs:
                old_path = os.path.join(current_dir, s["old"])
                new_path = os.path.join(current_dir, s["new"])
                if os.path.exists(old_path) and old_path != new_path:
                    os.rename(old_path, new_path)
                    log_message(f"Umbenannt/Hochgezogen (Extra): {s['old']} -> {s['new']}")
                    
        # Cleanup empty subdirectories
        for root, dirs, files in os.walk(current_dir, topdown=False):
            if root == current_dir: continue
            if not os.listdir(root):
                try:
                    os.rmdir(root)
                    log_message(f"Leeren Unterordner entfernt: {os.path.basename(root)}")
                except: pass
    
    if media_type == "tv":
        show_name = clean_series_name_for_fs(params.get("show_name", "Unknown Show"))
        nas_show_folder = params.get("nas_show_folder")
        if nas_show_folder:
            clean_show_name = clean_series_name_for_fs(nas_show_folder)
        else:
            nas_serien = destination if destination else f"{nas_root}/Serien"
            rel_dest = os.path.relpath(nas_serien, nas_root)
            outbox_serien = os.path.join(outbox_root, rel_dest)
            clean_show_name = get_matched_series_name(nas_serien, outbox_serien, limit_filename_length(sanitize_filename(show_name)))
            
        log_message(f"Typ: Serie | Name: {show_name} (Bereinigt: {clean_show_name}) | Staffel: {season}")
        
        # 1. Generate tvshow.nfo and download show artwork (poster.jpg, fanart.jpg)
        with active_jobs_lock:
            if task_id and task_id in active_jobs and "pipeline" in active_jobs[task_id]:
                active_jobs[task_id]["pipeline"]["metadata"]["status"] = "running"
                active_jobs[task_id]["pipeline"]["metadata"]["progress"] = 50
        if show_id and provider:
            log_message("Generiere tvshow.nfo und lade Poster/Fanart...")
            try:
                show_overrides = nfo_overrides.get("show")
                res = mw_metadata.generate_tvshow_nfo(provider, show_id, current_dir, nfo_overrides=show_overrides)
                log_message(f"tvshow.nfo Status: {res}")
            except Exception as e:
                log_message(f"Fehler bei tvshow.nfo: {e}")
                
        # 2. Fetch episodes metadata
        log_message("Rufe Episoden-Metadaten ab...")
        try:
            episodes = {}
            if provider == "tvdb":
                episodes = mw_metadata.fetch_tvdb(show_id, season, "deu")
            elif provider in ["tmdb_tv", "tmdb_tv_en"]:
                lang = "en-US" if provider == "tmdb_tv_en" else "de-DE"
                episodes = mw_metadata.fetch_tmdb_tv(show_id, season, lang)
            elif provider == "tvmaze":
                episodes = mw_metadata.fetch_tvmaze(show_id, season)
            elif provider == "mediathek":
                episodes = mw_metadata.fetch_mediathek_episodes(show_id)
            elif provider == "ytdlp":
                entries = mw_metadata.fetch_ytdlp_url_metadata(show_id)
                episodes = {}
                if not isinstance(entries, dict):
                    for idx, ent in enumerate(entries):
                        ep_idx = ent.get("playlist_index") or ent.get("playlist_autonumber") or (idx + 1)
                        title = ent.get("title", "")
                        alt_title = ent.get("alt_title", "")
                        show_name = ent.get("playlist_title") or ent.get("playlist", "")
                        ep_title = title
                        if alt_title and mw_metadata.normalize_title(title) == mw_metadata.normalize_title(show_name):
                            ep_title = alt_title
                        elif alt_title and not title:
                            ep_title = alt_title
                        episodes[str(ep_idx)] = {"title": ep_title, "plot": ent.get("description", "")}
            elif provider == "fernsehserien":
                episodes = mw_metadata.get_fernsehserien_episodes(show_id, season)
        except Exception as e:
            log_message(f"Fehler beim Laden der Episoden: {e}")
            episodes = {}

        # 3. Setup parallel transmission thread and queue
        mapping_items = list(mappings.items())
        N = len(mapping_items)
        if N == 0:
            log_message("Keine Mappings zur Verarbeitung vorhanden.")
            return

        conv_pct = [0] * N
        nas_pct = [0] * N
        pcloud_pct = 0
        file_titles = [""] * N
        
        has_conv = convert
        has_nas = copy_to_nas
        has_pcloud = params.get("copy_to_pcloud", False)
        
        w_conv = 0.5 if has_conv else 0
        w_nas = 0.3 if has_nas else 0
        w_pcloud = 0.2 if has_pcloud else 0
        total_w = w_conv + w_nas + w_pcloud
        
        if total_w > 0:
            w_conv = w_conv / total_w
            w_nas = w_nas / total_w
            w_pcloud = w_pcloud / total_w
        else:
            w_conv = 0.5
            w_nas = 0.5
            w_pcloud = 0.0

        progress_lock = threading.Lock()

        def update_global_job_progress():
            with progress_lock:
                total_file_progress = 0
                for i in range(N):
                    total_file_progress += (conv_pct[i] * w_conv) + (nas_pct[i] * w_nas)
                
                avg_files = total_file_progress / N if N > 0 else 0
                total_val = avg_files + (pcloud_pct * w_pcloud)
                percent = min(100, max(0, int(total_val)))
                
                active_conv = []
                active_trans = []
                for i in range(N):
                    if conv_pct[i] > 0 and conv_pct[i] < 100:
                        active_conv.append(f"{file_titles[i]} ({conv_pct[i]}%)")
                    if nas_pct[i] > 0 and nas_pct[i] < 100:
                        active_trans.append(f"{file_titles[i]} ({nas_pct[i]}%)")
                        
                status_parts = []
                if active_conv:
                    status_parts.append(f"Konvertierung: {', '.join(active_conv)}")
                elif has_conv and sum(conv_pct) < N * 100:
                    status_parts.append("Konvertierung wartet...")
                    
                if active_trans:
                    status_parts.append(f"Kopieren: {', '.join(active_trans)}")
                elif pcloud_pct > 0 and pcloud_pct < 100:
                    status_parts.append(f"pCloud Upload: {pcloud_pct}%")
                    
                if not status_parts:
                    status_parts.append("Verarbeitung läuft...")
                    
                message = " | ".join(status_parts)
                
                if task_id:
                    with active_jobs_lock:
                        if task_id in active_jobs:
                            active_jobs[task_id]["progress"] = percent
                            active_jobs[task_id]["message"] = message

        transfer_queue = queue.Queue()
        transfer_errors = []

        def transfer_worker():
            while True:
                task = transfer_queue.get()
                if task is None:
                    transfer_queue.task_done()
                    break
                try:
                    task_type = task["type"]
                    file_idx = task.get("file_idx")
                    
                    if task_type == "nas_transfer":
                        dest_dir_outbox = task["dest_dir_outbox"]
                        dest_dir_nas = task["dest_dir_nas"]
                        final_filename = task["final_filename"]
                        clean_title = task["clean_title"]
                        
                        log_message(f"[Transfer Thread]: Starte NAS-Kopieren für {final_filename}...")
                        
                        def nas_progress_cb(percent, msg):
                            nas_pct[file_idx] = percent
                            update_global_job_progress()
                            with active_jobs_lock:
                                if task_id and task_id in active_jobs and "pipeline" in active_jobs[task_id]:
                                    active_jobs[task_id]["pipeline"]["nas"]["status"] = "running"
                                    avg_nas = sum(nas_pct) / N
                                    active_jobs[task_id]["pipeline"]["nas"]["progress"] = int(avg_nas)
                            
                        os.makedirs(dest_dir_nas, exist_ok=True)
                        success = run_rsync_with_progress(
                            os.path.join(dest_dir_outbox, final_filename),
                            os.path.join(dest_dir_nas, final_filename),
                            task_id=nas_progress_cb
                        )
                        if not success:
                            log_message(f"⚠️ [Transfer Thread]: Fehler beim Kopieren von {final_filename} auf das NAS.")
                        else:
                            nas_pct[file_idx] = 100
                            
                        # Copy accompanying files
                        for f in os.listdir(dest_dir_outbox):
                            if f.startswith(clean_title) and f != final_filename:
                                shutil.copy(os.path.join(dest_dir_outbox, f), os.path.join(dest_dir_nas, f))
                        
                        log_message(f"[Transfer Thread]: NAS-Kopieren fertig für {final_filename}.")
                        update_global_job_progress()
                        
                    elif task_type == "show_metadata_nas_transfer":
                        dest_show_dir_outbox = task["dest_show_dir_outbox"]
                        dest_show_dir_nas = task["dest_show_dir_nas"]
                        
                        log_message("[Transfer Thread]: Kopiere Serien-Metadaten auf NAS...")
                        os.makedirs(dest_show_dir_nas, exist_ok=True)
                        for f in ["tvshow.nfo", "poster.jpg", "fanart.jpg"]:
                            p_src = os.path.join(dest_show_dir_outbox, f)
                            if os.path.exists(p_src):
                                shutil.copy(p_src, os.path.join(dest_show_dir_nas, f))
                        log_message("[Transfer Thread]: Serien-Metadaten kopiert.")
                        subprocess.run(["open", dest_show_dir_nas])
                        
                    elif task_type == "pcloud_transfer":
                        dest_show_dir_outbox = task["dest_show_dir_outbox"]
                        nas_serien = task["nas_serien"]
                        explicit_pcloud_base = task["explicit_pcloud_base"]
                        
                        log_message("[Transfer Thread]: Starte pCloud-Upload...")
                        
                        def pcloud_progress_cb(percent, msg):
                            nonlocal pcloud_pct
                            pcloud_pct = percent
                            update_global_job_progress()
                            with active_jobs_lock:
                                if task_id and task_id in active_jobs and "pipeline" in active_jobs[task_id]:
                                    active_jobs[task_id]["pipeline"]["pcloud"]["status"] = "running"
                                    active_jobs[task_id]["pipeline"]["pcloud"]["progress"] = percent
                            
                        copy_to_pcloud(
                            dest_show_dir_outbox,
                            nas_serien,
                            task_id=pcloud_progress_cb,
                            explicit_remote_base=explicit_pcloud_base
                        )
                        pcloud_pct = 100
                        log_message("[Transfer Thread]: pCloud-Upload fertig.")
                        update_global_job_progress()
                        with active_jobs_lock:
                            if task_id and task_id in active_jobs and "pipeline" in active_jobs[task_id]:
                                active_jobs[task_id]["pipeline"]["pcloud"]["status"] = "done"
                                active_jobs[task_id]["pipeline"]["pcloud"]["progress"] = 100
                        
                except Exception as e:
                    log_message(f"❌ [Transfer Thread] Fehler: {e}")
                    transfer_errors.append(e)
                finally:
                    transfer_queue.task_done()

        # Start the Transfer Thread
        transfer_thread = threading.Thread(target=transfer_worker, daemon=True)
        transfer_thread.start()

        # 4. Process mappings sequentially
        for file_idx, (filename, ep_num_val) in enumerate(mapping_items):
            # If explicit_renames was used, the file is ALREADY renamed to the target_filename
            # We just need to generate the NFO!
            
            # Get episode title and original season/episode values
            if isinstance(ep_num_val, dict):
                ep_num = ep_num_val.get("episode", 1)
                ep_season = ep_num_val.get("season", season)
                ep_title = ep_num_val.get("title", "")
                orig_season = ep_season
                orig_episode = ep_num
            else:
                ep_data = episodes.get(str(ep_num_val), {})
                if not ep_data and provider == "ytdlp" and len(episodes) == 1:
                    ep_data = list(episodes.values())[0]
                ep_title = ""
                if isinstance(ep_data, dict):
                    ep_title = ep_data.get("title", "")
                else:
                    ep_title = str(ep_data)
                
                import re
                match = re.match(r"^S(\d+)E(\d+)$", str(ep_num_val), re.IGNORECASE)
                if match:
                    ep_season = int(match.group(1))
                    ep_num = int(match.group(2))
                else:
                    ep_num = ep_num_val
                    ep_season = season
                orig_season = ep_season
                orig_episode = ep_num
                
            force_abs = params.get("force_absolute_season_1", False)
            if force_abs:
                if isinstance(ep_num_val, dict):
                    ep_data = ep_num_val
                else:
                    ep_data = episodes.get(str(ep_num_val), {})
                    if not ep_data and provider == "ytdlp" and len(episodes) == 1:
                        ep_data = list(episodes.values())[0]
                abs_num = extract_absolute_episode_number(ep_num_val, ep_data, filename)
                ep_season = 1
                ep_num = abs_num
                
            ep_title = sanitize_filename(ep_title)
            
            # Format: Show Name - SxxExx - Title.ext
            ext = os.path.splitext(filename)[1].lower()
            try:
                season_str = f"S{int(ep_season):02d}"
            except (ValueError, TypeError):
                season_str = f"S{ep_season}"
            try:
                ep_str = f"E{int(ep_num):02d}"
            except (ValueError, TypeError):
                ep_str = f"E{ep_num}"
            
            # Save file title for display
            file_titles[file_idx] = f"{season_str}{ep_str}"
            
            clean_title = f"{clean_show_name} - {season_str}{ep_str}"
            if ep_title:
                clean_title += f" - {ep_title}"
            clean_title = limit_filename_length(clean_title)
                
            target_filename = f"{clean_title}{ext}"
            target_filepath = os.path.join(current_dir, target_filename)
            
            if explicit_renames is None:
                # Old backwards compatible fallback
                filepath = os.path.join(current_dir, filename)
                if not os.path.exists(filepath):
                    continue
                log_message(f"Benenne um: {filename} -> {target_filename}")
                try:
                    os.rename(filepath, target_filepath)
                except Exception as e:
                    log_message(f"Fehler beim Umbenennen: {e}")
                    continue
                    
                # Rename subtitles
                base_old = os.path.splitext(filename)[0]
                for f in os.listdir(current_dir):
                    if f.startswith(base_old) and f != filename:
                        sub_ext = os.path.splitext(f)[1].lower()
                        if sub_ext in ['.srt', '.vtt', '.ass']:
                            sub_old_path = os.path.join(current_dir, f)
                            sub_new_path = os.path.join(current_dir, f"{clean_title}{sub_ext}")
                            log_message(f"Benenne Untertitel um: {f} -> {clean_title}{sub_ext}")
                            try:
                                os.rename(sub_old_path, sub_new_path)
                            except Exception as e:
                                log_message(f"Fehler: {e}")
                                
            # Generate Episode NFO
            if show_id and provider:
                log_message(f"Generiere Episoden-NFO für {ep_str}...")
                try:
                    ep_overrides = None
                    if "episodes" in nfo_overrides:
                        ep_overrides = nfo_overrides["episodes"].get(filename) or nfo_overrides["episodes"].get(os.path.join(current_dir, filename))
                    res = mw_metadata.generate_episode_nfo(
                        provider, show_id, orig_season, orig_episode, current_dir, clean_title,
                        force_season=ep_season, force_episode=ep_num, nfo_overrides=ep_overrides
                    )
                    log_message(f"Episode NFO Status: {res}")
                except Exception as e:
                    log_message(f"Fehler bei Episode NFO: {e}")
            with active_jobs_lock:
                if task_id and task_id in active_jobs and "pipeline" in active_jobs[task_id]:
                    current_prog = 50 + int(50 * (file_idx + 1) / N)
                    active_jobs[task_id]["pipeline"]["metadata"]["progress"] = min(100, current_prog)
                    if file_idx == N - 1:
                        active_jobs[task_id]["pipeline"]["metadata"]["status"] = "done"

            # H.265 Conversion
            final_filename = target_filename
            final_filepath = target_filepath
            if convert:
                is_hevc = False
                try:
                    probe_cmd = ["ffprobe", "-v", "quiet", "-show_entries", "stream=codec_name", "-select_streams", "v:0", "-of", "csv=p=0", target_filepath]
                    codec = subprocess.check_output(probe_cmd, text=True).strip()
                    if codec in ["hevc", "h265"]:
                        log_message(f"{target_filename} ist bereits HEVC/H.265. Überspringe Konvertierung.")
                        is_hevc = True
                except Exception:
                    pass
                    
                if not is_hevc:
                    log_message(f"Konvertiere {target_filename} nach H.265 (Qualität {quality})...")
                    temp_output = os.path.join(current_dir, f"{clean_title}_neu.mkv")
                    ffmpeg_cmd = [
                        "caffeinate", "-i", "-s", "ffmpeg", "-nostdin", "-i", target_filepath,
                        "-c:v", "hevc_videotoolbox", "-tag:v", "hvc1", "-q:v", str(quality),
                        "-c:a", "copy", temp_output
                    ]
                    try:
                        def ffmpeg_progress_cb(percent, msg):
                            conv_pct[file_idx] = percent
                            update_global_job_progress()
                            with active_jobs_lock:
                                if task_id and task_id in active_jobs and "pipeline" in active_jobs[task_id]:
                                    active_jobs[task_id]["pipeline"]["convert"]["status"] = "running"
                                    avg_conv = sum(conv_pct) / N
                                    active_jobs[task_id]["pipeline"]["convert"]["progress"] = int(avg_conv)
                        success = run_ffmpeg_with_progress(ffmpeg_cmd, target_filepath, task_id=ffmpeg_progress_cb, log_queue=log_queue)
                        if success and os.path.exists(temp_output) and os.path.getsize(temp_output) > 0:
                            log_message("Konvertierung erfolgreich beendet.")
                            try:
                                size_in = os.path.getsize(target_filepath)
                                size_out = os.path.getsize(temp_output)
                                if size_in > 0:
                                    ratio = size_out / size_in
                                    media.add_conversion_to_history(quality, "hevc", ratio)
                                    log_message(f"Konvertierungs-Verhältnis erfasst: {ratio:.4f}")
                            except Exception as e:
                                log_message(f"Fehler beim Erfassen des Konvertierungs-Verhältnisses: {e}")
                            if delete_original:
                                os.remove(target_filepath)
                                log_message("Originaldatei gelöscht.")
                            final_filepath = os.path.join(current_dir, f"{clean_title}.mkv")
                            if os.path.exists(final_filepath):
                                os.remove(final_filepath)
                            os.rename(temp_output, final_filepath)
                            final_filename = f"{clean_title}.mkv"
                            conv_pct[file_idx] = 100
                        else:
                            log_message(f"❌ Fehler bei der Konvertierung von {target_filename}.")
                            if os.path.exists(temp_output):
                                os.remove(temp_output)
                            conv_pct[file_idx] = 100
                    except Exception as e:
                        log_message(f"Konvertierungsfehler: {e}")
                        if os.path.exists(temp_output):
                            os.remove(temp_output)
                        conv_pct[file_idx] = 100
                else:
                    conv_pct[file_idx] = 100
            else:
                conv_pct[file_idx] = 100
            update_global_job_progress()
            
            # Move to local Output folder
            nas_serien = destination if destination else f"{nas_root}/Serien"
            rel_dest = os.path.relpath(nas_serien, nas_root)
            outbox_serien = os.path.join(outbox_root, rel_dest)
            dest_dir_outbox = os.path.join(outbox_serien, clean_show_name, f"Staffel {int(ep_season)}", clean_title)
            
            log_message(f"Verschiebe in Output-Pfad: {dest_dir_outbox}")
            try:
                os.makedirs(dest_dir_outbox, exist_ok=True)
                
                # Move video file
                shutil.move(final_filepath, os.path.join(dest_dir_outbox, final_filename))
                log_message(f"Erfolgreich in Output-Ordner verschoben: {final_filename}")
                
                # Move accompanying files (excluding original unconverted videos)
                video_exts = ('.mp4', '.mkv', '.avi', '.webm', '.mov', '.ts', '.m2ts', '.flv', '.3gp', '.wmv')
                for f in os.listdir(current_dir):
                    if f.startswith(clean_title) and f != final_filename:
                        if f.lower().endswith(video_exts):
                            continue
                        shutil.move(os.path.join(current_dir, f), os.path.join(dest_dir_outbox, f))
                        log_message(f"Begleitdatei in Output-Ordner verschoben: {f}")
            except Exception as e:
                log_message(f"Fehler beim Verschieben in Output-Ordner: {e}")
 
            # Queue NAS transfer task
            if copy_to_nas:
                if not ensure_nas_mounted():
                    raise RuntimeError("NAS konnte nicht gemountet werden. Kopiervorgang abgebrochen.")
                dest_dir_nas = os.path.join(nas_serien, clean_show_name, f"Staffel {int(ep_season)}", clean_title)
                transfer_queue.put({
                    "type": "nas_transfer",
                    "file_idx": file_idx,
                    "dest_dir_outbox": dest_dir_outbox,
                    "dest_dir_nas": dest_dir_nas,
                    "final_filename": final_filename,
                    "clean_title": clean_title
                })
            else:
                nas_pct[file_idx] = 100
                update_global_job_progress()
                
        with active_jobs_lock:
            if task_id and task_id in active_jobs and "pipeline" in active_jobs[task_id]:
                if active_jobs[task_id]["pipeline"]["convert"]["status"] == "running":
                    active_jobs[task_id]["pipeline"]["convert"]["status"] = "done"
                    active_jobs[task_id]["pipeline"]["convert"]["progress"] = 100
                    
        # Move show-level files to local Output
        nas_serien = destination if destination else f"{nas_root}/Serien"
        rel_dest = os.path.relpath(nas_serien, nas_root)
        outbox_serien = os.path.join(outbox_root, rel_dest)
        dest_show_dir_outbox = os.path.join(outbox_serien, clean_show_name)
        try:
            os.makedirs(dest_show_dir_outbox, exist_ok=True)
            for f in ["tvshow.nfo", "poster.jpg", "fanart.jpg"]:
                p_src = os.path.join(current_dir, f)
                if os.path.exists(p_src):
                    shutil.move(p_src, os.path.join(dest_show_dir_outbox, f))
                    log_message(f"Serien-Metadatei in Output-Ordner verschoben: {f}")
            # Open local destination in Finder
            subprocess.run(["open", dest_show_dir_outbox])
        except Exception as e:
            log_message(f"Fehler beim Verschieben der Serien-Metadaten in Output-Ordner: {e}")

        # Copy show-level files to NAS if requested
        if copy_to_nas:
            dest_show_dir_nas = os.path.join(nas_serien, clean_show_name)
            transfer_queue.put({
                "type": "show_metadata_nas_transfer",
                "dest_show_dir_outbox": dest_show_dir_outbox,
                "dest_show_dir_nas": dest_show_dir_nas
            })
            
        if params.get("copy_to_pcloud"):
            transfer_queue.put({
                "type": "pcloud_transfer",
                "dest_show_dir_outbox": dest_show_dir_outbox,
                "nas_serien": nas_serien,
                "explicit_pcloud_base": explicit_pcloud_base
            })
        else:
            pcloud_pct = 100
            update_global_job_progress()
            
        # Send Sentinel and join
        transfer_queue.put(None)
        transfer_thread.join()
        
        with active_jobs_lock:
            if task_id and task_id in active_jobs and "pipeline" in active_jobs[task_id]:
                if active_jobs[task_id]["pipeline"]["nas"]["status"] == "running":
                    active_jobs[task_id]["pipeline"]["nas"]["status"] = "done"
                    active_jobs[task_id]["pipeline"]["nas"]["progress"] = 100
                if active_jobs[task_id]["pipeline"]["pcloud"]["status"] == "running":
                    active_jobs[task_id]["pipeline"]["pcloud"]["status"] = "done"
                    active_jobs[task_id]["pipeline"]["pcloud"]["progress"] = 100
        
        try:
            trigger_job_notifications(params, job_size_gb, is_end_of_job=True)
            open_folders_post_processing(params)
        except Exception as e:
            log_message(f"Fehler bei Benachrichtigungen/Finder-Öffnung: {e}")
        
        if transfer_errors:
            raise transfer_errors[0]

        # Cleanup input folder if it was a project directory under inbox_root
        if current_dir != inbox_root and os.path.exists(current_dir):
            try:
                if not os.listdir(current_dir):
                    os.rmdir(current_dir)
                    log_message(f"Leeren Projekt-Ordner im Input bereinigt: {os.path.basename(current_dir)}")
            except Exception as e:
                log_message(f"Fehler beim Bereinigen des Projekt-Ordners: {e}")

    elif media_type == "movie":
        movie_name = params.get("movie_name")
        movie_id = params.get("movie_id")
        provider = params.get("provider")
        dest_movies = destination if destination else f"{nas_root}/Filme"
        
        log_message(f"Typ: Film | Name: {movie_name} | Ziel: {dest_movies}")
        
        # Scan video files
        if explicit_renames is not None:
            video_files = [r["new"] for r in explicit_renames]
        else:
            video_files = [f for f in os.listdir(current_dir) if f.lower().endswith(('.mp4', '.mkv', '.avi', '.webm', '.mov')) and not f.startswith(".")]
        if not video_files:
            log_message("Keine Video-Dateien im Ordner gefunden.")
            return
            
        clean_movie_name = limit_filename_length(sanitize_filename(movie_name))
        with active_jobs_lock:
            if task_id and task_id in active_jobs and "pipeline" in active_jobs[task_id]:
                active_jobs[task_id]["pipeline"]["metadata"]["status"] = "running"
                active_jobs[task_id]["pipeline"]["metadata"]["progress"] = 50
        
        # Setup progress tracking
        N = len(video_files)
        conv_pct = [0] * N
        nas_pct = [0] * N
        pcloud_pct = [0] * N
        file_titles = [clean_movie_name] * N
        
        has_conv = convert
        has_nas = copy_to_nas
        has_pcloud = params.get("copy_to_pcloud", False)
        
        w_conv = 0.5 if has_conv else 0
        w_nas = 0.3 if has_nas else 0
        w_pcloud = 0.2 if has_pcloud else 0
        total_w = w_conv + w_nas + w_pcloud
        
        if total_w > 0:
            w_conv = w_conv / total_w
            w_nas = w_nas / total_w
            w_pcloud = w_pcloud / total_w
        else:
            w_conv = 0.5
            w_nas = 0.5
            w_pcloud = 0.0

        progress_lock = threading.Lock()

        def update_global_job_progress():
            with progress_lock:
                total_file_progress = 0
                for i in range(N):
                    total_file_progress += (conv_pct[i] * w_conv) + (nas_pct[i] * w_nas) + (pcloud_pct[i] * w_pcloud)
                
                avg_files = total_file_progress / N if N > 0 else 0
                percent = min(100, max(0, int(avg_files)))
                
                active_conv = []
                active_trans = []
                for i in range(N):
                    if conv_pct[i] > 0 and conv_pct[i] < 100:
                        active_conv.append(f"{file_titles[i]} ({conv_pct[i]}%)")
                    if nas_pct[i] > 0 and nas_pct[i] < 100:
                        active_trans.append(f"NAS ({nas_pct[i]}%)")
                    if pcloud_pct[i] > 0 and pcloud_pct[i] < 100:
                        active_trans.append(f"pCloud ({pcloud_pct[i]}%)")
                        
                status_parts = []
                if active_conv:
                    status_parts.append(f"Konvertierung: {', '.join(active_conv)}")
                elif has_conv and sum(conv_pct) < N * 100:
                    status_parts.append("Konvertierung wartet...")
                    
                if active_trans:
                    status_parts.append(f"Übertragung: {', '.join(active_trans)}")
                    
                if not status_parts:
                    status_parts.append("Verarbeitung läuft...")
                    
                message = " | ".join(status_parts)
                
                if task_id:
                    with active_jobs_lock:
                        if task_id in active_jobs:
                            active_jobs[task_id]["progress"] = percent
                            active_jobs[task_id]["message"] = message

        # Initialize Transfer Queue
        transfer_queue = queue.Queue()
        transfer_errors = []

        def transfer_worker():
            while True:
                task = transfer_queue.get()
                if task is None:
                    transfer_queue.task_done()
                    break
                try:
                    task_type = task["type"]
                    file_idx = task.get("file_idx")
                    
                    if task_type == "movie_nas_transfer":
                        dest_movie_dir_outbox = task["dest_movie_dir_outbox"]
                        dest_movie_dir_nas = task["dest_movie_dir_nas"]
                        final_filename = task["final_filename"]
                        
                        log_message(f"[Transfer Thread]: Starte NAS-Kopieren für {final_filename}...")
                        
                        def nas_progress_cb(percent, msg):
                            nas_pct[file_idx] = percent
                            update_global_job_progress()
                            with active_jobs_lock:
                                if task_id and task_id in active_jobs and "pipeline" in active_jobs[task_id]:
                                    active_jobs[task_id]["pipeline"]["nas"]["status"] = "running"
                                    avg_nas = sum(nas_pct) / N
                                    active_jobs[task_id]["pipeline"]["nas"]["progress"] = int(avg_nas)
                            
                        os.makedirs(dest_movie_dir_nas, exist_ok=True)
                        success = run_rsync_with_progress(
                            dest_movie_dir_outbox,
                            dest_movie_dir_nas,
                            task_id=nas_progress_cb
                        )
                        if success:
                            log_message(f"[Transfer Thread]: NAS-Kopieren fertig für {final_filename}.")
                            nas_pct[file_idx] = 100
                            subprocess.run(["open", dest_movie_dir_nas])
                        else:
                            log_message(f"⚠️ [Transfer Thread]: Fehler beim Kopieren von {final_filename} auf das NAS.")
                        update_global_job_progress()
                        
                    elif task_type == "movie_pcloud_transfer":
                        dest_movie_dir_outbox = task["dest_movie_dir_outbox"]
                        dest_movies = task["dest_movies"]
                        explicit_pcloud_base = task["explicit_pcloud_base"]
                        
                        log_message(f"[Transfer Thread]: Starte pCloud-Upload für {clean_movie_name}...")
                        
                        def pcloud_progress_cb(percent, msg):
                            pcloud_pct[file_idx] = percent
                            update_global_job_progress()
                            with active_jobs_lock:
                                if task_id and task_id in active_jobs and "pipeline" in active_jobs[task_id]:
                                    active_jobs[task_id]["pipeline"]["pcloud"]["status"] = "running"
                                    avg_pcloud = sum(pcloud_pct) / N
                                    active_jobs[task_id]["pipeline"]["pcloud"]["progress"] = int(avg_pcloud)
                            
                        copy_to_pcloud(
                            dest_movie_dir_outbox,
                            dest_movies,
                            task_id=pcloud_progress_cb,
                            explicit_remote_base=explicit_pcloud_base
                        )
                        pcloud_pct[file_idx] = 100
                        log_message(f"[Transfer Thread]: pCloud-Upload fertig für {clean_movie_name}.")
                        update_global_job_progress()
                        with active_jobs_lock:
                            if task_id and task_id in active_jobs and "pipeline" in active_jobs[task_id]:
                                active_jobs[task_id]["pipeline"]["pcloud"]["status"] = "done"
                                active_jobs[task_id]["pipeline"]["pcloud"]["progress"] = 100
                        
                except Exception as e:
                    log_message(f"❌ [Transfer Thread] Fehler: {e}")
                    transfer_errors.append(e)
                finally:
                    transfer_queue.task_done()

        # Start the Transfer Thread
        transfer_thread = threading.Thread(target=transfer_worker, daemon=True)
        transfer_thread.start()
        
        # Process video files sequentially
        for file_idx, video_file in enumerate(video_files):
            ext = os.path.splitext(video_file)[1].lower()
            target_filename = f"{clean_movie_name}{ext}"
            filepath = os.path.join(current_dir, video_file)
            target_filepath = os.path.join(current_dir, target_filename)
            
            if video_file != target_filename:
                log_message(f"Benenne um: {video_file} -> {target_filename}")
                try:
                    os.rename(filepath, target_filepath)
                except Exception as e:
                    log_message(f"Fehler beim Umbenennen: {e}")
                    continue
            
            # Generate movie NFO
            if movie_id and provider:
                log_message("Generiere NFO und lade Poster/Fanart...")
                try:
                    movie_overrides = nfo_overrides.get("movie")
                    if provider == "ofdb":
                        res = mw_metadata.generate_ofdb_nfo(movie_id, current_dir, clean_movie_name)
                    else:
                        res = mw_metadata.generate_movie_nfo(movie_id, current_dir, clean_movie_name, nfo_overrides=movie_overrides)
                    log_message(f"Movie NFO Status: {res}")
                except Exception as e:
                    log_message(f"Fehler bei NFO-Erstellung: {e}")
            with active_jobs_lock:
                if task_id and task_id in active_jobs and "pipeline" in active_jobs[task_id]:
                    current_prog = 50 + int(50 * (file_idx + 1) / N)
                    active_jobs[task_id]["pipeline"]["metadata"]["progress"] = min(100, current_prog)
                    if file_idx == N - 1:
                        active_jobs[task_id]["pipeline"]["metadata"]["status"] = "done"
            
            # H.265 Conversion
            final_filename = target_filename
            final_filepath = target_filepath
            if convert:
                is_hevc = False
                try:
                    probe_cmd = ["ffprobe", "-v", "quiet", "-show_entries", "stream=codec_name", "-select_streams", "v:0", "-of", "csv=p=0", target_filepath]
                    codec = subprocess.check_output(probe_cmd, text=True).strip()
                    if codec in ["hevc", "h265"]:
                        log_message(f"{target_filename} ist bereits HEVC/H.265. Überspringe Konvertierung.")
                        is_hevc = True
                except Exception:
                    pass
                    
                if not is_hevc:
                    log_message(f"Konvertiere {target_filename} nach H.265 (Qualität {quality})...")
                    temp_output = os.path.join(current_dir, f"{clean_movie_name}_neu.mkv")
                    ffmpeg_cmd = [
                        "caffeinate", "-i", "-s", "ffmpeg", "-nostdin", "-i", target_filepath,
                        "-c:v", "hevc_videotoolbox", "-tag:v", "hvc1", "-q:v", str(quality),
                        "-c:a", "copy", temp_output
                    ]
                    try:
                        def ffmpeg_progress_cb(percent, msg):
                            conv_pct[file_idx] = percent
                            update_global_job_progress()
                            with active_jobs_lock:
                                if task_id and task_id in active_jobs and "pipeline" in active_jobs[task_id]:
                                    active_jobs[task_id]["pipeline"]["convert"]["status"] = "running"
                                    avg_conv = sum(conv_pct) / N
                                    active_jobs[task_id]["pipeline"]["convert"]["progress"] = int(avg_conv)
                        success = run_ffmpeg_with_progress(ffmpeg_cmd, target_filepath, task_id=ffmpeg_progress_cb, log_queue=log_queue)
                        if success and os.path.exists(temp_output) and os.path.getsize(temp_output) > 0:
                            log_message("Konvertierung erfolgreich.")
                            try:
                                size_in = os.path.getsize(target_filepath)
                                size_out = os.path.getsize(temp_output)
                                if size_in > 0:
                                    ratio = size_out / size_in
                                    media.add_conversion_to_history(quality, "hevc", ratio)
                                    log_message(f"Konvertierungs-Verhältnis erfasst: {ratio:.4f}")
                            except Exception as e:
                                log_message(f"Fehler beim Erfassen des Konvertierungs-Verhältnisses: {e}")
                            if delete_original:
                                os.remove(target_filepath)
                                log_message("Originaldatei gelöscht.")
                            final_filepath = os.path.join(current_dir, f"{clean_movie_name}.mkv")
                            if os.path.exists(final_filepath):
                                os.remove(final_filepath)
                            os.rename(temp_output, final_filepath)
                            final_filename = f"{clean_movie_name}.mkv"
                            conv_pct[file_idx] = 100
                        else:
                            log_message(f"❌ Fehler bei der Konvertierung.")
                            if os.path.exists(temp_output):
                                os.remove(temp_output)
                            conv_pct[file_idx] = 100
                    except Exception as e:
                        log_message(f"Konvertierungsfehler: {e}")
                        if os.path.exists(temp_output):
                            os.remove(temp_output)
                        conv_pct[file_idx] = 100
                else:
                    conv_pct[file_idx] = 100
            else:
                conv_pct[file_idx] = 100
            update_global_job_progress()
 
            # Move to local Output folder
            dest_movies = destination if destination else f"{nas_root}/Filme"
            rel_dest = os.path.relpath(dest_movies, nas_root)
            outbox_movies = os.path.join(outbox_root, rel_dest)
            dest_movie_dir_outbox = os.path.join(outbox_movies, clean_movie_name)
            
            log_message(f"Verschiebe in Output-Pfad: {dest_movie_dir_outbox}")
            try:
                os.makedirs(dest_movie_dir_outbox, exist_ok=True)
                
                # Move movie video file
                shutil.move(final_filepath, os.path.join(dest_movie_dir_outbox, final_filename))
                log_message(f"Erfolgreich in Output-Ordner verschoben: {final_filename}")
                
                # Move accompanying files (excluding unconverted video files)
                video_exts = ('.mp4', '.mkv', '.avi', '.webm', '.mov', '.ts', '.m2ts', '.flv', '.3gp', '.wmv')
                for f in os.listdir(current_dir):
                    if f != final_filename and not f.startswith("."):
                        if f.lower().endswith(video_exts):
                            continue
                        shutil.move(os.path.join(current_dir, f), os.path.join(dest_movie_dir_outbox, f))
                        log_message(f"Begleitdatei in Output-Ordner verschoben: {f}")
                        
                # Ensure both poster.jpg/fanart.jpg and [clean_movie_name]-poster.jpg / [clean_movie_name]-fanart.jpg exist
                for art_name in ["poster.jpg", "fanart.jpg"]:
                    art_src = os.path.join(dest_movie_dir_outbox, art_name)
                    suffix = "-poster.jpg" if art_name == "poster.jpg" else "-fanart.jpg"
                    art_dst = os.path.join(dest_movie_dir_outbox, f"{clean_movie_name}{suffix}")
                    
                    if os.path.exists(art_src) and not os.path.exists(art_dst):
                        shutil.copy(art_src, art_dst)
                        log_message(f"Erstellt: {clean_movie_name}{suffix}")
                    elif os.path.exists(art_dst) and not os.path.exists(art_src):
                        shutil.copy(art_dst, art_src)
                        log_message(f"Erstellt: {art_name}")
                        
                # Open output directory in Finder
                subprocess.run(["open", dest_movie_dir_outbox])
            except Exception as e:
                log_message(f"Fehler beim Verschieben in Output-Ordner: {e}")
 
            # Queue NAS copy
            if copy_to_nas:
                if not ensure_nas_mounted():
                    raise RuntimeError("NAS konnte nicht gemountet werden. Kopiervorgang abgebrochen.")
                dest_movie_dir_nas = os.path.join(dest_movies, clean_movie_name)
                transfer_queue.put({
                    "type": "movie_nas_transfer",
                    "file_idx": file_idx,
                    "dest_movie_dir_outbox": dest_movie_dir_outbox,
                    "dest_movie_dir_nas": dest_movie_dir_nas,
                    "final_filename": final_filename
                })
            else:
                nas_pct[file_idx] = 100
                update_global_job_progress()
                
            # Queue pCloud copy
            if params.get("copy_to_pcloud"):
                transfer_queue.put({
                    "type": "movie_pcloud_transfer",
                    "file_idx": file_idx,
                    "dest_movie_dir_outbox": dest_movie_dir_outbox,
                    "dest_movies": dest_movies,
                    "explicit_pcloud_base": explicit_pcloud_base
                })
            else:
                pcloud_pct[file_idx] = 100
                update_global_job_progress()
                
        with active_jobs_lock:
            if task_id and task_id in active_jobs and "pipeline" in active_jobs[task_id]:
                if active_jobs[task_id]["pipeline"]["convert"]["status"] == "running":
                    active_jobs[task_id]["pipeline"]["convert"]["status"] = "done"
                    active_jobs[task_id]["pipeline"]["convert"]["progress"] = 100
                    
        # Send Sentinel and join
        transfer_queue.put(None)
        transfer_thread.join()
        
        with active_jobs_lock:
            if task_id and task_id in active_jobs and "pipeline" in active_jobs[task_id]:
                if active_jobs[task_id]["pipeline"]["nas"]["status"] == "running":
                    active_jobs[task_id]["pipeline"]["nas"]["status"] = "done"
                    active_jobs[task_id]["pipeline"]["nas"]["progress"] = 100
                if active_jobs[task_id]["pipeline"]["pcloud"]["status"] == "running":
                    active_jobs[task_id]["pipeline"]["pcloud"]["status"] = "done"
                    active_jobs[task_id]["pipeline"]["pcloud"]["progress"] = 100
        
        try:
            trigger_job_notifications(params, job_size_gb, is_end_of_job=True)
            open_folders_post_processing(params)
        except Exception as e:
            log_message(f"Fehler bei Benachrichtigungen/Finder-Öffnung: {e}")
        
        if transfer_errors:
            raise transfer_errors[0]
 
        # Cleanup input folder if it was a project directory under inbox_root
        if current_dir != inbox_root and os.path.exists(current_dir):
            try:
                if not os.listdir(current_dir):
                    os.rmdir(current_dir)
                    log_message(f"Leeren Projekt-Ordner im Input bereinigt: {os.path.basename(current_dir)}")
            except Exception as e:
                log_message(f"Fehler beim Bereinigen des Projekt-Ordners: {e}")
                    
    elif media_type == "youtube":
        task_id = params.get("task_id")
        url = params.get("yt_url")
        format_opt = params.get("yt_format", "best")
        embed_thumb = params.get("yt_embed_thumbnail", False)
        subs = params.get("yt_subtitles", [])
        
        split_chapters = params.get("split_chapters", False)
        open_losslesscut = params.get("open_losslesscut", False)
        trim_start = params.get("trim_start", "")
        trim_end = params.get("trim_end", "")
        
        metadata_mode = params.get("metadata_mode", "youtube")
        movie_id = params.get("movie_id")
        movie_name = params.get("movie_name")
        show_id = params.get("show_id")
        show_name = clean_series_name_for_fs(params.get("show_name")) if params.get("show_name") else ""
        
        nas_show_folder = params.get("nas_show_folder")
        if nas_show_folder:
            clean_show_name = clean_series_name_for_fs(nas_show_folder)
        else:
            nas_serien = destination if destination else f"{nas_root}/Serien"
            rel_dest = os.path.relpath(nas_serien, nas_root)
            outbox_serien = os.path.join(outbox_root, rel_dest)
            clean_show_name = get_matched_series_name(nas_serien, outbox_serien, limit_filename_length(sanitize_filename(show_name))) if show_name else ""
            
        season = params.get("season")
        provider = params.get("provider")
        
        copy_to_nas = params.get("copy_to_nas", False)
        # Use destination resolved at the beginning of process_worker instead of overwriting it
        
        settings = load_settings()
        inbox_root = settings.get("inbox_dir", os.path.expanduser("~/Downloads/Medien Input"))
        nas_root = settings.get("nas_root", "/Volumes/Kino")
        
        # Temp dir inside Downloads/Medien Input/temp_yt_<task_id>
        temp_dir = os.path.join(inbox_root, f"temp_yt_{task_id}")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Setup task state
        task_info = {
            "state": "downloading",
            "temp_dir": temp_dir,
            "params": params,
            "event": threading.Event(),
            "mapping_event": threading.Event(),
            "mapping": None
        }
        with active_yt_tasks_lock:
            active_yt_tasks[task_id] = task_info
            
        log_message(f"=== STARTE YOUTUBE DOWNLOAD PIPELINE FUER TASK {task_id} ===")
        log_message(f"Ziel-Temp-Ordner: {temp_dir}")
        
        try:
            # Build yt-dlp command
            cmd = ["yt-dlp", "--newline", "-P", temp_dir]
            
            # Format selection
            if format_opt == "audio":
                cmd.extend(["-f", "ba", "-x", "--audio-format", "mp3"])
            elif format_opt == "best":
                cmd.extend(["-f", "bv*+ba/b"])
            elif "_h264" in format_opt:
                h_val = format_opt.split("p_")[0]
                cmd.extend(["-f", f"bestvideo[height<={h_val}][vcodec^=avc1]+bestaudio[acodec^=mp4a]/bestvideo[height<={h_val}]+bestaudio/best"])
            elif "_vp9" in format_opt:
                h_val = format_opt.split("p_")[0]
                cmd.extend(["-f", f"bestvideo[height<={h_val}][vcodec^=vp09]+bestaudio/bestvideo[height<={h_val}][vcodec^=vp9]+bestaudio/bestvideo[height<={h_val}]+bestaudio/best"])
            elif "_av1" in format_opt:
                h_val = format_opt.split("p_")[0]
                cmd.extend(["-f", f"bestvideo[height<={h_val}][vcodec^=av01]+bestaudio/bestvideo[height<={h_val}]+bestaudio/best"])
            elif format_opt.endswith("p"):
                h_val = format_opt[:-1]
                cmd.extend(["-f", f"bestvideo[height<={h_val}]+bestaudio/best"])
            else:
                cmd.extend(["-f", "bv*+ba/b"])
                
            # Thumbnail embedding (native yt-dlp, if not splitting chapters or doing LosslessCut where it might strip metadata)
            if embed_thumb and not (split_chapters or open_losslesscut):
                cmd.append("--embed-thumbnail")
                
            # Subtitles
            if subs:
                cmd.extend(["--write-subs", "--embed-subs"])
                lang_str = ",".join(subs)
                cmd.extend(["--sub-langs", lang_str])
                
            # Trimming / Chapter splitting
            if split_chapters:
                cmd.extend(["--split-chapters", "--force-keyframes-at-cuts"])
            elif trim_start or trim_end:
                t_start = trim_start if trim_start else "00:00:00"
                t_end = trim_end if trim_end else "*inf"
                cmd.extend(["--download-sections", f"*{t_start}-{t_end}"])
                
            cmd.extend(["--cookies-from-browser", "chrome"])
            cmd.append(url)
            
            log_message(f"Fuehre aus: {' '.join(cmd)}")
            success = run_ytdlp_with_progress(cmd, task_id=task_id, log_queue=log_queue)
            
            # If fail, retry without cookies
            if not success:
                log_message("Download mit Cookies fehlgeschlagen. Versuche ohne Cookies...")
                cmd_fallback = [x for x in cmd if x != "chrome" and x != "--cookies-from-browser"]
                success = run_ytdlp_with_progress(cmd_fallback, task_id=task_id, log_queue=log_queue)
                
            if not success:
                raise RuntimeError("Download vollständig fehlgeschlagen.")
                
            log_message("Download erfolgreich beendet.")
            
            # Find downloaded files
            downloaded_files = [f for f in os.listdir(temp_dir) if f.lower().endswith(('.mp4', '.mkv', '.avi', '.webm', '.mov', '.mp3', '.m4a')) and not f.startswith(".")]
            
            # If LosslessCut is checked and we have video files
            if open_losslesscut and downloaded_files:
                primary_file = downloaded_files[0]
                primary_filepath = os.path.join(temp_dir, primary_file)
                
                lossless_path = "/Applications/LosslessCut.app"
                if os.path.exists(lossless_path):
                    log_message(f"🎬 Oeffne {primary_file} in LosslessCut...")
                    subprocess.run(["open", "-a", "LosslessCut", primary_filepath])
                    
                    # Update state and wait for GUI event
                    task_info["state"] = "waiting_for_cut"
                    log_message("⏳ Warte darauf, dass der Nutzer den Schnitt in LosslessCut fertigstellt...")
                    task_info["event"].wait()
                    
                    log_message("Schnitt als abgeschlossen markiert. Scanne nach exportierten Dateien...")
                    time.sleep(1)
                    
                    all_videos = [f for f in os.listdir(temp_dir) if f.lower().endswith(('.mp4', '.mkv', '.avi', '.webm', '.mov')) and not f.startswith(".")]
                    cut_files = [f for f in all_videos if f != primary_file]
                    
                    if cut_files:
                        log_message(f"Schnittdateien gefunden: {', '.join(cut_files)}")
                        try:
                            os.remove(primary_filepath)
                            log_message("Ungeschnittene Originaldatei gelöscht.")
                        except Exception as e:
                            log_message(f"Fehler beim Loeschen des Originals: {e}")
                        downloaded_files = cut_files
                    else:
                        log_message("Keine Schnittdateien gefunden. Verwende Originaldatei.")
                        downloaded_files = [primary_file]
                else:
                    log_message("⚠️ LosslessCut.app nicht unter /Applications gefunden. Ueberspringe...")
            
            # Refresh downloaded files list
            downloaded_files = sorted([f for f in os.listdir(temp_dir) if f.lower().endswith(('.mp4', '.mkv', '.avi', '.webm', '.mov', '.mp3', '.m4a')) and not f.startswith(".")])
            
            if not downloaded_files:
                raise RuntimeError("Keine verarbeitbaren Videodateien gefunden.")
                
            # TMDB/TVDB Season/Episodes Mapping for Series Mode
            mapping = {}
            if metadata_mode == "tv" and show_id and len(downloaded_files) > 1:
                task_info["state"] = "waiting_for_mapping"
                log_message("⏳ Warte auf Zuweisung der Video-Kapitel/Segmente im Web-Interface...")
                task_info["mapping_event"].wait()
                
                mapping = task_info.get("mapping", {})
                log_message(f"Zuweisungen erhalten: {mapping}")
                
            # If embed_thumbnail was requested and we had splits/cuts, embed thumbnail now
            if embed_thumb:
                log_message("🖼️ Thumbnail wird heruntergeladen und eingebettet...")
                thumb_tmp = os.path.join(temp_dir, ".thumbnail_tmp")
                thumb_jpg = os.path.join(temp_dir, ".thumbnail_tmp.jpg")
                if os.path.exists(thumb_jpg):
                    os.remove(thumb_jpg)
                
                thumb_dl_cmd = ["yt-dlp", "--write-thumbnail", "--skip-download", "--convert-thumbnails", "jpg", "-o", thumb_tmp, url]
                subprocess.run(thumb_dl_cmd, capture_output=True)
                
                if os.path.exists(thumb_jpg):
                    for f in downloaded_files:
                        if f.lower().endswith(('.mp4', '.mkv')):
                            filepath = os.path.join(temp_dir, f)
                            temp_thumb_file = os.path.join(temp_dir, f"thumb_{f}")
                            ff_thumb_cmd = [
                                "ffmpeg", "-y", "-i", filepath, "-i", thumb_jpg,
                                "-map", "0", "-map", "1", "-c", "copy",
                                "-disposition:v:1", "attached_pic", temp_thumb_file
                            ]
                            ff_proc = subprocess.run(ff_thumb_cmd, capture_output=True)
                            if ff_proc.returncode == 0 and os.path.exists(temp_thumb_file):
                                os.replace(temp_thumb_file, filepath)
                                log_message(f"  ✅ Thumbnail in {f} eingebettet.")
                            else:
                                if os.path.exists(temp_thumb_file):
                                    os.remove(temp_thumb_file)
                                log_message(f"  ❌ Einbetten in {f} fehlgeschlagen.")
                    os.remove(thumb_jpg)
                else:
                    log_message("  ❌ Thumbnail konnte nicht geladen werden.")
            
            # NFO & Renaming
            # Generate tvshow.nfo in Series mode
            if metadata_mode == "tv" and show_id and provider:
                try:
                    mw_metadata.generate_tvshow_nfo(provider, show_id, temp_dir)
                except Exception as e:
                    log_message(f"Fehler bei tvshow.nfo: {e}")
                    
            all_transfers_successful = True
            for idx, filename in enumerate(downloaded_files):
                filepath = os.path.join(temp_dir, filename)
                ext = os.path.splitext(filename)[1].lower()
                target_filename = filename
                clean_base = os.path.splitext(filename)[0]
                
                if metadata_mode == "movie" and movie_id:
                    clean_movie_name = limit_filename_length(sanitize_filename(movie_name))
                    target_filename = f"{clean_movie_name}{ext}"
                    os.rename(filepath, os.path.join(temp_dir, target_filename))
                    filepath = os.path.join(temp_dir, target_filename)
                    clean_base = clean_movie_name
                    
                    log_message(f"Generiere Film-NFO für {target_filename}...")
                    if provider == "ofdb":
                        mw_metadata.generate_ofdb_nfo(movie_id, temp_dir, clean_base)
                    else:
                        mw_metadata.generate_movie_nfo(movie_id, temp_dir, clean_base)
                        
                elif metadata_mode == "tv" and show_id:
                    ep_num = mapping.get(filename)
                    if not ep_num and len(downloaded_files) == 1:
                        ep_num = params.get("episode")
                        
                    if ep_num:
                        ep_title = ""
                        try:
                            if provider == "tvdb":
                                eps = mw_metadata.fetch_tvdb(show_id, season, "deu")
                            else:
                                lang = "en-US" if provider == "tmdb_tv_en" else "de-DE"
                                eps = mw_metadata.fetch_tmdb_tv(show_id, season, lang)
                            ep_data = eps.get(str(ep_num), {})
                            if isinstance(ep_data, dict):
                                ep_title = ep_data.get("title", "")
                            else:
                                ep_title = str(ep_data)
                        except Exception:
                            pass
                            
                        ep_title = sanitize_filename(ep_title)
                        season_str = f"S{int(season):02d}"
                        ep_str = f"E{int(ep_num):02d}"
                        
                        clean_show_title = f"{clean_show_name} - {season_str}{ep_str}"
                        if ep_title:
                            clean_show_title += f" - {ep_title}"
                        clean_show_title = limit_filename_length(clean_show_title)
                            
                        target_filename = f"{clean_show_title}{ext}"
                        os.rename(filepath, os.path.join(temp_dir, target_filename))
                        filepath = os.path.join(temp_dir, target_filename)
                        clean_base = clean_show_title
                        
                        log_message(f"Generiere Episoden-NFO für {ep_str} ({target_filename})...")
                        mw_metadata.generate_episode_nfo(provider, show_id, season, ep_num, temp_dir, clean_base)
                        
                else:
                    # YouTube Mode (Allgemein)
                    log_message(f"Generiere standardmäßige YouTube-NFO für {filename}...")
                    nfo_path = os.path.join(temp_dir, f"{clean_base}.nfo")
                    yt_title = params.get("yt_title", clean_base)
                    yt_uploader = params.get("yt_uploader", "YouTube")
                    yt_description = params.get("yt_description", "")
                    
                    xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                    xml += '<movie>\n  <lockdata>true</lockdata>\n'
                    xml += f"  <title>{yt_title.replace('&', '&amp;')}</title>\n"
                    xml += f"  <plot>{yt_description.replace('&', '&amp;').replace('<', '&lt;')}</plot>\n"
                    xml += f"  <studio>{yt_uploader.replace('&', '&amp;')}</studio>\n"
                    xml += '</movie>\n'
                    
                    try:
                        with open(nfo_path, "w", encoding="utf-8") as nf:
                            nf.write(xml)
                        log_message(f"  ✅ NFO erstellt: {clean_base}.nfo")
                    except Exception as e:
                        log_message(f"  ❌ Fehler bei NFO-Erstellung: {e}")
                        
                    # Download YouTube thumbnail as poster.jpg and fanart.jpg
                    yt_thumb_url = params.get("yt_thumbnail")
                    if yt_thumb_url:
                        log_message("🖼️ Lade YouTube-Thumbnail als Poster/Fanart herunter...")
                        try:
                            import urllib.request
                            req = urllib.request.Request(yt_thumb_url, headers={'User-Agent': 'Mozilla/5.0'})
                            with urllib.request.urlopen(req) as response:
                                thumb_data = response.read()
                            
                            for filename_artwork in ["poster.jpg", "fanart.jpg"]:
                                art_path = os.path.join(temp_dir, filename_artwork)
                                with open(art_path, "wb") as f_art:
                                    f_art.write(thumb_data)
                            log_message("  ✅ Poster und Fanart heruntergeladen.")
                        except Exception as e:
                            log_message(f"  ❌ Fehler beim Herunterladen des YouTube-Thumbnails: {e}")
                        
                # Determine local outbox equivalent
                if destination:
                    if destination.startswith(nas_root):
                        rel_dest = os.path.relpath(destination, nas_root)
                        outbox_dest = os.path.join(outbox_root, rel_dest)
                    else:
                        outbox_dest = os.path.join(outbox_root, os.path.basename(destination))
                else:
                    outbox_dest = outbox_root

                dest_dir_outbox = outbox_dest
                if metadata_mode == "tv" and show_id:
                    dest_dir_outbox = os.path.join(outbox_dest, clean_show_name, f"Staffel {int(season)}", clean_base)
                elif metadata_mode == "movie" and movie_id:
                    dest_dir_outbox = os.path.join(outbox_dest, clean_base)
                
                log_message(f"Verschiebe {target_filename} nach {dest_dir_outbox}...")
                transfer_successful = False
                try:
                    os.makedirs(dest_dir_outbox, exist_ok=True)
                    
                    # Move file
                    shutil.move(filepath, os.path.join(dest_dir_outbox, target_filename))
                    # Move accompanying files
                    for f in os.listdir(temp_dir):
                        if f.startswith(clean_base) and f != target_filename:
                            shutil.move(os.path.join(temp_dir, f), os.path.join(dest_dir_outbox, f))
                            
                    # Copy poster/fanart if they exist
                    for art_name in ["poster.jpg", "fanart.jpg"]:
                        art_src = os.path.join(temp_dir, art_name)
                        if os.path.exists(art_src):
                            shutil.copy(art_src, os.path.join(dest_dir_outbox, art_name))
                            suffix = "-poster.jpg" if art_name == "poster.jpg" else "-fanart.jpg"
                            shutil.copy(art_src, os.path.join(dest_dir_outbox, f"{clean_base}{suffix}"))
                            log_message(f"  ✅ Artwork kopiert: {art_name}")
                            
                    log_message(f"  ✅ Erfolgreich in Output-Ordner übertragen: {target_filename}")
                    transfer_successful = True
                    
                    # Open destination directory in Finder
                    subprocess.run(["open", dest_dir_outbox])
                except Exception as e:
                    log_message(f"  ❌ Fehler bei Übertragung in Output-Ordner: {e}")
                    all_transfers_successful = False

                # Copy to NAS if requested
                if copy_to_nas and destination and transfer_successful:
                    if not ensure_nas_mounted():
                        raise RuntimeError("NAS konnte nicht gemountet werden. Kopiervorgang abgebrochen.")
                    dest_dir_nas = destination
                    if metadata_mode == "tv" and show_id:
                        dest_dir_nas = os.path.join(destination, clean_show_name, f"Staffel {int(season)}", clean_base)
                    elif metadata_mode == "movie" and movie_id:
                        dest_dir_nas = os.path.join(destination, clean_base)
                        
                    log_message(f"Kopiere von Output auf NAS: {dest_dir_nas}...")
                    try:
                        os.makedirs(dest_dir_nas, exist_ok=True)
                        success = run_rsync_with_progress(os.path.join(dest_dir_outbox, target_filename), os.path.join(dest_dir_nas, target_filename), task_id)
                        if not success:
                            raise RuntimeError("Kopieren der Videodatei auf NAS fehlgeschlagen.")
                        for f in os.listdir(dest_dir_outbox):
                            if f.startswith(clean_base) and f != target_filename:
                                shutil.copy(os.path.join(dest_dir_outbox, f), os.path.join(dest_dir_nas, f))
                        for art_name in ["poster.jpg", "fanart.jpg"]:
                            art_src = os.path.join(dest_dir_outbox, art_name)
                            if os.path.exists(art_src):
                                shutil.copy(art_src, os.path.join(dest_dir_nas, art_name))
                                suffix = "-poster.jpg" if art_name == "poster.jpg" else "-fanart.jpg"
                                shutil.copy(art_src, os.path.join(dest_dir_nas, f"{clean_base}{suffix}"))
                        log_message(f"  ✅ Erfolgreich auf NAS kopiert.")
                        subprocess.run(["open", dest_dir_nas])
                    except Exception as e:
                        log_message(f"  ❌ Fehler bei NAS-Kopie: {e}")
                        all_transfers_successful = False
                        
            # Move show-level files in series mode to outbox
            dest_show_dir_outbox = None
            if metadata_mode == "tv" and show_id and destination:
                dest_show_dir_outbox = os.path.join(outbox_dest, clean_show_name)
                try:
                    os.makedirs(dest_show_dir_outbox, exist_ok=True)
                    for f in ["tvshow.nfo", "poster.jpg", "fanart.jpg"]:
                        p_src = os.path.join(temp_dir, f)
                        if os.path.exists(p_src):
                            shutil.move(p_src, os.path.join(dest_show_dir_outbox, f))
                            log_message(f"Serien-Metadatei verschoben: {f}")
                except Exception as e:
                    log_message(f"Fehler beim Verschieben der Serien-Metadaten in Output: {e}")
                    all_transfers_successful = False

            # Copy show-level files to NAS if requested
            if metadata_mode == "tv" and show_id and copy_to_nas and destination:
                dest_show_dir_nas = os.path.join(destination, clean_show_name)
                try:
                    os.makedirs(dest_show_dir_nas, exist_ok=True)
                    for f in ["tvshow.nfo", "poster.jpg", "fanart.jpg"]:
                        p_src = os.path.join(dest_show_dir_outbox, f) if dest_show_dir_outbox else os.path.join(temp_dir, f)
                        if os.path.exists(p_src):
                            shutil.copy(p_src, os.path.join(dest_show_dir_nas, f))
                            log_message(f"Serien-Metadatei auf NAS kopiert: {f}")
                except Exception as e:
                    log_message(f"Fehler beim Kopieren der Serien-Metadaten auf NAS: {e}")
                    all_transfers_successful = False
                    
            if params.get("copy_to_pcloud") and (destination or explicit_pcloud_base):
                dest_dir_outbox = outbox_dest
                if metadata_mode == "tv" and show_id:
                    dest_dir_outbox = os.path.join(outbox_dest, clean_show_name)
                elif metadata_mode == "movie" and movie_id:
                    dest_dir_outbox = os.path.join(outbox_dest, clean_base)
                pcloud_target = destination if destination else f"{nas_root}/Sonstiges"
                pcloud_success = copy_to_pcloud(dest_dir_outbox, pcloud_target, task_id=task_id, explicit_remote_base=explicit_pcloud_base)
                if not pcloud_success:
                    all_transfers_successful = False
                    
            # Clean up temp folder OR open it on failure
            if not copy_to_nas or transfer_successful:
                try:
                    shutil.rmtree(temp_dir)
                    log_message("Temporärer Ordner bereinigt.")
                except Exception:
                    pass
            else:
                log_message(f"⚠️  Übertragung fehlgeschlagen. Der temporäre Ordner '{temp_dir}' wurde NICHT gelöscht.")
                # Open temp folder in Finder so the user can access files manually
                subprocess.run(["open", temp_dir])
                
            with active_jobs_lock:
                if task_id in active_jobs:
                    if not all_transfers_successful:
                        active_jobs[task_id]["status"] = "error"
                        active_jobs[task_id]["message"] = "Übertragung unvollständig oder fehlgeschlagen"
                    else:
                        active_jobs[task_id]["status"] = "done"
                        active_jobs[task_id]["progress"] = 100
                        active_jobs[task_id]["message"] = "Erfolgreich beendet"
                    
        except Exception as e:
            log_message(f"❌ Fehler in YouTube-Pipeline: {e}")
            with active_jobs_lock:
                if task_id in active_jobs:
                    active_jobs[task_id]["status"] = "error"
                    active_jobs[task_id]["message"] = f"Fehler: {str(e)}"
        finally:
            with active_yt_tasks_lock:
                active_yt_tasks.pop(task_id, None)
            log_message("=== YOUTUBE PIPELINE BEENDET ===")

    elif media_type == "tool_pull_files":
        log_message(f"=== STARTE DATEIEN HOCHZIEHEN IN: {current_dir} ===")
        moved_count = 0
        for root, dirs, files in os.walk(current_dir):
            if root == current_dir:
                continue
            for f in files:
                src = os.path.join(root, f)
                dst = os.path.join(current_dir, f)
                if not os.path.exists(dst):
                    try:
                        shutil.move(src, dst)
                        log_message(f"Hochgezogen: {f}")
                        moved_count += 1
                    except Exception as e:
                        log_message(f"Fehler bei {f}: {e}")
                else:
                    log_message(f"Übersprungen (existiert bereits im Hauptordner): {f}")
        
        deleted_dirs = 0
        for root, dirs, files in os.walk(current_dir, topdown=False):
            if root == current_dir:
                continue
            if not os.listdir(root):
                try:
                    os.rmdir(root)
                    deleted_dirs += 1
                except Exception:
                    pass
        log_message(f"✅ {moved_count} Datei(en) hochgezogen. {deleted_dirs} leere(n) Ordner gelöscht.")

    elif media_type == "tool_batch_convert":
        log_message(f"=== STARTE BATCH H.265 KONVERTIERUNG IN: {current_dir} ===")
        video_files = [f for f in os.listdir(current_dir) if f.lower().endswith(('.mp4', '.mkv', '.avi', '.webm', '.mov')) and not f.startswith(".")]
        if not video_files:
            log_message("Keine Videodateien im Ordner gefunden.")
        else:
            for f in video_files:
                filepath = os.path.join(current_dir, f)
                is_hevc = False
                try:
                    probe_cmd = ["ffprobe", "-v", "quiet", "-show_entries", "stream=codec_name", "-select_streams", "v:0", "-of", "csv=p=0", filepath]
                    codec = subprocess.check_output(probe_cmd, text=True).strip()
                    if codec in ["hevc", "h265"]:
                        log_message(f"{f} ist bereits HEVC/H.265. Überspringe.")
                        is_hevc = True
                except Exception:
                    pass
                    
                if not is_hevc:
                    log_message(f"Konvertiere {f} nach H.265 (Qualität {quality})...")
                    base = os.path.splitext(f)[0]
                    temp_output = os.path.join(current_dir, f"{base}_neu.mkv")
                    ffmpeg_cmd = [
                        "caffeinate", "-i", "-s", "ffmpeg", "-nostdin", "-i", filepath,
                        "-c:v", "hevc_videotoolbox", "-tag:v", "hvc1", "-q:v", str(quality),
                        "-c:a", "copy", temp_output
                    ]
                    try:
                        success = run_ffmpeg_with_progress(ffmpeg_cmd, filepath, task_id=task_id, log_queue=log_queue)
                        if success and os.path.exists(temp_output) and os.path.getsize(temp_output) > 0:
                            log_message(f"Erfolgreich konvertiert: {f}")
                            try:
                                size_in = os.path.getsize(filepath)
                                size_out = os.path.getsize(temp_output)
                                if size_in > 0:
                                    ratio = size_out / size_in
                                    media.add_conversion_to_history(quality, "hevc", ratio)
                                    log_message(f"Konvertierungs-Verhältnis erfasst: {ratio:.4f}")
                            except Exception as e:
                                log_message(f"Fehler beim Erfassen des Konvertierungs-Verhältnisses: {e}")
                            os.remove(filepath)
                            os.rename(temp_output, os.path.join(current_dir, f"{base}.mkv"))
                        else:
                            log_message(f"❌ Fehler bei der Konvertierung von {f}.")
                            if os.path.exists(temp_output):
                                os.remove(temp_output)
                    except Exception as e:
                        log_message(f"Konvertierungsfehler bei {f}: {e}")
                        if os.path.exists(temp_output):
                            os.remove(temp_output)

    elif media_type == "tool_nfo_agent":
        log_message(f"=== STARTE NFO AGENT IN: {current_dir} ===")
        log_message("💡 Tipp: Nutze den Inbox-Workflow, suche den Film/Serie, und deaktiviere 'Konvertieren' und 'Auf das NAS verschieben'.")
        log_message("Dies generiert NFO und Bilder direkt im aktuellen Ordner, ohne Dateien zu verschieben.")
        
    elif media_type == "tool_nfo_batch_fsk":
        fsk_val = params.get("fsk", 16)
        log_message(f"=== STARTE NFO BATCH FSK-ANPASSUNG (FSK {fsk_val}) IN: {current_dir} ===")
        import re
        nfo_files = [f for f in os.listdir(current_dir) if f.lower().endswith(".nfo")]
        if not nfo_files:
            log_message("❌ Keine .nfo Dateien im Hauptordner gefunden.")
        else:
            for f in nfo_files:
                path = os.path.join(current_dir, f)
                try:
                    with open(path, "r", encoding="utf-8") as file:
                        content = file.read()
                    
                    if "<mpaa>" in content:
                        content = re.sub(r"<mpaa>.*?</mpaa>", f"<mpaa>FSK {fsk_val}</mpaa>", content)
                    else:
                        content = content.replace("</movie>", f"  <mpaa>FSK {fsk_val}</mpaa>\n</movie>")
                        content = content.replace("</tvshow>", f"  <mpaa>FSK {fsk_val}</mpaa>\n</tvshow>")
                        
                    with open(path, "w", encoding="utf-8") as file:
                        file.write(content)
                    log_message(f"✅ FSK {fsk_val} gesetzt in {f}")
                except Exception as e:
                    log_message(f"❌ Fehler bei {f}: {e}")
                    
    elif media_type == "tool_manual_sync":
        dest = params.get("destination", "/Volumes/Kino/Filme")
        do_pcloud = params.get("copy_to_pcloud", False)
        open_after = params.get("open_after", False)
        delete_original = params.get("delete_original", False)
        task_id = params.get("task_id")
        
        log_message(f"=== STARTE MANUELLES SYNC NACH: {dest} ===")
        if not ensure_nas_mounted():
            raise RuntimeError("NAS konnte nicht gemountet werden. Kopiervorgang abgebrochen.")
        
        folder_name = os.path.basename(current_dir.rstrip('/'))
        nas_target = os.path.join(dest, folder_name)
        
        log_message(f"Kopiere Ordner auf NAS: {nas_target}")
        nas_success = False
        try:
            nas_success = run_rsync_with_progress(current_dir, nas_target, task_id)
            if nas_success:
                log_message(f"✅ Erfolgreich auf NAS synchronisiert.")
                if open_after:
                    subprocess.run(["open", nas_target])
            else:
                log_message(f"❌ Fehler bei NAS Sync.")
        except Exception as e:
            log_message(f"❌ Ausnahme bei NAS Sync: {e}")
            
        pcloud_success = True
        if do_pcloud:
            pcloud_success = copy_to_pcloud(current_dir, dest, task_id)
            
        if delete_original and nas_success and pcloud_success:
            log_message(f"🗑️ Lösche Originalordner nach erfolgreichem Transfer: {current_dir}")
            try:
                shutil.rmtree(current_dir)
            except Exception as e:
                log_message(f"⚠️ Konnte Originalordner nicht löschen: {e}")

    elif media_type == "tool_pcloud_sync":
        dest = params.get("destination", "/Volumes/Kino/Filme")
        open_after = params.get("open_after", False)
        delete_original = params.get("delete_original", False)
        task_id = params.get("task_id")
        
        log_message(f"=== STARTE REINEN PCLOUD SYNC FÜR: {dest} ===")
        success = copy_to_pcloud(current_dir, dest, task_id)
        
        if success and delete_original:
            log_message(f"🗑️ Lösche Originalordner nach erfolgreichem Transfer: {current_dir}")
            try:
                shutil.rmtree(current_dir)
            except Exception as e:
                log_message(f"⚠️ Konnte Originalordner nicht löschen: {e}")
                
        if success and open_after:
            # We don't exactly know the local fuse path here easily without reproducing it, 
            # but we can try to open the source dir if it wasn't deleted.
            pass

    log_message("=== VORGANG BEENDET ===")

class GUIRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass # Suppress logs to keep terminal readable
        
    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        path = url.path
        query = urllib.parse.parse_qs(url.query)
        
        if path == "/api/status":
            self.handle_api_status()
        elif path == "/api/browse-folder":
            self.handle_api_browse_folder()
        elif path == "/api/scan-project":
            self.handle_api_scan_project(query)
        elif path == "/api/search":
            self.handle_api_search(query)
        elif path == "/api/fetch-show-info":
            self.handle_api_fetch_show_info(query)
        elif path == "/api/fetch-episodes":
            self.handle_api_fetch_episodes(query)
        elif path == "/api/yt/fetch":
            self.handle_api_yt_fetch(query)
        elif path == "/api/yt/segments":
            self.handle_api_yt_segments(query)
        elif path == "/api/queue":
            self.handle_api_queue()
        elif path == "/api/logs":
            self.handle_api_logs()
        elif path == "/api/settings":
            self.handle_api_get_settings()
        elif path == "/api/profile":
            self.handle_api_get_profile(query)
        elif path == "/api/check-dependencies":
            self.handle_api_check_dependencies(query)
        elif path == "/api/nas-series":
            self.handle_api_nas_series(query)
        elif path == "/api/series/detect":
            self.handle_api_series_detect(query)
        elif path == "/api/metadata/fetch":
            self.handle_api_metadata_fetch(query)
        elif path == "/api/system/open-folder":
            self.handle_api_system_open_folder(query)
        elif path == "/api/joke":
            self.handle_api_joke()
        elif path == "/api/youtube/subscriptions":
            self.handle_api_get_subscriptions()
        else:
            self.handle_static_files(path)
            
    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        path = url.path
        
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        params = {}
        if post_data:
            try:
                params = json.loads(post_data)
            except Exception:
                pass
                
        if path == "/api/streamfab-import":
            self.handle_api_streamfab_import()
        elif path == "/api/preview_clean":
            self.handle_api_preview_clean(params)
        elif path == "/api/paths/preview_clean":
            self.handle_api_paths_preview_clean(params)
        elif path == "/api/paths/clean":
            self.handle_api_paths_clean(params)
        elif path == "/api/clean-project":
            self.handle_api_clean_project(params)
        elif path == "/api/delete-project":
            self.handle_api_delete_project(params)
        elif path == "/api/split-project-file":
            self.handle_api_split_project_file(params)
        elif path == "/api/preview_process":
            self.handle_api_preview_process(params)
        elif path == "/api/nas-series":
            self.handle_api_nas_series(params)
        elif path == "/api/process":
            self.handle_api_process(params)
        elif path == "/api/yt/cut-done":
            self.handle_api_yt_cut_done(params)
        elif path == "/api/yt/finalize":
            self.handle_api_yt_finalize(params)
        elif path == "/api/settings":
            self.handle_api_post_settings(params)
        elif path == "/api/profile":
            self.handle_api_post_profile(params)
        elif path == "/api/system/restart":
            self.handle_api_system_restart()
        elif path == "/api/toggle-visibility":
            self.handle_api_toggle_visibility(params)
        elif path == "/api/guess-season":
            self.handle_api_guess_season(params)
        elif path == "/api/match-episodes":
            self.handle_api_match_episodes(params)
        elif path == "/api/estimate-conversion":
            self.handle_api_estimate_conversion(params)
        elif path == "/api/queue/clear":
            self.handle_api_queue_clear()
        elif path == "/api/youtube/subscriptions":
            self.handle_api_post_subscriptions(params)
        elif path == "/api/youtube/subscriptions/check":
            self.handle_api_check_subscriptions()
        else:
            self.send_error(404, "Not found")

    def handle_static_files(self, path):
        if path == "/":
            path = "/index.html"
        
        normalized_path = os.path.normpath(path).lstrip("/")
        file_path = os.path.join(os.path.dirname(__file__), "static", normalized_path)
        
        if not os.path.exists(file_path) or os.path.isdir(file_path):
            self.send_error(404, "File not found")
            return
            
        ext = os.path.splitext(file_path)[1].lower()
        mime_types = {
            ".html": "text/html",
            ".css": "text/css",
            ".js": "text/javascript",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".svg": "image/svg+xml",
            ".json": "application/json"
        }
        content_type = mime_types.get(ext, "application/octet-stream")
        
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Error: {e}")
    def handle_api_get_settings(self):
        settings = load_settings()
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(settings).encode())

    def handle_api_check_dependencies(self, query):
        force = query.get("force", ["false"])[0].lower() == "true"
        results = check_dependency_status(force_updates=force)
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(results).encode())

    def handle_api_post_settings(self, params):
        settings = load_settings()
        for k, v in params.items():
            settings[k] = v
        if save_settings(settings):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success"}).encode())
        else:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Failed to save settings"}).encode())

    def handle_api_get_profile(self, query):
        show_name = query.get("show_name", [""])[0]
        if not show_name:
            self.send_error(400, "show_name parameter is missing")
            return
        profile = utils.load_show_profile(show_name)
        self.send_json(profile)

    def handle_api_post_profile(self, params):
        show_name = params.get("show_name")
        profile_data = params.get("profile")
        if not show_name or not profile_data:
            self.send_error(400, "show_name or profile parameter is missing")
            return
        success = utils.save_show_profile(show_name, profile_data)
        self.send_json({"success": success})

    def handle_api_system_restart(self):
        # Check active background tasks
        active_count = 0
        with active_jobs_lock:
            for job in active_jobs.values():
                if job.get("status") not in ("done", "error"):
                    active_count += 1
                    
        if active_count > 0:
            self.send_json({
                "status": "busy",
                "message": "Der Server kann nicht neu gestartet werden, da aktuell noch Konvertierungen oder Dateiübertragungen laufen!"
            })
            return
            
        self.send_json({"status": "restarting"})
        
        # Schedule restart in a separate thread to allow response to send
        def do_restart():
            time.sleep(0.5)
            print("Restarting server process...")
            os.execv(sys.executable, [sys.executable] + sys.argv)
            
        threading.Thread(target=do_restart, daemon=True).start()

    def handle_api_guess_season(self, params):
        provider = params.get("provider")
        show_id = params.get("show_id")
        filenames = params.get("filenames", [])
        
        if not provider or not show_id:
            self.send_error(400, "provider or show_id is missing")
            return
            
        try:
            season = mw_metadata.guess_season(provider, show_id, filenames)
            self.send_json({"season": season})
        except Exception as e:
            print(f"Error guessing season: {e}")
            self.send_json({"season": None})

    def handle_api_match_episodes(self, params):
        provider = params.get("provider")
        show_id = params.get("show_id")
        season = params.get("season")
        filenames = params.get("filenames", [])
        
        if not provider or not show_id or not season:
            self.send_error(400, "provider, show_id or season is missing")
            return
            
        episodes = {}
        try:
            if provider == "tvdb":
                episodes = mw_metadata.fetch_tvdb(show_id, season, "deu")
            elif provider in ["tmdb_tv", "tmdb_tv_en"]:
                lang = "en-US" if provider == "tmdb_tv_en" else "de-DE"
                episodes = mw_metadata.fetch_tmdb_tv(show_id, season, lang)
            elif provider == "tvmaze":
                episodes = mw_metadata.fetch_tvmaze(show_id, season)
            elif provider == "mediathek":
                episodes = mw_metadata.fetch_mediathek_episodes(show_id)
            elif provider == "ytdlp":
                entries = mw_metadata.fetch_ytdlp_url_metadata(show_id)
                episodes = {}
                if not isinstance(entries, dict):
                    for idx, ent in enumerate(entries):
                        ep_idx = ent.get("playlist_index") or ent.get("playlist_autonumber") or (idx + 1)
                        episodes[str(ep_idx)] = {"title": ent.get("title", ""), "plot": ent.get("description", "")}
        except Exception as e:
            print(f"Error fetching episodes for matching: {e}")
            
        matches = {}
        import re
        def guess_ep_num(filename):
            clean_name = filename.lower()
            # 1. Parentheses/brackets check for absolute episode numbers first! E.g. (381) or [381]
            match = re.search(r'(?:\(|\[)(?:folge\s+)?(\d+)(?:\)|\])', clean_name)
            if match:
                return int(match.group(1))
                
            # s01e05
            match = re.search(r's\d+e(\d+)', clean_name)
            if match:
                return int(match.group(1))
            # 1x05
            match = re.search(r'\d+x(\d+)', clean_name)
            if match:
                return int(match.group(1))
            # ep 05 / episode 05
            match = re.search(r'ep(?:isode)?[.\s-]?(\d+)', clean_name)
            if match:
                return int(match.group(1))
            # isolated digits (excluding year range 1900-2100)
            without_ext = os.path.splitext(filename)[0]
            digit_matches = re.findall(r'\b\d+\b', without_ext)
            if digit_matches:
                for digit_str in digit_matches:
                    val = int(digit_str)
                    if 0 < val < 2000:
                        if 1950 <= val <= 2050:
                            continue
                        return val
            return None
            
        def get_words(text):
            words = set(re.findall(r'\w+', text.lower()))
            return {w for w in words if w not in ['der', 'die', 'das', 'in', 'im', 'teil', 'part', 'von', 'und', 'folge', 'episode']}
            
        for file in filenames:
            basename = os.path.basename(file)
            # 1. Hard match based on filename patterns
            ep_num = guess_ep_num(basename)
            if ep_num is not None:
                # Direct check (e.g. if key is "381" or "39")
                if str(ep_num) in episodes:
                    matches[file] = str(ep_num)
                    continue
                    
                # Absolute number check (e.g. if keys are S01E01 style or year-based S2010E39 style, but contain absolute_number = 381)
                found_key = None
                for key, ep_data in episodes.items():
                    if isinstance(ep_data, dict) and ep_data.get("absolute_number") is not None:
                        try:
                            if int(ep_data.get("absolute_number")) == int(ep_num):
                                found_key = key
                                break
                        except (ValueError, TypeError):
                            pass
                if found_key:
                    matches[file] = found_key
                    continue
                    
                # Check if it matches the episode number suffix in key (e.g., ep_num=39, key="S2010E39")
                found_key = None
                for key in episodes.keys():
                    match = re.match(r"^s\d+e(\d+)$", str(key), re.IGNORECASE)
                    if match:
                        if int(match.group(1)) == int(ep_num):
                            found_key = key
                            break
                if found_key:
                    matches[file] = found_key
                    continue
                
            # 2. Fuzzy match based on text overlap with episode titles
            file_words = get_words(basename)
            if not file_words:
                matches[file] = None
                continue
                
            best_ep_num = None
            best_score = 0.0
            for ep_n, ep_data in episodes.items():
                title = ep_data.get('title', '') if isinstance(ep_data, dict) else str(ep_data)
                title_words = get_words(title)
                if not title_words:
                    continue
                overlap = len(title_words.intersection(file_words))
                score = overlap / len(title_words)
                if score > best_score:
                    best_score = score
                    best_ep_num = ep_n
                    
            if best_score > 0.35:
                matches[file] = best_ep_num
            else:
                matches[file] = None
                
        # Duplicate detection logic
        duplicates = {}
        nas_destination_id = params.get("nas_destination_id")
        nas_show_folder = params.get("nas_show_folder")
        show_name = params.get("show_name")
        
        settings = load_settings()
        nas_root = settings.get("nas_root", "/Volumes/Kino")
        
        show_dir = None
        if show_name or nas_show_folder:
            destination = None
            if nas_destination_id:
                sync_cats = settings.get("sync_categories", [])
                found_cat = None
                for cat in sync_cats:
                    if cat.get("id") == str(nas_destination_id):
                        found_cat = cat
                        break
                if found_cat:
                    destination = os.path.join(nas_root, found_cat.get("nas_sub", "").lstrip("/"))
            if not destination:
                destination = os.path.join(nas_root, "Serien")
                
            clean_show_name = clean_series_name_for_fs(nas_show_folder or show_name)
            if clean_show_name:
                show_dir = os.path.join(destination, clean_show_name)
                
        def check_duplicate(ep_season, ep_num):
            if not show_dir or not os.path.exists(show_dir) or ep_season is None or ep_num is None:
                return None
            pats = [
                f"s{ep_season:02d}e{ep_num:02d}",
                f"s{ep_season:02d}e{ep_num:03d}",
                f"s{ep_season}e{ep_num:02d}",
                f"s{ep_season:02d}e{ep_num}",
            ]
            for root, _, files in os.walk(show_dir):
                for f in files:
                    if f.startswith('.'):
                        continue
                    fl = f.lower()
                    matched = False
                    for pat in pats:
                        if pat in fl:
                            matched = True
                            break
                    if not matched and ep_season == 1:
                        pat_iso_1 = f" - {ep_num:02d} "
                        pat_iso_2 = f" - {ep_num:02d}."
                        pat_iso_3 = f" - {ep_num:03d} "
                        pat_iso_4 = f" - {ep_num:03d}."
                        if pat_iso_1 in fl or pat_iso_2 in fl or pat_iso_3 in fl or pat_iso_4 in fl:
                            matched = True
                    if matched:
                        details = {"filename": f}
                        filepath = os.path.join(root, f)
                        try:
                            size_bytes = os.path.getsize(filepath)
                            details["size_gb"] = size_bytes / (1024 * 1024 * 1024)
                            cmd = [
                                "ffprobe", "-v", "error", "-select_streams", "v:0",
                                "-show_entries", "stream=width,height", "-of", "csv=p=0",
                                filepath
                            ]
                            res = subprocess.run(cmd, capture_output=True, text=True, timeout=2.0)
                            if res.returncode == 0:
                                dimensions = res.stdout.strip().split(',')
                                if len(dimensions) == 2:
                                    details["resolution"] = f"{dimensions[0]}x{dimensions[1]}"
                        except Exception:
                            pass
                        return details
            return None

        for file in filenames:
            matched_ep = matches.get(file)
            if matched_ep:
                import re
                match = re.match(r"^S(\d+)E(\d+)$", str(matched_ep), re.IGNORECASE)
                if match:
                    ep_season = int(match.group(1))
                    ep_num = int(match.group(2))
                else:
                    try:
                        ep_num = int(matched_ep)
                        ep_season = int(season)
                    except (ValueError, TypeError):
                        ep_num = None
                        ep_season = None
                
                dup_details = check_duplicate(ep_season, ep_num)
                if dup_details:
                    duplicates[file] = dup_details
                    
        self.send_json({"matches": matches, "duplicates": duplicates})

    def handle_api_estimate_conversion(self, params):
        project_name = params.get("project_name", "")
        filenames = params.get("filenames", [])
        quality = params.get("quality", 60)
        
        settings = load_settings()
        inbox_root = settings.get("inbox_dir", os.path.expanduser("~/Downloads/Medien Input"))
        
        if project_name:
            target_dir = os.path.join(inbox_root, project_name)
        else:
            target_dir = inbox_root
            
        estimates = {}
        first_successful_ratio = None
        for f in filenames:
            filepath = os.path.join(target_dir, f)
            if os.path.exists(filepath):
                try:
                    size_in = os.path.getsize(filepath)
                    if first_successful_ratio is not None:
                        ratio = first_successful_ratio
                    else:
                        ratio = media.konvertierung_schaetzen(filepath, quality)
                        first_successful_ratio = ratio
                    
                    estimated_size = int(size_in * ratio)
                    estimates[f] = {
                        "ratio": ratio,
                        "size_in": size_in,
                        "size_out": estimated_size
                    }
                except Exception as e:
                    print(f"Error estimating size for {f}: {e}")
                    estimates[f] = {"error": str(e)}
            else:
                estimates[f] = {"error": "File not found"}
                
        self.send_json({"estimates": estimates})

    def handle_api_toggle_visibility(self, params):
        target_path = params.get("path")
        hide = params.get("hide", True)
        if not target_path or not os.path.exists(target_path):
            self.send_error(400, "Invalid path")
            return
            
        try:
            flag = "hidden" if hide else "nohidden"
            subprocess.run(["chflags", flag, target_path], check=True)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success"}).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def handle_api_status(self):
        inbox = os.path.expanduser("~/Downloads/Medien Input")
        outbox = os.path.expanduser("~/Downloads/Medien Output")
        os.makedirs(inbox, exist_ok=True)
        os.makedirs(outbox, exist_ok=True)
        
        projects = []
        for d in os.listdir(inbox):
            if os.path.isdir(os.path.join(inbox, d)) and not d.startswith("."):
                projects.append(d)
                
        status = {
            "nas_status": check_nas_status(),
            "inbox_path": inbox,
            "outbox_path": outbox,
            "streamfab_downloads": check_streamfab(),
            "projects": sorted(projects)
        }
        
        self.send_json(status)

    def handle_api_streamfab_import(self):
        count = import_streamfab_files()
        self.send_json({"status": "ok", "moved_count": count})

    def handle_api_browse_folder(self):
        script = '''
        tell application "System Events"
            activate
            try
                set f to choose folder with prompt "Wähle einen Zielordner für die Werkzeuge:"
                POSIX path of f
            on error
                return ""
            end try
        end tell
        '''
        try:
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            folder_path = result.stdout.strip()
            self.send_json({"status": "ok", "path": folder_path})
        except Exception as e:
            self.send_json({"status": "error", "message": str(e)})

    def handle_api_scan_project(self, query):
        project = query.get("project", [""])[0]
        inbox_root = os.path.expanduser("~/Downloads/Medien Input")
        if project:
            target_dir = os.path.join(inbox_root, project)
        else:
            target_dir = inbox_root
            
        if not os.path.exists(target_dir):
            self.send_error(404, "Directory not found")
            return
            
        file_list = []
        ext_counts = {}
        
        # Scannen des Verzeichnisses (rekursiv, damit auch Dateien in Unterordnern gefunden werden)
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
        
        self.send_json({
            "current_dir": target_dir,
            "files": file_list,
            "video_count": video_count,
            "ext_counts": ext_counts,
            "is_doku": is_doku
        })

    def handle_api_preview_clean(self, params):
        project = params.get("project", "")
        inbox_root = os.path.expanduser("~/Downloads/Medien Input")
        if project:
            target_dir = os.path.join(inbox_root, project)
        else:
            target_dir = inbox_root
            
        if not os.path.exists(target_dir):
            self.send_json({"error": "Verzeichnis nicht gefunden"})
            return
            
        all_files = find_files_recursively(target_dir)
        groups = {}
        for f in all_files:
            ext = os.path.splitext(f)[1].lower()
            if not ext:
                ext = "ohne_endung"
            if ext not in groups:
                groups[ext] = []
            groups[ext].append(f)
            
        self.send_json({"groups": groups})

    def handle_api_paths_preview_clean(self, params):
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
                    
            self.send_json({
                "inbox_files": inbox_files,
                "output_files": output_files
            })
        except Exception as e:
            self.send_json({"error": f"Fehler beim Scannen der Medienpfade: {e}"})

    def handle_api_paths_clean(self, params):
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
                    if os.path.exists(path_f):
                        try:
                            os.remove(path_f)
                            deleted_files.append(f"inbox/{f}")
                        except Exception as e:
                            print(f"Error removing {path_f}: {e}")
                            
            # Lösche Dateien aus Output
            if outbox_dir and os.path.exists(outbox_dir):
                for f in output_files:
                    path_f = os.path.join(outbox_dir, f)
                    if os.path.exists(path_f):
                        try:
                            os.remove(path_f)
                            deleted_files.append(f"output/{f}")
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
                                os.rmdir(dir_path)
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
                
            self.send_json({
                "status": "ok",
                "deleted_files": deleted_files,
                "deleted_dirs": deleted_dirs
            })
        except Exception as e:
            self.send_json({"error": f"Fehler beim Bereinigen der Medienpfade: {e}"})

    def handle_api_clean_project(self, params):
        project = params.get("project", "")
        inbox_root = os.path.expanduser("~/Downloads/Medien Input")
        if project:
            target_dir = os.path.join(inbox_root, project)
        else:
            target_dir = inbox_root
            
        deleted_files = []
        deleted_dirs = []
        
        explicit_files = params.get("explicit_files")
        
        if explicit_files is not None:
            # Neuer interaktiver Modus: Lösche nur, was der Benutzer ausgewählt hat
            for f in explicit_files:
                path_f = os.path.join(target_dir, f)
                if os.path.exists(path_f):
                    try:
                        os.remove(path_f)
                        deleted_files.append(f)
                    except Exception:
                        pass
                        
            # Leere Ordner aufräumen
            for root, dirs, files in os.walk(target_dir, topdown=False):
                if root == target_dir: continue
                if not os.listdir(root):
                    try:
                        os.rmdir(root)
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
                            os.remove(path_f)
                            deleted_files.append(os.path.relpath(path_f, target_dir))
                        except Exception:
                            pass
                for d in dirs:
                    path_d = os.path.join(root, d)
                    if not os.listdir(path_d):
                        try:
                            os.rmdir(path_d)
                            deleted_dirs.append(os.path.relpath(path_d, target_dir))
                        except Exception:
                            pass
                            
        self.send_json({
            "status": "ok",
            "deleted_files": deleted_files,
            "deleted_dirs": deleted_dirs
        })

    def handle_api_delete_project(self, params):
        project = params.get("project")
        if not project:
            self.send_json({"status": "error", "error": "Kein Ordnername angegeben."})
            return
            
        settings = load_settings()
        inbox_root = settings.get("inbox_dir", os.path.expanduser("~/Downloads/Medien Input"))
        
        target_dir = os.path.join(inbox_root, project)
        inbox_root_abs = os.path.abspath(inbox_root)
        target_dir_abs = os.path.abspath(target_dir)
        
        # Security check: Ensure target is inside inbox_root and not the root itself
        if not target_dir_abs.startswith(inbox_root_abs + os.sep) or target_dir_abs == inbox_root_abs:
            self.send_json({"status": "error", "error": "Ungültiger oder unzulässiger Pfad."})
            return
            
        if not os.path.exists(target_dir_abs):
            self.send_json({"status": "error", "error": "Ordner existiert nicht."})
            return
            
        try:
            import shutil
            shutil.rmtree(target_dir_abs)
            log_message(f"🗑️ Ordner erfolgreich gelöscht: {project}")
            self.send_json({"status": "success"})
        except Exception as e:
            log_message(f"❌ Fehler beim Löschen des Ordners {project}: {e}")
            self.send_json({"status": "error", "error": str(e)})

    def handle_api_split_project_file(self, params):
        project = params.get("project", "")
        file_name = params.get("file_name")
        if not file_name:
            self.send_json({"status": "error", "error": "Kein Dateiname angegeben."})
            return
            
        settings = load_settings()
        inbox_root = settings.get("inbox_dir", os.path.expanduser("~/Downloads/Medien Input"))
        
        inbox_root_abs = os.path.abspath(inbox_root)
        
        if project:
            source_dir = os.path.join(inbox_root, project)
        else:
            source_dir = inbox_root
            
        source_dir_abs = os.path.abspath(source_dir)
        
        # Security check: Ensure source_dir is inside inbox_root
        if not source_dir_abs.startswith(inbox_root_abs):
            self.send_json({"status": "error", "error": "Ungültiger oder unzulässiger Quell-Pfad."})
            return
            
        # Security check: Prevent path traversal in file_name
        safe_file_name = os.path.basename(file_name)
        if safe_file_name != file_name:
            self.send_json({"status": "error", "error": "Ungültiger Dateiname."})
            return
            
        source_file_path = os.path.join(source_dir_abs, safe_file_name)
        if not os.path.exists(source_file_path):
            self.send_json({"status": "error", "error": f"Datei {safe_file_name} existiert nicht im Projekt."})
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
                self.send_json({"status": "error", "error": "Keine Dateien zum Verschieben gefunden."})
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
                        shutil.rmtree(source_dir_abs)
                        log_message(f"🗑️ Quellordner gelöscht, da leer: {project}")
                    except Exception as e:
                        log_message(f"⚠️ Fehler beim Löschen des leeren Quellordners {project}: {e}")
                        
            self.send_json({
                "status": "success",
                "new_project": new_project_name
            })
        except Exception as e:
            log_message(f"❌ Fehler bei handle_api_split_project_file: {e}")
            self.send_json({"status": "error", "error": str(e)})

    def handle_api_search(self, query):
        q = query.get("q", [""])[0].strip()
        media_type = query.get("type", ["tv"])[0]
        
        results = []
        try:
            if q.startswith("http://") or q.startswith("https://"):
                if "fernsehserien.de" in q:
                    slug = q.rstrip("/").split("/")[-1]
                    results = [{
                        "id": q,
                        "name": f"{slug.replace('-', ' ').title()} (fernsehserien.de URL)",
                        "provider": "fernsehserien",
                        "media_type": "tv"
                    }]
                else:
                    entries = mw_metadata.fetch_ytdlp_url_metadata(q)
                    if entries:
                        if len(entries) > 1:
                            show_name = entries[0].get("playlist_title") or entries[0].get("playlist") or "YouTube/Mediathek Playlist"
                            results = [{
                                "id": q,
                                "name": f"{show_name} ({len(entries)} Videos via URL)",
                                "provider": "ytdlp",
                                "media_type": "tv"
                            }]
                        else:
                            title = entries[0].get("title") or "Video via URL"
                            # Determine media type based on search request and metadata
                            has_series_info = any(entries[0].get(k) for k in ["series", "season_number", "episode_number", "season", "episode"])
                            if media_type in ("tv", "doku") or has_series_info:
                                res_type = media_type if media_type in ("tv", "doku") else "tv"
                            else:
                                res_type = "movie"
                            results = [{
                                "id": q,
                                "name": f"{title} (Video via URL)",
                                "provider": "ytdlp",
                                "media_type": res_type
                            }]
                    else:
                        # Fallback for Mediathek/other URLs that yt-dlp fails to extract directly
                        import urllib.request
                        import re
                        req = urllib.request.Request(q, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"})
                        try:
                            with urllib.request.urlopen(req, timeout=5) as response:
                                html = response.read().decode('utf-8', errors='ignore')
                            title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE)
                            if title_match:
                                title = title_match.group(1).strip()
                                title = re.sub(r"^Vorschau:\s*", "", title, flags=re.IGNORECASE)
                                title = title.split("|")[0].split(" - ARD")[0].split(" - ZDF")[0].strip()
                                
                                search_term = title
                                if "•" in title:
                                    search_term = title.split("•")[0].strip()
                                elif " - " in title:
                                    search_term = title.split(" - ")[0].strip()
                                
                                res_type = media_type if media_type in ("tv", "doku") else "movie"
                                name_suffix = "Serie aus URL" if res_type != "movie" else "Film aus URL"
                                results = [{
                                    "id": f"url_mediathek:{search_term}",
                                    "name": f"{search_term} (Mediathek {name_suffix})",
                                    "provider": "mediathek",
                                    "media_type": res_type
                                }]
                        except Exception as e:
                            print(f"Error scraping fallback URL {q}: {e}")
            elif media_type == "tv":
                results = mw_metadata.search_all_db(q)
                for r in results:
                    r["media_type"] = "tv"
                # Add free-search option for Mediathek
                results.append({
                    "id": f"url_mediathek:{q}",
                    "name": f"{q} (Freie Mediathek-Suche)",
                    "provider": "mediathek",
                    "media_type": "tv"
                })
            elif media_type == "movie":
                tmdb_res = mw_metadata.search_tmdb_movie(q)
                for r in tmdb_res:
                    r['provider'] = 'tmdb'
                    r["media_type"] = "movie"
                results.extend(tmdb_res)
                
                ofdb_res = mw_metadata.search_ofdb(q)
                for r in ofdb_res:
                    results.append({
                        "id": r["id"],
                        "name": f"{r['title']} ({r['year']})",
                        "provider": "ofdb",
                        "media_type": "movie"
                    })
                results.sort(key=lambda r: mw_metadata.calculate_match_score(q, r['name']), reverse=True)
            elif media_type == "doku":
                # Parallel-ish search for Dokus (TV, Movies, Mediathek)
                # 1. TV Series
                tv_res = mw_metadata.search_all_db(q)
                for r in tv_res:
                    r["media_type"] = "tv"
                results.extend(tv_res)
                
                # 2. Movie search
                tmdb_res = mw_metadata.search_tmdb_movie(q)
                for r in tmdb_res:
                    r['provider'] = 'tmdb'
                    r["media_type"] = "movie"
                results.extend(tmdb_res)
                
                # 3. Mediathek search
                mediathek_res = mw_metadata.search_mediathek(q)
                for r in mediathek_res:
                    r["media_type"] = "tv"
                    r["provider"] = "mediathek"
                results.extend(mediathek_res)
                
                # Sort combined results
                results.sort(key=lambda r: mw_metadata.calculate_match_score(q, r['name']), reverse=True)
        except Exception as e:
            print(f"Search error: {e}")
            
        self.send_json(results)

    def handle_api_fetch_show_info(self, query):
        provider = query.get("provider", ["tmdb_tv"])[0]
        show_id = query.get("show_id", [""])[0]
        
        info = "Keine Info gefunden"
        try:
            info = mw_metadata.get_show_info(provider, show_id)
        except Exception as e:
            info = f"Fehler: {e}"
            
        self.send_json({"info": info})

    def handle_api_fetch_episodes(self):
        pass # Implemented below in actual request handling

    def handle_api_fetch_episodes(self, query):
        provider = query.get("provider", ["tmdb_tv"])[0]
        show_id = query.get("show_id", [""])[0]
        season = query.get("season", ["1"])[0]
        
        episodes = {}
        try:
            if provider == "tvdb":
                episodes = mw_metadata.fetch_tvdb(show_id, season, "deu")
            elif provider in ["tmdb_tv", "tmdb_tv_en"]:
                lang = "en-US" if provider == "tmdb_tv_en" else "de-DE"
                episodes = mw_metadata.fetch_tmdb_tv(show_id, season, lang)
            elif provider == "tvmaze":
                episodes = mw_metadata.fetch_tvmaze(show_id, season)
            elif provider == "mediathek":
                episodes = mw_metadata.fetch_mediathek_episodes(show_id)
            elif provider == "ytdlp":
                entries = mw_metadata.fetch_ytdlp_url_metadata(show_id)
                if not isinstance(entries, dict):
                    for idx, ent in enumerate(entries):
                        ep_idx = ent.get("playlist_index") or ent.get("playlist_autonumber") or (idx + 1)
                        title = ent.get("title", "")
                        alt_title = ent.get("alt_title", "")
                        show_name = ent.get("playlist_title") or ent.get("playlist", "")
                        ep_title = title
                        if alt_title and mw_metadata.normalize_title(title) == mw_metadata.normalize_title(show_name):
                            ep_title = alt_title
                        elif alt_title and not title:
                            ep_title = alt_title
                        episodes[str(ep_idx)] = {"title": ep_title, "plot": ent.get("description", ""), "date": ent.get("upload_date", "")}
            elif provider == "fernsehserien":
                episodes = mw_metadata.get_fernsehserien_episodes(show_id, season)
        except Exception as e:
            print(f"Error fetching episodes: {e}")
            
        self.send_json(episodes)

    def handle_api_preview_process(self, params):
        media_type = params.get("media_type")
        project_name = params.get("project_name", "")
        show_id = params.get("show_id")
        movie_id = params.get("movie_id")
        provider = params.get("provider")
        season = params.get("season")
        mappings = params.get("mappings", {})
        destination = params.get("destination")
        nas_destination_id = params.get("nas_destination_id") or params.get("destination_id")
        pcloud_destination_id = params.get("pcloud_destination_id") or params.get("destination_id")
        
        settings = load_settings()
        inbox_root = settings.get("inbox_dir", os.path.expanduser("~/Downloads/Medien Input"))
        outbox_root = settings.get("outbox_dir", os.path.expanduser("~/Downloads/Medien Output"))
        nas_root = settings.get("nas_root", "/Volumes/Kino")
        
        destination = params.get("destination")
        # Resolve NAS destination path
        if nas_destination_id:
            sync_cats = settings.get("sync_categories", [])
            found_cat = None
            for cat in sync_cats:
                if cat.get("id") == str(nas_destination_id):
                    found_cat = cat
                    break
            if not found_cat:
                for cat in sync_cats:
                    nas_sub = cat.get("nas_sub", "")
                    if nas_sub and (nas_sub in str(nas_destination_id)):
                        found_cat = cat
                        break
            if found_cat:
                destination = f"{nas_root}{found_cat.get('nas_sub')}"

        # Resolve pCloud destination remote base
        explicit_pcloud_base = None
        if pcloud_destination_id:
            sync_cats = settings.get("sync_categories", [])
            found_cat = None
            for cat in sync_cats:
                if cat.get("id") == str(pcloud_destination_id):
                    found_cat = cat
                    break
            if not found_cat:
                for cat in sync_cats:
                    nas_sub = cat.get("nas_sub", "")
                    if nas_sub and (nas_sub in str(pcloud_destination_id)):
                        found_cat = cat
                        break
            if found_cat:
                explicit_pcloud_base = found_cat.get('pcloud_remote')
        
        if project_name:
            current_dir = os.path.join(inbox_root, project_name)
        else:
            current_dir = inbox_root
            
        if not os.path.exists(current_dir):
            self.send_json({"error": "Ordner existiert nicht."})
            return
            
        all_files = find_files_recursively(current_dir)
        video_exts = ('.mp4', '.mkv', '.avi', '.webm', '.mov', '.ts', '.m2ts', '.flv', '.3gp', '.wmv')
        sub_exts = ('.srt', '.vtt', '.ass')
        good_meta = ('tvshow.nfo', 'poster.jpg', 'fanart.jpg', 'season.nfo', 'movie.nfo')
        
        preview = {
            "renames": [],
            "subs": [],
            "junk": [],
            "destination": ""
        }
        
        if media_type == "movie":
            movie_name = params.get("movie_name", "Unbekannter Film")
            dest_movies = destination if destination else f"{nas_root}/Filme"
            clean_movie_name = limit_filename_length(sanitize_filename(movie_name))
            
            nas_path = os.path.join(dest_movies, clean_movie_name)
            pcloud_path = f"{explicit_pcloud_base}/{clean_movie_name}" if explicit_pcloud_base else None
            
            if params.get("copy_to_nas", True):
                dest_str = f"NAS: {nas_path}"
            else:
                dest_str = "NAS: (nicht aktiv)"
                
            if params.get("copy_to_pcloud", False):
                if pcloud_path:
                    dest_str += f"\n☁️ pCloud: {pcloud_path}"
                else:
                    dest_str += "\n☁️ pCloud: (Kein Mapping gefunden)"
            else:
                dest_str += "\n☁️ pCloud: (nicht aktiv)"
            preview["destination"] = dest_str
            
            for f in all_files:
                basename = os.path.basename(f)
                ext = os.path.splitext(f)[1].lower()
                if ext in video_exts:
                    target_filename = f"{clean_movie_name}{ext}"
                    preview["renames"].append({"old": f, "new": target_filename})
                elif ext in sub_exts:
                    target_filename = f"{clean_movie_name}{ext}"
                    preview["subs"].append({"old": f, "new": target_filename})
                elif basename.lower() in ['poster.jpg', 'fanart.jpg', 'tvshow.nfo', 'season.nfo']:
                    preview["subs"].append({"old": f, "new": basename})
                elif ext == '.nfo':
                    preview["subs"].append({"old": f, "new": f"{clean_movie_name}.nfo"})
                elif ext in ('.jpg', '.png') and 'poster' in basename.lower():
                    preview["subs"].append({"old": f, "new": f"{clean_movie_name}-poster{ext}"})
                elif ext in ('.jpg', '.png') and 'fanart' in basename.lower():
                    preview["subs"].append({"old": f, "new": f"{clean_movie_name}-fanart{ext}"})
                else:
                    preview["junk"].append(f)
                    
        elif media_type == "tv":
            show_name = clean_series_name_for_fs(params.get("show_name", "Unknown Show"))
            nas_show_folder = params.get("nas_show_folder")
            if nas_show_folder:
                clean_show_name = clean_series_name_for_fs(nas_show_folder)
            else:
                nas_serien = destination if destination else f"{nas_root}/Serien"
                rel_dest = os.path.relpath(nas_serien, nas_root)
                outbox_serien = os.path.join(outbox_root, rel_dest)
                clean_show_name = get_matched_series_name(nas_serien, outbox_serien, limit_filename_length(sanitize_filename(show_name)))
                
            nas_serien = destination if destination else f"{nas_root}/Serien"
            dest_show_dir = os.path.join(nas_serien, clean_show_name)
            
            pcloud_path = f"{explicit_pcloud_base}/{clean_show_name}" if explicit_pcloud_base else None
            
            episodes = {}
            if provider and show_id:
                try:
                    if provider == "tvdb":
                        episodes = mw_metadata.fetch_tvdb(show_id, season, "deu")
                    elif provider in ["tmdb_tv", "tmdb_tv_en"]:
                        lang = "en-US" if provider == "tmdb_tv_en" else "de-DE"
                        episodes = mw_metadata.fetch_tmdb_tv(show_id, season, lang)
                    elif provider == "tvmaze":
                        episodes = mw_metadata.fetch_tvmaze(show_id, season)
                    elif provider == "mediathek":
                        episodes = mw_metadata.fetch_mediathek_episodes(show_id)
                    elif provider == "ytdlp":
                        entries = mw_metadata.fetch_ytdlp_url_metadata(show_id)
                        episodes = {}
                        if not isinstance(entries, dict):
                            for idx, ent in enumerate(entries):
                                ep_idx = ent.get("playlist_index") or ent.get("playlist_autonumber") or (idx + 1)
                                title = ent.get("title", "")
                                alt_title = ent.get("alt_title", "")
                                show_name_yt = ent.get("playlist_title") or ent.get("playlist", "")
                                ep_title = title
                                if alt_title and mw_metadata.normalize_title(title) == mw_metadata.normalize_title(show_name_yt):
                                    ep_title = alt_title
                                elif alt_title and not title:
                                    ep_title = alt_title
                                episodes[str(ep_idx)] = {"title": ep_title, "plot": ent.get("description", "")}
                except Exception as e:
                    print(f"Error fetching preview episodes: {e}")
            
            clean_titles = []
            for f in all_files:
                basename = os.path.basename(f)
                ext = os.path.splitext(f)[1].lower()
                
                if ext in video_exts:
                    rel_f = os.path.relpath(f, current_dir)
                    ep_num = mappings.get(rel_f) or mappings.get(f) or mappings.get(basename)
                    if ep_num:
                        if isinstance(ep_num, dict):
                            curr_season = ep_num.get("season", season)
                            curr_ep_num = ep_num.get("episode", 1)
                            ep_title = ep_num.get("title", "")
                        else:
                            ep_data = episodes.get(str(ep_num), {})
                            if not ep_data and provider == "ytdlp" and len(episodes) == 1:
                                ep_data = list(episodes.values())[0]
                            ep_title = ep_data.get("title", "") if isinstance(ep_data, dict) else str(ep_data)
                            
                            import re
                            match = re.match(r"^S(\d+)E(\d+)$", str(ep_num), re.IGNORECASE)
                            if match:
                                curr_season = int(match.group(1))
                                curr_ep_num = int(match.group(2))
                            else:
                                curr_season = season
                                curr_ep_num = ep_num
                        
                        force_abs = params.get("force_absolute_season_1", False)
                        if force_abs:
                            if isinstance(ep_num, dict):
                                ep_data = ep_num
                            else:
                                ep_data = episodes.get(str(ep_num), {})
                                if not ep_data and provider == "ytdlp" and len(episodes) == 1:
                                    ep_data = list(episodes.values())[0]
                            abs_num = extract_absolute_episode_number(ep_num, ep_data, basename)
                            curr_season = 1
                            curr_ep_num = abs_num
                            
                        ep_title = sanitize_filename(ep_title)
                        
                        try:
                            season_str = f"S{int(curr_season):02d}"
                        except (ValueError, TypeError):
                            season_str = f"S{curr_season}"
                        try:
                            ep_str = f"E{int(curr_ep_num):02d}"
                        except (ValueError, TypeError):
                            ep_str = f"E{curr_ep_num}"
                            
                        clean_title = f"{clean_show_name} - {season_str}{ep_str}"
                        if ep_title: clean_title += f" - {ep_title}"
                        clean_title = limit_filename_length(clean_title)
                        
                        clean_titles.append((curr_season, clean_title))
                        
                        target_filename = f"{clean_title}{ext}"
                        preview["renames"].append({"old": f, "new": target_filename})
                        
                        base_old = os.path.splitext(basename)[0]
                        for sf in all_files:
                            sbasename = os.path.basename(sf)
                            sext = os.path.splitext(sf)[1].lower()
                            if sbasename.startswith(base_old) and sf != f and sext in sub_exts:
                                preview["subs"].append({"old": sf, "new": f"{clean_title}{sext}"})
                    else:
                        pass
                elif ext in sub_exts:
                    pass # Handled above or ignored
                elif basename.lower() in good_meta or (ext in ('.nfo', '.jpg', '.png') and ('poster' in basename.lower() or 'fanart' in basename.lower())):
                    preview["subs"].append({"old": f, "new": basename})
                else:
                    preview["junk"].append(f)
                    
            sub_olds = [x["old"] for x in preview["subs"]]
            preview["junk"] = [j for j in preview["junk"] if j not in sub_olds and j not in [r["old"] for r in preview["renames"]]]
            
            if params.get("copy_to_nas", True):
                if clean_titles:
                    unique_paths = []
                    for s, t in clean_titles:
                        try:
                            s_num = int(s)
                            p = f"{dest_show_dir}/Staffel {s_num}/{t}"
                        except (ValueError, TypeError):
                            p = f"{dest_show_dir}/{s}/{t}"
                        if p not in unique_paths:
                            unique_paths.append(p)
                    if len(unique_paths) == 1:
                        dest_str = f"NAS: {unique_paths[0]}"
                    else:
                        dest_str = "NAS:\n" + "\n".join(f"• {p}" for p in unique_paths)
                else:
                    try:
                        s_num = int(season)
                        dest_str = f"NAS: {dest_show_dir}/Staffel {s_num}/[Episoden-Unterordner]"
                    except (ValueError, TypeError):
                        dest_str = f"NAS: {dest_show_dir}/[Staffeln]/[Episoden-Unterordner]"
            else:
                dest_str = "NAS: (nicht aktiv)"
                
            if params.get("copy_to_pcloud", False):
                if pcloud_path:
                    dest_str += f"\n☁️ pCloud: {pcloud_path}"
                else:
                    dest_str += "\n☁️ pCloud: (Kein Mapping gefunden)"
            else:
                dest_str += "\n☁️ pCloud: (nicht aktiv)"
            preview["destination"] = dest_str
            
        # Season year warning
        if media_type == "tv" and season is not None and not params.get("force_absolute_season_1", False):
            try:
                s_num = int(season)
                if s_num >= 1000:
                    preview["warning"] = f"Staffel-Nummer ist eine Jahreszahl ({s_num})! Bitte prüfen, ob das korrekt ist (z.B. Staffel 56 statt 2026)."
            except Exception:
                pass
                
        self.send_json(preview)

    def handle_api_nas_series(self, params):
        settings = load_settings()
        nas_root = settings.get("nas_root", "/Volumes/Kino")
        outbox_root = settings.get("outbox_dir", os.path.expanduser("~/Downloads/Medien Output"))
        
        nas_destination_id = params.get("nas_destination_id") or params.get("destination_id") or "2"
        if isinstance(nas_destination_id, list) and len(nas_destination_id) > 0:
            nas_destination_id = nas_destination_id[0]
        
        sync_cats = settings.get("sync_categories", [])
        categories_to_scan = []
        
        if nas_destination_id == "all":
            categories_to_scan = sync_cats
        else:
            found_cat = None
            for cat in sync_cats:
                if cat.get("id") == str(nas_destination_id):
                    found_cat = cat
                    break
            if not found_cat:
                for cat in sync_cats:
                    nas_sub = cat.get("nas_sub", "")
                    if nas_sub and (nas_sub in str(nas_destination_id)):
                        found_cat = cat
                        break
            if found_cat:
                categories_to_scan = [found_cat]
            else:
                categories_to_scan = [{"id": "2", "name": "Serien", "nas_sub": "/Serien"}]
                
        connected = ensure_nas_mounted()
        
        folders = set()
        folder_to_dest = {}
        
        for cat in categories_to_scan:
            nas_sub = cat.get("nas_sub")
            if not nas_sub:
                continue
            destination = f"{nas_root}{nas_sub}"
            cat_folders = set()
            
            if connected and os.path.exists(destination):
                try:
                    for entry in os.listdir(destination):
                        if os.path.isdir(os.path.join(destination, entry)) and not entry.startswith('.'):
                            cat_folders.add(entry)
                except Exception as e:
                    print(f"Fehler beim Scannen von NAS {destination}: {e}")
                    
            rel_dest = os.path.relpath(destination, nas_root)
            outbox_dest = os.path.join(outbox_root, rel_dest)
            if os.path.exists(outbox_dest):
                try:
                    for entry in os.listdir(outbox_dest):
                        if os.path.isdir(os.path.join(outbox_dest, entry)) and not entry.startswith('.'):
                            cat_folders.add(entry)
                except Exception as e:
                    print(f"Fehler beim Scannen von Outbox {outbox_dest}: {e}")
                    
            for folder in cat_folders:
                folder_clean = folder.strip()
                if not folder_clean:
                    continue
                lower_folder = folder_clean.lower()
                folders.add(folder_clean)
                folder_to_dest[lower_folder] = destination
                    
        # Case-insensitive deduplication
        deduped = {}
        for entry in folders:
            name = entry.strip()
            if not name:
                continue
            lowered = name.lower()
            if lowered in deduped:
                # Keep the one with better casing (more uppercase letters)
                existing = deduped[lowered]
                existing_caps = sum(1 for c in existing if c.isupper())
                entry_caps = sum(1 for c in name if c.isupper())
                if entry_caps > existing_caps:
                    deduped[lowered] = name
            else:
                deduped[lowered] = name

        self.send_json({
            "connected": connected,
            "folders": sorted(list(deduped.values()), key=lambda s: s.lower()),
            "folder_destinations": {k: folder_to_dest[k] for k in deduped.keys() if k in folder_to_dest}
        })

    def handle_api_series_detect(self, query):
        project_name = ""
        if "project_name" in query and len(query["project_name"]) > 0:
            project_name = query["project_name"][0]
            
        nas_destination_id = ""
        if "nas_destination_id" in query and len(query["nas_destination_id"]) > 0:
            nas_destination_id = query["nas_destination_id"][0]
        elif "destination_id" in query and len(query["destination_id"]) > 0:
            nas_destination_id = query["destination_id"][0]
            
        if not project_name:
            self.send_json({"found": False})
            return
            
        settings = load_settings()
        nas_root = settings.get("nas_root", "/Volumes/Kino")
        outbox_root = settings.get("outbox_dir", os.path.expanduser("~/Downloads/Medien Output"))
        
        # Resolve destination paths to search in
        destinations = []
        sync_cats = settings.get("sync_categories", [])
        
        if nas_destination_id == "all":
            for cat in sync_cats:
                nas_sub = cat.get("nas_sub", "")
                if nas_sub:
                    destinations.append(f"{nas_root}{nas_sub}")
        else:
            found_cat = None
            if nas_destination_id:
                for cat in sync_cats:
                    if cat.get("id") == str(nas_destination_id):
                        found_cat = cat
                        break
                if not found_cat:
                    for cat in sync_cats:
                        nas_sub = cat.get("nas_sub", "")
                        if nas_sub and (nas_sub in str(nas_destination_id)):
                            found_cat = cat
                            break
            if found_cat:
                destinations.append(f"{nas_root}{found_cat.get('nas_sub')}")
            else:
                destinations.append(f"{nas_root}/Serien")
            
        connected = ensure_nas_mounted()
        
        # Find all folders and map them to their parent destination directory
        folders = set()
        folder_to_dest = {}
        
        for destination in destinations:
            if connected and os.path.exists(destination):
                try:
                    for entry in os.listdir(destination):
                        if os.path.isdir(os.path.join(destination, entry)) and not entry.startswith('.'):
                            folders.add(entry)
                            folder_to_dest[entry] = destination
                except Exception:
                    pass
                    
            rel_dest = os.path.relpath(destination, nas_root)
            outbox_dest = os.path.join(outbox_root, rel_dest)
            if os.path.exists(outbox_dest):
                try:
                    for entry in os.listdir(outbox_dest):
                        if os.path.isdir(os.path.join(outbox_dest, entry)) and not entry.startswith('.'):
                            folders.add(entry)
                            if entry not in folder_to_dest:
                                folder_to_dest[entry] = destination
                except Exception:
                    pass
                    
        cleaned_proj = clean_series_name_for_fs(project_name)
        
        # Helper to find best match in list
        best_match = None
        
        # 1. Exact case-insensitive match
        for f in folders:
            if f.lower().strip() == cleaned_proj.lower().strip():
                best_match = f
                break
                
        # 2. Normalized match
        if not best_match:
            import re
            norm_proj = re.sub(r'[^a-zA-Z0-9]', '', cleaned_proj.lower())
            if norm_proj:
                for f in folders:
                    norm_f = re.sub(r'[^a-zA-Z0-9]', '', f.lower())
                    if norm_f == norm_proj:
                        best_match = f
                        break
                        
        # 3. Substring match
        if not best_match:
            norm_proj = re.sub(r'[^a-zA-Z0-9]', '', cleaned_proj.lower())
            if len(norm_proj) >= 4:
                for f in folders:
                    norm_f = re.sub(r'[^a-zA-Z0-9]', '', f.lower())
                    if norm_proj in norm_f or norm_f in norm_proj:
                        best_match = f
                        break
                        
        if best_match:
            existing_seasons = []
            folder_found = False
            matched_dest = folder_to_dest.get(best_match)
            if matched_dest:
                folder_found = True
                series_dirs = []
                if connected and os.path.exists(matched_dest):
                    series_dirs.append(os.path.join(matched_dest, best_match))
                
                rel_dest = os.path.relpath(matched_dest, nas_root)
                outbox_series_dir = os.path.join(outbox_root, rel_dest, best_match)
                series_dirs.append(outbox_series_dir)
                
                for sd in series_dirs:
                    if os.path.exists(sd) and os.path.isdir(sd):
                        try:
                            for entry in os.listdir(sd):
                                entry_path = os.path.join(sd, entry)
                                if os.path.isdir(entry_path) and not entry.startswith('.'):
                                    if entry not in existing_seasons:
                                        existing_seasons.append(entry)
                        except Exception:
                            pass
            existing_seasons.sort(key=lambda s: s.lower())

            # Check if tvshow.nfo exists
            # We must check both NAS and Outbox paths
            nfo_paths = []
            if matched_dest:
                if connected and os.path.exists(matched_dest):
                    nfo_paths.append(os.path.join(matched_dest, best_match, "tvshow.nfo"))
                
                rel_dest = os.path.relpath(matched_dest, nas_root)
                outbox_dest = os.path.join(outbox_root, rel_dest)
                nfo_paths.append(os.path.join(outbox_dest, best_match, "tvshow.nfo"))
                
            show_id = None
            provider = None
            
            for np in nfo_paths:
                if os.path.exists(np):
                    try:
                        with open(np, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                        # Search for mw_provider and mw_showid
                        import re
                        m_prov = re.search(r'<mw_provider>(.*?)</mw_provider>', content)
                        m_id = re.search(r'<mw_showid>(.*?)</mw_showid>', content)
                        
                        if m_prov and m_id:
                            provider = m_prov.group(1).strip()
                            show_id = m_id.group(1).strip()
                            break
                            
                        # Fallback search for tvdbid or tmdbid
                        m_tvdb = re.search(r'<tvdbid>(.*?)</tvdbid>', content)
                        if m_tvdb:
                            provider = "tvdb"
                            show_id = m_tvdb.group(1).strip()
                            break
                            
                        m_tmdb = re.search(r'<tmdbid>(.*?)</tmdbid>', content)
                        if m_tmdb:
                            provider = "tmdb_tv"
                            show_id = m_tmdb.group(1).strip()
                            break
                    except Exception:
                        pass
                        
            if show_id and provider:
                self.send_json({
                    "found": True,
                    "show_id": show_id,
                    "provider": provider,
                    "show_name": best_match,
                    "folder_found": folder_found,
                    "existing_seasons": existing_seasons
                })
                return
            else:
                self.send_json({
                    "found": False,
                    "show_name": best_match,
                    "folder_found": folder_found,
                    "existing_seasons": existing_seasons
                })
                return
                
        self.send_json({"found": False})

    def handle_api_metadata_fetch(self, query):
        media_type = query.get("media_type", [""])[0]
        provider = query.get("provider", [""])[0]
        
        result = {}
        try:
            if media_type == "tv":
                show_id = query.get("show_id", [""])[0]
                result = mw_metadata.fetch_show_nfo_data(provider, show_id)
            elif media_type == "movie":
                movie_id = query.get("movie_id", [""])[0]
                result = mw_metadata.fetch_movie_nfo_data(provider, movie_id)
            elif media_type == "episode":
                show_id = query.get("show_id", [""])[0]
                season = query.get("season", [""])[0]
                episode = query.get("episode", [""])[0]
                result = mw_metadata.fetch_episode_nfo_data(provider, show_id, season, episode)
        except Exception as e:
            result = {"error": str(e)}
            
        self.send_json(result)

    def handle_api_system_open_folder(self, query):
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
                self.send_json({"error": f"Kategorie mit ID {category_id} nicht gefunden."})
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
            self.send_json({"error": "Pfad oder Kategorie-Parameter fehlt."})
            return
            
        if not os.path.exists(folder_path):
            self.send_json({"error": f"Pfad existiert nicht: {folder_path}. Ist das NAS gemountet?"})
            return
            
        try:
            subprocess.run(["open", folder_path], check=True)
            self.send_json({"success": True, "msg": f"Ordner {folder_path} im Finder geöffnet."})
        except Exception as e:
            self.send_json({"error": f"Fehler beim Öffnen des Ordners: {str(e)}"})

    def handle_api_joke(self):
        joke = get_random_joke()
        self.send_json({"joke": joke})

    def handle_api_get_subscriptions(self):
        settings = load_settings()
        self.send_json({"subscriptions": settings.get("youtube_subscriptions", [])})
        
    def handle_api_post_subscriptions(self, params):
        subs = params.get("subscriptions", [])
        settings = load_settings()
        settings["youtube_subscriptions"] = subs
        save_settings(settings)
        self.send_json({"status": "success"})
        
    def handle_api_check_subscriptions(self):
        trigger_youtube_subscriptions_check()
        self.send_json({"status": "success", "message": "Überprüfung gestartet"})

    def handle_api_process(self, params):
        task_id = str(uuid.uuid4())
        params["task_id"] = task_id
        media_type = params.get("media_type", "unknown")
        
        name = params.get("project_name", "Unbekannt")
        if name.endswith("/"): name = name[:-1]
        name = os.path.basename(name)
        if media_type == "youtube":
            name = "YouTube Download"
            
        convert = params.get("convert", False)
        copy_to_nas = params.get("copy_to_nas", True)
        copy_to_pcloud = params.get("copy_to_pcloud", False)
        show_id = params.get("show_id")
        movie_id = params.get("movie_id")
        provider = params.get("provider")
        has_metadata = (show_id and provider) or (movie_id and provider)
        
        job_info = {
            "id": task_id,
            "type": media_type,
            "name": name,
            "status": "queued",
            "progress": 0,
            "message": "Wartet in der Schlange...",
            "timestamp": time.time(),
            "params": params,
            "pipeline": {
                "metadata": {"status": "pending" if has_metadata else "skipped", "progress": 0},
                "convert": {"status": "pending" if convert else "skipped", "progress": 0},
                "nas": {"status": "pending" if copy_to_nas else "skipped", "progress": 0},
                "pcloud": {"status": "pending" if copy_to_pcloud else "skipped", "progress": 0}
            }
        }
        
        with active_jobs_lock:
            active_jobs[task_id] = job_info
            
        if media_type == "youtube":
            job_info["status"] = "running"
            job_info["message"] = "Download läuft..."
            thread = threading.Thread(target=process_worker, args=(params,), daemon=True)
            thread.start()
        else:
            job_queue.put(job_info)
            
        self.send_json({"status": "started", "task_id": task_id})

    def handle_api_queue(self):
        with active_jobs_lock:
            jobs_list = []
            for j in active_jobs.values():
                jobs_list.append({
                    "id": j["id"],
                    "type": j["type"],
                    "name": j["name"],
                    "status": j["status"],
                    "progress": j["progress"],
                    "message": j["message"],
                    "timestamp": j["timestamp"],
                    "pipeline": j.get("pipeline")
                })
        jobs_list.sort(key=lambda x: x["timestamp"])
        self.send_json({"jobs": jobs_list})

    def handle_api_queue_clear(self):
        with active_jobs_lock:
            to_keep = {}
            for task_id, job in active_jobs.items():
                if job.get("status") not in ("done", "error"):
                    to_keep[task_id] = job
            active_jobs.clear()
            active_jobs.update(to_keep)
        self.send_json({"status": "success"})

    def handle_api_yt_fetch(self, query):
        url_list = query.get("url", [""])
        url = url_list[0]
        if not url:
            self.send_json({"error": "Keine URL angegeben."})
            return
            
        cmd = ["yt-dlp", "--dump-json", "--skip-download", "--cookies-from-browser", "chrome", url]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if proc.returncode != 0:
                cmd_fallback = ["yt-dlp", "--dump-json", "--skip-download", url]
                proc = subprocess.run(cmd_fallback, capture_output=True, text=True, timeout=15)
                
            if proc.returncode != 0:
                self.send_json({"error": f"yt-dlp Fehler: {proc.stderr}"})
                return
                
            stdout_lines = proc.stdout.strip().split("\n")
            if not stdout_lines or not stdout_lines[0]:
                self.send_json({"error": "Keine Daten von yt-dlp erhalten."})
                return
                
            data = json.loads(stdout_lines[0])
            
            title = data.get("title") or "Unbekannter Titel"
            uploader = data.get("uploader") or "Unbekannter Uploader"
            thumbnail = data.get("thumbnail") or ""
            duration = data.get("duration") or 0
            
            chapters = []
            for ch in (data.get("chapters") or []):
                if ch:
                    chapters.append({
                        "title": ch.get("title", ""),
                        "start_time": ch.get("start_time", 0),
                        "end_time": ch.get("end_time", 0)
                    })
                
            # Helper to map exact format heights to standard resolutions (e.g. 808p -> 1080p)
            def get_standard_resolution(fmt):
                note = fmt.get("format_note") or ""
                if note.endswith("p") and note[:-1].isdigit():
                    return int(note[:-1])
                h = fmt.get("height")
                if h and isinstance(h, int):
                    if h > 1440:
                        return 2160
                    elif h > 720:
                        return 1080
                    elif h > 480:
                        return 720
                    elif h > 360:
                        return 480
                    else:
                        return 360
                return None

            # Analyze formats to detect codecs and standard heights
            formats_list = data.get("formats") or []
            std_heights = set()
            for fmt in formats_list:
                if fmt:
                    std_h = get_standard_resolution(fmt)
                    if std_h:
                        std_heights.add(std_h)
            
            sorted_std_heights = sorted(list(std_heights), reverse=True)
            resolutions = []
            
            # 1. Best quality option
            resolutions.append({
                "id": "best",
                "label": "Beste Qualität (Video + Audio)"
            })
            
            # 2. Add height-specific options with codec information
            for std_h in sorted_std_heights:
                if std_h < 360:
                    continue
                    
                has_av1 = False
                has_vp9 = False
                has_h264 = False
                
                # Check what codecs are available for this standard height
                for fmt in formats_list:
                    if fmt and get_standard_resolution(fmt) == std_h:
                        vcodec = (fmt.get("vcodec") or "").lower()
                        if vcodec.startswith("av01") or "av1" in vcodec:
                            has_av1 = True
                        elif vcodec.startswith("vp9") or vcodec.startswith("vp09"):
                            has_vp9 = True
                        elif vcodec.startswith("avc1") or "h264" in vcodec or "avc" in vcodec:
                            has_h264 = True
                
                added_any = False
                # H.264 (AVC)
                if has_h264:
                    resolutions.append({
                        "id": f"{std_h}p_h264",
                        "label": f"Maximal {std_h}p (H.264 – beste Kompatibilität)"
                    })
                    added_any = True
                # VP9
                if has_vp9:
                    resolutions.append({
                        "id": f"{std_h}p_vp9",
                        "label": f"Maximal {std_h}p (VP9 – höchste Bildqualität)"
                    })
                    added_any = True
                # AV1
                if has_av1:
                    resolutions.append({
                        "id": f"{std_h}p_av1",
                        "label": f"Maximal {std_h}p (AV1 – kleinere Datei)"
                    })
                    added_any = True
                
                # Fallback if no specific codec detected or none were added
                if not added_any:
                    resolutions.append({
                        "id": f"{std_h}p",
                        "label": f"Maximal {std_h}p"
                    })
            
            # 3. Audio-only option
            resolutions.append({
                "id": "audio",
                "label": "Nur Audio extrahieren (MP3)"
            })
            
            subs_dict = data.get("subtitles") or {}
            auto_subs_dict = data.get("automatic_captions") or {}
            subs = list(subs_dict.keys())
            
            # Filter auto-captions to common languages only (de, en)
            common_langs = {'de', 'en'}
            auto_subs = []
            for lang in auto_subs_dict.keys():
                lang_lower = lang.lower()
                base_lang = lang_lower.split('-')[0]
                if base_lang in common_langs:
                    auto_subs.append(lang)
                    
            all_subs = sorted(list(set(subs + auto_subs)))
            
            description = data.get("description", "")
            
            self.send_json({
                "title": title,
                "uploader": uploader,
                "thumbnail": thumbnail,
                "duration": duration,
                "chapters": chapters,
                "resolutions": resolutions,
                "subtitles": all_subs,
                "description": description
            })
        except Exception as e:
            self.send_json({"error": f"Fehler bei Link-Analyse: {str(e)}"})

    def handle_api_yt_segments(self, query):
        task_id = query.get("taskId", [""])[0]
        if not task_id:
            self.send_json({"error": "Keine taskId angegeben."})
            return
            
        with active_yt_tasks_lock:
            task = active_yt_tasks.get(task_id)
            
        if not task:
            self.send_json({"error": "Task nicht gefunden."})
            return
            
        temp_dir = task.get("temp_dir")
        segments = []
        if temp_dir and os.path.exists(temp_dir):
            for f in sorted(os.listdir(temp_dir)):
                if f.lower().endswith(('.mp4', '.mkv', '.avi', '.webm', '.mov')) and not f.startswith("."):
                    segments.append(f)
                    
        self.send_json({
            "state": task.get("state"),
            "segments": segments,
            "title": task.get("params", {}).get("yt_title", "")
        })

    def handle_api_yt_cut_done(self, params):
        task_id = params.get("task_id")
        if not task_id:
            self.send_json({"error": "Keine task_id angegeben."})
            return
            
        with active_yt_tasks_lock:
            task = active_yt_tasks.get(task_id)
            
        if not task:
            self.send_json({"error": "Task nicht gefunden."})
            return
            
        task["state"] = "scanning_after_cut"
        task["event"].set()
        self.send_json({"status": "ok"})

    def handle_api_yt_finalize(self, params):
        task_id = params.get("task_id")
        mapping = params.get("mapping", {})
        
        if not task_id:
            self.send_json({"error": "Keine task_id angegeben."})
            return
            
        with active_yt_tasks_lock:
            task = active_yt_tasks.get(task_id)
            
        if not task:
            self.send_json({"error": "Task nicht gefunden."})
            return
            
        task["mapping"] = mapping
        task["state"] = "finalizing"
        task["mapping_event"].set()
        self.send_json({"status": "ok"})

    def handle_api_logs(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        self.wfile.write(b"data: Konsole verbunden. Log-Streaming aktiv...\n\n")
        self.wfile.flush()
        
        while True:
            try:
                line = log_queue.get(timeout=2.0)
                data_str = f"data: {line.strip()}\n\n"
                self.wfile.write(data_str.encode('utf-8'))
                self.wfile.flush()
            except queue.Empty:
                try:
                    self.wfile.write(b": keep-alive\n\n")
                    self.wfile.flush()
                except socket.error:
                    break
            except socket.error:
                break

    def send_json(self, data):
        content = json.dumps(data).encode('utf-8')
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

def job_queue_worker():
    while True:
        job = job_queue.get()
        if job is None:
            break
        task_id = job["id"]
        with active_jobs_lock:
            active_jobs[task_id]["status"] = "running"
            active_jobs[task_id]["message"] = "Verarbeitung gestartet..."
        
        try:
            params = job["params"]
            params["task_id"] = task_id
            process_worker(params)
            
            with active_jobs_lock:
                active_jobs[task_id]["status"] = "done"
                active_jobs[task_id]["progress"] = 100
                active_jobs[task_id]["message"] = "Erfolgreich beendet"
        except Exception as e:
            with active_jobs_lock:
                active_jobs[task_id]["status"] = "error"
                active_jobs[task_id]["message"] = f"Fehler: {str(e)}"
            print(f"Job {task_id} failed: {e}")
        finally:
            job_queue.task_done()

def run_server():
    import webbrowser
    launch_url = f"http://127.0.0.1:8000/?v={int(time.time())}"
    
    try:
        fetch_online_jokes_async()
    except Exception as e:
        print(f"Jokes-Update fehlgeschlagen: {e}")
        
    try:
        server_address = ('127.0.0.1', 8000)
        httpd = ThreadingHTTPServer(server_address, GUIRequestHandler)
        print("Server started on http://127.0.0.1:8000")
        
        # Start browser after a tiny delay
        def open_browser():
            time.sleep(0.5)
            webbrowser.open(launch_url)
            
        threading.Thread(target=open_browser, daemon=True).start()
        
        # Start background job worker
        threading.Thread(target=job_queue_worker, daemon=True).start()
        
        # Start background YouTube subscriptions monitoring thread
        threading.Thread(target=check_youtube_subscriptions_loop, daemon=True).start()
        
        # Block and serve requests forever
        httpd.serve_forever()
        
    except OSError as e:
        if e.errno == 48 or "Address already in use" in str(e):
            print("Server is already running! Just opening the browser...")
            webbrowser.open(launch_url)
        else:
            raise e

if __name__ == '__main__':
    run_server()


