import os
import time
import threading
import signal
import sys
import shutil
import copy
from contextlib import contextmanager

from gui.core.persistence import (
    get_jobs_state_file_path,
    read_json_file,
    write_json_file,
    update_json_file,
    jobs_state_lock
)

ACTIVE_JOB_STATUSES = ("queued", "running", "pausing", "paused", "cancelling")
TERMINAL_JOB_STATUSES = ("done", "error", "cancelled")
PAUSE_PENDING_MESSAGE = "Pausiert nach aktuellem Schritt…"

_UNSET = object()


class JobCancelledError(Exception):
    """Raised when a queued, paused, or running job is cancelled by the user."""


class _JobControl:
    def __init__(self):
        self.cancel_event = threading.Event()
        self.resume_event = threading.Event()
        self.resume_event.set()
        self.procs = {}
        self.wait_events = []


class _JobRunContext:
    def __init__(self, task_id, ctrl=None):
        self.task_id = task_id
        self.ctrl = ctrl


# Global memory state for active jobs
# Strict lock hierarchy everywhere: job_queue.mutex -> active_jobs_lock -> _job_controls_lock
active_jobs = {}
active_jobs_lock = threading.Lock()
_job_controls = {}
_job_controls_lock = threading.Lock()
_job_thread_local = threading.local()

_load_jobs_lock = threading.Lock()
_jobs_loaded = False

# Throttle tracking
_last_saved_time = {}
_last_saved_progress = {}


def _get_or_create_control_locked(job_id):
    ctrl = _job_controls.get(job_id)
    if ctrl is None:
        ctrl = _JobControl()
        _job_controls[job_id] = ctrl
    return ctrl


def get_bound_job_control(explicit_task_id=None):
    job_id = resolve_job_id(explicit_task_id)
    if not job_id:
        return None
    run_ctx = getattr(_job_thread_local, "run_ctx", None)
    if run_ctx is not None and run_ctx.task_id == job_id and run_ctx.ctrl is not None:
        return run_ctx.ctrl
    return None


def get_job_control(job_id):
    bound = get_bound_job_control(job_id)
    if bound is not None:
        return bound
    with _job_controls_lock:
        return _get_or_create_control_locked(job_id)


def reset_job_control(job_id):
    if not job_id:
        return
    with _job_controls_lock:
        _job_controls[job_id] = _JobControl()


def cleanup_job_control(job_id, expected_ctrl=_UNSET):
    if not job_id:
        return
    if expected_ctrl is _UNSET:
        bound = get_bound_job_control(job_id)
        if bound is not None:
            expected_ctrl = bound
    with _job_controls_lock:
        if expected_ctrl is _UNSET:
            _job_controls.pop(job_id, None)
        elif expected_ctrl is not None and _job_controls.get(job_id) is expected_ctrl:
            _job_controls.pop(job_id, None)


@contextmanager
def bind_job_context(task_id, ctrl=None):
    clean_id = task_id if isinstance(task_id, str) and task_id else None
    prev_id = getattr(_job_thread_local, "task_id", None)
    prev_ctx = getattr(_job_thread_local, "run_ctx", None)
    resolved_ctrl = ctrl
    if resolved_ctrl is None and clean_id:
        if prev_ctx is not None and prev_ctx.task_id == clean_id and prev_ctx.ctrl is not None:
            resolved_ctrl = prev_ctx.ctrl
        else:
            with _job_controls_lock:
                resolved_ctrl = _job_controls.get(clean_id)
    run_ctx = _JobRunContext(clean_id, resolved_ctrl)
    _job_thread_local.task_id = clean_id
    _job_thread_local.run_ctx = run_ctx
    try:
        yield run_ctx
    finally:
        if prev_id is None:
            if hasattr(_job_thread_local, "task_id"):
                delattr(_job_thread_local, "task_id")
        else:
            _job_thread_local.task_id = prev_id
        if prev_ctx is None:
            if hasattr(_job_thread_local, "run_ctx"):
                delattr(_job_thread_local, "run_ctx")
        else:
            _job_thread_local.run_ctx = prev_ctx


def resolve_job_id(explicit_task_id=None):
    if isinstance(explicit_task_id, str) and explicit_task_id:
        return explicit_task_id
    tl_id = getattr(_job_thread_local, "task_id", None)
    if isinstance(tl_id, str) and tl_id:
        return tl_id
    from gui.core.helpers import get_current_task_id
    cur = get_current_task_id()
    if isinstance(cur, str) and cur and cur != "None":
        return cur
    return None


def _terminate_process_groups(procs, kill_after_sec=1.5):
    """Sends SIGTERM to process groups outside locks and reaps survivors with SIGKILL."""
    targets = []
    for proc in procs:
        if proc is None:
            continue
        pgid = None
        if os.name != "nt":
            try:
                pgid = os.getpgid(proc.pid)
            except (ProcessLookupError, PermissionError, OSError):
                pgid = proc.pid
            try:
                os.killpg(pgid, signal.SIGTERM)
                targets.append((proc, pgid))
            except (ProcessLookupError, PermissionError, OSError):
                pass
        else:
            try:
                if proc.poll() is None:
                    proc.terminate()
                    targets.append((proc, None))
            except OSError:
                pass

    if not targets:
        return

    def _reap_survivors():
        deadline = time.monotonic() + kill_after_sec
        while time.monotonic() < deadline:
            still_alive = False
            for proc, pgid in targets:
                if os.name != "nt" and pgid is not None:
                    try:
                        os.killpg(pgid, 0)
                        still_alive = True
                        break
                    except ProcessLookupError:
                        continue
                    except PermissionError:
                        still_alive = True
                        break
                else:
                    if proc.poll() is None:
                        still_alive = True
                        break
            if not still_alive:
                return
            time.sleep(0.05)

        for proc, pgid in targets:
            if os.name != "nt" and pgid is not None:
                try:
                    os.killpg(pgid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError, OSError):
                    pass
            else:
                try:
                    if proc.poll() is None:
                        proc.kill()
                except OSError:
                    pass

    threading.Thread(target=_reap_survivors, name="job-proc-reaper", daemon=True).start()


def register_job_process(explicit_task_id, proc):
    job_id = resolve_job_id(explicit_task_id)
    if not job_id or proc is None:
        return
    bound = get_bound_job_control(job_id)
    with _job_controls_lock:
        ctrl = bound if bound is not None else _get_or_create_control_locked(job_id)
        already_cancelled = ctrl.cancel_event.is_set()
        ctrl.procs[proc.pid] = proc
    if already_cancelled:
        _terminate_process_groups([proc])


def unregister_job_process(explicit_task_id, proc):
    job_id = resolve_job_id(explicit_task_id)
    if not job_id or proc is None:
        return
    bound = get_bound_job_control(job_id)
    with _job_controls_lock:
        ctrl = bound if bound is not None else _job_controls.get(job_id)
        if ctrl is not None:
            ctrl.procs.pop(proc.pid, None)


def register_job_wait_event(explicit_task_id, ev):
    job_id = resolve_job_id(explicit_task_id)
    if not job_id or ev is None:
        return
    bound = get_bound_job_control(job_id)
    with _job_controls_lock:
        ctrl = bound if bound is not None else _get_or_create_control_locked(job_id)
        if ev not in ctrl.wait_events:
            ctrl.wait_events.append(ev)
        if ctrl.cancel_event.is_set():
            ev.set()


def is_job_cancelled(explicit_task_id=None):
    job_id = resolve_job_id(explicit_task_id)
    if not job_id:
        return False
    bound = get_bound_job_control(job_id)
    with active_jobs_lock:
        job = active_jobs.get(job_id)
        status = job.get("status") if job else None
        with _job_controls_lock:
            if bound is not None:
                if bound.cancel_event.is_set():
                    return True
                if _job_controls.get(job_id) is bound:
                    return status in ("cancelling", "cancelled")
                return False
            ctrl = _job_controls.get(job_id)
            if ctrl is not None and ctrl.cancel_event.is_set():
                return True
    return status in ("cancelling", "cancelled")


def check_cancelled(explicit_task_id=None):
    if is_job_cancelled(explicit_task_id):
        raise JobCancelledError("Vom Benutzer abgebrochen")


def wait_if_paused_or_cancelled(explicit_task_id=None, _claim_if_queued=False):
    """Cooperative pause/cancel checkpoint with atomic lock synchronization."""
    job_id = resolve_job_id(explicit_task_id)
    if not job_id:
        return
    bound = get_bound_job_control(job_id)
    while True:
        should_save = False
        resume_ev = None
        with active_jobs_lock:
            job = active_jobs.get(job_id)
            with _job_controls_lock:
                cur_ctrl = _job_controls.get(job_id)
                ctrl = bound if bound is not None else cur_ctrl
                is_current_run = bound is None or cur_ctrl is bound
                if (ctrl is not None and ctrl.cancel_event.is_set()) or (
                    is_current_run and job is not None and job.get("status") in ("cancelling", "cancelled")
                ):
                    raise JobCancelledError("Vom Benutzer abgebrochen")
                if ctrl is None or ctrl.resume_event.is_set():
                    if (
                        is_current_run
                        and job is not None
                        and job.get("paused_from") != "queued"
                        and (
                            job.get("status") in ("pausing", "paused")
                            or (_claim_if_queued and job.get("status") == "queued")
                        )
                    ):
                        job["status"] = "running"
                        job["paused_from"] = None
                        job["message"] = (
                            "Verarbeitung gestartet..." if _claim_if_queued else "Verarbeitung wird fortgesetzt..."
                        )
                        should_save = True
                else:
                    resume_ev = ctrl.resume_event
                    if is_current_run and job is not None and job.get("status") != "paused":
                        job["status"] = "paused"
                        if not job.get("paused_from"):
                            job["paused_from"] = "running"
                        job["message"] = "Pausiert"
                        should_save = True
        if should_save:
            save_jobs_to_disk()
        if resume_ev is None:
            return
        resume_ev.wait()


def is_confirmed_manifest_entry(entry):
    return isinstance(entry, dict) and not entry.get("provisional")


def _strip_provisional_manifest(manifest):
    if not isinstance(manifest, dict):
        return manifest
    return {
        k: copy.deepcopy(v)
        for k, v in manifest.items()
        if is_confirmed_manifest_entry(v)
    }


def prepare_outbox_manifest_entry(job_id, key, entry):
    """Atomically verifies job is not cancelled and records provisional Outbox manifest before moving."""
    resolved_id = resolve_job_id(job_id)
    if not resolved_id or not key or not isinstance(entry, dict):
        return
    bound = get_bound_job_control(resolved_id)
    should_save = False
    with active_jobs_lock:
        job = active_jobs.get(resolved_id)
        with _job_controls_lock:
            cur_ctrl = _job_controls.get(resolved_id)
            ctrl = bound if bound is not None else cur_ctrl
            is_current_run = bound is None or cur_ctrl is bound
            if (ctrl is not None and ctrl.cancel_event.is_set()) or (
                is_current_run and job is not None and job.get("status") in ("cancelling", "cancelled")
            ):
                raise JobCancelledError("Vom Benutzer abgebrochen")
            if is_current_run and job is not None and job.get("status") not in TERMINAL_JOB_STATUSES:
                mf = job.get("manifest")
                if not isinstance(mf, dict):
                    mf = {}
                    job["manifest"] = mf
                if not is_confirmed_manifest_entry(mf.get(key)):
                    prov = copy.deepcopy(entry)
                    prov["provisional"] = True
                    mf[key] = prov
                    should_save = True
    if should_save:
        save_jobs_to_disk()


def commit_job_manifest(job_id, manifest):
    """Persists confirmed Outbox manifest entries even if status transitioned to 'cancelling' mid-move."""
    resolved_id = resolve_job_id(job_id)
    if not resolved_id or manifest is None:
        return False
    bound = get_bound_job_control(resolved_id)
    should_save = False
    with active_jobs_lock:
        job = active_jobs.get(resolved_id)
        with _job_controls_lock:
            cur_ctrl = _job_controls.get(resolved_id)
            is_current_run = bound is None or cur_ctrl is bound
        if job is not None and is_current_run and job.get("status") not in TERMINAL_JOB_STATUSES:
            job["manifest"] = _strip_provisional_manifest(manifest)
            should_save = True
    if should_save:
        save_jobs_to_disk()
    return should_save


def _remove_job_from_queue_locked(job_id):
    """Removes matching job entries from job_queue while job_queue.mutex is held."""
    from gui.core.helpers import job_queue
    kept = []
    removed_count = 0
    for item in job_queue.queue:
        if isinstance(item, dict) and item.get("id") == job_id:
            removed_count += 1
        else:
            kept.append(item)
    if removed_count > 0:
        job_queue.queue.clear()
        job_queue.queue.extend(kept)
        job_queue.unfinished_tasks = max(0, job_queue.unfinished_tasks - removed_count)
        if job_queue.unfinished_tasks == 0:
            job_queue.all_tasks_done.notify_all()
    return removed_count


def _mark_open_pipeline_steps_cancelled_locked(job):
    pipeline = job.get("pipeline")
    if isinstance(pipeline, dict):
        for step in pipeline.values():
            if isinstance(step, dict) and step.get("status") in ("pending", "running"):
                step["status"] = "cancelled"
                step["message"] = "Abgebrochen"


def pause_job(job_id):
    from gui.core.helpers import job_queue
    with job_queue.mutex:
        with active_jobs_lock:
            job = active_jobs.get(job_id)
            if job is None:
                return False, 404, "Job nicht gefunden"
            status = job.get("status")
            if status not in ("queued", "running"):
                return False, 400, f"Job im Status '{status}' kann nicht pausiert werden"
            with _job_controls_lock:
                ctrl = _get_or_create_control_locked(job_id)
                if status == "queued":
                    removed_count = _remove_job_from_queue_locked(job_id)
                    if removed_count > 0:
                        job["status"] = "paused"
                        job["paused_from"] = "queued"
                        job["message"] = "Pausiert (wartend)"
                        new_status = "paused"
                    else:
                        ctrl.resume_event.clear()
                        job["status"] = "pausing"
                        job["paused_from"] = "running"
                        job["message"] = PAUSE_PENDING_MESSAGE
                        new_status = "pausing"
                else:
                    ctrl.resume_event.clear()
                    job["status"] = "pausing"
                    job["paused_from"] = "running"
                    job["message"] = PAUSE_PENDING_MESSAGE
                    new_status = "pausing"
    save_jobs_to_disk()
    return True, 200, new_status


def resume_job(job_id):
    from gui.core.helpers import job_queue
    with job_queue.mutex:
        with active_jobs_lock:
            job = active_jobs.get(job_id)
            if job is None:
                return False, 404, "Job nicht gefunden"
            status = job.get("status")
            if status not in ("paused", "pausing"):
                return False, 400, f"Job im Status '{status}' kann nicht fortgesetzt werden"
            with _job_controls_lock:
                ctrl = _get_or_create_control_locked(job_id)
                paused_from = job.get("paused_from")
                ctrl.resume_event.set()
                if paused_from == "queued":
                    job["status"] = "queued"
                    job["paused_from"] = None
                    job["message"] = "Wartet in der Warteschlange..."
                    already_in_q = any(
                        isinstance(it, dict) and it.get("id") == job_id
                        for it in job_queue.queue
                    )
                    if not already_in_q:
                        job_queue.queue.appendleft(copy.deepcopy(job))
                        job_queue.unfinished_tasks += 1
                        job_queue.not_empty.notify()
                    new_status = "queued"
                else:
                    job["paused_from"] = None
                    job["status"] = "running"
                    job["message"] = "Verarbeitung wird fortgesetzt..."
                    new_status = "running"
    save_jobs_to_disk()
    return True, 200, new_status


def cancel_job(job_id):
    from gui.core.helpers import job_queue
    procs_snapshot = []
    with job_queue.mutex:
        with active_jobs_lock:
            job = active_jobs.get(job_id)
            if job is None:
                return False, 404, "Job nicht gefunden"
            status = job.get("status")
            if status in TERMINAL_JOB_STATUSES:
                return False, 400, f"Job ist bereits abgeschlossen ({status})"
            with _job_controls_lock:
                ctrl = _get_or_create_control_locked(job_id)
                if status == "cancelling":
                    ctrl.cancel_event.set()
                    ctrl.resume_event.set()
                    for ev in ctrl.wait_events:
                        ev.set()
                    procs_snapshot = list(ctrl.procs.values())
                    new_status = "cancelling"
                else:
                    removed_count = _remove_job_from_queue_locked(job_id)
                    is_waiting_only = (
                        (status == "queued" and removed_count > 0)
                        or (status == "paused" and job.get("paused_from") == "queued")
                    )
                    ctrl.cancel_event.set()
                    ctrl.resume_event.set()
                    for ev in ctrl.wait_events:
                        ev.set()
                    if is_waiting_only:
                        job["status"] = "cancelled"
                        job["paused_from"] = None
                        job["message"] = "Vom Benutzer abgebrochen"
                        _mark_open_pipeline_steps_cancelled_locked(job)
                        _job_controls.pop(job_id, None)
                        new_status = "cancelled"
                    else:
                        job["status"] = "cancelling"
                        job["paused_from"] = None
                        job["message"] = "Wird abgebrochen..."
                        procs_snapshot = list(ctrl.procs.values())
                        new_status = "cancelling"
    if procs_snapshot:
        _terminate_process_groups(procs_snapshot)
    save_jobs_to_disk()
    return True, 200, new_status


def retry_job(job_id, build_pipeline_fn):
    """
    Atomically validates terminal status, resets job control + state, and enqueues
    under job_queue.mutex -> active_jobs_lock -> _job_controls_lock.
    """
    from gui.core.helpers import job_queue

    snap = get_job(job_id)
    if not snap:
        return False, 404, "Job nicht gefunden"

    preview_params = copy.deepcopy(snap.get("params") or {})
    preview_type = preview_params.get("media_type") or snap.get("type")
    ref_pipeline = None
    if preview_type not in (None, "", "unknown", "normalize"):
        preview_params.setdefault("media_type", preview_type)
        ref_pipeline = build_pipeline_fn(preview_params)

    with job_queue.mutex:
        with active_jobs_lock:
            job = active_jobs.get(job_id)
            if job is None:
                return False, 404, "Job nicht gefunden"

            if job.get("status") not in TERMINAL_JOB_STATUSES:
                return False, 400, "Job ist nicht fehlgeschlagen, abgebrochen oder beendet"

            job_params = copy.deepcopy(job.get("params") or {})
            effective_type = job_params.get("media_type") or job.get("type")
            if effective_type in (None, "", "unknown", "normalize"):
                return False, 400, "Dieser Aufgabentyp unterstützt keine Wiederholung."

            job_params.setdefault("media_type", effective_type)
            if ref_pipeline is None or job_params != preview_params:
                ref_pipeline = build_pipeline_fn(job_params)

            old_pipeline = job.get("pipeline") or {}
            new_pipeline = {}
            for step_key, ref_val in ref_pipeline.items():
                old_step = old_pipeline.get(step_key, {})
                if old_step.get("status") == "done":
                    new_pipeline[step_key] = {"status": "done", "progress": 100}
                elif old_step.get("status") == "skipped":
                    new_pipeline[step_key] = {"status": "skipped", "progress": 0}
                elif ref_val.get("status") == "skipped":
                    new_pipeline[step_key] = {"status": "skipped", "progress": 0}
                else:
                    new_pipeline[step_key] = {"status": "pending", "progress": 0}

            with _job_controls_lock:
                _job_controls[job_id] = _JobControl()

            job["status"] = "queued"
            job["progress"] = 0
            job["message"] = "Wiederholung eingereiht..."
            job["pipeline"] = new_pipeline
            job["params"] = job_params
            job["paused_from"] = None
            if isinstance(job.get("manifest"), dict):
                job["manifest"] = _strip_provisional_manifest(job["manifest"])

            _remove_job_from_queue_locked(job_id)
            job_queue.queue.append(copy.deepcopy(job))
            job_queue.unfinished_tasks += 1
            job_queue.not_empty.notify()

    save_jobs_to_disk()
    _last_saved_time[job_id] = time.time()
    _last_saved_progress[job_id] = 0
    return True, 200, "queued"


def claim_or_skip_dequeued_job(task_id):
    """
    Atomically claims a job popped by job_queue_worker.
    Returns (claimed: bool, keep_control: bool).
    Raises JobCancelledError if job is already cancelling.
    """
    needs_pause_wait = False
    should_save = False
    run_ctx = getattr(_job_thread_local, "run_ctx", None)
    with active_jobs_lock:
        job = active_jobs.get(task_id)
        if job is None or job.get("status") in TERMINAL_JOB_STATUSES:
            if run_ctx is not None and run_ctx.task_id == task_id:
                run_ctx.ctrl = None
            return False, True
        status = job.get("status")
        if status == "paused" and job.get("paused_from") == "queued":
            if run_ctx is not None and run_ctx.task_id == task_id:
                run_ctx.ctrl = None
            return False, True
        with _job_controls_lock:
            ctrl = _get_or_create_control_locked(task_id)
            if run_ctx is not None and run_ctx.task_id == task_id:
                run_ctx.ctrl = ctrl
            if status == "cancelling" or ctrl.cancel_event.is_set():
                raise JobCancelledError("Vom Benutzer abgebrochen")
            if not ctrl.resume_event.is_set() or status in ("pausing", "paused"):
                needs_pause_wait = True
            else:
                job["status"] = "running"
                job["paused_from"] = None
                job["message"] = "Verarbeitung gestartet..."
                should_save = True
    if should_save:
        save_jobs_to_disk()
    if needs_pause_wait:
        wait_if_paused_or_cancelled(task_id, _claim_if_queued=True)
    return True, False


def finalize_cancelled_job(task_id, message="Vom Benutzer abgebrochen", expected_ctrl=_UNSET):
    exp_ctrl = get_bound_job_control(task_id) if expected_ctrl is _UNSET else expected_ctrl
    changed = False
    with active_jobs_lock:
        job = active_jobs.get(task_id)
        with _job_controls_lock:
            cur_ctrl = _job_controls.get(task_id)
            if exp_ctrl is not None and cur_ctrl is not exp_ctrl:
                return
            if job is not None and job.get("status") not in ("done", "cancelled"):
                job["status"] = "cancelled"
                job["paused_from"] = None
                job["message"] = message
                _mark_open_pipeline_steps_cancelled_locked(job)
                if exp_ctrl is None or cur_ctrl is exp_ctrl:
                    _job_controls.pop(task_id, None)
                changed = True
    if changed:
        save_jobs_to_disk()


def finalize_cancelling_job_if_needed(task_id, expected_ctrl=_UNSET):
    """End-of-run safety net so no job can ever remain stuck in 'cancelling'."""
    exp_ctrl = get_bound_job_control(task_id) if expected_ctrl is _UNSET else expected_ctrl
    changed = False
    with active_jobs_lock:
        job = active_jobs.get(task_id)
        with _job_controls_lock:
            cur_ctrl = _job_controls.get(task_id)
            if exp_ctrl is not None and cur_ctrl is not exp_ctrl:
                return
            ctrl = exp_ctrl if exp_ctrl is not None else cur_ctrl
            cancel_flag = bool(ctrl and ctrl.cancel_event.is_set())
            if job is not None and (
                job.get("status") == "cancelling"
                or (cancel_flag and job.get("status") not in TERMINAL_JOB_STATUSES)
            ):
                job["status"] = "cancelled"
                job["paused_from"] = None
                job["message"] = "Vom Benutzer abgebrochen"
                _mark_open_pipeline_steps_cancelled_locked(job)
                if exp_ctrl is None or cur_ctrl is exp_ctrl:
                    _job_controls.pop(task_id, None)
                changed = True
    if changed:
        save_jobs_to_disk()


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
        with _job_controls_lock:
            if status in TERMINAL_JOB_STATUSES:
                _job_controls.pop(job_id, None)
            else:
                _job_controls[job_id] = _JobControl()

    # Persist immediately on creation
    save_jobs_to_disk()
    return job


def update_job(job_id, status=None, progress=None, message=None,
               pipeline_step=None, pipeline_status=None, pipeline_progress=None,
               pipeline_message=None, pipeline=None, manifest=None, params=None,
               paused_from=_UNSET, _allow_retry_reset=False, _allow_resume=False):
    """
    Updates a job's status, progress, or message.
    Updates the RAM state immediately. Throttles disk-writes for progress updates
    (maximum once per 1.5 seconds) to reduce disk I/O, but writes status changes immediately.
    """
    global active_jobs
    bound = get_bound_job_control(job_id)
    with active_jobs_lock:
        if job_id not in active_jobs:
            return False

        job = active_jobs[job_id]
        cur_status = job.get("status")

        with _job_controls_lock:
            cur_ctrl = _job_controls.get(job_id)
            if bound is not None and not _allow_retry_reset and cur_ctrl is not bound:
                return True
            if _allow_retry_reset and status not in TERMINAL_JOB_STATUSES:
                if cur_ctrl is None:
                    _job_controls[job_id] = _JobControl()
            ctrl_for_resume = bound if bound is not None else cur_ctrl
            allow_resume_now = bool(
                _allow_resume and (ctrl_for_resume is None or ctrl_for_resume.resume_event.is_set())
            )

        # Strict terminal-state guard: never reactivate without explicit _allow_retry_reset=True
        if cur_status in TERMINAL_JOB_STATUSES and not _allow_retry_reset:
            return True

        # While cancelling, ignore all lagging updates except final transition to cancelled
        if cur_status == "cancelling" and status != "cancelled":
            return True

        # Protect pausing/paused against ordinary worker status="running" updates
        if cur_status in ("pausing", "paused") and not allow_resume_now:
            if status in ("running", "queued"):
                status = None
            if status is None:
                if cur_status == "pausing":
                    if message is not None and not message.startswith("Pausiert nach aktuellem Schritt"):
                        message = f"{PAUSE_PENDING_MESSAGE} ({message})"
                elif cur_status == "paused":
                    message = None

        status_changed = False
        if status is not None and job.get("status") != status:
            job["status"] = status
            status_changed = True
            if status in TERMINAL_JOB_STATUSES:
                with _job_controls_lock:
                    if bound is None or _job_controls.get(job_id) is bound:
                        _job_controls.pop(job_id, None)

        if paused_from is not _UNSET and job.get("paused_from") != paused_from:
            job["paused_from"] = paused_from
            status_changed = True

        if progress is not None:
            job["progress"] = progress

        if message is not None:
            job["message"] = message

        if params is not None:
            job["params"] = copy.deepcopy(params)
            status_changed = True

        if manifest is not None:
            job["manifest"] = copy.deepcopy(manifest)
            status_changed = True

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
    """Removes only terminal jobs ('done', 'error', 'cancelled'); leaves active/queued jobs intact."""
    global active_jobs
    with active_jobs_lock:
        with _job_controls_lock:
            active_ids = list(active_jobs.keys())
            for j_id in active_ids:
                job = active_jobs[j_id]
                if job.get("status") in TERMINAL_JOB_STATUSES:
                    active_jobs.pop(j_id, None)
                    _last_saved_time.pop(j_id, None)
                    _last_saved_progress.pop(j_id, None)
                    _job_controls.pop(j_id, None)

    return save_jobs_to_disk()


def recover_interrupted_jobs():
    """
    Invoked during startup. Checks jobs_state.json on disk.
    Any jobs in ACTIVE_JOB_STATUSES ('running', 'queued', 'pausing', 'paused', 'cancelling')
    are set to 'error' while 'done' and 'cancelled' remain untouched.
    """
    file_path = get_jobs_state_file_path()

    def mutate(disk_jobs):
        recovered = False
        for job_id, job in disk_jobs.items():
            if job.get("status") in ACTIVE_JOB_STATUSES:
                job["status"] = "error"
                job["paused_from"] = None
                job["message"] = "Prozess durch unerwarteten App-Neustart abgebrochen."
                if isinstance(job.get("manifest"), dict):
                    job["manifest"] = _strip_provisional_manifest(job["manifest"])
                if "pipeline" in job and isinstance(job["pipeline"], dict):
                    for step in job["pipeline"].values():
                        if isinstance(step, dict) and step.get("status") in ("running", "pending"):
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
