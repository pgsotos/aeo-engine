# aeo-engine

Monitoring and analysis platform for **AEO (Answer Engine
Optimization)**. It measures how often **Linear** is the **direct answer**
produced by **Google Gemini** when users ask about project management tools. It
is not broad web visibility (GEO) — it is Answer Engine Optimization (AEO).

Primary metric: **Direct Answer Win Rate** — the share of model runs where
Linear is classified as `Direct Winner`, reported with a Wilson score confidence
interval over N independent runs.

## What makes this different

**Multi-dimension prompt analysis.** Instead of a single "best tool" query,
this engine tests 5 prompt types (direct, comparative, use_case, feature,
negative) with symmetric pairs to isolate positional bias. The result is a
heatmap showing WHERE Linear wins and WHERE it loses — not just a single number.

## Repository layout

```
aeo-engine/
├── backend/             Python services (FastAPI + uv)
│   ├── src/aeo_engine/  Application code
│   └── tests/           pytest-asyncio suites
├── frontend/            Next.js dashboard (Bun)  — TBD
├── migrations/          Supabase SQL schemas
├── CLAUDE.md            agent guidance and rules
├── DECISIONS.md         decision & scope log
└── OBJECTIVE.md         project scope and goals
```

## Requirements

| Tool | Use | Install |
|---|---|---|
| [uv](https://docs.astral.sh/uv/) | backend Python env + packages | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| [Bun](https://bun.sh) | frontend package manager + runtime | `curl -fsSL https://bun.sh/install \| bash` |

## Run it locally

### Docker (one command)

```bash
cd backend && cp .env.example .env    # fill in GEMINI_API_KEY, SUPABASE_URL, SUPABASE_KEY
cd .. && docker compose up --build
```

- frontend → http://localhost:3000
- backend  → http://localhost:8000 (OpenAPI docs at `/docs`)

The database is hosted Supabase, so there is no local Postgres container — the
containers talk to your Supabase project using the credentials in
`backend/.env`. To point the frontend at a different backend, set
`NEXT_PUBLIC_API_URL` before `docker compose build` (it is inlined at build
time).

### Without Docker

**Backend**

```bash
cd backend
cp .env.example .env     # add your GEMINI_API_KEY
uv sync
uv run uvicorn aeo_engine.main:app --reload
# API at http://localhost:8000
```

**Frontend**

```bash
cd frontend
bun install
bun run dev              # http://localhost:3000
```

**Database (Supabase)**

Hosted Supabase. The schema is in `migrations/001_initial_schema.sql` — run it
once in the Supabase SQL editor.

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/api/prompts` | Prompt corpus grouped by type |
| POST | `/api/evaluate` | Run full evaluation (N runs × M prompts) |
| GET | `/api/evaluations` | List all evaluations |
| GET | `/api/evaluations/{id}` | Evaluation detail with metrics |

## Agent Teams

| Agent | Writes in | Role |
|---|---|---|
| `backend-agent` | `backend/` | Python, FastAPI, Gemini, metrics |
| `frontend-agent` | `frontend/` | Next.js, TypeScript, dashboard |

## Working in this repo

Read `CLAUDE.md` first. Commits are gradual, atomic, and use Conventional
Commits. No AI attribution.

### Branching

Git Flow: `main` → `develop` → `feature/<slug>`. Branch from `develop`, PR back
to `develop`. When `develop` moves ahead, **rebase** your branch
(`git rebase origin/develop` + `git push --force-with-lease`) — never merge
`develop` in. See the `git-flow` skill and ADR-013 / ADR-014.

After cloning, enable the commit-message hook (Conventional Commits + no AI
attribution):

```bash
git config core.hooksPath .githooks
```

### Secrets

Never commit real credentials. `.env` is git-ignored; only `.env.example`
(placeholders) is tracked. Backend secrets (`GEMINI_API_KEY`, `SUPABASE_URL`,
`SUPABASE_KEY`) are set in the Render dashboard. `gitleaks` scans every push and
PR (`.github/workflows/gitleaks.yml`, config `.gitleaks.toml`); run
`gitleaks detect` locally before pushing if you want an early check. See
ADR-015.
