from gui.core.utils import load_settings, save_settings
import os, subprocess, time, shlex, shutil
from gui.core.helpers import *
import gui.core.media as media

_rsync_progress_flag = None

def check_nas_status():
    settings = load_settings()
    nas_target = next((t for t in settings.get("storage_targets", []) if t.get("id") == "nas"), None)
    if nas_target:
        nas_root = nas_target.get("root_path", "/Volumes/Kino")
        nas_host = nas_target.get("nas_ip", "192.168.2.208")
        nas_host_ts = nas_target.get("nas_ip_backup", "100.74.187.125")
        if not nas_target.get("enabled", True):
            return "offline"
    else:
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
        if not ip:
            continue
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
    nas_target = next((t for t in settings.get("storage_targets", []) if t.get("id") == "nas"), None)
    if nas_target:
        nas_root = nas_target.get("root_path", "/Volumes/Kino")
        if not nas_target.get("enabled", True):
            return False
    else:
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
        if nas_target:
            nas_host = nas_target.get("nas_ip", "192.168.2.208")
            nas_host_ts = nas_target.get("nas_ip_backup", "100.74.187.125")
            nas_share = nas_target.get("nas_share", "Kino")
        else:
            nas_host = "192.168.2.208"
            nas_host_ts = "100.74.187.125"
            nas_share = "Kino"
        
        chosen_ip = None
        for ip in [nas_host, nas_host_ts]:
            if not ip:
                continue
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
    
    cmd = ["rsync", "-a", "--inplace", "--no-owner", "--no-group", get_rsync_progress_flag()]
    if move:
        cmd.append("--remove-source-files")
        
    src_path = src
    if os.path.isdir(src) and not src.endswith('/'):
        src_path += '/'
        
    cmd.extend([src_path, dst])
    
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0)
    progress_pattern = re.compile(r'(\d+)%')
    speed_pattern = re.compile(r'(\d+\.?\d*\s*[kKMG]i?B/s)')
    
    output_lines = []
    last_logged_pct = -1
    for line in read_lines_from_stream(process.stdout):
        output_lines.append(line.strip())
        match = progress_pattern.search(line)
        if match:
            percent = int(match.group(1))
            speed_match = speed_pattern.search(line)
            speed_str = f" ({speed_match.group(1)})" if speed_match else ""
            msg = f"Übertragung: {percent}%{speed_str}"
            if task_id:
                if callable(task_id):
                    task_id(percent, msg)
                else:
                    with active_jobs_lock:
                        if task_id in active_jobs:
                            active_jobs[task_id]["progress"] = percent
                            active_jobs[task_id]["message"] = msg
            # Throttle logging: only print to log_message at multiples of 10%
            if percent % 10 == 0 and percent != last_logged_pct:
                log_message(msg)
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
        except Exception:
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
                        if "pipeline" in active_jobs[task_id] and "metadata" in active_jobs[task_id]["pipeline"]:
                            active_jobs[task_id]["pipeline"]["metadata"]["progress"] = percent
                            active_jobs[task_id]["pipeline"]["metadata"]["status"] = "running"
                        
    proc.wait()
    return proc.returncode == 0

def resolve_target_destination(target, rel_sub, media_type="movie"):
    """
    Resolves the destination folder/path for a specific target based on the relative subpath on NAS.
    """
    settings = load_settings()
    t_id = target.get("id")
    t_type = target.get("type")
    
    # 1. Look up sync category mapping
    sync_cats = settings.get("sync_categories", [])
    for cat in sync_cats:
        if cat.get("nas_sub") == rel_sub:
            if "targets" in cat and t_id in cat["targets"]:
                val = cat["targets"][t_id]
                if t_type == "nas" or t_id == "nas" or t_type == "local":
                    root = target.get("root_path", "/Volumes/Kino")
                    if val.startswith(root):
                        return val
                    else:
                        return os.path.join(root, val.lstrip("/"))
                return val
            # Fallbacks
            if t_type == "nas" or t_id == "nas":
                return os.path.join(target.get("root_path", "/Volumes/Kino"), cat.get("nas_sub", rel_sub).lstrip("/"))
            else:
                return cat.get("pcloud_remote", "")
                
    # 2. Fallback if no sync category matches rel_sub
    if t_type == "nas" or t_id == "nas":
        return os.path.join(target.get("root_path", "/Volumes/Kino"), rel_sub.lstrip("/"))
    else:
        # Cloud/Rclone remote prefix
        rclone_remote = target.get("rclone_remote", "")
        # Fallback category name based on media_type
        fallback_sub = "03_Filme" if media_type == "movie" else "04_Serien"
        if rclone_remote:
            remote_prefix = rclone_remote if ":" in rclone_remote else f"{rclone_remote}:"
            return f"{remote_prefix}{fallback_sub}"
        else:
            return fallback_sub

def copy_to_cloud_target(source_dir, nas_target_dir, target_id, task_id=None, explicit_remote_base=None):
    import shutil
    settings = load_settings()
    nas_target = next((t for t in settings.get("storage_targets", []) if t.get("id") == "nas"), None)
    nas_root = nas_target.get("root_path", "/Volumes/Kino") if nas_target else settings.get("nas_root", "/Volumes/Kino")
    
    # Find the target configuration
    target = next((t for t in settings.get("storage_targets", []) if t.get("id") == target_id), None)
    if not target:
        log_message(f"❌ Ziel '{target_id}' nicht in Einstellungen gefunden.")
        return False
        
    if not target.get("enabled", True):
        log_message(f"⚠️ Ziel '{target.get('name')}' ist deaktiviert. Überspringe Kopieren.")
        return True
        
    pcloud_local = target.get("root_path", "")
    rclone_remote = target.get("rclone_remote", "")
    target_name = target.get("name", target_id)
    
    if explicit_remote_base:
        remote_base = explicit_remote_base
    else:
        sync_cats = settings.get("sync_categories", [])
        mapping = {}
        for cat in sync_cats:
            t_sub = None
            if "targets" in cat and target_id in cat["targets"]:
                t_sub = cat["targets"][target_id]
            if not t_sub:
                if target.get("type") == "nas":
                    t_sub = cat.get("nas_sub", "")
                else:
                    t_sub = cat.get("pcloud_remote", "")
            
            nas_path = f"{nas_root}{cat['nas_sub']}"
            mapping[nas_path] = t_sub

        remote_base = mapping.get(nas_target_dir)
        if not remote_base:
            # Backend-neutraler Fallback-Ordner, falls eine Kategorie kein Mapping hat.
            # (Greift nur, wenn weder targets[<id>] noch cloud_remote/pcloud_remote gesetzt sind.)
            fallback_sub = "Sonstiges"
            if rclone_remote:
                remote_prefix = rclone_remote if ":" in rclone_remote else f"{rclone_remote}:"
                remote_base = f"{remote_prefix}{fallback_sub}"
            else:
                remote_base = fallback_sub
            log_message(f"⚠️ Warnung: Kein Mapping für '{nas_target_dir}' auf '{target_name}' gefunden. Nutze Fallback: '{remote_base}'")

    folder_name = os.path.basename(source_dir.rstrip('/'))
    if rclone_remote and ":" in rclone_remote and remote_base and ":" not in remote_base:
        remote_base = f"{rclone_remote.split(':')[0]}:{remote_base}"

    remote_target = f"{remote_base}/{folder_name}"
    
    log_message(f"☁️ Upload nach {target_name} wird vorbereitet...")
    
    fuse_ok = False
    if pcloud_local and os.path.isdir(pcloud_local):
        try:
            subprocess.run(["ls", pcloud_local], capture_output=True, timeout=2, check=True)
            fuse_ok = True
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            log_message(f"⚠️ Lokaler Pfad {pcloud_local} antwortet nicht. Falle auf rclone zurück.")
            
    if fuse_ok:
        prefix = rclone_remote
        if prefix and ":" in prefix:
            clean_remote_target = remote_target.replace(prefix, pcloud_local + "/")
        else:
            clean_remote_target = os.path.join(pcloud_local, remote_target.lstrip("/"))
            
        local_target = os.path.abspath(clean_remote_target)
        
        log_message(f"☁️ {target_name} (Lokal): Kopiere nach {local_target}")
        try:
            success = run_rsync_with_progress(source_dir, local_target, task_id)
            if success:
                log_message(f"✅ {target_name}: Erfolgreich übertragen nach {local_target}")
                return True
            else:
                log_message(f"❌ {target_name} Fehler bei der Übertragung.")
        except Exception as e:
            log_message(f"❌ Fehler bei lokalem Kopieren nach {target_name}: {e}")
            
    if rclone_remote:
        log_message(f"☁️ {target_name} (rclone Fallback): {remote_target}")
        if not shutil.which("rclone"):
            log_message("⚠️ Warnung: rclone nicht gefunden. Upload abgebrochen.")
            return False
            
        try:
            cmd = ["rclone", "copy", source_dir, remote_target, "--transfers", "2", "--retries", "3", "--stats", "1s", "--stats-one-line"]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0)
            rclone_pattern = re.compile(r'(\d+)%,')
            speed_pattern = re.compile(r'(\d+\.?\d*\s*[kKMG]i?B/s)')
            
            last_logged_pct = -1
            for line in read_lines_from_stream(process.stdout):
                match = rclone_pattern.search(line)
                if match:
                    percent = int(match.group(1))
                    speed_match = speed_pattern.search(line)
                    speed_str = f" ({speed_match.group(1)})" if speed_match else ""
                    msg = f"Upload ({target_name}): {percent}%{speed_str}"
                    if task_id:
                        if callable(task_id):
                            task_id(percent, msg)
                        else:
                            with active_jobs_lock:
                                if task_id in active_jobs:
                                    active_jobs[task_id]["progress"] = percent
                                    active_jobs[task_id]["message"] = msg
                    if percent % 10 == 0 and percent != last_logged_pct:
                        log_message(msg)
                        last_logged_pct = percent
                            
            process.wait()
            if process.returncode == 0:
                log_message(f"✅ {target_name}: Rclone-Upload abgeschlossen nach {remote_target}")
                return True
            else:
                log_message(f"❌ {target_name} Rclone Fehler.")
        except Exception as e:
            log_message(f"❌ Fehler bei {target_name} Rclone: {e}")
            
    return False

def copy_to_pcloud(source_dir, nas_target_dir, task_id=None, explicit_remote_base=None):
    return copy_to_cloud_target(source_dir, nas_target_dir, "pcloud", task_id, explicit_remote_base)


def walk_nas_categories(settings=None):
    """Iteriert über alle Top-Level-Ordner (Serien/Filme) aller NAS-Sync-Kategorien.

    Gemeinsame Grundlage für Health-Scan (Feature 3) und Duplikat-Erkennung (Feature 4).

    Liefert pro Show-/Film-Ordner ein dict:
        {
          "category": <Kategoriename>,
          "category_id": <id>,
          "type": "series" | "movie",   # series = Ordner mit Staffel-Struktur
          "name": <Ordnername>,
          "path": <absoluter Pfad>
        }

    'type' wird primär über den Kategorienamen bestimmt ("Serie" -> series),
    mit Fallback auf das Vorhandensein von "Staffel/Season"-Unterordnern.
    """
    if settings is None:
        settings = load_settings()
    nas_root = settings.get("nas_root", "/Volumes/Kino")
    sync_cats = settings.get("sync_categories", [])

    def looks_like_season(entry_name):
        low = entry_name.lower()
        return low.startswith("staffel ") or low.startswith("season ") or low.startswith("specials")

    for cat in sync_cats:
        nas_sub = cat.get("nas_sub")
        if not nas_sub:
            continue
        cat_path = f"{nas_root}{nas_sub}"
        if not os.path.isdir(cat_path):
            continue

        cat_name = cat.get("name", "")
        # Kategorie-Typ: Name enthält "serie" -> Serien-Kategorie
        cat_is_series = "serie" in cat_name.lower()

        try:
            entries = sorted(os.listdir(cat_path))
        except OSError:
            continue

        for entry in entries:
            if entry.startswith('.'):
                continue
            show_path = os.path.join(cat_path, entry)
            if not os.path.isdir(show_path):
                continue

            # Typ bestimmen: Kategorie-Hinweis, sonst Fallback über Staffel-Unterordner
            item_type = "series" if cat_is_series else "movie"
            if not cat_is_series:
                try:
                    if any(os.path.isdir(os.path.join(show_path, e)) and looks_like_season(e)
                           for e in os.listdir(show_path)):
                        item_type = "series"
                except OSError:
                    pass

            yield {
                "category": cat_name,
                "category_id": cat.get("id"),
                "type": item_type,
                "name": entry,
                "path": show_path,
            }
