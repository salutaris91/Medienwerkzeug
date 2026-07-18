"""Tests for OFDb film page parsing and the movie detail fetch branch."""

import urllib.error
import urllib.request

from gui import mw_metadata


SAMPLE_HTML = """<html><head><title>OFDb - Killing Faith (2025)</title></head><body>
Erscheinungsjahr: <a href="/jahr/2025">2025</a>
<div class="plot">Ein <b>düsterer</b> Western.</div>
Freigabe: FSK 16<br>
<a href="https://www.ofdb.de/view/genre/Horror/"><span class="genre">Horror</span></a>
<a href="https://www.ofdb.de/view/genre/Thriller/"><span class="genre">Thriller</span></a>
<a href="https://www.ofdb.de/person/1,Someone">Jane Doe</a>
</body></html>"""


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self._payload


def test_parse_ofdb_film_page_extracts_all_fields():
    film = mw_metadata._parse_ofdb_film_page(SAMPLE_HTML)

    assert film["title"] == "Killing Faith"
    assert film["year"] == "2025"
    assert film["plot"] == "Ein düsterer Western."
    assert film["fsk"] == "FSK 16"
    assert film["genres"] == ["Horror", "Thriller"]
    assert film["actors"] == ["Jane Doe"]


def test_fetch_movie_nfo_data_serves_ofdb_details(monkeypatch):
    requested = []

    def fake_urlopen(request, timeout=None):
        requested.append(request.full_url)
        return _FakeResponse(SAMPLE_HTML.encode())

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    result = mw_metadata.fetch_movie_nfo_data("ofdb", "ofdb_406952_Killing-Faith")

    assert requested == ["https://www.ofdb.de/film/406952,Killing-Faith/"]
    assert result["title"] == "Killing Faith"
    assert result["fsk"] == "16"
    assert result["genres"] == ["Horror", "Thriller"]
    assert "error" not in result


def test_fetch_movie_nfo_data_reports_ofdb_failures_visibly(monkeypatch):
    def fake_urlopen(request, timeout=None):
        raise urllib.error.URLError("timed out")

    logged = []
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(mw_metadata.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(mw_metadata, "log_message", logged.append)

    result = mw_metadata.fetch_movie_nfo_data("ofdb", "ofdb_406952_Killing-Faith")

    assert "OFDb-Filmmetadaten konnten nicht geladen werden" in result["error"]
    assert any("nicht abrufbar" in line for line in logged)


def test_fetch_movie_nfo_data_rejects_malformed_ofdb_id():
    result = mw_metadata.fetch_movie_nfo_data("ofdb", "ofdb_broken")

    assert "Ungültige OFDb-ID" in result["error"]


def test_generate_ofdb_nfo_writes_fsk_and_genres(tmp_path, monkeypatch):
    def fake_urlopen(request, timeout=None):
        return _FakeResponse(SAMPLE_HTML.encode())

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    result = mw_metadata.generate_ofdb_nfo("ofdb_406952_Killing-Faith", str(tmp_path), "Killing Faith (2025)")

    assert result.get("nfo") is True
    content = (tmp_path / "Killing Faith (2025).nfo").read_text(encoding="utf-8")
    assert "<mpaa>FSK 16</mpaa>" in content
    assert "<genre>Horror</genre>" in content
    assert "<genre>Thriller</genre>" in content
    assert "<title>Killing Faith</title>" in content
