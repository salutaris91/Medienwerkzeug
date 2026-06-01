import os
from flask import Blueprint, request, jsonify
import gui.core.nas_renamer as nas_renamer
from gui.core.utils import load_settings

nas_renamer_api = Blueprint('nas_renamer_api', __name__)

def _get_nas_destination(destination_id, folder_name):
    settings = load_settings()
    nas_root = settings.get("nas_root", "")
    if not nas_root:
        return None
    
    destination = None
    if destination_id:
        sync_cats = settings.get("sync_categories", [])
        for cat in sync_cats:
            if cat.get("id") == str(destination_id):
                destination = os.path.join(nas_root, cat.get("nas_sub", "").lstrip("/"))
                break
                
    if not destination:
        destination = os.path.join(nas_root, "Serien")
        
    if folder_name:
        return os.path.join(destination, folder_name)
    return destination


@nas_renamer_api.route('/nas-renamer/preview', methods=['POST'])
def handle_api_nas_renamer_preview():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
        
    destination_id = params.get("destination_id")
    folder_name = params.get("folder_name")
    
    target_folder = _get_nas_destination(destination_id, folder_name)
    if not target_folder:
        return jsonify({"status": "error", "message": "NAS-Root ist nicht konfiguriert."}), 400
    
    try:
        result = nas_renamer.preview_renames(target_folder)
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@nas_renamer_api.route('/nas-renamer/apply', methods=['POST'])
def handle_api_nas_renamer_apply():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
        
    destination_id = params.get("destination_id")
    folder_name = params.get("folder_name")
    rename_plan = params.get("rename_plan", [])
    
    if not rename_plan:
        return jsonify({"status": "error", "message": "Keine Dateien zum Umbenennen ausgewählt."}), 400
        
    target_folder = _get_nas_destination(destination_id, folder_name)
    if not target_folder:
        return jsonify({"status": "error", "message": "NAS-Root ist nicht konfiguriert."}), 400
    
    try:
        result = nas_renamer.apply_renames(target_folder, rename_plan)
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@nas_renamer_api.route('/nas-renamer/rollback', methods=['POST'])
def handle_api_nas_renamer_rollback():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
        
    transaction_id = params.get("transaction_id")
    if not transaction_id:
        return jsonify({"status": "error", "message": "Keine Transaktions-ID angegeben."}), 400
        
    try:
        result = nas_renamer.rollback_renames(transaction_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
