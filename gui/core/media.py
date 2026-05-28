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

def add_conversion_to_history(quality, codec, ratio, size_in=None, size_out=None):
    import time
    history = utils.load_konv_history()
    history.append({
        "quality": int(quality) if str(quality).isdigit() else quality,
        "codec": codec,
        "ratio": round(ratio, 4),
        "size_in": size_in,
        "size_out": size_out,
        "timestamp": time.time()
    })
    utils.save_konv_history(history)

def get_video_codec(filepath):
    try:
        cmd = ["ffprobe", "-v", "quiet", "-show_entries", "stream=codec_name", "-select_streams", "v:0", "-of", "csv=p=0", filepath]
        return subprocess.check_output(cmd, text=True, timeout=5).strip().lower()
    except Exception:
        return None

