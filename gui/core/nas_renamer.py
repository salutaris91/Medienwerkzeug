import os
import json
import re
import time
import shutil
import gui.mw_metadata as mw_metadata
from gui.core.helpers import limit_filename_length, sanitize_filename
import gui.core.trash as trash

TRANSACTIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "rename_transactions")

def _get_show_info_from_nfo(target_folder):
    nfo_path = os.path.join(target_folder, "tvshow.nfo")
    if not os.path.exists(nfo_path):
        return None, None
        
    try:
        with open(nfo_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        m_prov = re.search(r'<mw_provider>(.*?)</mw_provider>', content)
        m_id = re.search(r'<mw_showid>(.*?)</mw_showid>', content)
        if m_prov and m_id:
            return m_prov.group(1).strip(), m_id.group(1).strip()
            
        m_tvdb = re.search(r'<tvdbid>(.*?)</tvdbid>', content)
        if m_tvdb:
            return "tvdb", m_tvdb.group(1).strip()
            
        m_tmdb = re.search(r'<tmdbid>(.*?)</tmdbid>', content)
        if m_tmdb:
            return "tmdb_tv", m_tmdb.group(1).strip()
            
    except Exception as e:
        print(f"[NAS Renamer] Error reading {nfo_path}: {e}")
        
    return None, None

def _guess_season_from_folder(folder_name):
    # e.g., "Staffel 02", "Season 1", "Specials"
    if folder_name.lower() == "specials":
        return 0
    m = re.search(r'(?:staffel|season)\s*(\d+)', folder_name, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return None

def _parse_episode_from_filename(filename, season=None):
    # Matches S01E02, s1e2, 01x02
    m = re.search(r's(\d{1,2})e(\d{1,3})', filename, re.IGNORECASE)
    if m:
        return int(m.group(1)), int(m.group(2))
    
    m2 = re.search(r'(?<!\d)(\d{1,2})x(\d{1,3})(?!\d)', filename, re.IGNORECASE)
    if m2:
        return int(m2.group(1)), int(m2.group(2))
        
    # If season is known (e.g. from folder), look for standalone episode numbers
    if season is not None:
        if season == 1:
            # Maybe absolute number format "Show - 01 - Title"
            m3 = re.search(r'\s-\s(\d{2,3})(?:\s|-|\.)', filename)
            if m3:
                return season, int(m3.group(1))
        
        # Match - 02.mkv or _02_
        m4 = re.search(r'[_\-\s](\d{1,3})(?:\.|_|\s|$)', filename)
        if m4:
            return season, int(m4.group(1))
            
    return None, None

def preview_renames(target_folder):
    """
    Scans the given folder, fetches metadata, and returns a list of proposed renames.
    Returns: { "status": "ok", "provider": ..., "show_id": ..., "items": [...] }
    """
    if not os.path.exists(target_folder):
        return {"status": "error", "message": "Der Ordner existiert nicht."}
        
    provider, show_id = _get_show_info_from_nfo(target_folder)
    
    # If no nfo, user has to supply it manually, but for now we error out or ask for manual entry later
    if not provider or not show_id:
        return {"status": "error", "message": "Keine tvshow.nfo gefunden oder ID konnte nicht extrahiert werden. Bitte erst manuell mit Metadaten versehen."}
        
    items = []
    # Cache fetched seasons metadata
    season_metadata_cache = {}
    
    video_extensions = {'.mkv', '.mp4', '.avi', '.m4v', '.ts', '.mov', '.wmv'}
    
    # Recursively find video files
    for root, dirs, files in os.walk(target_folder):
        # Ignore dot-folders
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        rel_root = os.path.relpath(root, target_folder)
        folder_name = os.path.basename(root)
        
        season_from_folder = _guess_season_from_folder(folder_name)
        
        for f in files:
            if f.startswith('.'):
                continue
            ext = os.path.splitext(f)[1].lower()
            if ext not in video_extensions:
                continue
                
            filepath = os.path.join(root, f)
            rel_path = os.path.relpath(filepath, target_folder)
            
            ep_season, ep_num = _parse_episode_from_filename(f, season_from_folder)
            
            item = {
                "rel_path": rel_path,
                "current_filename": f,
                "season": ep_season,
                "episode": ep_num,
                "status": "kein_treffer",
                "proposed_filename": "",
                "proposed_rel_path": ""
            }
            
            if ep_season is not None and ep_num is not None:
                # Load metadata for this season if not loaded
                if ep_season not in season_metadata_cache:
                    try:
                        if provider == "tvdb":
                            season_metadata_cache[ep_season] = mw_metadata.fetch_tvdb(show_id, ep_season, "deu")
                        elif provider in ["tmdb_tv", "tmdb_tv_en"]:
                            lang = "en-US" if provider == "tmdb_tv_en" else "de-DE"
                            season_metadata_cache[ep_season] = mw_metadata.fetch_tmdb_tv(show_id, ep_season, lang)
                        else:
                            # Not supported for auto-rename yet
                            season_metadata_cache[ep_season] = {}
                    except Exception as e:
                        print(f"[NAS Renamer] Error fetching metadata for S{ep_season}: {e}")
                        season_metadata_cache[ep_season] = {}
                        
                ep_data = season_metadata_cache[ep_season].get(str(ep_num))
                
                if ep_data:
                    title = ep_data.get("title", "")
                    clean_title = sanitize_filename(limit_filename_length(title, 80))
                    
                    if clean_title:
                        proposed_name = f"S{ep_season:02d}E{ep_num:02d} - {clean_title}{ext}"
                    else:
                        proposed_name = f"S{ep_season:02d}E{ep_num:02d}{ext}"
                        
                    item["proposed_filename"] = proposed_name
                    
                    # Target season folder
                    target_season_folder = f"Staffel {ep_season:02d}" if ep_season > 0 else "Specials"
                    item["proposed_rel_path"] = os.path.join(target_season_folder, proposed_name)
                    
                    if item["proposed_rel_path"] == rel_path:
                        item["status"] = "passt_bereits"
                    elif proposed_name == f:
                        item["status"] = "passt_bereits" # Different folder, but name is correct
                        item["proposed_rel_path"] = rel_path # Avoid moving folders for now if not requested
                    else:
                        item["status"] = "abweichung"
                        # We will just rename the file in its current directory
                        item["proposed_rel_path"] = os.path.join(os.path.dirname(rel_path), proposed_name)
                        
            items.append(item)
            
    # Sort items by rel_path
    items.sort(key=lambda x: x["rel_path"])
    
    return {
        "status": "ok",
        "provider": provider,
        "show_id": show_id,
        "items": items
    }


def apply_renames(target_folder, rename_plan):
    """
    Applies the selected renames, backs up NFOs, and writes a transaction log.
    rename_plan format: [ { "rel_path": "Staffel 1/S01E01.mkv", "proposed_rel_path": "Staffel 1/S01E01 - Title.mkv", "season": 1, "episode": 1 } ]
    """
    if not os.path.exists(target_folder):
        return {"status": "error", "message": "Der Ordner existiert nicht."}
        
    if not os.path.exists(TRANSACTIONS_DIR):
        os.makedirs(TRANSACTIONS_DIR, exist_ok=True)
        
    transaction_id = str(int(time.time() * 1000))
    transaction_log = {
        "transaction_id": transaction_id,
        "target_folder": target_folder,
        "timestamp": time.time(),
        "operations": [] # list of { "old": "...", "new": "..." }
    }
    
    success_count = 0
    errors = []
    
    for item in rename_plan:
        old_rel = item.get("rel_path")
        new_rel = item.get("proposed_rel_path")
        if new_rel:
            parent_dir = os.path.dirname(new_rel)
            filename = os.path.basename(new_rel)
            new_rel = os.path.join(parent_dir, sanitize_filename(filename))
            
        if not old_rel or not new_rel or old_rel == new_rel:
            continue
            
        old_abs = os.path.join(target_folder, old_rel)
        new_abs = os.path.join(target_folder, new_rel)
        
        # Ensure target directory exists
        os.makedirs(os.path.dirname(new_abs), exist_ok=True)
        
        if not os.path.exists(old_abs):
            errors.append(f"Datei nicht gefunden: {old_rel}")
            continue
            
        if os.path.exists(new_abs):
            errors.append(f"Zieldatei existiert bereits: {new_rel}")
            continue
            
        # 1. Rename the main video file
        try:
            os.rename(old_abs, new_abs)
            transaction_log["operations"].append({"old": old_abs, "new": new_abs})
            success_count += 1
        except Exception as e:
            errors.append(f"Fehler beim Umbenennen von {old_rel}: {e}")
            continue
            
        # 2. Look for associated files (NFO, subtitles, artwork)
        old_base = os.path.splitext(old_abs)[0]
        new_base = os.path.splitext(new_abs)[0]
        
        assoc_exts = ['.nfo', '.srt', '.en.srt', '.de.srt', '-thumb.jpg', '-fanart.jpg', '-poster.jpg']
        for ext in assoc_exts:
            old_assoc = old_base + ext
            new_assoc = new_base + ext
            if os.path.exists(old_assoc):
                try:
                    if ext == '.nfo':
                        # Special handling for NFO: create a .nfo.bak
                        bak_path = old_assoc + ".bak"
                        if not os.path.exists(bak_path):
                            shutil.copy2(old_assoc, bak_path)
                            transaction_log["operations"].append({"old": bak_path, "new": None}) # Remember we created a bak
                    
                    os.rename(old_assoc, new_assoc)
                    transaction_log["operations"].append({"old": old_assoc, "new": new_assoc})
                except Exception as e:
                    print(f"Fehler beim Umbenennen der Begleitdatei {old_assoc}: {e}")
                    
    # Write transaction log
    if transaction_log["operations"]:
        log_file = os.path.join(TRANSACTIONS_DIR, f"{transaction_id}.json")
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(transaction_log, f, indent=2, ensure_ascii=False)
            
    return {
        "status": "ok",
        "success_count": success_count,
        "errors": errors,
        "transaction_id": transaction_id
    }


def rollback_renames(transaction_id):
    """
    Reverts a renaming transaction.
    """
    log_file = os.path.join(TRANSACTIONS_DIR, f"{transaction_id}.json")
    if not os.path.exists(log_file):
        return {"status": "error", "message": "Transaktionslog nicht gefunden."}
        
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            transaction_log = json.load(f)
    except Exception as e:
        return {"status": "error", "message": f"Fehler beim Lesen des Logs: {e}"}
        
    success_count = 0
    errors = []
    
    # We must reverse the operations
    ops = reversed(transaction_log.get("operations", []))
    for op in ops:
        old_path = op.get("old")
        new_path = op.get("new")
        
        if new_path is None:
            # It was a backup creation (e.g. .nfo.bak), we don't strictly need to delete it, but we could.
            if os.path.exists(old_path):
                try:
                    trash.send_to_trash(old_path)
                except Exception:
                    pass
            continue
            
        if os.path.exists(new_path):
            try:
                os.rename(new_path, old_path)
                success_count += 1
            except Exception as e:
                errors.append(f"Fehler beim Wiederherstellen von {new_path}: {e}")
        else:
            errors.append(f"Datei nicht mehr vorhanden für Rollback: {new_path}")
            
    return {
        "status": "ok",
        "success_count": success_count,
        "errors": errors
    }
