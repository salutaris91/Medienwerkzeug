"""Ähnliche-Titel-Hinweis für Filme vor der finalen Verarbeitung.

Stufe 1 (`find_movie_folders_by_id`):
    Deterministischer TMDb-ID-Abgleich über vorhandene Film-NFOs in der
    Ziel-Kategorie (max. 2 Ebenen: `<Kategorie>/<Film>` und
    `<Kategorie>/<Genre>/<Film>`).

Stufe 2 (`find_similar_movie_folders_by_name`):
    Großzügige Namens-Heuristik rein über Ordnernamen (keine NFO-Lektüre)
    mit struktureller Wort- und Präfixregel sowie Allgemeinwort-Filter.
"""

import os
import re
import unicodedata

from gui.core.health import find_primary_nfo
from gui.core.helpers import log_message
from gui.core.nfo_helper import read_nfo_metadata

# Payload-seitige Provider-Whitelist für Stufe 1 (Fakten-Korrektur 2)
ALLOWED_MOVIE_ID_PROVIDERS = {"tmdb", "tmdb_movie"}

# NFO-seitige Provider-Label-Whitelist für Stufe 1 (Fakten-Korrektur 4 / AK19)
ALLOWED_NFO_PROVIDER_LABELS = {"tmdb", "tmdb_movie", "tmdb_tv"}

# Leicht anpassbare Liste allgemeiner Wörter, die allein keinen Treffer begründen
GENERAL_WORDS = {
    "man",
    "men",
    "woman",
    "women",
    "love",
    "night",
    "day",
    "big",
    "little",
    "new",
    "world",
    "story",
    "part",
    "teil",
}

STOP_WORDS = {
    "der",
    "die",
    "das",
    "ein",
    "eine",
    "one",
    "the",
    "a",
    "an",
    "und",
    "and",
    "of",
    "&",
}

RELEASE_TAG_TOKENS = {
    "480p",
    "720p",
    "1080p",
    "2160p",
    "x264",
    "x265",
    "bluray",
    "dvd",
    "remux",
    "proper",
    "repack",
    "extended",
    "uncut",
    "german",
    "multi",
    "dual",
}

# Einzelbuchstaben 'v' und 'x' sind bewusst NICHT enthalten, damit Titel wie
# "X-Men" ihr bedeutungstragendes Token 'x' behalten (AK12).
SEQUEL_NUMBER_TOKENS = {
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "ii",
    "iii",
    "iv",
    "vi",
    "vii",
    "viii",
    "ix",
}

_BRACKET_RE = re.compile(r"\([^()]*\)|\[[^\[\]]*\]|\{[^{}]*\}")
_RESOLUTION_TOKEN_RE = re.compile(r"^\d{3,4}[pi]$")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")

# Obergrenze für verschachtelte Klammer-Durchläufe in _clean_title_and_tokens,
# um bei pathologischen Eingaben quadratische Laufzeit O(n²) zu verhindern.
_MAX_BRACKET_DEPTH = 10


def _normalize_exclude_set(exclude) -> set[str]:
    """Normalisiert `exclude_folder` (str) bzw. `exclude_folders` (Iterable[str])."""
    if not exclude:
        return set()
    if isinstance(exclude, str):
        stripped = exclude.strip()
        return {stripped} if stripped else set()
    result = set()
    for item in exclude:
        if isinstance(item, str) and item.strip():
            result.add(item.strip())
    return result


def _iter_candidate_folders(category_root: str) -> list[tuple[str, str, str]]:
    """Liefert Kandidatenordner bis max. 2 Ebenen unterhalb von `category_root`.

    Rückgabe: Liste aus `(folder_name, relative_path, full_path)`.
    Versteckte Ordner (`.`-Präfix) werden auf beiden Ebenen übersprungen.
    """
    if not category_root or not os.path.isdir(category_root):
        return []

    try:
        level1_entries = sorted(os.listdir(category_root))
    except OSError as exc:
        log_message(f"⚠️ [Ähnliche Titel] Kategorie-Ordner nicht lesbar: {category_root} ({exc})")
        return []

    candidates: list[tuple[str, str, str]] = []
    for entry1 in level1_entries:
        if entry1.startswith("."):
            continue
        path1 = os.path.join(category_root, entry1)
        try:
            if not os.path.isdir(path1):
                continue
        except OSError as exc:
            log_message(f"⚠️ [Ähnliche Titel] Ordnerstatus nicht prüfbar: {path1} ({exc})")
            continue

        candidates.append((entry1, entry1, path1))

        try:
            level2_entries = sorted(os.listdir(path1))
        except OSError as exc:
            log_message(f"⚠️ [Ähnliche Titel] Unterordner nicht lesbar: {path1} ({exc})")
            continue

        for entry2 in level2_entries:
            if entry2.startswith("."):
                continue
            path2 = os.path.join(path1, entry2)
            try:
                if not os.path.isdir(path2):
                    continue
            except OSError as exc:
                log_message(f"⚠️ [Ähnliche Titel] Ordnerstatus nicht prüfbar: {path2} ({exc})")
                continue
            candidates.append((entry2, f"{entry1}/{entry2}", path2))

    return candidates


def _resolve_movie_nfo(folder_path: str) -> str | None:
    """Ermittelt die Film-NFO nach Fakten-Korrektur 3.

    Reihenfolge: `movie.nfo` -> `<ordnername>.nfo` -> `find_primary_nfo(..., is_movie=True)`.
    """
    folder_name = os.path.basename(folder_path)
    for candidate_name in ("movie.nfo", f"{folder_name}.nfo"):
        candidate_path = os.path.join(folder_path, candidate_name)
        if os.path.isfile(candidate_path):
            return candidate_path

    primary = find_primary_nfo(folder_path, is_movie=True)
    if primary and os.path.isfile(primary):
        return primary
    return None


def _clean_title_and_tokens(raw_title: str) -> tuple[str, set[str]]:
    """Bereinigt einen Filmtitel/Ordnernamen für Stufe 2.

    Gibt `(cleaned_title, meaningful_tokens)` zurück, wobei `meaningful_tokens`
    alle bereinigten Tokens enthält, die nicht in `GENERAL_WORDS` stehen.
    """
    if not raw_title or not isinstance(raw_title, str):
        return "", set()

    text = unicodedata.normalize("NFC", raw_title).lower()
    text = (
        text.replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )

    # Klammerinhalte (…), […], {…} iterativ von innen nach außen entfernen.
    # Die Schleife ist auf _MAX_BRACKET_DEPTH Durchläufe begrenzt, damit auch
    # tief verschachtelte oder pathologische Eingaben strikt in O(n) laufen;
    # evtl. übrig bleibende Einzelklammern entfernt anschließend _NON_ALNUM_RE.
    for _ in range(_MAX_BRACKET_DEPTH):
        updated = _BRACKET_RE.sub(" ", text)
        if updated == text:
            break
        text = updated

    text = _NON_ALNUM_RE.sub(" ", text)
    raw_tokens = text.split()

    cleaned_tokens: list[str] = []
    for token in raw_tokens:
        if token in RELEASE_TAG_TOKENS or _RESOLUTION_TOKEN_RE.match(token):
            continue
        if token in STOP_WORDS:
            continue
        if token in SEQUEL_NUMBER_TOKENS:
            continue
        cleaned_tokens.append(token)

    cleaned_title = " ".join(cleaned_tokens)
    meaningful_tokens = {tok for tok in cleaned_tokens if tok not in GENERAL_WORDS}
    return cleaned_title, meaningful_tokens


def find_movie_folders_by_id(
    category_root: str,
    provider: str | None,
    movie_id: str | int | None,
    exclude_folder: str | None = None,
) -> list[dict]:
    """Sucht Filmordner mit derselben TMDb-Film-ID in `category_root` (Stufe 1)."""
    norm_provider = str(provider or "").strip().lower()
    norm_movie_id = str(movie_id or "").strip()

    if norm_provider not in ALLOWED_MOVIE_ID_PROVIDERS or not norm_movie_id:
        log_message(
            f"ℹ️ [Ähnliche Titel] Stufe-1-ID-Abgleich übersprungen "
            f"(provider={provider!r}, movie_id={movie_id!r})."
        )
        return []

    if not category_root or not os.path.isdir(category_root):
        return []

    exclude_set = _normalize_exclude_set(exclude_folder)
    matches: list[dict] = []

    for folder_name, rel_path, full_path in _iter_candidate_folders(category_root):
        if folder_name in exclude_set or rel_path in exclude_set:
            continue

        try:
            nfo_path = _resolve_movie_nfo(full_path)
            if not nfo_path:
                continue

            meta = read_nfo_metadata(nfo_path)
            if not meta:
                log_message(f"⚠️ [Ähnliche Titel] NFO leer oder nicht lesbar: {nfo_path}")
                continue

            meta_provider = str(meta.get("mw_provider") or "").strip().lower()
            meta_id = str(meta.get("mw_showid") or "").strip()

            if not meta_provider or not meta_id:
                log_message(f"⚠️ [Ähnliche Titel] Keine gültige ID in NFO gefunden: {nfo_path}")
                continue

            if meta_provider not in ALLOWED_NFO_PROVIDER_LABELS:
                log_message(
                    f"ℹ️ [Ähnliche Titel] NFO-Provider '{meta_provider}' in '{rel_path}' "
                    f"nicht in TMDb-Whitelist, überspringe Ordner."
                )
                continue

            if meta_id == norm_movie_id:
                matches.append({"folder": folder_name, "relative_path": rel_path})
        except Exception as exc:
            log_message(f"⚠️ [Ähnliche Titel] Fehler beim Lesen der NFO in '{rel_path}': {exc}")

    matches.sort(key=lambda item: (item["folder"].lower(), item["relative_path"].lower()))
    return matches


def find_similar_movie_folders_by_name(
    category_root: str,
    movie_name: str | None,
    exclude_folders=None,
    limit: int = 10,
) -> list[dict]:
    """Sucht ähnliche Filmordner anhand der Ordnernamen-Heuristik (Stufe 2)."""
    if not category_root or not os.path.isdir(category_root) or not movie_name:
        return []

    source_clean, source_meaningful = _clean_title_and_tokens(movie_name)
    # Leer-Guard (gilt verbindlich für Wort- und Präfixregel, AK13 / plan-review B1)
    if not source_meaningful or not source_clean:
        return []

    exclude_set = _normalize_exclude_set(exclude_folders)
    matches: list[dict] = []

    for folder_name, rel_path, _full_path in _iter_candidate_folders(category_root):
        if folder_name in exclude_set or rel_path in exclude_set:
            continue

        cand_clean, cand_meaningful = _clean_title_and_tokens(folder_name)
        if not cand_meaningful or not cand_clean:
            continue

        shared_count = len(source_meaningful & cand_meaningful)
        is_prefix = source_clean.startswith(cand_clean) or cand_clean.startswith(source_clean)
        overlap = max(shared_count, 2 if is_prefix else 0)

        if overlap > 0:
            matches.append(
                {
                    "folder": folder_name,
                    "relative_path": rel_path,
                    "overlap": overlap,
                }
            )

    matches.sort(
        key=lambda item: (-item["overlap"], item["folder"].lower(), item["relative_path"].lower())
    )
    if limit is not None and limit >= 0:
        return matches[:limit]
    return matches
