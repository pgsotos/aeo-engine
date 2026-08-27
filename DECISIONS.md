# DECISIONS.md — Decision & Scope Log

This document is the comprehensive record of how `aeo-engine` was shaped. It is
**not** limited to technology choices or Architecture Decision Records. Updating
it is mandatory whenever any of the following changes:

1. **What was decided** — architecture, stack, sampling and analytical
   methodology. Captured as ADRs in [Section 1](#section-1--decisions-adr).
2. **What was assumed** — project-category brands (e.g. Linear / Jira), and the
   handling and limits of LLM output variance. Captured as ASMs in
   [Section 2](#section-2--assumptions-asm).
3. **What was left out** — product scope dropped for time, additional answer
   engines, long-horizon time-series analysis. Captured as OOS entries in
   [Section 3](#section-3--out-of-scope-oos).

Every entry has Status, Context, Decision/Assumption/Exclusion, and
Consequences. Newest last within each section. When an assumption is validated
or invalidated, or an excluded item is brought back in, add a new entry rather
than editing history.

---

## Section 1 — Decisions (ADR)

## ADR-001 — Single monorepo

**Status:** Accepted

**Context:** The platform has a Next.js frontend and a set of Python backend
services that share contracts (prompt corpus schema, `raw_response` shape,
metric definitions). The deliverable must be deployable quickly.

**Decision:** One Git repository at the root, with `frontend/` and `backend/`
as sibling directories. Frontend deploys by pointing Vercel at `frontend/`;
backend deploys via Docker/Railway reading the same repo.

**Consequences:** Shared types and docs stay in sync. CI must be path-aware.
Strict per-agent directory ownership is enforced to avoid cross-writes.

---

## ADR-002 — AEO focus, not GEO

**Status:** Accepted

**Context:** "Brand visibility" in answer engines can mean broad web presence
(GEO) or being the direct generated recommendation (AEO). These need different
data models and metrics.

**Decision:** The engine measures **AEO only**: the Direct Answer Win Rate of a
brand versus its full competitive category, classified as `Direct Winner`,
`Alternative Mention`, or `Omitted/Lost`.

**Consequences:** All prompts are category-symmetric and used in inverted
pairs. Metrics are defined over generated answers plus grounding metadata, not
over crawled pages.

---

## ADR-003 — FastStream + Redis for inter-service messaging

**Status:** Accepted

**Context:** Backend work splits into collection, extraction, and aggregation
stages that should scale and fail independently.

**Decision:** Python services built with FastStream, communicating over Redis
Pub/Sub. Redis also serves as a short-lived cache.

**Consequences:** Lightweight broker, no extra infra beyond Redis. Redis
Pub/Sub has no durability — anything that must survive a crash goes through
Temporal or Postgres, never the broker alone.

---

## ADR-004 — Temporal.io for sampling orchestration

**Status:** Accepted

**Context:** The analytical method requires N independent parallel runs per
prompt, with retries and durability, so partial failures do not corrupt a
metric.

**Decision:** Temporal.io workflows own the fan-out of N runs per prompt,
retry policy, and result collection. Workflow code is deterministic; all I/O
(Gemini calls, DB writes) lives in activities.

**Consequences:** Adds a Temporal server + its own Postgres to the infra. This
cost is accepted because parallel sampling with retries is exactly Temporal's
use case and maps directly to a project requirement, not just future needs.

---

## ADR-005 — Immutable OLTP (Supabase / PostgreSQL) + OLAP (ClickHouse)

**Status:** Accepted

**Context:** Raw Gemini responses must be preserved verbatim for auditability.
Derived metrics need fast columnar aggregation across many runs.

**Decision:** Postgres (via Supabase) stores users, config, and an append-only
`raw_response` table — no updates, no deletes. Derived metrics are batch-ingested
into ClickHouse for analytics. The OLAP write path sits behind a `MetricsSink`
interface.

**Consequences:** Two stores to operate. `raw_response` rows are immutable by
convention and by DB permissions. In milestone 1 only Postgres is wired;
ClickHouse joins in milestone 4.

Local Postgres runs as **plain `postgres:16-alpine`**, not `supabase/postgres`.
The Supabase image ships its own `pg_hba.conf` with `peer map=supabase_map` and
init scripts that reject a custom `POSTGRES_USER`, so it only works inside the
full Supabase CLI stack; nothing in milestones 2–4 needs its bundled extensions
(pgsodium, vault, pg_cron, TimescaleDB). The full Supabase stack (Auth, Studio,
PostgREST, RLS) is a hosted project used in staging/production — not part of
`docker-compose.yml`. Schema and migrations are written to run on both.

---

## ADR-006 — N-run sampling with confidence intervals

**Status:** Accepted

**Context:** LLM outputs are probabilistic. A single call is not a measurement.

**Decision:** Default N = 8 independent runs per prompt. Win Rate and other
metrics are reported with a confidence interval computed over the N runs.
N is configurable per evaluation.

**Consequences:** API cost scales with N. Temporal manages the parallelism and
partial-failure handling so a metric is only emitted when enough runs succeed.

---

## ADR-007 — Deferred scope (accepted risk)

**Status:** Accepted

**Context:** The immediate goal is a deployable technical deliverable; the
target is also a long-term platform. Building the full heavy stack up front
risks missing the deadline.

**Decision:** Milestone 1 ships structure + governance only. Heavy components
land on a schedule: Temporal + Redis (M2), Gemini sampling (M3), ClickHouse +
extraction (M4), dashboard (M5), QA + deploy (M6). The innovation modules —
adversarial simulation, predictive forecasting, cross-lingual consistency —
are roadmap only, not scheduled.

**Consequences:** Running ClickHouse, a full Temporal cluster and dual
persistence early is heavier than a technical test strictly needs. This
overhead is a deliberate, documented bet on the long-term platform.

---

## ADR-008 — Strict branch and PR governance

**Status:** Accepted

**Context:** Multiple agents write to one monorepo. Direct commits to `main`
would make ownership violations and unreviewed work land in the trunk.

**Decision:** No direct commits to `main`. Every milestone or sub-task runs on a
dedicated branch (`feature/hito-<N>-<slug>`). Merge to `main` requires:

1. `team-lead` audits the branch — atomic Conventional Commits, correct
   per-agent file ownership, scope matches the milestone.
2. `qa-validator-agent` approves: acceptance criteria met, tests pass.

Only then does `team-lead` merge. Milestone 1 governance/setup commits are the
last work committed directly to `main`.

**Consequences:** Slower than committing straight to trunk, but every change to
`main` is reviewed and attributable. The `file-ownership-guard` hook enforces
directory ownership during work; this ADR adds the human-gate before merge.

---

## ADR-009 — Simplified stack for technical test scope

**Status:** Accepted

**Context:** The original architecture included ClickHouse, Temporal.io, Redis,
and a 5-agent team with file-ownership guards. This is a technical test with a
2-day deadline, developed by a single person.

**Decision:** Use a minimal stack: FastAPI + Gemini API + Supabase (hosted
Postgres). No local infrastructure. Two specialist agents
(`backend-agent`, `frontend-agent`) instead of five.

**Consequences:** Faster to build and deploy. ClickHouse, Temporal, and Redis
can be added post-deliverable if the project scales. The agent team can grow
as needed.

---

## ADR-010 — Multi-dimension prompt analysis

**Status:** Accepted

**Context:** A single "best tool" prompt does not capture how brand visibility
varies by query type. The enunciado encourages creativity.

**Decision:** Prompts span 5 types: direct, comparative, use_case, feature,
negative. Each type has symmetric pairs (brand order swapped) to isolate
positional bias. Win Rate is reported per type, creating a heatmap
visualization.

**Consequences:** 20 prompts × 8 runs = 160 API calls per evaluation. Cost is
acceptable for the insight gained: shows WHERE Linear wins and WHERE it loses,
not just an overall number.

---

## ADR-011 — Gemini 3.6 Flash as the measured engine

**Status:** Accepted

**Context:** The enunciado specifies Gemini as the AI engine. The available
model at development time is `gemini-3.6-flash`.

**Decision:** Use `gemini-3.6-flash` for all evaluations. Model ID is stored
with each response for auditability.

**Consequences:** Model version affects results. Cross-evaluation comparisons
are only valid when using the same model version. This is documented in ASM-002.

---

## Section 2 — Assumptions (ASM)

Assumptions are things taken as true without full proof. Each carries a risk if
wrong and a trigger that would force a revisit.

---

## ASM-001 — Project-category brands

**Status:** Assumed

**Context:** The evaluation needs a fixed competitive category to measure Win
Rate against. The technical test fixes a focus brand and its competitors.

**Assumption:** The focus brand is **Linear**; the category is project /
issue-tracking tools, with competitors **Jira, Asana, ClickUp, Monday.com**
(adjustable). Prompts are authored around this set and used in inverted pairs
(e.g. "Linear vs Jira" and "Jira vs Linear").

**Consequences:** The prompt corpus, competitor list and grounding fixtures are
hard-coded to this category for the deliverable. Supporting a different brand or
category means a new corpus, not a config toggle — until the corpus is made
data-driven (roadmap). If the category definition is wrong (missing a real
competitor, including a non-competitor), Share of Voice and Win Rate are skewed.

**Revisit trigger:** onboarding a second brand, or evidence that the category
set does not match how answer engines actually frame the space.

---

## ASM-002 — LLM output variance is bounded and estimable

**Status:** Assumed

**Context:** Gemini responses are non-deterministic. Metrics must still be
reportable with a stated uncertainty.

**Assumption:** N = 8 independent runs per prompt is enough to estimate the
proportion of `Direct Winner` outcomes with a usable confidence interval, and
the underlying distribution is stable enough over a single evaluation window
that the runs are effectively i.i.d.

**Consequences and known limits:**

- N = 8 gives wide intervals for rare outcomes; small Win Rate differences
  between close competitors may not be statistically separable. Intervals are
  reported so consumers do not over-read noise.
- Model version, safety filtering, prompt phrasing and time of day all shift the
  distribution. Runs within one evaluation are comparable; runs across model
  versions or long gaps are not, and are labelled with the model id and
  timestamp.
- Grounding (`google_search`) adds a second source of variance (which searches
  fire, which pages are retrieved) that N-run sampling captures but does not
  isolate.
- The classifier itself (`Direct Winner` / `Alternative Mention` /
  `Omitted/Lost`) is a deterministic function over `raw_response`; its error is
  bounded by fixture coverage, tracked separately in QA, not by N.

**Revisit trigger:** intervals too wide to support a product claim, or observed
run-to-run drift within a single evaluation window.

---

## Section 3 — Out of scope (OOS)

Explicitly excluded for the current deliverable. Listed so the boundary is a
decision, not an oversight. Each entry says why and what it would take to bring
in.

---

## OOS-001 — Product scope dropped for time

**Status:** Excluded (deliverable)

**Excluded:** user auth and multi-tenant accounts beyond a minimal config row;
scheduled/recurring evaluations; alerting and notifications; historical
dashboards beyond the current evaluation; prompt-corpus editing UI; export /
reporting.

**Why:** none are needed to demonstrate the core measurement (Direct Answer Win
Rate with confidence intervals, grounding attribution, category symmetry).

**To bring in:** post-deliverable milestones; most depend on the corpus becoming
data-driven and on a job scheduler layered on Temporal.

---

## OOS-002 — Additional answer engines

**Status:** Excluded (deliverable)

**Excluded:** ChatGPT / OpenAI, Perplexity, Claude, Google AI Overviews as
measured engines. Only **Google Gemini (Pro / Flash)** is wired.

**Why:** each engine has a different response shape, grounding model and citation
format. Supporting one well — including causal source attribution — is more
valuable for the deliverable than shallow multi-engine coverage.

**To bring in:** introduce an `AnswerEngine` port with per-engine adapters and
normalise responses to a common internal shape before classification. The
immutable `raw_response` store already keeps each engine's payload verbatim, so
this is additive.

---

## OOS-003 — Long-horizon time-series analysis

**Status:** Excluded (deliverable)

**Excluded:** trend lines over weeks/months, seasonality detection, forecasting
citation saturation, change-point detection on Win Rate.

**Why:** requires sustained scheduled collection and a body of historical data
that does not exist yet. Supabase schemas are designed to support this later,
but the analysis itself is not built.

**To bring in:** the predictive forecasting innovation module — depends on
OOS-001 (scheduled evaluations) and accumulated history.

---

## OOS-004 — Local infrastructure (ClickHouse, Temporal, Redis)

**Status:** Excluded (simplified per ADR-009)

**Excluded:** local Docker infrastructure with ClickHouse (OLAP), Temporal.io
(workflow orchestration), and Redis (broker/cache). Originally planned for
milestones 2–4.

**Why:** the technical test scope does not require distributed workflow
orchestration or columnar analytics. Supabase (hosted Postgres) handles
persistence. asyncio handles parallelism.

**To bring in:** if the platform scales to scheduled evaluations across multiple
brands/engines, Temporal would own the fan-out and ClickHouse would handle
metric aggregation.

