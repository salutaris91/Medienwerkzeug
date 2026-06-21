import os
import shutil
import time

class TrashError(Exception):
    """Exception raised for errors during safe deletion/trash operations."""
    pass

def get_allowed_roots():
    from gui.core.utils import load_settings
    settings = load_settings()
    roots = []
    
    inbox = settings.get("inbox_dir")
    if inbox: roots.append(os.path.realpath(inbox))
        
    outbox = settings.get("outbox_dir")
    if outbox: roots.append(os.path.realpath(outbox))
        
    nas = settings.get("nas_root")
    if nas: roots.append(os.path.realpath(nas))
        
    sources = settings.get("import_sources", [])
    for src in sources:
        if isinstance(src, str):
            roots.append(os.path.realpath(src))
        elif isinstance(src, dict):
            path = src.get("path")
            if path: roots.append(os.path.realpath(path))
        
    return [r for r in roots if os.path.exists(r)]

def send_to_trash(filepath: str, force: bool = False) -> bool:
    if not os.path.exists(filepath):
        return True # Bereits weg
        
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
    
    # Verhindere das Löschen des Quarantäne-Ordners selbst
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
        # Desktop: natives send2trash
        try:
            import send2trash
            send2trash.send2trash(real_path)
            return True
        except ImportError:
            raise TrashError("Die Bibliothek send2trash ist nicht installiert.")
        except Exception as e:
            raise TrashError(f"Nativer Papierkorb-Fehler: {e}")
            
    else:
        # Docker: Quarantäne-Ordner
        current_dir = os.path.dirname(real_path) if os.path.isfile(real_path) else real_path
        
        try:
            target_st_dev = os.stat(current_dir).st_dev
        except Exception as e:
            raise TrashError(f"Kann stat auf {current_dir} nicht ausführen: {e}")
            
        mount_point = current_dir
        while True:
            parent = os.path.dirname(mount_point)
            if parent == mount_point: # Root erreicht
                break
            try:
                if os.stat(parent).st_dev != target_st_dev:
                    break
            except Exception:
                break
            mount_point = parent
            
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
            dest_path = os.path.join(target_parent_dir, f"{name}_{int(time.time())}{ext}")
            
        try:
            shutil.move(real_path, dest_path)
            return True
        except Exception as e:
            raise TrashError(f"Verschieben in den Quarantäne-Ordner fehlgeschlagen: {e}")

