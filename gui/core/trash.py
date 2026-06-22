import os
import shutil
import time
import re
import threading
from gui.core.utils import get_allowed_roots

class TrashError(Exception):
    """Exception raised for errors during safe deletion/trash operations."""
    pass

# Global cleanup status kept in RAM
TRASH_CLEANUP_STATUS = {
    "running": False,
    "started_at": None,
    "finished_at": None,
    "deleted_count": 0,
    "error_count": 0,
    "last_error": None,
    "dry_run": False
}

_cleanup_lock = threading.Lock()

# Cache variable for trash stats to prevent Flask hang-ups
_cached_trash_stats = {
    "bytes": 0,
    "count": 0,
    "last_check": 0
}

def _get_mount_point(path: str) -> str:
    real_path = os.path.realpath(path)
    current_dir = os.path.dirname(real_path) if os.path.isfile(real_path) else real_path
    try:
        target_st_dev = os.stat(current_dir).st_dev
    except Exception as e:
        raise TrashError(f"Kann stat auf {current_dir} nicht ausführen: {e}")
        
    mount_point = current_dir
    while True:
        parent = os.path.dirname(mount_point)
        if parent == mount_point: # Root reached
            break
        try:
            if os.stat(parent).st_dev != target_st_dev:
                break
        except Exception:
            break
        mount_point = parent
    return mount_point

def send_to_trash(filepath: str, force: bool = False) -> bool:
    if not os.path.exists(filepath):
        return True # Already gone
        
    real_path = os.path.realpath(filepath)
    
    # 1. Guard check for NAS metadata files if not forced
    if not force:
        from gui.core.utils import load_settings
        settings = load_settings()
        nas = settings.get("nas_root")
        if nas:
            nas_real = os.path.realpath(nas)
            is_under_nas = False
            try:
                is_under_nas = (os.path.commonpath([real_path, nas_real]) == nas_real)
            except ValueError:
                pass
            
            if is_under_nas and os.path.basename(real_path).lower() in ("tvshow.nfo", "season.nfo"):
                import traceback
                from gui.core.helpers import log_message
                tb_str = "".join(traceback.format_stack()[:-1])
                log_message(f"🚨 BLOCKIERTE LÖSCHUNG auf NAS: {filepath} (force=False)\nStacktrace:\n{tb_str}")
                raise TrashError(f"Löschen von Metadaten-Datei '{os.path.basename(real_path)}' auf dem NAS wurde blockiert, da force=False.")
    
    # Prevent deleting the quarantine directory itself
    if ".medienwerkzeug-trash" in real_path.split(os.sep):
        raise TrashError(f"Löschen des Quarantäne-Ordners oder seiner Inhalte ist nicht direkt erlaubt: {filepath}")
 
    # Boundary Check
    allowed_roots = get_allowed_roots()
    is_allowed = False
    for root in allowed_roots:
        try:
            if os.path.commonpath([real_path, root]) == root:
                is_allowed = True
                break
        except ValueError:
            pass
            
    if not is_allowed:
        raise TrashError(f"Der Pfad {filepath} liegt außerhalb der erlaubten Lösch-Zonen.")
        
    from gui.core.utils import get_runtime_capabilities
    caps = get_runtime_capabilities()
    
    if caps.get("runtime") != "docker":
        # Desktop: native send2trash
        try:
            import send2trash
            send2trash.send2trash(real_path)
            return True
        except ImportError:
            raise TrashError("Die Bibliothek send2trash ist nicht installiert.")
        except Exception as e:
            raise TrashError(f"Nativer Papierkorb-Fehler: {e}")
            
    else:
        # Docker: Quarantine folder relative to mountpoint
        try:
            mount_point = _get_mount_point(real_path)
        except Exception as e:
            raise TrashError(str(e))
            
        if mount_point == "/":
            raise TrashError(f"Kein spezifischer Mountpoint für {filepath} gefunden. Fallback auf '/' verboten.")
            
        trash_dir = os.path.join(mount_point, ".medienwerkzeug-trash")
        
        try:
            os.makedirs(trash_dir, exist_ok=True)
            if not os.access(trash_dir, os.W_OK):
                raise TrashError(f"Quarantäne-Ordner {trash_dir} ist nicht beschreibbar.")
        except Exception as e:
            raise TrashError(f"Kann Quarantäne-Ordner auf Mountpoint {mount_point} nicht anlegen/prüfen: {e}")
            
        # Structure the quarantine path: YYYY-MM-DD_HH-MM-SS/ParentDirName/Basename
        timestamp_folder = time.strftime("%Y-%m-%d_%H-%M-%S")
        parent_dir_name = os.path.basename(os.path.dirname(real_path))
        if not parent_dir_name:
            parent_dir_name = "root"
            
        target_parent_dir = os.path.join(trash_dir, timestamp_folder, parent_dir_name)
        try:
            os.makedirs(target_parent_dir, exist_ok=True)
        except Exception as e:
            raise TrashError(f"Kann Ziel-Quarantäne-Unterordner {target_parent_dir} nicht anlegen: {e}")
            
        basename = os.path.basename(real_path)
        dest_path = os.path.join(target_parent_dir, basename)
        
        if os.path.exists(dest_path):
            name, ext = os.path.splitext(basename)
            counter = 1
            while True:
                candidate = os.path.join(target_parent_dir, f"{name}_{counter}{ext}")
                if not os.path.exists(candidate):
                    dest_path = candidate
                    break
                counter += 1
            
        try:
            shutil.move(real_path, dest_path)
            return True
        except Exception as e:
            raise TrashError(f"Verschieben in den Quarantäne-Ordner fehlgeschlagen: {e}")

def get_trash_dirs():
    allowed_roots = get_allowed_roots()
    trash_dirs = set()
    for root in allowed_roots:
        if not os.path.exists(root):
            continue
        try:
            mount_point = _get_mount_point(root)
            if mount_point != "/":
                trash_dir = os.path.join(mount_point, ".medienwerkzeug-trash")
                if os.path.exists(trash_dir) and os.path.isdir(trash_dir):
                    trash_dirs.add(os.path.realpath(trash_dir))
        except Exception:
            pass
    return list(trash_dirs)

def get_trash_stats(force_refresh=False):
    global _cached_trash_stats
    
    # Return cache if fresh enough and not forced
    if not force_refresh and time.time() - _cached_trash_stats["last_check"] < 60:
        return {
            "bytes": _cached_trash_stats["bytes"],
            "count": _cached_trash_stats["count"]
        }
        
    total_bytes = 0
    total_files = 0
    trash_dirs = get_trash_dirs()
    
    # Delay import to avoid circular dependencies
    from gui.workers.processor import _run_storage_probe
    for trash_dir in trash_dirs:
        res, timed_out = _run_storage_probe("trash_stats", trash_dir, timeout_sec=10)
        if res and not timed_out:
            total_bytes += res.get("bytes", 0)
            total_files += res.get("count", 0)
            
    _cached_trash_stats = {
        "bytes": total_bytes,
        "count": total_files,
        "last_check": time.time()
    }
    
    return {
        "bytes": total_bytes,
        "count": total_files
    }

def empty_trash_async(retention_days=None, dry_run=False):
    global TRASH_CLEANUP_STATUS
    
    # Concurrency check
    if TRASH_CLEANUP_STATUS["running"]:
        raise TrashError("Ein Quarantäne-Bereinigungsprozess läuft bereits.")
        
    if retention_days is None:
        from gui.core.persistence import load_settings
        settings = load_settings()
        retention_days = int(settings.get("trash_retention_days", 7))
        
    if dry_run:
        # Dry-run is executed synchronously since it's just a scan
        deleted, errors = _empty_trash_core(retention_days, dry_run=True)
        return {"status": "dry_run_results", "deleted": deleted, "errors": errors}
    else:
        # Async execution in background thread
        with _cleanup_lock:
            TRASH_CLEANUP_STATUS["running"] = True
            TRASH_CLEANUP_STATUS["started_at"] = time.time()
            TRASH_CLEANUP_STATUS["finished_at"] = None
            TRASH_CLEANUP_STATUS["deleted_count"] = 0
            TRASH_CLEANUP_STATUS["error_count"] = 0
            TRASH_CLEANUP_STATUS["last_error"] = None
            TRASH_CLEANUP_STATUS["dry_run"] = False
        
        t = threading.Thread(target=_empty_trash_thread_run, args=(retention_days,))
        t.daemon = True
        t.start()
        return {"status": "started"}

def _empty_trash_thread_run(retention_days):
    global TRASH_CLEANUP_STATUS
    try:
        deleted, errors = _empty_trash_core(retention_days, dry_run=False)
        with _cleanup_lock:
            TRASH_CLEANUP_STATUS["deleted_count"] = len(deleted)
            TRASH_CLEANUP_STATUS["error_count"] = len(errors)
            if errors:
                TRASH_CLEANUP_STATUS["last_error"] = f"{len(errors)} Fehler aufgetreten. Erster Fehler: {errors[0][1]}"
    except Exception as e:
        with _cleanup_lock:
            TRASH_CLEANUP_STATUS["last_error"] = str(e)
            TRASH_CLEANUP_STATUS["error_count"] = 1
    finally:
        with _cleanup_lock:
            TRASH_CLEANUP_STATUS["finished_at"] = time.time()
            TRASH_CLEANUP_STATUS["running"] = False
        try:
            get_trash_stats(force_refresh=True)
        except Exception:
            pass

def _empty_trash_core(retention_days, dry_run=False):
    import datetime
    deleted_paths = []
    errors = []
    
    trash_dirs = get_trash_dirs()
    timestamp_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$")
    
    for trash_dir in trash_dirs:
        # Write permission pre-test
        if not dry_run:
            test_file = os.path.join(trash_dir, f".write_test_{int(time.time())}")
            try:
                with open(test_file, "w") as f:
                    f.write("test")
                os.remove(test_file)
            except Exception as e:
                errors.append((trash_dir, f"Schreibtest in {trash_dir} fehlgeschlagen: {e}"))
                continue
                
        try:
            subdirs = os.listdir(trash_dir)
        except Exception as e:
            errors.append((trash_dir, f"Kann Inhalt von {trash_dir} nicht auflisten: {e}"))
            continue
            
        for name in subdirs:
            if not timestamp_pattern.match(name):
                continue
                
            subdir_path = os.path.join(trash_dir, name)
            
            # Parse folder timestamp to determine age
            try:
                dt = datetime.datetime.strptime(name, "%Y-%m-%d_%H-%M-%S")
                age_days = (datetime.datetime.now() - dt).total_seconds() / 86400.0
            except Exception:
                continue
                
            if age_days < retention_days:
                continue
                
            # Secure deletion walkthrough
            try:
                items_to_delete = []
                for root, dirs, files in os.walk(subdir_path, followlinks=False):
                    for d in dirs:
                        full_p = os.path.join(root, d)
                        items_to_delete.append((full_p, True if os.path.islink(full_p) else False))
                    for f in files:
                        full_p = os.path.join(root, f)
                        items_to_delete.append((full_p, True if os.path.islink(full_p) else False))
                
                # Include the timestamp folder itself
                items_to_delete.append((subdir_path, False))
                
                # Sort longest paths first (delete files/subfolders before parents)
                items_to_delete.sort(key=lambda x: len(x[0]), reverse=True)
                
                for item_path, is_symlink in items_to_delete:
                    # Security boundary check (must lie inside the trash dir root)
                    abs_item = os.path.abspath(item_path)
                    abs_trash = os.path.abspath(trash_dir)
                    
                    try:
                        if os.path.commonpath([abs_item, abs_trash]) != abs_trash or abs_item == abs_trash:
                            errors.append((item_path, "Sicherheits-Check fehlgeschlagen: Pfad liegt außerhalb des Trash-Ordners."))
                            continue
                    except ValueError:
                        errors.append((item_path, "Sicherheits-Check fehlgeschlagen: Pfad-Partitionen weichen ab."))
                        continue
                        
                    if dry_run:
                        deleted_paths.append(item_path)
                    else:
                        try:
                            if is_symlink or os.path.islink(item_path):
                                os.unlink(item_path)
                            elif os.path.isdir(item_path):
                                try:
                                    os.rmdir(item_path)
                                except OSError:
                                    shutil.rmtree(item_path)
                            else:
                                os.remove(item_path)
                            deleted_paths.append(item_path)
                        except Exception as e:
                            errors.append((item_path, str(e)))
            except Exception as e:
                errors.append((subdir_path, f"Fehler beim Traversieren von {subdir_path}: {e}"))
                
    return deleted_paths, errors


