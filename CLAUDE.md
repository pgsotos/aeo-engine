# CLAUDE.md — aeo-engine

Guidance for Claude Code agents working in this monorepo. These rules override
default behavior.

## What this project is

`aeo-engine` is a monitoring, auditing and analysis platform for **AEO
(Answer Engine Optimization)**. It measures how often a brand is the **direct
answer** produced by generative answer engines (Google Gemini Pro / Flash),
not broad web visibility (GEO).

### Response classification (Ranker Agent)

Every model answer about a brand is classified into exactly one bucket:

| Bucket | Meaning |
|---|---|
| `Direct Winner` | The brand is the #1 solution or recommendation generated for the user. |
| `Alternative Mention` | The brand appears only as a secondary option or as part of a list. |
| `Omitted/Lost` | The brand is absent; a competitor takes the direct answer. |

The primary metric is **Direct Answer Win Rate**: share of runs classified as
`Direct Winner`, reported with a confidence interval over N runs.

## Analytical rules (non-negotiable)

1. **Multiple parallel sampling.** A single API call is not a metric. Every
   prompt is run N independent times (default N = 8) in parallel so confidence
   intervals can be computed.
2. **Absolute immutability.** The raw JSON (`raw_response`) returned by Gemini is
   never mutated. It is stored verbatim in Postgres. Agents interpret over
   in-memory copies or reads; metrics are pure functions over the raw responses.
3. **Grounding and causal attribution.** The Source Auditor maps which search the
   engine actually ran (`google_search_call.queries`) and which text range
   (`start_index` to `end_index`) each cited URL justifies.
4. **Competitive symmetry.** Brand evaluations always include the full category.
   Prompts are used in inverted pairs (e.g. "Linear vs Jira" and "Jira vs
   Linear") to isolate positional bias.

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | Next.js, managed with **Bun** — `frontend/` |
| Backend | Python 3.12+, managed with **uv** — FastStream microservices — `backend/` |
| Broker / cache | Redis (Pub/Sub for inter-agent messaging) |
| OLTP | Supabase / PostgreSQL (users, config, immutable `raw_response` logs) |
| OLAP | ClickHouse (batch ingestion for derived metrics) |
| Orchestration | Temporal.io (durable workflows, parallel sampling, retries) |

## Coding rules

### Python (`backend/`)

- Manage everything with `uv` (`uv sync`, `uv run`, `uv add`). Never call `pip`
  or `python -m venv` directly.
- **Strict typing.** `from __future__ import annotations`, full annotations on
  every function, `mypy --strict` clean. No bare `Any` without justification.
- **async/await everywhere.** All I/O (DB, HTTP, broker, Temporal activities) is
  async. No blocking calls inside the event loop.
- Ruff for lint + format. Line length 100.
- Metrics code is **pure functions** over `raw_response`. No hidden state, no
  mutation of inputs.
- Temporal: deterministic workflow code only; all I/O lives in activities.

### Frontend (`frontend/`)

- Bun for install, scripts and the runtime (`bun install`, `bun run`).
- TypeScript strict mode. No `any`.
- Server Components by default; client components only when interactivity needs
  them.

### General

- Conventional Commits only. No AI attribution / `Co-Authored-By` lines.
- Gradual, atomic commits per milestone — never a single commit at the end.
- English for all code, comments, identifiers, docs, tests and commit messages.

## File ownership (Agent Teams)

Each agent writes **only** inside its directory. See
`.claude/agents/team/` for the full definitions.

| Agent | Writes in |
|---|---|
| `team-lead` | nothing (coordination, review, integration only) |
| `backend-agent` | `backend/` (except `backend/db/`) |
| `database-agent` | `backend/db/`, `migrations/`, Supabase & ClickHouse schemas |
| `frontend-agent` | `frontend/` |
| `qa-validator-agent` | `tests/` only — read-only everywhere else |

## Roadmap

Milestone 1 (this commit): monorepo structure, governance docs, agent team
setup. Milestones 2–6 and the innovation modules (adversarial simulation,
predictive forecasting, cross-lingual consistency) are tracked in
`DECISIONS.md`.

## DECISIONS.md is mandatory

`DECISIONS.md` is a full decision & scope log, not just ADRs. Record there,
without exception:

- **Decided** — architecture, stack, sampling and analytical methodology (ADR).
- **Assumed** — category brands (Linear / Jira / …), LLM variance handling and
  its statistical limits (ASM).
- **Left out** — product scope cut for time, extra answer engines, long-horizon
  time series (OOS).

Any agent making or discovering such a choice adds an entry before finishing the
task.
