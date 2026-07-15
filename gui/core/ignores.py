"""Persisted ignore rules for Health findings and duplicate groups.

Version 2 keeps legacy exact keys for backwards compatibility and adds scoped
Health rules. A scoped rule is based on the registry group plus canonical media
ownership, so new findings do not need ad-hoc UI wiring.
"""

import json
import os
import threading

from gui.core import utils
from gui.core.health_issue_registry import HEALTH_ISSUE_GROUPS, get_issue_definition
from gui.core.helpers import is_season_folder_name, log_message


IGNORE_FILE = os.path.join(utils.DATA_DIR, "ignored_findings.json")
IGNORE_SCHEMA_VERSION = 2
ALLOWED_SCOPE_KINDS = {"movie", "series", "season", "episode"}
_lock = threading.Lock()


def _empty_state():
    return {"version": IGNORE_SCHEMA_VERSION, "exact_keys": [], "health_rules": []}


def _normalize_rule(rule):
    if not isinstance(rule, dict):
        return None
    scope_kind = str(rule.get("scope_kind", "")).strip()
    scope_path = str(rule.get("scope_path", "")).strip()
    groups = sorted({group for group in rule.get("groups", []) if group in HEALTH_ISSUE_GROUPS})
    if scope_kind not in ALLOWED_SCOPE_KINDS or not scope_path or not groups:
        return None
    return {
        "scope_kind": scope_kind,
        "scope_path": os.path.realpath(scope_path),
        "groups": groups,
    }


def _migrate_legacy_list(keys):
    state = _empty_state()
    rules_by_scope = {}
    for key in keys:
        if not isinstance(key, str) or not key:
            continue
        migrated = False
        for issue_type in ("incomplete_nfo", "small_file"):
            prefix = f"health:{issue_type}:"
            if not key.startswith(prefix):
                continue
            legacy_path = os.path.realpath(key[len(prefix):])
            if is_season_folder_name(os.path.basename(os.path.normpath(legacy_path))):
                scope_key = ("season", legacy_path)
                rules_by_scope.setdefault(scope_key, set()).add(get_issue_definition(issue_type)["group"])
                migrated = True
            break
        if not migrated:
            state["exact_keys"].append(key)

    state["exact_keys"] = sorted(set(state["exact_keys"]))
    state["health_rules"] = [
        {"scope_kind": scope_kind, "scope_path": scope_path, "groups": sorted(groups)}
        for (scope_kind, scope_path), groups in sorted(rules_by_scope.items())
    ]
    return state


def _normalize_state(data):
    if isinstance(data, list):
        return _migrate_legacy_list(data), True
    if not isinstance(data, dict):
        return _empty_state(), False
    state = _empty_state()
    state["exact_keys"] = sorted({key for key in data.get("exact_keys", []) if isinstance(key, str) and key})
    state["health_rules"] = [rule for rule in (_normalize_rule(item) for item in data.get("health_rules", [])) if rule]
    return state, data.get("version") != IGNORE_SCHEMA_VERSION


def _load_state():
    try:
        if os.path.exists(IGNORE_FILE):
            with open(IGNORE_FILE, "r", encoding="utf-8") as file_handle:
                state, migrated = _normalize_state(json.load(file_handle))
            if migrated:
                _save_state(state)
            return state
    except Exception as exc:
        log_message(f"⚠️ Ignorier-Regeln konnten nicht gelesen werden: {IGNORE_FILE} ({exc})")
    return _empty_state()


def _save_state(state):
    try:
        os.makedirs(os.path.dirname(IGNORE_FILE), exist_ok=True)
        temp_path = f"{IGNORE_FILE}.tmp"
        with open(temp_path, "w", encoding="utf-8") as file_handle:
            json.dump(state, file_handle, ensure_ascii=False, indent=2, sort_keys=True)
        os.replace(temp_path, IGNORE_FILE)
        return True
    except Exception as exc:
        log_message(f"⚠️ Ignorier-Regeln konnten nicht gespeichert werden: {IGNORE_FILE} ({exc})")
        return False


def get_ignore_state():
    with _lock:
        return _load_state()


def get_ignored():
    """Return legacy exact keys used by duplicate filtering and old clients."""
    return set(get_ignore_state()["exact_keys"])


def add_ignore(key):
    if not key:
        return False
    with _lock:
        state = _load_state()
        state["exact_keys"] = sorted(set(state["exact_keys"]) | {key})
        return _save_state(state)


def remove_ignore(key):
    if not key:
        return False
    with _lock:
        state = _load_state()
        state["exact_keys"] = [item for item in state["exact_keys"] if item != key]
        return _save_state(state)


def add_health_rule(scope_kind, scope_path, groups):
    normalized = _normalize_rule({"scope_kind": scope_kind, "scope_path": scope_path, "groups": groups})
    if normalized is None:
        return False
    with _lock:
        state = _load_state()
        merged = False
        for rule in state["health_rules"]:
            if rule["scope_kind"] == normalized["scope_kind"] and rule["scope_path"] == normalized["scope_path"]:
                rule["groups"] = sorted(set(rule["groups"]) | set(normalized["groups"]))
                merged = True
                break
        if not merged:
            state["health_rules"].append(normalized)
        return _save_state(state)


def clear_all():
    with _lock:
        return _save_state(_empty_state())


def _issue_belongs_to_rule(issue, rule):
    scope_kind = rule["scope_kind"]
    scope_path = rule["scope_path"]
    if scope_kind == "series":
        candidate = issue.get("series_path")
        if not candidate and issue.get("scope_kind") == "series":
            candidate = issue.get("scope_path")
    elif scope_kind == "season":
        candidate = issue.get("season_path")
        if not candidate and issue.get("scope_kind") == "season":
            candidate = issue.get("scope_path")
    elif scope_kind == "episode":
        candidate = issue.get("episode_path")
        if not candidate and issue.get("scope_kind") == "episode":
            candidate = issue.get("scope_path")
    else:
        candidate = issue.get("scope_path") if issue.get("scope_kind") == "movie" else None
    return bool(candidate and os.path.realpath(candidate) == scope_path)


def is_health_issue_ignored(issue, state=None):
    state = state or get_ignore_state()
    if issue.get("key") in set(state["exact_keys"]):
        return True
    definition = get_issue_definition(issue.get("type", ""))
    if issue.get("ignoreable", definition["ignoreable"]) is False:
        return False
    group = issue.get("group") or definition["group"]
    return any(group in rule["groups"] and _issue_belongs_to_rule(issue, rule) for rule in state["health_rules"])
