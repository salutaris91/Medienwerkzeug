import os
import time
import threading
import sys
import shutil
import copy

from gui.core.persistence import (
    get_jobs_state_file_path,
    read_json_file,
    write_json_file,
    update_json_file,
    jobs_state_lock
)

# Global memory state for active jobs
active_jobs = {}
active_jobs_lock = threading.Lock()
_load_jobs_lock = threading.Lock()
_jobs_loaded = False

# Throttle tracking
_last_saved_time = {}
_last_saved_progress = {}

def load_jobs_from_disk():
    """Initializes the memory state with jobs loaded from disk."""
    global active_jobs, _jobs_loaded
    file_path = get_jobs_state_file_path()
    disk_jobs = read_json_file(file_path, jobs_state_lock, {})
    with active_jobs_lock:
        active_jobs.clear()
        active_jobs.update(copy.deepcopy(disk_jobs))
        _jobs_loaded = True
    return disk_jobs

def save_jobs_to_disk():
    """Atomically writes the entire memory state of active jobs to disk."""
    global active_jobs
    file_path = get_jobs_state_file_path()
    with active_jobs_lock:
        data_to_write = copy.deepcopy(active_jobs)
    return write_json_file(file_path, jobs_state_lock, data_to_write)

def create_job(job_id, name, job_type, params, pipeline=None, status="queued"):
    """
    Creates a new job thread-safely in memory and persists it to disk immediately.
    """
    global active_jobs
    job = {
        "id": job_id,
        "name": name,
        "type": job_type,
        "status": status,
        "progress": 0,
        "message": "Wartet in der Warteschlange..." if status == "queued" else "Wird ausgeführt...",
        "timestamp": time.time(),
        "params": copy.deepcopy(params),
        "task_id": job_id
    }
    if pipeline:
        job["pipeline"] = copy.deepcopy(pipeline)

    with active_jobs_lock:
        active_jobs[job_id] = job

    # Persist immediately on creation
    save_jobs_to_disk()
    return job

def update_job(job_id, status=None, progress=None, message=None,
               pipeline_step=None, pipeline_status=None, pipeline_progress=None,
               pipeline_message=None, pipeline=None):
    """
    Updates a job's status, progress, or message.
    Updates the RAM state immediately. Throttles disk-writes for progress updates
    (maximum once per 1.5 seconds) to reduce disk I/O, but writes status changes immediately.
    """
    global active_jobs
    with active_jobs_lock:
        if job_id not in active_jobs:
            return False
        
        job = active_jobs[job_id]
        
        # Check if critical status has changed
        status_changed = False
        if status is not None and job.get("status") != status:
            job["status"] = status
            status_changed = True
            
        if progress is not None:
            job["progress"] = progress
            
        if message is not None:
            job["message"] = message

        if pipeline is not None:
            job["pipeline"] = copy.deepcopy(pipeline)
            status_changed = True
            
        # Update pipeline step values if provided
        if "pipeline" in job and pipeline_step is not None:
            step = job["pipeline"].get(pipeline_step)
            if step:
                if pipeline_status is not None:
                    if step.get("status") != pipeline_status:
                        step["status"] = pipeline_status
                        status_changed = True
                if pipeline_progress is not None:
                    step["progress"] = pipeline_progress
                if pipeline_message is not None:
                    step["message"] = pipeline_message

    # Determine whether we should write to disk immediately or throttle
    should_write = status_changed
    
    if not should_write and progress is not None:
        # Edge cases: 0% and 100% must always be written immediately
        if progress == 0 or progress == 100:
            should_write = True
        else:
            now = time.time()
            last_time = _last_saved_time.get(job_id, 0)
            last_progress = _last_saved_progress.get(job_id, -1)
            # Write if 1.5 seconds passed or progress leaped by 5%+
            if now - last_time >= 1.5 or abs(progress - last_progress) >= 5:
                should_write = True

    if should_write:
        save_jobs_to_disk()
        _last_saved_time[job_id] = time.time()
        if progress is not None:
            _last_saved_progress[job_id] = progress
            
    return True

def get_job(job_id):
    """Returns a copy of a job by ID from memory, fallback to disk."""
    global active_jobs
    with active_jobs_lock:
        if job_id in active_jobs:
            return copy.deepcopy(active_jobs[job_id])
            
    # Fallback to disk if cache missing
    file_path = get_jobs_state_file_path()
    disk_jobs = read_json_file(file_path, jobs_state_lock, {})
    job = disk_jobs.get(job_id)
    if job:
        with active_jobs_lock:
            active_jobs[job_id] = copy.deepcopy(job)
        return copy.deepcopy(job)
    return None

def get_all_jobs():
    """Returns a list of all jobs, sorted by timestamp."""
    global active_jobs, _jobs_loaded
    
    # 1. Fast-Path check
    with active_jobs_lock:
        needs_loading = not _jobs_loaded
        
    if needs_loading:
        # 2. Lock to prevent concurrent load operations
        with _load_jobs_lock:
            # Double-check under active_jobs_lock
            with active_jobs_lock:
                still_needs_loading = not _jobs_loaded
            if still_needs_loading:
                load_jobs_from_disk()
                
    # 3. Safely copy and sort
    with active_jobs_lock:
        jobs_list = list(active_jobs.values())
    
    jobs_copy = copy.deepcopy(jobs_list)
    jobs_copy.sort(key=lambda x: x.get("timestamp", 0))
    return jobs_copy

def clear_finished_jobs():
    """Removes completed, failed, or queued jobs from the active state and disk."""
    global active_jobs
    with active_jobs_lock:
        active_ids = list(active_jobs.keys())
        for j_id in active_ids:
            job = active_jobs[j_id]
            if job.get("status") in ("done", "error", "queued"):
                active_jobs.pop(j_id, None)
                _last_saved_time.pop(j_id, None)
                _last_saved_progress.pop(j_id, None)
                
    from gui.core.helpers import job_queue
    with job_queue.mutex:
        cleared_count = len(job_queue.queue)
        job_queue.queue.clear()
        job_queue.unfinished_tasks = max(0, job_queue.unfinished_tasks - cleared_count)
        if job_queue.unfinished_tasks == 0:
            job_queue.all_tasks_done.notify_all()
            
    return save_jobs_to_disk()

def recover_interrupted_jobs():
    """
    Invoked during startup. Checks jobs_state.json on disk.
    Any jobs with status 'running' or 'queued' are set to 'error'
    with a descriptive message since they were interrupted by an app crash/restart.
    """
    file_path = get_jobs_state_file_path()
    
    def mutate(disk_jobs):
        recovered = False
        for job_id, job in disk_jobs.items():
            if job.get("status") in ("running", "queued"):
                job["status"] = "error"
                job["message"] = "Prozess durch unerwarteten App-Neustart abgebrochen."
                if "pipeline" in job:
                    for step in job["pipeline"].values():
                        if step.get("status") in ("running", "pending"):
                            step["status"] = "error"
                            step["message"] = "Abgebrochen"
                recovered = True
                print(f"[Jobs] Recovered interrupted job {job_id} -> error", file=sys.stderr)
        return recovered

    # We use update_json_file to run the mutation transactionally
    update_json_file(file_path, jobs_state_lock, mutate, {})
    
    # Reload into memory after recovery
    load_jobs_from_disk()

def clean_orphaned_temp_files():
    """
    Finds temporary files with suffix .mwtmp or .mwtmp.mkv in inbox and outbox
    that are older than 12 hours, and moves them to the quarantine folder.
    """
    from gui.core.persistence import load_settings, get_data_dir_path
    settings = load_settings()
    data_dir = get_data_dir_path()
    quarantine_dir = os.path.join(data_dir, "quarantine")
    os.makedirs(quarantine_dir, exist_ok=True)
    
    inbox = settings.get("inbox_dir")
    outbox = settings.get("outbox_dir")
    
    now = time.time()
    max_age_seconds = 12 * 3600
    
    moved_count = 0
    for folder in [inbox, outbox]:
        if not folder or not os.path.exists(folder):
            continue
        for root, _, files in os.walk(folder):
            for f in files:
                if f.endswith(".mwtmp") or f.endswith(".mwtmp.mkv") or ".mwtmp." in f:
                    path = os.path.join(root, f)
                    try:
                        mtime = os.path.getmtime(path)
                        if now - mtime > max_age_seconds:
                            dest = os.path.join(quarantine_dir, f)
                            if os.path.exists(dest):
                                base, ext = os.path.splitext(f)
                                dest = os.path.join(quarantine_dir, f"{base}_{int(time.time())}{ext}")
                            shutil.move(path, dest)
                            print(f"[Jobs] Quarantined orphaned file: {path} -> {dest}", file=sys.stderr)
                            moved_count += 1
                    except Exception as e:
                        print(f"[Jobs] Failed to quarantine {path}: {e}", file=sys.stderr)
    return moved_count
