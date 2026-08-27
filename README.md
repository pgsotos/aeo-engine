# aeo-engine

Monitoring, auditing and analysis platform for **AEO (Answer Engine
Optimization)**. It measures how often a brand is the **direct answer**
produced by generative answer engines (Google Gemini), versus its full
competitive category — not broad web visibility (GEO).

Primary metric: **Direct Answer Win Rate** — the share of model runs where the
brand is classified as `Direct Winner`, reported with a confidence interval
over N independent runs.

## Repository layout

```
aeo-engine/
├── frontend/            Next.js dashboard (Bun)          — frontend-agent
├── backend/             Python services (uv + FastStream) — backend-agent
│   └── db/              persistence layer                — database-agent
├── migrations/          Postgres + ClickHouse migrations — database-agent
├── tests/               pytest-asyncio suites            — qa-validator-agent
├── .claude/agents/team/ Agent Teams definitions
├── .claude/hooks/       file-ownership guard
├── CLAUDE.md            agent guidance and rules
├── DECISIONS.md         decision & scope log: decided / assumed / left out
└── docker-compose.yml   global infrastructure
```

## Requirements

| Tool | Use | Install |
|---|---|---|
| [Bun](https://bun.sh) | frontend package manager + runtime | `curl -fsSL https://bun.sh/install \| bash` |
| [uv](https://docs.astral.sh/uv/) | backend Python env + packages | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Docker + Compose | Redis, Postgres, ClickHouse, Temporal | Docker Desktop or engine ≥ 24 |

## Infrastructure

`docker-compose.yml` provides:

| Service | Port | Purpose |
|---|---|---|
| `aeo-redis` | 6379 | FastStream broker + cache |
| `aeo-postgres` | 5432 | OLTP: users, config, immutable `raw_response` (`postgres:16-alpine`) |
| `aeo-clickhouse` | 8123 / 9000 | OLAP: derived metrics |
| `aeo-temporal` | 7233 | durable workflow engine |
| `aeo-temporal-postgres` | — | Temporal's own persistence |
| `aeo-temporal-ui` | 8080 | Temporal Web UI |

> Local Postgres is plain `postgres:16-alpine` — no Supabase extensions. The
> full Supabase stack (Auth, Studio, PostgREST, RLS) is a hosted project or the
> `supabase` CLI, used in staging/production. Schema and migrations run on both.
> See `DECISIONS.md` ADR-005.

### Run

```bash
cp .env.example .env        # then edit values
docker compose up -d
docker compose ps           # all services healthy
```

`.env` is git-ignored; `.env.example` is the tracked template. Variables:

| Var | Default | Notes |
|---|---|---|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | `aeo` / `aeo` / `aeo_engine` | |
| `CLICKHOUSE_USER` / `CLICKHOUSE_PASSWORD` / `CLICKHOUSE_DB` | `aeo` / `aeo` / `aeo_metrics` | |
| `GEMINI_API_KEY` | — | added in milestone 3 |
| `AEO_SAMPLING_N` | `8` | independent runs per prompt |

## Backend (from milestone 2)

```bash
cd backend
uv sync
uv run <service>
```

## Frontend (from milestone 5)

```bash
cd frontend
bun install
bun run dev        # http://localhost:3000
```

## Deployment

- **Frontend:** point Vercel at the `frontend/` directory (monorepo root
  setting). Set the backend API URL as an environment variable.
- **Backend + infra:** Docker images per service, deployed to Railway (or any
  container host) reading this monorepo. Managed Postgres / ClickHouse /
  Temporal Cloud replace the Compose services in production.

## Milestones

| # | Deliverable |
|---|---|
| 1 | Monorepo structure, governance docs, agent team setup *(this commit)* |
| 2 | Infrastructure + orchestration: Temporal client, Compose validated, Supabase schemas |
| 3 | Collection engine: Gemini connector + grounding, parallel N-run sampling workflow |
| 4 | Analytical extraction + OLAP ingestion: Source Auditor rules, ClickHouse schemas |
| 5 | Dashboard: Win Rate, Share of Voice, category leaderboard, drill-down |
| 6 | QA + deployment: integration tests, public URL, deploy docs |

Innovation modules (adversarial simulation, predictive forecasting,
cross-lingual consistency) are roadmap only — see `DECISIONS.md`.

## Working in this repo

Read `CLAUDE.md` first. Each agent writes only inside its owned directory;
`.claude/hooks/file-ownership-guard.sh` enforces this once wired into
`.claude/settings.json`. Commits are gradual, atomic, and use Conventional
Commits.
