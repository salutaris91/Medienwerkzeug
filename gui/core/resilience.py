import subprocess
import time
import os
import signal
import threading
from gui.core.helpers import log_message
from gui.core.jobs import (
    JobCancelledError,
    check_cancelled,
    get_job_control,
    is_job_cancelled,
    register_job_process,
    resolve_job_id,
    unregister_job_process,
)


def run_with_retries_and_timeout(cmd, max_attempts=3, timeout_sec=300, line_callback=None, task_id=None):
    """
    Führt cmd aus, fängt Timeouts ab, terminiert Prozesse sauber und macht Retries mit Backoff.
    line_callback(str) -> wird pro stdout-Zeile aufgerufen.
    """
    job_id = resolve_job_id(task_id)

    for attempt in range(1, max_attempts + 1):
        check_cancelled(job_id)

        if attempt > 1:
            wait_sec = 2 ** attempt
            log_message(f"🔄 Retry {attempt}/{max_attempts} in {wait_sec}s...")
            if job_id is not None:
                ctrl = get_job_control(job_id)
                if ctrl.cancel_event.wait(wait_sec):
                    raise JobCancelledError("Vom Benutzer abgebrochen")
                check_cancelled(job_id)
            else:
                time.sleep(wait_sec)

        process = None
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                start_new_session=(os.name != 'nt'),
            )
            register_job_process(job_id, process)

            def read_output(proc, cb):
                callback_error_logged = False
                try:
                    for line in iter(proc.stdout.readline, ''):
                        if not line:
                            break
                        if cb:
                            try:
                                cb(line)
                            except Exception as cb_err:
                                if not callback_error_logged:
                                    log_message(f"❌ Fehler im Callback des Output-Readers: {cb_err}")
                                    callback_error_logged = True
                except (ValueError, OSError):
                    # Normaler Abbruch beim Schließen des Streams durch Prozess-Beendigung
                    pass
                except Exception as e:
                    log_message(f"⚠️ Unerwarteter Fehler im Output-Reader-Thread: {e}")

            parent_name = threading.current_thread().name
            reader_thread = threading.Thread(
                target=read_output,
                args=(process, line_callback),
                name=f"{parent_name}-reader"
            )
            reader_thread.daemon = True
            reader_thread.start()

            process.wait(timeout=timeout_sec)
            if process.stdout:
                try:
                    process.stdout.close()
                except Exception:
                    pass
            reader_thread.join(timeout=2.0)

            if is_job_cancelled(job_id):
                raise JobCancelledError("Vom Benutzer abgebrochen")

            if process.returncode == 0:
                return True
            else:
                log_message(f"❌ Befehl fehlgeschlagen mit Returncode {process.returncode} in Versuch {attempt}.")

        except JobCancelledError:
            raise
        except subprocess.TimeoutExpired:
            log_message(f"⚠️ Timeout ({timeout_sec}s) in Versuch {attempt}. Breche Prozess ab.")
            if process:
                try:
                    if os.name != 'nt':
                        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    else:
                        process.terminate()
                    process.wait(timeout=5)
                except Exception as e:
                    log_message(f"Fehler beim Beenden des Prozesses: {e}")
                    if os.name != 'nt':
                        try:
                            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                        except Exception:
                            pass
                    else:
                        try:
                            process.kill()
                        except Exception:
                            pass
            if is_job_cancelled(job_id):
                raise JobCancelledError("Vom Benutzer abgebrochen")
        except Exception as e:
            log_message(f"❌ Unerwarteter Fehler in Versuch {attempt}: {e}")
            if process:
                try:
                    if os.name != 'nt':
                        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    else:
                        process.terminate()
                except Exception:
                    pass
            if is_job_cancelled(job_id):
                raise JobCancelledError("Vom Benutzer abgebrochen")
        finally:
            if process is not None:
                unregister_job_process(job_id, process)

    return False
