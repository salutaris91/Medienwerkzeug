import os
from gui.core.helpers import log_message, limit_filename_length, clean_series_name_for_fs
from gui.core.nfo_helper import read_nfo_metadata

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
                        meta = read_nfo_metadata(nfo_path)
                        if meta:
                            meta_show_id = meta.get("mw_showid")
                            meta_provider = meta.get("mw_provider")

                            if meta_show_id and meta_provider:
                                if str(meta_show_id).strip() == str(show_id).strip() and str(meta_provider).strip() == str(provider).strip():
                                    return entry

                            # Fallback checks (e.g. if we search for tvdb/tmdb directly)
                            if provider == "tvdb" and str(meta_show_id).strip() == str(show_id).strip():
                                return entry
                            elif provider in ["tmdb_tv", "tmdb_tv_en"] and str(meta_show_id).strip() == str(show_id).strip():
                                return entry
                    except Exception as e:
                        log_message(f"⚠️ tvshow.nfo in '{entry}' konnte nicht gelesen werden: {e}")
    except Exception as e:
        print(f"Error scanning folders for ID match: {e}")
    return None

def resolve_series_folder_name(destination, outbox_root, provider, show_id, show_name, nas_show_folder=None, log_reason=True):
    """
    Zentrale Funktion zur Ermittlung des Serienordnernamens (Bug 2 & 3 Fix).
    Priorität:
    1. nas_show_folder (falls vom Nutzer explizit vorgegeben)
    2. ID-Match auf NAS (destination)
    3. ID-Match auf Outbox (outbox_root)
    4. Name-basiert (Fallback)
    """
    if nas_show_folder and str(nas_show_folder).strip():
        # Ensure it's safe for FS just in case, but keep user intent
        clean_user = limit_filename_length(clean_series_name_for_fs(str(nas_show_folder).strip()))
        if log_reason:
            log_message(f"📁 [Folder Resolve] Nutze expliziten NAS Show Folder: '{clean_user}'")
        return clean_user

    # ID-based Match auf Destination
    nas_match = find_existing_series_folder_by_id(destination, provider, show_id)
    if nas_match:
        if log_reason:
            log_message(f"📁 [Folder Resolve] ID-Match in NAS gefunden: '{nas_match}'")
        return nas_match

    # ID-based Match auf Outbox
    outbox_match = find_existing_series_folder_by_id(outbox_root, provider, show_id)
    if outbox_match:
        if log_reason:
            log_message(f"📁 [Folder Resolve] ID-Match in Outbox gefunden: '{outbox_match}'")
        return outbox_match

    # Fallback: fuzzy match via get_matched_series_name
    from gui.core.helpers import get_matched_series_name
    clean_name = limit_filename_length(clean_series_name_for_fs(show_name))
    fuzzy_match = get_matched_series_name(destination, outbox_root, clean_name)
    if fuzzy_match and fuzzy_match != clean_name:
        if log_reason:
            log_message(f"📁 [Folder Resolve] Fuzzy-Match gefunden: '{fuzzy_match}' (für '{clean_name}')")
        return fuzzy_match

    # Fallback: clean name
    if log_reason:
        log_message(f"📁 [Folder Resolve] Kein Match gefunden. Erstelle neuen Ordner: '{clean_name}'")
    return clean_name
