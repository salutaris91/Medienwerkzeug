import os, time, threading, subprocess, traceback, shutil
from gui.core.helpers import *
from gui.core.transfers import *
from gui.core.notifications import *
import gui.mw_metadata as mw_metadata
import gui.core.media as media
from gui.core.utils import load_settings, save_settings, clean_show_name

JOB_QUEUE = []
SYSTEM_STATUS = {'running': True}
STATUS_LOCK = threading.Lock()
active_jobs = {}
active_jobs_lock = threading.Lock()
def build_job_pipeline(params, has_metadata, convert):
    pipeline = {
        "metadata": {"status": "pending" if has_metadata else "skipped", "progress": 0},
        "convert": {"status": "pending" if convert else "skipped", "progress": 0}
    }
    settings = load_settings()
    for target in settings.get("storage_targets", []):
        t_id = target.get("id")
        t_type = target.get("type")
        
        should_copy = False
        if params.get(f"copy_to_{t_id}") is not None:
            should_copy = params.get(f"copy_to_{t_id}")
        elif t_type == "nas" and params.get("copy_to_nas") is not None:
            should_copy = params.get("copy_to_nas")
        elif t_type != "nas" and params.get("copy_to_pcloud") is not None:
            should_copy = params.get("copy_to_pcloud")
            
        pipeline[t_id] = {"status": "pending" if (should_copy and target.get("enabled", True)) else "skipped", "progress": 0}
        
    if params.get("copy_to_local"):
        pipeline["local"] = {"status": "pending", "progress": 0}
    return pipeline

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

def run_subscription_check_job(task_id):
    try:
        settings = load_settings()
        subs = settings.get("youtube_subscriptions", [])
        active_subs = [s for s in subs if s.get("enabled")]
        if not active_subs:
            log_message("[YouTube Abo-Überwachung]: Keine aktiven Abonnements zum Überprüfen gefunden.")
            with active_jobs_lock:
                if task_id in active_jobs:
                    active_jobs[task_id]["progress"] = 100
                    active_jobs[task_id]["message"] = "Keine aktiven Abonnements"
            return
            
        total = len(active_subs)
        log_message(f"[YouTube Abo-Überwachung]: Starte manuell getriggerten Check für {total} Abos (via Warteschlange)...")
        
        for idx, sub in enumerate(active_subs):
            current_progress = int((idx / total) * 100)
            sub_name = sub.get("name", "Unbekannt")
            
            with active_jobs_lock:
                if task_id in active_jobs:
                    active_jobs[task_id]["progress"] = current_progress
                    active_jobs[task_id]["message"] = f"Prüfe '{sub_name}' ({idx + 1}/{total})..."
                    
            log_message(f"[YouTube Abo-Überwachung] Überprüfe '{sub_name}' ({idx + 1}/{total})...")
            try:
                check_single_subscription(sub)
            except Exception as sub_err:
                log_message(f"[YouTube Abo-Überwachung] Fehler bei '{sub_name}': {sub_err}")
            
        with active_jobs_lock:
            if task_id in active_jobs:
                active_jobs[task_id]["progress"] = 100
                active_jobs[task_id]["message"] = f"{total} Abonnements erfolgreich überprüft."
    except Exception as e:
        log_message(f"[YouTube Abo-Überwachung] Fehler bei der manuellen Überprüfung: {e}")
        raise e

def process_worker(params):
    media_type = params.get("media_type")

    # Map content_type for Feature 2
    content_type = "live_action"
    if media_type == "movie":
        content_type = "movie"
    elif media_type == "tv":
        # Destination ID: 2 (Serien), 3 (Dokus), 4 (Doku-Serien)
        dest_id = str(params.get("destination_id", ""))
        is_anime = params.get("is_anime", False)
        if dest_id == "3" or dest_id == "4":
            content_type = "doku"
        elif dest_id == "2" and is_anime:
            content_type = "anime"
    if media_type == "youtube_subscription_check":
        from gui.workers.youtube_worker import _do_subscription_check
        _do_subscription_check()
        return

    if media_type == "youtube_subscription_check":
        task_id = params.get("task_id")
        run_subscription_check_job(task_id)
        return
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

    # Resolve local destination path
    local_destination_id = params.get("local_destination_id")
    local_destination_path = None
    if local_destination_id:
        if local_destination_id == "__inbox__":
            local_destination_path = inbox_root
        elif local_destination_id == "__outbox__":
            local_destination_path = outbox_root
        elif local_destination_id.startswith("__cat_"):
            cat_id = local_destination_id[6:]  # strip "__cat_"
            sync_cats = settings.get("sync_categories", [])
            for cat in sync_cats:
                if cat.get("id") == str(cat_id):
                    nas_sub = cat.get("nas_sub", "")
                    local_destination_path = os.path.join(outbox_root, nas_sub.lstrip("/"))
                    break
        elif local_destination_id.startswith("__custom_"):
            try:
                idx = int(local_destination_id[9:])  # strip "__custom_"
                custom_folders = settings.get("local_download_folders", [])
                if 0 <= idx < len(custom_folders):
                    local_destination_path = custom_folders[idx].get("path", "")
            except (ValueError, IndexError):
                pass

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
                    try:
                        if os.path.isdir(jp):
                            shutil.rmtree(jp)
                        else:
                            os.remove(jp)
                        log_message(f"Gelöscht (Junk): {j}")
                    except Exception as e:
                        log_message(f"Fehler beim Löschen von Junk {j}: {e}")
                    
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
                except Exception as e: print(f"Warning: Ignored exception {e}")
    
    if media_type == "tv":
        rel_sub = ""
        if destination:
            if destination.startswith(nas_root):
                rel_sub = destination[len(nas_root):]
            else:
                rel_sub = os.path.basename(destination)
        else:
            rel_sub = "/Serien"
            
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
        file_titles = [""] * N

        # Determine active targets
        settings = load_settings()
        storage_targets = settings.get("storage_targets", [])
        
        active_nas_targets = []
        active_cloud_targets = []
        for target in storage_targets:
            t_id = target.get("id")
            t_type = target.get("type")
            
            should_copy = False
            if params.get(f"copy_to_{t_id}") is not None:
                should_copy = params.get(f"copy_to_{t_id}")
            elif t_type == "nas" and params.get("copy_to_nas") is not None:
                should_copy = params.get("copy_to_nas")
            elif t_type != "nas" and params.get("copy_to_pcloud") is not None:
                should_copy = params.get("copy_to_pcloud")
                
            if should_copy and target.get("enabled", True):
                if t_type == "nas" or t_id == "nas":
                    active_nas_targets.append(t_id)
                else:
                    active_cloud_targets.append(t_id)
                    
        has_conv = convert
        w_conv = 0.5 if has_conv else 0
        
        target_weights = {}
        if active_nas_targets:
            nas_weight = 0.3 / len(active_nas_targets)
            for t_id in active_nas_targets:
                target_weights[t_id] = nas_weight
        if active_cloud_targets:
            cloud_weight = 0.2 / len(active_cloud_targets)
            for t_id in active_cloud_targets:
                target_weights[t_id] = cloud_weight
                
        # Normalize weights
        total_w = w_conv + sum(target_weights.values())
        if total_w > 0:
            w_conv = w_conv / total_w
            for t_id in target_weights:
                target_weights[t_id] = target_weights[t_id] / total_w
        else:
            w_conv = 0.5
            target_weights = {}
            
        progress_lock = threading.RLock()
        
        # Track progresses for each target
        target_progresses = {}
        target_speeds = {}
        for target in storage_targets:
            t_id = target.get("id")
            target_progresses[t_id] = [0] * N if (target.get("type") == "nas" or t_id == "nas") else 0
            target_speeds[t_id] = [""] * N if (target.get("type") == "nas" or t_id == "nas") else ""

        def update_global_job_progress():
            with progress_lock:
                total_file_progress = 0
                for i in range(N):
                    nas_prog = sum(target_progresses[t_id][i] * target_weights.get(t_id, 0) for t_id in target_weights if isinstance(target_progresses[t_id], list))
                    total_file_progress += (conv_pct[i] * w_conv) + nas_prog
                
                avg_files = total_file_progress / N if N > 0 else 0
                cloud_prog = sum(target_progresses[t_id] * target_weights.get(t_id, 0) for t_id in target_weights if not isinstance(target_progresses[t_id], list))
                total_val = avg_files + cloud_prog
                percent = min(100, max(0, int(total_val)))
                
                active_conv = []
                active_trans = []
                for i in range(N):
                    if conv_pct[i] > 0 and conv_pct[i] < 100:
                        active_conv.append(f"{file_titles[i]} ({conv_pct[i]}%)")
                    for target in storage_targets:
                        t_id = target.get("id")
                        t_name = target.get("name", t_id)
                        t_pct = target_progresses[t_id]
                        t_speeds = target_speeds[t_id]
                        if t_id in target_weights and isinstance(t_pct, list) and t_pct[i] > 0 and t_pct[i] < 100:
                            speed_info = f" bei {t_speeds[i]}" if t_speeds[i] else ""
                            active_trans.append(f"{file_titles[i]} ({t_name} {t_pct[i]}%{speed_info})")
                            
                status_parts = []
                if active_conv:
                    status_parts.append(f"Konvertierung: {', '.join(active_conv)}")
                elif has_conv and sum(conv_pct) < N * 100:
                    status_parts.append("Konvertierung wartet...")
                    
                if active_trans:
                    status_parts.append(f"Kopieren: {', '.join(active_trans)}")
                
                # Check active cloud uploads
                for target in storage_targets:
                    t_id = target.get("id")
                    t_name = target.get("name", t_id)
                    t_pct = target_progresses[t_id]
                    t_speed = target_speeds[t_id]
                    if t_id in target_weights and not isinstance(t_pct, list) and t_pct > 0 and t_pct < 100:
                        speed_info = f" ({t_speed})" if t_speed else ""
                        status_parts.append(f"{t_name} Upload: {t_pct}%{speed_info}")
                        
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
                        target_id = task.get("target_id", "nas")
                        dest_dir_outbox = task["dest_dir_outbox"]
                        dest_dir_nas = task["dest_dir_nas"]
                        final_filename = task["final_filename"]
                        clean_title = task["clean_title"]
                        
                        log_message(f"[Transfer Thread]: Starte NAS-Kopieren für {final_filename} auf {target_id}...")
                        
                        def nas_progress_cb(percent, msg):
                            target_progresses[target_id][file_idx] = percent
                            speed_match = re.search(r'\(([\d.]+\s*[kKMG]i?B/s)\)', msg)
                            if speed_match:
                                target_speeds[target_id][file_idx] = speed_match.group(1)
                            else:
                                speed_match_raw = re.search(r'([\d.]+\s*[kKMG]i?B/s)', msg)
                                if speed_match_raw:
                                    target_speeds[target_id][file_idx] = speed_match_raw.group(1)
                            update_global_job_progress()
                            with active_jobs_lock:
                                if task_id and task_id in active_jobs and "pipeline" in active_jobs[task_id]:
                                    if target_id in active_jobs[task_id]["pipeline"]:
                                        active_jobs[task_id]["pipeline"][target_id]["status"] = "running"
                                        avg_nas = sum(target_progresses[target_id]) / N
                                        active_jobs[task_id]["pipeline"][target_id]["progress"] = int(avg_nas)
                            
                        os.makedirs(dest_dir_nas, exist_ok=True)
                        success = run_rsync_with_progress(
                            os.path.join(dest_dir_outbox, final_filename),
                            os.path.join(dest_dir_nas, final_filename),
                            task_id=nas_progress_cb
                        )
                        if not success:
                            log_message(f"⚠️ [Transfer Thread]: Fehler beim Kopieren von {final_filename} auf {target_id}.")
                            with active_jobs_lock:
                                if task_id and task_id in active_jobs and "pipeline" in active_jobs[task_id]:
                                    if target_id in active_jobs[task_id]["pipeline"]:
                                        active_jobs[task_id]["pipeline"][target_id]["status"] = "error"
                                        active_jobs[task_id]["pipeline"][target_id]["message"] = "Fehlgeschlagen"
                        else:
                            target_progresses[target_id][file_idx] = 100
                            
                        # Copy accompanying files
                        for f in os.listdir(dest_dir_outbox):
                            if f.startswith(clean_title) and f != final_filename:
                                shutil.copy(os.path.join(dest_dir_outbox, f), os.path.join(dest_dir_nas, f))
                        
                        log_message(f"[Transfer Thread]: Kopieren auf {target_id} fertig für {final_filename}.")
                        update_global_job_progress()
                        
                    elif task_type == "show_metadata_nas_transfer":
                        dest_show_dir_outbox = task["dest_show_dir_outbox"]
                        dest_show_dir_nas = task["dest_show_dir_nas"]
                        
                        log_message(f"[Transfer Thread]: Kopiere Serien-Metadaten auf {dest_show_dir_nas}...")
                        os.makedirs(dest_show_dir_nas, exist_ok=True)
                        for f in ["tvshow.nfo", "poster.jpg", "fanart.jpg"]:
                            p_src = os.path.join(dest_show_dir_outbox, f)
                            if os.path.exists(p_src):
                                p_dest = os.path.join(dest_show_dir_nas, f)
                                if os.path.exists(p_dest):
                                    log_message(f"[Transfer Thread]: {f} existiert bereits. Wird nicht überschrieben.")
                                else:
                                    shutil.copy(p_src, p_dest)
                        log_message("[Transfer Thread]: Serien-Metadaten kopiert.")
                        # settings = load_settings()
                        # if settings.get("open_nas_finder") and "/Volumes/Kino" in dest_show_dir_nas:
                        #     open_folder_in_finder(dest_show_dir_nas)
                        
                    elif task_type in ["pcloud_transfer", "cloud_transfer"]:
                        target_id = task.get("target_id", "pcloud")
                        dest_show_dir_outbox = task["dest_show_dir_outbox"]
                        nas_serien = task["nas_serien"]
                        explicit_remote_base = task.get("explicit_remote_base") or task.get("explicit_pcloud_base")
                        
                        settings = load_settings()
                        target = next((t for t in settings.get("storage_targets", []) if t.get("id") == target_id), None)
                        target_name = target.get("name", target_id) if target else target_id
                        
                        log_message(f"[Transfer Thread]: Starte Upload für {target_name}...")
                        
                        def cloud_progress_cb(percent, msg):
                            with progress_lock:
                                target_progresses[target_id] = percent
                                speed_match = re.search(r'\(([\d.]+\s*[kKMG]i?B/s)\)', msg)
                                if speed_match:
                                    target_speeds[target_id] = speed_match.group(1)
                                else:
                                    speed_match_raw = re.search(r'([\d.]+\s*[kKMG]i?B/s)', msg)
                                    if speed_match_raw:
                                        target_speeds[target_id] = speed_match_raw.group(1)
                            update_global_job_progress()
                            with active_jobs_lock:
                                if task_id and task_id in active_jobs and "pipeline" in active_jobs[task_id]:
                                    if target_id in active_jobs[task_id]["pipeline"]:
                                        active_jobs[task_id]["pipeline"][target_id]["status"] = "running"
                                        active_jobs[task_id]["pipeline"][target_id]["progress"] = percent
                            
                        success = copy_to_cloud_target(
                            dest_show_dir_outbox,
                            nas_serien,
                            target_id=target_id,
                            task_id=cloud_progress_cb,
                            explicit_remote_base=explicit_remote_base
                        )
                        if success:
                            with progress_lock:
                                target_progresses[target_id] = 100
                            log_message(f"[Transfer Thread]: Upload für {target_name} fertig.")
                            update_global_job_progress()
                            with active_jobs_lock:
                                if task_id and task_id in active_jobs and "pipeline" in active_jobs[task_id]:
                                    if target_id in active_jobs[task_id]["pipeline"]:
                                        active_jobs[task_id]["pipeline"][target_id]["status"] = "done"
                                        active_jobs[task_id]["pipeline"][target_id]["progress"] = 100
                        else:
                            log_message(f"[Transfer Thread]: ❌ Upload für {target_name} fehlgeschlagen.")
                            with active_jobs_lock:
                                if task_id and task_id in active_jobs and "pipeline" in active_jobs[task_id]:
                                    if target_id in active_jobs[task_id]["pipeline"]:
                                        active_jobs[task_id]["pipeline"][target_id]["status"] = "error"
                                        active_jobs[task_id]["pipeline"][target_id]["message"] = "Fehlgeschlagen"
                        
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
                                media.add_conversion_to_history(quality, "hevc", ratio, size_in, size_out, content_type=content_type, filename=os.path.basename(filepath if 'filepath' in locals() else target_filepath), resolution=None)
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
            settings = load_settings()
            storage_targets = settings.get("storage_targets", [])
            for target in storage_targets:
                t_id = target.get("id")
                t_type = target.get("type")
                if t_type != "nas" and t_id != "nas":
                    continue
                    
                should_copy = False
                if params.get(f"copy_to_{t_id}") is not None:
                    should_copy = params.get(f"copy_to_{t_id}")
                elif params.get("copy_to_nas") is not None:
                    should_copy = params.get("copy_to_nas")
                    
                if should_copy and target.get("enabled", True):
                    if t_id == "nas":
                        if not ensure_nas_mounted():
                            raise RuntimeError("NAS konnte nicht gemountet werden. Kopiervorgang abgebrochen.")
                    
                    target_base = resolve_target_destination(target, rel_sub, "tv")
                    dest_dir_target = os.path.join(target_base, clean_show_name, f"Staffel {int(ep_season)}", clean_title)
                    transfer_queue.put({
                        "type": "nas_transfer",
                        "target_id": t_id,
                        "file_idx": file_idx,
                        "dest_dir_outbox": dest_dir_outbox,
                        "dest_dir_nas": dest_dir_target,
                        "final_filename": final_filename,
                        "clean_title": clean_title
                    })
                else:
                    if t_id in target_progresses:
                        target_progresses[t_id][file_idx] = 100
                        
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
                    p_dest = os.path.join(dest_show_dir_outbox, f)
                    if os.path.exists(p_dest):
                        log_message(f"Serien-Metadatei existiert bereits im Output-Ordner und wird nicht überschrieben: {f}")
                    else:
                        shutil.move(p_src, p_dest)
                        log_message(f"Serien-Metadatei in Output-Ordner verschoben: {f}")
            # Open local destination in Finder
            if settings.get("open_outbox_finder"):
                open_folder_in_finder(dest_show_dir_outbox)
        except Exception as e:
            log_message(f"Fehler beim Verschieben der Serien-Metadaten in Output-Ordner: {e}")

        # Copy show-level files to NAS targets if requested
        for target in settings.get("storage_targets", []):
            t_id = target.get("id")
            t_type = target.get("type")
            if t_type != "nas" and t_id != "nas":
                continue
                
            should_copy = False
            if params.get(f"copy_to_{t_id}") is not None:
                should_copy = params.get(f"copy_to_{t_id}")
            elif params.get("copy_to_nas") is not None:
                should_copy = params.get("copy_to_nas")
                
            if should_copy and target.get("enabled", True):
                target_base = resolve_target_destination(target, rel_sub, "tv")
                dest_show_dir_target = os.path.join(target_base, clean_show_name)
                transfer_queue.put({
                    "type": "show_metadata_nas_transfer",
                    "dest_show_dir_outbox": dest_show_dir_outbox,
                    "dest_show_dir_nas": dest_show_dir_target
                })
                
        # Queue all Cloud/third-party targets copies
        for target in settings.get("storage_targets", []):
            t_id = target.get("id")
            t_type = target.get("type")
            if t_type == "nas" or t_id == "nas":
                continue
                
            should_copy = False
            if params.get(f"copy_to_{t_id}") is not None:
                should_copy = params.get(f"copy_to_{t_id}")
            elif params.get("copy_to_pcloud") is not None:
                should_copy = params.get("copy_to_pcloud")
                
            if should_copy and target.get("enabled", True):
                target_base = resolve_target_destination(target, rel_sub, "tv")
                transfer_queue.put({
                    "type": "cloud_transfer",
                    "target_id": t_id,
                    "dest_show_dir_outbox": dest_show_dir_outbox,
                    "nas_serien": target_base,
                    "explicit_remote_base": explicit_pcloud_base if t_id == "pcloud" else None
                })
            else:
                with progress_lock:
                    if t_id in target_progresses:
                        target_progresses[t_id] = 100
                update_global_job_progress()
                
        # Send Sentinel and join
        transfer_queue.put(None)
        transfer_thread.join()
        
        with active_jobs_lock:
            if task_id and task_id in active_jobs and "pipeline" in active_jobs[task_id]:
                for step_key, step_info in active_jobs[task_id]["pipeline"].items():
                    if step_key not in ["metadata", "convert"] and step_info["status"] == "running":
                        step_info["status"] = "done"
                        step_info["progress"] = 100
        
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
                video_exts = ('.mp4', '.mkv', '.avi', '.webm', '.mov', '.ts', '.m2ts', '.flv', '.3gp', '.wmv')
                remaining_videos = []
                for root, dirs, files in os.walk(current_dir):
                    for f in files:
                        if f.lower().endswith(video_exts) and not f.startswith("."):
                            remaining_videos.append(os.path.join(root, f))
                
                if not remaining_videos:
                    import shutil
                    shutil.rmtree(current_dir)
                    log_message(f"Projekt-Ordner im Input bereinigt (keine Videos mehr vorhanden): {os.path.basename(current_dir)}")
                else:
                    non_dot_files = [f for f in os.listdir(current_dir) if not f.startswith(".")]
                    if not non_dot_files:
                        import shutil
                        shutil.rmtree(current_dir)
                        log_message(f"Leeren Projekt-Ordner im Input bereinigt: {os.path.basename(current_dir)}")
            except Exception as e:
                log_message(f"Fehler beim Bereinigen des Projekt-Ordners: {e}")

    elif media_type == "movie":
        rel_sub = ""
        if destination:
            if destination.startswith(nas_root):
                rel_sub = destination[len(nas_root):]
            else:
                rel_sub = os.path.basename(destination)
        else:
            rel_sub = "/Filme"
            
        movie_name = params.get("movie_name")
        if movie_name:
            movie_name = re.sub(r"\s*\(Mediathek.*?\)", "", movie_name)
            movie_name = re.sub(r"\s*\(Freie Mediathek.*?\)", "", movie_name).strip()
            movie_overrides = nfo_overrides.get("movie") if nfo_overrides else None
            if movie_overrides and movie_overrides.get("year"):
                year = str(movie_overrides.get("year")).strip()
                if year.isdigit() and len(year) == 4:
                    movie_name = re.sub(r"\s*\(\d{4}\)$", "", movie_name).strip()
                    movie_name = f"{movie_name} ({year})"
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
        file_titles = [clean_movie_name] * N
        
        # Determine active targets
        settings = load_settings()
        storage_targets = settings.get("storage_targets", [])
        
        active_nas_targets = []
        active_cloud_targets = []
        for target in storage_targets:
            t_id = target.get("id")
            t_type = target.get("type")
            
            should_copy = False
            if params.get(f"copy_to_{t_id}") is not None:
                should_copy = params.get(f"copy_to_{t_id}")
            elif t_type == "nas" and params.get("copy_to_nas") is not None:
                should_copy = params.get("copy_to_nas")
            elif t_type != "nas" and params.get("copy_to_pcloud") is not None:
                should_copy = params.get("copy_to_pcloud")
                
            if should_copy and target.get("enabled", True):
                if t_type == "nas" or t_id == "nas":
                    active_nas_targets.append(t_id)
                else:
                    active_cloud_targets.append(t_id)
                    
        has_conv = convert
        w_conv = 0.5 if has_conv else 0
        
        target_weights = {}
        if active_nas_targets:
            nas_weight = 0.3 / len(active_nas_targets)
            for t_id in active_nas_targets:
                target_weights[t_id] = nas_weight
        if active_cloud_targets:
            cloud_weight = 0.2 / len(active_cloud_targets)
            for t_id in active_cloud_targets:
                target_weights[t_id] = cloud_weight
                
        # Normalize weights
        total_w = w_conv + sum(target_weights.values())
        if total_w > 0:
            w_conv = w_conv / total_w
            for t_id in target_weights:
                target_weights[t_id] = target_weights[t_id] / total_w
        else:
            w_conv = 0.5
            target_weights = {}
            
        progress_lock = threading.Lock()
        
        target_progresses = {}
        target_speeds = {}
        for target in storage_targets:
            t_id = target.get("id")
            target_progresses[t_id] = [0] * N
            target_speeds[t_id] = [""] * N

        def update_global_job_progress():
            with progress_lock:
                total_file_progress = 0
                for i in range(N):
                    target_prog = sum(target_progresses[t_id][i] * target_weights.get(t_id, 0) for t_id in target_weights)
                    total_file_progress += (conv_pct[i] * w_conv) + target_prog
                
                avg_files = total_file_progress / N if N > 0 else 0
                percent = min(100, max(0, int(avg_files)))
                
                active_conv = []
                active_trans = []
                for i in range(N):
                    if conv_pct[i] > 0 and conv_pct[i] < 100:
                        active_conv.append(f"{file_titles[i]} ({conv_pct[i]}%)")
                    for target in storage_targets:
                        t_id = target.get("id")
                        t_name = target.get("name", t_id)
                        t_pct = target_progresses[t_id]
                        t_speeds = target_speeds[t_id]
                        if t_id in target_weights and t_pct[i] > 0 and t_pct[i] < 100:
                            speed_info = f" bei {t_speeds[i]}" if t_speeds[i] else ""
                            active_trans.append(f"{t_name} ({t_pct[i]}%{speed_info})")
                            
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
                        target_id = task.get("target_id", "nas")
                        dest_movie_dir_outbox = task["dest_movie_dir_outbox"]
                        dest_movie_dir_nas = task["dest_movie_dir_nas"]
                        final_filename = task["final_filename"]
                        
                        log_message(f"[Transfer Thread]: Starte NAS-Kopieren für {final_filename} auf {target_id}...")
                        
                        def nas_progress_cb(percent, msg):
                            target_progresses[target_id][file_idx] = percent
                            speed_match = re.search(r'\(([\d.]+\s*[kKMG]i?B/s)\)', msg)
                            if speed_match:
                                target_speeds[target_id][file_idx] = speed_match.group(1)
                            else:
                                speed_match_raw = re.search(r'([\d.]+\s*[kKMG]i?B/s)', msg)
                                if speed_match_raw:
                                    target_speeds[target_id][file_idx] = speed_match_raw.group(1)
                            update_global_job_progress()
                            with active_jobs_lock:
                                if task_id and task_id in active_jobs and "pipeline" in active_jobs[task_id]:
                                    if target_id in active_jobs[task_id]["pipeline"]:
                                        active_jobs[task_id]["pipeline"][target_id]["status"] = "running"
                                        avg_nas = sum(target_progresses[target_id]) / N
                                        active_jobs[task_id]["pipeline"][target_id]["progress"] = int(avg_nas)
                            
                        os.makedirs(dest_movie_dir_nas, exist_ok=True)
                        success = run_rsync_with_progress(
                            dest_movie_dir_outbox,
                            dest_movie_dir_nas,
                            task_id=nas_progress_cb
                        )
                        if success:
                            log_message(f"[Transfer Thread]: Kopieren auf {target_id} fertig für {final_filename}.")
                            target_progresses[target_id][file_idx] = 100
                            # settings = load_settings()
                            # if settings.get("open_nas_finder") and "/Volumes/Kino" in dest_movie_dir_nas:
                            #     open_folder_in_finder(dest_movie_dir_nas)
                        else:
                            log_message(f"⚠️ [Transfer Thread]: Fehler beim Kopieren von {final_filename} auf {target_id}.")
                            with active_jobs_lock:
                                if task_id and task_id in active_jobs and "pipeline" in active_jobs[task_id]:
                                    if target_id in active_jobs[task_id]["pipeline"]:
                                        active_jobs[task_id]["pipeline"][target_id]["status"] = "error"
                        update_global_job_progress()
                        
                    elif task_type in ["movie_pcloud_transfer", "movie_cloud_transfer"]:
                        target_id = task.get("target_id", "pcloud")
                        dest_movie_dir_outbox = task["dest_movie_dir_outbox"]
                        dest_movies = task["dest_movies"]
                        explicit_remote_base = task.get("explicit_remote_base") or task.get("explicit_pcloud_base")
                        
                        settings = load_settings()
                        target = next((t for t in settings.get("storage_targets", []) if t.get("id") == target_id), None)
                        target_name = target.get("name", target_id) if target else target_id
                        
                        log_message(f"[Transfer Thread]: Starte Upload nach {target_name} für {clean_movie_name}...")
                        
                        def cloud_progress_cb(percent, msg):
                            with progress_lock:
                                target_progresses[target_id][file_idx] = percent
                                speed_match = re.search(r'\(([\d.]+\s*[kKMG]i?B/s)\)', msg)
                                if speed_match:
                                    target_speeds[target_id][file_idx] = speed_match.group(1)
                                else:
                                    speed_match_raw = re.search(r'([\d.]+\s*[kKMG]i?B/s)', msg)
                                    if speed_match_raw:
                                        target_speeds[target_id][file_idx] = speed_match_raw.group(1)
                            update_global_job_progress()
                            with active_jobs_lock:
                                if task_id and task_id in active_jobs and "pipeline" in active_jobs[task_id]:
                                    if target_id in active_jobs[task_id]["pipeline"]:
                                        active_jobs[task_id]["pipeline"][target_id]["status"] = "running"
                                        avg_pcloud = sum(target_progresses[target_id]) / N
                                        active_jobs[task_id]["pipeline"][target_id]["progress"] = int(avg_pcloud)
                            
                        success = copy_to_cloud_target(
                            dest_movie_dir_outbox,
                            dest_movies,
                            target_id=target_id,
                            task_id=cloud_progress_cb,
                            explicit_remote_base=explicit_remote_base
                        )
                        if success:
                            with progress_lock:
                                target_progresses[target_id][file_idx] = 100
                            log_message(f"[Transfer Thread]: Upload nach {target_name} fertig für {clean_movie_name}.")
                            update_global_job_progress()
                            with active_jobs_lock:
                                if task_id and task_id in active_jobs and "pipeline" in active_jobs[task_id]:
                                    if target_id in active_jobs[task_id]["pipeline"]:
                                        active_jobs[task_id]["pipeline"][target_id]["status"] = "done"
                                        active_jobs[task_id]["pipeline"][target_id]["progress"] = 100
                        else:
                            log_message(f"[Transfer Thread]: ❌ Upload nach {target_name} fehlgeschlagen für {clean_movie_name}.")
                            with active_jobs_lock:
                                if task_id and task_id in active_jobs and "pipeline" in active_jobs[task_id]:
                                    if target_id in active_jobs[task_id]["pipeline"]:
                                        active_jobs[task_id]["pipeline"][target_id]["status"] = "error"
                                        active_jobs[task_id]["pipeline"][target_id]["message"] = "Fehlgeschlagen"
                        
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
                                media.add_conversion_to_history(quality, "hevc", ratio, size_in, size_out, content_type=content_type, filename=os.path.basename(filepath if 'filepath' in locals() else target_filepath), resolution=None)
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
                if settings.get("open_outbox_finder"):
                    open_folder_in_finder(dest_movie_dir_outbox)
            except Exception as e:
                log_message(f"Fehler beim Verschieben in Output-Ordner: {e}")
 
            # Queue copies for each enabled target
            settings = load_settings()
            for target in settings.get("storage_targets", []):
                t_id = target.get("id")
                t_type = target.get("type")
                
                should_copy = False
                if params.get(f"copy_to_{t_id}") is not None:
                    should_copy = params.get(f"copy_to_{t_id}")
                elif t_type == "nas" and params.get("copy_to_nas") is not None:
                    should_copy = params.get("copy_to_nas")
                elif t_type != "nas" and params.get("copy_to_pcloud") is not None:
                    should_copy = params.get("copy_to_pcloud")
                    
                if should_copy and target.get("enabled", True):
                    if t_type == "nas" or t_id == "nas":
                        if t_id == "nas":
                            if not ensure_nas_mounted():
                                raise RuntimeError("NAS konnte nicht gemountet werden. Kopiervorgang abgebrochen.")
                        
                        target_base = resolve_target_destination(target, rel_sub, "movie")
                        dest_movie_dir_target = os.path.join(target_base, clean_movie_name)
                        
                        transfer_queue.put({
                            "type": "movie_nas_transfer",
                            "target_id": t_id,
                            "file_idx": file_idx,
                            "dest_movie_dir_outbox": dest_movie_dir_outbox,
                            "dest_movie_dir_nas": dest_movie_dir_target,
                            "final_filename": final_filename
                        })
                    else:
                        target_base = resolve_target_destination(target, rel_sub, "movie")
                        transfer_queue.put({
                            "type": "movie_cloud_transfer",
                            "target_id": t_id,
                            "file_idx": file_idx,
                            "dest_movie_dir_outbox": dest_movie_dir_outbox,
                            "dest_movies": target_base,
                            "explicit_remote_base": explicit_pcloud_base if t_id == "pcloud" else None
                        })
                else:
                    if t_id in target_progresses:
                        target_progresses[t_id][file_idx] = 100
                        
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
                for step_key, step_info in active_jobs[task_id]["pipeline"].items():
                    if step_key not in ["metadata", "convert"] and step_info["status"] == "running":
                        step_info["status"] = "done"
                        step_info["progress"] = 100
        
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
                    
    elif media_type in ["youtube", "youtube_merge"]:
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
        
        settings = load_settings()
        inbox_root = settings.get("inbox_dir", os.path.expanduser("~/Downloads/Medien Input"))
        nas_root = settings.get("nas_root", "/Volumes/Kino")
        
        # Temp dir inside Downloads/Medien Input/.temp_yt_<task_id>
        temp_dir = os.path.join(inbox_root, f".temp_yt_{task_id}")
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
            
        update_task_pipeline_status(task_id, "metadata", "running", 0)
        
        log_message(f"=== STARTE YOUTUBE DOWNLOAD PIPELINE FUER TASK {task_id} ===")
        log_message(f"Ziel-Temp-Ordner: {temp_dir}")
        
        try:
            if media_type == "youtube":
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
                downloaded_files = [f for f in os.listdir(temp_dir) if f.lower().endswith(('.mp4', '.mkv', '.avi', '.webm', '.mov', '.mp3', '.m4a')) and not f.startswith(".")]
                
                update_task_pipeline_status(task_id, "metadata", "done", 100)
                
                # Mark convert as skipped if we don't do any post-processing split/cut
                if not (split_chapters or trim_start or trim_end or open_losslesscut):
                    update_task_pipeline_status(task_id, "convert", "skipped")
            
            else: # youtube_merge
                urls = params.get("yt_urls", [])
                final_title = params.get("title", "Merged Video")
                subscription_id = params.get("subscription_id")
                video_ids_to_remove = params.get("video_ids_to_remove", [])
                num_urls = len(urls)
                
                log_message(f"=== STARTE YOUTUBE MERGE PIPELINE FUER TASK {task_id} ===")
                
                # Download parts sequentially
                for idx, part_url in enumerate(urls, 1):
                    with active_jobs_lock:
                        if task_id in active_jobs:
                            active_jobs[task_id]["progress"] = int(((idx - 1) / num_urls) * 90)
                            active_jobs[task_id]["message"] = f"Lade Teil {idx} von {num_urls}..."
                    
                    format_opt = params.get("yt_format", "best")
                    part_output = f"part_{idx:02d}.%(ext)s"
                    cmd = ["yt-dlp", "-P", temp_dir, "--output", part_output, "--merge-output-format", "mkv", "--remux-video", "mkv"]
                    
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
                        
                    cmd.extend(["--cookies-from-browser", "chrome", part_url])
                    
                    log_message(f"Lade Teil {idx}/{num_urls}: {' '.join(cmd)}")
                    success = run_ytdlp_with_progress(cmd, task_id=None, log_queue=log_queue)
                    if not success:
                        cmd_fallback = [x for x in cmd if x != "chrome" and x != "--cookies-from-browser"]
                        success = run_ytdlp_with_progress(cmd_fallback, task_id=None, log_queue=log_queue)
                    if not success:
                        raise RuntimeError(f"Download von Teil {idx} ({part_url}) fehlgeschlagen.")
                
                files = sorted([f for f in os.listdir(temp_dir) if f.startswith("part_") and f.lower().endswith(".mkv")])
                if not files:
                    raise RuntimeError("Keine heruntergeladenen Teile gefunden.")
                
                final_name = f"{sanitize_filename(final_title)}.mkv"
                final_path = os.path.join(temp_dir, final_name)
                
                if len(files) < 2:
                    log_message("Nur ein Teil heruntergeladen. Überspringe FFmpeg-Concat.")
                    os.rename(os.path.join(temp_dir, files[0]), final_path)
                else:
                    with active_jobs_lock:
                        if task_id in active_jobs:
                            active_jobs[task_id]["progress"] = 90
                            active_jobs[task_id]["message"] = "Füge Teile zusammen (FFmpeg)..."
                    
                    update_task_pipeline_status(task_id, "metadata", "done", 100)
                    update_task_pipeline_status(task_id, "convert", "running", 0)
                    
                    inputs_txt_path = os.path.join(temp_dir, "inputs.txt")
                    with open(inputs_txt_path, "w", encoding="utf-8") as f_inputs:
                        for f in files:
                            f_inputs.write(f"file '{f}'\n")
                    
                    ffmpeg_cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", inputs_txt_path, "-c", "copy", final_path]
                    log_message(f"Führe FFmpeg aus: {' '.join(ffmpeg_cmd)}")
                    ffmpeg_res = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
                    if ffmpeg_res.returncode != 0:
                        raise RuntimeError(f"FFmpeg-Zusammenfügen fehlgeschlagen: {ffmpeg_res.stderr}")
                    
                    log_message("FFmpeg-Zusammenfügen erfolgreich.")
                    update_task_pipeline_status(task_id, "convert", "done", 100)
                    
                    # Cleanup downloaded parts
                    for f in files:
                        try:
                            os.remove(os.path.join(temp_dir, f))
                        except Exception as e:
                            log_message(f"  ❌ Fehler beim Löschen von Teil {f}: {e}")
                    try:
                        os.remove(inputs_txt_path)
                    except Exception as e:
                        log_message(f"  ❌ Fehler beim Löschen von inputs.txt: {e}")
                
                # Clear pending videos in subscription if needed
                if subscription_id and video_ids_to_remove:
                    try:
                        settings_save = load_settings()
                        for s in settings_save.get("youtube_subscriptions", []):
                            if s.get("id") == subscription_id:
                                pending = s.get("pending_videos", [])
                                s["pending_videos"] = [v for v in pending if v.get("id") not in video_ids_to_remove]
                                downloaded_ids = s.get("downloaded_ids", [])
                                for vid in video_ids_to_remove:
                                    if vid not in downloaded_ids:
                                        downloaded_ids.append(vid)
                                s["downloaded_ids"] = downloaded_ids
                                save_settings(settings_save)
                                break
                    except Exception as sub_clean_err:
                        log_message(f"Fehler beim Bereinigen der Freigabeliste nach Merge: {sub_clean_err}")
                
                downloaded_files = [final_name]
            
            # If LosslessCut is checked and we have video files
            if open_losslesscut and downloaded_files:
                primary_file = downloaded_files[0]
                primary_filepath = os.path.join(temp_dir, primary_file)
                
                lossless_path = "/Applications/LosslessCut.app"
                if os.path.exists(lossless_path):
                    log_message(f"🎬 Oeffne {primary_file} in LosslessCut...")
                    update_task_pipeline_status(task_id, "convert", "running", 50)
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
                    update_task_pipeline_status(task_id, "convert", "done", 100)
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
                update_task_pipeline_status(task_id, "metadata", "running", 90)
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
                    
                    if settings.get("open_outbox_finder"):
                        open_folder_in_finder(dest_dir_outbox)
                except Exception as e:
                    log_message(f"  ❌ Fehler bei Übertragung in Output-Ordner: {e}")
                    all_transfers_successful = False

                # Copy to targets dynamically
                if destination and transfer_successful:
                    settings = load_settings()
                    nas_target = next((t for t in settings.get("storage_targets", []) if t.get("id") == "nas"), None)
                    nas_root = nas_target.get("root_path", "/Volumes/Kino") if nas_target else settings.get("nas_root", "/Volumes/Kino")
                    
                    rel_sub = ""
                    if destination.startswith(nas_root):
                        rel_sub = destination[len(nas_root):]
                    else:
                        rel_sub = os.path.basename(destination)
                        
                    for target in settings.get("storage_targets", []):
                        t_id = target.get("id")
                        t_type = target.get("type")
                        
                        should_copy = False
                        if params.get(f"copy_to_{t_id}") is not None:
                            should_copy = params.get(f"copy_to_{t_id}")
                        elif t_type == "nas" and params.get("copy_to_nas") is not None:
                            should_copy = params.get("copy_to_nas")
                        elif t_type != "nas" and params.get("copy_to_pcloud") is not None:
                            should_copy = params.get("copy_to_pcloud")
                            
                        if should_copy and target.get("enabled", True):
                            if t_type == "nas" or t_id == "nas":
                                # NAS copy
                                update_task_pipeline_status(task_id, t_id, "running", 0)
                                if t_id == "nas":
                                    if not ensure_nas_mounted():
                                        update_task_pipeline_status(task_id, t_id, "error", 0)
                                        raise RuntimeError("NAS konnte nicht gemountet werden. Kopiervorgang abgebrochen.")
                                
                                target_base = resolve_target_destination(target, rel_sub, metadata_mode)
                                dest_dir_target = target_base
                                if metadata_mode == "tv" and show_id:
                                    dest_dir_target = os.path.join(target_base, clean_show_name, f"Staffel {int(season)}", clean_base)
                                elif metadata_mode == "movie" and movie_id:
                                    dest_dir_target = os.path.join(target_base, clean_base)
                                    
                                log_message(f"Kopiere von Output auf {target.get('name', t_id)}: {dest_dir_target}...")
                                try:
                                    os.makedirs(dest_dir_target, exist_ok=True)
                                    success = run_rsync_with_progress(os.path.join(dest_dir_outbox, target_filename), os.path.join(dest_dir_target, target_filename), task_id)
                                    if not success:
                                        raise RuntimeError(f"Kopieren auf {target.get('name', t_id)} fehlgeschlagen.")
                                    for f in os.listdir(dest_dir_outbox):
                                        if f.startswith(clean_base) and f != target_filename:
                                            shutil.copy(os.path.join(dest_dir_outbox, f), os.path.join(dest_dir_target, f))
                                    for art_name in ["poster.jpg", "fanart.jpg"]:
                                        art_src = os.path.join(dest_dir_outbox, art_name)
                                        if os.path.exists(art_src):
                                            shutil.copy(art_src, os.path.join(dest_dir_target, art_name))
                                            suffix = "-poster.jpg" if art_name == "poster.jpg" else "-fanart.jpg"
                                            shutil.copy(art_src, os.path.join(dest_dir_target, f"{clean_base}{suffix}"))
                                    log_message(f"  ✅ Erfolgreich auf {target.get('name', t_id)} kopiert.")
                                    update_task_pipeline_status(task_id, t_id, "done", 100)
                                    if t_id == "nas" and settings.get("open_nas_finder"):
                                        open_folder_in_finder(dest_dir_target)
                                except Exception as e:
                                    log_message(f"  ❌ Fehler bei {target.get('name', t_id)}-Kopie: {e}")
                                    update_task_pipeline_status(task_id, t_id, "error", 0)
                                    all_transfers_successful = False
                            else:
                                # Cloud copy
                                update_task_pipeline_status(task_id, t_id, "running", 0)
                                dest_dir_cloud_outbox = dest_dir_outbox
                                if metadata_mode == "tv" and show_id:
                                    dest_dir_cloud_outbox = os.path.join(outbox_dest, clean_show_name)
                                elif metadata_mode == "movie" and movie_id:
                                    dest_dir_cloud_outbox = os.path.join(outbox_dest, clean_base)
                                
                                target_base = resolve_target_destination(target, rel_sub, metadata_mode)
                                cloud_success = copy_to_cloud_target(
                                    dest_dir_cloud_outbox,
                                    target_base,
                                    target_id=t_id,
                                    task_id=task_id,
                                    explicit_remote_base=explicit_pcloud_base if t_id == "pcloud" else None
                                )
                                if not cloud_success:
                                    update_task_pipeline_status(task_id, t_id, "error", 0)
                                    all_transfers_successful = False
                                else:
                                    update_task_pipeline_status(task_id, t_id, "done", 100)
                                    
            # Move show-level files in series mode to outbox
            dest_show_dir_outbox = None
            if metadata_mode == "tv" and show_id and destination:
                dest_show_dir_outbox = os.path.join(outbox_dest, clean_show_name)
                try:
                    os.makedirs(dest_show_dir_outbox, exist_ok=True)
                    for f in ["tvshow.nfo", "poster.jpg", "fanart.jpg"]:
                        p_src = os.path.join(temp_dir, f)
                        if os.path.exists(p_src):
                            p_dest = os.path.join(dest_show_dir_outbox, f)
                            if os.path.exists(p_dest):
                                log_message(f"Serien-Metadatei existiert bereits in Output und wird nicht überschrieben: {f}")
                            else:
                                shutil.move(p_src, p_dest)
                                log_message(f"Serien-Metadatei verschoben: {f}")
                except Exception as e:
                    log_message(f"Fehler beim Verschieben der Serien-Metadaten in Output: {e}")
                    all_transfers_successful = False
 
                # Copy show-level files to NAS targets if requested
                settings = load_settings()
                for target in settings.get("storage_targets", []):
                    t_id = target.get("id")
                    t_type = target.get("type")
                    if t_type != "nas" and t_id != "nas":
                        continue
                        
                    should_copy = False
                    if params.get(f"copy_to_{t_id}") is not None:
                        should_copy = params.get(f"copy_to_{t_id}")
                    elif params.get("copy_to_nas") is not None:
                        should_copy = params.get("copy_to_nas")
                        
                    if should_copy and target.get("enabled", True):
                        target_base = resolve_target_destination(target, rel_sub, "tv")
                        dest_show_dir_target = os.path.join(target_base, clean_show_name)
                        try:
                            os.makedirs(dest_show_dir_target, exist_ok=True)
                            for f in ["tvshow.nfo", "poster.jpg", "fanart.jpg"]:
                                p_src = os.path.join(dest_show_dir_outbox, f) if dest_show_dir_outbox else os.path.join(temp_dir, f)
                                if os.path.exists(p_src):
                                    p_dest = os.path.join(dest_show_dir_target, f)
                                    if os.path.exists(p_dest):
                                        log_message(f"Serien-Metadatei existiert bereits auf {target.get('name', t_id)} und wird nicht überschrieben: {f}")
                                    else:
                                        shutil.copy(p_src, p_dest)
                                        log_message(f"Serien-Metadatei auf {target.get('name', t_id)} kopiert: {f}")
                        except Exception as e:
                            log_message(f"Fehler beim Kopieren der Serien-Metadaten auf {target.get('name', t_id)}: {e}")
                            all_transfers_successful = False
            # Copy to local folder if requested
            copy_to_local = params.get("copy_to_local", False)
            if copy_to_local and local_destination_path:
                update_task_pipeline_status(task_id, "local", "running", 0)
                try:
                    # Build structured destination path
                    local_dest_dir = local_destination_path
                    if metadata_mode == "tv" and show_id:
                        local_dest_dir = os.path.join(local_destination_path, clean_show_name, f"Staffel {int(season)}", clean_base)
                    elif metadata_mode == "movie" and movie_id:
                        local_dest_dir = os.path.join(local_destination_path, clean_base)
                    else:
                        # General YouTube: use video title as folder name
                        yt_title = sanitize_filename(params.get("yt_title", "YouTube Download"))
                        local_dest_dir = os.path.join(local_destination_path, limit_filename_length(yt_title))
                    
                    os.makedirs(local_dest_dir, exist_ok=True)
                    log_message(f"Kopiere in lokalen Ordner: {local_dest_dir}...")
                    
                    # Copy video file
                    src_video = os.path.join(dest_dir_outbox, target_filename) if transfer_successful else filepath
                    shutil.copy2(src_video, os.path.join(local_dest_dir, target_filename))
                    
                    # Copy accompanying files (NFOs, subtitles)
                    source_dir = dest_dir_outbox if transfer_successful else temp_dir
                    for f in os.listdir(source_dir):
                        f_path = os.path.join(source_dir, f)
                        if os.path.isfile(f_path) and f != target_filename:
                            if f.startswith(clean_base) or f in ["poster.jpg", "fanart.jpg"]:
                                shutil.copy2(f_path, os.path.join(local_dest_dir, f))
                    
                    # Copy show-level files for series
                    if metadata_mode == "tv" and show_id and dest_show_dir_outbox and os.path.isdir(dest_show_dir_outbox):
                        local_show_dir = os.path.join(local_destination_path, clean_show_name)
                        os.makedirs(local_show_dir, exist_ok=True)
                        for f in ["tvshow.nfo", "poster.jpg", "fanart.jpg"]:
                            src = os.path.join(dest_show_dir_outbox, f)
                            if os.path.exists(src):
                                dest_f = os.path.join(local_show_dir, f)
                                if os.path.exists(dest_f):
                                    log_message(f"Serien-Metadatei existiert bereits im lokalen Zielordner und wird nicht überschrieben: {f}")
                                else:
                                    shutil.copy2(src, dest_f)
                    
                    log_message(f"  ✅ Erfolgreich in lokalen Ordner kopiert: {local_dest_dir}")
                    update_task_pipeline_status(task_id, "local", "done", 100)
                    
                    # Open local folder if setting is enabled
                    if settings.get("open_outbox_finder"):
                        open_folder_in_finder(local_dest_dir)
                except Exception as e:
                    log_message(f"  ❌ Fehler beim Kopieren in lokalen Ordner: {e}")
                    update_task_pipeline_status(task_id, "local", "error", 0)
                    all_transfers_successful = False
                    
            # Clean up temp folder OR open it on failure
            if not copy_to_nas or all_transfers_successful:
                try:
                    shutil.rmtree(temp_dir)
                    log_message("Temporärer Ordner bereinigt.")
                except Exception as e:
                    log_message(f"  ❌ Fehler beim Bereinigen des temporären Ordners: {e}")
            else:
                log_message(f"⚠️  Übertragung fehlgeschlagen. Der temporäre Ordner '{temp_dir}' wurde NICHT gelöscht.")
                # Open temp folder in Finder so the user can access files manually
                open_folder_in_finder(temp_dir)
                
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
        force_reconvert = params.get("force_reconvert", False)
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
                    if not force_reconvert and codec in ["hevc", "h265", "vp9", "av1"]:
                        log_message(f"{f} ist bereits {codec.upper()}. Überspringe.")
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
                                    media.add_conversion_to_history(quality, "hevc", ratio, size_in, size_out, content_type=content_type, filename=os.path.basename(filepath if 'filepath' in locals() else target_filepath), resolution=None)
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
                    open_folder_in_finder(nas_target)
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
                if active_jobs[task_id]["status"] != "error":
                    active_jobs[task_id]["status"] = "done"
                    active_jobs[task_id]["progress"] = 100
                    active_jobs[task_id]["message"] = "Erfolgreich beendet"
        except Exception as e:
            with active_jobs_lock:
                active_jobs[task_id]["status"] = "error"
                active_jobs[task_id]["message"] = f"Fehler: {str(e)}"
                # Setze alle unvollständigen Pipeline-Schritte bei einem Abbruch auf error
                if "pipeline" in active_jobs[task_id]:
                    for step_key, step_info in active_jobs[task_id]["pipeline"].items():
                        if step_info.get("status") in ["running", "pending"]:
                            step_info["status"] = "error"
                            step_info["message"] = "Fehlgeschlagen"
            print(f"Job {task_id} failed: {e}")
        finally:
            job_queue.task_done()
