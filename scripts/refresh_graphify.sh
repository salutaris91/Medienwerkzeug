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
warnings = []

for label, anchors in label_anchors.items():
    anchor_communities = []
    for anchor in anchors:
        matches = communities.get(anchor, set())
        if not matches:
            warnings.append(f"Anchor not found for '{label}': {anchor}")
        anchor_communities.extend(matches)
    
    if not anchor_communities:
        continue
    
    from collections import Counter
    community = Counter(anchor_communities).most_common(1)[0][0]
    
    if community in resolved_labels:
        resolved_labels[community] = f"{resolved_labels[community]} & {label}"
    else:
        resolved_labels[community] = label

unlabeled = sorted(all_community_ids - set(resolved_labels), key=int)
for uc in unlabeled:
    nodes_in_uc = []
    for node in graph.get("nodes", []):
        if str(node.get("community")) == uc:
            lbl = node.get("label") or node.get("id")
            if lbl:
                nodes_in_uc.append(lbl)
    
    short_names = []
    for name in nodes_in_uc:
        short = name.split("/")[-1].split("\\")[-1]
        if short not in short_names:
            short_names.append(short)
            
    preview = ", ".join(short_names[:3])
    resolved_labels[uc] = f"Community {uc} ({preview})"

if warnings:
    print("Warnings during label resolution:", file=sys.stderr)
    for warning in warnings:
        print(f"- {warning}", file=sys.stderr)

labels_target.write_text(
    json.dumps(resolved_labels, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
PY

graphify export html
graphify export wiki

echo "Graphify exports refreshed with versioned community labels."
