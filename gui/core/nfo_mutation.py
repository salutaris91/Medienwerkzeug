"""Safe, field-scoped mutations for existing Kodi-compatible NFO files."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import stat
import tempfile
import time
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape


SUPPORTED_ROOTS = {"movie", "tvshow", "episodedetails"}
SINGLE_VALUE_TAGS = {
    "title": "title",
    "year": "year",
    "plot": "plot",
    "fsk": "mpaa",
}


class NfoConflictError(RuntimeError):
    """Raised when an NFO changed after its preview was created."""


def make_nfo_fingerprint(nfo_path: str) -> dict | None:
    """Return a content fingerprint, or ``None`` when the file is absent."""
    if not os.path.exists(nfo_path):
        return None
    stat_result = os.stat(nfo_path)
    with open(nfo_path, "rb") as nfo_file:
        digest = hashlib.sha256(nfo_file.read()).hexdigest()
    return {
        "path": os.path.realpath(nfo_path),
        "mtime_ns": str(stat_result.st_mtime_ns),
        "size": stat_result.st_size,
        "hash": digest,
    }


def assert_nfo_fingerprint(nfo_path: str, expected: dict | None) -> None:
    """Reject creation or mutation when the preview snapshot is stale."""
    current = make_nfo_fingerprint(nfo_path)
    if expected is None:
        if current is not None:
            raise NfoConflictError(
                f"{os.path.basename(nfo_path)} wurde seit der Vorschau neu angelegt."
            )
        return
    if current is None:
        raise NfoConflictError(
            f"{os.path.basename(nfo_path)} fehlt seit der Vorschau."
        )
    if (
        current["path"] != os.path.realpath(expected.get("path", ""))
        or current["size"] != expected.get("size")
        or current["hash"] != expected.get("hash")
    ):
        raise NfoConflictError(
            f"{os.path.basename(nfo_path)} wurde seit der Vorschau verändert."
        )


def normalize_fsk(value) -> str:
    """Normalize a supported German age rating to Kodi's ``FSK N`` value."""
    text = str(value or "").strip()
    match = re.fullmatch(r"(?:FSK\s*)?(0|6|12|16|18)\+?", text, re.IGNORECASE)
    return f"FSK {match.group(1)}" if match else ""


def _detect_xml_encoding(content: bytes) -> str:
    """Return the declared byte encoding without rewriting the XML declaration."""
    if content.startswith((b"\xff\xfe", b"\xfe\xff", b"\xff\xfe\x00\x00", b"\x00\x00\xfe\xff")):
        raise ValueError("UTF-16/UTF-32-NFOs können nicht bytegenau ergänzt werden.")
    declaration = re.match(
        rb"(?:\xef\xbb\xbf)?\s*<\?xml\s+[^>]*encoding=[\"'](?P<encoding>[^\"']+)[\"']",
        content,
        re.IGNORECASE,
    )
    return declaration.group("encoding").decode("ascii") if declaration else "utf-8"


def _encode_xml_text(value: str, encoding: str) -> bytes:
    try:
        return escape(str(value)).encode(encoding)
    except (LookupError, UnicodeEncodeError) as error:
        raise ValueError(
            f"Wert kann nicht in der vorhandenen XML-Kodierung {encoding} gespeichert werden."
        ) from error


def _replace_or_insert_single(
    content: bytes,
    root_tag: str,
    tag: str,
    value: str,
    encoding: str,
) -> bytes:
    pattern = re.compile(
        rb"(?P<open><" + tag.encode("ascii") + rb"(?:\s[^>]*)?>)"
        rb"(?P<value>.*?)"
        rb"(?P<close></" + tag.encode("ascii") + rb"\s*>)",
        re.DOTALL | re.IGNORECASE,
    )
    matches = list(pattern.finditer(content))
    if len(matches) > 1:
        raise ValueError(f"Mehrere <{tag}>-Tags gefunden. Bitte manuell bereinigen.")

    escaped_value = _encode_xml_text(value, encoding)
    if matches:
        return pattern.sub(
            lambda match: match.group("open") + escaped_value + match.group("close"),
            content,
            count=1,
        )

    closing_tag = f"</{root_tag}>".encode("utf-8")
    insertion_index = content.rfind(closing_tag)
    if insertion_index == -1:
        raise ValueError(f"NFO-Datei ist unvollständig (End-Tag </{root_tag}> fehlt).")
    new_tag = b"  <" + tag.encode("ascii") + b">" + escaped_value
    new_tag += b"</" + tag.encode("ascii") + b">\n"
    return content[:insertion_index] + new_tag + content[insertion_index:]


def _replace_or_insert_genres(content: bytes, root_tag: str, genres, encoding: str) -> bytes:
    if isinstance(genres, str):
        values = [part.strip() for part in re.split(r"[,;]", genres) if part.strip()]
    else:
        values = [str(part).strip() for part in (genres or []) if str(part).strip()]
    if not values:
        return content

    pattern = re.compile(rb"[ \t]*<genre(?:\s[^>]*)?>.*?</genre\s*>\r?\n?", re.DOTALL | re.IGNORECASE)
    matches = list(pattern.finditer(content))
    replacement = b"".join(
        b"  <genre>" + _encode_xml_text(value, encoding) + b"</genre>\n"
        for value in values
    )
    if matches:
        start = matches[0].start()
        end = matches[-1].end()
        return content[:start] + replacement + content[end:]

    closing_tag = f"</{root_tag}>".encode("utf-8")
    insertion_index = content.rfind(closing_tag)
    if insertion_index == -1:
        raise ValueError(f"NFO-Datei ist unvollständig (End-Tag </{root_tag}> fehlt).")
    return content[:insertion_index] + replacement + content[insertion_index:]


def patch_nfo_fields(
    nfo_path: str,
    fields: dict,
    *,
    expected_fingerprint: dict | None | object = ...,
    create_backup: bool = True,
) -> tuple[bool, str]:
    """Patch only non-empty selected fields and preserve all unrelated bytes."""
    if expected_fingerprint is not ...:
        assert_nfo_fingerprint(nfo_path, expected_fingerprint)

    try:
        with open(nfo_path, "rb") as nfo_file:
            original = nfo_file.read()
    except OSError as error:
        return False, f"NFO Lesefehler: {error}"

    try:
        root = ET.fromstring(original)
    except ET.ParseError as error:
        return False, f"Original-XML fehlerhaft: {error}"
    root_tag = root.tag.split("}")[-1]
    if root_tag not in SUPPORTED_ROOTS:
        return False, f"Ungültiges NFO Root-Tag: {root.tag}"
    if any("}" in element.tag for element in root.iter()):
        return False, "XML-Namespaces werden für sichere NFO-Patches nicht unterstützt."
    try:
        xml_encoding = _detect_xml_encoding(original)
    except ValueError as error:
        return False, f"NFO-Patch abgebrochen: {error}"

    selected = {}
    for field, value in (fields or {}).items():
        if field == "fsk":
            value = normalize_fsk(value)
        if field == "genres":
            if value:
                selected[field] = value
        elif field in SINGLE_VALUE_TAGS and str(value or "").strip():
            selected[field] = str(value).strip()
    if not selected:
        return True, "Keine ausgewählten Metadaten geändert."

    updated = original
    try:
        for field in ("title", "year", "plot", "fsk"):
            if field in selected:
                updated = _replace_or_insert_single(
                    updated,
                    root_tag,
                    SINGLE_VALUE_TAGS[field],
                    selected[field],
                    xml_encoding,
                )
        if "genres" in selected:
            updated = _replace_or_insert_genres(
                updated, root_tag, selected["genres"], xml_encoding
            )
        ET.fromstring(updated)
    except (ValueError, ET.ParseError) as error:
        return False, f"NFO-Patch abgebrochen: {error}"

    if updated == original:
        return True, "NFO war bereits unverändert."

    temp_path = None
    try:
        original_mode = stat.S_IMODE(os.stat(nfo_path).st_mode)
        if create_backup:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            backup_path = f"{nfo_path}.bak.{timestamp}"
            suffix = 1
            while os.path.exists(backup_path):
                backup_path = f"{nfo_path}.bak.{timestamp}_{suffix}"
                suffix += 1
            shutil.copy2(nfo_path, backup_path)

        descriptor, temp_path = tempfile.mkstemp(dir=os.path.dirname(nfo_path), text=False)
        with os.fdopen(descriptor, "wb") as temp_file:
            temp_file.write(updated)
        os.chmod(temp_path, original_mode)
        os.replace(temp_path, nfo_path)
        temp_path = None
        return True, "NFO-Metadaten erfolgreich aktualisiert."
    except OSError as error:
        return False, f"Fehler beim Speichern: {error}"
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass
