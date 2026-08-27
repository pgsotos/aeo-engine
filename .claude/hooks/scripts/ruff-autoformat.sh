#!/usr/bin/env bash
# ruff-autoformat: PostToolUse hook that runs `ruff format` + `ruff check --fix`
# on Python files after edits, and reports lint issues.
#
# Runs only for the backend-agent writing inside backend/.

set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
  exit 0
fi

# Read stdin JSON.
if [[ -p /dev/stdin ]]; then
  INPUT="$(cat /dev/stdin)"
else
  INPUT=""
fi

TOOL_NAME="$(printf '%s' "$INPUT" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("tool_name",""))' 2>/dev/null || true)"
FILE_PATH="$(printf '%s' "$INPUT" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("tool_input",{}).get("file_path","") or d.get("tool_input",{}).get("path",""))' 2>/dev/null || true)"

# Only handle Python writes inside backend/.
case "$TOOL_NAME" in
  Write|Edit|MultiEdit|NotebookEdit) ;;
  *) exit 0 ;;
esac

case "$FILE_PATH" in
  backend/*.py) ;;
  *) exit 0 ;;
esac

BACKEND_DIR="$(cd "$(dirname "$0")/../../.." && pwd)/backend"
if [[ ! -d "$BACKEND_DIR" ]]; then
  exit 0
fi

# ruff is available as `uv run ruff` in the backend venv.
if [[ -x "$BACKEND_DIR/.venv/bin/ruff" ]]; then
  RUFF="$BACKEND_DIR/.venv/bin/ruff"
elif command -v uv >/dev/null 2>&1; then
  RUFF="uv run ruff"
else
  exit 0
fi

# Auto-fix + format; report any remaining issues to stdout (non-blocking).
(
  cd "$BACKEND_DIR"
  ${RUFF} format "$FILE_PATH" 2>/dev/null || true
  ${RUFF} check --fix "$FILE_PATH" 2>/dev/null || true
) || true
exit 0
