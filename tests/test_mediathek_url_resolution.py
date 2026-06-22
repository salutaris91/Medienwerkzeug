import pytest
from unittest.mock import patch, MagicMock
import urllib.request
import urllib.error
import json
from gui.mw_metadata import resolve_mediathek_url_topic, SmartRedirectHandler, fetch_mediathek_episodes
from gui.main import app

def test_smart_redirect_handler():
    # Mock redirect behavior
    handler = SmartRedirectHandler()
    req = MagicMock()
    req.full_url = "https://example.com/start"
    fp = MagicMock()
    headers = {"Location": "/redirect-target"}

    # We mock parent and redirect_request
    handler.parent = MagicMock()
    handler.redirect_request = MagicMock(return_value="mock_redirected_request")

    handler.http_error_308(req, fp, 308, "Permanent Redirect", headers)

    handler.redirect_request.assert_called_once_with(req, fp, 307, "Permanent Redirect", headers, "https://example.com/redirect-target")
    handler.parent.open.assert_called_once_with("mock_redirected_request")

def test_resolve_mediathek_url_topic_scraping_success():
    # Test successful scraping
    html_content = "<html><head><title>Tatort: Borowski und das Meer - ARD Mediathek</title></head></html>"

    mock_response = MagicMock()
    mock_response.read.return_value = html_content.encode('utf-8')

    with patch('urllib.request.build_opener') as mock_build:
        mock_opener = MagicMock()
        mock_opener.open.return_value.__enter__.return_value = mock_response
        mock_build.return_value = mock_opener

        # Test scraping resolving to title
        res = resolve_mediathek_url_topic("https://www.ardmediathek.de/sendung/tatort/Y3JpZDovLz")
        assert res == "Tatort: Borowski und das Meer"

def test_resolve_mediathek_url_topic_title_cleanups():
    # Test title cleanup variants (heute-show must stay today-show, splits only on spacers)
    titles = [
        ("Vorschau: heute-show - ZDFmediathek", "heute-show"),
        ("Tatort: Der feine Geist | ARD Mediathek", "Tatort: Der feine Geist"),
        ("Serengeti • Das Abenteuer - ARD", "Serengeti"),
        ("Ein Film - Doku - ZDF", "Ein Film")
    ]

    for raw_title, cleaned in titles:
        html = f"<html><title>{raw_title}</title></html>"
        mock_resp = MagicMock()
        mock_resp.read.return_value = html.encode('utf-8')

        with patch('urllib.request.build_opener') as mock_build:
            mock_opener = MagicMock()
            mock_opener.open.return_value.__enter__.return_value = mock_resp
            mock_build.return_value = mock_opener

            res = resolve_mediathek_url_topic("https://example.com/show")
            assert res == cleaned

def test_resolve_mediathek_url_topic_heuristics_fallback():
    # Test heuristics fallback when urllib fails (404/ConnectionError)
    with patch('urllib.request.build_opener') as mock_build:
        mock_opener = MagicMock()
        mock_opener.open.side_effect = urllib.error.HTTPError("https://example.com/show", 404, "Not Found", {}, None)
        mock_build.return_value = mock_opener

        # ZDF comedy URL
        res_zdf = resolve_mediathek_url_topic("https://www.zdf.de/comedy/heute-show")
        assert res_zdf == "Heute Show"

        # ZDF shows with trailing id
        res_zdf_id = resolve_mediathek_url_topic("https://www.zdf.de/shows/heute-show-104")
        assert res_zdf_id == "Heute Show"

        # ARD URL
        res_ard = resolve_mediathek_url_topic("https://www.ardmediathek.de/sendung/tatort/Y3JpZDovL2Rhc2Vyc3RlLmRlL3RhdG9ydA")
        assert res_ard == "Tatort"

        # Arte URL
        res_arte = resolve_mediathek_url_topic("https://www.arte.tv/de/videos/RC-023959/serengeti/")
        assert res_arte == "Serengeti"

        # Generic fallback
        res_generic = resolve_mediathek_url_topic("https://example.com/shows/my-custom-docu-series")
        assert res_generic == "My Custom Docu Series"

def test_resolve_mediathek_url_topic_unresolvable_url():
    # Test that an unresolvable URL (e.g. homepage without relevant path parts and scraping fails)
    # resolves to None instead of the raw URL.
    with patch('urllib.request.build_opener') as mock_build:
        mock_opener = MagicMock()
        mock_opener.open.side_effect = urllib.error.HTTPError("https://www.zdf.de", 404, "Not Found", {}, None)
        mock_build.return_value = mock_opener

        res = resolve_mediathek_url_topic("https://www.zdf.de")
        assert res is None

def test_fetch_mediathek_episodes_with_url():
    # Test fetch_mediathek_episodes when passed a URL.
    # It should first resolve it using resolve_mediathek_url_topic and then query the API.

    dummy_response = {
        "result": {
            "results": [
                {"title": "Tatort 1", "timestamp": 1700000000, "description": "Plot 1"}
            ]
        }
    }

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(dummy_response).encode('utf-8')

    with patch('gui.mw_metadata.resolve_mediathek_url_topic', return_value="Tatort") as mock_resolve, \
         patch('urllib.request.urlopen') as mock_urlopen:

        mock_urlopen.return_value.__enter__.return_value = mock_resp

        url_input = "https://www.ardmediathek.de/sendung/tatort/Y3JpZ"
        res = fetch_mediathek_episodes(f"url_mediathek:{url_input}")

        mock_resolve.assert_called_once_with(url_input)
        assert len(res) == 1
        assert res["1"]["title"] == "Tatort 1"

def test_api_search_url_resolution():
    # Test /api/search using Flask test client
    app.config['TESTING'] = True
    client = app.test_client()

    with patch('gui.api.search_api.mw_metadata.resolve_mediathek_url_topic', return_value="Heute Show") as mock_resolve, \
         patch('gui.api.search_api.mw_metadata.fetch_ytdlp_url_metadata', return_value=[]):

        response = client.get('/api/search?q=https://www.zdf.de/comedy/heute-show&type=tv')
        assert response.status_code == 200
        data = response.get_json()

        assert len(data) == 1
        assert data[0]["id"] == "url_mediathek:Heute Show"
        assert data[0]["name"] == "Heute Show (Mediathek Serie aus URL)"
        assert data[0]["provider"] == "mediathek"
        mock_resolve.assert_called_once_with("https://www.zdf.de/comedy/heute-show")
