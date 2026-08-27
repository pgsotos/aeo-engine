# CLAUDE.md — aeo-engine

Guidance for Claude Code agents working in this project. These rules override
default behavior.

## What this project is

`aeo-engine` measures how often **Linear** is the **direct answer** produced by
**Google Gemini** when users ask about project management tools. It is not broad
web visibility (GEO) — it is Answer Engine Optimization (AEO).

### Response classification

Every model answer about a brand is classified into exactly one bucket:

| Bucket | Meaning |
|---|---|
| `Direct Winner` | The brand is the #1 solution or recommendation. |
| `Alternative Mention` | The brand appears as a secondary option or in a list. |
| `Omitted` | The brand is absent; a competitor takes the direct answer. |

Primary metric: **Direct Answer Win Rate** with a Wilson score confidence
interval over N independent runs.

## Analytical rules (non-negotiable)

1. **Multiple parallel sampling.** A single API call is not a metric. Every
   prompt is run N independent times (default N = 8) so confidence intervals
   can be computed.
2. **Absolute immutability.** The raw text returned by Gemini is never mutated.
   Stored verbatim in Supabase. Metrics are pure functions over raw responses.
3. **Competitive symmetry.** Prompts are used in inverted pairs (e.g. "Linear
   vs Jira" and "Jira vs Linear") to isolate positional bias.
4. **Multi-dimension analysis.** Prompts span 5 types: direct, comparative,
   use_case, feature, negative. Win Rate is reported per type.

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | Next.js + Bun — `frontend/` |
| Backend | Python 3.12 + FastAPI + uv — `backend/` |
| Database | Supabase (hosted Postgres) |
| AI Engine | Gemini API (google-genai) |

## Coding rules

### Python (`backend/`)

- Manage with `uv` (`uv sync`, `uv run`, `uv add`). Never `pip`.
- Strict typing, full annotations, no unjustified `Any`.
- async/await for all I/O. No blocking calls in the event loop.
- Ruff for lint + format. Line length 100.
- Metrics code is **pure functions**. No hidden state, no input mutation.
- Tests: `uv run pytest` from `backend/`.

### Frontend (`frontend/`)

- Bun for install and runtime (`bun install`, `bun run`).
- TypeScript strict mode. No `any`.
- Server Components by default; client components only when needed.
- Frontend renders metrics from the API — it never calculates them.

### General

- Conventional Commits only. No AI attribution.
- Gradual, atomic commits — never a single commit at the end.
- English for all code, comments, identifiers, docs, and commits.

## Agent teams

Two specialist agents for delegated work. See `.claude/agents/team/`.

| Agent | Writes in | Role |
|---|---|---|
| `backend-agent` | `backend/` | Python, FastAPI, Gemini, metrics |
| `frontend-agent` | `frontend/` | Next.js, TypeScript, dashboard |

## DECISIONS.md is mandatory

Record decisions, assumptions, and exclusions in `DECISIONS.md`:

- **Decided** — architecture, stack, analytical methodology.
- **Assumed** — brand set, LLM variance handling, statistical limits.
- **Left out** — scope cut, excluded features, deferred work.

Any agent making or discovering such a choice adds an entry before finishing.
