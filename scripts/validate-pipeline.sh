#!/usr/bin/env bash
#
# validate-pipeline.sh — Validiert die Einrichtung der Agenten-Pipeline im Projekt.
#
# Aufruf:
#   scripts/validate-pipeline.sh [projekt_pfad]
#

set -euo pipefail

ROOT="${1:-}"
if [ -z "$ROOT" ]; then
  # Ermittle Root-Pfad relativ zum Skript-Speicherort (zwei Ebenen hoch)
  ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi

echo "=== Pipeline-Validierung für: $ROOT ==="
echo

ERRORS=0
IS_KIT=0
if [ "$(basename "$ROOT")" = "ai-coding-starter-kit" ]; then
  IS_KIT=1
  echo "  (Führe Validierung im Starter-Kit-Modus aus)"
fi

# Helper: print status
status_ok() {
  echo -e "  [\033[0;32mOK\033[0m] $1"
}

status_warn() {
  echo -e "  [\033[0;33mWARN\033[0m] $1"
}

status_err() {
  echo -e "  [\033[0;31mFAIL\033[0m] $1"
  ERRORS=$((ERRORS + 1))
}

# 1. Check project rules and files
echo "1. Dateipflichtprüfungen:"
# Im Kit prüfen wir nur CLAUDE.md und AGENTS.md, da STAND/VERLAUF/Briefing dort nur Templates sind.
declare -a required_files
if [ "$IS_KIT" -eq 1 ]; then
  required_files=(CLAUDE.md AGENTS.md)
else
  required_files=(CLAUDE.md AGENTS.md .agents/AGENTS.md STAND.md VERLAUF.md)
fi

for f in "${required_files[@]}"; do
  if [ -f "$ROOT/$f" ]; then
    status_ok "$f existiert."
  else
    status_err "$f fehlt."
  fi
done

if [ "$IS_KIT" -eq 0 ]; then
  if [ -f "$ROOT/FEATURE_BRIEFING.md" ] || [ -f "$ROOT/docs/alexandria/FEATURE_BRIEFING.md" ]; then
    status_ok "FEATURE_BRIEFING.md existiert."
  else
    status_warn "FEATURE_BRIEFING.md oder docs/alexandria/FEATURE_BRIEFING.md fehlt."
  fi

  # OpenCode Reviewer Capability Check
  HAS_OPENCODE_KEY=0
  HAS_OPENCODE_MODEL=0
  if [ -f "$ROOT/.env" ]; then
    KEY_VAL=$(grep -E '^[[:space:]]*OPENCODE_API_KEY=' "$ROOT/.env" | head -n 1 | cut -d'=' -f2- | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//" || true)
    if [ -n "$KEY_VAL" ] && [ "$KEY_VAL" != "your_opencode_api_key_here" ]; then HAS_OPENCODE_KEY=1; fi

    MOD_VAL=$(grep -E '^[[:space:]]*OPENCODE_MODEL=' "$ROOT/.env" | head -n 1 | cut -d'=' -f2- | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//" || true)
    if [ -n "$MOD_VAL" ] && [ "$MOD_VAL" != "your_opencode_model_here" ]; then HAS_OPENCODE_MODEL=1; fi
  fi

  if [ "$HAS_OPENCODE_KEY" -eq 1 ] || [ "$HAS_OPENCODE_MODEL" -eq 1 ]; then
    if [ "$HAS_OPENCODE_KEY" -eq 1 ] && [ "$HAS_OPENCODE_MODEL" -eq 1 ]; then
      if [ -f "$ROOT/scripts/opencode-reviewer.sh" ]; then
        status_ok "OpenCode Capability erkannt und scripts/opencode-reviewer.sh existiert."
      else
        status_err "OpenCode Capability erkannt, aber scripts/opencode-reviewer.sh FEHLT."
      fi
    else
      if [ "$HAS_OPENCODE_KEY" -eq 1 ]; then
        status_err "Unvollständige OpenCode Konfiguration: OPENCODE_API_KEY ist gesetzt, aber OPENCODE_MODEL fehlt in .env"
      else
        status_err "Unvollständige OpenCode Konfiguration: OPENCODE_MODEL ist gesetzt, aber OPENCODE_API_KEY fehlt in .env"
      fi
      if [ ! -f "$ROOT/scripts/opencode-reviewer.sh" ]; then
        status_err "Zusätzlich FEHLT scripts/opencode-reviewer.sh"
      fi
    fi
  else
    status_ok "Keine OpenCode Capability in .env konfiguriert (Info)."
  fi
fi

# 2. Check .gitignore
echo
echo "2. Gitignore-Sicherheitsprüfungen:"
if [ "$IS_KIT" -eq 1 ]; then
  status_ok "Starter-Kit benötigt keine .gitignore-Validierung für Secrets."
else
  if [ -d "$ROOT/.git" ]; then
    for entry in "STAND.md" ".env" ".env.local" ".mcp.json"; do
      if (cd "$ROOT" && git check-ignore -q "$entry" 2>/dev/null); then
        status_ok "'$entry' wird korrekt ignoriert."
      else
        status_err "'$entry' wird NICHT ignoriert!"
      fi
    done
  else
    GI="$ROOT/.gitignore"
    if [ -f "$GI" ]; then
      for entry in "STAND.md" ".env" ".env.local" ".mcp.json"; do
        if grep -q "$entry" "$GI"; then
          status_ok ".gitignore enthält Muster für '$entry'."
        else
          status_err ".gitignore fehlt Eintrag für '$entry'!"
        fi
      done
    else
      status_err ".gitignore fehlt völlig!"
    fi
  fi
fi

# 3. Check Secrets / .env
echo
echo "3. Secrets & Tokens Prüfungen:"
if [ "$IS_KIT" -eq 1 ]; then
  status_ok "Starter-Kit benötigt keine .env Secrets."
else
  ENV_FILE="$ROOT/.env"
  ENV_EX="$ROOT/.env.example"

  if [ -f "$ENV_EX" ]; then
    status_ok ".env.example existiert."
    if [ -f "$ENV_FILE" ]; then
      status_ok ".env existiert."
      # Keys aus .env.example lesen (alles vor = und ohne Kommentare)
      while IFS= read -r line || [ -n "$line" ]; do
        # Überspringe Leerzeilen und Kommentare
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "${line// /}" ]] && continue

        key="${line%%=*}"
        if grep -q "^$key=" "$ENV_FILE"; then
          val="$(grep "^$key=" "$ENV_FILE" | cut -d'=' -f2-)"
          if [ -z "$val" ] || [[ "$val" == *"here"* ]]; then
            status_warn "Key '$key' in .env ist leer oder enthält Platzhalter."
          else
            status_ok "Key '$key' in .env ist konfiguriert."
          fi
        else
          status_err "Key '$key' ist in .env.example deklariert, fehlt aber in .env!"
        fi
      done < "$ENV_EX"
    else
      status_warn ".env fehlt! (In CI-Umgebungen normal, sonst bitte aus .env.example kopieren)."
    fi
  else
    status_warn ".env.example fehlt."
  fi
fi

# 4. Check rule synchronization (Rule Compilation)
echo
echo "4. Regel-Kompilierung (Regelsynchronität):"

# Weiche über rules/ (nicht über den Ordnernamen): auch Kit-Worktrees und
# Temp-Klone haben rules/ und müssen als Kit geprüft werden.
AGENTS_FILE="$ROOT/AGENTS.md"
HAS_LOCAL_RULES=0
[ -d "$ROOT/rules" ] && HAS_LOCAL_RULES=1

# Kompatible Liste für Bash 3
declare -a check_list
check_list=(
  "VERDICT|Review-Urteilsformat (VERDICT: APPROVE | REVISE)"
  "ADR-Blöcke|Plan-Ausgabeformat (ADR-Blöcke)"
  "Akzeptanzkriterium|Teststrategie (Akzeptanzkriterium)"
  "Eskalationsregel|Multi-Agent-Eskalationsregel"
)

# Prüft die Ankerwörter in einer Datei; $3 = "err" (hart) oder "warn".
check_rule_keywords() {
  local file="$1" label="$2" level="$3" item kw desc
  status_ok "Prüfe $label..."
  for item in "${check_list[@]}"; do
    kw="${item%%|*}"
    desc="${item#*|}"
    if grep -q "$kw" "$file"; then
      status_ok "Regel-Begriff gefunden: $desc"
    elif [ "$level" = "err" ]; then
      status_err "Regel-Begriff FEHLT in $file: $desc!"
    else
      status_warn "Regel-Begriff fehlt in $file: $desc (globale Regeln neu bauen: scripts/build-global.sh im Kit)."
    fi
  done
}

if [ -f "$AGENTS_FILE" ]; then
  if [ "$HAS_LOCAL_RULES" -eq 1 ]; then
    # Kit: der Volltext enthält alle Regeln, die Ankerwörter müssen drinstehen.
    check_rule_keywords "$AGENTS_FILE" "lokale '$AGENTS_FILE'" err
  else
    # Projekt: AGENTS.md enthält nur den Projektteil, die Hausregeln liegen
    # global. Hart geprüft wird nur die Struktur der Projektdatei.
    status_ok "Prüfe Projekt-AGENTS.md ($AGENTS_FILE)..."
    if grep -q "^## Projektspezifisch" "$AGENTS_FILE"; then
      status_ok "AGENTS.md enthält den Abschnitt '## Projektspezifisch'."
    else
      status_err "AGENTS.md enthält keinen Abschnitt '## Projektspezifisch'!"
    fi
    if [ -f "$ROOT/CLAUDE.md" ] && grep -q "^@rules/" "$ROOT/CLAUDE.md"; then
      status_err "CLAUDE.md enthält ungelöste @rules/-Imports!"
    else
      status_ok "CLAUDE.md ist frei von ungelösten @rules/-Imports."
    fi
    if grep -q "^@rules/" "$AGENTS_FILE"; then
      status_err "AGENTS.md enthält ungelöste @rules/-Imports!"
    else
      status_ok "AGENTS.md ist frei von ungelösten @rules/-Imports."
    fi
    # Globale Regeln nur als Hinweis: in CI/Containern gibt es sie nicht.
    GLOBAL_RULES_FILE=""
    for candidate in "$HOME/.claude/CLAUDE.md" "$HOME/.gemini/config/AGENTS.md"; do
      if [ -f "$candidate" ] && grep -q "AI-CODING-KIT:START" "$candidate"; then
        GLOBAL_RULES_FILE="$candidate"
        break
      fi
    done
    if [ -n "$GLOBAL_RULES_FILE" ]; then
      check_rule_keywords "$GLOBAL_RULES_FILE" "globale Hausregeln ($GLOBAL_RULES_FILE)" warn
    else
      status_warn "Keine globale Regeldatei in \$HOME gefunden (in CI normal)."
    fi
  fi
else
  status_err "Kompilierte AGENTS.md ($AGENTS_FILE) existiert nicht, Inhalt kann nicht validiert werden."
fi

echo
if [ $ERRORS -eq 0 ]; then
  echo -e "\033[0;32mVERDICT: PIPELINE OK\033[0m"
  exit 0
else
  echo -e "\033[0;31mVERDICT: PIPELINE ERRORS ($ERRORS Fehler)\033[0m"
  exit 1
fi
