#!/usr/bin/env bash
# owner-guard: PreToolUse hook that enforces per-agent directory ownership.
# Reads agent identity from the hook's stdin JSON and blocks writes outside
# the agent's allowed directories.
#
# NOTE: Claude Code subagent identity does NOT come from the CLAUDE_AGENT_NAME
# env var (it does not exist). It comes from the `agent_type` field of the
# PreToolUse JSON on stdin.

set -euo pipefail

# Determine agent type from stdin JSON (fallback: parent/main agent).
if [[ -p /dev/stdin ]]; then
  readonly INPUT="$(cat /dev/stdin)"
else
  readonly INPUT=""
fi

HINTS="$INPUT"

# Extract agent_type. Could also use python/jq; keep it dependency-light.
AGENT_TYPE=""
if command -v python3 >/dev/null 2>&1; then
  AGENT_TYPE="$(printf '%s' "$INPUT" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("agent_type",""))' 2>/dev/null || true)"
fi
if [[ -z "$AGENT_TYPE" ]]; then
  AGENT_TYPE="parent"
fi

# Parse tool name and file path(s) from input.
TOOL_NAME="$(printf '%s' "$INPUT" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("tool_name",""))' 2>/dev/null || true)"
FILE_PATH="$(printf '%s' "$INPUT" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("tool_input",{}).get("file_path","") or d.get("tool_input",{}).get("path",""))' 2>/dev/null || true)"

# Only enforce on write-type tools.
case "$TOOL_NAME" in
  Write|Edit|MultiEdit|NotebookEdit) ;;
  *) exit 0 ;;
esac

if [[ -z "$FILE_PATH" ]]; then
  exit 0
fi

# Ownership map: agent -> allowed path prefixes (normalized, no trailing slash).
# Default (parent/unknown) agents may write anywhere.
case "$AGENT_TYPE" in
  backend-agent)
    ALLOWED=("backend")
    ;;
  frontend-agent)
    ALLOWED=("frontend")
    ;;
  db-agent)
    ALLOWED=("migrations" "supabase")
    ;;
  deploy-agent)
    ALLOWED=("render.yaml" "frontend" ".vercel")
    ;;
  *)
    exit 0
    ;;
esac

# Normalize the target path (strip leading ./).
TARGET="${FILE_PATH#./}"

for prefix in "${ALLOWED[@]}"; do
  if [[ "$TARGET" == "$prefix" || "$TARGET" == "$prefix"/* ]]; then
    exit 0
  fi
done

# Blocked — emit JSON to stderr so Claude Code shows it.
cat >&2 <<EOF
{"type":"block","reason":"owner-guard: agent '$AGENT_TYPE' attempted to write '$FILE_PATH', outside its allowed directories ${ALLOWED[*]}."}
EOF
exit 2
