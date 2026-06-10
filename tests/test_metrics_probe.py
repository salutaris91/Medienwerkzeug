"""Tests für Roadmap #16: Speichermessung über killbare Probe-Prozesse
und Circuit Breaker im system_metrics_worker."""
import json
import os
import subprocess
import sys
import time
from unittest.mock import patch

import gui.workers.processor as processor
from gui.workers.processor import (
    _MetricsCircuitBreaker,
    _measure_folder_size_bytes,
    _read_target_storage,
    _run_storage_probe,
)

PROBE_PATH = processor._STORAGE_PROBE_PATH


def _run_probe_subprocess(mode, path):
    return subprocess.run(
        [sys.executable, PROBE_PATH, mode, path],
        capture_output=True, text=True, timeout=30,
    )


# --- Probe-Skript (echter Subprocess) ---

def test_probe_folder_size_returns_correct_bytes(tmp_path):
    """Es prüft, dass die Probe im Modus folder_size die Größe eines
    Testordners korrekt als JSON liefert."""
    (tmp_path / "a.bin").write_bytes(b"x" * 1000)
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.bin").write_bytes(b"y" * 500)

    result = _run_probe_subprocess("folder_size", str(tmp_path))

    assert result.returncode == 0
    assert json.loads(result.stdout) == {"bytes": 1500}


def test_probe_disk_usage_returns_valid_values(tmp_path):
    """Es prüft, dass die Probe im Modus disk_usage gültige
    total/used/free-Werte für ein existierendes Verzeichnis liefert."""
    result = _run_probe_subprocess("disk_usage", str(tmp_path))

    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["exists"] is True
    assert data["total"] > 0
    assert data["free"] >= 0
    assert data["used"] >= 0


def test_probe_disk_usage_missing_path_reports_not_exists(tmp_path):
    """Es prüft, dass die Probe für einen nicht existierenden Pfad
    exists=False liefert."""
    result = _run_probe_subprocess("disk_usage", str(tmp_path / "missing"))

    assert result.returncode == 0
    assert json.loads(result.stdout) == {"exists": False}


def test_probe_rejects_unknown_mode():
    """Es prüft, dass die Probe bei unbekanntem Modus mit Usage-Hinweis
    und Exit-Code 2 abbricht."""
    result = _run_probe_subprocess("invalid_mode", "/tmp")

    assert result.returncode == 2
    assert "usage" in result.stderr


# --- _run_storage_probe (Eltern-Seite) ---

def test_run_storage_probe_kills_hanging_process_and_logs(tmp_path):
    """Es prüft, dass _run_storage_probe einen hängenden Probe-Prozess nach
    dem Timeout killt, (None, True) zurückgibt und den Timeout loggt."""
    hanging_probe = tmp_path / "hanging_probe.py"
    hanging_probe.write_text("import time\ntime.sleep(60)\n")

    logged = []
    with patch.object(processor, "_STORAGE_PROBE_PATH", str(hanging_probe)), \
         patch.object(processor, "log_message", logged.append):
        start = time.monotonic()
        result, timed_out = _run_storage_probe("folder_size", "/tmp", timeout_sec=1)
        elapsed = time.monotonic() - start

    assert result is None
    assert timed_out is True
    assert elapsed < 10
    assert any("Timeout" in msg for msg in logged)


def test_run_storage_probe_logs_probe_errors(tmp_path):
    """Es prüft, dass Probe-Fehler (Exit-Code != 0) None liefern und der
    stderr-Inhalt geloggt wird."""
    failing_probe = tmp_path / "failing_probe.py"
    failing_probe.write_text(
        "import sys\nprint('probe exploded', file=sys.stderr)\nsys.exit(1)\n"
    )

    logged = []
    with patch.object(processor, "_STORAGE_PROBE_PATH", str(failing_probe)), \
         patch.object(processor, "log_message", logged.append):
        result, timed_out = _run_storage_probe("folder_size", "/tmp")

    assert result is None
    assert timed_out is False
    assert any("probe exploded" in msg for msg in logged)


def test_run_storage_probe_returns_parsed_json(tmp_path):
    """Es prüft, dass _run_storage_probe das JSON-Ergebnis der echten Probe
    parst und ohne Timeout zurückgibt."""
    (tmp_path / "a.bin").write_bytes(b"x" * 42)

    result, timed_out = _run_storage_probe("folder_size", str(tmp_path))

    assert timed_out is False
    assert result == {"bytes": 42}


# --- Circuit Breaker ---

def test_breaker_pauses_after_threshold_timeouts_and_logs():
    """Es prüft, dass der Circuit Breaker nach 3 aufeinanderfolgenden
    Timeouts die Messung pausiert und dies loggt."""
    logged = []
    with patch.object(processor, "log_message", logged.append):
        breaker = _MetricsCircuitBreaker(threshold=3, pause_sec=600)
        for _ in range(3):
            assert breaker.allows("inbox") is True
            breaker.record_timeout("inbox")

        assert breaker.allows("inbox") is False
    assert any("pausiert" in msg for msg in logged)


def test_breaker_allows_again_after_pause_expires():
    """Es prüft, dass der Circuit Breaker nach Ablauf der Pause wieder
    Messungen zulässt."""
    with patch.object(processor, "log_message", lambda msg: None):
        breaker = _MetricsCircuitBreaker(threshold=1, pause_sec=600)
        breaker.record_timeout("outbox")
        assert breaker.allows("outbox") is False

        # Pausenende deterministisch in die Vergangenheit legen
        breaker._paused_until["outbox"] = time.time() - 1
        assert breaker.allows("outbox") is True
        # Pause ist abgebaut, der Schlüssel ist wieder normal nutzbar
        assert breaker.allows("outbox") is True


def test_breaker_resets_counter_on_result():
    """Es prüft, dass ein erfolgreiches Ergebnis den Timeout-Zähler
    zurücksetzt."""
    with patch.object(processor, "log_message", lambda msg: None):
        breaker = _MetricsCircuitBreaker(threshold=3, pause_sec=600)
        breaker.record_timeout("inbox")
        breaker.record_timeout("inbox")
        breaker.record_result("inbox")
        breaker.record_timeout("inbox")
        breaker.record_timeout("inbox")
        assert breaker.allows("inbox") is True


# --- Integration in die Messfunktionen ---

def test_measure_folder_size_skips_when_breaker_open():
    """Es prüft, dass _measure_folder_size_bytes bei offenem Breaker keine
    Probe startet und None liefert."""
    with patch.object(processor, "log_message", lambda msg: None):
        breaker = _MetricsCircuitBreaker(threshold=1, pause_sec=600)
        breaker.record_timeout("inbox")

        with patch.object(processor, "_run_storage_probe") as probe_mock:
            assert _measure_folder_size_bytes("/tmp", breaker, "inbox") is None
            probe_mock.assert_not_called()


def test_measure_folder_size_records_timeout_in_breaker():
    """Es prüft, dass ein Probe-Timeout im Breaker gezählt wird und die
    Messung None liefert."""
    with patch.object(processor, "log_message", lambda msg: None):
        breaker = _MetricsCircuitBreaker(threshold=1, pause_sec=600)
        with patch.object(processor, "_run_storage_probe", return_value=(None, True)):
            assert _measure_folder_size_bytes("/tmp", breaker, "inbox") is None
        assert breaker.allows("inbox") is False


def test_read_target_storage_uses_probe_for_local_path(tmp_path):
    """Es prüft, dass _read_target_storage für ein lokales Ziel die Probe
    nutzt und die Speicherwerte übernimmt."""
    target = {"name": "NAS", "type": "smb", "root_path": str(tmp_path)}
    usage = {"exists": True, "total": 1000, "used": 250, "free": 750}

    with patch.object(processor, "_run_storage_probe", return_value=(usage, False)) as probe_mock:
        info = _read_target_storage(target)

    probe_mock.assert_called_once_with("disk_usage", str(tmp_path))
    assert info["available"] is True
    assert info["total"] == 1000
    assert info["used_percent"] == 25.0


def test_read_target_storage_skips_probe_when_breaker_open(tmp_path):
    """Es prüft, dass _read_target_storage bei offenem Breaker keine Probe
    startet und einen sprechenden Fehler liefert."""
    target = {"name": "NAS", "type": "smb", "root_path": str(tmp_path)}
    key = f"target:{tmp_path}"

    with patch.object(processor, "log_message", lambda msg: None):
        breaker = _MetricsCircuitBreaker(threshold=1, pause_sec=600)
        breaker.record_timeout(key)

        with patch.object(processor, "_run_storage_probe") as probe_mock:
            info = _read_target_storage(target, breaker=breaker)

    probe_mock.assert_not_called()
    assert info["available"] is False
    assert "pausiert" in info["error"]


def test_read_target_storage_timeout_sets_error_and_breaker(tmp_path):
    """Es prüft, dass ein disk_usage-Timeout als Fehler gemeldet und im
    Breaker gezählt wird."""
    target = {"name": "NAS", "type": "smb", "root_path": str(tmp_path)}
    key = f"target:{tmp_path}"

    with patch.object(processor, "log_message", lambda msg: None):
        breaker = _MetricsCircuitBreaker(threshold=1, pause_sec=600)
        with patch.object(processor, "_run_storage_probe", return_value=(None, True)):
            info = _read_target_storage(target, breaker=breaker)
        assert breaker.allows(key) is False

    assert info["available"] is False
    assert "Timeout" in info["error"]


def test_read_target_storage_prefers_rclone_remote(tmp_path):
    """Es prüft, dass bei konfiguriertem rclone-Remote weiterhin rclone
    befragt wird und keine disk_usage-Probe läuft."""
    target = {"name": "pCloud", "type": "rclone", "rclone_remote": "pcloud:", "root_path": str(tmp_path)}
    about = {"total": 2000, "used": 500, "free": 1500}

    with patch.object(processor, "_rclone_about", return_value=about) as rclone_mock, \
         patch.object(processor, "_run_storage_probe") as probe_mock:
        info = _read_target_storage(target)

    rclone_mock.assert_called_once_with("pcloud:")
    probe_mock.assert_not_called()
    assert info["available"] is True
    assert info["used_percent"] == 25.0
