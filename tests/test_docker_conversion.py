import os
from unittest.mock import patch
from gui.core.media import build_hevc_ffmpeg_cmd


def test_build_ffmpeg_cmd_mac_desktop():
    """Test standard macOS desktop behavior: should use caffeinate and hevc_videotoolbox."""
    with patch("sys.platform", "darwin"):
        with patch.dict(os.environ, {"MW_RUNTIME": "desktop"}):
            cmd = build_hevc_ffmpeg_cmd("/path/to/in.mp4", "/path/to/out.mkv", 60)
            
            assert cmd[0] == "caffeinate"
            assert cmd[1] == "-i"
            assert cmd[2] == "-s"
            assert cmd[3] == "ffmpeg"
            assert cmd[4] == "-nostdin"
            
            # Check input and output paths
            ffmpeg_idx = cmd.index("ffmpeg")
            assert "-i" in cmd[ffmpeg_idx:]
            input_idx = cmd.index("-i", ffmpeg_idx)
            assert cmd[input_idx + 1] == "/path/to/in.mp4"
            assert cmd[-1] == "/path/to/out.mkv"
            
            # Check codec and quality parameters
            assert "-c:v" in cmd
            codec_idx = cmd.index("-c:v")
            assert cmd[codec_idx + 1] == "hevc_videotoolbox"
            
            assert "-q:v" in cmd
            q_idx = cmd.index("-q:v")
            assert cmd[q_idx + 1] == "60"
            
            assert "-tag:v" in cmd
            tag_idx = cmd.index("-tag:v")
            assert cmd[tag_idx + 1] == "hvc1"


def test_build_ffmpeg_cmd_mac_but_docker():
    """Test macOS host but running inside a Docker container: should use libx265 and no caffeinate."""
    # Even if sys.platform is darwin (unlikely in container, but test logic),
    # MW_RUNTIME=docker should disable macOS hardware acceleration/caffeinate.
    with patch("sys.platform", "darwin"):
        with patch.dict(os.environ, {"MW_RUNTIME": "docker"}):
            cmd = build_hevc_ffmpeg_cmd("/path/to/in.mp4", "/path/to/out.mkv", 60)
            
            assert cmd[0] == "ffmpeg"
            assert cmd[1] == "-nostdin"
            
            assert "-c:v" in cmd
            codec_idx = cmd.index("-c:v")
            assert cmd[codec_idx + 1] == "libx265"
            
            assert "-crf" in cmd
            crf_idx = cmd.index("-crf")
            assert cmd[crf_idx + 1] == "26"


def test_build_ffmpeg_cmd_docker_linux():
    """Test standard Docker container behavior (Linux host, docker runtime): should use libx265 and no caffeinate."""
    with patch("sys.platform", "linux"):
        with patch.dict(os.environ, {"MW_RUNTIME": "docker"}):
            cmd = build_hevc_ffmpeg_cmd("/path/to/in.mp4", "/path/to/out.mkv", 60)
            
            assert cmd[0] == "ffmpeg"
            assert cmd[1] == "-nostdin"
            
            # Check codec and mapped CRF
            assert "-c:v" in cmd
            codec_idx = cmd.index("-c:v")
            assert cmd[codec_idx + 1] == "libx265"
            
            assert "-crf" in cmd
            crf_idx = cmd.index("-crf")
            assert cmd[crf_idx + 1] == "26"
            
            assert "-tag:v" in cmd
            tag_idx = cmd.index("-tag:v")
            assert cmd[tag_idx + 1] == "hvc1"


def test_build_ffmpeg_cmd_linux_desktop():
    """Test Linux desktop behavior: should use libx265 and no caffeinate."""
    with patch("sys.platform", "linux"):
        with patch.dict(os.environ, {"MW_RUNTIME": "desktop"}):
            cmd = build_hevc_ffmpeg_cmd("/path/to/in.mp4", "/path/to/out.mkv", 60)
            
            assert cmd[0] == "ffmpeg"
            
            assert "-c:v" in cmd
            codec_idx = cmd.index("-c:v")
            assert cmd[codec_idx + 1] == "libx265"


def test_build_ffmpeg_cmd_with_time_options():
    """Test build_hevc_ffmpeg_cmd handles start_sec and duration correctly."""
    with patch("sys.platform", "linux"):
        with patch.dict(os.environ, {"MW_RUNTIME": "docker"}):
            cmd = build_hevc_ffmpeg_cmd("/path/to/in.mp4", "/path/to/out.mkv", 60, start_sec=12.345, duration=15.0)
            
            assert "-ss" in cmd
            ss_idx = cmd.index("-ss")
            assert cmd[ss_idx + 1] == "12.35"  # Rounded to 2 decimal places
            
            assert "-t" in cmd
            t_idx = cmd.index("-t")
            assert cmd[t_idx + 1] == "15.0"


def test_quality_mapping_crf_ranges():
    """Test CRF mapping formula under Docker/Linux for various quality levels."""
    with patch("sys.platform", "linux"):
        with patch.dict(os.environ, {"MW_RUNTIME": "docker"}):
            # Test key values
            # q=100 -> CRF 18
            cmd_100 = build_hevc_ffmpeg_cmd("in.mp4", "out.mkv", 100)
            assert cmd_100[cmd_100.index("-crf") + 1] == "18"
            
            # q=60 -> CRF 26
            cmd_60 = build_hevc_ffmpeg_cmd("in.mp4", "out.mkv", 60)
            assert cmd_60[cmd_60.index("-crf") + 1] == "26"
            
            # q=50 -> CRF 28
            cmd_50 = build_hevc_ffmpeg_cmd("in.mp4", "out.mkv", 50)
            assert cmd_50[cmd_50.index("-crf") + 1] == "28"
            
            # q=0 -> CRF 38
            cmd_0 = build_hevc_ffmpeg_cmd("in.mp4", "out.mkv", 0)
            assert cmd_0[cmd_0.index("-crf") + 1] == "38"
            
            # Test clipping boundaries
            # q=200 -> CRF clipped to min 10
            cmd_high = build_hevc_ffmpeg_cmd("in.mp4", "out.mkv", 200)
            assert cmd_high[cmd_high.index("-crf") + 1] == "10"
            
            # q=-50 -> CRF clipped to max 45
            cmd_low = build_hevc_ffmpeg_cmd("in.mp4", "out.mkv", -50)
            assert cmd_low[cmd_low.index("-crf") + 1] == "45"
            
            # Test invalid/string quality values fallback to q=60 -> CRF 26
            cmd_invalid = build_hevc_ffmpeg_cmd("in.mp4", "out.mkv", "invalid_quality")
            assert cmd_invalid[cmd_invalid.index("-crf") + 1] == "26"
