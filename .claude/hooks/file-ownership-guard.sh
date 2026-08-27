#!/usr/bin/env bash
# file-ownership-guard.sh
#
# PreToolUse hook (Edit|Write|MultiEdit). Blocks an agent from writing outside
# its owned directory, per the Agent Teams ownership rules in CLAUDE.md.
#
# Wire it up in .claude/settings.json (not done automatically — milestone 1
# ships the script only):
#
#   "hooks": {
#     "PreToolUse": [{
#       "matcher": "Edit|Write|MultiEdit",
#       "hooks": [{ "type": "command",
#                   "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/file-ownership-guard.sh" }]
#     }]
#   }
#
# Input: JSON on stdin with .tool_input.file_path and an agent identifier.
# Output: exit 0 to allow; exit 2 with a message on stderr to block.

set -euo pipefail

payload="$(cat)"
file_path="$(printf '%s' "$payload" | sed -n 's/.*"file_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')"
agent="${CLAUDE_AGENT_NAME:-unknown}"

[ -z "$file_path" ] && exit 0

rel="${file_path#"$CLAUDE_PROJECT_DIR/"}"

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
    allow ;;
esac
