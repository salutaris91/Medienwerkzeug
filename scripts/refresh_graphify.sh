#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

labels_source="docs/graphify-community-labels.json"
labels_target="graphify-out/.graphify_labels.json"

if ! command -v graphify >/dev/null 2>&1; then
    echo "Error: graphify is not installed or not available in PATH." >&2
    exit 1
fi

if [[ ! -f "graphify-out/graph.json" ]]; then
    echo "Error: graphify-out/graph.json is missing. Build the local graph before refreshing exports." >&2
    exit 1
fi

graphify update .

python3 - "$labels_source" <<'PY'
import json
import sys
from pathlib import Path

labels_path = Path(sys.argv[1])
graph_path = Path("graphify-out/graph.json")

labels = json.loads(labels_path.read_text(encoding="utf-8"))
graph = json.loads(graph_path.read_text(encoding="utf-8"))

community_ids = {
    str(node["community"])
    for node in graph.get("nodes", [])
    if node.get("community") is not None
}
label_ids = set(labels)

missing = sorted(community_ids - label_ids, key=int)
extra = sorted(label_ids - community_ids, key=int)
duplicate_labels = sorted({
    label
    for label in labels.values()
    if list(labels.values()).count(label) > 1
})

if missing or extra or duplicate_labels:
    print("Error: docs/graphify-community-labels.json does not match the current graph.", file=sys.stderr)
    if missing:
        print(f"Missing community IDs: {', '.join(missing)}", file=sys.stderr)
    if extra:
        print(f"Stale community IDs: {', '.join(extra)}", file=sys.stderr)
    if duplicate_labels:
        print(f"Duplicate labels: {', '.join(duplicate_labels)}", file=sys.stderr)
    print("Update the versioned labels intentionally, then run the script again.", file=sys.stderr)
    raise SystemExit(1)
PY

cp "$labels_source" "$labels_target"
graphify export html
graphify export wiki

echo "Graphify exports refreshed with versioned community labels."
