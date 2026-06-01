import os
import sys
import threading
import socket
import webbrowser
from flask import Flask, send_from_directory
from gui.api.system_api import system_api
from gui.api.youtube_api import youtube_api
from gui.api.nas_api import nas_api
from gui.api.project_api import project_api
from gui.api.search_api import search_api
from gui.api.queue_api import queue_api
from gui.api.nas_renamer_api import nas_renamer_api
from gui.workers.processor import job_queue_worker, SYSTEM_STATUS
from gui.core.utils import load_settings

app = Flask(__name__, static_folder='static', static_url_path='')

# Register endpoints blueprint
app.register_blueprint(system_api, url_prefix='/api')
app.register_blueprint(youtube_api, url_prefix='/api')
app.register_blueprint(nas_api, url_prefix='/api')
app.register_blueprint(project_api, url_prefix='/api')
app.register_blueprint(search_api, url_prefix='/api')
app.register_blueprint(queue_api, url_prefix='/api')
app.register_blueprint(nas_renamer_api, url_prefix='/api')

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def main():
    import time
    port = int(os.environ.get("MW_PORT", 5001))
    print(f"Starting Medienwerkzeug Flask Server on port {port}...")
    
    # Wait up to 5 times (total 7.5 seconds) if port is in use (e.g. from quick restart)
    for i in range(5):
        if is_port_in_use(port):
            print(f"Port {port} belegt, warte auf Freigabe (Versuch {i+1}/5)...")
            time.sleep(1.5)
        else:
            break
            
    if is_port_in_use(port):
        print(f"Server is already running on port {port}! Just opening the browser...")
        webbrowser.open(f"http://127.0.0.1:{port}")
        sys.exit(0)
        
    # Init settings
    settings = load_settings()
    
    # Ensure standard directories exist
    inbox = settings.get("inbox_dir", os.path.expanduser("~/Downloads/Medien Input"))
    outbox = settings.get("outbox_dir", os.path.expanduser("~/Downloads/Medien Output"))
    os.makedirs(inbox, exist_ok=True)
    os.makedirs(outbox, exist_ok=True)
    
    # Start background worker
    worker_thread = threading.Thread(target=job_queue_worker, daemon=True)
    worker_thread.start()
    print("Background worker thread started.")
    
    # Start folder monitor thread
    from gui.core.helpers import folder_size_monitor
    monitor_thread = threading.Thread(target=folder_size_monitor, daemon=True)
    monitor_thread.start()
    print("Folder size monitor thread started.")
    
    # Fetch jokes from online repository asynchronously on startup
    try:
        from gui.workers.youtube_worker import fetch_online_jokes_async
        fetch_online_jokes_async()
        print("Async jokes update started.")
    except Exception as e:
        print(f"Failed to start async joke fetch: {e}")
        
    try:
        def open_browser():
            webbrowser.open(f"http://127.0.0.1:{port}")
        threading.Timer(1.0, open_browser).start()
        
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    except OSError as e:
        if e.errno == 48 or "Address already in use" in str(e):
            print(f"Server is already running on port {port}! Just opening the browser...")
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
