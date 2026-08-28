---
name: aeo-testing
description: How to run tests and static checks in aeo-engine. Backend (pytest, ruff, mypy) and frontend (eslint, build).
---

# aeo-testing — Test and quality commands for aeo-engine

Use this whenever you need to run tests, lint, type-check, or format code in
this repository.

## Backend

Run from `backend/` (the `uv` environment is already set up):

```bash
# All tests (pytest-asyncio, asyncio_mode=auto)
uv run pytest

# A single test file or a filtered test
uv run pytest tests/test_metrics.py
uv run pytest -k "wilson"

# Lint + format (Ruff, line length 100)
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/

# Auto-fix lint
uv run ruff check --fix src/ tests/

# Type checking (strict)
uv run mypy src/
```

Full quality gate before committing backend work:

```bash
uv run pytest && uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/ && uv run mypy src/
```

## Frontend

Run from `frontend/`:

```bash
bun run lint        # ESLint (eslint-config-next)
bun run build       # TypeScript check + production build
```

## Golden rule

- Backend tests must be **pure and deterministic** — no live Gemini API calls,
  no network. Mock Gemini in tests (see `test_gemini.py` for the pattern).
- Do not add a test that depends on a live Supabase/Gemini connection.
