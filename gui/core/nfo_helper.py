import os
import shutil
import tempfile
import time
import re
import xml.etree.ElementTree as ET
from gui.core.helpers import log_message

def update_or_insert_nfo_element(nfo_path, tag_name, inner_content, is_xml_block=False):
    """
    Updates or inserts a tag in an XML NFO file safely.
    Follows the FSK-Health-Fix pattern:
    1. Read content
    2. Validate XML
    3. Replace/insert tag using regex/string replacement (to preserve comments/formatting)
    4. Validate updated XML
    5. Backup original
    6. Write to temp file
    7. Atomic replace
    """
    if not os.path.exists(nfo_path):
        raise FileNotFoundError(f"NFO file not found: {nfo_path}")
        
    # Validate tag name to prevent XML injection / malformed tags
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9._-]*$', tag_name):
        raise ValueError(f"Ungültiger XML-Tag-Name: {tag_name}")

    try:
        with open(nfo_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        raise IOError(f"NFO lesefehler: {e}")

    try:
        tree = ET.fromstring(content)
    except Exception as e:
        raise ValueError(f"Original-XML fehlerhaft in {os.path.basename(nfo_path)}: {e}")

    root_tag = tree.tag
    if root_tag not in ["movie", "tvshow", "episodedetails"]:
        raise ValueError(f"Ungültiges NFO Root-Tag: {root_tag}")

    # Check how many occurrences of the tag exist
    elements = tree.findall(f'.//{tag_name}')
    if len(elements) > 1:
        raise ValueError(f"Mehrere <{tag_name}>-Tags gefunden. Bitte manuell bereinigen.")

    # Escape the inner content if it is not an XML block
    if not is_xml_block:
        from xml.sax.saxutils import escape
        escaped_content = escape(inner_content)
    else:
        escaped_content = inner_content

    replacement = f"<{tag_name}>{escaped_content}</{tag_name}>"

    if len(elements) == 1:
        # Replace existing tag (supports both self-closing and standard tags)
        escaped_tag = re.escape(tag_name)
        pattern = re.compile(rf'<{escaped_tag}(?:\s+[^>]*?)?/>|<{escaped_tag}[\s>].*?</{escaped_tag}>', re.DOTALL | re.IGNORECASE)
        new_content, count = re.subn(pattern, replacement, content, count=1)
        if count == 0:
            raise ValueError(f"Tag <{tag_name}> existiert laut Parser, konnte aber im XML-String nicht per Regex ersetzt werden (evtl. fehlerhaftes Format).")
    else:
        # Insert before closing tag
        closing_tag = f"</{root_tag}>"
        if closing_tag not in content:
            raise ValueError(f"NFO-Datei ist unvollständig (End-Tag {closing_tag} fehlt).")
        # Ensure we place it on a new line and format it slightly
        new_content = content.replace(closing_tag, f"  {replacement}\n{closing_tag}")

    # Validate updated XML
    try:
        ET.fromstring(new_content)
    except Exception as e:
        raise ValueError(f"Generiertes XML fehlerhaft in {os.path.basename(nfo_path)}: {e}")

    # Backup original
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak_path = f"{nfo_path}.bak.{ts}"
    suffix = 1
    while os.path.exists(bak_path):
        bak_path = f"{nfo_path}.bak.{ts}_{suffix}"
        suffix += 1
    shutil.copy2(nfo_path, bak_path)

    # Write to temp file and atomic replace
    temp_path = None
    try:
        fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(nfo_path), text=True)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(new_content)
        os.replace(temp_path, nfo_path)
        log_message(f"🔧 [NFO-Helper] Element <{tag_name}> aktualisiert in {os.path.basename(nfo_path)}")
    except Exception as e:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        raise IOError(f"Fehler beim atomaren Ersetzen der NFO: {e}")


def read_nfo_metadata(nfo_path):
    """
    Liest Metadaten aus einer NFO-Datei (tvshow.nfo) aus.
    Gibt ein Dictionary mit den Werten zurück.
    """
    if not os.path.exists(nfo_path):
        return {}
    
    try:
        with open(nfo_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        log_message(f"⚠️ [NFO-Helper] Fehler beim Lesen der Datei {nfo_path}: {e}")
        return {}

    metadata = {
        "title": None,
        "year": None,
        "plot": None,
        "mw_provider": None,
        "mw_showid": None,
        "mw_data": {}
    }

    # XML-basiertes Parsen (Tolerant/Robust)
    try:
        tree = ET.fromstring(content)
        
        # Standard-Tags
        for tag in ["title", "year", "plot", "mw_provider", "mw_showid"]:
            el = tree.find(tag)
            if el is not None:
                metadata[tag] = el.text.strip() if el.text else ""

        # Fallbacks für provider/show_id auf Root-Ebene
        if not metadata["mw_provider"] or not metadata["mw_showid"]:
            tvdb_el = tree.find("tvdbid")
            if tvdb_el is not None:
                metadata["mw_provider"] = "tvdb"
                metadata["mw_showid"] = tvdb_el.text.strip() if tvdb_el.text else ""
            else:
                tmdb_el = tree.find("tmdbid")
                if tmdb_el is not None:
                    metadata["mw_provider"] = "tmdb_tv"
                    metadata["mw_showid"] = tmdb_el.text.strip() if tmdb_el.text else ""

        # mw_data-Block auslesen
        mw_data_el = tree.find("mw_data")
        if mw_data_el is not None:
            mw_data = {}
            for subtag in ["source_url", "provider", "resolved_topic", "last_sync", "show_id"]:
                sub_el = mw_data_el.find(subtag)
                if sub_el is not None:
                    mw_data[subtag] = sub_el.text.strip() if sub_el.text else ""
            metadata["mw_data"] = mw_data

    except Exception as e:
        # Fallback auf Regex bei fehlerhaftem XML
        log_message(f"⚠️ [NFO-Helper] XML-Parsing fehlgeschlagen für {nfo_path}, nutze Regex-Fallback: {e}")
        
        m_title = re.search(r'<title>(.*?)</title>', content, re.DOTALL | re.IGNORECASE)
        m_year = re.search(r'<year>(.*?)</year>', content, re.DOTALL | re.IGNORECASE)
        m_plot = re.search(r'<plot>(.*?)</plot>', content, re.DOTALL | re.IGNORECASE)
        m_prov = re.search(r'<mw_provider>(.*?)</mw_provider>', content, re.DOTALL | re.IGNORECASE)
        m_id = re.search(r'<mw_showid>(.*?)</mw_showid>', content, re.DOTALL | re.IGNORECASE)

        metadata["title"] = m_title.group(1).strip() if m_title else None
        metadata["year"] = m_year.group(1).strip() if m_year else None
        metadata["plot"] = m_plot.group(1).strip() if m_plot else None
        metadata["mw_provider"] = m_prov.group(1).strip() if m_prov else None
        metadata["mw_showid"] = m_id.group(1).strip() if m_id else None

        # Fallbacks
        if not metadata["mw_provider"] or not metadata["mw_showid"]:
            m_tvdb = re.search(r'<tvdbid>(.*?)</tvdbid>', content, re.DOTALL | re.IGNORECASE)
            if m_tvdb:
                metadata["mw_provider"] = "tvdb"
                metadata["mw_showid"] = m_tvdb.group(1).strip()
            else:
                m_tmdb = re.search(r'<tmdbid>(.*?)</tmdbid>', content, re.DOTALL | re.IGNORECASE)
                if m_tmdb:
                    metadata["mw_provider"] = "tmdb_tv"
                    metadata["mw_showid"] = m_tmdb.group(1).strip()

        m_data_block = re.search(r'<mw_data>(.*?)</mw_data>', content, re.DOTALL | re.IGNORECASE)
        if m_data_block:
            block_content = m_data_block.group(1)
            mw_data = {}
            for subtag in ["source_url", "provider", "resolved_topic", "last_sync", "show_id"]:
                m_sub = re.search(rf'<{subtag}>(.*?)</{subtag}>', block_content, re.DOTALL | re.IGNORECASE)
                if m_sub:
                    mw_data[subtag] = m_sub.group(1).strip()
            metadata["mw_data"] = mw_data

    # Promote values from mw_data if top-level tags are missing
    if metadata.get("mw_data"):
        mw = metadata["mw_data"]
        if not metadata.get("mw_provider") and mw.get("provider"):
            metadata["mw_provider"] = mw["provider"]
        if not metadata.get("mw_showid") and (mw.get("show_id") or mw.get("source_url")):
            metadata["mw_showid"] = mw.get("show_id") or mw.get("source_url")

    return metadata


def update_nfo_mw_data(nfo_path, provider, show_id, source_url=None, resolved_topic=None):
    """
    Sicheres, XML-validiertes, atomares Schreiben/Aktualisieren des <mw_data>-Blocks in der tvshow.nfo.
    Verwendet strict XML-Validation: Bricht ab, wenn das originale oder generierte XML invalide sind.
    """
    if not os.path.exists(nfo_path):
        raise FileNotFoundError(f"NFO file not found: {nfo_path}")

    # Bei manual prüfen wir, ob sinnvolle Werte vorliegen
    if provider == "manual":
        has_url = source_url and source_url.strip() and not source_url.strip().startswith("{")
        has_topic = resolved_topic and resolved_topic.strip()
        is_id_json = show_id and (show_id.strip().startswith("{") or show_id.strip().startswith("["))
        
        # Falls keine sinnvollen Werte vorliegen, brechen wir ab (kein Fehler, einfach keine mw_data schreiben)
        if not has_url and not has_topic and (not show_id or is_id_json):
            log_message(f"ℹ️ [NFO-Helper] Überspringe mw_data-Schreiben für manual-Provider (keine sinnvollen Werte).")
            return

    # 1. Lies vorhandene Metadaten aus der NFO mit Strict-XML Validation
    try:
        with open(nfo_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        raise IOError(f"NFO lesefehler: {e}")

    try:
        # Strict validation of original XML
        tree = ET.fromstring(content)
    except Exception as e:
        raise ValueError(f"Original-XML fehlerhaft (Strict-Guard): {e}")

    # 2. Bestehende mw_data-Werte auslesen, um sie nicht zu überschreiben
    existing_mw = {}
    mw_data_el = tree.find("mw_data")
    if mw_data_el is not None:
        for subtag in ["source_url", "provider", "resolved_topic", "last_sync", "show_id"]:
            sub_el = mw_data_el.find(subtag)
            if sub_el is not None:
                existing_mw[subtag] = sub_el.text.strip() if sub_el.text else ""

    # Zusammenführen von neuen und bestehenden Werten
    final_source_url = source_url if source_url is not None else existing_mw.get("source_url")
    final_resolved_topic = resolved_topic if resolved_topic is not None else existing_mw.get("resolved_topic")
    final_show_id = show_id if show_id is not None else existing_mw.get("show_id")

    # Bug 4: Provider-Konsistenz prüfen
    old_provider = existing_mw.get("provider")
    if old_provider and old_provider != provider:
        log_message(f"⚠️ [NFO-Helper] Provider-Inkonsistenz in {os.path.basename(nfo_path)}: Alt={old_provider}, Neu={provider}. Schreibe alte Werte (Provider/ID) neu in den Block und aktualisiere nur <last_sync>.")
        provider = old_provider
        final_show_id = existing_mw.get("show_id")
        final_source_url = existing_mw.get("source_url")
        final_resolved_topic = existing_mw.get("resolved_topic")

    # Fallback-Herleitung für URLs/Topics
    if not final_source_url:
        if provider == "ytdlp":
            final_source_url = final_show_id or show_id
        elif provider == "mediathek" and final_show_id and final_show_id.startswith("http"):
            final_source_url = final_show_id
            
    if not final_resolved_topic:
        if provider == "mediathek" and final_show_id:
            if final_show_id.startswith("url_mediathek:"):
                final_resolved_topic = final_show_id.split("url_mediathek:", 1)[1]
            else:
                final_resolved_topic = final_show_id
        elif provider == "ytdlp":
            # Versuche Titel aus der NFO zu lesen
            title_el = tree.find("title")
            if title_el is not None and title_el.text:
                final_resolved_topic = title_el.text.strip()

    # Manual Provider Check für Show-ID (kein JSON erlauben)
    if provider == "manual" and final_show_id:
        if final_show_id.strip().startswith("{") or final_show_id.strip().startswith("["):
            final_show_id = None

    # 3. Baue XML Block für mw_data
    from xml.sax.saxutils import escape
    import time
    
    xml_block_content = "\n"
    xml_block_content += f"    <provider>{escape(provider)}</provider>\n"
    if final_show_id:
        xml_block_content += f"    <show_id>{escape(str(final_show_id))}</show_id>\n"
    if final_source_url:
        xml_block_content += f"    <source_url>{escape(final_source_url)}</source_url>\n"
    if final_resolved_topic:
        xml_block_content += f"    <resolved_topic>{escape(final_resolved_topic)}</resolved_topic>\n"
    xml_block_content += f"    <last_sync>{time.strftime('%Y-%m-%dT%H:%M:%S')}</last_sync>\n"
    xml_block_content += "  "

    # Nutze das bestehende update_or_insert_nfo_element für das XML-validierte Schreiben
    update_or_insert_nfo_element(nfo_path, "mw_data", xml_block_content, is_xml_block=True)
