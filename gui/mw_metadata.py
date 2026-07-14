import sys
import json
import urllib.request
from gui.core import artwork_validators
from gui.core.utils import load_settings
from gui.core.persistence import load_env_keys
from gui.core.helpers import log_message

def _download_with_timeout(url, path, timeout=10):
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r, open(path, "wb") as f:
            f.write(r.read())
    except Exception as e:
        print(f"Warning: Download failed: {e}")
        raise e

def get_ext_from_url(url, fallback=".jpg"):
    try:
        parsed = urllib.parse.urlparse(url)
        _, ext = os.path.splitext(parsed.path)
        if ext:
            ext_lower = ext.lower()
            if ext_lower in (".jpg", ".jpeg", ".png", ".webp"):
                if ext_lower == ".jpeg":
                    return ".jpg"
                return ext_lower
    except Exception:
        pass
    return fallback

import urllib.parse
import re
import os
import time
import xml.sax.saxutils

def escape_xml(s):
    if s is None:
        return ""
    # Standard XML escaping for &, <, >
    # Also escape double/single quotes to be safe in attributes/text
    return xml.sax.saxutils.escape(str(s), {'"': '&quot;', "'": '&apos;'})

# --- .env Datei parsen (Hausregel #1: Keine Secrets im Code) ---
env_keys = load_env_keys()
os.environ.pop("TVDB_API_KEY", None)
os.environ.pop("TMDB_API_KEY", None)
for k, v in env_keys.items():
    os.environ[k] = v

TVDB_API_KEY = os.environ.get("TVDB_API_KEY", "")
TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")
tvdb_token = None
tvdb_token_time = 0

def reload_metadata_keys():
    global TVDB_API_KEY, TMDB_API_KEY, tvdb_token, tvdb_token_time
    env_keys = load_env_keys()
    os.environ.pop("TVDB_API_KEY", None)
    os.environ.pop("TMDB_API_KEY", None)
    for k, v in env_keys.items():
        os.environ[k] = v
    TVDB_API_KEY = os.environ.get("TVDB_API_KEY", "")
    TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")
    tvdb_token = None
    tvdb_token_time = 0


class MetadataProviderUnavailable(Exception):
    def __init__(self, message, status_code=503):
        super().__init__(message)
        self.status_code = status_code

def check_tmdb_auth_method():
    """
    Checks the format of TMDB_API_KEY and returns ('v3', key) or ('v4', token)
    or raises MetadataProviderUnavailable if invalid.
    """
    key = TMDB_API_KEY.strip()
    if not key:
        raise MetadataProviderUnavailable("TMDb API-Key ist nicht konfiguriert.", status_code=502)

    import re
    if len(key) == 32 and re.match(r'^[0-9a-fA-F]{32}$', key):
        return 'v3', key

    if len(key) > 50 and '.' in key:
        return 'v4', key
    raise MetadataProviderUnavailable(
        "Ungueltiges Format fuer den TMDb API-Key. Erwartet wird ein 32-stelliger v3 API-Key oder ein v4 Read Access Token (JWT).",
        status_code=502
    )

def make_tmdb_request(url, headers=None):
    import urllib.request
    import urllib.parse

    if headers is None:
        headers = {'User-Agent': 'Mozilla/5.0'}
    else:
        headers = headers.copy()
        if 'User-Agent' not in headers:
            headers['User-Agent'] = 'Mozilla/5.0'

    method, key = check_tmdb_auth_method()

    if method == 'v4':
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qsl(parsed.query)
        new_params = [(k, v) for k, v in params if k != 'api_key']
        new_query = urllib.parse.urlencode(new_params)
        parsed = parsed._replace(query=new_query)
        url = urllib.parse.urlunparse(parsed)

        headers['Authorization'] = f'Bearer {key}'

    return urllib.request.Request(url, headers=headers)

def _handle_metadata_error(e, context=""):
    import urllib.error
    import socket
    import json

    if isinstance(e, json.JSONDecodeError):
        raise MetadataProviderUnavailable(f"Ungueltige Provider-Antwort (JSON): {e}", status_code=503)

    if isinstance(e, urllib.error.HTTPError):
        if e.code in (401, 403):
            raise MetadataProviderUnavailable(f"API-Key ungueltig oder fehlend (HTTP {e.code})", status_code=502)
        elif e.code == 429 or e.code >= 500:
            raise MetadataProviderUnavailable(f"Provider temporaer nicht erreichbar (HTTP {e.code})", status_code=503)

    if isinstance(e, (urllib.error.URLError, socket.timeout)):
        raise MetadataProviderUnavailable(f"Netzwerk- oder Timeout-Fehler: {e}", status_code=503)

def get_tvdb_token():
    global tvdb_token, tvdb_token_time
    now = time.time()
    if tvdb_token and (now - tvdb_token_time < 12 * 3600):
        return tvdb_token
    try:
        url = "https://api4.thetvdb.com/v4/login"
        data = json.dumps({"apikey": TVDB_API_KEY}).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            res = json.loads(response.read().decode())
            tvdb_token = res.get('data', {}).get('token')
            tvdb_token_time = time.time()
            return tvdb_token
    except urllib.error.HTTPError as e:
        _handle_metadata_error(e)
        # fallback down to exception handling if not raised
    except urllib.error.URLError as e:
        _handle_metadata_error(e)
        # fallback

        print(f"[TVDB Login Error] Netzwerk/Timeout Fehler: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"[TVDB Login Error] Ungültige JSON Antwort: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[TVDB Login Error] Unerwarteter Fehler: {e}", file=sys.stderr)
        return None

def normalize_title(t):
    if not t:
        return ""
    t = t.lower()
    t = t.replace("&", "und")
    return re.sub(r'[^a-z0-9]', '', t)

def search_tvdb(query, lang="deu"):
    token = get_tvdb_token()
    if not token: return []
    url = f"https://api4.thetvdb.com/v4/search?query={urllib.parse.quote(query)}&type=series&language={lang}"
    try:
        req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}', 'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            results = []
            for item in data.get('data', [])[:25]:
                year = item.get('year', '????')
                title = item.get('name', '')
                trans = item.get('translations', {})
                if isinstance(trans, dict) and 'deu' in trans:
                    title = trans['deu']
                country = item.get('country', 'Unbekannt')
                results.append({
                    'id': str(item.get('tvdb_id')),
                    'name': f"{title} ({year}) [{country}]",
                    'provider': 'tvdb'
                })
            return results
    except urllib.error.HTTPError as e:
        _handle_metadata_error(e)
        # fallback down to exception handling if not raised
    except urllib.error.URLError as e:
        _handle_metadata_error(e)
        # fallback

        print(f"[TVDB Search Error] Netzwerk/Timeout Fehler bei '{query}': {e}", file=sys.stderr)
        return []
    except json.JSONDecodeError as e:
        _handle_metadata_error(e, context="[TVDB Search Error]")
        raise MetadataProviderUnavailable(f"Ungueltiges JSON: {e}", status_code=503)
    except Exception as e:
        _handle_metadata_error(e, context="[TVDB Search Error]")
        print(f"[TVDB Search Error] Unerwarteter Fehler: {e}", file=sys.stderr)
        return []

def fetch_tvdb(show_id, season, lang="deu"):
    token = get_tvdb_token()
    if not token: return {}
    result = {}
    page = 0
    is_all = (str(season).lower() == "all")
    while True:
        url = f"https://api4.thetvdb.com/v4/series/{show_id}/episodes/default/{lang}?page={page}"
        try:
            req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}', 'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                episodes = data.get('data', {}).get('episodes', [])
                if not episodes:
                    break
                for ep in episodes:
                    ep_season = ep.get('seasonNumber')
                    if ep_season is None or int(ep_season) <= 0:
                        continue

                    if is_all or str(ep_season) == str(season):
                        ep_num = str(ep.get('number'))
                        title = ep.get('name', '').replace('/', '-').replace(':', '').strip()
                        date_str = ep.get('aired', '')

                        abs_val = ep.get('absoluteNumber')
                        if is_all:
                            s_str = str(ep_season)
                            if len(s_str) < 2:
                                s_str = s_str.zfill(2)
                            e_str = str(ep_num)
                            if len(e_str) < 2:
                                e_str = e_str.zfill(2)
                            key = f"S{s_str}E{e_str}"
                            result[key] = {"title": title, "date": date_str, "absolute_number": abs_val}
                        else:
                            result[ep_num] = {"title": title, "date": date_str, "absolute_number": abs_val}
                links = data.get('links', {})
                if links.get('next') and links['next'] != links.get('self'):
                    page += 1
                else:
                    break
        except urllib.error.HTTPError as e:
            _handle_metadata_error(e)
            # fallback down to exception handling if not raised
        except urllib.error.URLError as e:
            _handle_metadata_error(e)
            # fallback

            print(f"[TVDB Fetch Error] Netzwerk/Timeout bei Staffel {season}: {e}", file=sys.stderr)
            break
        except json.JSONDecodeError as e:
            print(f"[TVDB Fetch Error] Ungültige JSON Antwort: {e}", file=sys.stderr)
            break
        except Exception as e:
            print(f"[TVDB Fetch Error] Unerwarteter Fehler: {e}", file=sys.stderr)
            break
    # EN-Fallback für Episoden ohne deutschen Titel
    if lang == "deu":
        missing = [k for k, v in result.items() if not v.get("title")]
        if missing:
            en_result = fetch_tvdb(show_id, season, lang="eng")
            for ep_num in missing:
                if ep_num in en_result and en_result[ep_num].get("title"):
                    result[ep_num]["title"] = en_result[ep_num]["title"]
    return result

def search_all_db(query):
    import re
    # Clean query using the new robust clean_search_query
    clean_query = clean_search_query(query)
    if not clean_query:
        clean_query = query.strip()

    errors = []

    def _do_search(q_str):
        results = []
        # 1. TMDb DE
        try:
            for r in search_tmdb_tv(q_str, "de-DE"):
                r['provider'] = 'tmdb_tv'
                results.append(r)
        except MetadataProviderUnavailable as e:
            errors.append(e)
        except Exception as e:
            errors.append(MetadataProviderUnavailable(f"TMDb DE Fehler: {e}"))

        # 2. TVDb DE
        try:
            results.extend(search_tvdb(q_str, "deu"))
        except MetadataProviderUnavailable as e:
            errors.append(e)
        except Exception as e:
            errors.append(MetadataProviderUnavailable(f"TVDb DE Fehler: {e}"))

        # 3. TVmaze
        try:
            for r in search_tvmaze(q_str):
                r['provider'] = 'tvmaze'
                results.append(r)
        except MetadataProviderUnavailable as e:
            errors.append(e)
        except Exception as e:
            errors.append(MetadataProviderUnavailable(f"TVmaze Fehler: {e}"))

        # 4. TMDb EN (Fallback)
        try:
            for r in search_tmdb_tv(q_str, "en-US"):
                r['provider'] = 'tmdb_tv_en'
                results.append(r)
        except MetadataProviderUnavailable as e:
            if not any(isinstance(err, MetadataProviderUnavailable) and str(err) == str(e) for err in errors):
                errors.append(e)
        except Exception as e:
            errors.append(MetadataProviderUnavailable(f"TMDb EN Fehler: {e}"))

        return results

    results = _do_search(clean_query)

    # Fallback für deutsche Umlaute (ae -> ä, oe -> ö, ue -> ü) da TMDB/TVDB sehr strikt suchen
    umlaut_query = clean_query
    umlaut_query = re.sub(r'ae', 'ä', umlaut_query, flags=re.IGNORECASE)
    umlaut_query = re.sub(r'oe', 'ö', umlaut_query, flags=re.IGNORECASE)
    umlaut_query = re.sub(r'ue', 'ü', umlaut_query, flags=re.IGNORECASE)
    if umlaut_query != clean_query:
        extra_results = _do_search(umlaut_query)
        seen_sigs = {f"{r['name'].split('[')[0].strip().lower()}_{r['provider']}" for r in results}
        for r in extra_results:
            sig = f"{r['name'].split('[')[0].strip().lower()}_{r['provider']}"
            if sig not in seen_sigs:
                results.append(r)

    final_results = []
    seen = set()
    for r in results:
        # Signatur für Deduplizierung: Titel + Jahr + PROVIDER
        sig = f"{r['name'].split('[')[0].strip().lower()}_{r['provider']}"
        if sig not in seen:
            seen.add(sig)
            # Anbieter im Anzeigenamen markieren
            r['name'] = f"{r['name']} [{r['provider'].upper()}]"
            final_results.append(r)

    # Sort results by match score with original query
    final_results.sort(key=lambda r: calculate_match_score(query, r['name']), reverse=True)

    if not final_results and errors:
        first_error = None
        for err in errors:
            if isinstance(err, MetadataProviderUnavailable):
                first_error = err
                break
        if not first_error:
            first_error = errors[0]
        raise first_error

    return final_results[:20]


def get_all_season_numbers(provider, show_id):
    seasons = []
    try:
        if provider in ["tmdb_tv", "tmdb_tv_en"]:
            url = f"https://api.themoviedb.org/3/tv/{show_id}?api_key={TMDB_API_KEY}"
            req = make_tmdb_request(url)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                seasons = [s['season_number'] for s in data.get('seasons', []) if s.get('season_number', 0) > 0]
        elif provider == "tvdb":
            token = get_tvdb_token()
            url = f"https://api4.thetvdb.com/v4/series/{show_id}/extended"
            req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}', 'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode()).get('data', {})
                seasons = [s['number'] for s in data.get('seasons', []) if s.get('type', {}).get('id') == 1 and s.get('number', 0) > 0]
        elif provider == "tvmaze":
            url = f"https://api.tvmaze.com/shows/{show_id}/seasons"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                seasons = [s['number'] for s in data if s.get('number', 0) > 0]
    except Exception as e:
        print(f"[get_all_season_numbers Error] {e}", file=sys.stderr)
    return sorted(list(set(seasons)))

def get_show_info(provider, show_id):
    try:
        seasons = get_all_season_numbers(provider, show_id)
        if seasons:
            seasons_str = [str(s) for s in seasons]
            info_str = f"Staffeln vorhanden: {', '.join(seasons_str)}"
            if len(seasons) > 20:
                info_str = f"Staffeln vorhanden: {seasons[0]} bis {seasons[-1]}"
            return info_str
    except Exception as e:
        print(f"[Show Info Error] Staffelstruktur für '{show_id}' ({provider}) nicht abrufbar: {e}", file=sys.stderr)
    return "Keine Info zur Staffelstruktur gefunden."

def search_tvmaze(query):
    # Automatische Fallbacks für eine tolerantere Suche
    queries_to_try = [query]

    # 1. Fallback: Entferne Länderkürzel (USA, UK)
    clean_query = re.sub(r'\b(USA|UK|AU|NZ)\b', '', query, flags=re.IGNORECASE).strip()
    if clean_query != query and clean_query:
        queries_to_try.append(clean_query)

    # 2. Fallback: Leerzeichen entfernen (z.B. "Master Chef" -> "MasterChef")
    no_space_query = clean_query.replace(' ', '')
    if no_space_query != clean_query and len(no_space_query) > 3:
        queries_to_try.append(no_space_query)

    # 3. Fallback: Nur die ersten zwei Wörter nehmen
    words = clean_query.split()
    if len(words) > 2:
        queries_to_try.append(f"{words[0]} {words[1]}")

    all_results = {}
    for q in queries_to_try:
        search_url = f"https://api.tvmaze.com/search/shows?q={urllib.parse.quote(q)}"
        try:
            req = urllib.request.Request(search_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                for item in data:
                    show = item['show']
                    if show['id'] not in all_results:
                        year = show.get('premiered', '')[:4] if show.get('premiered') else '?'

                        # Land ermitteln (aus Network oder WebChannel)
                        network = show.get('network') or show.get('webChannel') or {}
                        country = network.get('country') or {}
                        country_name = country.get('name') or 'Unbekannt'

                        all_results[show['id']] = {
                            'id': show['id'],
                            'name': f"{show['name']} ({year}) [{country_name}]"
                        }
        except Exception as e:
            print(f"[TVMaze Search Error] Suchvariante '{q}' fehlgeschlagen: {e}", file=sys.stderr)
            continue

    return list(all_results.values())[:8]

def fetch_tvmaze(show_id, season):
    is_all = (str(season).lower() == "all")
    episodes_url = f"https://api.tvmaze.com/shows/{show_id}/episodes"
    try:
        req = urllib.request.Request(episodes_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            episodes_data = json.loads(response.read().decode())

        result = {}
        for ep in episodes_data:
            ep_season = ep.get('season')
            if ep_season is None or int(ep_season) <= 0:
                continue

            if is_all or str(ep_season) == str(season):
                ep_num = str(ep.get('number'))
                if ep_num and ep_num != 'None':
                    title = ep.get('name', '').replace('/', '-').replace(':', '')
                    date_str = ep.get('airdate', '')
                    if is_all:
                        s_str = str(ep_season).zfill(2)
                        e_str = str(ep_num).zfill(2)
                        key = f"S{s_str}E{e_str}"
                        result[key] = {"title": title, "date": date_str}
                    else:
                        result[ep_num] = {"title": title, "date": date_str}
        return result
    except Exception as e:
        print(f"[TVMaze Fetch Error] Episoden für Show {show_id}, Staffel {season} nicht abrufbar: {e}", file=sys.stderr)
        return {}

def get_fernsehserien_episodes(series_name_or_url, season):
    if series_name_or_url.startswith('http'):
        url = series_name_or_url
    else:
        url_name = series_name_or_url.lower().replace(' ', '-').replace('.', '').replace(':', '')
        url = f"https://www.fernsehserien.de/{url_name}/episodenguide/staffel-{season}"

    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
        })
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8')

        result = {}
        for match in re.finditer(r'<td class="episodenliste-episodennummer">.*?(\d+).*?</td>.*?<span itemprop="name">(.*?)</span>', html, re.IGNORECASE | re.DOTALL):
            ep_num = match.group(1).strip()
            title = match.group(2).strip().replace('/', '-').replace(':', '')
            result[ep_num] = title

        return result
    except Exception as e:
        print(f"[Fernsehserien Error] Episodenliste für '{series_name_or_url}', Staffel {season} nicht abrufbar: {e}", file=sys.stderr)
        return {}



def search_tmdb_movie(query):
    query = query.strip()
    # Direkte ID-Suche (IMDB oder TMDB)
    if query.startswith("tt"):
        url = f"https://api.themoviedb.org/3/find/{query}?api_key={TMDB_API_KEY}&external_source=imdb_id&language=de-DE"
        try:
            req = make_tmdb_request(url)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                results = []
                for item in data.get('movie_results', []):
                    year = item.get('release_date', '')[:4] if item.get('release_date') else '????'
                    title = item.get('title', '')
                    results.append({'id': item['id'], 'name': f"{title} ({year})", 'genre_ids': item.get('genre_ids', [])})
                if results: return results
        except urllib.error.HTTPError as e:
            _handle_metadata_error(e)
            # fallback down to exception handling if not raised
        except urllib.error.URLError as e:
            _handle_metadata_error(e)
            # fallback

            print(f"[TMDb Movie Error] Netzwerk/Timeout bei ID-Suche: {e}", file=sys.stderr)
        except Exception as e:
            print(f"[TMDb Movie Error] Unerwarteter Fehler bei ID-Suche: {e}", file=sys.stderr)
    elif query.isdigit() or query.startswith("tmdb:"):
        tmdb_id = query.replace("tmdb:", "")
        url = f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={TMDB_API_KEY}&language=de-DE"
        try:
            req = make_tmdb_request(url)
            with urllib.request.urlopen(req, timeout=10) as response:
                item = json.loads(response.read().decode())
                year = item.get('release_date', '')[:4] if item.get('release_date') else '????'
                title = item.get('title', '')
                gids = [g.get('id') for g in item.get('genres', [])] if 'genres' in item else item.get('genre_ids', [])
                return [{'id': item['id'], 'name': f"{title} ({year})", 'genre_ids': gids}]
        except urllib.error.HTTPError as e:
            _handle_metadata_error(e)
            # fallback down to exception handling if not raised
        except urllib.error.URLError as e:
            _handle_metadata_error(e)
            # fallback

            print(f"[TMDb Movie Error] Netzwerk/Timeout bei TMDB-ID-Suche: {e}", file=sys.stderr)
        except Exception as e:
            print(f"[TMDb Movie Error] Unerwarteter Fehler bei TMDB-ID-Suche: {e}", file=sys.stderr)

    # Normale Textsuche
    clean_query = clean_search_query(query)

    def _do_tmdb_search(q_str):
        url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={urllib.parse.quote(q_str)}&language=de-DE"
        try:
            req = make_tmdb_request(url)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                results = []
                for item in data.get('results', [])[:8]:
                    year = item.get('release_date', '')[:4] if item.get('release_date') else '????'
                    title = item.get('title', '')
                    results.append({
                        'id': item['id'],
                        'name': f"{title} ({year})",
                        'genre_ids': item.get('genre_ids', [])
                    })
                return results
        except Exception as e:
            _handle_metadata_error(e, context="[TMDb Movie Error]")
            raise MetadataProviderUnavailable(f"Unerwarteter Provider-Fehler: {e}", status_code=503)

    results = _do_tmdb_search(clean_query)

    # Fallback für deutsche Umlaute (ae -> ä, oe -> ö, ue -> ü) da TMDB sehr strikt sucht
    umlaut_query = clean_query
    umlaut_query = re.sub(r'ae', 'ä', umlaut_query, flags=re.IGNORECASE)
    umlaut_query = re.sub(r'oe', 'ö', umlaut_query, flags=re.IGNORECASE)
    umlaut_query = re.sub(r'ue', 'ü', umlaut_query, flags=re.IGNORECASE)
    if umlaut_query != clean_query:
        extra_results = _do_tmdb_search(umlaut_query)
        seen_ids = {r['id'] for r in results}
        for r in extra_results:
            if r['id'] not in seen_ids:
                results.append(r)

    return results

def search_tmdb_tv(query, lang="de-DE"):
    query = query.strip()
    # Direkte ID-Suche (IMDB oder TMDB)
    if query.startswith("tt"):
        url = f"https://api.themoviedb.org/3/find/{query}?api_key={TMDB_API_KEY}&external_source=imdb_id&language={lang}"
        try:
            req = make_tmdb_request(url)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                results = []
                for item in data.get('tv_results', []):
                    year = item.get('first_air_date', '')[:4] if item.get('first_air_date') else '????'
                    title = item.get('name', '')
                    country = item.get('origin_country', [''])[0] if item.get('origin_country') else 'Unbekannt'
                    results.append({'id': item['id'], 'name': f"{title} ({year}) [{country}]", 'genre_ids': item.get('genre_ids', [])})
                if results: return results
        except urllib.error.HTTPError as e:
            _handle_metadata_error(e)
            # fallback down to exception handling if not raised
        except urllib.error.URLError as e:
            _handle_metadata_error(e)
            # fallback

            print(f"[TMDb TV Error] Netzwerk/Timeout bei ID-Suche: {e}", file=sys.stderr)
        except Exception as e:
            print(f"[TMDb TV Error] Unerwarteter Fehler bei ID-Suche: {e}", file=sys.stderr)
    elif query.isdigit() or query.startswith("tmdb:"):
        tmdb_id = query.replace("tmdb:", "")
        url = f"https://api.themoviedb.org/3/tv/{tmdb_id}?api_key={TMDB_API_KEY}&language={lang}"
        try:
            req = make_tmdb_request(url)
            with urllib.request.urlopen(req, timeout=10) as response:
                item = json.loads(response.read().decode())
                year = item.get('first_air_date', '')[:4] if item.get('first_air_date') else '????'
                title = item.get('name', '')
                country = item.get('origin_country', [''])[0] if item.get('origin_country') else 'Unbekannt'
                gids = [g.get('id') for g in item.get('genres', [])] if 'genres' in item else item.get('genre_ids', [])
                return [{'id': item['id'], 'name': f"{title} ({year}) [{country}]", 'genre_ids': gids}]
        except urllib.error.HTTPError as e:
            _handle_metadata_error(e)
            # fallback down to exception handling if not raised
        except urllib.error.URLError as e:
            _handle_metadata_error(e)
            # fallback

            print(f"[TMDb TV Error] Netzwerk/Timeout bei TMDB-ID-Suche: {e}", file=sys.stderr)
        except Exception as e:
            print(f"[TMDb TV Error] Unerwarteter Fehler bei TMDB-ID-Suche: {e}", file=sys.stderr)

    # Normale Textsuche
    url = f"https://api.themoviedb.org/3/search/tv?api_key={TMDB_API_KEY}&query={urllib.parse.quote(query)}&language={lang}"
    try:
        req = make_tmdb_request(url)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            results = []
            for item in data.get('results', [])[:8]:
                year = item.get('first_air_date', '')[:4] if item.get('first_air_date') else '????'
                title = item.get('name', '')
                country = item.get('origin_country', [''])[0] if item.get('origin_country') else 'Unbekannt'
                results.append({
                    'id': item['id'],
                    'name': f"{title} ({year}) [{country}]",
                    'genre_ids': item.get('genre_ids', [])
                })
            return results
    except urllib.error.HTTPError as e:
        _handle_metadata_error(e)
        # fallback down to exception handling if not raised
    except urllib.error.URLError as e:
        _handle_metadata_error(e)
        # fallback

        print(f"[TMDb TV Error] Netzwerk/Timeout bei Textsuche '{query}': {e}", file=sys.stderr)
        return []
    except json.JSONDecodeError as e:
        print(f"[TMDb TV Error] Ungültige JSON Antwort: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"[TMDb TV Error] Unerwarteter Fehler bei Textsuche: {e}", file=sys.stderr)
        return []

def fetch_tmdb_tv(show_id, season, lang="de-DE"):
    is_all = (str(season).lower() == "all")
    if is_all:
        result = {}
        provider = "tmdb_tv_en" if lang == "en-US" else "tmdb_tv"
        seasons = get_all_season_numbers(provider, show_id)
        for s_num in seasons:
            s_eps = fetch_tmdb_tv(show_id, s_num, lang)
            for ep_num, ep_data in s_eps.items():
                s_str = str(s_num).zfill(2)
                e_str = str(ep_num).zfill(2)
                key = f"S{s_str}E{e_str}"
                result[key] = ep_data
        return result

    url = f"https://api.themoviedb.org/3/tv/{show_id}/season/{season}?api_key={TMDB_API_KEY}&language={lang}"
    try:
        req = make_tmdb_request(url)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            result = {}
            for ep in data.get('episodes', []):
                ep_num = str(ep['episode_number'])
                title = ep.get('name', '').replace('/', '-').replace(':', '')
                date_str = ep.get('air_date', '')
                result[ep_num] = {"title": title, "date": date_str}
            return result
    except Exception as e:
        print(f"[TMDB TV Fetch Error] Episoden für Show {show_id}, Staffel {season} nicht abrufbar: {e}", file=sys.stderr)
        return {}

def match_episode(filename, json_str):
    try:
        episodes = json.loads(json_str)
        best_match = ""
        best_score = 0.0

        import re
        def get_words(text):
            # Filtere Füllwörter aus
            text = text.lower()
            text = text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
            words = set(re.findall(r'\w+', text))
            return {w for w in words if w not in ['der', 'die', 'das', 'in', 'im', 'teil', 'part', 'von', 'und']}

        file_words = get_words(filename)

        for ep_num, ep_data in episodes.items():
            if isinstance(ep_data, dict):
                title = ep_data.get('title', '')
                date_str = ep_data.get('date', '')
            else:
                title = str(ep_data)
                date_str = ""

            if date_str:
                parts = date_str.split('-')
                if len(parts) == 3:
                    y, m, d = parts
                    # Prüfe gängige Datumsformate im Dateinamen
                    if f"{d}.{m}.{y}" in filename or f"{d}{m}{y}" in filename or f"{y}-{m}-{d}" in filename or f"{y}{m}{d}" in filename:
                        return ep_num

            title_words = get_words(title)
            if not title_words: continue

            overlap = len(title_words.intersection(file_words))
            score = overlap / len(title_words)

            if score > best_score:
                best_score = score
                best_match = ep_num

        if best_score >= 0.5:
            return best_match
    except Exception as e:
        print(f"[Episode Match Error] Episoden-Matching für '{filename}' fehlgeschlagen: {e}", file=sys.stderr)
    return ""


def search_ofdb(query):
    clean_query = clean_search_query(query)

    def _do_ofdb_search(q_str):
        url = "https://www.ofdb.de/suchergebnis/"
        data = urllib.parse.urlencode({'QSinput': q_str}).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"[OFDb Search Error] Suche nach '{q_str}' fehlgeschlagen: {e}", file=sys.stderr)
            return []

        results = []
        matches = re.finditer(r'<a[^>]*href=\"https://www.ofdb.de/film/(\d+),([^\"]*)\"[^>]*>.*?<span class=\"tooltipster\"[^>]*>(.*?)</span></a>.*?</td>\s*<td>(\d{4})</td>', html, re.DOTALL | re.IGNORECASE)
        for m in matches:
            ofdb_id = m.group(1)
            url_part = m.group(2)
            title_raw = m.group(3)
            title = re.sub(r'^">', '', title_raw).strip()
            year = m.group(4)
            results.append({
                "id": f"ofdb_{ofdb_id}_{url_part}",
                "title": title,
                "year": year
            })
        return results

    results = _do_ofdb_search(clean_query)

    # Fallback für deutsche Umlaute (ae -> ä, oe -> ö, ue -> ü)
    umlaut_query = clean_query
    umlaut_query = re.sub(r'ae', 'ä', umlaut_query, flags=re.IGNORECASE)
    umlaut_query = re.sub(r'oe', 'ö', umlaut_query, flags=re.IGNORECASE)
    umlaut_query = re.sub(r'ue', 'ü', umlaut_query, flags=re.IGNORECASE)
    if umlaut_query != clean_query:
        extra_results = _do_ofdb_search(umlaut_query)
        seen_ids = {r['id'] for r in results}
        for r in extra_results:
            if r['id'] not in seen_ids:
                results.append(r)

    return results

def generate_ofdb_nfo(ofdb_full_id, target_folder, filename_base, fallback_json=None):
    parts = ofdb_full_id.split('_', 2)
    if len(parts) != 3: return {}
    ofdb_id = parts[1]
    url_part = parts[2]

    url = f"https://www.ofdb.de/film/{ofdb_id},{url_part}/"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"[OFDb NFO Error] Filmseite für OFDb-ID {ofdb_id} nicht abrufbar: {e}", file=sys.stderr)
        return {}

    title_m = re.search(r'<title>OFDb - (.*?) \(\d{4}\)</title>', html)
    title = title_m.group(1) if title_m else filename_base

    year_m = re.search(r'Erscheinungsjahr:.*?<a[^>]*>(\d{4})</a>', html, re.DOTALL)
    year = year_m.group(1) if year_m else ""

    plot_m = re.search(r'<div class=\"plot\">(.*?)</div>', html, re.DOTALL)
    plot = plot_m.group(1).strip() if plot_m else ""
    plot = re.sub(r'<[^>]+>', '', plot)

    actors = []
    for m in re.finditer(r'<a[^>]*href=\"https://www.ofdb.de/person/[^>]*>(.*?)</a>', html):
        actor_name = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        if actor_name and actor_name not in actors:
            actors.append(actor_name)

    xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<movie>\n  <lockdata>true</lockdata>\n'
    xml += f"  <title>{escape_xml(title)}</title>\n"
    xml += f"  <plot>{escape_xml(plot)}</plot>\n"
    xml += f"  <year>{escape_xml(year)}</year>\n"

    for a in actors[:15]:
        xml += "  <actor>\n"
        xml += f"    <name>{escape_xml(a)}</name>\n"
        xml += "  </actor>\n"
    xml += "</movie>\n"

    nfo_path = os.path.join(target_folder, f"{filename_base}.nfo")
    with open(nfo_path, 'w', encoding='utf-8') as f:
        f.write(xml)
        log_message(f"[NFO] {nfo_path}: created (provider='ofdb')")

    return {"nfo": True, "poster": False, "fanart": False, "msg": "OFDb NFO erstellt"}

def fetch_tmdb_images(media_type, tmdb_id):
    """
    media_type: 'movie' or 'tv'
    tmdb_id: the ID of the movie or show
    returns: dict containing 'poster', 'backdrop', 'logo' (all German preferred, fallback to neutral/English)
    """
    if not TMDB_API_KEY:
        return {}
    url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}/images?api_key={TMDB_API_KEY}&include_image_language=de,en,null"
    try:
        req = make_tmdb_request(url)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())

            def find_best_image(items):
                if not items:
                    return None
                for item in items:
                    if item.get('iso_639_1') == 'de':
                        return item.get('file_path')
                for item in items:
                    if not item.get('iso_639_1'):
                        return item.get('file_path')
                for item in items:
                    if item.get('iso_639_1') == 'en':
                        return item.get('file_path')
                return items[0].get('file_path')

            poster_path = find_best_image(data.get('posters', []))
            backdrop_path = find_best_image(data.get('backdrops', []))
            logo_path = find_best_image(data.get('logos', []))

            res = {}
            if poster_path:
                res['poster'] = f"https://image.tmdb.org/t/p/original{poster_path}"
            if backdrop_path:
                res['backdrop'] = f"https://image.tmdb.org/t/p/original{backdrop_path}"
            if logo_path:
                res['logo'] = f"https://image.tmdb.org/t/p/original{logo_path}"
            return res
    except Exception as e:
        print(f"[TMDB Images Error] Failed to fetch images for {media_type}/{tmdb_id}: {e}")
        return {}


def generate_movie_nfo(tmdb_id, folder_path, filename_base, fallback_json=None, nfo_overrides=None, overwrite=False):

    import os
    nfo_path = os.path.join(folder_path, f"{filename_base}.nfo")

    settings = load_settings()
    server_type = settings.get("media_server", "emby")
    validator = artwork_validators.get_validator(server_type)

    poster_filename = validator.get_preferred_movie_poster_name(f"{filename_base}.mkv")
    fanart_filename = validator.get_preferred_movie_backdrop_name(f"{filename_base}.mkv")
    logo_filename = validator.get_preferred_movie_logo_name(f"{filename_base}.mkv")
    banner_filename = validator.get_preferred_movie_banner_name(f"{filename_base}.mkv")

    poster_path = os.path.join(folder_path, poster_filename)
    fanart_path = os.path.join(folder_path, fanart_filename)
    logo_path = os.path.join(folder_path, logo_filename)
    banner_path = os.path.join(folder_path, banner_filename)

    def has_movie_poster():
        for ext in (".jpg", ".png", ".webp"):
            if os.path.exists(os.path.join(folder_path, f"poster{ext}")): return True
            if os.path.exists(os.path.join(folder_path, f"folder{ext}")): return True
            if os.path.exists(os.path.join(folder_path, f"cover{ext}")): return True
            if os.path.exists(os.path.join(folder_path, f"{filename_base}-poster{ext}")): return True
        return False

    def has_movie_fanart():
        for ext in (".jpg", ".png", ".webp"):
            if os.path.exists(os.path.join(folder_path, f"fanart{ext}")): return True
            if os.path.exists(os.path.join(folder_path, f"backdrop{ext}")): return True
            if os.path.exists(os.path.join(folder_path, f"background{ext}")): return True
            if os.path.exists(os.path.join(folder_path, f"{filename_base}-fanart{ext}")): return True
            if os.path.exists(os.path.join(folder_path, f"{filename_base}-backdrop{ext}")): return True
        return False

    needs_nfo = overwrite or not os.path.exists(nfo_path)
    if not needs_nfo and not overwrite:
        log_message(f"[NFO] {nfo_path}: skipped (already exists)")
    needs_poster = not has_movie_poster()
    needs_fanart = not has_movie_fanart()
    needs_logo = validator.supports_logos and not any(os.path.exists(os.path.join(folder_path, f"logo{ext}")) or os.path.exists(os.path.join(folder_path, f"clearlogo{ext}")) or os.path.exists(os.path.join(folder_path, f"{filename_base}-logo{ext}")) for ext in (".jpg", ".png", ".webp"))
    needs_banner = validator.supports_banners and not any(os.path.exists(os.path.join(folder_path, f"banner{ext}")) or os.path.exists(os.path.join(folder_path, f"{filename_base}-banner{ext}")) for ext in (".jpg", ".png", ".webp"))

    if isinstance(tmdb_id, str) and tmdb_id.startswith("url_mediathek:"):
        if needs_nfo:
            title = tmdb_id.split("url_mediathek:", 1)[1]
            plot = ""
            year = ""
            if nfo_overrides:
                if nfo_overrides.get("title"): title = nfo_overrides["title"]
                if nfo_overrides.get("plot"): plot = nfo_overrides["plot"]
                if nfo_overrides.get("year"): year = nfo_overrides["year"]

            xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            xml += '<movie>\n  <lockdata>true</lockdata>\n'
            xml += f"  <title>{escape_xml(title)}</title>\n"
            if plot:
                xml += f"  <plot>{escape_xml(plot)}</plot>\n"
            if year:
                xml += f"  <year>{escape_xml(year)}</year>\n"
            xml += "  <mw_provider>mediathek</mw_provider>\n"
            xml += '</movie>\n'
            with open(nfo_path, 'w', encoding='utf-8') as f:
                f.write(xml)
                log_message(f"[NFO] {nfo_path}: created (provider='mediathek')")
        return {"nfo": needs_nfo, "poster": False, "fanart": False, "msg": "Mediathek Film NFO erstellt"}

    if tmdb_id == "manual" or (isinstance(tmdb_id, str) and tmdb_id.startswith("{")):
        if needs_nfo:
            try:
                meta = json.loads(tmdb_id) if isinstance(tmdb_id, str) else tmdb_id
            except Exception as e:
                print(f"[Movie NFO Error] Manuelle Metadaten unlesbar, nutze Fallback '{filename_base}': {e}", file=sys.stderr)
                meta = {"title": filename_base, "year": "", "plot": ""}
            title = meta.get("title", filename_base)
            year = meta.get("year", "")
            plot = meta.get("plot", "")
            if nfo_overrides:
                if nfo_overrides.get("title"): title = nfo_overrides["title"]
                if nfo_overrides.get("plot"): plot = nfo_overrides["plot"]
                if nfo_overrides.get("year"): year = nfo_overrides["year"]

            xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            xml += '<movie>\n  <lockdata>true</lockdata>\n'
            xml += f"  <title>{escape_xml(title)}</title>\n"
            if plot:
                xml += f"  <plot>{escape_xml(plot)}</plot>\n"
            if year:
                xml += f"  <year>{escape_xml(year)}</year>\n"
            xml += "  <mw_provider>manual</mw_provider>\n"
            xml += '</movie>\n'
            with open(nfo_path, 'w', encoding='utf-8') as f:
                f.write(xml)
                log_message(f"[NFO] {nfo_path}: created (provider='manual')")
        return {"nfo": needs_nfo, "poster": False, "fanart": False, "msg": "Manuelle Film NFO erstellt"}

    if isinstance(tmdb_id, str) and (tmdb_id.startswith("http://") or tmdb_id.startswith("https://")):
        downloaded_poster = False
        if needs_nfo or needs_poster:
            entries = fetch_ytdlp_url_metadata(tmdb_id)
            title = filename_base
            plot = ""
            year = ""
            studio = ""
            thumbnail_url = None
            if not isinstance(entries, dict) and len(entries) > 0:
                entry = entries[0]
                title = entry.get("title", filename_base)
                plot = entry.get("description", "")
                studio = entry.get("uploader", "")
                thumbnail_url = entry.get("thumbnail")
                if entry.get("upload_date"):
                    year = entry.get("upload_date")[:4]
                elif entry.get("release_year"):
                    year = str(entry.get("release_year"))

            if nfo_overrides:
                if nfo_overrides.get("title"): title = nfo_overrides["title"]
                if nfo_overrides.get("plot"): plot = nfo_overrides["plot"]
                if nfo_overrides.get("year"): year = nfo_overrides["year"]

            if needs_nfo:
                xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                xml += '<movie>\n  <lockdata>true</lockdata>\n'
                xml += f"  <title>{escape_xml(title)}</title>\n"
                if plot:
                    xml += f"  <plot>{escape_xml(plot)}</plot>\n"
                if year:
                    xml += f"  <year>{escape_xml(year)}</year>\n"
                if studio:
                    xml += f"  <studio>{escape_xml(studio)}</studio>\n"
                xml += "  <mw_provider>ytdlp</mw_provider>\n"
                xml += '</movie>\n'
                with open(nfo_path, 'w', encoding='utf-8') as f:
                    f.write(xml)
                    log_message(f"[NFO] {nfo_path}: created (provider='ytdlp')")

            if thumbnail_url and needs_poster:
                try:
                    _download_with_timeout(thumbnail_url, poster_path)
                    downloaded_poster = True
                except Exception as e:
                    print(f"[ytdlp poster error] {e}")

        return {"nfo": needs_nfo, "poster": downloaded_poster, "fanart": False, "msg": "ytdlp movie NFO erstellt"}

    if not (needs_nfo or needs_poster or needs_fanart):
        return {"nfo": False, "poster": False, "fanart": False, "msg": "existiert"}

    url = f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={TMDB_API_KEY}&language=de-DE&append_to_response=credits,release_dates"
    try:
        req = make_tmdb_request(url)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
    except Exception as e:
        return {"error": str(e)}

    if needs_nfo:
        yt_data = {}
        if fallback_json and os.path.exists(fallback_json):
            try:
                with open(fallback_json, 'r', encoding='utf-8') as f:
                    yt_data = json.load(f)
            except Exception as e: print(f"Warning: Ignored exception {e}")

        fsk = ""
        for r in data.get('release_dates', {}).get('results', []):
            if r.get('iso_3166_1') == 'DE':
                for rd in r.get('release_dates', []):
                    if rd.get('certification'):
                        fsk = rd.get('certification')
                        break
                break

        year = data.get('release_date', '')[:4] if data.get('release_date') else ''
        if not year and yt_data.get('upload_date'):
            year = yt_data.get('upload_date')[:4]

        plot = data.get('overview', '')
        if yt_data.get('description') and len(yt_data.get('description', '')) > len(plot):
            plot = f"{plot}\n\n--- YouTube Info ---\n{yt_data['description']}".strip()

        studio = yt_data.get('uploader', '')
        title = data.get('title', '')

        if nfo_overrides:
            if nfo_overrides.get("title"): title = nfo_overrides["title"]
            if nfo_overrides.get("plot"): plot = nfo_overrides["plot"]
            if nfo_overrides.get("year"): year = nfo_overrides["year"]

        xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        xml += '<movie>\n  <lockdata>true</lockdata>\n'
        xml += f"  <title>{escape_xml(title)}</title>\n"
        xml += f"  <originaltitle>{escape_xml(data.get('original_title', ''))}</originaltitle>\n"
        xml += f"  <plot>{escape_xml(plot)}</plot>\n"
        if fsk:
            xml += f"  <mpaa>FSK {fsk}</mpaa>\n"
        for pc in data.get('production_companies', []):
            if pc.get('name'):
                xml += f"  <studio>{escape_xml(pc.get('name'))}</studio>\n"
        xml += f"  <year>{escape_xml(year)}</year>\n"
        if data.get('release_date'):
            xml += f"  <premiered>{escape_xml(data.get('release_date', ''))}</premiered>\n"
        xml += f"  <rating>{data.get('vote_average', 0)}</rating>\n"
        if studio:
            xml += f"  <studio>{escape_xml(studio)}</studio>\n"
        xml += f"  <tmdbid>{tmdb_id}</tmdbid>\n"

        for g in data.get('genres', []):
            xml += f"  <genre>{escape_xml(g.get('name', ''))}</genre>\n"

        for c in data.get('credits', {}).get('cast', [])[:15]:
            xml += "  <actor>\n"
            xml += f"    <name>{escape_xml(c.get('name', ''))}</name>\n"
            xml += f"    <role>{escape_xml(c.get('character', ''))}</role>\n"
            if c.get('profile_path'):
                xml += f"    <thumb>https://image.tmdb.org/t/p/w500{c.get('profile_path')}</thumb>\n"
            xml += "  </actor>\n"

        xml += '</movie>\n'

        with open(nfo_path, 'w', encoding='utf-8') as f:
            f.write(xml)
            log_message(f"[NFO] {nfo_path}: created (provider='tmdb')")

    # Download images using TMDB Images API for German-localized/higher-quality art
    if (needs_poster or needs_fanart or needs_logo or needs_banner) and str(tmdb_id).isdigit():
        images = fetch_tmdb_images("movie", tmdb_id)

        if needs_poster and images.get('poster'):
            try:
                ext = get_ext_from_url(images['poster'], ".jpg")
                p_path = os.path.join(folder_path, f"poster{ext}")
                _download_with_timeout(images['poster'], p_path)
                needs_poster = False
            except Exception:
                pass

        if needs_fanart and images.get('backdrop'):
            try:
                ext = get_ext_from_url(images['backdrop'], ".jpg")
                pref_name = validator.get_preferred_movie_backdrop_name(f"{filename_base}.mkv")
                pref_base, _ = os.path.splitext(pref_name)
                f_path = os.path.join(folder_path, f"{pref_base}{ext}")
                _download_with_timeout(images['backdrop'], f_path)
                needs_fanart = False
            except Exception:
                pass

        if needs_logo and images.get('logo'):
            try:
                ext = get_ext_from_url(images['logo'], ".png")
                l_path = os.path.join(folder_path, f"logo{ext}")
                _download_with_timeout(images['logo'], l_path)
                needs_logo = False
            except Exception:
                pass

    # Fallback to main API response if images endpoint didn't provide URLs or for missing items
    if needs_poster and data.get('poster_path'):
        try:
            p_url = f"https://image.tmdb.org/t/p/original{data['poster_path']}"
            ext = get_ext_from_url(p_url, ".jpg")
            p_path = os.path.join(folder_path, f"poster{ext}")
            _download_with_timeout(p_url, p_path)
            needs_poster = False
        except Exception as e:
            print(f"[Artwork Error] Fallback-Poster-Download für Film '{filename_base}' fehlgeschlagen: {e}", file=sys.stderr)

    if needs_fanart and data.get('backdrop_path'):
        try:
            b_url = f"https://image.tmdb.org/t/p/original{data['backdrop_path']}"
            ext = get_ext_from_url(b_url, ".jpg")
            pref_name = validator.get_preferred_movie_backdrop_name(f"{filename_base}.mkv")
            pref_base, _ = os.path.splitext(pref_name)
            f_path = os.path.join(folder_path, f"{pref_base}{ext}")
            _download_with_timeout(b_url, f_path)
            needs_fanart = False
        except Exception as e:
            print(f"[Artwork Error] Fallback-Fanart-Download für Film '{filename_base}' fehlgeschlagen: {e}", file=sys.stderr)

    return {"nfo": needs_nfo, "poster": not needs_poster, "fanart": not needs_fanart, "logo": not needs_logo, "banner": not needs_banner}

def fetch_show_nfo_data(provider, show_id):
    from gui.core.nfo_mutation import normalize_fsk

    if provider == "manual":
        try:
            meta = json.loads(show_id) if isinstance(show_id, str) else show_id
        except Exception as e:
            print(f"[Show NFO Error] Manuelle Serien-Metadaten unlesbar, nutze Fallback: {e}", file=sys.stderr)
            meta = {"title": show_id or "Manuelle Serie", "plot": "", "year": ""}
        return {
            "title": meta.get("title", "Manuelle Serie"),
            "plot": meta.get("plot", ""),
            "year": meta.get("year", ""),
            "fsk": normalize_fsk(meta.get("fsk", "")).replace("FSK ", ""),
            "genres": meta.get("genres", []),
        }
    elif provider == "mediathek":
        return {
            "title": show_id or "",
            "plot": "",
            "year": "",
            "fsk": "",
            "genres": [],
        }
    elif provider == "ytdlp":
        try:
            entries = fetch_ytdlp_url_metadata(show_id)
            title = "YouTube/Mediathek Serie"
            plot = ""
            if not isinstance(entries, dict) and len(entries) > 0:
                title = entries[0].get("playlist_title") or entries[0].get("playlist") or entries[0].get("title") or "YouTube/Mediathek Serie"
                plot = entries[0].get("description") or ""
            return {"title": title, "plot": plot, "year": "", "fsk": "", "genres": []}
        except Exception as e:
            print(f"[Show NFO Error] yt-dlp-Metadaten für '{show_id}' nicht abrufbar: {e}", file=sys.stderr)
            return {"title": "YouTube/Mediathek Serie", "plot": "", "year": "", "fsk": "", "genres": []}
    elif provider == "tvdb":
        try:
            token = get_tvdb_token()
            url = f"https://api4.thetvdb.com/v4/series/{show_id}/extended?meta=translations"
            req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}', 'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode()).get('data', {})
            title = data.get('name', '')
            plot = data.get('overview', '')
            trans = data.get('translations', {})
            if isinstance(trans, dict):
                for t in trans.get('nameTranslations', []):
                    if t.get('language') == 'deu':
                        title = t.get('name', title)
                        break
                for t in trans.get('overviewTranslations', []):
                    if t.get('language') == 'deu':
                        plot = t.get('overview', plot)
                        break
            year = data.get('firstAired', '')[:4] if data.get('firstAired') else ''
            fsk = ""
            for rating in data.get("contentRatings", []):
                if rating.get("country") == "deu":
                    fsk = normalize_fsk(rating.get("name", "")).replace("FSK ", "")
                    break
            genres = [genre.get("name", "") for genre in data.get("genres", []) if genre.get("name")]
            return {"title": title, "plot": plot, "year": year, "fsk": fsk, "genres": genres}
        except Exception as e:
            return {
                "title": "", "plot": "", "year": "", "fsk": "", "genres": [],
                "error": f"TVDB-Metadaten konnten nicht geladen werden: {e}",
            }
    elif provider in ["tmdb_tv", "tmdb_tv_en"]:
        try:
            lang = "en-US" if provider == "tmdb_tv_en" else "de-DE"
            url = f"https://api.themoviedb.org/3/tv/{show_id}?api_key={TMDB_API_KEY}&language={lang}&append_to_response=content_ratings"
            req = make_tmdb_request(url)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
            title = data.get('name', '')
            plot = data.get('overview', '')
            year = data.get('first_air_date', '')[:4] if data.get('first_air_date') else ''
            fsk = ""
            for rating in data.get("content_ratings", {}).get("results", []):
                if rating.get("iso_3166_1") == "DE":
                    fsk = normalize_fsk(rating.get("rating", "")).replace("FSK ", "")
                    break
            genres = [genre.get("name", "") for genre in data.get("genres", []) if genre.get("name")]
            return {"title": title, "plot": plot, "year": year, "fsk": fsk, "genres": genres}
        except Exception as e:
            return {
                "title": "", "plot": "", "year": "", "fsk": "", "genres": [],
                "error": f"TMDB-Serienmetadaten konnten nicht geladen werden: {e}",
            }
    return {"title": "", "plot": "", "year": "", "fsk": "", "genres": []}

def fetch_movie_nfo_data(provider, movie_id):
    from gui.core.nfo_mutation import normalize_fsk

    if provider == "manual" or (isinstance(movie_id, str) and movie_id.startswith("{")):
        try:
            meta = json.loads(movie_id) if isinstance(movie_id, str) else movie_id
        except Exception as e:
            print(f"[Movie NFO Error] Manuelle Film-Metadaten unlesbar, nutze Fallback: {e}", file=sys.stderr)
            meta = {"title": "Manueller Film", "year": "", "plot": ""}
        return {
            "title": meta.get("title", ""),
            "plot": meta.get("plot", ""),
            "year": meta.get("year", ""),
            "fsk": normalize_fsk(meta.get("fsk", "")).replace("FSK ", ""),
            "genres": meta.get("genres", []),
        }
    elif provider == "mediathek" or (isinstance(movie_id, str) and movie_id.startswith("url_mediathek:")):
        title = movie_id
        if isinstance(title, str) and title.startswith("url_mediathek:"):
            title = title.split("url_mediathek:", 1)[1]
        plot = ""
        year = ""
        try:
            eps = fetch_mediathek_episodes(movie_id)
            if eps and "1" in eps:
                first_item = eps["1"]
                title = first_item.get("title", title)
                plot = first_item.get("plot", "")
                date_str = first_item.get("date", "")
                if date_str and len(date_str) >= 4:
                    year = date_str[:4]
        except Exception as e:
            print(f"[fetch_movie_nfo_data mediathek error] {e}")
        return {"title": title, "plot": plot, "year": year, "fsk": "", "genres": []}
    elif isinstance(movie_id, str) and (movie_id.startswith("http://") or movie_id.startswith("https://")):
        try:
            entries = fetch_ytdlp_url_metadata(movie_id)
            title = "YouTube Video"
            plot = ""
            year = ""
            if not isinstance(entries, dict) and len(entries) > 0:
                entry = entries[0]
                title = entry.get("title", "YouTube Video")
                plot = entry.get("description", "")
                if entry.get("upload_date"):
                    year = entry.get("upload_date")[:4]
                elif entry.get("release_year"):
                    year = str(entry.get("release_year"))
            return {"title": title, "plot": plot, "year": year, "fsk": "", "genres": []}
        except Exception as e:
            print(f"[Movie NFO Error] yt-dlp-Metadaten für '{movie_id}' nicht abrufbar: {e}", file=sys.stderr)
            return {"title": "", "plot": "", "year": "", "fsk": "", "genres": []}
    else: # TMDB
        try:
            url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}&language=de-DE&append_to_response=release_dates"
            req = make_tmdb_request(url)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
            title = data.get('title', '')
            plot = data.get('overview', '')
            year = data.get('release_date', '')[:4] if data.get('release_date') else ''
            fsk = ""
            for country in data.get("release_dates", {}).get("results", []):
                if country.get("iso_3166_1") == "DE":
                    for release in country.get("release_dates", []):
                        fsk = normalize_fsk(release.get("certification", "")).replace("FSK ", "")
                        if fsk:
                            break
                if fsk:
                    break
            genres = [genre.get("name", "") for genre in data.get("genres", []) if genre.get("name")]
            return {"title": title, "plot": plot, "year": year, "fsk": fsk, "genres": genres}
        except Exception as e:
            return {
                "title": "", "plot": "", "year": "", "fsk": "", "genres": [],
                "error": f"TMDB-Filmmetadaten konnten nicht geladen werden: {e}",
            }

def fetch_episode_nfo_data(provider, show_id, season, episode):
    if provider == "manual":
        ep_title = f"Folge {episode}"
        ep_plot = ""
        if isinstance(episode, dict):
            ep_title = episode.get("title", "")
            ep_plot = episode.get("plot", "")
        return {"title": ep_title, "plot": ep_plot, "aired": ""}
    elif provider == "mediathek":
        try:
            eps = fetch_mediathek_episodes(show_id)
            ep_data = eps.get(str(episode), {})
            return {
                "title": ep_data.get("title", f"Folge {episode}"),
                "plot": ep_data.get("plot", ""),
                "aired": ""
            }
        except Exception as e:
            print(f"[Episode NFO Error] Mediathek-Episode S{season}E{episode} für '{show_id}' nicht abrufbar: {e}", file=sys.stderr)
            return {"title": f"Folge {episode}", "plot": "", "aired": ""}
    elif provider == "ytdlp":
        try:
            entries = fetch_ytdlp_url_metadata(show_id)
            ep_title = f"Folge {episode}"
            ep_plot = ""
            aired = ""
            if not isinstance(entries, dict) and len(entries) > 0:
                matched_entry = None
                if len(entries) == 1:
                    matched_entry = entries[0]
                else:
                    for i, ent in enumerate(entries):
                        idx = ent.get("playlist_index") or ent.get("playlist_autonumber") or (i + 1)
                        if str(idx) == str(episode):
                            matched_entry = ent
                            break
                if matched_entry:
                    title = matched_entry.get("title", "")
                    alt_title = matched_entry.get("alt_title", "")
                    show_name = matched_entry.get("playlist_title") or matched_entry.get("playlist", "")
                    if alt_title and normalize_title(title) == normalize_title(show_name):
                        ep_title = alt_title
                    elif alt_title and not title:
                        ep_title = alt_title
                    else:
                        ep_title = title or f"Folge {episode}"
                    ep_plot = matched_entry.get("description", "")
                    if matched_entry.get("upload_date") and len(matched_entry.get("upload_date")) == 8:
                        d = matched_entry.get("upload_date")
                        aired = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
            return {"title": ep_title, "plot": ep_plot, "aired": aired}
        except Exception as e:
            print(f"[Episode NFO Error] yt-dlp-Episode {episode} für '{show_id}' nicht abrufbar: {e}", file=sys.stderr)
            return {"title": f"Folge {episode}", "plot": "", "aired": ""}
    elif provider == "tvdb":
        try:
            token = get_tvdb_token()
            import tempfile
            cache_file = os.path.join(tempfile.gettempdir(), f"tvdb_{show_id}_deu.json")

            def _tvdb_load_episodes(sid, lang_code, cache_path):
                eps = []
                if os.path.exists(cache_path):
                    try:
                        with open(cache_path, 'r', encoding='utf-8') as f:
                            eps = json.load(f)
                    except Exception as e: print(f"Warning: Ignored exception {e}")
                if not eps:
                    pg = 0
                    while True:
                        url = f"https://api4.thetvdb.com/v4/series/{sid}/episodes/default/{lang_code}?page={pg}"
                        try:
                            req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}', 'User-Agent': 'Mozilla/5.0'})
                            with urllib.request.urlopen(req, timeout=10) as response:
                                d = json.loads(response.read().decode())
                                batch = d.get('data', {}).get('episodes', [])
                                if not batch: break
                                eps.extend(batch)
                                lnk = d.get('links', {})
                                if lnk.get('next') and lnk['next'] != lnk.get('self'):
                                    pg += 1
                                else:
                                    break
                        except Exception as e:
                            print(f"[TVDB Fetch Error] Episodenliste ({lang_code}) für Serie {sid}, Seite {pg} abgebrochen: {e}", file=sys.stderr)
                            break
                    if eps:
                        try:
                            with open(cache_path, 'w', encoding='utf-8') as f:
                                json.dump(eps, f)
                        except Exception as e: print(f"Warning: Ignored exception {e}")
                return eps

            all_episodes = _tvdb_load_episodes(show_id, "deu", cache_file)
            ep_data = {}
            for ep in all_episodes:
                if str(ep.get('seasonNumber')) == str(season) and str(ep.get('number')) == str(episode):
                    ep_data = ep
                    break

            ep_title = ep_data.get('name', '').strip() if ep_data else ""
            ep_plot  = ep_data.get('overview', '').strip() if ep_data else ""
            aired = ep_data.get('aired', '') if ep_data else ""

            if not ep_title or not ep_plot:
                cache_file_en = os.path.join(tempfile.gettempdir(), f"tvdb_{show_id}_eng.json")
                all_episodes_en = _tvdb_load_episodes(show_id, "eng", cache_file_en)
                for ep_en in all_episodes_en:
                    if str(ep_en.get('seasonNumber')) == str(season) and str(ep_en.get('number')) == str(episode):
                        if not ep_title:
                            ep_title = ep_en.get('name', '').strip()
                        if not ep_plot:
                            ep_plot = ep_en.get('overview', '').strip()
                        if not aired:
                            aired = ep_en.get('aired', '')
                        break

            return {
                "title": ep_title or f"Folge {episode}",
                "plot": ep_plot,
                "aired": aired
            }
        except Exception as e:
            return {"title": f"Folge {episode}", "plot": f"Fehler: {e}", "aired": ""}
    elif provider in ["tmdb_tv", "tmdb_tv_en"]:
        try:
            lang = "en-US" if provider == "tmdb_tv_en" else "de-DE"
            url = f"https://api.themoviedb.org/3/tv/{show_id}/season/{season}/episode/{episode}?api_key={TMDB_API_KEY}&language={lang}"
            req = make_tmdb_request(url)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
            return {
                "title": data.get('name', f"Folge {episode}"),
                "plot": data.get('overview', ''),
                "aired": data.get('air_date', '')
            }
        except Exception as e:
            return {"title": f"Folge {episode}", "plot": f"Fehler: {e}", "aired": ""}
    return {"title": f"Folge {episode}", "plot": "", "aired": ""}

def generate_tvshow_nfo(provider, show_id, target_folder, nfo_overrides=None, source_url=None, resolved_topic=None, overwrite=False):
    import os

    def build_mw_data_xml(provider, show_id, title=None, source_url=None, resolved_topic=None):
        import time
        from xml.sax.saxutils import escape
        
        if provider == "manual":
            has_url = source_url and source_url.strip() and not source_url.strip().startswith("{")
            has_topic = resolved_topic and resolved_topic.strip()
            is_id_json = show_id and (show_id.strip().startswith("{") or show_id.strip().startswith("["))
            if not has_url and not has_topic and (not show_id or is_id_json):
                return ""

        final_source_url = source_url
        final_resolved_topic = resolved_topic
        final_show_id = show_id

        if not final_source_url:
            if provider == "ytdlp":
                final_source_url = show_id
            elif provider == "mediathek" and show_id and show_id.startswith("http"):
                final_source_url = show_id
                
        if not final_resolved_topic:
            if provider == "mediathek" and show_id:
                if show_id.startswith("url_mediathek:"):
                    final_resolved_topic = show_id.split("url_mediathek:", 1)[1]
                else:
                    final_resolved_topic = show_id
            elif provider == "ytdlp":
                final_resolved_topic = title or "YouTube/Mediathek Serie"

        if provider == "manual" and final_show_id:
            if final_show_id.strip().startswith("{") or final_show_id.strip().startswith("["):
                final_show_id = None

        mw_xml = "  <mw_data>\n"
        mw_xml += f"    <provider>{escape(provider)}</provider>\n"
        if final_show_id:
            mw_xml += f"    <show_id>{escape(str(final_show_id))}</show_id>\n"
        if final_source_url:
            mw_xml += f"    <source_url>{escape(final_source_url)}</source_url>\n"
        if final_resolved_topic:
            mw_xml += f"    <resolved_topic>{escape(final_resolved_topic)}</resolved_topic>\n"
        mw_xml += f"    <last_sync>{time.strftime('%Y-%m-%dT%H:%M:%S')}</last_sync>\n"
        mw_xml += "  </mw_data>\n"
        return mw_xml

    if provider == "manual":
        try:
            meta = json.loads(show_id) if isinstance(show_id, str) else show_id
        except Exception as e:
            print(f"[Show NFO Error] Manuelle Serien-Metadaten unlesbar, nutze Fallback: {e}", file=sys.stderr)
            meta = {"title": show_id or "Manuelle Serie", "plot": "", "year": ""}

        nfo_path = os.path.join(target_folder, "tvshow.nfo")
        if not overwrite and os.path.exists(nfo_path):
            return {"nfo": False, "poster": False, "fanart": False, "msg": "tvshow.nfo existiert bereits"}
        title = meta.get("title", "Manuelle Serie")
        plot = meta.get("plot", "")
        year = meta.get("year", "")
        if nfo_overrides:
            if nfo_overrides.get("title"): title = nfo_overrides["title"]
            if nfo_overrides.get("plot"): plot = nfo_overrides["plot"]
            if nfo_overrides.get("year"): year = nfo_overrides["year"]

        xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        xml += '<tvshow>\n  <lockdata>true</lockdata>\n'
        xml += f"  <title>{escape_xml(title)}</title>\n"
        if plot:
            xml += f"  <plot>{escape_xml(plot)}</plot>\n"
        if year:
            xml += f"  <year>{escape_xml(year)}</year>\n"
        xml += "  <mw_provider>manual</mw_provider>\n"
        xml += build_mw_data_xml("manual", show_id, title=title, source_url=source_url, resolved_topic=resolved_topic)
        xml += '</tvshow>\n'
        with open(nfo_path, 'w', encoding='utf-8') as f:
            f.write(xml)
            log_message(f"[NFO] {nfo_path}: created (provider={provider})")
        return {"nfo": True, "poster": False, "fanart": False, "msg": "Manuelle tvshow.nfo erstellt"}

    if provider == "mediathek":
        nfo_path = os.path.join(target_folder, "tvshow.nfo")
        if not overwrite and os.path.exists(nfo_path):
            return {"nfo": False, "poster": False, "fanart": False, "msg": "tvshow.nfo existiert bereits"}
        title = show_id
        plot = ""
        year = ""
        if nfo_overrides:
            if nfo_overrides.get("title"): title = nfo_overrides["title"]
            if nfo_overrides.get("plot"): plot = nfo_overrides["plot"]
            if nfo_overrides.get("year"): year = nfo_overrides["year"]

        xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        xml += '<tvshow>\n  <lockdata>true</lockdata>\n'
        xml += f"  <title>{escape_xml(title)}</title>\n"
        if plot:
            xml += f"  <plot>{escape_xml(plot)}</plot>\n"
        if year:
            xml += f"  <year>{escape_xml(year)}</year>\n"
        xml += f"  <mw_provider>mediathek</mw_provider>\n"
        xml += f"  <mw_showid>{escape_xml(show_id)}</mw_showid>\n"
        xml += build_mw_data_xml("mediathek", show_id, title=title, source_url=source_url, resolved_topic=resolved_topic)
        xml += '</tvshow>\n'
        with open(nfo_path, 'w', encoding='utf-8') as f:
            f.write(xml)
            log_message(f"[NFO] {nfo_path}: created (provider={provider})")
        return {"nfo": True, "poster": False, "fanart": False, "msg": "Mediathek tvshow.nfo erstellt"}

    if provider == "ytdlp":
        nfo_path = os.path.join(target_folder, "tvshow.nfo")
        if not overwrite and os.path.exists(nfo_path):
            return {"nfo": False, "poster": False, "fanart": False, "msg": "tvshow.nfo existiert bereits"}
        entries = fetch_ytdlp_url_metadata(show_id)
        title = "YouTube/Mediathek Serie"
        plot = ""
        year = ""
        if not isinstance(entries, dict) and len(entries) > 0:
            title = entries[0].get("playlist_title") or entries[0].get("playlist") or entries[0].get("title") or "YouTube/Mediathek Serie"
            plot = entries[0].get("description") or ""
        if nfo_overrides:
            if nfo_overrides.get("title"): title = nfo_overrides["title"]
            if nfo_overrides.get("plot"): plot = nfo_overrides["plot"]
            if nfo_overrides.get("year"): year = nfo_overrides["year"]

        xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        xml += '<tvshow>\n  <lockdata>true</lockdata>\n'
        xml += f"  <title>{escape_xml(title)}</title>\n"
        if plot:
            xml += f"  <plot>{escape_xml(plot)}</plot>\n"
        if year:
            xml += f"  <year>{year}</year>\n"
        xml += "  <mw_provider>ytdlp</mw_provider>\n"
        xml += f"  <mw_showid>{escape_xml(show_id)}</mw_showid>\n"
        xml += build_mw_data_xml("ytdlp", show_id, title=title, source_url=source_url, resolved_topic=resolved_topic)
        xml += '</tvshow>\n'
        with open(nfo_path, 'w', encoding='utf-8') as f:
            f.write(xml)
            log_message(f"[NFO] {nfo_path}: created (provider={provider})")
        return {"nfo": True, "poster": False, "fanart": False, "msg": "ytdlp tvshow.nfo erstellt"}

    if provider not in ["tmdb_tv", "tmdb_tv_en", "tvdb"]:
        return {"nfo": False, "poster": False, "fanart": False, "msg": f"Skipped for {provider}"}

    nfo_path = os.path.join(target_folder, "tvshow.nfo")

    settings = load_settings()
    server_type = settings.get("media_server", "emby")
    validator = artwork_validators.get_validator(server_type)

    poster_filename = validator.get_preferred_series_poster_name()
    fanart_filename = validator.get_preferred_series_backdrop_name()
    logo_filename = validator.get_preferred_series_logo_name()
    banner_filename = validator.get_preferred_series_banner_name()

    poster_path = os.path.join(target_folder, poster_filename)
    fanart_path = os.path.join(target_folder, fanart_filename)
    logo_path = os.path.join(target_folder, logo_filename)
    banner_path = os.path.join(target_folder, banner_filename)

    needs_nfo = overwrite or not os.path.exists(nfo_path)
    if not needs_nfo and not overwrite:
        log_message(f"[NFO] {nfo_path}: skipped (already exists)")
    needs_poster = not validator.has_artwork_file(target_folder, validator.get_series_poster_names())
    needs_fanart = not validator.has_artwork_file(target_folder, validator.get_series_backdrop_names())
    needs_logo = validator.supports_logos and not validator.has_artwork_file(target_folder, validator.get_series_logo_names())
    needs_banner = validator.supports_banners and not validator.has_artwork_file(target_folder, validator.get_series_banner_names())

    if not (needs_nfo or needs_poster or needs_fanart or needs_logo or needs_banner):
        return {"nfo": False, "poster": False, "fanart": False, "logo": False, "banner": False, "msg": "existiert"}

    if provider == "tvdb":
        token = get_tvdb_token()
        url = f"https://api4.thetvdb.com/v4/series/{show_id}/extended?meta=translations"
        try:
            req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}', 'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode()).get('data', {})
        except Exception as e:
            return {"error": str(e)}

        if needs_nfo:
            title = data.get('name', '')
            original_title = title
            plot = data.get('overview', '')
            trans = data.get('translations', {})
            if isinstance(trans, dict):
                for t in trans.get('nameTranslations', []):
                    if t.get('language') == 'deu':
                        title = t.get('name', title)
                        break
                for t in trans.get('overviewTranslations', []):
                    if t.get('language') == 'deu':
                        plot = t.get('overview', plot)
                        break

            fsk = ""
            for cr in data.get('contentRatings', []):
                if cr.get('country') == 'deu':
                    fsk = cr.get('name', '').replace('+', '')
                    break

            year = data.get('firstAired', '')[:4] if data.get('firstAired') else ''

            if nfo_overrides:
                if nfo_overrides.get("title"): title = nfo_overrides["title"]
                if nfo_overrides.get("plot"): plot = nfo_overrides["plot"]
                if nfo_overrides.get("year"): year = nfo_overrides["year"]

            xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            xml += '<tvshow>\n  <lockdata>true</lockdata>\n'
            xml += f"  <title>{escape_xml(title)}</title>\n"
            xml += f"  <originaltitle>{escape_xml(original_title)}</originaltitle>\n"
            xml += f"  <plot>{escape_xml(plot)}</plot>\n"
            xml += f"  <year>{escape_xml(year)}</year>\n"
            xml += f"  <premiered>{escape_xml(data.get('firstAired', ''))}</premiered>\n"
            xml += f"  <rating>{data.get('score', 0)}</rating>\n"
            status = data.get('status', {}).get('name') if isinstance(data.get('status'), dict) else ''
            if status:
                xml += f"  <status>{escape_xml(status)}</status>\n"
            if fsk:
                xml += f"  <mpaa>FSK {fsk}</mpaa>\n"
            for comp in data.get('companies', []):
                if comp.get('name'):
                    xml += f"  <studio>{escape_xml(comp.get('name'))}</studio>\n"
            xml += f"  <tvdbid>{escape_xml(str(show_id))}</tvdbid>\n"
            xml += f"  <mw_provider>{provider}</mw_provider>\n"
            xml += f"  <mw_showid>{escape_xml(str(show_id))}</mw_showid>\n"
            xml += build_mw_data_xml(provider, show_id, title=title, source_url=source_url, resolved_topic=resolved_topic)
            for g in data.get('genres', []):
                xml += f"  <genre>{escape_xml(g.get('name', ''))}</genre>\n"
            for c in data.get('characters', [])[:15]:
                xml += "  <actor>\n"
                xml += f"    <name>{escape_xml(c.get('personName', ''))}</name>\n"
                xml += f"    <role>{escape_xml(c.get('name', ''))}</role>\n"
                if c.get('image'):
                    xml += f"    <thumb>{c.get('image')}</thumb>\n"
                xml += "  </actor>\n"
            xml += '</tvshow>\n'
            with open(nfo_path, 'w', encoding='utf-8') as f:
                f.write(xml)
                log_message(f"[NFO] {nfo_path}: created (provider={provider})")

        if needs_poster or needs_fanart or needs_logo or needs_banner:
            artworks = data.get('artworks', [])

            def find_best_tvdb_art(art_type):
                candidates = [a for a in artworks if a.get('type') == art_type]
                if not candidates:
                    return None
                for a in candidates:
                    if a.get('language') == 'deu':
                        return a.get('image')
                for a in candidates:
                    if not a.get('language'):
                        return a.get('image')
                for a in candidates:
                    if a.get('language') == 'eng':
                        return a.get('image')
                return candidates[0].get('image')

            if needs_poster:
                p_url = find_best_tvdb_art(2)
                if p_url:
                    try:
                        _download_with_timeout(p_url, poster_path)
                        needs_poster = False
                    except Exception as e:
                        print(f"Warning: TVDB poster download failed: {e}")

            if needs_fanart:
                f_url = find_best_tvdb_art(3)
                if f_url:
                    try:
                        _download_with_timeout(f_url, fanart_path)
                        needs_fanart = False
                    except Exception as e:
                        print(f"Warning: TVDB fanart download failed: {e}")

            if needs_logo:
                l_url = find_best_tvdb_art(23)
                if l_url:
                    try:
                        _download_with_timeout(l_url, logo_path)
                        needs_logo = False
                    except Exception as e:
                        print(f"Warning: TVDB logo download failed: {e}")

            if needs_banner:
                b_url = find_best_tvdb_art(1)
                if b_url:
                    try:
                        _download_with_timeout(b_url, banner_path)
                        needs_banner = False
                    except Exception as e:
                        print(f"Warning: TVDB banner download failed: {e}")

        return {"nfo": needs_nfo, "poster": not needs_poster, "fanart": not needs_fanart, "logo": not needs_logo, "banner": not needs_banner}

    lang = "en-US" if provider == "tmdb_tv_en" else "de-DE"
    url = f"https://api.themoviedb.org/3/tv/{show_id}?api_key={TMDB_API_KEY}&language={lang}&append_to_response=credits,content_ratings"
    try:
        req = make_tmdb_request(url)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
    except Exception as e:
        return {"error": str(e)}

    if needs_nfo:
        fsk = ""
        for r in data.get('content_ratings', {}).get('results', []):
            if r.get('iso_3166_1') == 'DE':
                fsk = r.get('rating')
                break

        year = data.get('first_air_date', '')[:4] if data.get('first_air_date') else ''
        plot = data.get('overview', '')

        if nfo_overrides:
            if nfo_overrides.get("title"): data['name'] = nfo_overrides["title"]
            if nfo_overrides.get("plot"): plot = nfo_overrides["plot"]
            if nfo_overrides.get("year"): year = nfo_overrides["year"]

        xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        xml += '<tvshow>\n  <lockdata>true</lockdata>\n'
        xml += f"  <title>{escape_xml(data.get('name', ''))}</title>\n"
        xml += f"  <originaltitle>{escape_xml(data.get('original_name', ''))}</originaltitle>\n"
        xml += f"  <plot>{escape_xml(plot)}</plot>\n"
        xml += f"  <year>{escape_xml(year)}</year>\n"
        xml += f"  <premiered>{escape_xml(data.get('first_air_date', ''))}</premiered>\n"
        xml += f"  <rating>{data.get('vote_average', 0)}</rating>\n"
        if data.get('status'):
            xml += f"  <status>{escape_xml(data.get('status'))}</status>\n"
        if fsk:
            xml += f"  <mpaa>FSK {fsk}</mpaa>\n"
        for net in data.get('networks', []):
            if net.get('name'):
                xml += f"  <studio>{escape_xml(net.get('name'))}</studio>\n"
        xml += f"  <tmdbid>{escape_xml(str(show_id))}</tmdbid>\n"
        xml += f"  <mw_provider>{provider}</mw_provider>\n"
        xml += f"  <mw_showid>{escape_xml(str(show_id))}</mw_showid>\n"
        xml += build_mw_data_xml(provider, show_id, title=data.get('name', ''), source_url=source_url, resolved_topic=resolved_topic)
        for g in data.get('genres', []):
            xml += f"  <genre>{escape_xml(g.get('name', ''))}</genre>\n"
        for c in data.get('credits', {}).get('cast', [])[:15]:
            xml += "  <actor>\n"
            xml += f"    <name>{escape_xml(c.get('name', ''))}</name>\n"
            xml += f"    <role>{escape_xml(c.get('character', ''))}</role>\n"
            if c.get('profile_path'):
                xml += f"    <thumb>https://image.tmdb.org/t/p/w500{c.get('profile_path')}</thumb>\n"
            xml += "  </actor>\n"
        xml += '</tvshow>\n'
        with open(nfo_path, 'w', encoding='utf-8') as f:
            f.write(xml)
            log_message(f"[NFO] {nfo_path}: created (provider={provider})")

    if (needs_poster or needs_fanart or needs_logo or needs_banner) and str(show_id).isdigit():
        images = fetch_tmdb_images("tv", show_id)

        if needs_poster and images.get('poster'):
            try:
                _download_with_timeout(images['poster'], poster_path)
                needs_poster = False
            except Exception as e:
                print(f"[Artwork Error] Poster-Download für Serie {show_id} fehlgeschlagen: {e}", file=sys.stderr)

        if needs_fanart and images.get('backdrop'):
            try:
                _download_with_timeout(images['backdrop'], fanart_path)
                needs_fanart = False
            except Exception as e:
                print(f"[Artwork Error] Fanart-Download für Serie {show_id} fehlgeschlagen: {e}", file=sys.stderr)

        if needs_logo and images.get('logo'):
            try:
                _download_with_timeout(images['logo'], logo_path)
                needs_logo = False
            except Exception as e:
                print(f"[Artwork Error] Logo-Download für Serie {show_id} fehlgeschlagen: {e}", file=sys.stderr)

    if needs_poster and data.get('poster_path'):
        try:
            p_url = f"https://image.tmdb.org/t/p/original{data['poster_path']}"
            _download_with_timeout(p_url, poster_path)
            needs_poster = False
        except Exception as e:
            print(f"[Artwork Error] Fallback-Poster-Download für Serie {show_id} fehlgeschlagen: {e}", file=sys.stderr)
    if needs_fanart and data.get('backdrop_path'):
        try:
            b_url = f"https://image.tmdb.org/t/p/original{data['backdrop_path']}"
            _download_with_timeout(b_url, fanart_path)
            needs_fanart = False
        except Exception as e:
            print(f"[Artwork Error] Fallback-Fanart-Download für Serie {show_id} fehlgeschlagen: {e}", file=sys.stderr)

    return {"nfo": needs_nfo, "poster": not needs_poster, "fanart": not needs_fanart, "logo": not needs_logo, "banner": not needs_banner}

def generate_episode_nfo(provider, show_id, season, episode, target_folder, filename_base, force_season=None, force_episode=None, nfo_overrides=None, overwrite=False):
    import os
    nfo_path = os.path.join(target_folder, f"{filename_base}.nfo")
    thumb_path = os.path.join(target_folder, f"{filename_base}-thumb.jpg")

    needs_nfo = overwrite or not os.path.exists(nfo_path)
    if not needs_nfo and not overwrite:
        log_message(f"[NFO] {nfo_path}: skipped (already exists)")
    needs_thumb = not os.path.exists(thumb_path)

    nfo_season = force_season if force_season is not None else season
    nfo_episode = force_episode if force_episode is not None else episode

    if provider == "manual":
        ep_title = ""
        ep_num = episode
        ep_plot = ""
        ep_aired = ""
        if isinstance(episode, dict):
            ep_title = episode.get("title", "")
            ep_num = episode.get("episode", 1)
            ep_plot = episode.get("plot", "")

        if force_episode is not None:
            ep_num = force_episode

        if nfo_overrides:
            if nfo_overrides.get("title"): ep_title = nfo_overrides["title"]
            if nfo_overrides.get("plot"): ep_plot = nfo_overrides["plot"]
            if nfo_overrides.get("aired"): ep_aired = nfo_overrides["aired"]

        if needs_nfo:
            xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            xml += '<episodedetails>\n  <lockdata>true</lockdata>\n'
            xml += f"  <title>{escape_xml(ep_title)}</title>\n"
            xml += f"  <season>{nfo_season}</season>\n"
            xml += f"  <episode>{ep_num}</episode>\n"
            if ep_plot:
                xml += f"  <plot>{escape_xml(ep_plot)}</plot>\n"
            if ep_aired:
                xml += f"  <aired>{ep_aired}</aired>\n"
            xml += '</episodedetails>\n'
            with open(nfo_path, 'w', encoding='utf-8') as f:
                f.write(xml)
                log_message(f"[NFO] {nfo_path}: created (provider={provider})")
        return {"nfo": needs_nfo, "thumb": False}

    if provider == "mediathek":
        if needs_nfo:
            eps = fetch_mediathek_episodes(show_id)
            ep_data = eps.get(str(episode), {})
            ep_title = ep_data.get("title", f"Folge {episode}")
            ep_plot = ep_data.get("plot", "")
            ep_aired = ""
            if nfo_overrides:
                if nfo_overrides.get("title"): ep_title = nfo_overrides["title"]
                if nfo_overrides.get("plot"): ep_plot = nfo_overrides["plot"]
                if nfo_overrides.get("aired"): ep_aired = nfo_overrides["aired"]

            xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            xml += '<episodedetails>\n  <lockdata>true</lockdata>\n'
            xml += f"  <title>{escape_xml(ep_title)}</title>\n"
            xml += f"  <season>{nfo_season}</season>\n"
            xml += f"  <episode>{nfo_episode}</episode>\n"
            if ep_plot:
                xml += f"  <plot>{escape_xml(ep_plot)}</plot>\n"
            if ep_aired:
                xml += f"  <aired>{ep_aired}</aired>\n"
            xml += '</episodedetails>\n'
            with open(nfo_path, 'w', encoding='utf-8') as f:
                f.write(xml)
                log_message(f"[NFO] {nfo_path}: created (provider={provider})")
        return {"nfo": needs_nfo, "thumb": False}

    if provider == "ytdlp":
        downloaded_thumb = False
        if needs_nfo or needs_thumb:
            entries = fetch_ytdlp_url_metadata(show_id)
            ep_title = f"Folge {episode}"
            ep_plot = ""
            ep_aired = ""
            thumbnail_url = None
            if not isinstance(entries, dict) and len(entries) > 0:
                matched_entry = None
                if len(entries) == 1:
                    matched_entry = entries[0]
                else:
                    for i, ent in enumerate(entries):
                        idx = ent.get("playlist_index") or ent.get("playlist_autonumber") or (i + 1)
                        if str(idx) == str(episode):
                            matched_entry = ent
                            break
                if matched_entry:
                    title = matched_entry.get("title", "")
                    alt_title = matched_entry.get("alt_title", "")
                    show_name = matched_entry.get("playlist_title") or matched_entry.get("playlist", "")
                    thumbnail_url = matched_entry.get("thumbnail")
                    if alt_title and normalize_title(title) == normalize_title(show_name):
                        ep_title = alt_title
                    elif alt_title and not title:
                        ep_title = alt_title
                    else:
                        ep_title = title or f"Folge {episode}"
                    ep_plot = matched_entry.get("description", "")
                    if matched_entry.get("upload_date") and len(matched_entry.get("upload_date")) == 8:
                        d = matched_entry.get("upload_date")
                        ep_aired = f"{d[:4]}-{d[4:6]}-{d[6:8]}"

            if nfo_overrides:
                if nfo_overrides.get("title"): ep_title = nfo_overrides["title"]
                if nfo_overrides.get("plot"): ep_plot = nfo_overrides["plot"]
                if nfo_overrides.get("aired"): ep_aired = nfo_overrides["aired"]

            if needs_nfo:
                xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                xml += '<episodedetails>\n  <lockdata>true</lockdata>\n'
                xml += f"  <title>{escape_xml(ep_title)}</title>\n"
                xml += f"  <season>{nfo_season}</season>\n"
                xml += f"  <episode>{nfo_episode}</episode>\n"
                if ep_plot:
                    xml += f"  <plot>{escape_xml(ep_plot)}</plot>\n"
                if ep_aired:
                    xml += f"  <aired>{ep_aired}</aired>\n"
                xml += '</episodedetails>\n'
                with open(nfo_path, 'w', encoding='utf-8') as f:
                    f.write(xml)
                    log_message(f"[NFO] {nfo_path}: created (provider={provider})")

            if thumbnail_url and needs_thumb:
                try:
                    _download_with_timeout(thumbnail_url, thumb_path)
                    downloaded_thumb = True
                except Exception as e:
                    print(f"[ytdlp episode thumb error] {e}")

        return {"nfo": needs_nfo, "thumb": downloaded_thumb}

    if not (needs_nfo or needs_thumb):
        return {"nfo": False, "thumb": False, "msg": "existiert"}

    if provider == "tvdb":
        token = get_tvdb_token()
        ep_data = {}

        # Caching logic
        import tempfile
        cache_file = os.path.join(tempfile.gettempdir(), f"tvdb_{show_id}_deu.json")
        all_episodes = []

        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    all_episodes = json.load(f)
            except Exception as e: print(f"Warning: Ignored exception {e}")

        def _tvdb_load_episodes(sid, lang_code, cache_path):
            eps = []
            if os.path.exists(cache_path):
                try:
                    with open(cache_path, 'r', encoding='utf-8') as f:
                        eps = json.load(f)
                except Exception as e: print(f"Warning: Ignored exception {e}")
            if not eps:
                pg = 0
                while True:
                    url = f"https://api4.thetvdb.com/v4/series/{sid}/episodes/default/{lang_code}?page={pg}"
                    try:
                        req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}', 'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(req, timeout=10) as response:
                            d = json.loads(response.read().decode())
                            batch = d.get('data', {}).get('episodes', [])
                            if not batch: break
                            eps.extend(batch)
                            lnk = d.get('links', {})
                            if lnk.get('next') and lnk['next'] != lnk.get('self'):
                                pg += 1
                            else:
                                break
                    except Exception as e:
                        print(f"[TVDB Fetch Error] Episodenliste ({lang_code}) für Serie {sid}, Seite {pg} abgebrochen: {e}", file=sys.stderr)
                        break
                if eps:
                    try:
                        with open(cache_path, 'w', encoding='utf-8') as f:
                            json.dump(eps, f)
                    except Exception as e: print(f"Warning: Ignored exception {e}")
            return eps

        all_episodes = _tvdb_load_episodes(show_id, "deu", cache_file)

        for ep in all_episodes:
            if str(ep.get('seasonNumber')) == str(season) and str(ep.get('number')) == str(episode):
                ep_data = ep
                break

        if not ep_data:
            if needs_nfo:
                try:
                    ep_title = f"Folge {nfo_episode}"
                    ep_plot = "Automatischer Fallback: Episode online bei TVDB nicht gefunden."
                    ep_aired = ""
                    if nfo_overrides:
                        if nfo_overrides.get("title"): ep_title = nfo_overrides["title"]
                        if nfo_overrides.get("plot"): ep_plot = nfo_overrides["plot"]
                        if nfo_overrides.get("aired"): ep_aired = nfo_overrides["aired"]

                    xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                    xml += '<episodedetails>\n  <lockdata>true</lockdata>\n'
                    xml += f"  <title>{escape_xml(ep_title)}</title>\n"
                    xml += f"  <season>{nfo_season}</season>\n"
                    xml += f"  <episode>{nfo_episode}</episode>\n"
                    xml += f"  <plot>{escape_xml(ep_plot)}</plot>\n"
                    if ep_aired:
                        xml += f"  <aired>{ep_aired}</aired>\n"
                    xml += '</episodedetails>\n'
                    with open(nfo_path, 'w', encoding='utf-8') as f:
                        f.write(xml)
                        log_message(f"[NFO] {nfo_path}: created (provider={provider})")
                    return {"nfo": True, "thumb": False, "msg": "Episode online bei TVDB nicht gefunden (lokaler Fallback generiert)"}
                except Exception as write_err:
                    return {"nfo": False, "thumb": False, "msg": f"Episode online bei TVDB nicht gefunden, Schreibfehler: {write_err}"}
            return {"nfo": False, "thumb": False, "msg": "Episode nicht gefunden"}

        ep_title = ep_data.get('name', '').strip()
        ep_plot  = ep_data.get('overview', '').strip()
        ep_aired = ep_data.get('aired', '')

        # EN-Fallback wenn Titel oder Plot fehlt
        if not ep_title or not ep_plot:
            cache_file_en = os.path.join(tempfile.gettempdir(), f"tvdb_{show_id}_eng.json")
            all_episodes_en = _tvdb_load_episodes(show_id, "eng", cache_file_en)
            for ep_en in all_episodes_en:
                if str(ep_en.get('seasonNumber')) == str(season) and str(ep_en.get('number')) == str(episode):
                    if not ep_title:
                        ep_title = ep_en.get('name', '').strip()
                    if not ep_plot:
                        ep_plot = ep_en.get('overview', '').strip()
                    if not ep_aired:
                        ep_aired = ep_en.get('aired', '')
                    break

        if nfo_overrides:
            if nfo_overrides.get("title"): ep_title = nfo_overrides["title"]
            if nfo_overrides.get("plot"): ep_plot = nfo_overrides["plot"]
            if nfo_overrides.get("aired"): ep_aired = nfo_overrides["aired"]

        if needs_nfo:
            xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            xml += '<episodedetails>\n  <lockdata>true</lockdata>\n'
            xml += f"  <title>{escape_xml(ep_title)}</title>\n"
            xml += f"  <season>{nfo_season}</season>\n"
            xml += f"  <episode>{nfo_episode}</episode>\n"
            xml += f"  <plot>{escape_xml(ep_plot)}</plot>\n"
            if ep_aired:
                xml += f"  <aired>{ep_aired}</aired>\n"
            xml += f"  <rating>{ep_data.get('score', 0)}</rating>\n"
            xml += '</episodedetails>\n'
            with open(nfo_path, 'w', encoding='utf-8') as f:
                f.write(xml)
                log_message(f"[NFO] {nfo_path}: created (provider={provider})")

        if needs_thumb and ep_data.get('image'):
            try: _download_with_timeout(ep_data.get('image'), thumb_path); needs_thumb = False
            except Exception as e: print(f"Warning: Ignored exception {e}")

        return {"nfo": needs_nfo, "thumb": not needs_thumb}

    lang = "en-US" if provider == "tmdb_tv_en" else "de-DE"
    url = f"https://api.themoviedb.org/3/tv/{show_id}/season/{season}/episode/{episode}?api_key={TMDB_API_KEY}&language={lang}"
    try:
        req = make_tmdb_request(url)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
    except Exception as e:
        if needs_nfo:
            try:
                ep_title = f"Folge {nfo_episode}"
                ep_plot = f"Automatischer Fallback: Details konnten nicht geladen werden ({str(e)})."
                ep_aired = ""
                if nfo_overrides:
                    if nfo_overrides.get("title"): ep_title = nfo_overrides["title"]
                    if nfo_overrides.get("plot"): ep_plot = nfo_overrides["plot"]
                    if nfo_overrides.get("aired"): ep_aired = nfo_overrides["aired"]

                xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                xml += '<episodedetails>\n  <lockdata>true</lockdata>\n'
                xml += f"  <title>{escape_xml(ep_title)}</title>\n"
                xml += f"  <season>{nfo_season}</season>\n"
                xml += f"  <episode>{nfo_episode}</episode>\n"
                xml += f"  <plot>{escape_xml(ep_plot)}</plot>\n"
                if ep_aired:
                    xml += f"  <aired>{ep_aired}</aired>\n"
                xml += '</episodedetails>\n'
                with open(nfo_path, 'w', encoding='utf-8') as f:
                    f.write(xml)
                    log_message(f"[NFO] {nfo_path}: created (provider={provider})")
                return {"nfo": True, "thumb": False, "msg": f"Online-Fehler ({str(e)}), lokaler Fallback generiert"}
            except Exception as write_err:
                return {"error": f"Original: {str(e)}, Schreibfehler Fallback: {str(write_err)}"}
        return {"error": str(e)}

    if needs_nfo:
        ep_title = data.get('name', '')
        ep_plot = data.get('overview', '')
        ep_aired = data.get('air_date', '')
        if nfo_overrides:
            if nfo_overrides.get("title"): ep_title = nfo_overrides["title"]
            if nfo_overrides.get("plot"): ep_plot = nfo_overrides["plot"]
            if nfo_overrides.get("aired"): ep_aired = nfo_overrides["aired"]

        xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        xml += '<episodedetails>\n  <lockdata>true</lockdata>\n'
        xml += f"  <title>{escape_xml(ep_title)}</title>\n"
        xml += f"  <season>{nfo_season}</season>\n"
        xml += f"  <episode>{nfo_episode}</episode>\n"
        xml += f"  <plot>{escape_xml(ep_plot)}</plot>\n"
        if ep_aired:
            xml += f"  <aired>{ep_aired}</aired>\n"
        xml += f"  <rating>{data.get('vote_average', 0)}</rating>\n"
        xml += '</episodedetails>\n'
        with open(nfo_path, 'w', encoding='utf-8') as f:
            f.write(xml)
            log_message(f"[NFO] {nfo_path}: created (provider={provider})")

    if needs_thumb and data.get('still_path'):
        try:
            t_url = f"https://image.tmdb.org/t/p/original{data['still_path']}"
            _download_with_timeout(t_url, thumb_path)
        except Exception as e:
            print(f"[Artwork Error] Episoden-Thumbnail S{season}E{episode} nicht ladbar: {e}", file=sys.stderr)
            needs_thumb = False

    return {"nfo": needs_nfo, "thumb": needs_thumb}

def generate_youtube_nfo(json_path, nfo_path, nfo_type):
    import os
    if not os.path.exists(json_path):
        return {"nfo": False, "msg": "JSON not found"}

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        return {"error": str(e)}

    title = escape_xml(data.get('title', ''))
    plot = escape_xml(data.get('description', ''))
    year = data.get('upload_date', '')[:4] if data.get('upload_date') else ''
    premiered = f"{year}-{data['upload_date'][4:6]}-{data['upload_date'][6:8]}" if len(data.get('upload_date', '')) == 8 else ''
    channel = escape_xml(data.get('uploader', ''))

    xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    if nfo_type == "movie":
        xml += '<movie>\n  <lockdata>true</lockdata>\n'
        xml += f"  <title>{escape_xml(title)}</title>\n"
        xml += f"  <plot>{plot}</plot>\n"
        xml += f"  <year>{year}</year>\n"
        xml += f"  <premiered>{premiered}</premiered>\n"
        xml += f"  <studio>{channel}</studio>\n"
        xml += '</movie>\n'
    elif nfo_type == "episode":
        xml += '<episodedetails>\n  <lockdata>true</lockdata>\n'
        xml += f"  <title>{escape_xml(title)}</title>\n"
        xml += f"  <plot>{plot}</plot>\n"
        xml += f"  <year>{year}</year>\n"
        xml += f"  <aired>{premiered}</aired>\n"
        xml += f"  <studio>{channel}</studio>\n"
        xml += '</episodedetails>\n'

    with open(nfo_path, 'w', encoding='utf-8') as f:
        f.write(xml)
        log_message(f"[NFO] {nfo_path}: created (provider='youtube')")

    return {"nfo": True}

def guess_season(provider, show_id, filenames_json_or_list):
    if isinstance(filenames_json_or_list, str):
        try:
            filenames = json.loads(filenames_json_or_list)
        except Exception as e:
            print(f"[Season Guess Error] Dateinamen-Liste unlesbar: {e}", file=sys.stderr)
            return None
    else:
        filenames = filenames_json_or_list
    if not filenames:
        return None

    seasons = []
    try:
        if provider in ["tmdb_tv", "tmdb_tv_en", "tmdb"]:
            url = f"https://api.themoviedb.org/3/tv/{show_id}?api_key={TMDB_API_KEY}"
            req = make_tmdb_request(url)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                seasons = [str(s['season_number']) for s in data.get('seasons', []) if s.get('season_number', 0) > 0]
        elif provider == "tvdb":
            token = get_tvdb_token()
            url = f"https://api4.thetvdb.com/v4/series/{show_id}/extended"
            req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}', 'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode()).get('data', {})
                seasons = [str(s['number']) for s in data.get('seasons', []) if s.get('type', {}).get('id') == 1 and s.get('number', 0) > 0]
        elif provider == "tvmaze":
            url = f"https://api.tvmaze.com/shows/{show_id}/seasons"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                seasons = [str(s['number']) for s in data if s.get('number', 0) > 0]
    except Exception as e:
        print(f"[Season Guess Error] Staffelliste für '{show_id}' ({provider}) nicht abrufbar: {e}", file=sys.stderr)

    if not seasons: return None

    best_season = ""
    best_season_score = 0.0

    import re
    def get_words(text):
        words = set(re.findall(r'\w+', text.lower()))
        return {w for w in words if w not in ['der', 'die', 'das', 'in', 'im', 'teil', 'part', 'von', 'und', 'folge', 'episode']}

    file_word_sets = [get_words(f) for f in filenames]

    for season in reversed(seasons):
        if provider in ["tmdb_tv", "tmdb_tv_en", "tmdb"]:
            episodes = fetch_tmdb_tv(show_id, season, lang="de-DE")
        elif provider == "tvdb":
            episodes = fetch_tvdb(show_id, season, lang="deu")
        elif provider == "tvmaze":
            episodes = fetch_tvmaze(show_id, season)
        else:
            episodes = {}

        season_score = 0.0
        matches = 0

        for file_words in file_word_sets:
            best_ep_score = 0.0
            for ep_num, ep_data in episodes.items():
                title = ep_data.get('title', '') if isinstance(ep_data, dict) else str(ep_data)
                title_words = get_words(title)
                if not title_words: continue
                overlap = len(title_words.intersection(file_words))
                score = overlap / len(title_words)
                if score > best_ep_score:
                    best_ep_score = score
            if best_ep_score > 0.4:
                season_score += best_ep_score
                matches += 1

        if matches > 0 and season_score > best_season_score:
            best_season_score = season_score
            best_season = season

        # Fast exit if we found matches for almost all files (at least half)
        if matches >= max(1, len(filenames) * 0.5):
            break

    if best_season:
        return best_season
    return None

def clean_search_query(query):
    if not query:
        return ""
    q = query.strip()
    # If it is a direct ID (IMDB ID or TMDB ID) or digits, don't clean it
    if q.startswith("tt") or q.startswith("tmdb:") or q.isdigit():
        return q

    # Remove video file extensions first
    q = re.sub(r"\.(mkv|mp4|avi|webm|mov|m4v|3gp|flv)$", "", q, flags=re.IGNORECASE)

    # Clean prefix duplication: e.g. "Tom-Taxi.Taxi..." or "Tom-Taxi_Taxi..."
    temp_q = q.replace("_", ".").replace(" ", ".")
    if "." in temp_q:
        parts = [p.strip() for p in temp_q.split(".") if p.strip()]
        if len(parts) > 1:
            first_part = parts[0]
            second_part = parts[1]
            if len(first_part) > len(second_part) and first_part.lower().endswith(second_part.lower()):
                prefix_len = len(first_part) - len(second_part)
                if prefix_len <= 10 or any(c in first_part for c in ('-', '_', ' ')):
                    pattern = r"^" + re.escape(first_part) + r"[\._\s-]+"
                    q = re.sub(pattern, "", q, flags=re.IGNORECASE)

    # Check if the query looks like a raw release name containing common noise patterns.
    # We do this to distinguish release names from clean hyphenated titles like "He-Man".
    has_release_noise = bool(re.search(
        r"\b(19\d{2}|20\d{2}|1080p|720p|2160p|4k|uhd|x264|x265|h264|h265|hevc|bluray|web-dl|webdl|webrip|web|hdtv|german|deutsch|dl|multi|S\d+(E\d+)?)\b",
        q,
        re.IGNORECASE
    ))

    # Remove release tags at the end like "-GRP" or "-TvR" BEFORE replacing dashes,
    # but only if the query has release noise or the hyphen is preceded by a space, dot, underscore, or digit.
    if has_release_noise:
        q = re.sub(r"[\s\._-]\s*(?!\d{4}$)[a-zA-Z0-9]+$", "", q)
    elif re.search(r"[\s\._\d]-\s*[a-zA-Z0-9]+$", q):
        q = re.sub(r"-\s*[a-zA-Z0-9]+$", "", q)

    # Remove lowercase short prefixes followed by a hyphen (e.g., "sh-") at the start,
    # but avoid stripping capitalized names like "He-Man" or "X-Men".
    q = re.sub(r"^[a-z]{2,3}-(?=[A-Z0-9])", "", q)

    # Replace dots, underscores, dashes with spaces
    q = re.sub(r"[\._-]", " ", q)

    # Extract and remove 4-digit years (e.g. 2011) to avoid confusing search APIs
    year_match = re.search(r"\b(19\d{2}|20\d{2})\b", q)
    if year_match:
        year = year_match.group(1)
        q = q.replace(year, " ")

    # Noise terms commonly found in release filenames (resolutions, codecs, language, audio, groups)
    noise_patterns = [
        r"\bS\d+(E\d+)?\b",  # S01, S01E01
        r"\bSeason\s+\d+\b",
        r"\bStaffel\s+\d+\b",
        r"\b(1080p|720p|2160p|4k|576p|480p|1080i|720i|3d|uhd)\b",
        r"\b(x264|x265|h264|h265|hevc|avc|mpeg2|mpeg4|hvc1|av1|av01|vp9|vc1|divx|xvid)\b",
        r"\b(bluray|blu-ray|web-dl|webdl|webrip|web|hdtv|dvd|dvdrip|bdrip|brrip|remux|complete|uncut|unrated|retail|proper|repack)\b",
        r"\b(dd5\.?1|dd2\.?0|dts|dts-hd|truehd|atmos|ac3|aac)\b",
        r"\b(german|deutsch|english|englisch|dl|multi|subbed|dubbed|dub|sub)\b",
        r"\b(directors?\s*cut|extended\s*cut|theatrical\s*cut|final\s*cut)\b",
        r"\b(extended|directors?|theatrical|remastered|limited|special|edition|imax|hdr(10)?(\+)?|sdr|dv|dovi|dolby\s*vision|10\s*bit|8\s*bit|10bit|8bit)\b",
    ]

    for pat in noise_patterns:
        q = re.sub(pat, " ", q, flags=re.IGNORECASE)

    # Clean up double/multiple spaces and brackets
    q = re.sub(r"\(\s*\)", " ", q)
    q = re.sub(r"\[\s*\]", " ", q)
    q = re.sub(r"\s+", " ", q).strip()
    return q

def calculate_match_score(query, result_name):
    if not query or not result_name:
        return 0.0

    # Extract year from query
    q_year_match = re.search(r"\b(19\d{2}|20\d{2})\b", query)
    q_year = q_year_match.group(1) if q_year_match else None

    # Clean query (remove year for title matching)
    clean_q = query
    if q_year:
        clean_q = clean_q.replace(q_year, "")
    clean_q = clean_search_query(clean_q)

    # Extract year from result_name
    res_year_match = re.search(r"\((\d{4})\)", result_name)
    res_year = res_year_match.group(1) if res_year_match else None

    # Clean result name (remove year in parentheses and provider brackets)
    clean_res = re.sub(r"\[.*\]", "", result_name)
    clean_res = re.sub(r"\(\d{4}\)", "", clean_res)
    clean_res = clean_search_query(clean_res)

    # Normalize German umlauts to make comparison robust
    def normalize_umlauts(s):
        if not s: return ""
        s = s.lower()
        s = s.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
        return s

    clean_q_norm = normalize_umlauts(clean_q)
    clean_res_norm = normalize_umlauts(clean_res)

    # Compute words
    q_words = set(re.findall(r"\w+", clean_q_norm))
    res_words = set(re.findall(r"\w+", clean_res_norm))

    if not q_words or not res_words:
        score = 0.0
    else:
        # Jaccard similarity index
        intersection = q_words.intersection(res_words)
        union = q_words.union(res_words)
        score = len(intersection) / len(union)

        # Word set exact matching bonus
        q_sorted = " ".join(sorted(q_words))
        res_sorted = " ".join(sorted(res_words))
        if q_sorted == res_sorted:
            score += 0.5
        elif clean_q_norm in clean_res_norm or clean_res_norm in clean_q_norm:
            score += 0.2

    # Year compatibility score
    if q_year and res_year:
        if q_year == res_year:
            score += 0.3
        else:
            score -= 1.5  # Heavy penalty for mismatch

    return max(0.0, score)


# --- Mediathek & YT-DLP Integration ---

class SmartRedirectHandler(urllib.request.HTTPRedirectHandler):
    def http_error_308(self, req, fp, code, msg, headers):
        newurl = headers.get('location') or headers.get('Location')
        if not newurl:
            raise urllib.error.HTTPError(req.full_url, code, msg, headers, fp)
        newurl = urllib.parse.urljoin(req.full_url, newurl)
        new_req = self.redirect_request(req, fp, 307, msg, headers, newurl)
        return self.parent.open(new_req)

def resolve_mediathek_url_topic(url_or_topic):
    if not isinstance(url_or_topic, str):
        return url_or_topic

    val = url_or_topic.strip()
    if not (val.startswith("http://") or val.startswith("https://")):
        return val

    # Resolve URL to topic
    # 1. Try Scraping using a local SmartRedirectHandler
    try:
        req = urllib.request.Request(
            val,
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"}
        )
        opener = urllib.request.build_opener(SmartRedirectHandler)
        with opener.open(req, timeout=5) as response:
            html = response.read().decode('utf-8', errors='ignore')

        title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE)
        if title_match:
            raw_title = title_match.group(1).strip()

            # Apply title cleanup logic
            # Remove "Vorschau:" prefix
            title = re.sub(r"^Vorschau:\s*", "", raw_title, flags=re.IGNORECASE)

            # Remove explicit sender suffixes
            for suffix in [" - ZDFmediathek", " - ARD Mediathek", " - ZDF", " - ARD", " | ARD Mediathek", " | ZDFmediathek"]:
                if title.endswith(suffix):
                    title = title[:-len(suffix)].strip()

            # Split only on separators with spaces
            for sep in [" - ", " | ", " • "]:
                if sep in title:
                    title = title.split(sep)[0].strip()

            if title:
                return title
    except Exception as e:
        print(f"[resolve_mediathek_url_topic] Scraping failed for {val}: {e}", file=sys.stderr)

    # 2. Heuristics fallback (URL path parsing)
    try:
        parsed = urllib.parse.urlparse(val)
        path_parts = [p for p in parsed.path.split('/') if p]
        if path_parts:
            # ARD Mediathek check: /sendung/topic-name/id
            if "ardmediathek.de" in parsed.netloc:
                if "sendung" in path_parts:
                    idx = path_parts.index("sendung")
                    if idx + 1 < len(path_parts):
                        topic = path_parts[idx + 1]
                        return topic.replace("-", " ").title()

            # ZDF/Arte check or generic fallback:
            last_part = path_parts[-1]
            # If the last part looks like a numerical ID or long hash, use the penultimate part
            if len(path_parts) > 1 and (last_part.isdigit() or len(last_part) > 30):
                last_part = path_parts[-2]

            # Remove trailing numbers/version identifiers like heute-show-104 -> heute-show
            last_part = re.sub(r'-\d+$', '', last_part)
            return last_part.replace("-", " ").title()
    except Exception as e:
        print(f"[resolve_mediathek_url_topic] Heuristics failed for {val}: {e}", file=sys.stderr)

    if val.startswith("http://") or val.startswith("https://"):
        return None
    return val


def search_mediathek(query):
    url = "https://mediathekviewweb.de/api/query"
    payload = {
        "queries": [
            {
                "fields": ["title", "topic"],
                "query": query
            }
        ],
        "sortBy": "timestamp",
        "sortOrder": "desc",
        "future": True,
        "offset": 0,
        "size": 50
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            results = []
            seen_topics = set()
            for item in res_data.get("result", {}).get("results", []):
                topic = item.get("topic") or item.get("title")
                if not topic: continue
                topic_clean = topic.strip()
                if topic_clean not in seen_topics:
                    seen_topics.add(topic_clean)
                    channel = item.get("channel", "Mediathek")
                    results.append({
                        "id": topic_clean,
                        "name": f"{topic_clean} [{channel}]",
                        "provider": "mediathek"
                    })
            return results
    except Exception as e:
        print(f"[search_mediathek] Error: {e}", file=sys.stderr)
        return []

def fetch_mediathek_episodes(topic):
    is_query_search = False
    if topic.startswith("url_mediathek:"):
        topic = topic.split("url_mediathek:", 1)[1]
        is_query_search = True

    if topic.startswith("http://") or topic.startswith("https://"):
        resolved = resolve_mediathek_url_topic(topic)
        if resolved:
            topic = resolved
            is_query_search = True

    url = "https://mediathekviewweb.de/api/query"
    payload = {
        "queries": [
            {
                "fields": ["topic"] if not is_query_search else ["title", "topic"],
                "query": topic,
                "exact": not is_query_search
            }
        ],
        "sortBy": "timestamp",
        "sortOrder": "asc",
        "future": True,
        "offset": 0,
        "size": 100
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            episodes = {}
            results = res_data.get("result", {}).get("results", [])

            if not results:
                payload["queries"][0]["exact"] = False
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
                    },
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=10) as fallback_response:
                    res_data = json.loads(fallback_response.read().decode("utf-8"))
                    results = res_data.get("result", {}).get("results", [])

            for idx, item in enumerate(results):
                title = item.get("title") or f"Folge {idx+1}"
                date_str = ""
                ts = item.get("timestamp")
                if ts:
                    try:
                        import datetime
                        date_str = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
                    except Exception:
                        pass

                ep_num = str(idx + 1)
                episodes[ep_num] = {
                    "title": title.replace('/', '-').replace(':', '').strip(),
                    "date": date_str,
                    "plot": item.get("description", "")
                }
            return episodes
    except Exception as e:
        print(f"[fetch_mediathek_episodes] Error: {e}", file=sys.stderr)
        return {}

YTDLP_CACHE = {}

def fetch_ytdlp_url_metadata(url):
    if url in YTDLP_CACHE:
        return YTDLP_CACHE[url]

    import subprocess
    import json

    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--dump-json",
        "--cookies-from-browser", "chrome",
        url
    ]

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = proc.communicate(timeout=30)

        entries = []
        for line in stdout.splitlines():
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except Exception:
                    pass

        if not entries:
            cmd_no_cookies = ["yt-dlp", "--flat-playlist", "--dump-json", url]
            proc = subprocess.Popen(cmd_no_cookies, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = proc.communicate(timeout=30)
            for line in stdout.splitlines():
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except Exception:
                        pass

        if len(YTDLP_CACHE) >= 100:
            first_key = next(iter(YTDLP_CACHE))
            YTDLP_CACHE.pop(first_key, None)
        YTDLP_CACHE[url] = entries
        return entries
    except Exception as e:
        print(f"[fetch_ytdlp_url_metadata] Error: {e}", file=sys.stderr)
        return []

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("{}")
        sys.exit(1)

    action = sys.argv[1]

    if action == "search_tvmaze":
        query = sys.argv[2]
        res = search_tvmaze(query)
        print(json.dumps(res))
    elif action == "search_tmdb":
        query = sys.argv[2]
        res = search_tmdb_movie(query)
        print(json.dumps(res))
    elif action == "search_tmdb_tv":
        query = sys.argv[2]
        res = search_tmdb_tv(query, "de-DE")
        print(json.dumps(res))
    elif action == "search_tmdb_tv_en":
        query = sys.argv[2]
        res = search_tmdb_tv(query, "en-US")
        print(json.dumps(res))
    elif action == "fetch_tvmaze":
        show_id = sys.argv[2]
        season = sys.argv[3]
        res = fetch_tvmaze(show_id, season)
        print(json.dumps(res))
    elif action == "fetch_fernsehserien":
        show_name = sys.argv[2]
        season = sys.argv[3]
        res = get_fernsehserien_episodes(show_name, season)
        print(json.dumps(res))
    elif action == "fetch_tmdb_tv":
        show_id = sys.argv[2]
        season = sys.argv[3]
        res = fetch_tmdb_tv(show_id, season, "de-DE")
        print(json.dumps(res))
    elif action == "fetch_tmdb_tv_en":
        show_id = sys.argv[2]
        season = sys.argv[3]
        res = fetch_tmdb_tv(show_id, season, "en-US")
        print(json.dumps(res))
    elif action == "search_all_db":
        query = sys.argv[2]
        res = search_all_db(query)
        print(json.dumps(res))
    elif action == "fetch_tvdb":
        show_id = sys.argv[2]
        season = sys.argv[3]
        res = fetch_tvdb(show_id, season, "deu")
        print(json.dumps(res))
    elif action == "show_info":
        provider = sys.argv[2]
        show_id = sys.argv[3]
        res = get_show_info(provider, show_id)
        print(res)
    elif action == "match_episode":
        filename = sys.argv[2]
        json_str = sys.argv[3]
        res = match_episode(filename, json_str)
        print(res)
    elif action == "generate_movie_nfo":
        tmdb_id = sys.argv[2]
        folder_path = sys.argv[3]
        filename_base = sys.argv[4]
        fallback = sys.argv[5] if len(sys.argv) > 5 else None
        res = generate_movie_nfo(tmdb_id, folder_path, filename_base, fallback)
        print(json.dumps(res))
    elif action == "search_ofdb":
        query = sys.argv[2]
        res = search_ofdb(query)
        print(json.dumps(res))
    elif action == "generate_ofdb_nfo":
        ofdb_full_id = sys.argv[2]
        folder_path = sys.argv[3]
        filename_base = sys.argv[4]
        fallback = sys.argv[5] if len(sys.argv) > 5 else None
        res = generate_ofdb_nfo(ofdb_full_id, folder_path, filename_base, fallback)
        print(json.dumps(res))
    elif action == "generate_tvshow_nfo":
        provider = sys.argv[2]
        show_id = sys.argv[3]
        target_folder = sys.argv[4]
        res = generate_tvshow_nfo(provider, show_id, target_folder)
        print(json.dumps(res))
    elif action == "generate_episode_nfo":
        provider = sys.argv[2]
        show_id = sys.argv[3]
        season = sys.argv[4]
        episode = sys.argv[5]
        target_folder = sys.argv[6]
        filename_base = sys.argv[7]
        res = generate_episode_nfo(provider, show_id, season, episode, target_folder, filename_base)
        print(json.dumps(res))
    elif action == "generate_youtube_nfo":
        json_path = sys.argv[2]
        nfo_path = sys.argv[3]
        nfo_type = sys.argv[4]
        res = generate_youtube_nfo(json_path, nfo_path, nfo_type)
        print(json.dumps(res))
    elif action == "guess_season":
        provider = sys.argv[2]
        show_id = sys.argv[3]
        filenames_json = sys.argv[4]
        res = guess_season(provider, show_id, filenames_json)
        if res:
            print(res)
    else:
        print("{}")
