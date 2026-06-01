#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

labels_source="docs/graphify-community-labels.labels"
labels_target="graphify-out/.graphify_labels.json"

if ! command -v graphify >/dev/null 2>&1; then
    echo "Error: graphify is not installed or not available in PATH." >&2
    exit 1
fi

if [[ ! -f "graphify-out/graph.json" ]]; then
    echo "Error: graphify-out/graph.json is missing. Build the local graph before refreshing exports." >&2
    exit 1
fi

graphify update . --force

python3 - "$labels_source" "$labels_target" <<'PY'
import json
import sys
from collections import defaultdict
from pathlib import Path

labels_path = Path(sys.argv[1])
labels_target = Path(sys.argv[2])
graph_path = Path("graphify-out/graph.json")

label_anchors = json.loads(labels_path.read_text(encoding="utf-8"))
graph = json.loads(graph_path.read_text(encoding="utf-8"))

communities = defaultdict(set)
all_community_ids = set()
for node in graph.get("nodes", []):
    community = node.get("community")
    if community is None:
        continue
    community = str(community)
    all_community_ids.add(community)
    communities[str(node.get("id", ""))].add(community)
    communities[str(node.get("label", ""))].add(community)

resolved_labels = {}
errors = []
for label, anchors in label_anchors.items():
    anchor_communities = set()
    for anchor in anchors:
        matches = communities.get(anchor, set())
        if not matches:
            errors.append(f"Anchor not found for '{label}': {anchor}")
        anchor_communities.update(matches)
    if len(anchor_communities) != 1:
        errors.append(f"Anchors for '{label}' resolve to communities: {sorted(anchor_communities)}")
        continue
    community = next(iter(anchor_communities))
    if community in resolved_labels:
        errors.append(
            f"Community {community} has multiple labels: "
            f"'{resolved_labels[community]}' and '{label}'"
        )
        continue
    resolved_labels[community] = label

unlabeled = sorted(all_community_ids - set(resolved_labels), key=int)
if unlabeled:
    errors.append(f"Unlabeled community IDs: {', '.join(unlabeled)}")

if errors:
    print("Error: versioned Graphify labels need attention.", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    print("Update docs/graphify-community-labels.labels intentionally, then run the script again.", file=sys.stderr)
    raise SystemExit(1)

labels_target.write_text(
    json.dumps(resolved_labels, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
PY

graphify export html
graphify export wiki

echo "Graphify exports refreshed with versioned community labels."
