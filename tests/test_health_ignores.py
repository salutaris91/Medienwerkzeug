import json
import os
from pathlib import Path

from flask import Flask

from gui.api.nas_api import nas_api
from gui.core import health, ignores


def _issue(key, group, scope_kind, scope_path, issue_type=None, **paths):
    return {
        "key": key,
        "type": issue_type or ("incomplete_nfo" if group == "metadata" else "missing_poster"),
        "group": group,
        "severity": "warning",
        "scope_kind": scope_kind,
        "scope_path": str(scope_path),
        **{name: str(value) for name, value in paths.items()},
    }


def test_legacy_migration_only_expands_colliding_strict_season_keys(tmp_path, monkeypatch):
    ignore_file = tmp_path / "ignored_findings.json"
    legacy_season = tmp_path / "Show" / "Staffel 1"
    legacy_season_2 = tmp_path / "Show" / "Season 02 (2024)"
    backup_folder = tmp_path / "Show" / "Staffel Backup"
    legacy = [
        f"health:incomplete_nfo:{legacy_season}",
        f"health:small_file:{legacy_season_2}",
        f"health:incomplete_nfo:{backup_folder}",
        "dup:stable-group",
    ]
    ignore_file.write_text(json.dumps(legacy), encoding="utf-8")
    monkeypatch.setattr(ignores, "IGNORE_FILE", str(ignore_file))

    state = ignores.get_ignore_state()

    assert state["version"] == 2
    assert state["health_rules"] == [
        {"scope_kind": "season", "scope_path": os.path.realpath(legacy_season_2), "issue_types": ["small_file"]},
        {"scope_kind": "season", "scope_path": os.path.realpath(legacy_season), "issue_types": ["incomplete_nfo"]},
    ]
    assert f"health:incomplete_nfo:{backup_folder}" in state["exact_keys"]
    assert "dup:stable-group" in state["exact_keys"]
    assert json.loads(ignore_file.read_text(encoding="utf-8"))["version"] == 2


def test_scoped_rules_match_only_the_selected_issue_types_and_media_ownership(tmp_path, monkeypatch):
    monkeypatch.setattr(ignores, "IGNORE_FILE", str(tmp_path / "ignored_findings.json"))
    series_path = tmp_path / "Show"
    season_path = series_path / "Staffel 1"
    episode_path = season_path / "S01E01.nfo"
    other_episode = season_path / "S01E02.nfo"

    assert ignores.add_health_rule("season", str(season_path), ["incomplete_nfo"])
    state = ignores.get_ignore_state()

    assert ignores.is_health_issue_ignored(_issue(
        "episode-metadata", "metadata", "episode", episode_path,
        series_path=series_path, season_path=season_path, episode_path=episode_path,
    ), state)
    # Same group, different type: an incomplete_nfo rule must not cover missing_nfo.
    assert not ignores.is_health_issue_ignored(_issue(
        "episode-missing-nfo", "metadata", "episode", episode_path, issue_type="missing_nfo",
        series_path=series_path, season_path=season_path, episode_path=episode_path,
    ), state)
    assert not ignores.is_health_issue_ignored(_issue(
        "season-artwork", "artwork", "season", season_path,
        series_path=series_path, season_path=season_path,
    ), state)
    assert not ignores.is_health_issue_ignored(_issue(
        "other-episode", "metadata", "episode", other_episode,
        series_path=tmp_path / "Other", season_path=tmp_path / "Other" / "Staffel 1", episode_path=other_episode,
    ), state)


def test_early_group_rules_expand_once_to_current_issue_types(tmp_path, monkeypatch):
    ignore_file = tmp_path / "ignored_findings.json"
    season_path = tmp_path / "Show" / "Staffel 1"
    ignore_file.write_text(json.dumps({
        "version": 2,
        "exact_keys": [],
        "health_rules": [
            {"scope_kind": "season", "scope_path": str(season_path), "groups": ["artwork"]},
        ],
    }), encoding="utf-8")
    monkeypatch.setattr(ignores, "IGNORE_FILE", str(ignore_file))

    state = ignores.get_ignore_state()

    assert len(state["health_rules"]) == 1
    rule = state["health_rules"][0]
    assert "groups" not in rule
    expected_types = sorted(ignores._expand_groups_to_issue_types(["artwork"]))
    assert rule["issue_types"] == expected_types
    assert "missing_season_poster" in rule["issue_types"]
    # The expansion is persisted so future registry additions stay visible.
    persisted = json.loads(ignore_file.read_text(encoding="utf-8"))
    assert persisted["health_rules"][0]["issue_types"] == expected_types


def test_apply_ignores_recalculates_summary_for_scoped_rules(tmp_path, monkeypatch):
    monkeypatch.setattr(ignores, "IGNORE_FILE", str(tmp_path / "ignored_findings.json"))
    series_path = tmp_path / "Show"
    season_path = series_path / "Staffel 1"
    episode_path = season_path / "S01E01.nfo"
    assert ignores.add_health_rule("series", str(series_path), ["incomplete_nfo"])
    result = {
        "issues": [
            _issue("metadata", "metadata", "episode", episode_path, series_path=series_path, season_path=season_path, episode_path=episode_path),
            _issue("artwork", "artwork", "series", series_path, series_path=series_path),
        ]
    }

    filtered = health._apply_ignores(result)

    assert [issue["key"] for issue in filtered["issues"]] == ["artwork"]
    assert filtered["ignored_count"] == 1
    assert filtered["summary"] == {"critical": 0, "warning": 1, "info": 0}


def test_apply_ignores_removes_fsk_state_from_media_structure(tmp_path, monkeypatch):
    monkeypatch.setattr(ignores, "IGNORE_FILE", str(tmp_path / "ignored_findings.json"))
    movie_path = tmp_path / "Films" / "Movie"
    movie_path.mkdir(parents=True)
    fsk_issue = _issue("movie-fsk", "metadata", "movie", movie_path)
    fsk_issue["type"] = "missing_age_rating"
    assert ignores.add_health_rule("movie", str(movie_path), ["missing_age_rating"])
    result = {
        "issues": [fsk_issue],
        "media_structure": {
            "series": [],
            "movies": [{
                "path": str(movie_path),
                "fsk_status": "missing_fsk",
                "issue_keys": ["movie-fsk"],
            }],
        },
    }

    filtered = health._apply_ignores(result)

    assert filtered["issues"] == []
    assert filtered["media_structure"]["movies"][0]["issue_keys"] == []
    assert filtered["media_structure"]["movies"][0]["fsk_status"] == "ignored"


def test_unknown_issue_types_cannot_be_ignored(tmp_path, monkeypatch):
    monkeypatch.setattr(ignores, "IGNORE_FILE", str(tmp_path / "ignored_findings.json"))
    series_path = tmp_path / "Show"
    # Unregistered types are rejected outright when saving a rule ...
    assert ignores.add_health_rule("series", str(series_path), ["future_check"]) is False
    # ... and an unknown finding stays visible even under an existing rule.
    assert ignores.add_health_rule("series", str(series_path), ["missing_poster"])
    unknown = {
        "key": "future-check",
        "type": "future_check",
        "scope_kind": "series",
        "scope_path": str(series_path),
        "series_path": str(series_path),
    }

    assert ignores.is_health_issue_ignored(unknown) is False


def test_ignore_rule_endpoint_validates_scope_types_and_library_boundary(tmp_path, monkeypatch):
    app = Flask(__name__)
    app.register_blueprint(nas_api, url_prefix="/api")
    client = app.test_client()
    library = tmp_path / "Serien"
    show = library / "Show"
    season = show / "Staffel 1"
    season.mkdir(parents=True)
    monkeypatch.setattr("gui.core.utils.get_allowed_roots", lambda check_exists=False: [os.path.realpath(library)])
    monkeypatch.setattr(ignores, "IGNORE_FILE", str(tmp_path / "ignored_findings.json"))

    response = client.post("/api/findings/ignore-rules", json={
        "scope_kind": "season", "scope_path": str(season), "issue_types": ["incomplete_nfo", "missing_season_poster"],
    })
    assert response.status_code == 200
    assert response.get_json()["ok"] is True

    invalid_type = client.post("/api/findings/ignore-rules", json={
        "scope_kind": "series", "scope_path": str(show), "issue_types": ["unknown_type"],
    })
    assert invalid_type.status_code == 400

    group_instead_of_types = client.post("/api/findings/ignore-rules", json={
        "scope_kind": "series", "scope_path": str(show), "groups": ["metadata"],
    })
    assert group_instead_of_types.status_code == 400

    invalid_season = client.post("/api/findings/ignore-rules", json={
        "scope_kind": "season", "scope_path": str(show), "issue_types": ["incomplete_nfo"],
    })
    assert invalid_season.status_code == 400

    outside = client.post("/api/findings/ignore-rules", json={
        "scope_kind": "series", "scope_path": str(tmp_path / "Outside"), "issue_types": ["incomplete_nfo"],
    })
    assert outside.status_code == 403

    restored = client.delete("/api/findings/ignored")
    assert restored.status_code == 200
    assert ignores.get_ignore_state()["health_rules"] == []
