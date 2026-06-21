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
        
    try:
        with open(nfo_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        raise IOError(f"NFO lesefehler: {e}")

    try:
        tree = ET.fromstring(content)
    except Exception as e:
        raise ValueError(f"Original-XML fehlerhaft: {e}")

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
        # Replace existing tag
        pattern = re.compile(rf'<{tag_name}[\s>].*?</{tag_name}>', re.DOTALL | re.IGNORECASE)
        new_content = re.sub(pattern, replacement, content, count=1)
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
        raise ValueError(f"Generiertes XML fehlerhaft: {e}")

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
