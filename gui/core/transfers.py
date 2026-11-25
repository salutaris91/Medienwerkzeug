from gui.core.utils import load_settings, save_settings, get_runtime_capabilities
import os, socket, subprocess, time, shutil
from collections import deque
from urllib.parse import quote
from gui.core.helpers import *
from gui.core.resilience import run_with_retries_and_timeout
import gui.core.media as media

_rsync_progress_flag = None

def _is_nas_root_mounted(nas_root):
    if not nas_root:
        return False
    try:
        target_path = os.path.realpath(os.path.abspath(nas_root))
        out = subprocess.check_output(["mount"], text=True)
        for line in out.splitlines():
            if " on " in line:
                parts = line.split(" on ", 1)
                if len(parts) >= 2:
                    m_point = parts[1].split(" (", 1)[0].strip()
                    m_point_norm = os.path.realpath(os.path.abspath(m_point))
                    if target_path == m_point_norm or target_path.startswith(m_point_norm + "/"):
                        if os.path.isdir(target_path):
                            return True

        # Suffix-Prüfung (/Volumes/<Share>-1)
        if target_path.startswith("/Volumes/"):
            parts = target_path.split("/")
            if len(parts) >= 3:
                share_name = parts[2]
                for line in out.splitlines():
                    if " on " in line:
                        parts_m = line.split(" on ", 1)
                        if len(parts_m) >= 2:
                            m_point = parts_m[1].split(" (", 1)[0].strip()
                            m_point_norm = os.path.realpath(os.path.abspath(m_point))
                            if m_point_norm.startswith(f"/Volumes/{share_name}-"):
                                suffix_part = m_point_norm[len(f"/Volumes/{share_name}-"):]
                                if suffix_part.isdigit():
                                    relative_part = target_path[len(f"/Volumes/{share_name}"):]
                                    actual_target_path = m_point_norm + relative_part
                                    if os.path.isdir(actual_target_path):
                                        return True
    except Exception as e:
        log_message(f"❌ NAS-Mount-Status konnte nicht gelesen werden: {e}")
    return False

def diagnose_nas_mount(nas_root):
    if not nas_root:
        return 'not_mounted', "Kein Pfad konfiguriert."
    target_path = os.path.realpath(os.path.abspath(nas_root))
    try:
        out = subprocess.check_output(["mount"], text=True)
    except Exception as e:
        return 'not_mounted', f"Fehler beim Lesen der Mount-Tabelle: {e}"

    mountpoints = []
    for line in out.splitlines():
        if " on " in line:
            parts = line.split(" on ", 1)
            if len(parts) >= 2:
                m_point = parts[1].split(" (", 1)[0].strip()
                mountpoints.append(os.path.realpath(os.path.abspath(m_point)))

    for m_point in mountpoints:
        if target_path == m_point or target_path.startswith(m_point + "/"):
            if os.path.isdir(target_path):
                return 'connected', None
            else:
                return 'path_not_found', f"Das NAS-Laufwerk ist eingebunden, aber der konfigurierte Ordner '{nas_root}' existiert nicht auf dem Volume."

    if target_path.startswith("/Volumes/"):
        parts = target_path.split("/")
        if len(parts) >= 3:
            share_name = parts[2]
            for m_point in mountpoints:
                if m_point.startswith(f"/Volumes/{share_name}-"):
                    suffix_part = m_point[len(f"/Volumes/{share_name}-"):]
                    if suffix_part.isdigit():
                        relative_part = target_path[len(f"/Volumes/{share_name}"):]
                        actual_target_path = m_point + relative_part
                        if os.path.isdir(actual_target_path):
                            return 'mount_conflict_suffix', f"Das NAS wurde erfolgreich eingebunden, aber macOS hat es unter '{m_point}' (statt '/Volumes/{share_name}') gemountet. Bitte passe den Pfad in den Einstellungen entsprechend an."
                        else:
                            return 'path_not_found', f"Das NAS wurde unter '{m_point}' gemountet, aber der Ordner '{relative_part.lstrip('/')}' existiert dort nicht."

    return 'not_mounted', "Das NAS ist erreichbar, konnte aber nicht eingebunden werden. Bitte prüfe die SMB-Zugangsdaten im macOS-Schlüsselbund."

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
    details = check_nas_connection_details()
    return details["status"]

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
            status = "connected"
            error_message = None
            try:
                if not os.access(nas_root, os.R_OK):
                    status = "offline"
                    error_message = f"Einhängepfad '{nas_root}' ist nicht lesbar."
                else:
                    sync_cats = settings.get("sync_categories", [])
                    if not sync_cats:
                        status = "connected_but_no_library_paths"
                        error_message = "Keine Sync-Kategorien konfiguriert."
                    else:
                        valid_paths = 0
                        missing_paths = []
                        for cat in sync_cats:
                            nas_sub = cat.get("nas_sub")
                            if not nas_sub:
                                continue
                            cat_path = os.path.join(nas_root, nas_sub.lstrip("/"))
                            if os.path.isdir(cat_path) and os.access(cat_path, os.R_OK):
                                valid_paths += 1
                            else:
                                missing_paths.append(nas_sub)

                        if valid_paths == 0:
                            status = "connected_but_no_library_paths"
                            if missing_paths:
                                error_message = f"Keiner der Kategoriepfade existiert oder ist lesbar (fehlt: {', '.join(missing_paths)})."
                            else:
                                error_message = "Keiner der Kategoriepfade ist lesbar oder konfiguriert."
            except Exception as e:
                status = "offline"
                error_message = f"Fehler bei der Lesbarkeitsprüfung von nas_root: {e}"

            return {
                "status": status,
                "enabled": nas_enabled,
                "has_root": has_root,
                "checked_ips": [],
                "reachable_ip": None,
                "ip_details": [],
                "error_message": error_message
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

        # Härtungsprüfung für "connected"
        try:
            if not os.path.isdir(nas_root) or not os.access(nas_root, os.R_OK):
                status = "offline"
                error_message = f"Einhängepfad '{nas_root}' ist nicht lesbar oder kein Verzeichnis."
            else:
                sync_cats = settings.get("sync_categories", [])
                if not sync_cats:
                    status = "connected_but_no_library_paths"
                    error_message = "Keine Sync-Kategorien konfiguriert."
                else:
                    valid_paths = 0
                    missing_paths = []
                    for cat in sync_cats:
                        nas_sub = cat.get("nas_sub")
                        if not nas_sub:
                            continue
                        cat_path = os.path.join(nas_root, nas_sub.lstrip("/"))
                        if os.path.isdir(cat_path) and os.access(cat_path, os.R_OK):
                            valid_paths += 1
                        else:
                            missing_paths.append(nas_sub)

                    if valid_paths == 0:
                        status = "connected_but_no_library_paths"
                        if missing_paths:
                            error_message = f"Keiner der Kategoriepfade existiert oder ist lesbar (fehlt: {', '.join(missing_paths)})."
                        else:
                            error_message = "Keiner der Kategoriepfade ist lesbar oder konfiguriert."
        except Exception as e:
            status = "offline"
            error_message = f"Fehler bei der Lesbarkeitsprüfung von nas_root: {e}"
    elif reachable_ip:
        status = "available_not_mounted"
        diag_status, diag_msg = diagnose_nas_mount(nas_root)
        error_message = diag_msg
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
    if status in ["connected", "connected_but_no_library_paths"]:
        return True

    if status == "offline":
        try:
            log_message("🌐 Starte Tailscale...")
            subprocess.run(["tailscale", "up"], capture_output=True, timeout=5)
            status = check_nas_status()
        except Exception as e:
            log_message(f"⚠️ Tailscale-Start fehlgeschlagen: {e}")

    if status in ["connected", "connected_but_no_library_paths"]:
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

        finder_host = chosen_ip
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

def _makedirs_tracked(target_dir, created_dirs):
    if not target_dir:
        return
    norm = os.path.abspath(target_dir)
    missing = []
    cur = norm
    while cur and not os.path.exists(cur):
        missing.append(cur)
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    for d in reversed(missing):
        os.makedirs(d, exist_ok=True)
        if d not in created_dirs:
            created_dirs.append(d)


def run_copy_fallback(src, dst, task_id=None, protect_existing=False):
    import shutil
    import os
    import threading
    from gui.core.jobs import (
        JobCancelledError,
        check_cancelled,
        resolve_job_id,
        wait_if_paused_or_cancelled,
    )

    job_id = resolve_job_id(task_id)
    wait_if_paused_or_cancelled(job_id)

    log_message(f"rsync nicht verfügbar. Verwende Python-Fallback zum Kopieren von {src} nach {dst}...")
    if protect_existing:
        try:
            _quarantine_colliding_files(src, dst)
        except JobCancelledError:
            raise
        except Exception as e:
            log_message(f"❌ Kopiervorgang abgebrochen, da das Quarantäne-Sicherheitsnetz fehlgeschlagen ist: {e}")
            return False

    created_dirs = []
    created_files = []
    current_tmp_path = None

    def _cleanup_cancelled():
        nonlocal current_tmp_path
        if current_tmp_path and os.path.lexists(current_tmp_path):
            try:
                os.unlink(current_tmp_path)
            except OSError:
                pass
            current_tmp_path = None
        for fp in reversed(created_files):
            try:
                if os.path.isdir(fp) and not os.path.islink(fp):
                    shutil.rmtree(fp, ignore_errors=True)
                elif os.path.lexists(fp):
                    os.unlink(fp)
            except OSError:
                pass
        for dp in reversed(created_dirs):
            try:
                os.rmdir(dp)
            except OSError:
                pass

    try:
        # Determine if we are copying a directory or a file
        if os.path.isdir(src):
            # Target should be the destination directory (mirroring contents of src)
            _makedirs_tracked(dst, created_dirs)

            # Find all files/symlinks to copy recursively to calculate total size
            files_to_copy = []
            total_size = 0

            for root, dirs, files in os.walk(src):
                # Handle directory symlinks and modify dirs in-place to prevent recursing
                for d in list(dirs):
                    dir_path = os.path.join(root, d)
                    dest_dir = os.path.join(dst, os.path.relpath(dir_path, src))
                    if os.path.islink(dir_path):
                        existed_before = os.path.lexists(dest_dir)
                        if existed_before:
                            if os.path.isdir(dest_dir) and not os.path.islink(dest_dir):
                                shutil.rmtree(dest_dir)
                            else:
                                os.remove(dest_dir)
                        os.symlink(os.readlink(dir_path), dest_dir)
                        if not existed_before:
                            created_files.append(dest_dir)
                        dirs.remove(d)  # Prevent os.walk from entering this directory
                    else:
                        _makedirs_tracked(dest_dir, created_dirs)

                for f in files:
                    filepath = os.path.join(root, f)
                    relpath = os.path.relpath(filepath, src)
                    if os.path.islink(filepath):
                        files_to_copy.append((filepath, relpath, 0, True))
                    else:
                        size = os.path.getsize(filepath)
                        files_to_copy.append((filepath, relpath, size, False))
                        total_size += size

            copied_size = 0
            if not files_to_copy:
                check_cancelled(job_id)
                if task_id:
                    if callable(task_id):
                        task_id(100, "Übertragung: 100%")
                    else:
                        from gui.core.jobs import update_job
                        update_job(task_id, progress=100, message="Übertragung: 100%")
                return True

            last_logged_pct = -1
            for filepath, relpath, size, is_symlink in files_to_copy:
                wait_if_paused_or_cancelled(job_id)
                dest_filepath = os.path.join(dst, relpath)
                _makedirs_tracked(os.path.dirname(dest_filepath), created_dirs)
                existed_before = os.path.lexists(dest_filepath)

                if is_symlink:
                    if existed_before:
                        if os.path.isdir(dest_filepath) and not os.path.islink(dest_filepath):
                            shutil.rmtree(dest_filepath)
                        else:
                            os.remove(dest_filepath)
                    os.symlink(os.readlink(filepath), dest_filepath)
                    if not existed_before:
                        created_files.append(dest_filepath)
                else:
                    # Write to sibling temporary file first so pre-existing destination content is never truncated
                    tmp_path = f"{dest_filepath}.mwtmp.{os.getpid()}.{threading.get_ident()}"
                    current_tmp_path = tmp_path
                    with open(filepath, 'rb') as fsrc:
                        with open(tmp_path, 'wb') as fdst:
                            while True:
                                wait_if_paused_or_cancelled(job_id)
                                buf = fsrc.read(1024 * 1024)  # 1MB chunk
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
                                    if percent % 10 == 0 and percent != last_logged_pct:
                                        log_message(msg)
                                        last_logged_pct = percent

                    try:
                        shutil.copystat(filepath, tmp_path)
                    except Exception:
                        pass

                    check_cancelled(job_id)
                    os.replace(tmp_path, dest_filepath)
                    current_tmp_path = None
                    if not existed_before:
                        created_files.append(dest_filepath)

            check_cancelled(job_id)
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
            if os.path.isdir(dst) or dst.endswith("/") or dst.endswith(os.sep):
                _makedirs_tracked(dst, created_dirs)
                dest_file = os.path.join(dst, os.path.basename(src))
            else:
                dest_dir = os.path.dirname(dst)
                if dest_dir:
                    _makedirs_tracked(dest_dir, created_dirs)

            existed_before = os.path.lexists(dest_file)

            if os.path.islink(src):
                check_cancelled(job_id)
                if existed_before:
                    if os.path.isdir(dest_file) and not os.path.islink(dest_file):
                        shutil.rmtree(dest_file)
                    else:
                        os.remove(dest_file)
                os.symlink(os.readlink(src), dest_file)
                if not existed_before:
                    created_files.append(dest_file)
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

            tmp_path = f"{dest_file}.mwtmp.{os.getpid()}.{threading.get_ident()}"
            current_tmp_path = tmp_path

            with open(src, 'rb') as fsrc:
                with open(tmp_path, 'wb') as fdst:
                    while True:
                        wait_if_paused_or_cancelled(job_id)
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
                            if percent % 10 == 0 and percent != last_logged_pct:
                                log_message(msg)
                                last_logged_pct = percent

            try:
                shutil.copystat(src, tmp_path)
            except Exception:
                pass

            check_cancelled(job_id)
            os.replace(tmp_path, dest_file)
            current_tmp_path = None
            if not existed_before:
                created_files.append(dest_file)

            if task_id:
                if callable(task_id):
                    task_id(100, "Übertragung: 100%")
                else:
                    from gui.core.jobs import update_job
                    update_job(task_id, progress=100, message="Übertragung: 100%")
            log_message("Übertragung: 100%")
            return True

    except JobCancelledError:
        _cleanup_cancelled()
        raise
    except Exception as e:
        if current_tmp_path and os.path.lexists(current_tmp_path):
            try:
                os.unlink(current_tmp_path)
            except OSError:
                pass
        log_message(f"❌ Fehler bei Python-Kopier-Fallback von {src} nach {dst}: {e}")
        return False


def run_rsync_with_progress(src, dst, task_id=None, move=False, protect_existing=False):
    import subprocess
    import re
    import shutil
    from gui.core.jobs import (
        JobCancelledError,
        check_cancelled,
        is_job_cancelled,
        register_job_process,
        resolve_job_id,
        unregister_job_process,
        wait_if_paused_or_cancelled,
    )

    job_id = resolve_job_id(task_id)
    wait_if_paused_or_cancelled(job_id)

    if protect_existing:
        try:
            _quarantine_colliding_files(src, dst)
        except JobCancelledError:
            raise
        except Exception as e:
            log_message(f"❌ Rsync-Vorgang abgebrochen, da das Quarantäne-Sicherheitsnetz fehlgeschlagen ist: {e}")
            return False

    src_is_dir = os.path.isdir(src)
    created_dirs = []
    dst_dir_existed_before = False
    existing_rel_files = set()
    existing_rel_dirs = set()
    dest_file = None
    dest_file_existed_before = False
    dest_parent_dir = None
    parent_entries_before = set()

    if src_is_dir:
        dst_dir_existed_before = os.path.exists(dst)
        if dst_dir_existed_before:
            for r, ds, fs in os.walk(dst):
                for d in ds:
                    existing_rel_dirs.add(os.path.relpath(os.path.join(r, d), dst))
                for f in fs:
                    existing_rel_files.add(os.path.relpath(os.path.join(r, f), dst))
        has_preexisting_target = bool(existing_rel_files)
        _makedirs_tracked(dst, created_dirs)
    else:
        dst_is_dir_target = os.path.isdir(dst) or dst.endswith("/") or dst.endswith(os.sep)
        dest_file = os.path.join(dst, os.path.basename(src)) if dst_is_dir_target else dst
        dest_file_existed_before = os.path.lexists(dest_file)
        dest_parent_dir = dst if dst_is_dir_target else os.path.dirname(os.path.abspath(dst))
        if dest_parent_dir and os.path.isdir(dest_parent_dir):
            parent_entries_before = set(os.listdir(dest_parent_dir))
        has_preexisting_target = dest_file_existed_before
        _makedirs_tracked(dest_parent_dir, created_dirs)

    def _cleanup_cancelled_rsync():
        if src_is_dir:
            if not dst_dir_existed_before:
                if os.path.exists(dst):
                    shutil.rmtree(dst, ignore_errors=True)
                for dp in reversed(created_dirs):
                    try:
                        os.rmdir(dp)
                    except OSError:
                        pass
            else:
                for r, ds, fs in os.walk(dst, topdown=False):
                    for f in fs:
                        full_f = os.path.join(r, f)
                        rel_f = os.path.relpath(full_f, dst)
                        if rel_f not in existing_rel_files:
                            try:
                                os.unlink(full_f)
                            except OSError:
                                pass
                    for d in ds:
                        full_d = os.path.join(r, d)
                        rel_d = os.path.relpath(full_d, dst)
                        if rel_d not in existing_rel_dirs:
                            try:
                                os.rmdir(full_d)
                            except OSError:
                                pass
        else:
            if not dest_file_existed_before and dest_file and os.path.lexists(dest_file):
                try:
                    os.unlink(dest_file)
                except OSError:
                    pass
            if dest_parent_dir and os.path.isdir(dest_parent_dir) and dest_file:
                base_name = os.path.basename(dest_file)
                for entry in os.listdir(dest_parent_dir):
                    if entry not in parent_entries_before and entry.startswith(f".{base_name}."):
                        try:
                            os.unlink(os.path.join(dest_parent_dir, entry))
                        except OSError:
                            pass
            for dp in reversed(created_dirs):
                try:
                    os.rmdir(dp)
                except OSError:
                    pass

    cmd = ["rsync", "-a"]
    if not (has_preexisting_target and not protect_existing):
        cmd.append("--inplace")
    cmd.extend(["--no-owner", "--no-group", get_rsync_progress_flag()])
    src_path = src
    if src_is_dir and not src.endswith('/'):
        src_path += '/'

    cmd.extend([src_path, dst])

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
            start_new_session=(os.name != 'nt'),
        )
    except (FileNotFoundError, OSError) as e:
        for dp in reversed(created_dirs):
            try:
                os.rmdir(dp)
            except OSError:
                pass
        log_message(f"rsync konnte nicht gestartet werden ({e}). Verwende Python-Kopier-Fallback...")
        success = run_copy_fallback(src, dst, task_id, protect_existing=False)
        check_cancelled(job_id)
        if success and move:
            import gui.core.trash as trash
            try:
                trash.send_to_trash(src)
            except Exception as tr_err:
                log_message(f"⚠️ Konnte Quellpfad {src} nach Fallback-Move nicht in Quarantäne verschieben: {tr_err}")
        return success

    register_job_process(job_id, process)
    progress_pattern = re.compile(r'(\d+)%')
    speed_pattern = re.compile(r'(\d+\.?\d*\s*[kKMG]i?B/s)')

    output_lines = []
    last_logged_pct = -1
    try:
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
                if percent % 10 == 0 and percent != last_logged_pct:
                    log_message(msg)
                    last_logged_pct = percent

        process.wait()
    except JobCancelledError:
        try:
            process.wait(timeout=2)
        except Exception:
            pass
        _cleanup_cancelled_rsync()
        raise
    finally:
        unregister_job_process(job_id, process)

    if is_job_cancelled(job_id):
        _cleanup_cancelled_rsync()
        raise JobCancelledError("Vom Benutzer abgebrochen")

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
    from gui.core.jobs import (
        JobCancelledError,
        is_job_cancelled,
        register_job_process,
        resolve_job_id,
        unregister_job_process,
        wait_if_paused_or_cancelled,
    )

    job_id = resolve_job_id(task_id)
    wait_if_paused_or_cancelled(job_id)

    duration = None
    try:
        duration = media.get_video_duration(filepath)
    except Exception as e:
        log_message(f"Fehler bei get_video_duration: {e}")

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=(os.name != 'nt'),
    )
    register_job_process(job_id, proc)
    time_pattern = re.compile(r'time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})')
    time_pattern_sec = re.compile(r'time=(\d+)\.(\d+)')

    try:
        for line in proc.stdout:
            if log_queue:
                log_queue.put(line)

            if duration and duration > 0:
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

                if current_time is not None:
                    percent = min(99, int((current_time / duration) * 100))
                    if task_id:
                        if callable(task_id):
                            task_id(percent, f"Konvertierung: {percent}%")
                        else:
                            from gui.core.jobs import update_job
                            update_job(task_id, progress=percent, message=f"Konvertierung: {percent}%")

        proc.wait()
    finally:
        unregister_job_process(job_id, proc)

    if is_job_cancelled(job_id):
        raise JobCancelledError("Vom Benutzer abgebrochen")

    return proc.returncode == 0


def run_ytdlp_with_progress(cmd, task_id=None, log_queue=None):
    import subprocess
    import re
    from gui.core.jobs import (
        JobCancelledError,
        is_job_cancelled,
        register_job_process,
        resolve_job_id,
        unregister_job_process,
        wait_if_paused_or_cancelled,
    )

    job_id = resolve_job_id(task_id)
    wait_if_paused_or_cancelled(job_id)

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        start_new_session=(os.name != 'nt'),
    )
    register_job_process(job_id, proc)
    progress_pattern = re.compile(r'\[download\]\s+(\d+(?:\.\d+)?)%')

    try:
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
    finally:
        unregister_job_process(job_id, proc)

    if is_job_cancelled(job_id):
        raise JobCancelledError("Vom Benutzer abgebrochen")

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

_MIN_CLOUD_TIMEOUT_SEC = 3600
_MAX_CLOUD_TIMEOUT_SEC = 172800
_MIN_ASSUMED_UPLOAD_BYTES_PER_SEC = 512 * 1024
_CLOUD_TIMEOUT_BUFFER_SEC = 1800


def _calculate_cloud_upload_timeout_sec(source_path):
    """Berechnet ein größenbasiertes Upload-Timeout (in Sekunden) für rclone-Uploads."""
    if not source_path:
        return _MIN_CLOUD_TIMEOUT_SEC

    total_bytes = 0
    try:
        if not os.path.exists(source_path):
            return _MIN_CLOUD_TIMEOUT_SEC
        if os.path.isfile(source_path) and not os.path.islink(source_path):
            total_bytes = os.path.getsize(source_path)
        elif os.path.isdir(source_path):
            for root, _dirs, files in os.walk(source_path, followlinks=False):
                for fname in files:
                    fp = os.path.join(root, fname)
                    if os.path.islink(fp):
                        continue
                    try:
                        total_bytes += os.path.getsize(fp)
                    except OSError:
                        continue
    except OSError:
        return _MIN_CLOUD_TIMEOUT_SEC

    estimated = int(total_bytes / _MIN_ASSUMED_UPLOAD_BYTES_PER_SEC) + _CLOUD_TIMEOUT_BUFFER_SEC
    return max(_MIN_CLOUD_TIMEOUT_SEC, min(_MAX_CLOUD_TIMEOUT_SEC, estimated))


def copy_to_cloud_target(source_dir, nas_target_dir, target_id, task_id=None, explicit_remote_base=None):
    import shutil
    from gui.core.jobs import JobCancelledError, bind_job_context, resolve_job_id, wait_if_paused_or_cancelled

    job_id = resolve_job_id(task_id)
    wait_if_paused_or_cancelled(job_id)

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
        except JobCancelledError:
            raise
        except Exception as e:
            log_message(f"❌ Fehler bei lokalem Kopieren nach {target_name}: {e}")

    if rclone_remote:
        timeout_sec = _calculate_cloud_upload_timeout_sec(source_dir)
        log_message(f"☁️ {target_name} (rclone Fallback): {remote_target} (Timeout: {timeout_sec}s)")
        if not shutil.which("rclone"):
            log_message("⚠️ Warnung: rclone nicht gefunden. Upload abgebrochen.")
            return False

        cmd = [
            "rclone", "copy", source_dir, remote_target,
            "--transfers", "2",
            "--retries", "1",
            "--stats", "1s",
            "--stats-one-line",
            "--stats-log-level", "NOTICE",
        ]
        rclone_pattern = re.compile(r'(\d+)%,')
        speed_pattern = re.compile(r'(\d+\.?\d*\s*(?:[kKMGTPE]i?)?B/s)')

        last_logged_pct = [-1]
        diag_lines = deque(maxlen=20)
        immediate_error_count = [0]

        def handle_line(line):
            stripped = line.strip()
            if not stripped:
                return
            match = rclone_pattern.search(stripped)
            if match:
                percent = int(match.group(1))
                if percent < last_logged_pct[0]:
                    last_logged_pct[0] = -1
                speed_match = speed_pattern.search(stripped)
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
            else:
                already_logged = False
                if any(sig in stripped for sig in ("ERROR", "CRITICAL", "Failed")):
                    if immediate_error_count[0] < 20:
                        log_message(f"   rclone: {stripped}")
                        immediate_error_count[0] += 1
                        already_logged = True
                diag_lines.append((stripped, already_logged))

        with bind_job_context(job_id):
            success = run_with_retries_and_timeout(
                cmd,
                max_attempts=3,
                timeout_sec=timeout_sec,
                line_callback=handle_line,
            )
        if success:
            log_message(f"✅ {target_name}: Rclone-Upload abgeschlossen nach {remote_target}")
            return True
        else:
            log_message(f"❌ {target_name} Rclone-Upload fehlgeschlagen nach allen Retrys.")
            for diag_line, already_logged in diag_lines:
                if not already_logged:
                    log_message(f"   rclone: {diag_line}")

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
        cat_type = cat.get("type")
        if cat_type in ["series", "movie"]:
            cat_is_series = (cat_type == "series")
        else:
            # Zentraler Fallback für ältere/Legacy-Kategorien
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

def parse_nas_input(input_val):
    """Zerlegt eine SMB-Adresse oder einen lokalen Pfad in host, share und root_path."""
    val = input_val.strip()
    while len(val) > 1 and val.endswith("/"):
        val = val[:-1]

    if val.lower().startswith("smb://"):
        val = val[6:]
        parts = val.split("/", 1)
        host = parts[0]
        share = parts[1] if len(parts) > 1 else ""
        root_path = f"/Volumes/{share}" if share else ""
        return {
            "host": host,
            "share": share,
            "root_path": root_path
        }
    elif val.startswith("/"):
        parts = [p for p in val.split("/") if p]
        share = parts[-1] if parts else ""
        return {
            "host": "",
            "share": share,
            "root_path": val
        }
    return {
        "host": "",
        "share": "",
        "root_path": val
    }

def validate_nas_library_preflight(settings):
    """Führt einen einheitlichen Preflight-Check für alle Bibliothekswerkzeuge durch.

    Gibt (success, error_message) zurück.
    """
    nas_target = next((t for t in settings.get("storage_targets", []) if t.get("id") == "nas"), None)
    if not nas_target or not nas_target.get("enabled", True):
        return False, "NAS-Verbindung ist deaktiviert oder nicht konfiguriert."

    nas_root = nas_target.get("root_path", "")
    if not nas_root:
        return False, "NAS-Einhängepfad (Lokaler Pfad) ist nicht konfiguriert."

    is_docker = get_runtime_capabilities()["runtime"] == "docker"
    if is_docker:
        if not os.path.isdir(nas_root) or not os.access(nas_root, os.R_OK):
            return False, f"Einhängepfad '{nas_root}' ist im Docker-Container nicht verfügbar."
    else:
        if not _is_nas_root_mounted(nas_root):
            return False, f"Netzlaufwerk ist nicht eingehängt (Einhängepfad: {nas_root}). Bitte zuerst verbinden."

    sync_cats = settings.get("sync_categories", [])
    if not sync_cats:
        return False, "Keine Sync-Kategorien in den Einstellungen konfiguriert."

    valid_paths = 0
    missing_paths = []
    for cat in sync_cats:
        nas_sub = cat.get("nas_sub")
        if not nas_sub:
            continue
        cat_path = os.path.join(nas_root, nas_sub.lstrip("/"))
        if os.path.isdir(cat_path) and os.access(cat_path, os.R_OK):
            valid_paths += 1
        else:
            missing_paths.append(nas_sub)

    if valid_paths == 0:
        if missing_paths:
            return False, f"Keiner der Kategoriepfade existiert oder ist lesbar auf dem NAS (fehlt: {', '.join(missing_paths)})."
        else:
            return False, "Keiner der Kategoriepfade ist lesbar oder konfiguriert auf dem NAS."

    shows = list(walk_nas_categories(settings))
    if len(shows) == 0:
        return False, "Keine Medienordner (Serien- oder Film-Verzeichnisse) in den Kategoriepfaden auf dem NAS gefunden."

    return True, ""
