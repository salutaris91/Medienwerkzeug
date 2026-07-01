from gui.core.utils import load_settings, save_settings, get_runtime_capabilities
import os, socket, subprocess, time, shutil
from urllib.parse import quote
from gui.core.helpers import *
from gui.core.resilience import run_with_retries_and_timeout
import gui.core.media as media

_rsync_progress_flag = None

def _is_nas_root_mounted(nas_root):
    if not nas_root:
        return False
    try:
        target_path = os.path.abspath(nas_root).rstrip("/")
        out = subprocess.check_output(["mount"], text=True)
        for line in out.splitlines():
            if " on " in line:
                parts = line.split(" on ")
                if len(parts) >= 2:
                    mount_point = parts[1].split(" (")[0].strip()
                    mount_point = os.path.abspath(mount_point).rstrip("/")
                    if target_path == mount_point or target_path.startswith(mount_point + "/"):
                        if os.path.isdir(target_path):
                            return True
    except Exception as e:
        log_message(f"❌ NAS-Mount-Status konnte nicht gelesen werden: {e}")
    return False

def _wait_for_nas_mount(nas_root, attempts, delay_seconds=1):
    for _ in range(attempts):
        if _is_nas_root_mounted(nas_root):
            return True
        time.sleep(delay_seconds)
    return False

def _open_nas_in_finder(nas_host, nas_share):
    finder_url = f"smb://{nas_host}/{quote(nas_share)}"
    try:
        log_message(f"📂 Öffne Finder-Fallback für {finder_url}...")
        result = subprocess.run(
            ["open", finder_url],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            error = (result.stderr or result.stdout or "Unbekannter Finder-Fehler").strip()
            log_message(f"❌ Finder-Fallback fehlgeschlagen: {error}")
            return False
        return True
    except Exception as e:
        log_message(f"❌ Finder-Fallback konnte nicht geöffnet werden: {e}")
        return False

def check_nas_status():
    settings = load_settings()
    nas_target = next((t for t in settings.get("storage_targets", []) if t.get("id") == "nas"), None)
    if nas_target:
        nas_root = nas_target.get("root_path", "")
        nas_host = nas_target.get("nas_ip", "")
        nas_host_ts = nas_target.get("nas_ip_backup", "")
        if not nas_target.get("enabled", True):
            return "offline"
    else:
        nas_root = settings.get("nas_root", "")
        nas_host = ""
        nas_host_ts = ""
    
    if not nas_root:
        return "offline"
    
    is_docker = get_runtime_capabilities()["runtime"] == "docker"
    if is_docker:
        return "connected" if os.path.isdir(nas_root) else "offline"
    
    # 1. Check if mounted
    mounted = _is_nas_root_mounted(nas_root)
        
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

def check_nas_connection_details():
    settings = load_settings()
    nas_target = next((t for t in settings.get("storage_targets", []) if t.get("id") == "nas"), None)
    
    nas_enabled = True
    nas_root = ""
    nas_host = ""
    nas_host_ts = ""
    
    if nas_target:
        nas_root = nas_target.get("root_path", "")
        nas_host = nas_target.get("nas_ip", "")
        nas_host_ts = nas_target.get("nas_ip_backup", "")
        nas_enabled = nas_target.get("enabled", True)
    else:
        nas_root = settings.get("nas_root", "")
        
    has_root = bool(nas_root)
    
    ip_details = []
    if nas_host:
        ip_details.append({"address": nas_host, "role": "primary"})
    if nas_host_ts:
        ip_details.append({"address": nas_host_ts, "role": "backup"})
        
    checked_ips = [info["address"] for info in ip_details]
            
    if not nas_enabled:
        return {
            "status": "offline",
            "enabled": False,
            "has_root": has_root,
            "checked_ips": checked_ips,
            "reachable_ip": None,
            "ip_details": ip_details,
            "error_message": "NAS-Verbindung in den Einstellungen deaktiviert."
        }
        
    if not has_root:
        return {
            "status": "offline",
            "enabled": True,
            "has_root": False,
            "checked_ips": checked_ips,
            "reachable_ip": None,
            "ip_details": ip_details,
            "error_message": "Kein nas_root konfiguriert."
        }

    is_docker = get_runtime_capabilities()["runtime"] == "docker"
    if is_docker:
        if os.path.isdir(nas_root):
            return {
                "status": "connected",
                "enabled": nas_enabled,
                "has_root": has_root,
                "checked_ips": [],
                "reachable_ip": None,
                "ip_details": [],
                "error_message": None
            }
        else:
            return {
                "status": "offline",
                "enabled": nas_enabled,
                "has_root": has_root,
                "checked_ips": [],
                "reachable_ip": None,
                "ip_details": [],
                "error_message": f"Docker-Volume nicht im Container verfügbar (nas_root Pfad '{nas_root}' existiert nicht). Bitte das Volume-Mapping in docker-compose.yml prüfen."
            }

    # 1. Check if mounted
    mounted = _is_nas_root_mounted(nas_root)
        
    # 2. Check ping/nc
    reachable_ip = None
    errors = []
    
    for ip_info in ip_details:
        ip = ip_info["address"]
        if reachable_ip is not None:
            ip_info["reachable"] = False
            ip_info["error"] = None
            continue
            
        s = None
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.3)
            s.connect((ip, 445))
            reachable_ip = ip
            ip_info["reachable"] = True
            ip_info["error"] = None
        except socket.timeout:
            ip_info["reachable"] = False
            err_msg = "Timeout (Port 445 antwortet nicht)"
            ip_info["error"] = err_msg
            errors.append(f"{ip_info['role']} ({ip}): {err_msg}")
        except ConnectionRefusedError:
            ip_info["reachable"] = False
            err_msg = "Verbindung abgelehnt (Port 445 geschlossen)"
            ip_info["error"] = err_msg
            errors.append(f"{ip_info['role']} ({ip}): {err_msg}")
        except OSError as e:
            ip_info["reachable"] = False
            err_msg = f"Netzwerkfehler ({e})"
            ip_info["error"] = err_msg
            errors.append(f"{ip_info['role']} ({ip}): {err_msg}")
        except Exception as e:
            ip_info["reachable"] = False
            err_msg = f"Netzwerkfehler ({e})"
            ip_info["error"] = err_msg
            errors.append(f"{ip_info['role']} ({ip}): {err_msg}")
        finally:
            if s:
                s.close()
            
    if mounted:
        status = "connected"
        error_message = None
    elif reachable_ip:
        status = "available_not_mounted"
        error_message = "Laufwerk erreichbar, aber nicht eingehängt."
    else:
        status = "offline"
        error_message = "; ".join(errors) if errors else "Keine IP-Adressen konfiguriert."
        
    return {
        "status": status,
        "enabled": nas_enabled,
        "has_root": has_root,
        "checked_ips": checked_ips,
        "reachable_ip": reachable_ip,
        "ip_details": ip_details,
        "error_message": error_message
    }

def ensure_nas_mounted(allow_finder_fallback=False):
    settings = load_settings()
    nas_target = next((t for t in settings.get("storage_targets", []) if t.get("id") == "nas"), None)
    if nas_target:
        nas_root = nas_target.get("root_path", "")
        if not nas_target.get("enabled", True):
            return False
    else:
        nas_root = settings.get("nas_root", "")
        
    if not nas_root:
        return False
        
    caps = get_runtime_capabilities()
    if not caps["capabilities"]["mount_nas"]:
        # Im Docker-Modus prüfen wir nur die Erreichbarkeit, kein automatisches Mounten!
        return os.path.isdir(nas_root)
        
    status = check_nas_status()
    if status == "connected":
        return True
        
    if status == "offline":
        try:
            log_message("🌐 Starte Tailscale...")
            subprocess.run(["tailscale", "up"], capture_output=True, timeout=5)
            status = check_nas_status()
        except Exception as e:
            log_message(f"⚠️ Tailscale-Start fehlgeschlagen: {e}")
            
    if status == "connected":
        return True
        
    if status in ["available_not_mounted", "offline"]:
        if nas_target:
            nas_host = nas_target.get("nas_ip", "")
            nas_host_ts = nas_target.get("nas_ip_backup", "")
            nas_share = nas_target.get("nas_share", "")
            nas_hostname = nas_target.get("nas_hostname", "")
        else:
            nas_host = ""
            nas_host_ts = ""
            nas_share = ""
            nas_hostname = ""
        
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
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                error = (result.stderr or result.stdout or "Unbekannter AppleScript-Fehler").strip()
                log_message(f"⚠️ Automatisches SMB-Mounting fehlgeschlagen: {error}")
            elif _wait_for_nas_mount(nas_root, attempts=3):
                log_message("✅ NAS erfolgreich gemountet!")
                return True
        except Exception as e:
            log_message(f"❌ Fehler beim Einhängen des NAS: {e}")

        if not allow_finder_fallback:
            log_message("ℹ️ Finder-Fallback für NAS-Mount übersprungen.")
            return os.path.exists(nas_root)

        finder_host = nas_hostname or chosen_ip
        if _open_nas_in_finder(finder_host, nas_share):
            if _wait_for_nas_mount(nas_root, attempts=10):
                log_message("✅ NAS erfolgreich über Finder gemountet!")
                return True
            log_message("❌ Finder wurde geöffnet, aber das NAS-Volume ist noch nicht eingebunden.")
            
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

def _quarantine_colliding_files(src, dst):
    """
    Sucht nach kollidierenden Dateien zwischen src und dst.
    Verschiebt diese in die Quarantäne (send_to_trash) bevor der Kopiervorgang startet.
    Wenn ein Verschieben fehlschlägt, wird eine Exception geworfen, um den Transfer abzubrechen.
    """
    import os
    import gui.core.trash as trash
    from gui.core.helpers import log_message

    if not os.path.exists(src):
        return

    collisions = []

    if os.path.isdir(src):
        for root, dirs, files in os.walk(src):
            for f in files:
                src_file = os.path.join(root, f)
                rel_path = os.path.relpath(src_file, src)
                dest_file = os.path.join(dst, rel_path)
                if os.path.exists(dest_file):
                    collisions.append(dest_file)
    else:
        dest_file = dst
        if os.path.isdir(dst):
            dest_file = os.path.join(dst, os.path.basename(src))

        if os.path.exists(dest_file) and not os.path.isdir(dest_file):
            collisions.append(dest_file)

    for col in collisions:
        log_message(f"Zentraler Transfer-Schutz: Kollision entdeckt für {col}. Sende in die Quarantäne...")
        try:
            trash.send_to_trash(col, force=True)
        except Exception as e:
            log_message(f"❌ Zentraler Transfer-Schutz: Quarantäne fehlgeschlagen für {col}: {e}")
            raise RuntimeError(f"Quarantäne-Backup fehlgeschlagen für {col}: {e}")

def run_copy_fallback(src, dst, task_id=None, protect_existing=False):
    import shutil
    import os
    
    log_message(f"rsync nicht verfügbar. Verwende Python-Fallback zum Kopieren von {src} nach {dst}...")
    if protect_existing:
        try:
            _quarantine_colliding_files(src, dst)
        except Exception as e:
            log_message(f"❌ Kopiervorgang abgebrochen, da das Quarantäne-Sicherheitsnetz fehlgeschlagen ist: {e}")
            return False

    try:
        # Determine if we are copying a directory or a file
        if os.path.isdir(src):
            # Target should be the destination directory (mirroring contents of src)
            os.makedirs(dst, exist_ok=True)
            
            # Find all files/symlinks to copy recursively to calculate total size
            files_to_copy = []
            total_size = 0
            
            for root, dirs, files in os.walk(src):
                # Handle directory symlinks and modify dirs in-place to prevent recursing
                for d in list(dirs):
                    dir_path = os.path.join(root, d)
                    dest_dir = os.path.join(dst, os.path.relpath(dir_path, src))
                    if os.path.islink(dir_path):
                        # Recreate directory symlink
                        if os.path.lexists(dest_dir):
                            if os.path.isdir(dest_dir) and not os.path.islink(dest_dir):
                                shutil.rmtree(dest_dir)
                            else:
                                os.remove(dest_dir)
                        os.symlink(os.readlink(dir_path), dest_dir)
                        dirs.remove(d) # Prevent os.walk from entering this directory
                    else:
                        os.makedirs(dest_dir, exist_ok=True)
                        
                for f in files:
                    filepath = os.path.join(root, f)
                    relpath = os.path.relpath(filepath, src)
                    if os.path.islink(filepath):
                        # It's a symlink, size is 0 for copy progress, flag as symlink
                        files_to_copy.append((filepath, relpath, 0, True))
                    else:
                        size = os.path.getsize(filepath)
                        files_to_copy.append((filepath, relpath, size, False))
                        total_size += size
            
            copied_size = 0
            # If directory has no files or symlinks, we still succeed (empty dirs are already created in walk)
            if not files_to_copy:
                if task_id:
                    if callable(task_id):
                        task_id(100, "Übertragung: 100%")
                    else:
                        from gui.core.jobs import update_job
                        update_job(task_id, progress=100, message="Übertragung: 100%")
                return True
                
            last_logged_pct = -1
            for filepath, relpath, size, is_symlink in files_to_copy:
                dest_filepath = os.path.join(dst, relpath)
                os.makedirs(os.path.dirname(dest_filepath), exist_ok=True)
                
                if is_symlink:
                    # Recreate symlink
                    if os.path.lexists(dest_filepath):
                        if os.path.isdir(dest_filepath) and not os.path.islink(dest_filepath):
                            shutil.rmtree(dest_filepath)
                        else:
                            os.remove(dest_filepath)
                    os.symlink(os.readlink(filepath), dest_filepath)
                else:
                    # Copy with chunked progress
                    with open(filepath, 'rb') as fsrc:
                        with open(dest_filepath, 'wb') as fdst:
                            while True:
                                buf = fsrc.read(1024 * 1024) # 1MB chunk
                                if not buf:
                                    break
                                fdst.write(buf)
                                copied_size += len(buf)
                                if total_size > 0:
                                    percent = int((copied_size / total_size) * 100)
                                    percent = min(99, percent)
                                    msg = f"Übertragung: {percent}%"
                                    if task_id:
                                        if callable(task_id):
                                            task_id(percent, msg)
                                        else:
                                            from gui.core.jobs import update_job
                                            update_job(task_id, progress=percent, message=msg)
                                    # Throttle logging
                                    if percent % 10 == 0 and percent != last_logged_pct:
                                        log_message(msg)
                                        last_logged_pct = percent
                    
                    try:
                        shutil.copystat(filepath, dest_filepath)
                    except Exception:
                        pass
            
            if task_id:
                if callable(task_id):
                    task_id(100, "Übertragung: 100%")
                else:
                    from gui.core.jobs import update_job
                    update_job(task_id, progress=100, message="Übertragung: 100%")
            log_message("Übertragung: 100%")
            return True
            
        else:
            # src is a file
            dest_file = dst
            if os.path.isdir(dst):
                dest_file = os.path.join(dst, os.path.basename(src))
            else:
                dest_dir = os.path.dirname(dst)
                if dest_dir:
                    os.makedirs(dest_dir, exist_ok=True)
                    
            if os.path.islink(src):
                # Recreate symlink at dest_file
                if os.path.lexists(dest_file):
                    if os.path.isdir(dest_file) and not os.path.islink(dest_file):
                        shutil.rmtree(dest_file)
                    else:
                        os.remove(dest_file)
                os.symlink(os.readlink(src), dest_file)
                if task_id:
                    if callable(task_id):
                        task_id(100, "Übertragung: 100%")
                    else:
                        from gui.core.jobs import update_job
                        update_job(task_id, progress=100, message="Übertragung: 100%")
                log_message("Übertragung: 100%")
                return True
                
            total_size = os.path.getsize(src)
            copied_size = 0
            last_logged_pct = -1
            
            with open(src, 'rb') as fsrc:
                with open(dest_file, 'wb') as fdst:
                    while True:
                        buf = fsrc.read(1024 * 1024)
                        if not buf:
                            break
                        fdst.write(buf)
                        copied_size += len(buf)
                        if total_size > 0:
                            percent = int((copied_size / total_size) * 100)
                            percent = min(99, percent)
                            msg = f"Übertragung: {percent}%"
                            if task_id:
                                if callable(task_id):
                                    task_id(percent, msg)
                                else:
                                    from gui.core.jobs import update_job
                                    update_job(task_id, progress=percent, message=msg)
                            # Throttle logging
                            if percent % 10 == 0 and percent != last_logged_pct:
                                log_message(msg)
                                last_logged_pct = percent
            
            try:
                shutil.copystat(src, dest_file)
            except Exception:
                pass
                
            if task_id:
                if callable(task_id):
                    task_id(100, "Übertragung: 100%")
                else:
                    from gui.core.jobs import update_job
                    update_job(task_id, progress=100, message="Übertragung: 100%")
            log_message("Übertragung: 100%")
            return True
            
    except Exception as e:
        log_message(f"❌ Fehler bei Python-Kopier-Fallback von {src} nach {dst}: {e}")
        return False

def run_rsync_with_progress(src, dst, task_id=None, move=False, protect_existing=False):
    import subprocess
    import re
    import shutil
    
    if protect_existing:
        try:
            _quarantine_colliding_files(src, dst)
        except Exception as e:
            log_message(f"❌ Rsync-Vorgang abgebrochen, da das Quarantäne-Sicherheitsnetz fehlgeschlagen ist: {e}")
            return False

    os.makedirs(os.path.dirname(dst) if not os.path.isdir(dst) else dst, exist_ok=True)
    
    cmd = ["rsync", "-a", "--inplace", "--no-owner", "--no-group", get_rsync_progress_flag()]
    src_path = src
    if os.path.isdir(src) and not src.endswith('/'):
        src_path += '/'
        
    cmd.extend([src_path, dst])
    
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0)
    except (FileNotFoundError, OSError) as e:
        log_message(f"rsync konnte nicht gestartet werden ({e}). Verwende Python-Kopier-Fallback...")
        success = run_copy_fallback(src, dst, task_id, protect_existing=protect_existing)
        if success and move:
            import gui.core.trash as trash
            try:
                trash.send_to_trash(src)
            except Exception as tr_err:
                log_message(f"⚠️ Konnte Quellpfad {src} nach Fallback-Move nicht in Quarantäne verschieben: {tr_err}")
        return success
        
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
                    from gui.core.jobs import update_job
                    update_job(task_id, progress=percent, message=msg)
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
                
    if success and move:
        import gui.core.trash as trash
        try:
            trash.send_to_trash(src)
        except trash.TrashError as e:
            log_message(f"⚠️ TrashError für Quellpfad {src}: {e}")
        except Exception as e:
            log_message(f"⚠️ Konnte Quellpfad {src} nach Move nicht in Quarantäne verschieben: {e}")
            
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
                    from gui.core.jobs import update_job
                    update_job(task_id, progress=percent, message=f"Konvertierung: {percent}%")
                        
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
                from gui.core.jobs import update_job
                update_job(task_id, progress=percent, message=f"Download: {percent}%",
                           pipeline_step="metadata", pipeline_status="running", pipeline_progress=percent)
                        
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
                if val:
                    if t_type == "nas" or t_id == "nas" or t_type == "local":
                        root = target.get("root_path", "")
                        if val.startswith(root) and root:
                            return val
                        else:
                            return os.path.join(root, val.lstrip("/"))
                    return val
            # Fallbacks
            if t_type == "nas" or t_id == "nas":
                return os.path.join(target.get("root_path", ""), cat.get("nas_sub", rel_sub).lstrip("/"))
            else:
                return cat.get("pcloud_remote", "")
                
    # 2. Fallback if no sync category matches rel_sub
    if t_type == "nas" or t_id == "nas":
        return os.path.join(target.get("root_path", ""), rel_sub.lstrip("/"))
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

def resolve_category_target_path(destination_id, target_id, media_type="tv"):
    """
    Sucht die Kategorie anhand der destination_id (z. B. Kategorie-ID oder rel_sub)
    und ermittelt über resolve_target_destination den cloud-spezifischen Zielpfad.
    """
    if not destination_id:
        return None

    settings = load_settings()
    sync_cats = settings.get("sync_categories", [])

    # 1. Kategorie über ID oder nas_sub finden
    found_cat = None
    for cat in sync_cats:
        if cat.get("id") == str(destination_id):
            found_cat = cat
            break

    if not found_cat:
        for cat in sync_cats:
            nas_sub = cat.get("nas_sub", "")
            if nas_sub and (nas_sub in str(destination_id)):
                found_cat = cat
                break

    if not found_cat:
        return None

    # 2. Target-Konfiguration holen
    target = next((t for t in settings.get("storage_targets", []) if t.get("id") == target_id), None)
    if not target:
        target = {"id": target_id, "type": "cloud" if target_id == "pcloud" else "local"}

    # 3. Pfad auflösen
    nas_sub = found_cat.get("nas_sub", "")
    return resolve_target_destination(target, nas_sub, media_type)

def copy_to_cloud_target(source_dir, nas_target_dir, target_id, task_id=None, explicit_remote_base=None):
    import shutil
    settings = load_settings()
    nas_target = next((t for t in settings.get("storage_targets", []) if t.get("id") == "nas"), None)
    nas_root = nas_target.get("root_path", "") if nas_target else settings.get("nas_root", "")
    
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
        if ":" in remote_target:
            # Falls remote_target einen Doppelpunkt enthält (z. B. "pcloud:04a_Dokus/Serienname"),
            # spalten wir diesen ab, um einen sauberen lokalen Pfad zu erhalten.
            rel_target = remote_target.split(":", 1)[1].lstrip("/")
            clean_remote_target = os.path.join(pcloud_local, rel_target)
        elif prefix and ":" in prefix:
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
            
        cmd = ["rclone", "copy", source_dir, remote_target, "--transfers", "2", "--retries", "1", "--stats", "1s", "--stats-one-line"]
        rclone_pattern = re.compile(r'(\d+)%,')
        speed_pattern = re.compile(r'(\d+\.?\d*\s*[kKMG]i?B/s)')
        
        last_logged_pct = [-1]
        def handle_line(line):
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
                        from gui.core.jobs import update_job
                        update_job(task_id, progress=percent, message=msg)
                if percent % 10 == 0 and percent != last_logged_pct[0]:
                    log_message(msg)
                    last_logged_pct[0] = percent

        success = run_with_retries_and_timeout(
            cmd, 
            max_attempts=3, 
            timeout_sec=3600, # 1h default timeout for an upload, rclone might hang due to network
            line_callback=handle_line
        )
        if success:
            log_message(f"✅ {target_name}: Rclone-Upload abgeschlossen nach {remote_target}")
            return True
        else:
            log_message(f"❌ {target_name} Rclone-Upload fehlgeschlagen nach allen Retrys.")
            
    return False

def copy_to_pcloud(source_dir, nas_target_dir, task_id=None, explicit_remote_base=None):
    return copy_to_cloud_target(source_dir, nas_target_dir, "pcloud", task_id, explicit_remote_base)


def walk_nas_categories(settings=None, category_ids=None):
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
    nas_root = settings.get("nas_root", "")
    if not nas_root:
        return
    sync_cats = settings.get("sync_categories", [])

    def looks_like_season(entry_name):
        low = entry_name.lower()
        return low.startswith("staffel ") or low.startswith("season ") or low.startswith("specials")

    # Normalize category_ids to a set of strings if provided
    filter_cats = None
    if category_ids is not None:
        if isinstance(category_ids, str):
            filter_cats = {x.strip() for x in category_ids.split(",") if x.strip()}
        elif isinstance(category_ids, (list, tuple, set)):
            filter_cats = {str(x) for x in category_ids}
        else:
            filter_cats = {str(category_ids)}
        
        # If the set is empty, treat as None (no filtering)
        if not filter_cats:
            filter_cats = None

    for cat in sync_cats:
        cat_id = cat.get("id")
        if filter_cats is not None and str(cat_id) not in filter_cats:
            continue
            
        nas_sub = cat.get("nas_sub")
        if not nas_sub or not nas_root:
            continue
        cat_path = os.path.join(nas_root, nas_sub.lstrip("/"))
        if not os.path.isdir(cat_path):
            continue

        cat_name = cat.get("name", "")
        # Kategorie-Typ: Name enthält "serie" -> Serien-Kategorie
        cat_is_series = "serie" in cat_name.lower()

        try:
            entries = sorted(os.listdir(cat_path))
        except OSError as e:
            log_message(f"⚠️ [Bibliothek-Scan] Kategorie-Ordner nicht lesbar: {cat_path} ({e})")
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
                except OSError as e:
                    log_message(f"⚠️ [Bibliothek-Scan] Typ-Erkennung nicht möglich für {show_path}: {e}")

            yield {
                "category": cat_name,
                "category_id": cat.get("id"),
                "type": item_type,
                "name": entry,
                "path": show_path,
            }
