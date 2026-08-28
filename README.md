# aeo-engine

*[Versión en español](README.es.md) · [Resumen de decisiones](DECISIONES.md)*

Measures how often a brand is the **direct answer** Google Gemini gives when
someone asks about a product category — Answer Engine Optimization (AEO), not
broad web visibility (GEO).

| | |
|---|---|
| **Dashboard** | <https://aeo-engine-pgsotos.vercel.app> |
| **API** | <https://aeo-engine-35ii.onrender.com> · [OpenAPI docs](https://aeo-engine-35ii.onrender.com/docs) |

A **Start here** button on the dashboard opens the most recent finished
evaluation, so there are real results to read without running anything. The
live database holds **24 evaluations across 18 brands and 21 categories** —
including non-IT brands (e.g. Tesla/EVs, Duolingo, Figma, Shopify), which
exercises the engine's generic design.

## What it measures

Every Gemini answer is classified, per brand, into exactly one bucket:

| Bucket | Meaning |
|---|---|
| `direct_winner` | the brand is the #1 recommendation |
| `alternative_mention` | secondary option, or one item in a list |
| `omitted` | absent — a competitor takes the direct answer |

**Direct Answer Win Rate** is the share of runs classified `direct_winner`,
reported with a **Wilson score 95% confidence interval** — because a single API
call is an anecdote, not a measurement.

Three things make the number trustworthy rather than decorative:

- **Multi-dimension.** Five prompt types (direct, comparative, use-case,
  feature, negative) scored separately. A brand that wins "Linear vs Jira" can
  still be invisible on feature-specific questions — one blended number hides
  that; the heatmap shows it.
- **Competitive symmetry.** Every prompt is issued in both brand orderings
  (inverted pairs) so list position cannot flatter one brand.
- **N independent samples.** Default N = 8 per prompt, 4 prompts per type →
  32 runs per prompt type per brand, 160 Gemini calls per evaluation.

Raw Gemini text is stored verbatim and never mutated; every metric is a pure
function over it, so any number on screen can be traced back to the response
that produced it.

### The evaluation detail, made legible

Each evaluation's detail page layers two things on top of the raw responses so
the data reads like a conclusion instead of a log dump:

- **Executive Summary** — a deterministic interpretation of the metrics: a
  verdict (winning / contested / relegated), KPI chips (win rate with its
  Wilson interval), the focus brand's strengths and weaknesses from the five
  prompt types, and who currently leads it. It is a pure function over the same
  metric code — no LLM summarizer that could break traceability.
- **Source Auditor** — which cited domains appear in the responses and how each
  co-occurs with the focus brand being the direct winner. It relies on
  `google_search` grounding metadata; see **ADR-026** for the current caveat
  that `gemini-3.6-flash` rarely returns usable grounding chunks today.

## Repository layout

```
aeo-engine/
├── backend/             FastAPI service (Python 3.12 + uv)
│   ├── src/aeo_engine/  gemini · prompts · classifier · metrics · database
│   └── tests/           pytest-asyncio suites
├── frontend/            Next.js 16 dashboard (Bun + Tailwind)
├── migrations/          Supabase SQL schema
├── docker-compose.yml   local stack — `docker compose up`
├── .claude/             agent setup — agents/, skills/, hooks/, settings.json
├── .codex/              the same hooks, wired for the Codex harness
├── .githooks/           commit-msg validator (Conventional Commits)
├── CLAUDE.md            agent rules (Claude Code)
├── AGENTS.md            agent rules (Codex) — same content
├── DECISIONS.md         decision & scope log (decided / assumed / left out)
├── DECISIONES.md        resumen en español de las decisiones
└── README.es.md         este README en español
```

## Requirements

| Tool | Use | Install |
|---|---|---|
| [uv](https://docs.astral.sh/uv/) | backend Python env + packages | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| [Bun](https://bun.sh) | frontend package manager + runtime | `curl -fsSL https://bun.sh/install \| bash` |

## Run it locally

> **You do not need to run anything to see the results.** The deployed
> dashboard above holds 24 finished evaluations. Run it locally only to
> read the code with the app in front of you, or to evaluate your own brand.

Running it needs two credentials of your own: a **Gemini API key** (the engine
being measured) and a **Supabase project** (where responses are stored). Both
have free tiers. Setting them up takes about ten minutes.

### 1. Gemini API key

Create one at <https://aistudio.google.com/apikey>. The free tier is enough —
one evaluation is 160 requests to `gemini-3.6-flash`.

### 2. Supabase project

1. Create a project at <https://supabase.com/dashboard> (free tier).
2. **SQL Editor** → **New query** → paste the whole of
   `migrations/001_initial_schema.sql` → **Run**. This creates the four tables
   (`evaluations`, `gemini_responses`, `classifications`, `metrics`).
3. **Project Settings → API** → copy the **Project URL** and the **anon public**
   key.

Only the backend talks to Supabase; the browser never does.

### 3. Fill in the environment

```bash
cd backend
cp .env.example .env      # then edit it
```

```bash
SUPABASE_URL=https://<your-project>.supabase.co
SUPABASE_KEY=<anon public key>
GEMINI_API_KEY=<your Gemini key>
```

`SAMPLING_N` is optional — it sets how many independent Gemini samples each
prompt gets, and defaults to 8. Lower it to 4 for a faster demo run; a request
can also override it per evaluation.

### 4. Start it

```bash
docker compose up --build     # from the repository root
```

- frontend → <http://localhost:3000>
- backend → <http://localhost:8000> (OpenAPI docs at `/docs`)

Your database starts empty, so "Past Evaluations" is empty: type a brand,
resolve its category and competitors, and run one. It takes about two minutes.

There is no local Postgres container — the containers use the hosted Supabase
project from `backend/.env` (see ADR-005 and ADR-019 for why). To point the
frontend at a different backend, set `NEXT_PUBLIC_API_URL` before
`docker compose build`; Next.js inlines it at build time.

### Without Docker

Same credentials as above — steps 1 to 3 still apply. Then, in two terminals:

```bash
cd backend
uv sync
uv run uvicorn aeo_engine.main:app --reload    # http://localhost:8000
```

```bash
cd frontend
bun install
bun run dev                                    # http://localhost:3000
```

The frontend defaults to `http://localhost:8000`, so no frontend `.env` is
needed for local work.

## API

Interactive docs: **[`/docs`](https://aeo-engine-35ii.onrender.com/docs)**
(Swagger UI) and [`/redoc`](https://aeo-engine-35ii.onrender.com/redoc), both
generated from the FastAPI route models — every endpoint has a typed response
schema. To get the raw spec for other tooling:

```bash
cd backend && uv run python scripts/export_openapi.py   # -> openapi.json
```

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Health check — also at `/health` for uptime pingers (ADR-016) |
| GET | `/api/resolve-category?brand=` | Categories Gemini infers for a brand |
| GET | `/api/resolve-competitors?brand=&category=` | Competitors Gemini infers, with reasons |
| POST | `/api/evaluate` | Start an evaluation — returns immediately, runs in the background |
| GET | `/api/evaluations` | List evaluations, newest first |
| GET | `/api/evaluations/{id}` | Full detail: metrics, raw responses, classifications |
| GET | `/api/prompts?brand=&category=&competitors=` | Inspect the generated corpus |

### Running an evaluation from the API

`POST /api/evaluate` answers in about a second with `status: "running"` and does
the work in the background (ADR-017). Poll the detail endpoint until the status
flips to `completed` — a default N = 8 run takes roughly two minutes.

```bash
API=https://aeo-engine-35ii.onrender.com

# 1. Start a run
curl -s -X POST $API/api/evaluate \
  -H 'Content-Type: application/json' \
  -d '{"brand":"Linear","category":"project management tools",
       "competitors":["Jira","Asana","Monday","Notion"],"sampling_n":8}'
# -> {"evaluation_id":"…","status":"running","total_prompts":20,"total_responses":160}

# 2. Poll until completed
curl -s $API/api/evaluations/<evaluation_id> | jq '.evaluation.status'
```

Nothing is hardcoded to a brand: pass any `brand` / `category` / `competitors`,
or let Gemini resolve them with the two `resolve-*` endpoints (which is what the
dashboard form does).

## How this was built

This project was written with AI coding agents, and the setup that made that
work is committed alongside the code.

**Instructions** — `CLAUDE.md` (Claude Code) and `AGENTS.md` (Codex) carry the
same rules: what the project measures, the analytical constraints that are not
negotiable (immutable raw responses, pure metric functions, N-run sampling,
inverted pairs), the stack conventions, and who may write where.

**Specialist agents** — `.claude/agents/team/`, each scoped to one directory:

| Agent | Writes in | Role |
|---|---|---|
| `backend-agent` | `backend/` | Python, FastAPI, Gemini, metrics |
| `frontend-agent` | `frontend/` | Next.js, TypeScript, dashboard |
| `db-agent` | `migrations/` + Supabase | Schema, SQL, migrations |
| `deploy-agent` | `render.yaml`, `frontend/` config | Render + Vercel |

**Skills** — `.claude/skills/`, loaded on demand instead of bloating the base
instructions: `aeo-api` (endpoint contract), `aeo-testing` (how to run the
checks), `aeo-deploy` (Render + Vercel with env vars), `git-flow` (branching,
commit format, merge governance).

**Hooks** — deterministic guardrails, because rules an agent has to *remember*
get forgotten:

| Hook | Event | What it does |
|---|---|---|
| `owner-guard.sh` | `PreToolUse` | Blocks a write outside the agent's directory |
| `ruff-autoformat.sh` | `PostToolUse` | Formats and lints Python after every edit |
| `conventional-commit.sh` | git `commit-msg` | Rejects a bad commit format or any AI attribution |
| `gitleaks` | GitHub Actions | Scans every push and PR for secrets |

The same hook scripts exist under `.codex/` for the Codex harness.

Two things worth noting, both recorded in `DECISIONS.md`: subagent identity
comes from the `agent_type` field in the hook's stdin JSON, not an environment
variable (ADR-015 context); and `PreCommit` is not a Claude Code hook event, so
commit validation runs as a real git `commit-msg` hook via
`git config core.hooksPath .githooks`.

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
