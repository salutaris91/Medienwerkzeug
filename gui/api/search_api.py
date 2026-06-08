import os, sys, json, time, shutil, subprocess, urllib, threading
from flask import Blueprint, request, jsonify, Response, send_from_directory
from gui.core.utils import load_settings, save_settings, clean_show_name, load_show_profile, save_show_profile, load_konv_history
from gui.core.helpers import *
from gui.core.helpers import log_queue
from gui.core.transfers import *
from gui.workers.processor import *
from gui.workers.youtube_worker import *
import gui.core.media as media
import gui.mw_metadata as mw_metadata

search_api = Blueprint('search_api', __name__)

# Global variables imported from processor
from gui.workers.processor import SYSTEM_STATUS



@search_api.route('/guess-season', methods=['GET', 'POST'])
def handle_api_guess_season():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    query = request.args
    provider = params.get("provider")
    show_id = params.get("show_id")
    filenames = params.get("filenames", [])
    
    if not provider or not show_id:
        return jsonify({"error": "provider or show_id is missing"}), 400
        
    try:
        season = mw_metadata.guess_season(provider, show_id, filenames)
        return jsonify({"season": season})
    except Exception as e:
        print(f"Error guessing season: {e}")
        return jsonify({"season": None})



@search_api.route('/match-episodes', methods=['GET', 'POST'])
def handle_api_match_episodes():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    query = request.args
    provider = params.get("provider")
    show_id = params.get("show_id")
    season = params.get("season")
    filenames = params.get("filenames", [])
    
    if not provider or not show_id or not season:
        return jsonify({"error": "provider, show_id or season is missing"}), 400
        
    episodes = {}
    try:
        if provider == "tvdb":
            episodes = mw_metadata.fetch_tvdb(show_id, season, "deu")
        elif provider in ["tmdb_tv", "tmdb_tv_en"]:
            lang = "en-US" if provider == "tmdb_tv_en" else "de-DE"
            episodes = mw_metadata.fetch_tmdb_tv(show_id, season, lang)
        elif provider == "tvmaze":
            episodes = mw_metadata.fetch_tvmaze(show_id, season)
        elif provider == "mediathek":
            episodes = mw_metadata.fetch_mediathek_episodes(show_id)
        elif provider == "ytdlp":
            entries = mw_metadata.fetch_ytdlp_url_metadata(show_id)
            episodes = {}
            if not isinstance(entries, dict):
                for idx, ent in enumerate(entries):
                    ep_idx = ent.get("playlist_index") or ent.get("playlist_autonumber") or (idx + 1)
                    episodes[str(ep_idx)] = {"title": ent.get("title", ""), "plot": ent.get("description", "")}
    except mw_metadata.MetadataProviderUnavailable as e:
        print(f"Provider Error: {e}")
        return jsonify({"error": str(e), "status": "error"}), getattr(e, 'status_code', 503)
    except Exception as e:
        print(f"Error fetching episodes for matching: {e}")
        
    matches = {}
    def guess_ep_num(filename):
        clean_name = filename.lower()
        # 1. Parentheses/brackets check for absolute episode numbers first! E.g. (381) or [381]
        match = re.search(r'(?:\(|\[)(?:folge\s+)?(\d+)(?:\)|\])', clean_name)
        if match:
            return int(match.group(1))
            
        # s01e05
        match = re.search(r's\d+e(\d+)', clean_name)
        if match:
            return int(match.group(1))
        # 1x05
        match = re.search(r'\d+x(\d+)', clean_name)
        if match:
            return int(match.group(1))
        # ep 05 / episode 05
        match = re.search(r'ep(?:isode)?[.\s-]?(\d+)', clean_name)
        if match:
            return int(match.group(1))
        # isolated digits (excluding year range 1900-2100)
        without_ext = os.path.splitext(filename)[0]
        digit_matches = re.findall(r'\b\d+\b', without_ext)
        if digit_matches:
            for digit_str in digit_matches:
                val = int(digit_str)
                if 0 < val < 2000:
                    if 1950 <= val <= 2050:
                        continue
                    return val
        return None
        
    def get_words(text):
        words = set(re.findall(r'\w+', text.lower()))
        return {w for w in words if w not in ['der', 'die', 'das', 'in', 'im', 'teil', 'part', 'von', 'und', 'folge', 'episode']}
        
    for file in filenames:
        basename = os.path.basename(file)
        # 1. Hard match based on filename patterns
        ep_num = guess_ep_num(basename)
        if ep_num is not None:
            # Direct check (e.g. if key is "381" or "39")
            if str(ep_num) in episodes:
                matches[file] = str(ep_num)
                continue
                
            # Absolute number check (e.g. if keys are S01E01 style or year-based S2010E39 style, but contain absolute_number = 381)
            found_key = None
            for key, ep_data in episodes.items():
                if isinstance(ep_data, dict) and ep_data.get("absolute_number") is not None:
                    try:
                        if int(ep_data.get("absolute_number")) == int(ep_num):
                            found_key = key
                            break
                    except (ValueError, TypeError):
                        pass
            if found_key:
                matches[file] = found_key
                continue
                
            # Check if it matches the episode number suffix in key (e.g., ep_num=39, key="S2010E39")
            found_key = None
            for key in episodes.keys():
                match = re.match(r"^s\d+e(\d+)$", str(key), re.IGNORECASE)
                if match:
                    if int(match.group(1)) == int(ep_num):
                        found_key = key
                        break
            if found_key:
                matches[file] = found_key
                continue
            
        # 2. Fuzzy match based on text overlap with episode titles
        file_words = get_words(basename)
        if not file_words:
            matches[file] = None
            continue
            
        best_ep_num = None
        best_score = 0.0
        for ep_n, ep_data in episodes.items():
            title = ep_data.get('title', '') if isinstance(ep_data, dict) else str(ep_data)
            title_words = get_words(title)
            if not title_words:
                continue
            overlap = len(title_words.intersection(file_words))
            score = overlap / len(title_words)
            if score > best_score:
                best_score = score
                best_ep_num = ep_n
                
        if best_score > 0.35:
            matches[file] = best_ep_num
        else:
            matches[file] = None
            
    # Duplicate detection logic
    duplicates = {}
    nas_destination_id = params.get("nas_destination_id")
    nas_show_folder = params.get("nas_show_folder")
    show_name = params.get("show_name")
    
    settings = load_settings()
    nas_root = settings.get("nas_root", "")
    if not nas_root:
        return jsonify({"matches": matches, "duplicates": duplicates})
    
    show_dir = None
    if show_name or nas_show_folder:
        destination = None
        if nas_destination_id:
            sync_cats = settings.get("sync_categories", [])
            found_cat = None
            for cat in sync_cats:
                if cat.get("id") == str(nas_destination_id):
                    found_cat = cat
                    break
            if found_cat:
                destination = os.path.join(nas_root, found_cat.get("nas_sub", "").lstrip("/"))
        if not destination:
            destination = os.path.join(nas_root, "Serien")
            
        clean_show_name = clean_series_name_for_fs(nas_show_folder or show_name)
        if clean_show_name:
            show_dir = os.path.join(destination, clean_show_name)
            
    def check_duplicate(ep_season, ep_num):
        if not show_dir or not os.path.exists(show_dir) or ep_season is None or ep_num is None:
            return None
        pats = [
            f"s{ep_season:02d}e{ep_num:02d}",
            f"s{ep_season:02d}e{ep_num:03d}",
            f"s{ep_season}e{ep_num:02d}",
            f"s{ep_season:02d}e{ep_num}",
        ]
        for root, _, files in os.walk(show_dir):
            for f in files:
                if f.startswith('.'):
                    continue
                fl = f.lower()
                matched = False
                for pat in pats:
                    if pat in fl:
                        matched = True
                        break
                if not matched and ep_season == 1:
                    for suffix in [f" - {ep_num:02d} ", f" - {ep_num:02d}.", f" - {ep_num:03d} ", f" - {ep_num:03d}."]:
                        if suffix in fl:
                            matched = True
                            break
                if matched:
                    # Only count video files as duplicates
                    ext = os.path.splitext(f)[1].lower()
                    if ext not in ('.mp4', '.mkv', '.avi', '.webm', '.mov', '.ts', '.m2ts'):
                        continue
                    filepath = os.path.join(root, f)
                    details = {"filename": f, "path": filepath}
                    try:
                        size_bytes = os.path.getsize(filepath)
                        details["size_gb"] = size_bytes / (1024 * 1024 * 1024)
                        cmd = [
                            "ffprobe", "-v", "error", "-select_streams", "v:0",
                            "-show_entries", "stream=width,height", "-of", "csv=p=0",
                            filepath
                        ]
                        res = subprocess.run(cmd, capture_output=True, text=True, timeout=2.0)
                        if res.returncode == 0:
                            dimensions = res.stdout.strip().split(',')
                            if len(dimensions) == 2:
                                details["resolution"] = f"{dimensions[0]}x{dimensions[1]}"
                    except Exception:
                        pass
                    return details
        return None

    for file in filenames:
        matched_ep = matches.get(file)
        if matched_ep:
            match = re.match(r"^S(\d+)E(\d+)$", str(matched_ep), re.IGNORECASE)
            if match:
                ep_season = int(match.group(1))
                ep_num = int(match.group(2))
            else:
                try:
                    ep_num = int(matched_ep)
                    ep_season = int(season)
                except (ValueError, TypeError):
                    ep_num = None
                    ep_season = None
            
            dup_details = check_duplicate(ep_season, ep_num)
            if dup_details:
                duplicates[file] = dup_details
                
    return jsonify({"matches": matches, "duplicates": duplicates})



@search_api.route('/estimate-conversion', methods=['GET', 'POST'])
def handle_api_estimate_conversion():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    query = request.args
    project_name = params.get("project_name", "")
    filenames = params.get("filenames", [])
    quality = params.get("quality", 60)
    
    settings = load_settings()
    inbox_root = settings.get("inbox_dir", "")
    
    estimates = {}
    if not inbox_root:
        return jsonify({"estimates": estimates})
        
    if project_name:
        target_dir = os.path.join(inbox_root, project_name)
    else:
        target_dir = inbox_root
        
    estimates = {}
    first_successful_ratio = None
    for f in filenames:
        filepath = os.path.join(target_dir, f)
        if os.path.exists(filepath):
            try:
                size_in = os.path.getsize(filepath)
                if first_successful_ratio is not None:
                    ratio = first_successful_ratio
                else:
                    ratio = media.konvertierung_schaetzen(filepath, quality)
                    first_successful_ratio = ratio
                
                estimated_size = int(size_in * ratio)
                estimates[f] = {
                    "ratio": ratio,
                    "size_in": size_in,
                    "size_out": estimated_size
                }
            except Exception as e:
                print(f"Error estimating size for {f}: {e}")
                estimates[f] = {"error": str(e)}
        else:
            estimates[f] = {"error": "File not found"}
            
    return jsonify({"estimates": estimates})



@search_api.route('/toggle-visibility', methods=['POST'])
def handle_api_toggle_visibility():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    query = request.args
    target_path = params.get("path")
    hide = params.get("hide", True)
    if not target_path or not os.path.exists(target_path):
        return jsonify({"error": "Invalid path"}), 400
    # Security: only allow toggling visibility within known media directories
    abs_target = os.path.abspath(target_path)
    if not is_path_allowed(abs_target):
        return jsonify({"error": "Path not in allowed directories"}), 403
        
    try:
        flag = "hidden" if hide else "nohidden"
        subprocess.run(["chflags", flag, target_path], check=True)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)})



@search_api.route('/search', methods=['GET', 'POST'])
def handle_api_search():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    query = request.args
    q = query.get("q", "").strip()
    media_type = query.get("type", "tv")
    
    results = []
    errors = []
    
    try:
        if q.startswith("http://") or q.startswith("https://"):
            try:
                if "fernsehserien.de" in q:
                    slug = q.rstrip("/").split("/")[-1]
                    results = [{
                        "id": q,
                        "name": f"{slug.replace('-', ' ').title()} (fernsehserien.de URL)",
                        "provider": "fernsehserien",
                        "media_type": "tv"
                    }]
                else:
                    entries = mw_metadata.fetch_ytdlp_url_metadata(q)
                    if entries:
                        if len(entries) > 1:
                            show_name = entries[0].get("playlist_title") or entries[0].get("playlist") or "YouTube/Mediathek Playlist"
                            results = [{
                                "id": q,
                                "name": f"{show_name} ({len(entries)} Videos via URL)",
                                "provider": "ytdlp",
                                "media_type": "tv"
                            }]
                        else:
                            title = entries[0].get("title") or "Video via URL"
                            # Determine media type based on search request and metadata
                            has_series_info = any(entries[0].get(k) for k in ["series", "season_number", "episode_number", "season", "episode"])
                            if media_type in ("tv", "doku") or has_series_info:
                                res_type = media_type if media_type in ("tv", "doku") else "tv"
                            else:
                                res_type = "movie"
                            results = [{
                                "id": q,
                                "name": f"{title} (Video via URL)",
                                "provider": "ytdlp",
                                "media_type": res_type
                            }]
                    else:
                        # Fallback for Mediathek/other URLs that yt-dlp fails to extract directly
                        import urllib.request
                        import re
                        req = urllib.request.Request(q, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"})
                        try:
                            with urllib.request.urlopen(req, timeout=5) as response:
                                html = response.read().decode('utf-8', errors='ignore')
                            title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE)
                            if title_match:
                                title = title_match.group(1).strip()
                                title = re.sub(r"^Vorschau:\s*", "", title, flags=re.IGNORECASE)
                                title = title.split("|")[0].split(" - ARD")[0].split(" - ZDF")[0].strip()
                                
                                search_term = title
                                if "•" in title:
                                    search_term = title.split("•")[0].strip()
                                elif " - " in title:
                                    search_term = title.split(" - ")[0].strip()
                                
                                res_type = media_type if media_type in ("tv", "doku") else "movie"
                                name_suffix = "Serie aus URL" if res_type != "movie" else "Film aus URL"
                                results = [{
                                    "id": f"url_mediathek:{search_term}",
                                    "name": f"{search_term} (Mediathek {name_suffix})",
                                    "provider": "mediathek",
                                    "media_type": res_type
                                }]
                        except Exception as e:
                            print(f"Error scraping fallback URL {q}: {e}")
            except Exception as e:
                errors.append(e)
        elif media_type == "tv":
            try:
                tv_res = mw_metadata.search_all_db(q)
                for r in tv_res:
                    r["media_type"] = "tv"
                results.extend(tv_res)
            except Exception as e:
                errors.append(e)
            # Add free-search option for Mediathek
            results.append({
                "id": f"url_mediathek:{q}",
                "name": f"{q} (Freie Mediathek-Suche)",
                "provider": "mediathek",
                "media_type": "tv"
            })
        elif media_type == "movie":
            try:
                tmdb_res = mw_metadata.search_tmdb_movie(q)
                for r in tmdb_res:
                    r['provider'] = 'tmdb'
                    r["media_type"] = "movie"
                results.extend(tmdb_res)
            except Exception as e:
                errors.append(e)
            
            try:
                ofdb_res = mw_metadata.search_ofdb(q)
                for r in ofdb_res:
                    results.append({
                        "id": r["id"],
                        "name": f"{r['title']} ({r['year']})",
                        "provider": "ofdb",
                        "media_type": "movie"
                    })
            except Exception as e:
                errors.append(e)
            if results:
                results.sort(key=lambda r: mw_metadata.calculate_match_score(q, r['name']), reverse=True)
        elif media_type == "doku":
            # Parallel-ish search for Dokus (TV, Movies, Mediathek)
            # 1. TV Series
            try:
                tv_res = mw_metadata.search_all_db(q)
                for r in tv_res:
                    r["media_type"] = "tv"
                results.extend(tv_res)
            except Exception as e:
                errors.append(e)
            
            # 2. Movie search
            try:
                tmdb_res = mw_metadata.search_tmdb_movie(q)
                for r in tmdb_res:
                    r['provider'] = 'tmdb'
                    r["media_type"] = "movie"
                results.extend(tmdb_res)
            except Exception as e:
                errors.append(e)
            
            # 3. Mediathek search
            try:
                mediathek_res = mw_metadata.search_mediathek(q)
                for r in mediathek_res:
                    r["media_type"] = "tv"
                    r["provider"] = "mediathek"
                results.extend(mediathek_res)
            except Exception as e:
                errors.append(e)
            
            # Sort combined results
            if results:
                results.sort(key=lambda r: mw_metadata.calculate_match_score(q, r['name']), reverse=True)
    except Exception as e:
        errors.append(e)
        
    # Check if we have "real" results (i.e. not only the static Mediathek free-search fallback)
    has_real_results = False
    if results:
        if media_type == "tv":
            has_real_results = len(results) > 1 or (len(results) == 1 and not results[0]["id"].startswith("url_mediathek:"))
        else:
            has_real_results = len(results) > 0
            
    if not has_real_results and errors:
        first_error = None
        for err in errors:
            if isinstance(err, mw_metadata.MetadataProviderUnavailable):
                first_error = err
                break
        if not first_error:
            first_error = errors[0]
            
        if isinstance(first_error, mw_metadata.MetadataProviderUnavailable):
            print(f"Provider Error: {first_error}")
            return jsonify({"error": str(first_error), "status": "error"}), getattr(first_error, 'status_code', 503)
        else:
            print(f"Search error: {first_error}")
            return jsonify({"error": str(first_error), "status": "error"}), 500
            
    return jsonify(results)



@search_api.route('/fetch-show-info', methods=['GET', 'POST'])
def handle_api_fetch_show_info():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    query = request.args
    provider = query.get("provider", "tmdb_tv")
    show_id = query.get("show_id", "")
    
    info = "Keine Info gefunden"
    try:
        info = mw_metadata.get_show_info(provider, show_id)
    except Exception as e:
        info = f"Fehler: {e}"
        
    return jsonify({"info": info})



@search_api.route('/fetch-episodes', methods=['GET', 'POST'])
def handle_api_fetch_episodes():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    query = request.args
    provider = query.get("provider", "tmdb_tv")
    show_id = query.get("show_id", "")
    season = query.get("season", "1")
    
    episodes = {}
    try:
        if provider == "tvdb":
            episodes = mw_metadata.fetch_tvdb(show_id, season, "deu")
        elif provider in ["tmdb_tv", "tmdb_tv_en"]:
            lang = "en-US" if provider == "tmdb_tv_en" else "de-DE"
            episodes = mw_metadata.fetch_tmdb_tv(show_id, season, lang)
        elif provider == "tvmaze":
            episodes = mw_metadata.fetch_tvmaze(show_id, season)
        elif provider == "mediathek":
            episodes = mw_metadata.fetch_mediathek_episodes(show_id)
        elif provider == "ytdlp":
            entries = mw_metadata.fetch_ytdlp_url_metadata(show_id)
            if not isinstance(entries, dict):
                for idx, ent in enumerate(entries):
                    ep_idx = ent.get("playlist_index") or ent.get("playlist_autonumber") or (idx + 1)
                    title = ent.get("title", "")
                    alt_title = ent.get("alt_title", "")
                    show_name = ent.get("playlist_title") or ent.get("playlist", "")
                    ep_title = title
                    if alt_title and mw_metadata.normalize_title(title) == mw_metadata.normalize_title(show_name):
                        ep_title = alt_title
                    elif alt_title and not title:
                        ep_title = alt_title
                    episodes[str(ep_idx)] = {"title": ep_title, "plot": ent.get("description", ""), "date": ent.get("upload_date", "")}
        elif provider == "fernsehserien":
            episodes = mw_metadata.get_fernsehserien_episodes(show_id, season)
    except mw_metadata.MetadataProviderUnavailable as e:
        print(f"Provider Error: {e}")
        return jsonify({"error": str(e), "status": "error"}), getattr(e, 'status_code', 503)
    except Exception as e:
        print(f"Error fetching episodes: {e}")
        
    return jsonify(episodes)


def find_existing_series_folder_by_id(destination_path, provider, show_id):
    if not destination_path or not os.path.exists(destination_path) or not show_id:
        return None
    try:
        for entry in os.listdir(destination_path):
            folder_path = os.path.join(destination_path, entry)
            if os.path.isdir(folder_path) and not entry.startswith('.'):
                nfo_path = os.path.join(folder_path, "tvshow.nfo")
                if os.path.exists(nfo_path):
                    try:
                        with open(nfo_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        import re
                        m_id = re.search(r'<mw_showid>(.*?)</mw_showid>', content)
                        m_prov = re.search(r'<mw_provider>(.*?)</mw_provider>', content)
                        if m_id and m_prov:
                            if m_id.group(1).strip() == str(show_id) and m_prov.group(1).strip() == str(provider):
                                return entry
                        
                        if provider == "tvdb":
                            m_tvdb = re.search(r'<tvdbid>(.*?)</tvdbid>', content)
                            if m_tvdb and m_tvdb.group(1).strip() == str(show_id):
                                return entry
                        elif provider in ["tmdb_tv", "tmdb_tv_en"]:
                            m_tmdb = re.search(r'<tmdbid>(.*?)</tmdbid>', content)
                            if m_tmdb and m_tmdb.group(1).strip() == str(show_id):
                                return entry
                    except Exception:
                        pass
    except Exception as e:
        print(f"Error scanning folders for ID match: {e}")
    return None


@search_api.route('/series/find-folder-by-id', methods=['GET'])
def handle_api_find_folder_by_id():
    query = request.args
    provider = query.get("provider")
    show_id = query.get("show_id")
    destination_id = query.get("destination_id")
    
    if not provider or not show_id:
        return jsonify({"folder": None}), 400
        
    settings = load_settings()
    nas_root = settings.get("nas_root", "")
    if not nas_root:
        return jsonify({"folder": None})
    
    destination = None
    if destination_id:
        sync_cats = settings.get("sync_categories", [])
        for cat in sync_cats:
            if cat.get("id") == str(destination_id):
                destination = os.path.join(nas_root, cat.get("nas_sub", "").lstrip("/"))
                break
    if not destination:
        destination = os.path.join(nas_root, "Serien")
        
    folder = find_existing_series_folder_by_id(destination, provider, show_id)
    return jsonify({"folder": folder})


@search_api.route('/series-detect', methods=['GET', 'POST'])
@search_api.route('/series/detect', methods=['GET', 'POST'])
def handle_api_series_detect():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    query = request.args
    project_name = ""
    if "project_name" in query and len(query["project_name"]) > 0:
        project_name = query.get("project_name", "")
        
    nas_destination_id = ""
    if "nas_destination_id" in query and len(query["nas_destination_id"]) > 0:
        nas_destination_id = query.get("nas_destination_id", "")
    elif "destination_id" in query and len(query["destination_id"]) > 0:
        nas_destination_id = query.get("destination_id", "")
        
    if not project_name:
        return jsonify({"found": False})
        
    settings = load_settings()
    nas_root = settings.get("nas_root", "")
    outbox_root = settings.get("outbox_dir", "")
    if not nas_root or not outbox_root:
        return jsonify({"found": False})
    
    # Resolve destination paths to search in
    destinations = []
    sync_cats = settings.get("sync_categories", [])
    
    if nas_destination_id == "all":
        for cat in sync_cats:
            nas_sub = cat.get("nas_sub", "")
            if nas_sub:
                destinations.append(f"{nas_root}{nas_sub}")
    else:
        found_cat = None
        if nas_destination_id:
            for cat in sync_cats:
                if cat.get("id") == str(nas_destination_id):
                    found_cat = cat
                    break
            if not found_cat:
                for cat in sync_cats:
                    nas_sub = cat.get("nas_sub", "")
                    if nas_sub and (nas_sub in str(nas_destination_id)):
                        found_cat = cat
                        break
        if found_cat:
            destinations.append(f"{nas_root}{found_cat.get('nas_sub')}")
        else:
            destinations.append(f"{nas_root}/Serien")
        
    connected = ensure_nas_mounted()
    
    # Find all folders and map them to their parent destination directory
    folders = set()
    folder_to_dest = {}
    
    for destination in destinations:
        if connected and os.path.exists(destination):
            try:
                for entry in os.listdir(destination):
                    if os.path.isdir(os.path.join(destination, entry)) and not entry.startswith('.'):
                        folders.add(entry)
                        folder_to_dest[entry] = destination
            except Exception:
                pass
                
        rel_dest = os.path.relpath(destination, nas_root)
        outbox_dest = os.path.join(outbox_root, rel_dest)
        if os.path.exists(outbox_dest):
            try:
                for entry in os.listdir(outbox_dest):
                    if os.path.isdir(os.path.join(outbox_dest, entry)) and not entry.startswith('.'):
                        folders.add(entry)
                        if entry not in folder_to_dest:
                            folder_to_dest[entry] = destination
            except Exception:
                pass
                
    cleaned_proj = clean_series_name_for_fs(project_name)
    
    # Helper to find best match in list
    best_match = None
    
    # 1. Exact case-insensitive match
    for f in folders:
        if f.lower().strip() == cleaned_proj.lower().strip():
            best_match = f
            break
            
    # 2. Normalized match
    if not best_match:
        import re
        norm_proj = re.sub(r'[^a-zA-Z0-9]', '', cleaned_proj.lower())
        if norm_proj:
            for f in folders:
                norm_f = re.sub(r'[^a-zA-Z0-9]', '', f.lower())
                if norm_f == norm_proj:
                    best_match = f
                    break
                    
    # 3. Substring match
    if not best_match:
        norm_proj = re.sub(r'[^a-zA-Z0-9]', '', cleaned_proj.lower())
        if len(norm_proj) >= 4:
            for f in folders:
                norm_f = re.sub(r'[^a-zA-Z0-9]', '', f.lower())
                if norm_proj in norm_f or norm_f in norm_proj:
                    best_match = f
                    break
                    
    if best_match:
        existing_seasons = []
        folder_found = False
        matched_dest = folder_to_dest.get(best_match)
        if matched_dest:
            folder_found = True
            series_dirs = []
            if connected and os.path.exists(matched_dest):
                series_dirs.append(os.path.join(matched_dest, best_match))
            
            rel_dest = os.path.relpath(matched_dest, nas_root)
            outbox_series_dir = os.path.join(outbox_root, rel_dest, best_match)
            series_dirs.append(outbox_series_dir)
            
            for sd in series_dirs:
                if os.path.exists(sd) and os.path.isdir(sd):
                    try:
                        for entry in os.listdir(sd):
                            entry_path = os.path.join(sd, entry)
                            if os.path.isdir(entry_path) and not entry.startswith('.'):
                                if entry not in existing_seasons:
                                    existing_seasons.append(entry)
                    except Exception:
                        pass
        existing_seasons.sort(key=lambda s: s.lower())

        # Check if tvshow.nfo exists
        # We must check both NAS and Outbox paths
        nfo_paths = []
        if matched_dest:
            if connected and os.path.exists(matched_dest):
                nfo_paths.append(os.path.join(matched_dest, best_match, "tvshow.nfo"))
            
            rel_dest = os.path.relpath(matched_dest, nas_root)
            outbox_dest = os.path.join(outbox_root, rel_dest)
            nfo_paths.append(os.path.join(outbox_dest, best_match, "tvshow.nfo"))
            
        show_id = None
        provider = None
        
        for np in nfo_paths:
            if os.path.exists(np):
                try:
                    with open(np, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Search for mw_provider and mw_showid
                    import re
                    m_prov = re.search(r'<mw_provider>(.*?)</mw_provider>', content)
                    m_id = re.search(r'<mw_showid>(.*?)</mw_showid>', content)
                    
                    if m_prov and m_id:
                        provider = m_prov.group(1).strip()
                        show_id = m_id.group(1).strip()
                        break
                        
                    # Fallback search for tvdbid or tmdbid
                    m_tvdb = re.search(r'<tvdbid>(.*?)</tvdbid>', content)
                    if m_tvdb:
                        provider = "tvdb"
                        show_id = m_tvdb.group(1).strip()
                        break
                        
                    m_tmdb = re.search(r'<tmdbid>(.*?)</tmdbid>', content)
                    if m_tmdb:
                        provider = "tmdb_tv"
                        show_id = m_tmdb.group(1).strip()
                        break
                except Exception:
                    pass
                    
        if show_id and provider:
            return jsonify({
                "found": True,
                "show_id": show_id,
                "provider": provider,
                "show_name": best_match,
                "folder_found": folder_found,
                "existing_seasons": existing_seasons
            })
        else:
            return jsonify({
                "found": False,
                "show_name": best_match,
                "folder_found": folder_found,
                "existing_seasons": existing_seasons
            })
            
    return jsonify({"found": False})



@search_api.route('/metadata/fetch', methods=['GET', 'POST'])
def handle_api_metadata_fetch():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    query = request.args
    media_type = query.get("media_type", "")
    provider = query.get("provider", "")
    
    result = {}
    try:
        if media_type == "tv":
            show_id = query.get("show_id", "")
            result = mw_metadata.fetch_show_nfo_data(provider, show_id)
        elif media_type == "movie":
            movie_id = query.get("movie_id", "")
            result = mw_metadata.fetch_movie_nfo_data(provider, movie_id)
        elif media_type == "episode":
            show_id = query.get("show_id", "")
            season = query.get("season", "")
            episode = query.get("episode", "")
            result = mw_metadata.fetch_episode_nfo_data(provider, show_id, season, episode)
    except Exception as e:
        result = {"error": str(e)}
        
    return jsonify(result)



@search_api.route('/joke', methods=['GET', 'POST'])
def handle_api_joke():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    query = request.args
    joke = get_random_joke()
    return jsonify({"joke": joke})



@search_api.route('/quote', methods=['GET', 'POST'])
def handle_api_quote():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    query = request.args
    import urllib.request
    import urllib.error
    import random
    
    try:
        url = "https://api.zitat-service.de/v1/quote?language=de"
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            if data.get("quote"):
                return jsonify(data)
    except Exception as e:
        log_message(f"[Zitat API] Fehler beim Abrufen des Online-Zitats: {e}")
        
    backup_quotes = [
        {
            "quote": "Wenn du die Absicht hast, dich zu erneuern, tu es jeden Tag.",
            "authorName": "Konfuzius"
        },
        {
            "quote": "Die beste Methode, das Leben zu meistern, ist, es als ein Abenteuer zu betrachten.",
            "authorName": "Unbekannt"
        },
        {
            "quote": "Wege entstehen dadurch, dass man sie geht.",
            "authorName": "Franz Kafka"
        },
        {
            "quote": "Auch aus Steinen, die einem in den Weg gelegt werden, kann man Schönes bauen.",
            "authorName": "Johann Wolfgang von Goethe"
        },
        {
            "quote": "Fantasie ist wichtiger als Wissen, denn Wissen ist begrenzt.",
            "authorName": "Albert Einstein"
        }
    ]
    return jsonify(random.choice(backup_quotes))


