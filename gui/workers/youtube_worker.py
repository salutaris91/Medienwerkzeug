from gui.core.utils import load_settings, save_settings
import os, urllib.request, json, time, asyncio, subprocess
from gui.core.helpers import *
def fetch_online_jokes_async():
    def target():
        url = "https://raw.githubusercontent.com/salutaris91/Mediawerkzeug/main/gui/data/jokes.json"
        import urllib.request
        import json
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                if isinstance(data, list) and len(data) > 0:
                    local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "jokes.json")
                    os.makedirs(os.path.dirname(local_path), exist_ok=True)
                    with open(local_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    print(f"Jokes successfully updated from GitHub. Total jokes: {len(data)}")
        except Exception as e:
            print(f"Failed to fetch jokes from GitHub (using cached/local copy): {e}")
            
    threading.Thread(target=target, daemon=True).start()

def get_random_joke():
    import random
    import json
    local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "jokes.json")
    try:
        if os.path.exists(local_path):
            with open(local_path, "r", encoding="utf-8") as f:
                jokes = json.load(f)
                if isinstance(jokes, list) and len(jokes) > 0:
                    return random.choice(jokes)
    except Exception as e:
        print(f"Error loading joke: {e}")
        
    return "Was ist gelb und kann nicht schwimmen? Ein Bagger!"

def is_text_german(text, is_description=False, context_keywords=None):
    import re
    if not text:
        return False
    text_lower = text.lower()
    
    # 1. Check for German-specific characters
    if any(c in text_lower for c in ['ä', 'ö', 'ü', 'ß']):
        return True
        
    # 2. Words that are 100% German and immediately override any English stop words
    GERMAN_OVERRIDE = {
        'deutsch', 'deutsche', 'deutscher', 'deutsches', 'hörbuch', 
        'schauspieler', 'kinderserie', 'kindheit', 'erinnerungen',
        'karmesin', 'purpur', 'schwert', 'schild', 'feuerrot', 'blattgrün',
        'spieletipps', 'komplettlösung', 'spielvorstellung'
    }
    
    words = re.findall(r'\b[a-z]+\b', text_lower)
    if not words:
        return False
        
    # If any override word is present, it's German!
    if any(w in GERMAN_OVERRIDE for w in words):
        return True
        
    # 3. Strict German stop words (never/extremely rarely appear in English)
    GERMAN_STRICT = {
        'und', 'ich', 'mit', 'nicht', 'von', 'auf', 'dem', 'aus', 'sich', 'aber', 
        'oder', 'bei', 'nur', 'auch', 'nach', 'vor', 'über', 'mehr', 'durch', 
        'unter', 'wir', 'ihr', 'wer', 'wo', 'wenn', 'dann', 'alle', 'doch',
        'folge', 'staffel', 'freunde', 'welt', 'neue', 'neuen', 'suchen', 'suche', 'zieht', 
        'einen', 'einem', 'einer', 'eines', 'heute', 'damals', 'ganzer', 'ausflug', 
        'rummelplatz', 'spiel', 'spielen', 'abenteuer', 'lustig', 'kostenlos', 
        'herunterladen', 'anschauen', 'sehen', 'jetzt', 'immer', 'hier', 'uns',
        'euch', 'mich', 'dich', 'mein', 'meine', 'meinen', 'meinem', 'meiner', 'meines',
        'erste', 'erster', 'erstes', 'ersten', 'teil', 'neues', 'gibt', 'viele', 'alles',
        'gute', 'gutes', 'guten', 'guter'
    }
    
    # 4. Ambiguous words (very common in German, but also exist/common in English)
    GERMAN_AMBIGUOUS = {
        'der', 'die', 'das', 'ist', 'zu', 'den', 'ein', 'eine', 'im', 'des', 'als', 'was', 'an'
    }
    
    # 5. English stop words to detect English texts
    ENGLISH_STOP = {
        'the', 'and', 'to', 'of', 'a', 'in', 'is', 'that', 'it', 'he', 'was', 'for', 
        'on', 'are', 'as', 'with', 'his', 'they', 'i', 'at', 'be', 'this', 'have', 
        'from', 'or', 'one', 'had', 'by', 'but', 'not', 'what', 'all', 'were', 'we', 
        'when', 'your', 'can', 'there', 'use', 'an', 'each', 'which', 'she', 'how', 
        'their', 'if', 'will', 'up', 'other', 'about', 'out', 'many', 'then', 'them', 
        'these', 'so', 'some', 'her', 'would', 'make', 'like', 'him', 'into', 'has', 
        'look', 'two', 'more', 'write', 'go', 'see', 'no', 'way', 'could', 'people', 
        'my', 'than', 'first', 'been', 'who', 'its', 'now', 'find', 'long', 'down', 
        'day', 'did', 'get', 'come', 'made', 'may', 'part', 'you', 'your', 'yours',
        'about', 'subscription', 'channel', 'videos', 'twitter', 'instagram', 'patreon',
        'discord', 'playlist', 'subscribe', 'video', 'kids', 'tv', 'fun', 'episode',
        'episodes', 'official', 'series', 'full', 'game', 'games', 'play', 'playing',
        'toy', 'toys', 'show', 'shows', 'song', 'songs', 'music', 'cartoon', 'cartoons',
        'animation', 'animated', 'anime', 'only', 'before', 'worth', 'buying', 'price',
        'prices', 'box', 'boxes', 'card', 'cards', 'pack', 'packs', 'deck', 'decks',
        'opening', 'openings', 'rare', 'rarest', 'spent', 'days', 'trainer', 'minecraft',
        'mythical', 'shiny', 'leak', 'leaks', 'news', 'waves', 'winds', 'starters', 'into',
        'sword', 'shield', 'mystery', 'silver', 'tempest', 'keep', 'deals', 'cardshop',
        'shop', 'until', 'pull', 'charizard', 'challenge', 'meet', 'kanto', 'partner',
        'lonely', 'reality', 'store', 'stores', 'summer', 'collection', 'cheap', 'expensive',
        'pets', 'chased', 'chaos', 'rising', 'opened', 'tins', 'newest', 'meta', 'additions',
        'made', 'raid', 'attempted', 'nuzlocke', 'scarlet', 'violet', 'drop', 'random',
        'anniversary', 'evolution', 'life', 'stopping', 'league', 'tournament'
    }
    
    strict_matches = [w for w in words if w in GERMAN_STRICT]
    ambig_matches = [w for w in words if w in GERMAN_AMBIGUOUS]
    english_matches = [w for w in words if w in ENGLISH_STOP]
    
    # Count unique matches to avoid single word repetition throwing off the count
    unique_strict = set(strict_matches)
    unique_ambig = set(ambig_matches)
    unique_english = set(english_matches)
    
    # Score calculation
    # Strict German words are strong indicators
    german_score = len(unique_strict) * 3.0 + len(unique_ambig) * 0.8
    
    # Add context keywords bonus
    if context_keywords:
        context_matches = [w for w in words if w in context_keywords]
        unique_context = set(context_matches)
        german_score += len(unique_context) * 2.5
        
    english_score = len(unique_english) * 2.0
    
    if english_score > german_score:
        return False
        
    # Minimum requirement to be German
    if is_description:
        return german_score >= 5.0
    else:
        return german_score >= 1.5

def check_single_subscription(sub):
    import uuid
    import time
    url = sub.get("url")
    if url and not (url.startswith("http://") or url.startswith("https://")):
        url = f"ytsearch50:{url}"
        
    if not url:
        return
        
    cmd = ["yt-dlp", "--playlist-end", "50", "--dump-json", "--flat-playlist", url]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        if res.returncode != 0:
            log_message(f"[YouTube Abo-Überwachung] yt-dlp Fehler für {sub.get('name')}: {res.stderr}")
            return
            
        lines = res.stdout.strip().split('\n')
        
        settings = load_settings()
        sub_in_settings = None
        for s in settings.get("youtube_subscriptions", []):
            if s.get("id") == sub.get("id"):
                sub_in_settings = s
                break
                
        if not sub_in_settings:
            return
            
        has_changes = False
        
        # Fetch channel avatar if not already present
        if not sub_in_settings.get("avatar_url") and not (url.startswith("ytsearch")):
            try:
                avatar_cmd = ["yt-dlp", "--dump-single-json", "--playlist-items", "0", url]
                avatar_res = subprocess.run(avatar_cmd, capture_output=True, text=True, timeout=10)
                if avatar_res.returncode == 0:
                    playlist_data = json.loads(avatar_res.stdout)
                    thumbnails = playlist_data.get("thumbnails", [])
                    avatar_url = ""
                    for t in thumbnails:
                        if t.get("id") == "avatar_uncropped" or t.get("id") == "avatar":
                            avatar_url = t.get("url")
                            break
                    if not avatar_url and thumbnails:
                        sorted_thumbs = sorted(thumbnails, key=lambda x: x.get("preference", 0), reverse=True)
                        if sorted_thumbs:
                            avatar_url = sorted_thumbs[0].get("url")
                    if avatar_url:
                        sub_in_settings["avatar_url"] = avatar_url
                        has_changes = True
            except Exception as av_err:
                log_message(f"[YouTube Abo-Überwachung] Fehler beim Laden des Kanallogos: {av_err}")
                
        auto_download = sub_in_settings.get("auto_download", True)
        filter_german = sub_in_settings.get("filter_german", False)
        search_filter = sub_in_settings.get("search_filter", "").lower().strip()
        exclude_keywords = [w.strip().lower() for w in sub_in_settings.get("exclude_keywords", "").split(",") if w.strip()]
        last_checked_ts = sub_in_settings.get("last_checked_timestamp", 0)
        
        downloaded_ids = sub_in_settings.get("downloaded_ids", [])
        pending_videos = sub_in_settings.get("pending_videos", [])
        pending_ids = [v.get("id") for v in pending_videos if v.get("id")]
        
        is_first_check = (last_checked_ts == 0)
        new_downloads = 0
        max_timestamp = last_checked_ts
        
        if is_first_check:
            log_message(f"[YouTube Abo-Überwachung] Erste Überprüfung für Abonnement '{sub.get('name')}'. Initialisiere Basis-Zeitstempel und markiere bestehende Videos als gelesen.")
            for line in lines:
                if not line.strip():
                    continue
                try:
                    video_data = json.loads(line)
                    v_id = video_data.get("id")
                    v_timestamp = video_data.get("timestamp")
                    if not v_timestamp and video_data.get("upload_date"):
                        try:
                            from datetime import datetime
                            v_timestamp = datetime.strptime(video_data.get("upload_date"), "%Y%m%d").timestamp()
                        except Exception:
                            pass
                    
                    if v_id and v_id not in downloaded_ids:
                        downloaded_ids.append(v_id)
                        has_changes = True
                    if v_timestamp and v_timestamp > max_timestamp:
                        max_timestamp = v_timestamp
                except Exception:
                    pass
            if max_timestamp == 0:
                max_timestamp = time.time()
        else:
            # Parse all videos from the feed lines first
            feed_videos = []
            for line in lines:
                if not line.strip():
                    continue
                try:
                    video_data = json.loads(line)
                    feed_videos.append(video_data)
                except Exception:
                    pass

            # Extract dynamic context keywords if German filter is enabled
            context_keywords = set()
            if filter_german:
                try:
                    import re
                    from collections import Counter
                    words_list = []
                    german_video_count = 0
                    
                    ALL_STOP = {
                        'der', 'die', 'das', 'und', 'ist', 'zu', 'den', 'von', 'mit', 'auf', 'für', 'ein', 'eine', 
                        'im', 'dem', 'des', 'aus', 'nicht', 'sich', 'wie', 'aber', 'oder', 'bei', 'nur', 
                        'einen', 'einem', 'einer', 'eines', 'als', 'auch', 'nach', 'vor', 'über', 'mehr', 
                        'durch', 'unter', 'wir', 'ihr', 'was', 'wer', 'wo', 'wenn', 'dann', 'alle', 'doch',
                        'folge', 'staffel', 'deutsch', 'deutsche', 'deutscher', 'deutsches', 'video', 'neues',
                        'gibt', 'viele', 'alles', 'hier', 'immer', 'jetzt', 'sehen', 'uns', 'euch', 'mich', 'dich',
                        'mein', 'meine', 'meinen', 'meinem', 'meiner', 'meines',
                        'the', 'and', 'to', 'of', 'a', 'in', 'is', 'that', 'it', 'he', 'was', 'for', 
                        'on', 'are', 'as', 'with', 'his', 'they', 'i', 'at', 'be', 'this', 'have', 
                        'from', 'or', 'one', 'had', 'by', 'but', 'not', 'what', 'all', 'were', 'we', 
                        'when', 'your', 'can', 'there', 'use', 'an', 'each', 'which', 'she', 'how', 
                        'their', 'if', 'will', 'up', 'other', 'about', 'out', 'many', 'then', 'them', 
                        'these', 'so', 'some', 'her', 'would', 'make', 'like', 'him', 'into', 'has', 
                        'look', 'two', 'more', 'write', 'go', 'see', 'no', 'way', 'could', 'people', 
                        'my', 'than', 'first', 'been', 'who', 'its', 'now', 'find', 'long', 'down', 
                        'day', 'did', 'get', 'come', 'made', 'may', 'part', 'you', 'your', 'yours',
                        'about', 'subscription', 'channel', 'videos', 'twitter', 'instagram', 'patreon',
                        'discord', 'playlist', 'subscribe', 'video', 'kids', 'tv', 'fun', 'episode',
                        'episodes', 'official', 'series', 'full', 'game', 'games', 'play', 'playing',
                        'toy', 'toys', 'show', 'shows', 'song', 'songs', 'music', 'cartoon', 'cartoons',
                        'animation', 'animated', 'anime', 'only', 'before', 'worth', 'buying', 'price',
                        'prices', 'box', 'boxes', 'card', 'cards', 'pack', 'packs', 'deck', 'decks',
                        'opening', 'openings', 'rare', 'rarest', 'spent', 'days', 'trainer', 'minecraft',
                        'mythical', 'shiny', 'leak', 'leaks', 'news', 'waves', 'winds', 'starters', 'into',
                        'sword', 'shield', 'mystery', 'silver', 'tempest', 'keep', 'deals', 'cardshop',
                        'shop', 'until', 'pull', 'charizard', 'challenge', 'meet', 'kanto', 'partner',
                        'lonely', 'reality', 'store', 'stores', 'summer', 'collection', 'cheap', 'expensive',
                        'pets', 'chased', 'chaos', 'rising', 'opened', 'tins', 'newest', 'meta', 'additions',
                        'made', 'raid', 'attempted', 'nuzlocke', 'scarlet', 'violet', 'drop', 'random',
                        'anniversary', 'evolution', 'life', 'stopping', 'league', 'tournament'
                    }
                    
                    query_words = set(re.findall(r'\b[a-z]+\b', sub.get("name", "").lower()))
                    if sub.get("url"):
                        query_words.update(re.findall(r'\b[a-z]+\b', sub.get("url", "").lower()))
                        
                    for v in feed_videos:
                        title = v.get("title", "")
                        title_lower = title.lower()
                        if any(c in title_lower for c in ['ä', 'ö', 'ü', 'ß']) or any(w in title_lower for w in ['deutsch', 'deutsches', 'deutsche', 'deutscher', 'hörbuch', 'kinderserie']):
                            german_video_count += 1
                            tokens = re.findall(r'\b[a-z]{3,}\b', title_lower)
                            filtered = [t for t in tokens if t not in ALL_STOP and t not in query_words]
                            words_list.extend(filtered)
                            
                    if german_video_count >= 1:
                        counter = Counter(words_list)
                        min_freq = 2 if german_video_count >= 3 else 1
                        context_keywords = {word for word, count in counter.most_common(15) if count >= min_freq}
                        if context_keywords:
                            log_message(f"[YouTube Abo-Überwachung] Dynamische Kontext-Keywords für '{sub.get('name')}' geladen: {context_keywords}")
                except Exception as context_err:
                    log_message(f"[YouTube Abo-Überwachung] Fehler beim Extrahieren der Kontext-Keywords: {context_err}")

            for video_data in feed_videos:
                try:
                    v_id = video_data.get("id")
                    v_title = video_data.get("title", "")
                    v_url = video_data.get("url") or f"https://www.youtube.com/watch?v={v_id}"
                
                    if not v_id or v_id in downloaded_ids or v_id in pending_ids:
                        continue
                    
                    # Exclude keywords check
                    if exclude_keywords:
                        title_lower = v_title.lower()
                        if any(kw in title_lower for kw in exclude_keywords):
                            log_message(f"[YouTube Abo-Überwachung] Video übersprungen wegen Ausschluss-Keyword: {v_title}")
                            if v_id not in downloaded_ids:
                                downloaded_ids.append(v_id)
                                has_changes = True
                            continue
                        
                    # Get video timestamp and/or check German language filter
                    detail_data = None
                    v_timestamp = video_data.get("timestamp")
                    if not v_timestamp and video_data.get("upload_date"):
                        try:
                            from datetime import datetime
                            v_timestamp = datetime.strptime(video_data.get("upload_date"), "%Y%m%d").timestamp()
                        except Exception:
                            pass
                        
                    # Performance: bypass individual video detail fetching to prevent YouTube 429 rate limiting
                    need_details = False
                    if need_details:
                        detail_cmd = ["yt-dlp", "--dump-json", v_url]
                        try:
                            detail_res = subprocess.run(detail_cmd, capture_output=True, text=True, timeout=10)
                            if detail_res.returncode == 0:
                                detail_data = json.loads(detail_res.stdout)
                                video_data = detail_data
                                v_timestamp = video_data.get("timestamp")
                                if not v_timestamp and video_data.get("upload_date"):
                                    try:
                                        from datetime import datetime
                                        v_timestamp = datetime.strptime(video_data.get("upload_date"), "%Y%m%d").timestamp()
                                    except Exception:
                                        pass
                            else:
                                log_message(f"[YouTube Abo-Überwachung] Detail-Fehler für {v_title}: {detail_res.stderr}")
                        except Exception as detail_err:
                            log_message(f"[YouTube Abo-Überwachung] Detail-Timeout/Fehler für {v_title}: {detail_err}")
                
                    # Check timestamp
                    if v_timestamp:
                        if v_timestamp <= last_checked_ts:
                            if v_id not in downloaded_ids:
                                downloaded_ids.append(v_id)
                                has_changes = True
                            continue
                        if v_timestamp > max_timestamp:
                            max_timestamp = v_timestamp
                        
                    # Search filter check
                    if search_filter:
                        if search_filter not in v_title.lower():
                            continue
                        
                    # German language filter check
                    if filter_german:
                        is_german = is_text_german(v_title, context_keywords=context_keywords)
                        if not is_german:
                            desc = video_data.get("description") or ""
                            is_german = is_text_german(desc, is_description=True, context_keywords=context_keywords)
                            
                        # Cascade step 2: If still not recognized as German, but we have detail data (fallback/optional), check language codes and captions
                        if not is_german and detail_data:
                            v_lang = str(detail_data.get("language") or detail_data.get("language_code") or "").lower()
                            v_audio_lang = str(detail_data.get("default_audio_language") or "").lower()
                            if v_lang.startswith("de") or v_audio_lang.startswith("de"):
                                is_german = True
                            if not is_german:
                                auto_caps = detail_data.get("automatic_captions") or {}
                                manual_subs = detail_data.get("subtitles") or {}
                                if any(lang.startswith("de") for lang in auto_caps) or any(lang.startswith("de") for lang in manual_subs):
                                    is_german = True
                            
                        if not is_german:
                            continue
                            
                        if not auto_download:
                            v_thumb = video_data.get("thumbnail") or ""
                            if not v_thumb and video_data.get("thumbnails"):
                                v_thumb = video_data.get("thumbnails")[0].get("url") or ""
                            v_channel = video_data.get("uploader") or video_data.get("channel") or sub.get("name") or "Unbekannt"
                            v_published = video_data.get("upload_date") or ""
                        
                            pending_videos.append({
                                "id": v_id,
                                "title": v_title,
                                "url": v_url,
                                "thumbnail": v_thumb,
                                "channel": v_channel,
                                "published_at": v_published
                            })
                            if len(pending_videos) > 100:
                                pending_videos.pop(0)
                            
                            pending_ids.append(v_id)
                            has_changes = True
                            log_message(f"[YouTube Abo-Überwachung]: Neues Video in Inbox für Abo '{sub.get('name')}': {v_title}")
                        else:
                            log_message(f"[YouTube Abo-Überwachung]: Neuer Treffer für Abo '{sub.get('name')}': {v_title} ({v_url})")
                            task_id = str(uuid.uuid4())
                            sub_copy_to_nas = sub_in_settings.get("copy_to_nas", True)
                            sub_copy_to_pcloud = sub_in_settings.get("copy_to_pcloud", False)
                            sub_copy_to_local = sub_in_settings.get("copy_to_local", False)
                            sub_nas_dest = sub_in_settings.get("nas_destination_id", sub_in_settings.get("destination_id"))
                            sub_pcloud_dest = sub_in_settings.get("pcloud_destination_id")
                            sub_local_dest = sub_in_settings.get("local_destination_id")
                        
                            job_params = {
                                "media_type": "youtube",
                                "yt_url": v_url,
                                "yt_format": "best",
                                "yt_embed_thumbnail": True,
                                "copy_to_nas": sub_copy_to_nas,
                                "copy_to_pcloud": sub_copy_to_pcloud,
                                "copy_to_local": sub_copy_to_local,
                                "destination_id": sub_nas_dest,
                                "nas_destination_id": sub_nas_dest,
                                "pcloud_destination_id": sub_pcloud_dest,
                                "local_destination_id": sub_local_dest,
                                "project_name": "",
                                "task_id": task_id
                            }
                        
                            job_info = {
                                "id": task_id,
                                "type": "youtube",
                                "name": f"Abo: {v_title[:40]}",
                                "status": "queued",
                                "progress": 0,
                                "message": "Automatisch gestartet...",
                                "timestamp": time.time(),
                                "params": job_params,
                                "pipeline": build_job_pipeline(job_params, True, True)
                            }
                        
                            with active_jobs_lock:
                                active_jobs[task_id] = job_info
                            
                            job_queue.put(job_info)
                            downloaded_ids.append(v_id)
                            new_downloads += 1
                            has_changes = True
                        
                except Exception as ex:
                    log_message(f"[YouTube Abo-Überwachung] Fehler bei Video-Verarbeitung: {ex}")
                
        sub_in_settings["last_checked"] = time.time()
        sub_in_settings["last_checked_timestamp"] = max_timestamp
        if has_changes:
            sub_in_settings["downloaded_ids"] = downloaded_ids
            sub_in_settings["pending_videos"] = pending_videos
        save_settings(settings)
        
    except Exception as e:
        log_message(f"[YouTube Abo-Überwachung] Fehler bei Check für {sub.get('name')}: {e}")

def check_youtube_subscriptions_loop():
    # Delay initial check slightly
    time.sleep(10)
    is_startup = True
    while True:
        try:
            settings = load_settings()
            subs = settings.get("youtube_subscriptions", [])
            active_subs = [s for s in subs if s.get("enabled")]
            if active_subs:
                now = time.time()
                subs_to_check = []
                for sub in active_subs:
                    schedule = sub.get("schedule", "hourly")
                    last_checked = sub.get("last_checked") or 0
                    
                    if is_startup:
                        if schedule == "on_startup" or schedule == "hourly":
                            subs_to_check.append(sub)
                        elif schedule == "daily":
                            if now - last_checked >= 23 * 3600:
                                subs_to_check.append(sub)
                    else:
                        if schedule == "hourly":
                            subs_to_check.append(sub)
                        elif schedule == "daily":
                            if now - last_checked >= 23 * 3600:
                                subs_to_check.append(sub)
                                
                if subs_to_check:
                    log_message(f"[YouTube Abo-Überwachung]: Starte turnusmäßigen Check für {len(subs_to_check)} Abos (Startup={is_startup})...")
                    for sub in subs_to_check:
                        check_single_subscription(sub)
        except Exception as e:
            log_message(f"[YouTube Abo-Überwachung] Fehler im Background Loop: {e}")
        is_startup = False
        time.sleep(3600)  # Check every hour

def _do_subscription_check():
    try:
        settings = load_settings()
        subs = settings.get("youtube_subscriptions", [])
        active_subs = [s for s in subs if s.get("enabled")]
        if active_subs:
            log_message(f"[YouTube Abo-Überwachung]: Starte getriggerten Check für {len(active_subs)} Abos...")
            for sub in active_subs:
                check_single_subscription(sub)
    except Exception as e:
        log_message(f"[YouTube Abo-Überwachung] Überwachung Fehler: {e}")

def trigger_youtube_subscriptions_check():
    import uuid
    from gui.core.helpers import job_queue, active_jobs, active_jobs_lock
    task_id = str(uuid.uuid4())
    job_info = {
        "id": task_id,
        "name": "YouTube Abo-Check",
        "type": "youtube_subscription_check",
        "status": "queued",
        "message": "Wartet auf Ausführung...",
        "progress": 0,
        "params": {"media_type": "youtube_subscription_check"}
    }
    with active_jobs_lock:
        active_jobs[task_id] = job_info
    job_queue.put(job_info)

