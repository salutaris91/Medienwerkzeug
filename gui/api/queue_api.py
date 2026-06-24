import os, sys, json, time, shutil, subprocess, urllib, threading, uuid
from flask import Blueprint, request, jsonify, Response, send_from_directory
from gui.core.utils import load_settings, save_settings, clean_show_name, load_show_profile, save_show_profile, load_konv_history
from gui.core.helpers import *
from gui.core.helpers import log_queue
from gui.core.transfers import *
from gui.workers.processor import *
from gui.workers.youtube_worker import *
import gui.core.media as media
import gui.mw_metadata as mw_metadata

queue_api = Blueprint('queue_api', __name__)

# Global variables imported from processor
from gui.workers.processor import SYSTEM_STATUS



@queue_api.route('/preview-process', methods=['GET', 'POST'])
@queue_api.route('/preview_process', methods=['GET', 'POST'])
def handle_api_preview_process():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    query = request.args
    media_type = params.get("media_type")
    project_name = params.get("project_name", "")
    show_id = params.get("show_id")
    movie_id = params.get("movie_id")
    provider = params.get("provider")
    season = params.get("season")
    mappings = params.get("mappings", {})
    destination = params.get("destination")
    nas_destination_id = params.get("nas_destination_id") or params.get("destination_id")
    pcloud_destination_id = params.get("pcloud_destination_id") or params.get("destination_id")
    nfo_overrides = params.get("nfo_overrides", {})

    settings = load_settings()
    inbox_root = settings.get("inbox_dir", "")
    outbox_root = settings.get("outbox_dir", "")
    nas_root = settings.get("nas_root", "")

    if not inbox_root or not outbox_root:
        return jsonify({"status": "error", "message": "Inbox- oder Output-Verzeichnis ist nicht konfiguriert."}), 400

    destination = params.get("destination")
    # Resolve NAS destination path
    if nas_destination_id:
        if not nas_root:
            return jsonify({"status": "error", "message": "NAS-Root ist nicht konfiguriert."}), 400
        sync_cats = settings.get("sync_categories", [])
        found_cat = None
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
            destination = os.path.join(nas_root, found_cat.get('nas_sub', '').lstrip("/"))

    # Resolve pCloud destination remote base
    explicit_pcloud_base = None
    if pcloud_destination_id:
        from gui.core.transfers import resolve_category_target_path
        explicit_pcloud_base = resolve_category_target_path(pcloud_destination_id, "pcloud", media_type)

    is_single_file = False
    if project_name:
        current_dir = os.path.join(inbox_root, project_name)
        if os.path.isfile(current_dir):
            is_single_file = True
    else:
        current_dir = inbox_root

    if not os.path.exists(current_dir):
        return jsonify({"error": "Ordner existiert nicht."})

    if is_single_file:
        all_files = [os.path.basename(current_dir)]
        current_dir = os.path.dirname(current_dir)
    else:
        all_files = sorted(find_files_recursively(current_dir))
    video_exts = ('.mp4', '.mkv', '.avi', '.webm', '.mov', '.ts', '.m2ts', '.flv', '.3gp', '.wmv')
    sub_exts = ('.srt', '.vtt', '.ass', '.ssa', '.sub', '.idx')
    from gui.core.artwork_validators import get_all_allowed_metadata_names
    good_meta = tuple(get_all_allowed_metadata_names())

    preview = {
        "renames": [],
        "subs": [],
        "junk": [],
        "destination": ""
    }

    if media_type == "movie":
        movie_name = params.get("movie_name", "Unbekannter Film")
        if movie_name:
            movie_name = re.sub(r"\s*\(Mediathek.*?\)", "", movie_name)
            movie_name = re.sub(r"\s*\(Freie Mediathek.*?\)", "", movie_name).strip()
            movie_overrides = nfo_overrides.get("movie") if nfo_overrides else None
            if movie_overrides and movie_overrides.get("year"):
                year = str(movie_overrides.get("year")).strip()
                if year.isdigit() and len(year) == 4:
                    movie_name = re.sub(r"\s*\(\d{4}\)$", "", movie_name).strip()
                    movie_name = f"{movie_name} ({year})"
        # Resolve NAS destination target base using resolve_target_destination
        rel_sub = ""
        if destination:
            if destination.startswith(nas_root):
                rel_sub = destination[len(nas_root):]
            else:
                rel_sub = os.path.basename(destination)
        if not rel_sub:
            rel_sub = "/Filme"

        nas_target = None
        for target in settings.get("storage_targets", []):
            if target.get("type") == "nas":
                nas_target = target
                break

        if nas_target:
            target_base = resolve_target_destination(nas_target, rel_sub, "movie")
        else:
            target_base = destination if destination else os.path.join(nas_root, rel_sub.lstrip("/"))

        clean_movie_name = limit_filename_length(sanitize_filename(movie_name))
        nas_path = os.path.join(target_base, clean_movie_name)
        pcloud_path = f"{explicit_pcloud_base}/{clean_movie_name}" if explicit_pcloud_base else None

        if params.get("copy_to_nas", True):
            dest_str = f"NAS: {nas_path}"
        else:
            dest_str = "NAS: (nicht aktiv)"

        if params.get("copy_to_pcloud", False):
            if pcloud_path:
                dest_str += f"\n☁️ pCloud: {pcloud_path}"
            else:
                dest_str += "\n☁️ pCloud: (Kein Mapping gefunden)"
        else:
            dest_str += "\n☁️ pCloud: (nicht aktiv)"
        preview["destination"] = dest_str

        # Collect video files to identify main film and samples
        video_files_in_proj = []
        for f in all_files:
            ext = os.path.splitext(f)[1].lower()
            if ext in video_exts:
                full_p = os.path.join(current_dir, f)
                try:
                    sz = os.path.getsize(full_p) if os.path.exists(full_p) else 0
                except Exception:
                    sz = 0
                video_files_in_proj.append((f, sz))

        # Determine main video and samples
        video_files_in_proj.sort(key=lambda x: x[1], reverse=True)
        main_video = None
        samples = set()

        if video_files_in_proj:
            largest_file, largest_size = video_files_in_proj[0]

            for f, sz in video_files_in_proj:
                is_sample = False
                basename_lower = os.path.basename(f).lower()
                # Kriterium 1: "sample" im Namen oder Pfad
                if "sample" in basename_lower or "sample" in f.lower().split(os.sep):
                    is_sample = True
                # Kriterium 2: Datei < 300 MB und es gibt eine signifikant größere Videodatei
                elif sz < 300 * 1024 * 1024 and largest_size > 300 * 1024 * 1024:
                    is_sample = True

                if is_sample:
                    samples.add(f)

            # Hauptfilm ist die größte Datei, die kein Sample ist
            non_samples = [f for f, sz in video_files_in_proj if f not in samples]
            if non_samples:
                main_video = non_samples[0]
            else:
                main_video = largest_file
                if main_video in samples:
                    samples.remove(main_video)

            # Alle Videodateien außer dem Hauptfilm werden als Samples gewertet
            for f, sz in video_files_in_proj:
                if f != main_video:
                    samples.add(f)

        resolved_subs = {}
        used_resolved_basenames = set()
        for f in all_files:
            basename = os.path.basename(f)
            ext = os.path.splitext(f)[1].lower()

            # Check if this file belongs to a sample
            belongs_to_sample = False
            if f == main_video:
                belongs_to_sample = False
            elif f in samples:
                belongs_to_sample = True
            elif samples and ("sample" in basename.lower() or "sample" in f.lower().split(os.sep)):
                belongs_to_sample = True
            else:
                # Prüfen, ob die Datei zu einem der Sample-Videos gehört (Name match)
                for s_video in samples:
                    s_base = os.path.splitext(os.path.basename(s_video))[0]
                    if basename.startswith(s_base) and f != s_video:
                        belongs_to_sample = True
                        break

            if belongs_to_sample:
                preview["junk"].append(f)
                continue

            if ext in video_exts:
                if f == main_video:
                    target_filename = f"{clean_movie_name}{ext}"
                    preview["renames"].append({"old": f, "new": target_filename})
                else:
                    preview["junk"].append(f)
            elif ext in sub_exts:
                rel_path_no_ext, _ = os.path.splitext(f)
                if rel_path_no_ext in resolved_subs:
                    target_basename = resolved_subs[rel_path_no_ext]
                else:
                    suffix = parse_subtitle_suffix(f)
                    base_candidate = f"{clean_movie_name}{suffix}"
                    candidate = base_candidate
                    counter = 1
                    while candidate in used_resolved_basenames:
                        counter += 1
                        candidate = f"{base_candidate}.{counter}"
                    target_basename = candidate
                    resolved_subs[rel_path_no_ext] = target_basename
                    used_resolved_basenames.add(target_basename)

                target_filename = f"{target_basename}{ext}"
                preview["subs"].append({"old": f, "new": target_filename})
            elif basename.lower() in good_meta:
                preview["subs"].append({"old": f, "new": basename})
            elif ext == '.nfo':
                preview["subs"].append({"old": f, "new": f"{clean_movie_name}.nfo"})
            elif ext in ('.jpg', '.png', '.webp') and 'poster' in basename.lower():
                preview["subs"].append({"old": f, "new": f"{clean_movie_name}-poster{ext}"})
            elif ext in ('.jpg', '.png', '.webp') and ('fanart' in basename.lower() or 'backdrop' in basename.lower()):
                new_sfx = "-fanart" if "fanart" in basename.lower() else "-backdrop"
                preview["subs"].append({"old": f, "new": f"{clean_movie_name}{new_sfx}{ext}"})
            else:
                preview["junk"].append(f)

        # Collide warning for existing movie on NAS (based on planned renames)
        if params.get("copy_to_nas", True) and os.path.exists(nas_path):
            # Check if any renamed file actually collides
            colliding_renames = []
            for r in preview["renames"]:
                target_file_path = os.path.join(nas_path, r["new"])
                if os.path.exists(target_file_path):
                    colliding_renames.append(r)

            if colliding_renames:
                # We have at least one colliding video file. We compare metadata!
                comparison_txt = ""
                for r in colliding_renames:
                    src_full = os.path.join(current_dir, r["old"])
                    dst_full = os.path.join(nas_path, r["new"])

                    src_info = media.get_media_info(src_full)
                    dst_info = media.get_media_info(dst_full)

                    # Helper functions for formatting
                    def fmt_size(sz):
                        if not sz: return "Unbekannt"
                        val = float(sz)
                        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                            if val < 1024.0:
                                return f"{val:.2f} {unit}"
                            val /= 1024.0
                        return f"{val:.2f} PB"

                    def fmt_dur(d):
                        if not d: return "Unbekannt"
                        d = int(d)
                        h = d // 3600
                        m = (d % 3600) // 60
                        s = d % 60
                        if h > 0:
                            return f"{h}h {m}m {s}s"
                        return f"{m}m {s}s"

                    def fmt_bitrate(b):
                        if not b: return "Unbekannt"
                        mbps = b / 1_000_000.0
                        if mbps >= 1.0:
                            return f"{mbps:.1f} Mbps"
                        return f"{b / 1000.0:.0f} kbps"

                    def get_quality_desc(info):
                        if not info or not info.get("width") or not info.get("height"):
                            return "Unbekannt"
                        w = info["width"]
                        h = info["height"]
                        codec = info.get("codec", "unbekannt")
                        if w >= 3840 or h >= 2160:
                            res = "4K UHD"
                        elif w >= 1920 or h >= 1080:
                            res = "1080p Full HD"
                        elif w >= 1280 or h >= 720:
                            res = "720p HD"
                        else:
                            res = f"{w}x{h} SD"
                        return f"{res} ({str(codec).upper()})"

                    src_res = f"{src_info.get('width')}x{src_info.get('height')}" if src_info.get('width') else 'Unbekannt'
                    dst_res = f"{dst_info.get('width')}x{dst_info.get('height')}" if dst_info.get('width') else 'Unbekannt'

                    comparison_txt += (
                        f"ACHTUNG: Die Datei '{r['new']}' existiert bereits auf dem NAS im Ordner '{clean_movie_name}' und wird überschrieben!\n\n"
                        f"Vergleich der Videodateien:\n"
                        f"Eigenschaft           | Vorhandene Datei (NAS)              | Neue Datei (Vorschau)\n"
                        f"----------------------+-------------------------------------+-------------------------------------\n"
                        f"Dateiname             | {r['new'][:35]:<35} | {r['old'][:35]:<35}\n"
                        f"Dateigröße            | {fmt_size(dst_info.get('size')):<35} | {fmt_size(src_info.get('size')):<35}\n"
                        f"Auflösung             | {dst_res:<35} | {src_res:<35}\n"
                        f"Video-Codec           | {str(dst_info.get('codec') or 'Unbekannt').upper():<35} | {str(src_info.get('codec') or 'Unbekannt').upper():<35}\n"
                        f"Audio-Codec           | {str(dst_info.get('audio_codec') or 'Unbekannt').upper():<35} | {str(src_info.get('audio_codec') or 'Unbekannt').upper():<35}\n"
                        f"Bitrate               | {fmt_bitrate(dst_info.get('bit_rate')):<35} | {fmt_bitrate(src_info.get('bit_rate')):<35}\n"
                        f"Dauer                 | {fmt_dur(dst_info.get('duration')):<35} | {fmt_dur(src_info.get('duration')):<35}\n"
                        f"Qualitäts-Einschätzung | {get_quality_desc(dst_info):<35} | {get_quality_desc(src_info):<35}\n"
                    )
                preview["warning"] = comparison_txt
            else:
                existing_videos = []
                try:
                    for item in os.listdir(nas_path):
                        if os.path.splitext(item)[1].lower() in video_exts:
                            existing_videos.append(item)
                except Exception:
                    pass
                if existing_videos:
                    preview["warning"] = f"Achtung: Der Film existiert bereits auf dem NAS im Ordner '{clean_movie_name}' mit folgenden Videodateien: {', '.join(existing_videos)}. Diese Dateien werden nicht direkt von der geplanten Aktion überschrieben, könnten aber beeinträchtigt werden."
                else:
                    preview["warning"] = f"Achtung: Der Film-Ordner '{clean_movie_name}' existiert bereits auf dem NAS, enthält aber keine Videodateien. Vorhandene Metadaten könnten überschrieben werden."

    elif media_type == "tv":
        total_videos_in_proj = sum(1 for vf in all_files if os.path.splitext(vf)[1].lower() in video_exts)

        def is_subtitle_matching_video(sdir, vid_dir):
            is_nested = False
            if sdir == vid_dir:
                is_nested = True
            elif vid_dir == "":
                is_nested = True
            elif sdir.startswith(vid_dir + os.sep):
                is_nested = True

            if not is_nested:
                return False

            curr = sdir
            while curr != vid_dir:
                videos_in_curr = [vf for vf in all_files if os.path.splitext(vf)[1].lower() in video_exts and os.path.dirname(vf) == curr]
                if videos_in_curr:
                    return False
                if curr == "":
                    break
                curr = os.path.dirname(curr)
            return True

        def is_companion_of_any_video(sf):
            sbasename = os.path.basename(sf)
            sext = os.path.splitext(sf)[1].lower()
            sdir = os.path.dirname(sf)

            for vf in all_files:
                if os.path.splitext(vf)[1].lower() not in video_exts:
                    continue
                if vf == sf:
                    continue
                vbasename = os.path.basename(vf)
                vbase_old = os.path.splitext(vbasename)[0]
                vdir = os.path.dirname(vf)

                # Check name prefix
                if sbasename.startswith(vbase_old):
                    return True

                # Folder-level subtitle heuristics
                if sext in sub_exts:
                    if total_videos_in_proj == 1:
                        return True
                    videos_in_same_dir_as_vf = [x for x in all_files if os.path.splitext(x)[1].lower() in video_exts and os.path.dirname(x) == vdir]
                    if len(videos_in_same_dir_as_vf) == 1:
                        if is_subtitle_matching_video(sdir, vdir):
                            return True
            return False

        show_name = params.get("show_name", "Unknown Show")
        nas_show_folder = params.get("nas_show_folder")
        nas_serien = destination if destination else f"{nas_root}/Serien"
        rel_dest = os.path.relpath(nas_serien, nas_root)
        outbox_serien = os.path.join(outbox_root, rel_dest)

        from gui.core.series_helper import resolve_series_folder_name
        clean_show_name = resolve_series_folder_name(
            destination=nas_serien,
            outbox_root=outbox_serien,
            provider=provider,
            show_id=show_id,
            show_name=show_name,
            nas_show_folder=nas_show_folder,
            log_reason=False
        )

        nas_serien = destination if destination else f"{nas_root}/Serien"
        dest_show_dir = os.path.join(nas_serien, clean_show_name)

        pcloud_path = f"{explicit_pcloud_base}/{clean_show_name}" if explicit_pcloud_base else None

        episodes = {}
        if provider and show_id:
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
                            title = ent.get("title", "")
                            alt_title = ent.get("alt_title", "")
                            show_name_yt = ent.get("playlist_title") or ent.get("playlist", "")
                            ep_title = title
                            if alt_title and mw_metadata.normalize_title(title) == mw_metadata.normalize_title(show_name_yt):
                                ep_title = alt_title
                            elif alt_title and not title:
                                ep_title = alt_title
                            episodes[str(ep_idx)] = {"title": ep_title, "plot": ent.get("description", "")}
            except mw_metadata.MetadataProviderUnavailable as e:
                print(f"Provider Error: {e}")
                return jsonify({"error": str(e), "status": "error"}), getattr(e, 'status_code', 503)
            except Exception as e:
                print(f"Error fetching preview episodes: {e}")

        ui_season_val = params.get("ui_season", 1)
        try:
            ui_season_val = int(ui_season_val)
        except (ValueError, TypeError):
            ui_season_val = 1

        clean_titles = []
        for f in all_files:
            basename = os.path.basename(f)
            ext = os.path.splitext(f)[1].lower()

            if ext in video_exts:
                rel_f = os.path.relpath(f, current_dir)
                ep_num = mappings.get(rel_f) or mappings.get(f) or mappings.get(basename)
                if ep_num is not None and ep_num != "":
                    if isinstance(ep_num, dict):
                        curr_season = ep_num.get("season", season)
                        curr_ep_num = ep_num.get("episode", 1)
                        meta_ep = ep_num.get("metadata_ep_num")
                        if meta_ep:
                            ep_data = episodes.get(str(meta_ep), {})
                            if not ep_data and provider == "ytdlp" and len(episodes) == 1:
                                ep_data = list(episodes.values())[0]
                            ep_title = ep_data.get("title", "") if isinstance(ep_data, dict) else str(ep_data)

                            match = re.match(r"^S(\d+)E(\d+)$", str(meta_ep), re.IGNORECASE)
                            if match:
                                if curr_season == "all":
                                    curr_season = int(match.group(1))
                        else:
                            ep_title = ep_num.get("title", "")

                        if curr_season == "all":
                            curr_season = ui_season_val
                    else:
                        ep_data = episodes.get(str(ep_num), {})
                        if not ep_data and provider == "ytdlp" and len(episodes) == 1:
                            ep_data = list(episodes.values())[0]
                        ep_title = ep_data.get("title", "") if isinstance(ep_data, dict) else str(ep_data)

                        match = re.match(r"^S(\d+)E(\d+)$", str(ep_num), re.IGNORECASE)
                        if match:
                            curr_season = int(match.group(1))
                            curr_ep_num = int(match.group(2))
                        else:
                            curr_season = season
                            if curr_season == "all":
                                curr_season = ui_season_val
                            curr_ep_num = ep_num

                    force_abs = params.get("force_absolute_season_1", False)
                    if force_abs:
                        if isinstance(ep_num, dict):
                            ep_data = ep_num
                        else:
                            ep_data = episodes.get(str(ep_num), {})
                            if not ep_data and provider == "ytdlp" and len(episodes) == 1:
                                ep_data = list(episodes.values())[0]
                        abs_num = extract_absolute_episode_number(ep_num, ep_data, basename)
                        curr_season = 1
                        curr_ep_num = abs_num

                    ep_title = sanitize_filename(ep_title)
                    ep_title = clean_episode_title_for_filename(clean_show_name, ep_title)

                    try:
                        season_str = f"S{int(curr_season):02d}"
                    except (ValueError, TypeError):
                        season_str = f"S{curr_season}"
                    try:
                        ep_str = f"E{int(curr_ep_num):02d}"
                    except (ValueError, TypeError):
                        ep_str = f"E{curr_ep_num}"

                    clean_title = f"{clean_show_name} - {season_str}{ep_str}"
                    if ep_title: clean_title += f" - {ep_title}"
                    clean_title = limit_filename_length(clean_title)

                    clean_titles.append((curr_season, clean_title))

                    target_filename = f"{clean_title}{ext}"
                    preview["renames"].append({"old": f, "new": target_filename})

                    base_old = os.path.splitext(basename)[0]
                    vid_dir = os.path.dirname(f)

                    videos_in_same_dir = [vf for vf in all_files if os.path.splitext(vf)[1].lower() in video_exts and os.path.dirname(vf) == vid_dir]
                    total_videos_in_proj = sum(1 for vf in all_files if os.path.splitext(vf)[1].lower() in video_exts)

                    matching_subs = []
                    other_companion_files = []
                    for sf in all_files:
                        if sf == f: continue
                        sbasename = os.path.basename(sf)
                        sext = os.path.splitext(sf)[1].lower()
                        sdir = os.path.dirname(sf)

                        is_match = False
                        if sbasename.startswith(base_old):
                            is_match = True
                        elif sext in sub_exts:
                            if total_videos_in_proj == 1:
                                is_match = True
                            elif len(videos_in_same_dir) == 1:
                                if is_subtitle_matching_video(sdir, vid_dir):
                                    is_match = True

                        if is_match:
                            if sext in sub_exts:
                                matching_subs.append(sf)
                            elif sext in ('.nfo', '.jpg', '.png'):
                                if sbasename.startswith(base_old):
                                    other_companion_files.append((sf, sbasename, sext))

                    matching_subs.sort()
                    local_resolved_subs = {}
                    local_used = set()
                    for sf in matching_subs:
                        rel_path_no_ext, sext = os.path.splitext(sf)
                        sext = sext.lower()
                        if rel_path_no_ext in local_resolved_subs:
                            target_basename = local_resolved_subs[rel_path_no_ext]
                        else:
                            suffix = parse_subtitle_suffix(sf)
                            base_candidate = f"{clean_title}{suffix}"
                            candidate = base_candidate
                            counter = 1
                            while candidate in local_used:
                                counter += 1
                                candidate = f"{base_candidate}.{counter}"
                            target_basename = candidate
                            local_resolved_subs[rel_path_no_ext] = target_basename
                            local_used.add(target_basename)

                        preview["subs"].append({"old": sf, "new": f"{target_basename}{sext}"})

                    for sf, sbasename, sext in other_companion_files:
                        if sext == '.nfo':
                            preview["subs"].append({"old": sf, "new": f"{clean_title}.nfo"})
                        elif sext in ('.jpg', '.png'):
                            sbase_no_ext = os.path.splitext(sbasename)[0]
                            suffix_after_base = sbase_no_ext[len(base_old):]
                            if suffix_after_base:
                                preview["subs"].append({"old": sf, "new": f"{clean_title}{suffix_after_base}{sext}"})
                            else:
                                preview["subs"].append({"old": sf, "new": f"{clean_title}{sext}"})
                else:
                    pass
            elif ext in sub_exts:
                if not is_companion_of_any_video(f):
                    preview["junk"].append(f)
            elif basename.lower() in good_meta:
                # Show-level metadata files (tvshow.nfo, poster.jpg, fanart.jpg, season.nfo) — keep as-is
                preview["subs"].append({"old": f, "new": basename})
            elif ext in ('.nfo', '.jpg', '.png', '.webp') and ('poster' in basename.lower() or 'fanart' in basename.lower() or 'backdrop' in basename.lower() or 'banner' in basename.lower() or 'logo' in basename.lower() or 'clearlogo' in basename.lower() or 'thumb' in basename.lower() or 'landscape' in basename.lower()):
                # Standalone poster/fanart/backdrop not matching any video — keep as-is
                preview["subs"].append({"old": f, "new": basename})
            else:
                preview["junk"].append(f)

        sub_olds = [x["old"] for x in preview["subs"]]
        preview["junk"] = [j for j in preview["junk"] if j not in sub_olds and j not in [r["old"] for r in preview["renames"]]]

        if params.get("copy_to_nas", True):
            if clean_titles:
                unique_paths = []
                for s, t in clean_titles:
                    try:
                        s_num = int(s)
                        p = f"{dest_show_dir}/Staffel {s_num}/{t}"
                    except (ValueError, TypeError):
                        p = f"{dest_show_dir}/{s}/{t}"
                    if p not in unique_paths:
                        unique_paths.append(p)
                if len(unique_paths) == 1:
                    dest_str = f"NAS: {unique_paths[0]}"
                else:
                    dest_str = "NAS:\n" + "\n".join(f"• {p}" for p in unique_paths)
            else:
                try:
                    s_num = int(season)
                    dest_str = f"NAS: {dest_show_dir}/Staffel {s_num}/[Episoden-Unterordner]"
                except (ValueError, TypeError):
                    dest_str = f"NAS: {dest_show_dir}/[Staffeln]/[Episoden-Unterordner]"
        else:
            dest_str = "NAS: (nicht aktiv)"

        if params.get("copy_to_pcloud", False):
            if pcloud_path:
                if clean_titles:
                    unique_pcloud_paths = []
                    for s, t in clean_titles:
                        try:
                            s_num = int(s)
                            p = f"{pcloud_path}/Staffel {s_num}/{t}"
                        except (ValueError, TypeError):
                            p = f"{pcloud_path}/{s}/{t}"
                        if p not in unique_pcloud_paths:
                            unique_pcloud_paths.append(p)
                    if len(unique_pcloud_paths) == 1:
                        dest_str += f"\n☁️ pCloud: {unique_pcloud_paths[0]}"
                    else:
                        dest_str += "\n☁️ pCloud:\n" + "\n".join(f"  • {p}" for p in unique_pcloud_paths)
                else:
                    try:
                        s_num = int(season)
                        dest_str += f"\n☁️ pCloud: {pcloud_path}/Staffel {s_num}/[Episoden-Unterordner]"
                    except (ValueError, TypeError):
                        dest_str += f"\n☁️ pCloud: {pcloud_path}/[Staffeln]/[Episoden-Unterordner]"
            else:
                dest_str += "\n☁️ pCloud: (Kein Mapping gefunden)"
        else:
            dest_str += "\n☁️ pCloud: (nicht aktiv)"

        if params.get("copy_to_nas", True) and os.path.exists(dest_show_dir):
            server_type = settings.get("media_server", "emby") or "emby"
            from gui.core.artwork_validators import get_validator
            val = get_validator(server_type)
            check_names = ["tvshow.nfo"] + val.get_series_poster_names() + val.get_series_backdrop_names()
            seen = set()
            unique_check_names = [x for x in check_names if not (x in seen or seen.add(x))]
            existing_files = [f for f in unique_check_names if os.path.exists(os.path.join(dest_show_dir, f))]
            if existing_files:
                dest_str += f"\n⚠️ Serie existiert bereits auf NAS mit vorhandenen Metadaten ({', '.join(existing_files)}). Diese Dateien werden nicht überschrieben."
        preview["destination"] = dest_str

    # Season year warning
    # NAS structure mismatch warning
    if media_type == "tv" and not params.get("force_absolute_season_1", False):
        existing_seasons = []
        show_dirs = []
        if os.path.exists(dest_show_dir):
            show_dirs.append(dest_show_dir)

        # Check outbox as well
        rel_dest = os.path.relpath(nas_serien, nas_root)
        outbox_show_dir = os.path.join(outbox_root, rel_dest, clean_show_name)
        if os.path.exists(outbox_show_dir):
            show_dirs.append(outbox_show_dir)

        for sd in show_dirs:
            try:
                for entry in os.listdir(sd):
                    if os.path.isdir(os.path.join(sd, entry)) and not entry.startswith('.'):
                        match = re.search(r'(?:staffel|season|s)\s*(\d+)', entry, re.IGNORECASE)
                        if match:
                            existing_seasons.append(int(match.group(1)))
                        else:
                            if entry.isdigit():
                                existing_seasons.append(int(entry))
            except Exception as e:
                log_message(f"⚠️ Staffelordner konnten nicht gelistet werden: {sd} ({e})")

        preview_mapped_seasons = set()
        if season and season != "all":
            try:
                preview_mapped_seasons.add(int(season))
            except (ValueError, TypeError):
                pass
        for val in mappings.values():
            if isinstance(val, dict):
                s = val.get("season")
                if s is not None:
                    try:
                        preview_mapped_seasons.add(int(s))
                    except (ValueError, TypeError):
                        pass
            elif isinstance(val, str):
                match = re.match(r"^S(\d+)", val, re.IGNORECASE)
                if match:
                    preview_mapped_seasons.add(int(match.group(1)))
            elif isinstance(val, (int, float)):
                if season and season != "all":
                    try:
                        preview_mapped_seasons.add(int(season))
                    except (ValueError, TypeError):
                        pass

        has_existing_year_seasons = any(s >= 1000 for s in existing_seasons)
        has_existing_standard_seasons = any(0 < s < 1000 for s in existing_seasons)

        has_preview_year_seasons = any(s >= 1000 for s in preview_mapped_seasons)
        has_preview_standard_seasons = any(0 < s < 1000 for s in preview_mapped_seasons)

        if has_existing_year_seasons and has_preview_standard_seasons:
            preview["warning"] = "Abweichung der Nummerierung: Auf dem NAS existieren Jahreszahl-Staffeln (z.B. Staffel 2026), aber die Vorschau ordnet die Episoden Standard-Staffeln (z.B. Staffel 1) zu! Bitte passe die Staffeln in den Episoden-Details an."
        elif has_existing_standard_seasons and has_preview_year_seasons:
            preview["warning"] = "Abweichung der Nummerierung: Auf dem NAS existieren Standard-Staffeln (z.B. Staffel 1), aber die Vorschau ordnet die Episoden Jahreszahl-Staffeln (z.B. Staffel 2026) zu! Bitte passe die Staffeln in den Episoden-Details an."
        # Check for show name mismatch with existing NAS folder (matching show ID)
        if show_id and provider:
            from gui.core.series_helper import find_existing_series_folder_by_id, resolve_series_folder_name
            nas_match_folder = find_existing_series_folder_by_id(nas_serien, provider, show_id)

            # The default name based on metadata (without ID fallback)
            outbox_serien_path = os.path.join(outbox_root, os.path.relpath(nas_serien, nas_root))
            metadata_show_name = resolve_series_folder_name(nas_serien, outbox_serien_path, None, None, show_name, log_reason=False)

            if nas_match_folder and nas_match_folder != metadata_show_name:
                preview["show_name_mismatch"] = {
                    "nas_name": nas_match_folder,
                    "metadata_name": metadata_show_name
                }

    return jsonify(preview)



@queue_api.route('/process', methods=['POST'])
def handle_api_process():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    query = request.args
    task_id = str(uuid.uuid4())
    params["task_id"] = task_id
    media_type = params.get("media_type", "unknown")

    name = params.get("project_name", "Unbekannt")
    if name.endswith("/"): name = name[:-1]
    name = os.path.basename(name)
    if media_type == "movie" and params.get("movie_name"):
        name = params.get("movie_name")
    elif media_type == "tv" and params.get("show_name"):
        name = params.get("show_name")
    elif media_type == "youtube":
        name = "YouTube Download"

    convert = params.get("convert", False)
    copy_to_nas = params.get("copy_to_nas", True)
    copy_to_pcloud = params.get("copy_to_pcloud", False)
    copy_to_local = params.get("copy_to_local", False)
    show_id = params.get("show_id")
    movie_id = params.get("movie_id")
    provider = params.get("provider")
    has_metadata = (show_id and provider) or (movie_id and provider)

    job_info = {
        "id": task_id,
        "type": media_type,
        "name": name,
        "status": "queued",
        "progress": 0,
        "message": "Wartet in der Schlange...",
        "timestamp": time.time(),
        "params": params,
        "pipeline": build_job_pipeline(params, has_metadata, convert)
    }

    from gui.core.jobs import create_job
    create_job(
        job_id=task_id,
        name=name,
        job_type=media_type,
        params=params,
        pipeline=job_info["pipeline"]
    )

    job_queue.put(job_info)

    return jsonify({"status": "started", "task_id": task_id})



@queue_api.route('/queue', methods=['GET', 'POST'])
def handle_api_queue():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}
    query = request.args
    from gui.core.jobs import get_all_jobs
    all_jobs = get_all_jobs()
    jobs_list = []
    for j in all_jobs:
        params = j.get("params") or {}
        jobs_list.append({
            "id": j.get("id", ""),
            "type": j.get("type", "unknown"),
            "name": j.get("name", ""),
            "status": j.get("status", "unknown"),
            "progress": j.get("progress", 0),
            "message": j.get("message", ""),
            "timestamp": j.get("timestamp", 0),
            "pipeline": j.get("pipeline"),
            "project_name": params.get("project_name", "")
        })
    jobs_list.sort(key=lambda x: x.get("timestamp", 0))
    return jsonify({"jobs": jobs_list})



@queue_api.route('/queue-clear', methods=['POST'])
@queue_api.route('/queue/clear', methods=['POST'])
def handle_api_queue_clear():
    try:
        params = request.get_json(silent=True) or {}
    except Exception:
        params = {}
    from gui.core.jobs import clear_finished_jobs
    clear_finished_jobs()
    return jsonify({"status": "success"})



@queue_api.route('/queue/retry', methods=['POST'])
@queue_api.route('/queue-retry', methods=['POST'])
def handle_api_queue_retry():
    try:
        params = request.get_json() or {}
    except Exception:
        params = {}

    task_id = params.get("task_id")
    if not task_id:
        return jsonify({"status": "error", "message": "Missing task_id"}), 400

    from gui.core.jobs import get_job, update_job
    job = get_job(task_id)
    if not job:
        return jsonify({"status": "error", "message": "Job nicht gefunden"}), 404

    if job.get("status") not in ("error", "done"):
        return jsonify({"status": "error", "message": "Job ist nicht fehlgeschlagen oder beendet"}), 400

    # Parameter kopieren und Pipeline neu initialisieren
    job_params = job.get("params", {})
    convert = job_params.get("convert", False)

    # Bestimme has_metadata
    show_id = job_params.get("show_id")
    movie_id = job_params.get("movie_id")
    provider = job_params.get("provider")
    has_metadata = (show_id and provider) or (movie_id and provider)

    ref_pipeline = build_job_pipeline(job_params, has_metadata, convert)
    old_pipeline = job.get("pipeline", {})
    new_pipeline = {}
    for step_key, ref_val in ref_pipeline.items():
        old_step = old_pipeline.get(step_key, {})
        if old_step.get("status") == "done":
            new_pipeline[step_key] = {
                "status": "done",
                "progress": 100
            }
        elif old_step.get("status") == "skipped":
            new_pipeline[step_key] = {
                "status": "skipped",
                "progress": 0
            }
        else:
            if ref_val.get("status") == "skipped":
                new_pipeline[step_key] = {
                    "status": "skipped",
                    "progress": 0
                }
            else:
                new_pipeline[step_key] = {
                    "status": "pending",
                    "progress": 0
                }

    # Zurücksetzen auf initialen Warteschlangen-Zustand
    update_job(
        task_id,
        status="queued",
        progress=0,
        message="Wiederholung eingereiht...",
        pipeline=new_pipeline
    )

    # In die Queue einreihen
    updated_job = get_job(task_id)
    job_queue.put(updated_job)

    return jsonify({"status": "success"})
