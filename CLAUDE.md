# CLAUDE.md — aeo-engine

Guidance for Claude Code agents working in this project. These rules override
default behavior.

## What this project is

`aeo-engine` measures how often a **brand** is the **direct answer** produced by
**Google Gemini** when users ask about a product/service category. It is not
broad web visibility (GEO) — it is Answer Engine Optimization (AEO).

The engine is **fully generic**: any brand, category, and competitor set can be
evaluated. Nothing is hardcoded to a single brand. The focus brand, category,
and competitors are dynamic inputs (see ADR-009, DECISIONS.md).

### Response classification

Every model answer about a brand is classified into exactly one bucket:

| Bucket | Meaning |
|---|---|
| `direct_winner` | The brand is the #1 solution or recommendation. |
| `alternative_mention` | The brand appears as a secondary option or in a list. |
| `omitted` | The brand is absent; a competitor takes the direct answer. |

Primary metric: **Direct Answer Win Rate** with a Wilson score confidence
interval over N independent runs.

### Current status (as of 2026-08-28)

Deployed and running — dashboard at <https://aeo-engine-pgsotos.vercel.app>,
API at <https://aeo-engine-35ii.onrender.com> (`/docs` for OpenAPI).

| Component | Status |
|---|---|
| Backend (FastAPI + Gemini) | ✅ Deployed on Render, 12 tests passing |
| Supabase schema | ✅ 4 tables (`evaluations`, `gemini_responses`, `classifications`, `metrics`) |
| Gemini connection | ✅ Live (`gemini-3.6-flash`) |
| Frontend dashboard | ✅ Deployed on Vercel — heatmap, confidence bars, response drill-down |
| Deployment | ✅ Autodeploy from `main`: Render (API) + Vercel (dashboard) |
| Local run | ✅ `docker compose up` |

17 evaluations across 15 brands and 9 categories are stored.

### Git Flow

The repository uses standard Git Flow:

```
main (production)
  └── develop (integration)
        └── feature/* (work branches)
```

- **Never commit directly to `main` or `develop`.**
- Work happens on `feature/<slug>` branches created from `develop`.
- Merge `feature` → `develop` for integration; `develop` → `main` for release.
- See ADR-008 in DECISIONS.md for the governance rules.

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | Next.js 16 + Bun — `frontend/` |
| Backend | Python 3.12 + FastAPI + uv — `backend/` |
| Database | Supabase (hosted Postgres) |
| AI Engine | Gemini API (`gemini-3.6-flash`) via google-genai |
| Deploy | Render (backend API) + Vercel (frontend) |

### How to run locally

**Backend** (`backend/`):

```bash
cd backend
uv sync          # install deps
cp .env.example .env   # fill in GEMINI_API_KEY, SUPABASE_URL, SUPABASE_KEY
uv run uvicorn aeo_engine.main:app --reload
```

**Frontend** (`frontend/`):

```bash
cd frontend
bun install
cp .env.example .env.local   # fill in NEXT_PUBLIC_API_URL
bun run dev
```

## Available MCP tools

MCP servers are configured per developer, in the harness's own settings —
not versioned here, since each one names local paths and credentials. The set
this project was built against:

| MCP | Purpose |
|---|---|
| `Supabase` | Query/manage the hosted Postgres schema, run SQL, check advisors |
| `GitHub` | Repo management, issues, PRs |
| `Vercel` | Frontend deployment to Vercel |
| `Sentry` | Error monitoring (may be unreliable; verify before trusting) |
| `Context7` | Up-to-date library/framework docs |
| `Playwright` | Browser automation / E2E testing |
| `Engram` | Persistent memory across sessions |

## Coding rules

### Python (`backend/`)

- Manage with `uv` (`uv sync`, `uv run`, `uv add`). Never `pip`.
- Strict typing, full annotations, no unjustified `Any`.
- mypy strict is configured (`[tool.mypy] strict = true`).
- async/await for all I/O. No blocking calls in the event loop.
- Ruff for lint + format. Line length 100 (`ruff check`, `ruff format`).
- Metrics code is **pure functions**. No hidden state, no input mutation.
- **Immutability:** Gemini `raw_response` is stored verbatim. Never transform before storage.
- Tests: `uv run pytest` from `backend/`. Uses pytest-asyncio (`asyncio_mode = "auto"`).

### Frontend (`frontend/`)

- Bun for install and runtime (`bun install`, `bun run`).
- TypeScript strict mode. No `any` (see `tsconfig.json`).
- Server Components by default; client components only when needed.
- Path alias `@/*` maps to `src/*`.
- Lint: `bun run lint` (ESLint with `eslint-config-next`).
- Frontend renders metrics from the API — it never calculates them.

### Backend source layout

`backend/src/aeo_engine/`:

| File | Responsibility |
|---|---|
| `main.py` | FastAPI app, all HTTP endpoints |
| `config.py` | Settings from env vars (pydantic-settings) |
| `database.py` | Supabase client, CRUD for evaluations/responses/classifications/metrics |
| `models.py` | Pydantic models (Evaluation, GeminiResponse, ClassificationResult, MetricSummary, PromptType) |
| `gemini.py` | Gemini client, parallel sampling, brand→category→competitor resolution |
| `prompts.py` | Dynamic prompt corpus generation (5 types × inverted pairs) |
| `classifier.py` | Pure classification logic (per brand over raw text) |
| `metrics.py` | Wilson score confidence intervals, per-type metrics |

Tests in `backend/tests/`: `test_classifier.py`, `test_gemini.py`, `test_metrics.py`.

### API endpoints (backend)

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Health check (reports if Gemini key configured) |
| GET | `/api/resolve-category?brand=X` | Gemini-inferred categories for a brand |
| GET | `/api/resolve-competitors?brand=X&category=Y` | Gemini-inferred competitors |
| POST | `/api/evaluate` | Run full evaluation (N runs × M prompts × all brands) |
| GET | `/api/evaluations` | List all evaluations |
| GET | `/api/evaluations/{id}` | Full detail: responses, classifications, metrics |
| GET | `/api/prompts` | Inspect the generated prompt corpus for any brand/category |

### General

- Conventional Commits only. No AI attribution.
- Gradual, atomic commits — never a single commit at the end.
- English for all code, comments, identifiers, docs, and commits.

## Agent teams

Specialist agents for delegated work. See `.claude/agents/team/`.

| Agent | Writes in | Role |
|---|---|---|
| `backend-agent` | `backend/` | Python, FastAPI, Gemini, metrics |
| `frontend-agent` | `frontend/` | Next.js, TypeScript, dashboard |
| `db-agent` | `migrations/` + Supabase | Schema, SQL, migrations |
| `deploy-agent` | `render.yaml`, `frontend/` config | Render + Vercel deployment |

## Hooks

The project uses Claude Code hooks via `.claude/settings.json`:

- **owner-guard (PreToolUse)**: enforces directory ownership — `backend-agent`
  writes only in `backend/`, `frontend-agent` only in `frontend/`, etc.
- **ruff-autoformat (PostToolUse)**: runs `ruff format` + `ruff check --fix` on
  Python edits.
- **conventional-commit (PreCommit)**: validates commit messages.

## DECISIONS.md is mandatory

Record decisions, assumptions, and exclusions in `DECISIONS.md`:

- **Decided** — architecture, stack, analytical methodology.
- **Assumed** — brand set, LLM variance handling, statistical limits.
- **Left out** — scope cut, excluded features, deferred work.

Any agent making or discovering such a choice adds an entry before finishing.

## DEAD CODE / STALE REFERENCES

- ADR-003 (FastStream+Redis), ADR-004 (Temporal), ADR-005 (ClickHouse) are
  **superseded** by ADR-009. Do NOT re-introduce them without a new decision.
- The engine is generic — there is no hardcoded "Linear" anywhere. If you see
  a hardcoded brand, it is a bug.
