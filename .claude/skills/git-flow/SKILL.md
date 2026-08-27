---
name: git-flow
description: Git Flow workflow for aeo-engine — branch names, commit discipline, and the merge governance.
---

# git-flow — Branching and commit workflow for aeo-engine

Use this whenever you create branches, commit, merge, or push in this repo.

## Branch model

```
main (production / stable)
  └── develop (integration)
        └── feature/<slug> (work branches)
```

- **Never commit directly to `main` or `develop`.**
- Always create a `feature/<slug>` branch from `develop`:
  ```bash
  git checkout develop
  git pull origin develop
  git checkout -b feature/my-work
  ```
- Commit atomic increments; push the feature branch; open a PR to `develop`.

## Merge governance

Per ADR-008, merging to `main` requires (historically `team-lead` + `qa`):
1. Commit discipline: atomic Conventional Commits, English, no AI attribution.
2. Per-agent directory ownership respected (`backend-agent` → `backend/`, etc.).
3. Scope matches the branch intent.

```
feature/*  →  develop   (integration; normal PR)
develop    →  main      (release; reviewed, tested)
```

## Commit message format

Conventional Commits, English, no AI attribution:

```
feat(backend): add parallel sampling endpoint
fix(frontend): correct heatmap color encoding
chore(deploy): configure Render backend
docs: update README
test(backend): cover wilson confidence interval
```

Types: `build, chore, ci, docs, feat, fix, perf, refactor, revert, style, test`.

Breaking change: add `!` after scope, e.g. `feat(api)!: change response shape`.

## Golden rules

- **No AI attribution** (`Co-Authored-By`, "with Claude", etc.) — ever.
- **Gradual, atomic commits** — never one big commit at the end.
- The convention-commit hook (`.claude/settings.json`) enforces the format and
  blocks AI attribution automatically.
- The old `feature/hito-2-infrastructure-temporal` branch is deprecated and
  should be deleted from remote; the default branch is `main`.
