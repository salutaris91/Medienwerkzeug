"""Central catalog for health findings.

Stable issue codes are the contract between scanner, API, UI and ignore rules.
User-facing labels and grouping must be derived from this registry instead of
being duplicated in individual consumers.
"""

from copy import deepcopy


HEALTH_ISSUE_GROUPS = {
    "metadata": {"label": "Metadaten", "order": 10},
    "artwork": {"label": "Artwork", "order": 20},
    "files": {"label": "Dateien", "order": 30},
    "structure": {"label": "Struktur", "order": 40},
    "other": {"label": "Weitere Hinweise", "order": 90},
}


def _issue(label, group, scopes, description, remediation="manual", ignoreable=True):
    return {
        "label": label,
        "group": group,
        "allowed_scopes": list(scopes),
        "description": description,
        "remediation": remediation,
        "ignoreable": ignoreable,
    }


HEALTH_ISSUE_TYPES = {
    "missing_age_rating": _issue(
        "Fehlende Altersfreigabe", "metadata", ("movie", "series", "season", "episode"),
        "In der NFO ist keine gültige Altersfreigabe hinterlegt.", "metadata_editor",
    ),
    "invalid_age_rating": _issue(
        "Ungültige Altersfreigabe", "metadata", ("movie", "series", "season", "episode"),
        "Die Altersfreigabe in der NFO entspricht keiner unterstützten FSK-Stufe.", "metadata_editor",
    ),
    "missing_nfo": _issue(
        "Fehlende Metadaten", "metadata", ("movie", "series", "episode"),
        "Für das Medium wurde keine passende NFO-Datei gefunden.", "metadata_editor",
    ),
    "unreadable_nfo": _issue(
        "NFO unlesbar", "metadata", ("movie", "series", "season", "episode"),
        "Die vorhandene NFO-Datei konnte nicht sicher gelesen werden.", "metadata_editor",
    ),
    "incomplete_nfo": _issue(
        "Metadaten unvollständig", "metadata", ("movie", "series", "episode"),
        "Mindestens ein erwartetes Metadatenfeld fehlt oder ist leer.", "metadata_editor",
    ),
    "missing_poster": _issue(
        "Fehlendes Poster / Primärbild", "artwork", ("movie", "series"),
        "Es wurde kein passendes Poster gefunden.",
    ),
    "missing_backdrop": _issue(
        "Fehlendes Hintergrundbild / Backdrop", "artwork", ("movie", "series"),
        "Es wurde kein passendes Hintergrundbild gefunden.",
    ),
    "missing_logo": _issue(
        "Fehlendes Logo / Clearlogo", "artwork", ("movie", "series"),
        "Es wurde kein passendes Logo gefunden.",
    ),
    "missing_banner": _issue(
        "Fehlendes Banner", "artwork", ("movie", "series"),
        "Es wurde kein passendes Banner gefunden.",
    ),
    "missing_season_poster": _issue(
        "Fehlendes Staffelposter", "artwork", ("season",),
        "Für die Staffel wurde kein passendes Staffelposter gefunden.",
    ),
    "small_file": _issue(
        "Verdächtig kleine Videodatei", "files", ("movie", "episode"),
        "Die Videodatei liegt unterhalb der konfigurierten Mindestgröße.",
    ),
    "no_video": _issue(
        "Keine Videodatei im Ordner", "files", ("movie", "episode"),
        "Im erwarteten Medienordner wurde keine Videodatei gefunden.",
    ),
    "empty_folder": _issue(
        "Leerer Ordner", "files", ("movie", "series", "season", "episode"),
        "Der Medienordner enthält keine verwertbaren Dateien.",
    ),
    "codec_inconsistency": _issue(
        "Uneinheitliche Codecs in Staffel", "files", ("season",),
        "Die geprüften Episoden verwenden unterschiedliche Video-Codecs.",
    ),
    "episode_gap": _issue(
        "Episodenlücke in Staffel", "structure", ("season",),
        "In der erkannten Episodenfolge fehlt mindestens eine Nummer.",
    ),
    "nested_duplicate": _issue(
        "Doppelte Ordnerstruktur", "structure", ("movie", "series"),
        "Ein Medienordner ist unnötig in einem gleichnamigen Ordner verschachtelt.",
    ),
    "genre_container": _issue(
        "Sammelordner", "structure", ("movie",),
        "Ein Ordner wurde als Genre- oder Sammelcontainer erkannt.",
    ),
    "bad_folder_name": _issue(
        "Ungültiger Ordnername", "structure", ("movie", "series"),
        "Der Ordnername entspricht nicht dem erwarteten Namensschema.",
    ),
    "name_mismatch": _issue(
        "Namensabweichung (Ordner vs. Datei)", "structure", ("movie",),
        "Ordner- und Mediendateiname passen nicht zusammen.",
    ),
    "inconsistent_naming": _issue(
        "Uneinheitliche Benennung in Serie", "structure", ("series",),
        "Episodendateien verwenden uneinheitliche Seriennamen.",
    ),
}


def get_issue_definition(issue_type):
    """Return a copy of a registered definition or a visible safe fallback."""
    definition = HEALTH_ISSUE_TYPES.get(issue_type)
    if definition is not None:
        return deepcopy(definition)
    return {
        "label": f"Unbekannter Hinweis: {issue_type}",
        "group": "other",
        "allowed_scopes": ["movie", "series", "season", "episode"],
        "description": "Dieser Hinweis ist noch nicht im Health-Katalog registriert.",
        "remediation": "manual",
        "ignoreable": False,
        "unknown": True,
    }


def get_issue_catalog():
    return {
        "groups": deepcopy(HEALTH_ISSUE_GROUPS),
        "types": {code: get_issue_definition(code) for code in HEALTH_ISSUE_TYPES},
    }


def validate_registry():
    """Return validation errors so tests and preflight code can fail loudly."""
    errors = []
    required = {"label", "group", "allowed_scopes", "description", "remediation", "ignoreable"}
    for code, definition in HEALTH_ISSUE_TYPES.items():
        missing = required - set(definition)
        if missing:
            errors.append(f"{code}: missing {', '.join(sorted(missing))}")
        if definition.get("group") not in HEALTH_ISSUE_GROUPS:
            errors.append(f"{code}: unknown group {definition.get('group')}")
        if not definition.get("allowed_scopes"):
            errors.append(f"{code}: no allowed scopes")
    return errors
