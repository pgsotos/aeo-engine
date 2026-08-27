# DECISIONS.md — Architecture Decision Records

Format: each ADR has Status, Context, Decision, Consequences. Newest last.

---

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
ClickHouse joins in milestone 4. Local Supabase is run as the `supabase/postgres`
image only — the full Supabase stack (Auth, Studio, PostgREST) is a hosted
project or a separate CLI concern, not part of `docker-compose.yml`.

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
