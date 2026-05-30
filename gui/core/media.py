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

def get_historical_ratio(quality, codec="hevc"):
    history = utils.load_konv_history()
    ratios = []
    for entry in history:
        if str(entry.get("quality")) == str(quality) and entry.get("codec") == codec:
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

def konvertierung_schaetzen(filepath, quality, codec="hevc"):
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
    
    # Run test encode
    test_dur = 15.0
    ffmpeg_cmd = [
        "caffeinate", "-i", "-s", "ffmpeg", "-nostdin",
        "-ss", str(round(start_sec, 2)),
        "-i", filepath,
        "-t", str(test_dur),
        "-c:v", "hevc_videotoolbox", "-tag:v", "hvc1", "-q:v", str(quality),
        "-c:a", "copy",
        temp_out_path
    ]
    
    success = False
    try:
        # Run with a timeout to avoid hangs
        res = subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
        if res.returncode == 0 and os.path.exists(temp_out_path):
            size_out = os.path.getsize(temp_out_path)
            if size_out > 0:
                # Estimate ratio: output size for full duration divided by input size
                estimated_size = (size_out / test_dur) * duration
                estimated_ratio = estimated_size / size_in
                
                # Keep within sane boundaries
                estimated_ratio = max(0.05, min(1.5, estimated_ratio))
                success = True
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
