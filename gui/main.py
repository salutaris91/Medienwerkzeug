import os
import sys
import threading
import socket
import webbrowser
import signal
import subprocess
import urllib.request
from flask import Flask, send_from_directory
from gui.api.system_api import system_api
from gui.api.youtube_api import youtube_api
from gui.api.nas_api import nas_api
from gui.api.project_api import project_api
from gui.api.search_api import search_api
from gui.api.queue_api import queue_api
from gui.api.nas_renamer_api import nas_renamer_api
from gui.api.onboarding_api import onboarding_api
from gui.workers.processor import job_queue_worker, SYSTEM_STATUS
from gui.core.utils import load_settings

app = Flask(__name__, static_folder='static', static_url_path='')

# Configure Flask sessions and secure cookies
from gui.core.persistence import load_env_keys, save_env_keys
env_keys = load_env_keys()
secret_key = os.environ.get("FLASK_SECRET_KEY") or env_keys.get("FLASK_SECRET_KEY")
if not secret_key:
    import secrets
    secret_key = secrets.token_hex(32)
    save_env_keys({"FLASK_SECRET_KEY": secret_key})

app.config.update(
    SECRET_KEY=secret_key,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
)

# Register central auth and CSRF middleware hook
from gui.core.auth_middleware import auth_before_request
app.before_request(auth_before_request)


# Register endpoints blueprint
app.register_blueprint(system_api, url_prefix='/api')
app.register_blueprint(youtube_api, url_prefix='/api')
app.register_blueprint(nas_api, url_prefix='/api')
app.register_blueprint(project_api, url_prefix='/api')
app.register_blueprint(search_api, url_prefix='/api')
app.register_blueprint(queue_api, url_prefix='/api')
app.register_blueprint(nas_renamer_api, url_prefix='/api')
app.register_blueprint(onboarding_api, url_prefix='/api')

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def is_server_healthy(port, timeout=1.5):
    url = f"http://127.0.0.1:{port}/api/healthz"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.status == 200
    except Exception as e:
        print(f"Healthcheck failed for existing server on port {port}: {e}", flush=True)
        return False

def get_listener_pids(port):
    try:
        output = subprocess.check_output(
            ["lsof", "-ti", f"tcp:{port}", "-sTCP:LISTEN"],
            text=True,
            timeout=2,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"Could not detect listener process on port {port}: {e}", flush=True)
        return []

    current_pid = os.getpid()
    pids = []
    for line in output.splitlines():
        try:
            pid = int(line.strip())
        except ValueError:
            continue
        if pid != current_pid:
            pids.append(pid)
    return pids

def stop_unhealthy_server(port):
    pids = get_listener_pids(port)
    if not pids:
        return False

    print(f"Stopping unhealthy server process(es) on port {port}: {pids}", flush=True)
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        except Exception as e:
            print(f"Could not terminate process {pid}: {e}", flush=True)

    import time
    for _ in range(10):
        if not is_port_in_use(port):
            return True
        time.sleep(0.3)

    print(f"Port {port} still occupied after SIGTERM; forcing shutdown.", flush=True)
    for pid in pids:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except Exception as e:
            print(f"Could not force-kill process {pid}: {e}", flush=True)

    for _ in range(10):
        if not is_port_in_use(port):
            return True
        time.sleep(0.3)

    return not is_port_in_use(port)

def main():
    import time
    port = int(os.environ.get("MW_PORT", 5001))
    print(f"Starting Medienwerkzeug Flask Server on port {port}...")

    if is_port_in_use(port):
        if is_server_healthy(port):
            print(f"Healthy server is already running on port {port}. Opening browser.", flush=True)
            if os.environ.get("MW_RUNTIME") != "docker":
                webbrowser.open(f"http://127.0.0.1:{port}")
            sys.exit(0)

        print(f"Port {port} is occupied by an unhealthy server. Attempting self-healing restart.", flush=True)
        if not stop_unhealthy_server(port):
            print(f"Could not free port {port}; opening browser for the existing process.", flush=True)
            if os.environ.get("MW_RUNTIME") != "docker":
                webbrowser.open(f"http://127.0.0.1:{port}")
            sys.exit(1)
    
    # Wait up to 5 times (total 7.5 seconds) if port is in use (e.g. from quick restart)
    for i in range(5):
        if is_port_in_use(port):
            print(f"Port {port} belegt, warte auf Freigabe (Versuch {i+1}/5)...", flush=True)
            time.sleep(1.5)
        else:
            break
            
    if is_port_in_use(port):
        print(f"Server is already running on port {port}! Just opening the browser...")
        if os.environ.get("MW_RUNTIME") != "docker":
            webbrowser.open(f"http://127.0.0.1:{port}")
        sys.exit(0)
        
    # Init settings
    settings = load_settings()
    
    # Crash recovery & Temp cleaning
    try:
        from gui.core.jobs import recover_interrupted_jobs, clean_orphaned_temp_files
        print("Running crash recovery for jobs...")
        recover_interrupted_jobs()
        print("Cleaning orphaned temp files (>12h) to quarantine...")
        clean_orphaned_temp_files()
    except Exception as e:
        print(f"Error running startup jobs tasks: {e}", file=sys.stderr)
    
    # Ensure standard directories exist if configured
    inbox = settings.get("inbox_dir")
    outbox = settings.get("outbox_dir")
    if inbox and inbox.strip():
        os.makedirs(inbox, exist_ok=True)
    if outbox and outbox.strip():
        os.makedirs(outbox, exist_ok=True)
    
    # Start background worker
    worker_thread = threading.Thread(target=job_queue_worker, daemon=True)
    worker_thread.start()
    print("Background worker thread started.")
    
    # Start metrics worker
    from gui.workers.processor import system_metrics_worker
    metrics_thread = threading.Thread(target=system_metrics_worker, daemon=True)
    metrics_thread.start()
    print("System metrics worker thread started.")
    
    # Start folder monitor thread
    from gui.core.helpers import folder_size_monitor
    monitor_thread = threading.Thread(target=folder_size_monitor, daemon=True)
    monitor_thread.start()
    print("Folder size monitor thread started.")

    # Trigger app_start telemetry if enabled
    try:
        from gui.core.telemetry import track_event_async
        track_event_async("app_start")
    except Exception:
        pass
    
    # Fetch jokes from online repository asynchronously on startup
    try:
        from gui.workers.youtube_worker import fetch_online_jokes_async
        fetch_online_jokes_async()
        print("Async jokes update started.")
    except Exception as e:
        print(f"Failed to start async joke fetch: {e}")
        
    try:
        if os.environ.get("MW_RUNTIME") != "docker":
            def open_browser():
                webbrowser.open(f"http://127.0.0.1:{port}")
            threading.Timer(1.0, open_browser).start()
        
        try:
            from waitress import serve
        except ImportError:
            print("⚠️ waitress not installed, falling back to Flask dev server (run 'pip install -r requirements.txt').")
            app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
        else:
            # threads=16: SSE log streams hold one worker thread per open
            # connection, so the default pool of 4 would starve quickly.
            print(f"Serving via waitress on port {port}.")
            serve(app, host='0.0.0.0', port=port, threads=16)
    except OSError as e:
        if e.errno == 48 or "Address already in use" in str(e):
            print(f"Server is already running on port {port}! Just opening the browser...")
            if os.environ.get("MW_RUNTIME") != "docker":
                webbrowser.open(f"http://127.0.0.1:{port}")
        else:
            raise e
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        SYSTEM_STATUS["running"] = False
        print("Goodbye.")

if __name__ == '__main__':
    main()
