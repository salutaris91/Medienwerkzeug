import os, sys, json, time, shutil, subprocess, urllib, threading, math
from flask import Blueprint, request, jsonify, Response, send_file, send_from_directory
from gui.core.utils import load_settings, save_settings, clean_show_name, load_show_profile, save_show_profile, load_konv_history
from gui.core.helpers import *
from gui.core.helpers import log_queue
from gui.core.transfers import *
from gui.workers.processor import *
from gui.workers.youtube_worker import *
import gui.core.media as media
import gui.mw_metadata as mw_metadata

youtube_api = Blueprint('youtube_api', __name__)

# Global variables imported from processor
from gui.workers.processor import JOB_QUEUE, SYSTEM_STATUS, STATUS_LOCK



@youtube_api.route('/youtube/subscriptions', methods=['GET', 'POST'])
def handle_api_youtube_subscriptions():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    query = request.args
    settings = load_settings()

    if request.method == 'GET':
        return jsonify({"subscriptions": settings.get("youtube_subscriptions", [])})
    elif request.method == 'POST':
        subs = params.get("subscriptions", [])
        settings["youtube_subscriptions"] = subs
        save_settings(settings)
        return jsonify({"status": "success"})



@youtube_api.route('/youtube/subscriptions/check', methods=['POST'])
def handle_api_check_subscriptions():
    import uuid
    task_id = str(uuid.uuid4())
    job_params = {
        "media_type": "youtube_subscription_check",
        "task_id": task_id
    }
    job_info = {
        "id": task_id,
        "type": "youtube_subscription_check",
        "name": "YouTube-Abos überprüfen",
        "status": "queued",
        "progress": 0,
        "message": "In der Warteschlange...",
        "timestamp": time.time(),
        "params": job_params
    }
    from gui.core.jobs import create_job
    create_job(
        job_id=task_id,
        name=job_info["name"],
        job_type=job_info["type"],
        params=job_params,
        pipeline=job_info.get("pipeline")
    )
    job_queue.put(job_info)
    return jsonify({"status": "success", "message": "Überprüfung in Warteschlange eingereiht", "task_id": task_id})



@youtube_api.route('/youtube/subscriptions/approve', methods=['POST'])
def handle_api_subscriptions_approve():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    subscription_id = params.get("subscription_id")
    video_id = params.get("video_id")
    if not subscription_id or not video_id:
        return jsonify({"error": "Missing subscription_id or video_id"}), 400
        return
        
    settings = load_settings()
    subs = settings.get("youtube_subscriptions", [])
    target_sub = None
    for s in subs:
        if s.get("id") == subscription_id:
            target_sub = s
            break
            
    if not target_sub:
        return jsonify({"error": "Subscription not found"}), 404
        return
        
    pending = target_sub.get("pending_videos", [])
    video = None
    for v in pending:
        if v.get("id") == video_id:
            video = v
            break
            
    if video:
        pending.remove(video)
        downloaded_ids = target_sub.get("downloaded_ids", [])
        if video_id not in downloaded_ids:
            downloaded_ids.append(video_id)
        target_sub["pending_videos"] = pending
        target_sub["downloaded_ids"] = downloaded_ids
        save_settings(settings)
        
        # Queue download job
        import uuid
        import time
        task_id = str(uuid.uuid4())
        sub_copy_to_nas = target_sub.get("copy_to_nas", True)
        sub_copy_to_pcloud = target_sub.get("copy_to_pcloud", False)
        sub_copy_to_local = target_sub.get("copy_to_local", False)
        sub_nas_dest = target_sub.get("nas_destination_id", target_sub.get("destination_id"))
        sub_pcloud_dest = target_sub.get("pcloud_destination_id")
        sub_local_dest = target_sub.get("local_destination_id")
        
        job_params = {
            "media_type": "youtube",
            "yt_url": video.get("url"),
            "yt_format": "best",
            "yt_embed_thumbnail": True,
            "copy_to_nas": sub_copy_to_nas,
            "copy_to_pcloud": sub_copy_to_pcloud,
            "copy_to_local": sub_copy_to_local,
            "destination_id": sub_nas_dest,
            "nas_destination_id": sub_nas_dest,
            "pcloud_destination_id": sub_pcloud_dest,
            "local_destination_id": sub_local_dest,
            "project_name": "",
            "task_id": task_id
        }
        
        job_info = {
            "id": task_id,
            "type": "youtube",
            "name": f"Abo: {video.get('title', '')[:40]}",
            "status": "queued",
            "progress": 0,
            "message": "Manuell freigegeben...",
            "timestamp": time.time(),
            "params": job_params,
            "pipeline": build_job_pipeline(job_params, True, True)
        }
        
        from gui.core.jobs import create_job
        create_job(
            job_id=task_id,
            name=job_info["name"],
            job_type=job_info["type"],
            params=job_params,
            pipeline=job_info.get("pipeline")
        )
            
        job_queue.put(job_info)
        
        return jsonify({"status": "success", "message": "Video freigegeben und Download gestartet"})
    else:
        return jsonify({"status": "success", "message": "Video war nicht in Freigabeliste oder wurde bereits verarbeitet"})



@youtube_api.route('/youtube/subscriptions/ignore', methods=['POST'])
def handle_api_subscriptions_ignore():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    query = request.args
    subscription_id = params.get("subscription_id")
    video_id = params.get("video_id")
    if not subscription_id or not video_id:
        return jsonify({"error": "Missing subscription_id or video_id"}), 400
        return
        
    settings = load_settings()
    subs = settings.get("youtube_subscriptions", [])
    target_sub = None
    for s in subs:
        if s.get("id") == subscription_id:
            target_sub = s
            break
            
    if not target_sub:
        return jsonify({"error": "Subscription not found"}), 404
        return
        
    pending = target_sub.get("pending_videos", [])
    video = None
    for v in pending:
        if v.get("id") == video_id:
            video = v
            break
            
    if video:
        pending.remove(video)
        downloaded_ids = target_sub.get("downloaded_ids", [])
        if video_id not in downloaded_ids:
            downloaded_ids.append(video_id)
        target_sub["pending_videos"] = pending
        target_sub["downloaded_ids"] = downloaded_ids
        save_settings(settings)
        
        return jsonify({"status": "success", "message": "Video ignoriert"})
    else:
        return jsonify({"status": "success", "message": "Video war nicht in Freigabeliste oder wurde bereits verarbeitet"})



@youtube_api.route('/youtube/search-parts', methods=['GET', 'POST'])
def handle_api_youtube_search_parts():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    query = request.args
    titles = query.get("title", [])
    title = titles[0] if titles else ""
    if not title:
        return jsonify({"error": "Missing title"}), 400
        return
        
    import re
    patterns = [
        r"\bteil\s*\d+\b",
        r"\bpart\s*\d+\b",
        r"\bepisode\s*\d+\b",
        r"#\s*\d+\b",
        r"\b\d+\s*/\s*\d+\b",
        r"\b\d+\s*von\s*\d+\b",
        r"\b\d+\.\s*teil\b",
        r"\b\d+\.\s*part\b"
    ]
    
    search_query = title
    for pattern in patterns:
        clean_title = re.sub(pattern, "", search_query, flags=re.IGNORECASE).strip()
        if clean_title:
            search_query = clean_title
    
    search_query = re.sub(r"\s*-\s*$", "", search_query).strip()
    search_query = re.sub(r"\s+", " ", search_query)
    
    cmd = ["yt-dlp", "--playlist-end", "50", "--dump-json", "--flat-playlist", f"ytsearch50:{search_query}"]
    
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        results = []
        if res.returncode == 0:
            lines = res.stdout.strip().split('\n')
            for line in lines:
                if not line.strip():
                    continue
                try:
                    video_data = json.loads(line)
                    v_id = video_data.get("id")
                    v_title = video_data.get("title", "")
                    v_url = video_data.get("url") or f"https://www.youtube.com/watch?v={v_id}"
                    v_thumb = video_data.get("thumbnail") or ""
                    if not v_thumb and video_data.get("thumbnails"):
                        v_thumb = video_data.get("thumbnails")[0].get("url") or ""
                    v_channel = video_data.get("uploader") or video_data.get("channel") or ""
                    
                    results.append({
                        "id": v_id,
                        "title": v_title,
                        "url": v_url,
                        "thumbnail": v_thumb,
                        "channel": v_channel
                    })
                except Exception:
                    pass
        
        return jsonify({"query": search_query, "results": results})
    except Exception as e:
        return jsonify({"error": f"Error searching YouTube: {e}"}), 500



@youtube_api.route('/youtube/merge', methods=['POST'])
def handle_api_youtube_merge():
    urls = params.get("urls", [])
    title = params.get("title", "Merged Video")
    subscription_id = params.get("subscription_id")
    video_ids_to_remove = params.get("video_ids_to_remove", [])
    
    if not urls:
        return jsonify({"error": "Missing urls"}), 400
        return
        
    settings = load_settings()
    
    if "copy_to_nas" in params:
        sub_copy_to_nas = params.get("copy_to_nas", False)
        sub_copy_to_pcloud = params.get("copy_to_pcloud", False)
        sub_copy_to_local = params.get("copy_to_local", False)
        sub_nas_dest = params.get("nas_destination_id", "")
        sub_pcloud_dest = params.get("pcloud_destination_id", "")
        sub_local_dest = params.get("local_destination_id", "")
    elif subscription_id:
        sub_copy_to_nas = True
        sub_copy_to_pcloud = False
        sub_copy_to_local = False
        sub_nas_dest = ""
        sub_pcloud_dest = ""
        sub_local_dest = ""
        
        subs = settings.get("youtube_subscriptions", [])
        for s in subs:
            if s.get("id") == subscription_id:
                sub_copy_to_nas = s.get("copy_to_nas", True)
                sub_copy_to_pcloud = s.get("copy_to_pcloud", False)
                sub_copy_to_local = s.get("copy_to_local", False)
                sub_nas_dest = s.get("nas_destination_id", s.get("destination_id", ""))
                sub_pcloud_dest = s.get("pcloud_destination_id", "")
                sub_local_dest = s.get("local_destination_id", "")
                break
    else:
        sub_copy_to_nas = True
        sub_copy_to_pcloud = False
        sub_copy_to_local = False
        sub_nas_dest = ""
        sub_pcloud_dest = ""
        sub_local_dest = ""
                
    import uuid
    import time
    task_id = str(uuid.uuid4())
    
    first_thumb = params.get("thumbnail", "")
    
    job_params = {
        "media_type": "youtube_merge",
        "yt_urls": urls,
        "title": title,
        "subscription_id": subscription_id,
        "video_ids_to_remove": video_ids_to_remove,
        "copy_to_nas": sub_copy_to_nas,
        "copy_to_pcloud": sub_copy_to_pcloud,
        "copy_to_local": sub_copy_to_local,
        "destination_id": sub_nas_dest,
        "nas_destination_id": sub_nas_dest,
        "pcloud_destination_id": sub_pcloud_dest,
        "local_destination_id": sub_local_dest,
        "yt_thumbnail": first_thumb,
        "yt_title": title,
        "yt_format": params.get("yt_format", "best"),
        "task_id": task_id
    }
    
    job_info = {
        "id": task_id,
        "type": "youtube_merge",
        "name": f"Merge: {title[:40]}",
        "status": "queued",
        "progress": 0,
        "message": "In der Warteschlange...",
        "timestamp": time.time(),
        "params": job_params,
        "pipeline": build_job_pipeline(job_params, True, True)
    }
    
    from gui.core.jobs import create_job
    create_job(
        job_id=task_id,
        name=job_info["name"],
        job_type=job_info["type"],
        params=job_params,
        pipeline=job_info.get("pipeline")
    )
        
    job_queue.put(job_info)
    return jsonify({"status": "success", "task_id": task_id, "message": "Zusammenfügen gestartet"})



@youtube_api.route('/yt/fetch', methods=['POST'])
def handle_api_yt_fetch():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    url = params.get("url", "")
    if not url:
        return jsonify({"error": "Keine URL angegeben."})
        return
        
    cmd = ["yt-dlp", "--dump-json", "--skip-download", "--cookies-from-browser", "chrome", url]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if proc.returncode != 0:
            cmd_fallback = ["yt-dlp", "--dump-json", "--skip-download", url]
            proc = subprocess.run(cmd_fallback, capture_output=True, text=True, timeout=15)
            
        if proc.returncode != 0:
            return jsonify({"error": f"yt-dlp Fehler: {proc.stderr}"})
            return
            
        stdout_lines = proc.stdout.strip().split("\n")
        if not stdout_lines or not stdout_lines[0]:
            return jsonify({"error": "Keine Daten von yt-dlp erhalten."})
            return
            
        data = json.loads(stdout_lines[0])
        
        title = data.get("title") or "Unbekannter Titel"
        uploader = data.get("uploader") or "Unbekannter Uploader"
        thumbnail = data.get("thumbnail") or ""
        duration = data.get("duration") or 0
        
        chapters = []
        for ch in (data.get("chapters") or []):
            if ch:
                chapters.append({
                    "title": ch.get("title", ""),
                    "start_time": ch.get("start_time", 0),
                    "end_time": ch.get("end_time", 0)
                })
            
        # Helper to map exact format heights to standard resolutions (e.g. 808p -> 1080p)
        def get_standard_resolution(fmt):
            note = fmt.get("format_note") or ""
            if note.endswith("p") and note[:-1].isdigit():
                return int(note[:-1])
            h = fmt.get("height")
            if h and isinstance(h, int):
                if h > 1440:
                    return 2160
                elif h > 720:
                    return 1080
                elif h > 480:
                    return 720
                elif h > 360:
                    return 480
                else:
                    return 360
            return None

        # Analyze formats to detect codecs and standard heights
        formats_list = data.get("formats") or []
        std_heights = set()
        for fmt in formats_list:
            if fmt:
                std_h = get_standard_resolution(fmt)
                if std_h:
                    std_heights.add(std_h)
        
        sorted_std_heights = sorted(list(std_heights), reverse=True)
        resolutions = []
        
        # 1. Best quality option
        resolutions.append({
            "id": "best",
            "label": "Beste Qualität (Video + Audio)"
        })
        
        # 2. Add height-specific options with codec information
        for std_h in sorted_std_heights:
            if std_h < 360:
                continue
                
            has_av1 = False
            has_vp9 = False
            has_h264 = False
            
            # Check what codecs are available for this standard height
            for fmt in formats_list:
                if fmt and get_standard_resolution(fmt) == std_h:
                    vcodec = (fmt.get("vcodec") or "").lower()
                    if vcodec.startswith("av01") or "av1" in vcodec:
                        has_av1 = True
                    elif vcodec.startswith("vp9") or vcodec.startswith("vp09"):
                        has_vp9 = True
                    elif vcodec.startswith("avc1") or "h264" in vcodec or "avc" in vcodec:
                        has_h264 = True
            
            added_any = False
            # H.264 (AVC)
            if has_h264:
                resolutions.append({
                    "id": f"{std_h}p_h264",
                    "label": f"Maximal {std_h}p (H.264 – beste Kompatibilität)"
                })
                added_any = True
            # VP9
            if has_vp9:
                resolutions.append({
                    "id": f"{std_h}p_vp9",
                    "label": f"Maximal {std_h}p (VP9 – höchste Bildqualität)"
                })
                added_any = True
            # AV1
            if has_av1:
                resolutions.append({
                    "id": f"{std_h}p_av1",
                    "label": f"Maximal {std_h}p (AV1 – kleinere Datei)"
                })
                added_any = True
            
            # Fallback if no specific codec detected or none were added
            if not added_any:
                resolutions.append({
                    "id": f"{std_h}p",
                    "label": f"Maximal {std_h}p"
                })
        
        # 3. Audio-only option
        resolutions.append({
            "id": "audio",
            "label": "Nur Audio extrahieren (MP3)"
        })
        
        subs_dict = data.get("subtitles") or {}
        auto_subs_dict = data.get("automatic_captions") or {}
        subs = list(subs_dict.keys())
        
        # Filter auto-captions to common languages only (de, en)
        common_langs = {'de', 'en'}
        auto_subs = []
        for lang in auto_subs_dict.keys():
            lang_lower = lang.lower()
            base_lang = lang_lower.split('-')[0]
            if base_lang in common_langs:
                auto_subs.append(lang)
                
        all_subs = sorted(list(set(subs + auto_subs)))
        
        description = data.get("description", "")
        
        return jsonify({
            "title": title,
            "uploader": uploader,
            "thumbnail": thumbnail,
            "duration": duration,
            "chapters": chapters,
            "resolutions": resolutions,
            "subtitles": all_subs,
            "description": description
        })
    except Exception as e:
        return jsonify({"error": f"Fehler bei Link-Analyse: {str(e)}"})



@youtube_api.route('/yt/segments', methods=['GET', 'POST'])
def handle_api_yt_segments():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    query = request.args
    task_id = query.get("taskId", "")
    if not task_id:
        return jsonify({"error": "Keine taskId angegeben."})
        return
        
    with active_yt_tasks_lock:
        task = active_yt_tasks.get(task_id)
        
    if not task:
        return jsonify({"error": "Task nicht gefunden."})
        return
        
    temp_dir = task.get("temp_dir")
    segments = []
    if temp_dir and os.path.exists(temp_dir):
        for f in sorted(os.listdir(temp_dir)):
            if f.lower().endswith(('.mp4', '.mkv', '.avi', '.webm', '.mov')) and not f.startswith("."):
                segments.append(f)
                
    return jsonify({
        "state": task.get("state"),
        "segments": segments,
        "title": task.get("params", {}).get("yt_title", "")
    })



@youtube_api.route('/yt/cut-done', methods=['POST'])
def handle_api_yt_cut_done():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    query = request.args
    task_id = params.get("task_id")
    if not task_id:
        return jsonify({"error": "Keine task_id angegeben."})
        return
        
    with active_yt_tasks_lock:
        task = active_yt_tasks.get(task_id)
        
    if not task:
        return jsonify({"error": "Task nicht gefunden."})
        return
        
    task["state"] = "scanning_after_cut"
    task["event"].set()
    return jsonify({"status": "ok"})



@youtube_api.route('/yt/finalize', methods=['POST'])
def handle_api_yt_finalize():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    query = request.args
    task_id = params.get("task_id")
    mapping = params.get("mapping", {})
    
    if not task_id:
        return jsonify({"error": "Keine task_id angegeben."})
        return
        
    with active_yt_tasks_lock:
        task = active_yt_tasks.get(task_id)
        
    if not task:
        return jsonify({"error": "Task nicht gefunden."})
        return
        
    task["mapping"] = mapping
    task["state"] = "finalizing"
    task["mapping_event"].set()
    return jsonify({"status": "ok"})


