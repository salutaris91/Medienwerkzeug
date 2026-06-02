import os
import sys
import json
import threading
import datetime
import urllib.request
import urllib.error
from gui.core.persistence import load_settings

TELEMETRY_ENDPOINT_DEFAULT = "https://telemetry.mediawerkzeug.xyz/log"
NEWSLETTER_ENDPOINT_DEFAULT = "https://newsletter.mediawerkzeug.xyz/register"

def _send_request_silent(url, data_dict):
    try:
        data = json.dumps(data_dict).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "Medienwerkzeug/1.0"},
            method="POST"
        )
        # Using a shorter timeout for silent logs
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status in (200, 201)
    except Exception as e:
        print(f"[Telemetry] Silently ignored error sending to {url}: {e}", file=sys.stderr)
        return False

def track_event_async(event_name, feature_usage=None, error_class=None):
    """Sends telemetry asynchronously in a separate thread. Never blocks application flow."""
    settings = load_settings()
    if not settings.get("telemetry_enabled", False):
        return

    def runner():
        try:
            endpoint = os.environ.get("MW_TELEMETRY_ENDPOINT", TELEMETRY_ENDPOINT_DEFAULT)
            payload = {
                "event": event_name,
                "app_version": settings.get("version", 1),
                "os": sys.platform,
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
            }
            if feature_usage is not None:
                payload["feature_usage"] = feature_usage
            if error_class is not None:
                payload["error_class"] = error_class

            _send_request_silent(endpoint, payload)
        except Exception as ex:
            print(f"[Telemetry] Error in background thread: {ex}", file=sys.stderr)

    threading.Thread(target=runner, daemon=True).start()

def send_newsletter_registration(email):
    """Sends newsletter registration synchronously (returns True/False) since this is a user action."""
    endpoint = os.environ.get("MW_NEWSLETTER_ENDPOINT", NEWSLETTER_ENDPOINT_DEFAULT)
    payload = {
        "email": email,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
    }
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "Medienwerkzeug/1.0"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status in (200, 201)
    except Exception as e:
        print(f"[Newsletter] Registration request failed: {e}", file=sys.stderr)
        return False
