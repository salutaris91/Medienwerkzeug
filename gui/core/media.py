import os
import re
import json
import subprocess
import tempfile
import uuid
from . import utils

def get_video_duration(filepath):
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", filepath]
        out = subprocess.check_output(cmd, text=True).strip()
        return float(out)
    except Exception as e:
        print(f"Error getting video duration: {e}")
        return None

def get_historical_ratio(quality, codec="hevc_libx265"):
    history = utils.load_konv_history()
    ratios = []
    for entry in history:
        # Legacy entries often had "hevc", treat them as "hevc_libx265" for backwards compatibility
        entry_codec = entry.get("codec")
        if entry_codec == "hevc":
            entry_codec = "hevc_libx265"
            
        if str(entry.get("quality")) == str(quality) and entry_codec == codec:
            try:
                ratios.append(float(entry.get("ratio")))
            except (ValueError, TypeError):
                pass
                
    if ratios:
        ratios.sort()
        n = len(ratios)
        if n % 2 == 1:
            return ratios[n // 2]
        else:
            return (ratios[n // 2 - 1] + ratios[n // 2]) / 2.0
            
    # Default fallbacks based on quality
    try:
        q_val = int(quality)
    except ValueError:
        q_val = 60
        
    # Standard logic: higher quality factor -> less compression -> higher ratio
    # q=50: ~0.4, q=60: ~0.5, q=70: ~0.65, q=80: ~0.8
    if q_val <= 50:
        return 0.40
    elif q_val <= 60:
        return 0.50
    elif q_val <= 70:
        return 0.65
    else:
        return 0.80

def build_hevc_ffmpeg_cmd(input_path, output_path, quality, start_sec=None, duration=None, force_software=False):
    """
    Erstellt das passende FFmpeg-Kommando zur H.265 (HEVC)-Konvertierung basierend auf der Plattform.
    
    - Unter macOS Desktop (darwin & kein Docker): caffeinate + hevc_videotoolbox (Hardware-Beschleunigung)
    - Andere Plattformen (Docker, Linux):
      - Falls Hardware (/dev/dri/renderD*) vorhanden und force_software=False: VAAPI Hardware-Encoding
      - Sonst: libx265 (Software-Encoding) mit Qualitäts-Mapping
    """
    import sys
    import glob
    import os
    
    is_docker = utils.get_runtime_capabilities()["runtime"] == "docker"
    use_mac_hw = (sys.platform == "darwin" and not is_docker and not force_software)
    
    vaapi_device = None
    if is_docker and not force_software:
        devices = glob.glob('/dev/dri/renderD*')
        for dev in sorted(devices):
            if os.access(dev, os.R_OK | os.W_OK):
                vaapi_device = dev
                break
                
    cmd = []
    if use_mac_hw:
        cmd.extend(["caffeinate", "-i", "-s"])
        
    cmd.append("ffmpeg")
    cmd.append("-nostdin")
    
    if vaapi_device:
        cmd.extend(["-vaapi_device", vaapi_device])
        
    if start_sec is not None:
        cmd.extend(["-ss", str(round(start_sec, 2))])
        
    cmd.extend(["-i", input_path])
    
    if duration is not None:
        cmd.extend(["-t", str(duration)])
        
    if use_mac_hw:
        cmd.extend([
            "-c:v", "hevc_videotoolbox",
            "-tag:v", "hvc1",
            "-q:v", str(quality)
        ])
    elif vaapi_device:
        try:
            q_val = float(quality)
        except (ValueError, TypeError):
            q_val = 60.0
            
        if q_val >= 100:
            qp = 22
        elif q_val >= 60:
            qp = 28 - int((q_val - 60) * (6 / 40))
        elif q_val >= 50:
            qp = 30 - int((q_val - 50) * (2 / 10))
        elif q_val >= 30:
            qp = 34 - int((q_val - 30) * (4 / 20))
        else:
            qp = 34 + int((30 - q_val) * (4 / 30))
            
        cmd.extend([
            "-vf", "format=nv12,hwupload",
            "-c:v", "hevc_vaapi",
            "-qp", str(int(qp))
        ])
    else:
        try:
            q_val = float(quality)
        except (ValueError, TypeError):
            q_val = 60.0
            
        crf = round(38.0 - (q_val * 0.2))
        crf = max(10, min(45, crf))
        
        cmd.extend([
            "-c:v", "libx265",
            "-tag:v", "hvc1",
            "-crf", str(crf)
        ])
        
    cmd.extend(["-c:a", "copy"])
    cmd.append(output_path)
    return cmd

def konvertierung_schaetzen(filepath, quality, codec=None):
    # Determine the codec that will likely be used
    if not codec:
        test_cmd = build_hevc_ffmpeg_cmd(filepath, "dummy.mkv", quality)
        codec = "hevc_vaapi" if "-vaapi_device" in test_cmd else ("hevc_videotoolbox" if "-c:v" in test_cmd and "hevc_videotoolbox" in test_cmd else "hevc_libx265")

    if not os.path.exists(filepath):
        return get_historical_ratio(quality, codec)
        
    duration = get_video_duration(filepath)
    size_in = os.path.getsize(filepath)
    
    if not duration or size_in == 0:
        return get_historical_ratio(quality, codec)
        
    # Run a 15-second test encode from the middle of the video
    start_sec = max(0.0, duration / 2.0 - 7.5)
    
    # Save the temporary file inside the data directory to keep it self-contained
    temp_dir = os.path.join(utils.DATA_DIR, "temp")
    os.makedirs(temp_dir, exist_ok=True)
    temp_out_path = os.path.join(temp_dir, f"test_encode_{uuid.uuid4().hex}.mkv")
    
    test_dur = 15.0
    
    def run_test(force_soft):
        cmd = build_hevc_ffmpeg_cmd(filepath, temp_out_path, quality, start_sec=start_sec, duration=test_dur, force_software=force_soft)
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
        return res, cmd

    try:
        res, used_cmd = run_test(force_soft=False)
        
        # Fallback if VAAPI failed
        if res.returncode != 0 and "-vaapi_device" in used_cmd:
            if os.path.exists(temp_out_path):
                try: os.remove(temp_out_path)
                except Exception: pass
            res, used_cmd = run_test(force_soft=True)
            codec = "hevc_libx265"
            
        if res.returncode == 0 and os.path.exists(temp_out_path):
            size_out = os.path.getsize(temp_out_path)
            if size_out > 0:
                # Estimate ratio: output size for full duration divided by input size
                estimated_size = (size_out / test_dur) * duration
                estimated_ratio = estimated_size / size_in
                
                # Keep within sane boundaries
                estimated_ratio = max(0.05, min(1.5, estimated_ratio))
                return round(estimated_ratio, 4)
    except Exception as e:
        print(f"Error during test encode estimation: {e}")
    finally:
        # Clean up
        if os.path.exists(temp_out_path):
            try:
                os.remove(temp_out_path)
            except Exception:
                pass
                
    # Fallback to history if test encode failed
    return get_historical_ratio(quality, codec)

def add_conversion_to_history(quality, codec, ratio, size_in=None, size_out=None, content_type=None, filename=None, resolution=None):
    import time
    history = utils.load_konv_history()
    history.append({
        "quality": int(quality) if str(quality).isdigit() else quality,
        "codec": codec,
        "ratio": round(ratio, 4),
        "size_in": size_in,
        "size_out": size_out,
        "timestamp": time.time(),
        "content_type": content_type,
        "filename": filename,
        "resolution": resolution
    })
    utils.save_konv_history(history)

def get_video_codec(filepath):
    try:
        cmd = ["ffprobe", "-v", "quiet", "-show_entries", "stream=codec_name", "-select_streams", "v:0", "-of", "csv=p=0", filepath]
        return subprocess.check_output(cmd, text=True, timeout=5).strip().lower()
    except Exception:
        return None


def get_media_info(filepath):
    """Liefert Codec, Auflösung, Dauer und Größe einer Videodatei via einem ffprobe-Aufruf.

    Rückgabe-dict (Felder None, falls nicht ermittelbar):
        {"codec", "width", "height", "duration", "size"}
    """
    info = {"codec": None, "width": None, "height": None, "duration": None, "size": None}
    try:
        info["size"] = os.path.getsize(filepath)
    except OSError:
        pass
    try:
        cmd = ["ffprobe", "-v", "quiet", "-print_format", "json",
               "-show_format", "-show_streams", filepath]
        out = subprocess.check_output(cmd, text=True, timeout=15)
        data = json.loads(out)
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video":
                info["codec"] = (stream.get("codec_name") or "").lower() or None
                info["width"] = stream.get("width")
                info["height"] = stream.get("height")
                break
        dur = data.get("format", {}).get("duration")
        if dur is not None:
            try:
                info["duration"] = float(dur)
            except (ValueError, TypeError):
                pass
    except Exception:
        pass
    return info


def get_conversion_recommendations():
    import statistics
    history = utils.load_konv_history()
    
    # Gruppieren nach content_type
    groups = {}
    total_saved = 0
    total_conv = len(history)
    
    for entry in history:
        ct = entry.get("content_type")
        if not ct:
            filename = entry.get("filename") or ""
            fn_lower = filename.lower()
            if any(k in fn_lower for k in ["doku", "documentary", "dokumentation", "planet", "erde", "natur"]):
                ct = "doku"
            elif any(k in fn_lower for k in ["anime", "manga", "sub", "dub", "ger sub", "eng sub"]):
                ct = "anime"
            elif re.search(r"s\d{1,2}e\d{1,2}", fn_lower) or any(k in fn_lower for k in ["staffel", "season"]):
                ct = "live_action"
            elif re.search(r"\b(19|20)\d{2}\b", fn_lower):
                ct = "movie"
            else:
                ct = "unknown"
        
        if ct not in groups:
            groups[ct] = []
        groups[ct].append(entry)
        
        # Calculate saved bytes
        size_in = entry.get("size_in")
        size_out = entry.get("size_out")
        if size_in and size_out and size_in > size_out:
            total_saved += (size_in - size_out)
            
    recommendations = {}
    
    for ct, entries in groups.items():
        if ct == "unknown" or len(entries) < 3:
            continue
            
        ratios = [e["ratio"] for e in entries if e.get("ratio")]
        qualities = [e["quality"] for e in entries if isinstance(e.get("quality"), int)]
        
        if not ratios or not qualities:
            continue
            
        avg_ratio = statistics.median(ratios)
        # Optimal quality is median quality (oder mode)
        try:
            optimal_quality = statistics.mode(qualities)
        except statistics.StatisticsError:
            optimal_quality = statistics.median(qualities)
            
        recommendations[ct] = {
            "optimal_quality": int(optimal_quality),
            "avg_ratio": round(avg_ratio, 4),
            "sample_count": len(entries),
            "confidence": "high" if len(entries) >= 10 else "medium"
        }
        
    global_avg = 0
    if total_conv > 0:
        all_ratios = [e["ratio"] for e in history if e.get("ratio")]
        if all_ratios:
            global_avg = sum(all_ratios) / len(all_ratios)
            
    return {
        "recommendations": recommendations,
        "global": {
            "avg_ratio": round(global_avg, 4),
            "total_conversions": total_conv,
            "total_saved_bytes": total_saved
        }
    }


def execute_video_conversion(
    target_filepath,
    temp_output,
    final_filepath,
    quality,
    content_type,
    original_filename,
    delete_original,
    progress_callback,
    log_message_fn,
    run_ffmpeg_fn,
    send_to_trash_fn,
    log_queue=None
):
    log_message_fn(f"Konvertiere {os.path.basename(target_filepath)} nach H.265 (Qualität {quality})...")
    ffmpeg_cmd = build_hevc_ffmpeg_cmd(target_filepath, temp_output, quality)
    used_codec = "hevc_vaapi" if "-vaapi_device" in ffmpeg_cmd else ("hevc_videotoolbox" if "-c:v" in ffmpeg_cmd and "hevc_videotoolbox" in ffmpeg_cmd else "hevc_libx265")
    try:
        success = run_ffmpeg_fn(ffmpeg_cmd, target_filepath, task_id=progress_callback, log_queue=log_queue)
        
        if not success and "-vaapi_device" in ffmpeg_cmd:
            log_message_fn("⚠️ Hardware-Encoding fehlgeschlagen. Versuche Fallback auf Software-Encoding (libx265)...")
            if os.path.exists(temp_output):
                try: os.remove(temp_output)
                except Exception: pass
            ffmpeg_cmd = build_hevc_ffmpeg_cmd(target_filepath, temp_output, quality, force_software=True)
            used_codec = "hevc_libx265"
            success = run_ffmpeg_fn(ffmpeg_cmd, target_filepath, task_id=progress_callback, log_queue=log_queue)

        if success and os.path.exists(temp_output) and os.path.getsize(temp_output) > 0:
            log_message_fn("Konvertierung erfolgreich beendet.")
            try:
                size_in = os.path.getsize(target_filepath)
                size_out = os.path.getsize(temp_output)
                if size_in > 0:
                    ratio = size_out / size_in
                    add_conversion_to_history(quality, used_codec, ratio, size_in, size_out, content_type=content_type, filename=original_filename, resolution=None)
                    log_message_fn(f"Konvertierungs-Verhältnis erfasst: {ratio:.4f}")
            except Exception as e:
                log_message_fn(f"Fehler beim Erfassen des Konvertierungs-Verhältnisses: {e}")
            if delete_original:
                send_to_trash_fn(target_filepath)
                log_message_fn("Originaldatei in Quarantäne verschoben.")
            if os.path.exists(final_filepath):
                send_to_trash_fn(final_filepath)
            os.rename(temp_output, final_filepath)
            return True, os.path.basename(final_filepath)
        else:
            log_message_fn(f"❌ Fehler bei der Konvertierung von {os.path.basename(target_filepath)}.")
            if os.path.exists(temp_output):
                os.remove(temp_output)
            return False, None
    except Exception as e:
        log_message_fn(f"Konvertierungsfehler: {e}")
        if os.path.exists(temp_output):
            os.remove(temp_output)
        return False, None
