import os, time, threading, subprocess, traceback, shutil
from gui.core.helpers import *
from gui.core.transfers import *
from gui.core.notifications import *
import gui.mw_metadata as mw_metadata
import gui.core.media as media
from gui.core.utils import load_settings, save_settings, clean_show_name, get_runtime_capabilities
from gui.core import artwork_validators
import gui.core.trash as trash

def _get_series_meta_files(settings):
    """Returns 'tvshow.nfo' and all server-specific series artwork names."""
    server_type = settings.get("media_server", "emby") or "emby"
    validator = artwork_validators.get_validator(server_type)

    show_artworks = []
    show_artworks.extend(validator.get_series_poster_names())
    show_artworks.extend(validator.get_series_backdrop_names())
    if validator.supports_logos:
        show_artworks.extend(validator.get_series_logo_names())
    if validator.supports_banners:
        show_artworks.extend(validator.get_series_banner_names())
    unique_artworks = []
    for art in show_artworks:
        if art not in unique_artworks:
            unique_artworks.append(art)

    return ["tvshow.nfo"] + unique_artworks

def _update_transfer_progress(target_id, file_idx, percent, msg, target_progresses, target_speeds, progress_lock, N, task_id, update_global_job_progress):
    import re
    
    with progress_lock:
        try:
            target_progresses[target_id][file_idx] = percent
            is_list = True
        except TypeError:
            target_progresses[target_id] = percent
            is_list = False

        speed_match = re.search(r'\(([\d.]+\s*[kKMG]i?B/s)\)', msg)
        if not speed_match:
            speed_match = re.search(r'([\d.]+\s*[kKMG]i?B/s)', msg)
        
        speed_str = speed_match.group(1) if speed_match else None
        if speed_str:
            try:
                target_speeds[target_id][file_idx] = speed_str
            except TypeError:
                target_speeds[target_id] = speed_str

    update_global_job_progress()

    with active_jobs_lock:
        if task_id and task_id in active_jobs and "pipeline" in active_jobs[task_id]:
            if target_id in active_jobs[task_id]["pipeline"]:
                active_jobs[task_id]["pipeline"][target_id]["status"] = "running"
                if is_list:
                    avg_val = sum(target_progresses[target_id]) / N if N > 0 else percent
                    active_jobs[task_id]["pipeline"][target_id]["progress"] = int(avg_val)
                else:
                    active_jobs[task_id]["pipeline"][target_id]["progress"] = percent

def _handle_transfer_task(
    task,
    task_id,
    target_progresses,
    target_speeds,
    progress_lock,
    N,
    log_message,
    update_global_job_progress
):
    import os
    import shutil

    task_type = task["type"]
    file_idx = task.get("file_idx")
    
    if task_type in ["nas_transfer", "movie_nas_transfer"]:
        target_id = task.get("target_id", "nas")
        final_filename = task["final_filename"]
        
        def nas_progress_cb(percent, msg):
            _update_transfer_progress(
                target_id, file_idx, percent, msg,
                target_progresses, target_speeds, progress_lock,
                N, task_id, update_global_job_progress
            )
            
        if task_type == "nas_transfer":
            dest_dir_outbox = task["dest_dir_outbox"]
            dest_dir_nas = task["dest_dir_nas"]
            clean_title = task["clean_title"]
            
            log_message(f"[Transfer Thread]: Starte NAS-Kopieren für {final_filename} auf {target_id}...")
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
                with progress_lock:
                    target_progresses[target_id][file_idx] = 100
                # Copy accompanying files
                for f in os.listdir(dest_dir_outbox):
                    if f.startswith(clean_title) and f != final_filename:
                        shutil.copy(os.path.join(dest_dir_outbox, f), os.path.join(dest_dir_nas, f))
                log_message(f"[Transfer Thread]: Kopieren auf {target_id} fertig für {final_filename}.")
                
        else:  # movie_nas_transfer
            dest_movie_dir_outbox = task["dest_movie_dir_outbox"]
            dest_movie_dir_nas = task["dest_movie_dir_nas"]
            
            log_message(f"[Transfer Thread]: Starte NAS-Kopieren für {final_filename} auf {target_id}...")
            os.makedirs(dest_movie_dir_nas, exist_ok=True)
            success = run_rsync_with_progress(
                dest_movie_dir_outbox,
                dest_movie_dir_nas,
                task_id=nas_progress_cb
            )
            if success:
                log_message(f"[Transfer Thread]: Kopieren auf {target_id} fertig für {final_filename}.")
                with progress_lock:
                    target_progresses[target_id][file_idx] = 100
            else:
                log_message(f"⚠️ [Transfer Thread]: Fehler beim Kopieren von {final_filename} auf {target_id}.")
                with active_jobs_lock:
                    if task_id and task_id in active_jobs and "pipeline" in active_jobs[task_id]:
                        if target_id in active_jobs[task_id]["pipeline"]:
                            active_jobs[task_id]["pipeline"][target_id]["status"] = "error"
                            
        update_global_job_progress()
        
    elif task_type == "show_metadata_nas_transfer":
        dest_show_dir_outbox = task["dest_show_dir_outbox"]
        dest_show_dir_nas = task["dest_show_dir_nas"]

        log_message(f"[Transfer Thread]: Kopiere Serien-Metadaten auf {dest_show_dir_nas}...")
        os.makedirs(dest_show_dir_nas, exist_ok=True)
        settings = load_settings()
        meta_files = _get_series_meta_files(settings)
        for f in meta_files:
            p_src = os.path.join(dest_show_dir_outbox, f)
            if os.path.exists(p_src):
                p_dest = os.path.join(dest_show_dir_nas, f)
                if os.path.exists(p_dest):
                    log_message(f"[Transfer Thread]: {f} existiert bereits. Wird nicht überschrieben.")
                else:
                    shutil.copy(p_src, p_dest)
        log_message("[Transfer Thread]: Serien-Metadaten kopiert.")
        
    elif task_type in ["pcloud_transfer", "cloud_transfer", "movie_pcloud_transfer", "movie_cloud_transfer"]:
        target_id = task.get("target_id", "pcloud")
        explicit_remote_base = task.get("explicit_remote_base") or task.get("explicit_pcloud_base")
        
        settings = load_settings()
        target = next((t for t in settings.get("storage_targets", []) if t.get("id") == target_id), None)
        target_name = target.get("name", target_id) if target else target_id
        
        def cloud_progress_cb(percent, msg):
            _update_transfer_progress(
                target_id, file_idx, percent, msg,
                target_progresses, target_speeds, progress_lock,
                N, task_id, update_global_job_progress
            )
            
        if task_type in ["pcloud_transfer", "cloud_transfer"]:
            dest_show_dir_outbox = task["dest_show_dir_outbox"]
            nas_serien = task["nas_serien"]
            
            log_message(f"[Transfer Thread]: Starte Upload für {target_name}...")
            success = copy_to_cloud_target(
                dest_show_dir_outbox,
                nas_serien,
                target_id=target_id,
                task_id=cloud_progress_cb,
                explicit_remote_base=explicit_remote_base
            )
            name_log = target_name
        else:  # movie_pcloud_transfer / movie_cloud_transfer
            dest_movie_dir_outbox = task["dest_movie_dir_outbox"]
            dest_movies = task["dest_movies"]
            clean_movie_name = task.get("clean_movie_name", "")
            
            log_message(f"[Transfer Thread]: Starte Upload nach {target_name} für {clean_movie_name}...")
            success = copy_to_cloud_target(
                dest_movie_dir_outbox,
                dest_movies,
                target_id=target_id,
                task_id=cloud_progress_cb,
                explicit_remote_base=explicit_remote_base
            )
            name_log = f"{target_name} für {clean_movie_name}"
            
        if success:
            with progress_lock:
                try:
                    target_progresses[target_id][file_idx] = 100
                except TypeError:
                    target_progresses[target_id] = 100
            log_message(f"[Transfer Thread]: Upload nach {name_log} fertig.")
            update_global_job_progress()
            with active_jobs_lock:
                if task_id and task_id in active_jobs and "pipeline" in active_jobs[task_id]:
                    if target_id in active_jobs[task_id]["pipeline"]:
                        active_jobs[task_id]["pipeline"][target_id]["status"] = "done"
                        active_jobs[task_id]["pipeline"][target_id]["progress"] = 100
        else:
            log_message(f"[Transfer Thread]: ❌ Upload nach {name_log} fehlgeschlagen.")
            with active_jobs_lock:
                if task_id and task_id in active_jobs and "pipeline" in active_jobs[task_id]:
                    if target_id in active_jobs[task_id]["pipeline"]:
                        active_jobs[task_id]["pipeline"][target_id]["status"] = "error"
                        active_jobs[task_id]["pipeline"][target_id]["message"] = "Fehlgeschlagen"

def _update_pipeline_metadata_progress(task_id, current_prog):
    from gui.core.jobs import active_jobs, active_jobs_lock
    with active_jobs_lock:
        if task_id and task_id in active_jobs and "pipeline" in active_jobs[task_id]:
            active_jobs[task_id]["pipeline"]["metadata"]["progress"] = min(100, current_prog)
            if current_prog >= 100:
                active_jobs[task_id]["pipeline"]["metadata"]["status"] = "done"

def _mark_convert_step_done(task_id):
    from gui.core.jobs import active_jobs, active_jobs_lock
    with active_jobs_lock:
        if task_id and task_id in active_jobs and "pipeline" in active_jobs[task_id]:
            if active_jobs[task_id]["pipeline"]["convert"]["status"] == "running":
                active_jobs[task_id]["pipeline"]["convert"]["status"] = "done"
                active_jobs[task_id]["pipeline"]["convert"]["progress"] = 100

def _mark_remaining_steps_done(task_id):
    from gui.core.jobs import active_jobs, active_jobs_lock
    with active_jobs_lock:
        if task_id and task_id in active_jobs and "pipeline" in active_jobs[task_id]:
            for step_key, step_info in active_jobs[task_id]["pipeline"].items():
                if step_key not in ["metadata", "convert"] and step_info["status"] == "running":
                    step_info["status"] = "done"
                    step_info["progress"] = 100

def _finalize_job(params, job_size_gb, transfer_errors, current_dir, inbox_root, log_message):
    import os
    import gui.core.trash as trash

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
                trash.send_to_trash(current_dir)
                log_message(f"Projekt-Ordner im Input bereinigt (keine Videos mehr vorhanden): {os.path.basename(current_dir)}")
            else:
                non_dot_files = [f for f in os.listdir(current_dir) if not f.startswith(".")]
                if not non_dot_files:
                    trash.send_to_trash(current_dir)
                    log_message(f"Leeren Projekt-Ordner im Input bereinigt: {os.path.basename(current_dir)}")
        except Exception as e:
            log_message(f"Fehler beim Bereinigen des Projekt-Ordners: {e}")

def _get_movie_artwork_lists(settings, video_filename):
    """Returns (poster_names, backdrop_names) for the configured media server and film."""
    server_type = settings.get("media_server", "emby") or "emby"
    validator = artwork_validators.get_validator(server_type)
    return (
        validator.get_movie_poster_names(video_filename),
        validator.get_movie_backdrop_names(video_filename)
    )

def path_endswith(full_path, suffix_path):
    """Checks if full_path ends with the components of suffix_path, respecting path boundaries."""
    full_parts = os.path.normpath(full_path).split(os.sep)
    suffix_parts = os.path.normpath(suffix_path).split(os.sep)
    # Filter out empty parts that might occur from trailing slashes or absolute paths
    full_parts = [p for p in full_parts if p]
    suffix_parts = [p for p in suffix_parts if p]
    if len(full_parts) < len(suffix_parts):
        return False
    return full_parts[-len(suffix_parts):] == suffix_parts

def move_with_fallback(src_path, dest_dir, fallback_basename, whitelist=None):
    """
    Moves a file at src_path to dest_dir.
    If the file is in the whitelist (mapping old to new), it uses the new name.
    Otherwise, it uses fallback_basename + extension (with collision counter if needed).
    """
    try:
        if not os.path.exists(src_path):
            log_message(f"⚠️ [Fallback-Verschiebung] Quelldatei existiert nicht: {src_path}")
            return

        os.makedirs(dest_dir, exist_ok=True)
        filename = os.path.basename(src_path)
        ext = os.path.splitext(filename)[1].lower()

        target_name = None
        if whitelist:
            for item in whitelist:
                if path_endswith(src_path, item["old"]) or os.path.basename(src_path) == item["new"]:
                    target_name = item["new"]
                    break

        if not target_name:
            lower_name = filename.lower()
            is_metadata = False
            if ext == '.nfo':
                is_metadata = True
            else:
                metadata_keywords = ['poster', 'fanart', 'backdrop', 'folder', 'logo', 'banner', 'clearlogo', 'cover', 'background', 'art', 'default']
                for kw in metadata_keywords:
                    if kw in lower_name:
                        is_metadata = True
                        break
            if is_metadata:
                target_name = filename

        if target_name:
            dst_path = os.path.join(dest_dir, target_name)
            log_message(f"[Fallback-Verschiebung] Verwende Whitelist-Name: {target_name} für {src_path}")
        else:
            # Check for VobSub pairing (.sub / .idx) at the source
            is_vobsub_pair = False
            partner_src = None
            partner_ext = None
            if ext in ('.sub', '.idx'):
                partner_ext = '.idx' if ext == '.sub' else '.sub'
                partner_src = os.path.splitext(src_path)[0] + partner_ext
                if os.path.exists(partner_src):
                    is_vobsub_pair = True

            counter = 1
            while True:
                if counter == 1:
                    candidate = f"{fallback_basename}{ext}"
                else:
                    candidate = f"{fallback_basename}.{counter}{ext}"
                dst_path = os.path.join(dest_dir, candidate)

                if is_vobsub_pair:
                    if counter == 1:
                        partner_candidate = f"{fallback_basename}{partner_ext}"
                    else:
                        partner_candidate = f"{fallback_basename}.{counter}{partner_ext}"
                    partner_dst_path = os.path.join(dest_dir, partner_candidate)
                    if not os.path.exists(dst_path) and not os.path.exists(partner_dst_path):
                         break
                else:
                    if not os.path.exists(dst_path):
                        break
                counter += 1

            log_message(f"[Fallback-Verschiebung] Auffangregel: {src_path} -> {os.path.basename(dst_path)}")

            # If it's a VobSub pair, dynamically register the partner in the whitelist so it finds the same counter
            if is_vobsub_pair and whitelist is not None:
                whitelist.append({
                    "old": partner_src,
                    "new": os.path.basename(partner_dst_path)
                })

        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        if os.path.exists(dst_path):
            log_message(f"⚠️ [Fallback-Verschiebung] Ziel existiert bereits und wird überschrieben: {dst_path}")
            if os.path.isdir(dst_path):
                shutil.rmtree(dst_path)
            else:
                os.remove(dst_path)
        shutil.move(src_path, dst_path)
        log_message(f"✅ Datei verschoben: {os.path.basename(src_path)} -> {os.path.basename(dst_path)}")

    except Exception as e:
        log_message(f"❌ Fehler bei Fallback-Verschiebung von {src_path} nach {dest_dir}: {e}")

def safe_move_recursive(src_dir, dest_dir, prefix_filter=None, fallback_basename=None, whitelist=None, junk_list=None):
    """
    Recursively walks src_dir and moves files to dest_dir.
    If prefix_filter is provided, only files whose name starts with prefix_filter
    (or are whitelisted to a name starting with prefix_filter) are moved.
    """
    video_exts = ('.mp4', '.mkv', '.avi', '.webm', '.mov', '.ts', '.m2ts', '.flv', '.3gp', '.wmv')
    if not os.path.exists(src_dir):
        return

    # Gather files
    files_to_process = []
    for root, dirs, files in os.walk(src_dir):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for f in files:
            if f.startswith('.'):
                continue
            f_path = os.path.join(root, f)
            files_to_process.append(f_path)

    # Process files
    for f_path in files_to_process:
        filename = os.path.basename(f_path)
        if filename.lower().endswith(video_exts):
            continue

        # Check junk list
        is_junk = False
        if junk_list:
            for j in junk_list:
                if path_endswith(f_path, j):
                    is_junk = True
                    break
        if is_junk:
            log_message(f"[Safe Move] Überspringe Junk-Datei: {f_path}")
            continue

        belongs = False
        if prefix_filter is None:
            belongs = True
        else:
            if filename.startswith(prefix_filter):
                belongs = True
            elif whitelist:
                for item in whitelist:
                    if path_endswith(f_path, item["old"]) or os.path.basename(f_path) == item["new"]:
                        if item["new"].startswith(prefix_filter):
                            belongs = True
                            break

        if belongs:
            fb = prefix_filter if prefix_filter else fallback_basename
            move_with_fallback(f_path, dest_dir, fb, whitelist=whitelist)

    # Cleanup empty subdirectories
    for root, dirs, files in os.walk(src_dir, topdown=False):
        if root == src_dir:
            continue
        try:
            non_dot_files = [f for f in os.listdir(root) if not f.startswith('.')]
            if not non_dot_files:
                trash.send_to_trash(root)
                log_message(f"[Safe Move] Leeren Unterordner entfernt: {os.path.basename(root)}")
        except Exception as e:
            log_message(f"[Safe Move] Fehler beim Entfernen des Ordners {root}: {e}")

JOB_QUEUE = []
SYSTEM_STATUS = {'running': True}
STATUS_LOCK = threading.Lock()
SYSTEM_METRICS = {
    'inbox_size_gb': None,
    'outbox_size_gb': None,
    'nas_info': None,
    'last_updated': 0
}
METRICS_LOCK = threading.Lock()

from gui.core.jobs import active_jobs, active_jobs_lock
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

import re

def _extract_show_name(filename):
    """
    Extract the show name by removing SxxExx and everything after.
    Also handles Sxx and other common patterns.
    Fallback to base name if no pattern matches.
    """
    base_name, _ = os.path.splitext(filename)
    match = re.search(r'(?i)(.*?)[.\s-]*S\d+E\d+', base_name)
    if match:
        show = match.group(1).replace('.', ' ').strip()
        if show: return show
    return base_name.replace('.', ' ').strip()

def preview_streamfab_import():
    settings = load_settings()
    sources = settings.get("import_sources", [])

    all_files_to_import = []
    for sf_dir in sources:
        if not os.path.exists(sf_dir):
            continue
        for root, dirs, files in os.walk(sf_dir):
            for f in files:
                if f.startswith('.'): continue
                if f.lower().endswith(('.mp4', '.mkv', '.avi', '.webm', '.srt', '.nfo', '.vtt', '.jpg', '.png', '.ass', '.ssa', '.sub', '.idx')):
                    src = os.path.join(root, f)
                    all_files_to_import.append((src, f))

    groups = {}
    for src, f in all_files_to_import:
        show_name = _extract_show_name(f)
        key = show_name.lower()
        if key not in groups:
            groups[key] = {
                "project_name": show_name,
                "safe_folder_name": limit_filename_length(sanitize_filename(show_name)),
                "files": []
            }
        size = 0
        try:
            size = os.path.getsize(src)
        except Exception:
            pass
        groups[key]["files"].append({
            "path": src,
            "filename": f,
            "size": size,
            "is_video": f.lower().endswith(('.mp4', '.mkv', '.avi', '.webm'))
        })

    return list(groups.values())

def execute_streamfab_import(import_items, delete_items):
    settings = load_settings()
    sources = settings.get("import_sources", [])
    inbox = settings.get("inbox_dir", os.path.expanduser("~/Downloads/Medien Input"))

    os.makedirs(inbox, exist_ok=True)
    count = 0

    # import_items: dict {"safe_folder_name": ["/path/to/file1", ...]}
    for safe_folder, file_paths in import_items.items():
        project_dir = os.path.join(inbox, safe_folder)
        os.makedirs(project_dir, exist_ok=True)
        for src in file_paths:
            if not os.path.exists(src): continue
            f = os.path.basename(src)
            dst = os.path.join(project_dir, f)
            try:
                shutil.move(src, dst)
                count += 1
            except Exception as e:
                print(f"Error moving {f} to project dir {safe_folder}: {e}")

    for src in delete_items:
        if os.path.exists(src):
            try:
                trash.send_to_trash(src)
            except Exception as e:
                raise Exception(f"Quarantäne-Fehler bei {os.path.basename(src)}: {e}")

    for sf_dir in sources:
        if not os.path.exists(sf_dir):
            continue
        for root, dirs, files in os.walk(sf_dir, topdown=False):
            for d in dirs:
                dir_path = os.path.join(root, d)
                if not os.listdir(dir_path):
                    try:
                        trash.send_to_trash(dir_path)
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
            from gui.core.jobs import update_job
            update_job(task_id, progress=100, message="Keine aktiven Abonnements", status="done")
            return

        total = len(active_subs)
        log_message(f"[YouTube Abo-Überwachung]: Starte manuell getriggerten Check für {total} Abos (via Warteschlange)...")

        for idx, sub in enumerate(active_subs):
            current_progress = int((idx / total) * 100)
            sub_name = sub.get("name", "Unbekannt")

            from gui.core.jobs import update_job
            update_job(task_id, progress=current_progress, message=f"Prüfe '{sub_name}' ({idx + 1}/{total})...")

            log_message(f"[YouTube Abo-Überwachung] Überprüfe '{sub_name}' ({idx + 1}/{total})...")
            try:
                check_single_subscription(sub)
            except Exception as sub_err:
                log_message(f"[YouTube Abo-Überwachung] Fehler bei '{sub_name}': {sub_err}")

        from gui.core.jobs import update_job
        update_job(task_id, progress=100, message=f"{total} Abonnements erfolgreich überprüft.", status="done")
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
    inbox_root = settings.get("inbox_dir", "")
    nas_root = settings.get("nas_root", "")
    outbox_root = settings.get("outbox_dir", "")

    if not inbox_root or not outbox_root:
        raise RuntimeError("Inbox- oder Output-Verzeichnis ist nicht konfiguriert.")

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
                        trash.send_to_trash(jp)
                        log_message(f"In Quarantäne (Junk): {j}")
                    except Exception as e:
                        log_message(f"Fehler beim Löschen von Junk {j}: {e}")

        if explicit_renames:
            # Check for duplicate target names (collisions)
            new_to_olds = {}
            for r in explicit_renames:
                new_f = r["new"]
                if new_f not in new_to_olds:
                    new_to_olds[new_f] = []
                new_to_olds[new_f].append(r["old"])

            filtered_renames = []
            for new_f, old_files in new_to_olds.items():
                if len(old_files) > 1:
                    # Determine sizes of colliding files
                    file_sizes = []
                    for old_f in old_files:
                        fp = os.path.join(current_dir, old_f)
                        try:
                            sz = os.path.getsize(fp) if os.path.exists(fp) else 0
                        except Exception:
                            sz = 0
                        file_sizes.append((old_f, sz))

                    # Sort absteigend nach Dateigröße
                    file_sizes.sort(key=lambda x: x[1], reverse=True)
                    largest_old = file_sizes[0][0]

                    # Verify that all other colliding files are marked as junk
                    junk_set = set(explicit_junk or [])
                    smaller_files_in_junk = True
                    for old_f, sz in file_sizes[1:]:
                        if old_f not in junk_set:
                            smaller_files_in_junk = False
                            break

                    if not smaller_files_in_junk:
                        raise RuntimeError(
                            f"Kollision im Namensschema erkannt: Mehrere Dateien verweisen auf dasselbe Ziel '{new_f}' "
                            f"({', '.join(old_files)}), aber die Duplikate sind nicht explizit als Junk markiert. "
                            f"Abbruch zur Vermeidung von Datenverlust."
                        )

                    # Only process the largest one, the others are sent to trash in the junk block
                    filtered_renames.append({"old": largest_old, "new": new_f})
                else:
                    filtered_renames.append({"old": old_files[0], "new": new_f})

            for r in filtered_renames:
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
                    trash.send_to_trash(root)
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
        from gui.core.jobs import update_job
        update_job(task_id, pipeline_step="metadata", pipeline_status="running", pipeline_progress=50)
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
                    from gui.core.jobs import update_job
                    update_job(task_id, progress=percent, message=message)

        transfer_queue = queue.Queue()
        transfer_errors = []

        def transfer_worker():
            while True:
                task = transfer_queue.get()
                if task is None:
                    transfer_queue.task_done()
                    break
                try:
                    _handle_transfer_task(
                        task,
                        task_id,
                        target_progresses,
                        target_speeds,
                        progress_lock,
                        N,
                        log_message,
                        update_global_job_progress
                    )
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
                meta_ep = ep_num_val.get("metadata_ep_num")
                if meta_ep:
                    ep_data = episodes.get(str(meta_ep), {})
                    if not ep_data and provider == "ytdlp" and len(episodes) == 1:
                        ep_data = list(episodes.values())[0]
                    if isinstance(ep_data, dict):
                        ep_title = ep_data.get("title", ep_title)
                    else:
                        ep_title = str(ep_data) or ep_title

                    match = re.match(r"^S(\d+)E(\d+)$", str(meta_ep), re.IGNORECASE)
                    if match:
                        orig_season = int(match.group(1))
                        orig_episode = int(match.group(2))
                    else:
                        orig_season = season
                        try:
                            orig_episode = int(meta_ep)
                        except (ValueError, TypeError):
                            orig_episode = meta_ep
                else:
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
                        if sub_ext in ['.srt', '.vtt', '.ass', '.ssa', '.sub', '.idx']:
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
            current_prog = 50 + int(50 * (file_idx + 1) / N)
            _update_pipeline_metadata_progress(task_id, current_prog)

            # H.265 Conversion
            final_filename = target_filename
            final_filepath = target_filepath
            if convert:
                temp_output = os.path.join(current_dir, f"{clean_title}_neu.mkv")
                def ffmpeg_progress_cb(percent, msg):
                    conv_pct[file_idx] = percent
                    update_global_job_progress()
                    with active_jobs_lock:
                        if task_id and task_id in active_jobs and "pipeline" in active_jobs[task_id]:
                            active_jobs[task_id]["pipeline"]["convert"]["status"] = "running"
                            avg_conv = sum(conv_pct) / N
                            active_jobs[task_id]["pipeline"]["convert"]["progress"] = int(avg_conv)

                conv_success, conv_file = media.execute_video_conversion(
                    target_filepath=target_filepath,
                    temp_output=temp_output,
                    final_filepath=os.path.join(current_dir, f"{clean_title}.mkv"),
                    quality=quality,
                    content_type=content_type,
                    original_filename=os.path.basename(filepath if 'filepath' in locals() else target_filepath),
                    delete_original=delete_original,
                    progress_callback=ffmpeg_progress_cb,
                    log_message_fn=log_message,
                    run_ffmpeg_fn=run_ffmpeg_with_progress,
                    send_to_trash_fn=trash.send_to_trash,
                    log_queue=log_queue
                )
                if conv_success:
                    final_filepath = os.path.join(current_dir, conv_file)
                    final_filename = conv_file
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

                # Move accompanying files safely (excluding original video files, handling subfolders recursively)
                whitelist_tv = []
                if explicit_renames:
                    whitelist_tv.extend(explicit_renames)
                if explicit_subs:
                    whitelist_tv.extend(explicit_subs)
                safe_move_recursive(
                    current_dir,
                    dest_dir_outbox,
                    prefix_filter=clean_title,
                    fallback_basename=None,
                    whitelist=whitelist_tv,
                    junk_list=explicit_junk
                )
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

        _mark_convert_step_done(task_id)

        # Move show-level files to local Output
        nas_serien = destination if destination else f"{nas_root}/Serien"
        rel_dest = os.path.relpath(nas_serien, nas_root)
        outbox_serien = os.path.join(outbox_root, rel_dest)
        dest_show_dir_outbox = os.path.join(outbox_serien, clean_show_name)
        try:
            os.makedirs(dest_show_dir_outbox, exist_ok=True)
            meta_files = _get_series_meta_files(settings)
            for f in meta_files:
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

        # Auffangregel: Move any remaining non-video, non-dot files to the show folder
        try:
            whitelist_show = []
            if explicit_renames:
                whitelist_show.extend(explicit_renames)
            if explicit_subs:
                whitelist_show.extend(explicit_subs)
            safe_move_recursive(
                current_dir,
                dest_show_dir_outbox,
                prefix_filter=None,
                fallback_basename=clean_show_name,
                whitelist=whitelist_show,
                junk_list=explicit_junk
            )
        except Exception as e:
            log_message(f"Fehler bei finaler Safe-Move-Bereinigung: {e}")

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

        _mark_remaining_steps_done(task_id)

        _finalize_job(params, job_size_gb, transfer_errors, current_dir, inbox_root, log_message)

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
                    _handle_transfer_task(
                        task,
                        task_id,
                        target_progresses,
                        target_speeds,
                        progress_lock,
                        N,
                        log_message,
                        update_global_job_progress
                    )
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

            if not os.path.exists(filepath) and not os.path.exists(target_filepath):
                log_message(f"⚠️ Datei '{video_file}' existiert nicht (mehr). Überspringe.")
                continue

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
            current_prog = 50 + int(50 * (file_idx + 1) / N)
            _update_pipeline_metadata_progress(task_id, current_prog)

            # H.265 Conversion
            final_filename = target_filename
            final_filepath = target_filepath
            if convert:
                temp_output = os.path.join(current_dir, f"{clean_movie_name}_neu.mkv")
                def ffmpeg_progress_cb(percent, msg):
                    conv_pct[file_idx] = percent
                    update_global_job_progress()
                    with active_jobs_lock:
                        if task_id and task_id in active_jobs and "pipeline" in active_jobs[task_id]:
                            active_jobs[task_id]["pipeline"]["convert"]["status"] = "running"
                            avg_conv = sum(conv_pct) / N
                            active_jobs[task_id]["pipeline"]["convert"]["progress"] = int(avg_conv)

                conv_success, conv_file = media.execute_video_conversion(
                    target_filepath=target_filepath,
                    temp_output=temp_output,
                    final_filepath=os.path.join(current_dir, f"{clean_movie_name}.mkv"),
                    quality=quality,
                    content_type=content_type,
                    original_filename=os.path.basename(filepath if 'filepath' in locals() else target_filepath),
                    delete_original=delete_original,
                    progress_callback=ffmpeg_progress_cb,
                    log_message_fn=log_message,
                    run_ffmpeg_fn=run_ffmpeg_with_progress,
                    send_to_trash_fn=trash.send_to_trash,
                    log_queue=log_queue
                )
                if conv_success:
                    final_filepath = os.path.join(current_dir, conv_file)
                    final_filename = conv_file
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

                # Move accompanying files safely (excluding original video files, handling subfolders recursively)
                whitelist_movie = []
                if explicit_renames:
                    whitelist_movie.extend(explicit_renames)
                if explicit_subs:
                    whitelist_movie.extend(explicit_subs)
                safe_move_recursive(
                    current_dir,
                    dest_movie_dir_outbox,
                    prefix_filter=None,
                    fallback_basename=clean_movie_name,
                    whitelist=whitelist_movie,
                    junk_list=explicit_junk
                )

                # Ensure only server-specific core poster/backdrop variants exist
                server_type = settings.get("media_server", "emby") or "emby"
                all_outbox_files = os.listdir(dest_movie_dir_outbox)
                base_movie, _ = os.path.splitext(final_filename)

                # --- 1. Find all poster candidates ---
                poster_candidates = [
                    "poster.jpg", "poster.png", "poster.webp",
                    "folder.jpg", "folder.png", "folder.webp",
                    "cover.jpg", "cover.png", "cover.webp",
                    "default.jpg", "default.png", "default.webp",
                ]
                found_posters = []
                for f in all_outbox_files:
                    f_lower = f.lower()
                    if f_lower in poster_candidates or f_lower.startswith(base_movie.lower() + "-poster") or f_lower.startswith(base_movie.lower() + "-cover"):
                        found_posters.append(f)

                # Find the single best master poster
                master_poster = None
                poster_prio = [
                    "poster.jpg", "poster.png", "poster.webp",
                    "folder.jpg", "folder.png", "folder.webp",
                    "cover.jpg", "cover.png", "cover.webp",
                    "default.jpg", "default.png", "default.webp",
                ]
                for p_name in poster_prio:
                    for f in found_posters:
                        if f.lower() == p_name:
                            master_poster = f
                            break
                    if master_poster:
                        break
                if not master_poster and found_posters:
                    master_poster = found_posters[0]

                # Determine poster core targets
                target_posters = ["poster"]
                if server_type in ("emby", "jellyfin"):
                    target_posters.append("folder")

                # If master poster exists, copy/rename it and delete others
                if master_poster:
                    master_path = os.path.join(dest_movie_dir_outbox, master_poster)
                    _, ext = os.path.splitext(master_poster)
                    ext = ext.lower()

                    core_poster_names = [f"{t_base}{ext}" for t_base in target_posters]
                    for core_name in core_poster_names:
                        core_path = os.path.join(dest_movie_dir_outbox, core_name)
                        if not os.path.exists(core_path):
                            shutil.copy(master_path, core_path)
                            log_message(f"Erstellt (Filmplakat-Kompatibilität): {core_name}")

                    # Remove all other poster files (candidates) that are not the allowed core names
                    for f in found_posters:
                        if f not in core_poster_names:
                            try:
                                os.remove(os.path.join(dest_movie_dir_outbox, f))
                                log_message(f"Bereinigt (Poster-Duplikat entfernt): {f}")
                            except Exception:
                                pass

                # --- 2. Find all backdrop candidates ---
                backdrop_candidates = [
                    "fanart.jpg", "fanart.png", "fanart.webp",
                    "backdrop.jpg", "backdrop.png", "backdrop.webp",
                    "background.jpg", "background.png", "background.webp",
                    "backgrounds.jpg", "backgrounds.png", "backgrounds.webp",
                    "art.jpg", "art.png", "art.webp",
                ]
                found_backdrops = []
                for f in all_outbox_files:
                    f_lower = f.lower()
                    if f_lower in backdrop_candidates or f_lower.startswith(base_movie.lower() + "-fanart") or f_lower.startswith(base_movie.lower() + "-backdrop"):
                        found_backdrops.append(f)

                # Find the single best master backdrop
                master_backdrop = None
                backdrop_prio = [
                    "fanart.jpg", "fanart.png", "fanart.webp",
                    "backdrop.jpg", "backdrop.png", "backdrop.webp",
                    "background.jpg", "background.png", "background.webp",
                    "backgrounds.jpg", "backgrounds.png", "backgrounds.webp",
                    "art.jpg", "art.png", "art.webp",
                ]
                for b_name in backdrop_prio:
                    for f in found_backdrops:
                        if f.lower() == b_name:
                            master_backdrop = f
                            break
                    if master_backdrop:
                        break
                if not master_backdrop and found_backdrops:
                    master_backdrop = found_backdrops[0]

                # Determine backdrop core targets (fanart.ext and backdrop.ext are two allowed core names)
                target_backdrops = ["fanart", "backdrop"]

                # If master backdrop exists, copy/rename it and delete others
                if master_backdrop:
                    master_path = os.path.join(dest_movie_dir_outbox, master_backdrop)
                    _, ext = os.path.splitext(master_backdrop)
                    ext = ext.lower()

                    core_backdrop_names = [f"{t_base}{ext}" for t_base in target_backdrops]
                    for core_name in core_backdrop_names:
                        core_path = os.path.join(dest_movie_dir_outbox, core_name)
                        if not os.path.exists(core_path):
                            shutil.copy(master_path, core_path)
                            log_message(f"Erstellt (Hintergrundbild-Kompatibilität): {core_name}")

                    # Remove all other backdrop files (candidates) that are not the allowed core names
                    for f in found_backdrops:
                        if f not in core_backdrop_names:
                            try:
                                os.remove(os.path.join(dest_movie_dir_outbox, f))
                                log_message(f"Bereinigt (Hintergrund-Duplikat entfernt): {f}")
                            except Exception:
                                pass

                # --- 3. Clean up logo and banner title-specific duplicates ---
                all_outbox_files_now = os.listdir(dest_movie_dir_outbox)
                for f in all_outbox_files_now:
                    f_lower = f.lower()
                    if f_lower.startswith(base_movie.lower() + "-logo") or f_lower.startswith(base_movie.lower() + "-clearlogo"):
                        _, ext = os.path.splitext(f)
                        logo_target = f"logo{ext.lower()}"
                        if not os.path.exists(os.path.join(dest_movie_dir_outbox, logo_target)):
                            shutil.copy(os.path.join(dest_movie_dir_outbox, f), os.path.join(dest_movie_dir_outbox, logo_target))
                        try:
                            os.remove(os.path.join(dest_movie_dir_outbox, f))
                        except Exception:
                            pass
                    elif f_lower.startswith(base_movie.lower() + "-banner"):
                        _, ext = os.path.splitext(f)
                        banner_target = f"banner{ext.lower()}"
                        if not os.path.exists(os.path.join(dest_movie_dir_outbox, banner_target)):
                            shutil.copy(os.path.join(dest_movie_dir_outbox, f), os.path.join(dest_movie_dir_outbox, banner_target))
                        try:
                            os.remove(os.path.join(dest_movie_dir_outbox, f))
                        except Exception:
                            pass

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
                            "explicit_remote_base": explicit_pcloud_base if t_id == "pcloud" else None,
                            "clean_movie_name": clean_movie_name
                        })
                else:
                    if t_id in target_progresses:
                        target_progresses[t_id][file_idx] = 100

            update_global_job_progress()

        _mark_convert_step_done(task_id)

        # Send Sentinel and join
        transfer_queue.put(None)
        transfer_thread.join()

        _mark_remaining_steps_done(task_id)

        _finalize_job(params, job_size_gb, transfer_errors, current_dir, inbox_root, log_message)

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
        inbox_root = settings.get("inbox_dir", "")
        nas_root = settings.get("nas_root", "")
        if not inbox_root:
            raise RuntimeError("Inbox-Verzeichnis ist nicht konfiguriert.")

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

                if get_runtime_capabilities().get("runtime") != "docker":
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

                    if get_runtime_capabilities().get("runtime") != "docker":
                        cmd.extend(["--cookies-from-browser", "chrome", part_url])
                    else:
                        cmd.extend([part_url])

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
                            trash.send_to_trash(primary_filepath)
                            log_message("Ungeschnittene Originaldatei in Quarantäne verschoben.")
                        except Exception as e:
                            log_message(f"Fehler beim In-Quarantäne-Verschieben des Originals: {e}")
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

                            poster_names, backdrop_names = _get_movie_artwork_lists(settings, target_filename)
                            pref_poster = poster_names[0] if poster_names else "poster.jpg"
                            pref_backdrop = backdrop_names[0] if backdrop_names else "fanart.jpg"

                            for filename_artwork in [pref_poster, pref_backdrop]:
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

                    # Ensure all server-specific poster/backdrop variants exist in outbox
                    poster_names, backdrop_names = _get_movie_artwork_lists(settings, target_filename)

                    existing_poster_src = None
                    for p_name in poster_names:
                        p_path = os.path.join(temp_dir, p_name)
                        if os.path.exists(p_path):
                            existing_poster_src = p_path
                            break
                    if existing_poster_src:
                        for p_name in poster_names:
                            shutil.copy(existing_poster_src, os.path.join(dest_dir_outbox, p_name))
                            log_message(f"  ✅ Filmplakat kopiert: {p_name}")

                    existing_backdrop_src = None
                    for b_name in backdrop_names:
                        b_path = os.path.join(temp_dir, b_name)
                        if os.path.exists(b_path):
                            existing_backdrop_src = b_path
                            break
                    if existing_backdrop_src:
                        for b_name in backdrop_names:
                            shutil.copy(existing_backdrop_src, os.path.join(dest_dir_outbox, b_name))
                            log_message(f"  ✅ Hintergrundbild kopiert: {b_name}")

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
                    nas_root = nas_target.get("root_path", "") if nas_target else settings.get("nas_root", "")

                    rel_sub = ""
                    if nas_root and destination.startswith(nas_root):
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
                                    # Copy all server-specific movie artwork variants to target
                                    poster_names, backdrop_names = _get_movie_artwork_lists(settings, target_filename)
                                    for p_name in poster_names:
                                        p_src = os.path.join(dest_dir_outbox, p_name)
                                        if os.path.exists(p_src):
                                            shutil.copy(p_src, os.path.join(dest_dir_target, p_name))
                                    for b_name in backdrop_names:
                                        b_src = os.path.join(dest_dir_outbox, b_name)
                                        if os.path.exists(b_src):
                                            shutil.copy(b_src, os.path.join(dest_dir_target, b_name))
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
                    meta_files = _get_series_meta_files(settings)
                    for f in meta_files:
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
                            meta_files = _get_series_meta_files(settings)
                            for f in meta_files:
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
                            poster_names, backdrop_names = _get_movie_artwork_lists(settings, target_filename)
                            if f.startswith(clean_base) or f in poster_names or f in backdrop_names:
                                shutil.copy2(f_path, os.path.join(local_dest_dir, f))

                    # Copy show-level files for series
                    if metadata_mode == "tv" and show_id and dest_show_dir_outbox and os.path.isdir(dest_show_dir_outbox):
                        local_show_dir = os.path.join(local_destination_path, clean_show_name)
                        os.makedirs(local_show_dir, exist_ok=True)
                        meta_files = _get_series_meta_files(settings)
                        for f in meta_files:
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

            from gui.core.jobs import update_job
            if not all_transfers_successful:
                update_job(task_id, status="error", message="Übertragung unvollständig oder fehlgeschlagen")
            else:
                update_job(task_id, status="done", progress=100, message="Erfolgreich beendet")

        except Exception as e:
            log_message(f"❌ Fehler in YouTube-Pipeline: {e}")
            from gui.core.jobs import update_job
            update_job(task_id, status="error", message=f"Fehler: {str(e)}")
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
                    base = os.path.splitext(f)[0]
                    temp_output = os.path.join(current_dir, f"{base}_neu.mkv")
                    conv_success, conv_file = media.execute_video_conversion(
                        target_filepath=filepath,
                        temp_output=temp_output,
                        final_filepath=os.path.join(current_dir, f"{base}.mkv"),
                        quality=quality,
                        content_type=content_type,
                        original_filename=f,
                        delete_original=True,
                        progress_callback=task_id,
                        log_message_fn=log_message,
                        run_ffmpeg_fn=run_ffmpeg_with_progress,
                        send_to_trash_fn=trash.send_to_trash,
                        log_queue=log_queue
                    )
                    if conv_success:
                        log_message(f"Erfolgreich konvertiert: {f}")

    elif media_type == "tool_nfo_agent":
        log_message(f"=== STARTE NFO AGENT IN: {current_dir} ===")
        log_message("💡 Tipp: Nutze den Inbox-Workflow, suche den Film/Serie, und deaktiviere 'Konvertieren' und 'Auf das NAS verschieben'.")
        log_message("Dies generiert NFO und Bilder direkt im aktuellen Ordner, ohne Dateien zu verschieben.")


    elif media_type == "tool_manual_sync":
        cat_id = params.get("category_id")
        open_after = params.get("open_after", False)
        delete_original = params.get("delete_original", False)
        task_id = params.get("task_id")
        
        settings = load_settings()
        category = next((c for c in settings.get("sync_categories", []) if str(c.get("id")) == str(cat_id)), None)
        if not category:
            raise RuntimeError("Keine gültige Kategorie ausgewählt oder gefunden.")
            
        log_message(f"=== STARTE MANUELLES SYNC FÜR KATEGORIE: {category.get('name')} ===")
        all_success = True
        any_attempted = False
        
        for target in settings.get("storage_targets", []):
            t_id = target.get("id")
            if target.get("enabled") is False:
                continue
            if not params.get(f"copy_to_{t_id}", False):
                continue
                
            any_attempted = True
            log_message(f"Bereite Sync für Ziel '{target.get('name')}' vor...")
            
            if target.get("type") == "nas" or t_id == "nas":
                if not ensure_nas_mounted():
                    log_message(f"❌ NAS konnte nicht gemountet werden. Kopiervorgang für {target.get('name')} abgebrochen.")
                    all_success = False
                    continue
                
                # Resolve NAS path
                rel_sub = category.get("targets", {}).get(t_id)
                if not rel_sub and t_id == "nas":
                    rel_sub = category.get("nas_sub", "")
                
                if not rel_sub:
                    log_message(f"❌ Kein Zielpfad-Mapping konfiguriert für Ziel {target.get('name')}.")
                    all_success = False
                    continue

                root_path = target.get("root_path", "")
                dest = os.path.join(root_path, rel_sub.lstrip('/')) if root_path and not rel_sub.startswith(root_path) else rel_sub
                
                folder_name = os.path.basename(current_dir.rstrip('/'))
                nas_target = os.path.join(dest, folder_name)
                
                log_message(f"Kopiere Ordner auf NAS: {nas_target}")
                try:
                    success = run_rsync_with_progress(current_dir, nas_target, task_id)
                    if success:
                        log_message(f"✅ Erfolgreich auf {target.get('name')} synchronisiert.")
                        if open_after:
                            open_folder_in_finder(nas_target)
                    else:
                        log_message(f"❌ Fehler bei Sync für {target.get('name')}.")
                        all_success = False
                except Exception as e:
                    log_message(f"❌ Ausnahme bei Sync für {target.get('name')}: {e}")
                    all_success = False
            else:
                # Cloud target
                t_sub = category.get("targets", {}).get(t_id)
                if not t_sub and t_id == "pcloud":
                    t_sub = category.get("pcloud_remote", "")
                
                if not t_sub:
                    log_message(f"❌ Kein Remote-Zielpfad-Mapping konfiguriert für Cloud-Ziel {target.get('name')}.")
                    all_success = False
                    continue

                success = copy_to_cloud_target(
                    current_dir, 
                    "", 
                    t_id, 
                    task_id, 
                    explicit_remote_base=t_sub
                )
                if not success:
                    all_success = False

        if not any_attempted:
            raise RuntimeError("Keine Speicherziele ausgewählt oder Mapping ungültig.")
            
        if not all_success:
            raise RuntimeError("Fehler bei mindestens einem Synchronisations-Ziel.")

        if delete_original and all_success:
            log_message(f"🗑️ Lösche Originalordner nach erfolgreichem Transfer: {current_dir}")
            try:
                trash.send_to_trash(current_dir)
            except Exception as e:
                log_message(f"⚠️ Konnte Originalordner nicht in Quarantäne verschieben: {e}")

    elif media_type == "tool_pcloud_sync":
        dest = params.get("destination", "")
        if not dest:
            raise RuntimeError("Sync-Ziel (destination) ist nicht konfiguriert.")
        open_after = params.get("open_after", False)
        delete_original = params.get("delete_original", False)
        task_id = params.get("task_id")

        log_message(f"=== STARTE REINEN PCLOUD SYNC FÜR: {dest} ===")
        success = copy_to_pcloud(current_dir, dest, task_id)

        if success and delete_original:
            log_message(f"🗑️ Lösche Originalordner nach erfolgreichem Transfer: {current_dir}")
            try:
                trash.send_to_trash(current_dir)
            except Exception as e:
                log_message(f"⚠️ Konnte Originalordner nicht in Quarantäne verschieben: {e}")

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
        from gui.core.jobs import update_job, get_job
        update_job(task_id, status="running", message="Verarbeitung gestartet...")

        try:
            params = job["params"]
            params["task_id"] = task_id
            process_worker(params)

            job_state = get_job(task_id)
            if job_state and job_state.get("status") != "error":
                update_job(task_id, status="done", progress=100, message="Erfolgreich beendet")
        except Exception as e:
            job_state = get_job(task_id)
            pipeline = None
            if job_state and "pipeline" in job_state:
                pipeline = job_state["pipeline"]
                for step_key, step_info in pipeline.items():
                    if step_info.get("status") in ["running", "pending"]:
                        step_info["status"] = "error"
                        step_info["message"] = "Fehlgeschlagen"
            update_job(task_id, status="error", message=f"Fehler: {str(e)}", pipeline=pipeline)
            print(f"Job {task_id} failed: {e}")
        finally:
            job_queue.task_done()

_rclone_about_cache = {}
_RCLONE_ABOUT_TTL = 300

def _rclone_about(remote):
    import subprocess, json, time
    now = time.time()
    cached = _rclone_about_cache.get(remote)
    if cached and now - cached[0] < _RCLONE_ABOUT_TTL:
        return cached[1]
    data = None
    try:
        out = subprocess.check_output(["rclone", "about", remote, "--json"], text=True, timeout=20)
        parsed = json.loads(out)
        if parsed.get("total"):
            data = {"total": parsed.get("total"), "used": parsed.get("used"), "free": parsed.get("free")}
    except Exception:
        data = None
    _rclone_about_cache[remote] = (now, data)
    return data

def _read_target_storage(target):
    import shutil, os
    info = {
        "name": target.get("name", ""),
        "type": target.get("type", ""),
        "available": False,
        "total": None, "used": None, "free": None, "used_percent": None,
        "path": target.get("root_path", ""),
    }
    remote = (target.get("rclone_remote") or "").strip()
    if remote:
        about = _rclone_about(remote)
        if about and about.get("total"):
            info["available"] = True
            info["path"] = remote
            info["total"] = about["total"]
            info["used"] = about.get("used")
            info["free"] = about.get("free")
            if about["total"] > 0 and about.get("used") is not None:
                info["used_percent"] = round((about["used"] / about["total"]) * 100, 2)
        return info

    root_path = target.get("root_path")
    if root_path and os.path.exists(root_path):
        try:
            usage = shutil.disk_usage(root_path)
            info["available"] = True
            info["total"] = usage.total
            info["free"] = usage.free
            if usage.free > usage.total or usage.used < 0:
                info["usage_unreliable"] = True
            else:
                info["used"] = usage.used
                info["used_percent"] = round((usage.used / usage.total) * 100, 2) if usage.total > 0 else 0.0
        except Exception as e:
            info["error"] = str(e)
    return info

def system_metrics_worker():
    import time
    from gui.core.helpers import get_folder_size_bytes
    from gui.core.utils import load_settings

    def run_with_timeout(func, arg, timeout_sec=20):
        result = [None]
        def _worker():
            try:
                result[0] = func(arg)
            except Exception:
                pass
        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        t.join(timeout_sec)
        return result[0]

    while SYSTEM_STATUS.get('running', True):
        try:
            settings = load_settings()
            inbox = settings.get("inbox_dir", os.path.expanduser("~/Downloads/Medien Input"))
            outbox = settings.get("outbox_dir", os.path.expanduser("~/Downloads/Medien Output"))

            # 1. Berechne Ordnergrößen (mit 20s Timeout)
            inbox_bytes = run_with_timeout(get_folder_size_bytes, inbox, 20) if inbox else 0
            outbox_bytes = run_with_timeout(get_folder_size_bytes, outbox, 20) if outbox else 0
            with METRICS_LOCK:
                SYSTEM_METRICS['inbox_size_gb'] = round(inbox_bytes / (1024**3), 2) if inbox_bytes is not None else None
                SYSTEM_METRICS['outbox_size_gb'] = round(outbox_bytes / (1024**3), 2) if outbox_bytes is not None else None

            # 2. Berechne Speicherplatz (NAS/Cloud) mit 20s Timeout
            targets = [t for t in settings.get("storage_targets", []) if t.get("enabled", True)]
            nas_info = None
            for target in targets:
                candidate = run_with_timeout(_read_target_storage, target, 20)
                if candidate and candidate.get("available"):
                    nas_info = candidate
                    break

            if nas_info is None:
                nas_info = {
                    "name": targets[0]["name"] if targets else "",
                    "type": targets[0].get("type", "") if targets else "",
                    "available": False,
                    "total": None, "used": None, "free": None, "used_percent": None,
                    "path": targets[0].get("root_path", "") if targets else "",
                    "error": "Kein Speicherziel verbunden.",
                }

            with METRICS_LOCK:
                SYSTEM_METRICS['nas_info'] = nas_info
                SYSTEM_METRICS['last_updated'] = time.time()

        except Exception as e:
            print(f"[System Metrics Worker] Fehler: {e}")

        time.sleep(60)
