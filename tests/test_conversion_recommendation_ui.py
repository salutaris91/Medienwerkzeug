from pathlib import Path

from gui.api.project_api import is_efficient_video_codec


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_efficient_video_codec_aliases_include_av1_formats():
    for codec in ("hevc", "h265", "hvc1", "x265", "vp9", "vp09", "av1", "av01"):
        assert is_efficient_video_codec(codec)


def test_h264_video_codec_still_counts_as_inefficient():
    for codec in ("h264", "avc1", "mpeg4", "xvid"):
        assert not is_efficient_video_codec(codec)


def test_quality_hints_require_conversion_checkbox():
    intel_js = (REPO_ROOT / "gui/static/js/intelligence.js").read_text(encoding="utf-8")

    assert 'document.getElementById("movie-option-convert")' in intel_js
    assert 'document.getElementById("series-option-convert")' in intel_js
    assert "hintEl.classList.add(\"hidden\")" in intel_js
    assert "!convertCb || !convertCb.checked" in intel_js


def test_dynamic_storage_target_labels_keep_word_spacing():
    index_html = (REPO_ROOT / "gui/static/index.html").read_text(encoding="utf-8")

    assert "Auf&nbsp;<span class=\"nas-target-name\">NAS</span>&nbsp;verschieben" in index_html
    assert "Auch in&nbsp;<span class=\"cloud-target-name\">pCloud</span>&nbsp;sichern" in index_html
