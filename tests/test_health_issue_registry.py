import ast
from pathlib import Path

from gui.core.health_issue_registry import (
    HEALTH_ISSUE_TYPES,
    get_issue_definition,
    validate_registry,
)


def _literal_issue_types_from_health_module():
    source_path = Path(__file__).parents[1] / "gui" / "core" / "health.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    issue_types = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "_add_issue":
            continue
        if len(node.args) < 3 or not isinstance(node.args[2], ast.Constant):
            continue
        if isinstance(node.args[2].value, str):
            issue_types.add(node.args[2].value)
    return issue_types


def test_health_issue_registry_is_complete():
    assert validate_registry() == []


def test_every_literal_scanner_issue_type_is_registered():
    emitted_types = _literal_issue_types_from_health_module()
    assert emitted_types
    assert emitted_types <= set(HEALTH_ISSUE_TYPES)


def test_unknown_issue_type_has_visible_non_ignoreable_fallback():
    definition = get_issue_definition("future_health_problem")
    assert definition["group"] == "other"
    assert definition["ignoreable"] is False
    assert "future_health_problem" in definition["label"]
