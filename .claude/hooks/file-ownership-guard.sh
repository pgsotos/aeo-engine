#!/usr/bin/env bash
# file-ownership-guard.sh
#
# PreToolUse hook (Edit|Write|MultiEdit). Blocks a team subagent from writing
# outside its owned directory, per the Agent Teams ownership rules in CLAUDE.md.
#
# Agent identity comes from the `agent_type` field in the hook's stdin JSON
# (Claude Code sets it only when the tool call originates inside a subagent).
# A call with no `agent_type` is the main thread / human session and is never
# policed here.
#
# Wired in .claude/settings.json under hooks.PreToolUse with matcher
# "Edit|Write|MultiEdit". Exit 0 = allow, exit 2 = block (stderr goes to Claude).

set -euo pipefail

payload="$(cat)"

field() { printf '%s' "$payload" | jq -r "$1 // empty" 2>/dev/null || true; }

agent="$(field '.agent_type')"
file_path="$(field '.tool_input.file_path')"
project_dir="${CLAUDE_PROJECT_DIR:-$PWD}"

# No agent_type -> main thread / human session. Not this hook's job.
[ -z "$agent" ] && exit 0
[ -z "$file_path" ] && exit 0

rel="${file_path#"$project_dir/"}"

allow() { exit 0; }
deny() { echo "ownership-guard: '$agent' may not write '$rel'. $1" >&2; exit 2; }

case "$agent" in
  backend-agent)
    case "$rel" in
      backend/db/*) deny "backend/db/ belongs to database-agent." ;;
      backend/*)    allow ;;
      *)            deny "backend-agent owns backend/ only." ;;
    esac ;;
  database-agent)
    case "$rel" in
      backend/db/*|migrations/*) allow ;;
      *) deny "database-agent owns backend/db/ and migrations/ only." ;;
    esac ;;
  frontend-agent)
    case "$rel" in frontend/*) allow ;; *) deny "frontend-agent owns frontend/ only." ;; esac ;;
  qa-validator-agent)
    case "$rel" in tests/*) allow ;; *) deny "qa-validator-agent owns tests/ only (read-only elsewhere)." ;; esac ;;
  team-lead)
    deny "team-lead coordinates and reviews; it does not write code." ;;
  *)
    # Unknown agent type: not one of ours, stay out of its way.
    allow ;;
esac
