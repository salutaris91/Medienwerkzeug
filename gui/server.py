# Backward compatibility facade for unit tests
import json
from gui.core.helpers import *
from gui.core.transfers import *
from gui.workers.processor import *
from gui.workers.youtube_worker import *
from gui.api.endpoints import *
from gui.core.utils import *
import gui.core.media as media
from gui.main import app

test_client = app.test_client()

class GUIRequestHandler:
    @staticmethod
    def _proxy(endpoint, method, dummy, params=None):
        if method == 'GET':
            resp = test_client.get(endpoint, query_string=params)
        else:
            resp = test_client.post(endpoint, json=params)
        
        if hasattr(dummy, 'send_json'):
            if resp.is_json:
                dummy.send_json(resp.get_json())
            else:
                print(f"Response {resp.status_code}: {resp.data}")
                dummy.send_json({"error": str(resp.data)})
        elif hasattr(dummy, 'send_response') and hasattr(dummy, 'send_error'):
            if resp.status_code >= 400:
                dummy.send_error(resp.status_code, (resp.get_json() or {}).get("error", "Error"))
            else:
                dummy.send_response(resp.status_code)

    @staticmethod
    def handle_api_delete_project(dummy, params):
        GUIRequestHandler._proxy('/api/delete-project', 'POST', dummy, params)

    @staticmethod
    def handle_api_paths_preview_clean(dummy, params):
        GUIRequestHandler._proxy('/api/paths-preview-clean', 'POST', dummy, params)

    @staticmethod
    def handle_api_preview_process(dummy, params):
        GUIRequestHandler._proxy('/api/preview-process', 'POST', dummy, params)

    @staticmethod
    def handle_api_queue_clear(dummy, params=None):
        GUIRequestHandler._proxy('/api/queue-clear', 'POST', dummy, params)

    @staticmethod
    def handle_api_search(dummy, params):
        GUIRequestHandler._proxy('/api/search', 'GET', dummy, params)

    @staticmethod
    def handle_api_nas_series_get(dummy, params):
        GUIRequestHandler._proxy('/api/nas-series', 'GET', dummy, params)
        
    @staticmethod
    def handle_api_nas_series_get_all(dummy, params=None):
        GUIRequestHandler._proxy('/api/nas-series', 'GET', dummy, params)
        
    @staticmethod
    def handle_api_match_episodes(dummy, params):
        GUIRequestHandler._proxy('/api/match-episodes', 'POST', dummy, params)

    @staticmethod
    def handle_api_series_detect(dummy, params):
        GUIRequestHandler._proxy('/api/series-detect', 'GET', dummy, params)

    @staticmethod
    def handle_api_scan_project_detect_doku(dummy, params):
        GUIRequestHandler._proxy('/api/scan-project', 'POST', dummy, params)

    @staticmethod
    def handle_api_split_project_file(dummy, params):
        GUIRequestHandler._proxy('/api/split-project-file', 'POST', dummy, params)

    @staticmethod
    def handle_api_estimate_conversion_optimization(dummy, params):
        GUIRequestHandler._proxy('/api/estimate-conversion', 'POST', dummy, params)

    @staticmethod
    def handle_api_subscriptions_approve(dummy, params):
        GUIRequestHandler._proxy('/api/youtube/subscriptions/approve', 'POST', dummy, params)

    @staticmethod
    def handle_api_subscriptions_ignore(dummy, params):
        GUIRequestHandler._proxy('/api/youtube/subscriptions/ignore', 'POST', dummy, params)

    @staticmethod
    def handle_api_check_subscriptions(dummy, params=None):
        GUIRequestHandler._proxy('/api/check-subscriptions', 'GET', dummy, params)


    @staticmethod
    def handle_api_nas_series(dummy, params):
        GUIRequestHandler._proxy('/api/nas-series', 'GET', dummy, params)

    @staticmethod
    def handle_api_scan_project(dummy, params):
        GUIRequestHandler._proxy('/api/scan-project', 'GET', dummy, params)

    @staticmethod
    def handle_api_paths_clean(dummy, params):
        GUIRequestHandler._proxy('/api/paths-clean', 'POST', dummy, params)

    @staticmethod
    def handle_api_estimate_conversion(dummy, params):
        GUIRequestHandler._proxy('/api/estimate-conversion', 'POST', dummy, params)
