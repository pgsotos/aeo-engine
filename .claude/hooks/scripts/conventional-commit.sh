#!/usr/bin/env bash
# conventional-commit: PreCommit hook that validates a git commit message
# follows Conventional Commits and blocks AI attribution.
#
# Reads from the pre-commit hook (COMMIT_MESSAGE env var or stdin) as
# supported by Claude Code's PreCommit hook, and git's prepare-commit-msg.

set -euo pipefail

# --- Resolve the commit message ---
MSG=""
if [[ -n "${COMMIT_MESSAGE:-}" ]]; then
  MSG="$COMMIT_MESSAGE"
else
  # Git prepare-commit-msg passes the msg file as $1
  if [[ -f "${1:-}" ]]; then
    MSG="$(cat "${1:-}" | sed '/^#/d')"
  elif [[ -p /dev/stdin ]]; then
    MSG="$(cat /dev/stdin)"
  fi
fi

# Strip anything after first newline for type validation.
FIRST_LINE="$(printf '%s' "$MSG" | head -n1 || true)"

if [[ -z "$FIRST_LINE" ]]; then
  exit 0
fi

# Remove leading whitespace
FIRST_LINE="${FIRST_LINE#"${FIRST_LINE%%[![:space:]]*}"}"

# --- Validate Conventional Commits format ---
# Types: build, chore, ci, docs, feat, fix, perf, refactor, revert, style, test
# Optional scope in ().
# Optional ! for breaking change.
PATTERN='^(build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test)(\([a-z0-9._-]+\))?!?: .+'

if [[ ! "$FIRST_LINE" =~ $PATTERN ]]; then
  echo "❌ Conventional Commit required." >&2
  echo "Format: type(scope): description (English)" >&2
  echo "Examples:" >&2
  echo "  feat(backend): add parallel sampling endpoint" >&2
  echo "  fix(frontend): correct heatmap color encoding" >&2
  echo "  chore(deploy): configure Render backend" >&2
  exit 1
fi

# --- Block AI attribution ---
if grep -qiE 'Co-Authored-By|Generated with|via Claude|by Claude|Created by AI' <<<"$MSG"; then
  echo "❌ AI attribution (Co-Authored-By / Claude references) is not allowed." >&2
  exit 1
fi

exit 0
