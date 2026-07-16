"""Tests for the transient-failure retry around metadata JSON fetches."""

import json
import urllib.error
import urllib.request

import pytest

from gui import mw_metadata


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self._payload).encode()


def _build_request():
    return urllib.request.Request("https://example.invalid/test")


def test_fetch_json_with_retry_recovers_from_transient_timeout(monkeypatch):
    calls = []

    def fake_urlopen(request, timeout=None):
        calls.append(timeout)
        if len(calls) == 1:
            raise TimeoutError("The read operation timed out")
        return _FakeResponse({"title": "Killing Faith"})

    logged = []
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(mw_metadata.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(mw_metadata, "log_message", logged.append)

    result = mw_metadata.fetch_json_with_retry(_build_request, context="Test")

    assert result == {"title": "Killing Faith"}
    assert len(calls) == 2
    assert len(logged) == 1
    assert "Versuch 1/3" in logged[0]


def test_fetch_json_with_retry_gives_up_visibly_after_all_attempts(monkeypatch):
    attempts = []

    def fake_urlopen(request, timeout=None):
        attempts.append(1)
        raise urllib.error.URLError("timed out")

    logged = []
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(mw_metadata.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(mw_metadata, "log_message", logged.append)

    with pytest.raises(urllib.error.URLError):
        mw_metadata.fetch_json_with_retry(_build_request, context="Test")

    assert len(attempts) == 3
    assert len(logged) == 3


def test_fetch_json_with_retry_does_not_retry_http_errors(monkeypatch):
    attempts = []

    def fake_urlopen(request, timeout=None):
        attempts.append(1)
        raise urllib.error.HTTPError("https://example.invalid", 404, "not found", None, None)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(mw_metadata.time, "sleep", lambda seconds: None)

    with pytest.raises(urllib.error.HTTPError):
        mw_metadata.fetch_json_with_retry(_build_request, context="Test")

    # A 404/401 is a real answer from the service, not a transient stall.
    assert len(attempts) == 1


def test_fetch_movie_nfo_data_logs_and_returns_error_after_retries(monkeypatch):
    def fake_urlopen(request, timeout=None):
        raise TimeoutError("The read operation timed out")

    logged = []
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(mw_metadata.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(mw_metadata, "log_message", logged.append)

    result = mw_metadata.fetch_movie_nfo_data("tmdb_movie", "1200320")

    assert "TMDB-Filmmetadaten konnten nicht geladen werden" in result["error"]
    # Three retry logs plus the final visible NFO-agent failure log.
    assert any("nicht abrufbar" in line for line in logged)
