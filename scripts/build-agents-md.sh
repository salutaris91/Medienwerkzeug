#!/usr/bin/env bash
#
# build-agents-md.sh — erzeugt AGENTS.md aus CLAUDE.md.
#
# CLAUDE.md ist die kanonische Quelle für den Projektteil.
# - Wenn ein lokaler rules/-Ordner existiert (Kit-Modus):
#   Die Regeln aus rules/*.md werden (wie in build-global.sh) direkt vor
#   "## Projektspezifisch" eingefügt; CLAUDE.md braucht keine @-Imports.
# - Wenn KEIN lokaler rules/ Ordner existiert (Projekt):
#   AGENTS.md enthält nur den Projektteil. Die generischen Hausregeln liegen
#   global (build-global.sh) und werden von den Tools von dort geladen; sie
#   werden bewusst NICHT eingebettet (sonst Drift bei jedem Regel-Rollout und
#   doppelte Ladung).
#
# Aufruf:
#   scripts/build-agents-md.sh            -> baut im Kit-Root (Verzeichnis über diesem Skript)
#   scripts/build-agents-md.sh /ziel/pfad -> baut CLAUDE.md -> AGENTS.md in /ziel/pfad

set -euo pipefail

# Feste Locale für reproduzierbare Ausgabe (siehe build-index.sh): awk und
# Glob-Sortierung hängen sonst von der Umgebung ab, was zu unterschiedlichen
# Artefakten auf macOS vs. Linux-CI und damit zu Drift-Check-Fehlern führt.
export LC_ALL=C.UTF-8

# Ziel-Root: explizites Argument, sonst Verzeichnis über diesem Skript.
if [ "${1:-}" != "" ]; then
  ROOT="$(cd "$1" && pwd)"
else
  ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi
SRC="$ROOT/CLAUDE.md"
OUT="$ROOT/AGENTS.md"

if [ ! -f "$SRC" ]; then
  echo "Fehler: $SRC nicht gefunden." >&2
  exit 1
fi

# Bestimme, ob wir im Kit-Modus sind
HAS_LOCAL_RULES=0
if [ -d "$ROOT/rules" ]; then
  HAS_LOCAL_RULES=1
fi

# Skill-/MCP-Übersicht (rules/99-...) aktualisieren — nur im Kit-Kontext
INDEX_GEN="$(dirname "${BASH_SOURCE[0]}")/build-index.sh"
if [ -f "$INDEX_GEN" ] && [ -d "$ROOT/skills-src" ]; then
  bash "$INDEX_GEN" "$ROOT" >/dev/null 2>&1 || \
    echo "Hinweis: Übersicht (build-index) übersprungen." >&2
fi

TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

{
  echo "<!-- AUTOMATISCH GENERIERT aus CLAUDE.md durch scripts/build-agents-md.sh."
  if [ "$HAS_LOCAL_RULES" -eq 1 ]; then
    echo "     NICHT direkt bearbeiten — Änderungen in rules/*.md vornehmen und neu bauen. -->"
  else
    echo "     NICHT direkt bearbeiten — Projektblock in CLAUDE.md ändern und neu bauen."
    echo "     Generische Hausregeln liegen global (im Kit gepflegt: rules/, dann build-global.sh) und sind hier nicht eingebettet. -->"
  fi
  echo
} > "$TMP"

in_claude_only=0
while IFS= read -r line || [ -n "$line" ]; do
  if [[ "$line" == *"CLAUDE-ONLY-START"* ]]; then
    in_claude_only=1
    {
      echo "Diese Datei ist **generiert** aus \`CLAUDE.md\` und \`rules/\` durch"
      echo "\`scripts/build-agents-md.sh\` und enthält den Volltext aller Regeln für"
      echo "Tools ohne globale Regeldatei (Codex u. a.)."
      echo
      echo "> Nicht direkt bearbeiten. Regeln in \`rules/*.md\` ändern und neu bauen."
    } >> "$TMP"
    continue
  fi
  if [[ "$line" == *"CLAUDE-ONLY-END"* ]]; then
    in_claude_only=0
    continue
  fi
  if [ "$in_claude_only" -eq 1 ]; then
    continue
  fi

  # Kit-Modus: Regeln aus rules/*.md direkt vor ## Projektspezifisch einfügen
  # (gleiche Quelle und gleiches Format wie build-global.sh).
  if [ "$HAS_LOCAL_RULES" -eq 1 ] && [[ "$line" == "## Projektspezifisch"* ]]; then
    for rule_file in "$ROOT/rules"/*.md; do
      cat "$rule_file" >> "$TMP"
      echo >> "$TMP"
    done
    echo "---" >> "$TMP"
    echo >> "$TMP"
  fi

  if [[ "$line" =~ ^@ ]]; then
    echo "Fehler: @-Imports werden nicht mehr unterstützt (Regeln kommen aus rules/ bzw. global): $line" >&2
    exit 1
  else
    # Titelzeile anpassen: "# CLAUDE.md ..." -> "# AGENTS.md ..."
    if [[ "$line" == "# CLAUDE.md"* ]]; then
      echo "# AGENTS.md${line#\# CLAUDE.md}" >> "$TMP"
    else
      echo "$line" >> "$TMP"
    fi
  fi
done < "$SRC"

mv "$TMP" "$OUT"
trap - EXIT
chmod 644 "$OUT"
echo "AGENTS.md neu erzeugt: $OUT"

# Zweite Ausgabe für Gemini/Antigravity: derselbe Volltext unter .agents/AGENTS.md.
AGENTS_DIR="$ROOT/.agents"
mkdir -p "$AGENTS_DIR"
cp "$OUT" "$AGENTS_DIR/AGENTS.md"
chmod 644 "$AGENTS_DIR/AGENTS.md"
echo "Außerdem geschrieben: $AGENTS_DIR/AGENTS.md (für Gemini/Antigravity)"

# Größen-Wächter am Ende
MAX_BYTES="${AGENTS_MAX_BYTES:-28672}"   # 28 KiB Vorwarnung vor dem 32-KiB-Limit
BYTES="$(wc -c < "$OUT" | tr -d ' ')"
echo "Größe: ${BYTES} Bytes (Warnschwelle ${MAX_BYTES})."
if [ "$BYTES" -gt "$MAX_BYTES" ]; then
  echo "Warnung: AGENTS.md nähert sich dem Tool-Limit für Projekt-Doku" >&2
  echo "         (z. B. Codex project_doc_max_bytes ~32 KiB). Regeln kürzen oder" >&2
  echo "         komplexe Abläufe in Skills/separate Docs auslagern." >&2
fi
