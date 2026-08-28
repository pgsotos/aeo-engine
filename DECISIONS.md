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
than editing history — the superseded entries below are the record of a real
change of direction, not clutter.

## Index

**What the product is and how it measures** — the analytical core.

| | |
|---|---|
| [ADR-002](#adr-002--aeo-focus-not-geo) | AEO, not GEO — direct-answer win rate against the whole category |
| [ADR-006](#adr-006--n-run-sampling-with-confidence-intervals) | N independent samples per prompt with a Wilson score interval |
| [ADR-010](#adr-010--multi-dimension-prompt-analysis) | Five prompt types in inverted pairs, scored separately |
| [ADR-011](#adr-011--gemini-36-flash-as-the-measured-engine) | `gemini-3.6-flash` as the measured engine |
| [ADR-012](#adr-012--generic-aeo-engine-no-hardcoded-brands) | Generic engine — no hardcoded brands |
| [ASM-001](#asm-001--project-category-brands) · [ASM-002](#asm-002--llm-output-variance-is-bounded-and-estimable) | What the brand set and the variance model assume |
| [OOS-001](#oos-001--product-scope-dropped-for-time) … [OOS-004](#oos-004--local-infrastructure-clickhouse-temporal-redis) | What was deliberately left out |

**Architecture** — the stack, and the one that was abandoned.

| | |
|---|---|
| [ADR-009](#adr-009--simplified-stack-for-technical-test-scope) | **The pivot.** FastAPI + Gemini + Supabase, replacing the original heavy stack |
| [ADR-001](#adr-001--single-monorepo) | Single monorepo |
| [ADR-005](#adr-005--immutable-oltp-supabase--postgresql--olap-clickhouse) | Immutable raw responses; the OLAP half superseded |
| [ADR-017](#adr-017--evaluations-run-in-the-background-sampled-in-parallel) | Background evaluations with parallel sampling |
| [ADR-016](#adr-016--health-check-served-at-apihealth) | Health check at `/api/health` — content blockers |
| [ADR-018](#adr-018--local-stack-runs-on-docker-compose) | `docker compose up` for the local stack |
| [ADR-019](#adr-019--one-database-for-now-per-environment-databases-deferred) | One database now; per-environment split deferred |
| [ADR-003](#adr-003--faststream--redis-for-inter-service-messaging) · [ADR-004](#adr-004--temporalio-for-sampling-orchestration) | *Superseded by ADR-009* — Redis broker, Temporal orchestration |

**How the work was done** — the agent setup and the rules around it. The brief
asks for this to be committed; these entries explain why each piece exists.

| | |
|---|---|
| [ADR-008](#adr-008--strict-branch-and-pr-governance) · [ADR-013](#adr-013--git-flow-branching-main--develop--feature) · [ADR-014](#adr-014--feature-branches-rebase-never-merge) | Branch model, merge gate, rebase over merge |
| [ADR-015](#adr-015--secret-scanning-and-gitignore-hygiene) | Secret scanning and `.gitignore` hygiene |
| [ADR-007](#adr-007--deferred-scope-accepted-risk) | Scope deferred under deadline, with the risk named |

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

**Status:** Superseded by ADR-009 (2026)

**Context:** Backend work splits into collection, extraction, and aggregation
stages that should scale and fail independently.

**Decision (original):** Python services built with FastStream, communicating
over Redis Pub/Sub. Redis also serves as a short-lived cache.

**Revision:** This architecture was **abandoned** in ADR-009. The project now
uses a single FastAPI service with asyncio for parallelism — no message broker
or Redis. This ADR is kept for history only; do not re-introduce Redis or
FastStream without a new decision.

**Consequences (original):** Lightweight broker, no extra infra beyond Redis.
Redis Pub/Sub has no durability — anything that must survive a crash goes
through Temporal or Postgres, never the broker alone.

---

## ADR-004 — Temporal.io for sampling orchestration

**Status:** Superseded by ADR-009 (2026)

**Context:** The analytical method requires N independent parallel runs per
prompt, with retries and durability, so partial failures do not corrupt a
metric.

**Decision (original):** Temporal.io workflows own the fan-out of N runs per
prompt, retry policy, and result collection. Workflow code is deterministic; all
I/O (Gemini calls, DB writes) lives in activities.

**Revision:** This was **abandoned** in ADR-009. The project uses asyncio
(`asyncio.gather`) for parallel sampling. Temporal is not running and is not
planned for the deliverable. This ADR is kept for history only.

**Consequences (original):** Adds a Temporal server + its own Postgres to the
infra. This cost is accepted because parallel sampling with retries is exactly
Temporal's use case and maps directly to a project requirement, not just future
needs.

---

## ADR-005 — Immutable OLTP (Supabase / PostgreSQL) + OLAP (ClickHouse)

**Status:** Superseded by ADR-009 (2026)

**Context:** Raw Gemini responses must be preserved verbatim for auditability.
Derived metrics need fast columnar aggregation across many runs.

**Decision (original):** Postgres (via Supabase) stores users, config, and an
append-only `raw_response` table — no updates, no deletes. Derived metrics are
batch-ingested into ClickHouse for analytics. The OLAP write path sits behind a
`MetricsSink` interface.

**Revision:** The immutable OLTP half (append-only `gemini_responses` table) is
**kept** — it is a core project rule. The ClickHouse OLAP half was **abandoned**
in ADR-009; metrics are computed on read from Postgres with no separate OLAP
store. This ADR is kept for history of the ClickHouse decision.

**Consequences (original):** Two stores to operate. `raw_response` rows are
immutable by convention and by DB permissions. In milestone 1 only Postgres is
wired; ClickHouse joins in milestone 4.

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

## ADR-012 — Generic AEO engine (no hardcoded brands)

**Status:** Accepted

**Context:** The initial design centered on a fixed focus brand (Linear) with a
hardcoded competitive set. The user required the platform to work for any brand
or category (e.g. Sony in TVs, Linear in PM tools), not just the challenge's
focus.

**Decision:** The engine is fully generic. Brand, category, and competitors are
dynamic inputs to `POST /api/evaluate`. Prompt corpus generation
(`prompts.py`) is template-based and produces the 5 prompt types × inverted
pairs for any brand/category. Gemini resolves brand→categories and
brand→competitors dynamically. No brand names are hardcoded anywhere in
`backend/`.

**Consequences:** Any brand/category can be evaluated without code changes. The
challenge's original hardcoded fixtures (Linear, Jira, Asana, Monday, Notion)
are no longer baked in — they are just the default input values. This supersedes
the hardcoded-category assumption in ASM-001 (now revised below).

---

## ADR-013 — Git Flow branching (main → develop → feature/*)

**Status:** Accepted

**Context:** Multiple agents write to one monorepo. The old workflow used a
`feature/hito-2-*` branch as the de facto default and had no stable integration
branch.

**Decision:** Standard Git Flow:
- `main` is the default branch and holds production/stable code.
- `develop` is the integration branch, created from `main`.
- All work happens on `feature/<slug>` branches created from `develop`.
- `feature` → `develop` for integration; `develop` → `main` for release.
- No direct commits to `main` or `develop`. See ADR-008 for the merge
  governance (team-lead audit + qa approval).

**Consequences:** A stable `main` that is always deployable, an integration
`develop` where features accumulate, and isolated `feature` branches for
review. Old branches (`feature/hito-2-infrastructure-temporal`) were
superseded and should be deleted from remote.

---

## ADR-014 — Feature branches rebase, never merge

**Status:** Accepted

**Context:** Feature branches fell behind `develop` and were caught up with
`git merge develop`, producing merge commits inside the branch that muddied the
PR diff. Stacked PRs (`feature/strict-aeo-grounding` on
`feature/strict-aeo-methodology`) made this worse.

**Decision:** When `develop` moves ahead, a feature branch catches up with
`git rebase origin/develop` and `git push --force-with-lease` — never
`git merge develop`. Stacked PRs rebase onto their parent branch the same way.
Full procedure in the `git-flow` skill.

**Consequences:** Linear history; each PR is a clean diff against `develop`.
Requires `--force-with-lease` pushes on feature branches (safe: only the branch
author works on them). `main` and `develop` are never force-pushed.

---

## ADR-015 — Secret scanning and `.gitignore` hygiene

**Status:** Accepted

**Context:** Multiple AI agents and the developer edit tracked files. Live
credentials in play: Gemini API key, Supabase anon + service keys, Render API
key. A committed-and-pushed secret is expensive to undo (rotate + rewrite
history + force-push). A full audit on 2026-08-27 (`gitleaks` over all branches
and history, plus manual `git grep`) found **no secret ever committed** — only
placeholder `.env.example` templates.

**Decision:**

- **`.gitignore`** ignores every secret-bearing or machine-local path:
  `.env` / `.env.*` (except `.env.example`), `.vercel/`, `supabase/.branches/`
  `supabase/.temp/` `supabase/.env`, `.mcp.json`, `.serena/`, `.codegraph/`,
  `.atl/`, build caches (`.next/`, `*.tsbuildinfo`, `next-env.d.ts`).
- **`gitleaks`** runs in CI (`.github/workflows/gitleaks.yml`) on every push and
  PR, configured by `.gitleaks.toml` (default ruleset + allowlist for
  `.env.example`, `.next/`, lockfiles, placeholder regexes).
- **No local pre-commit hook.** For a solo developer it is largely redundant
  with CI and only helps machines that have `gitleaks` installed. Re-run
  `gitleaks detect` manually before a push if desired.
- MCP servers are registered with `claude mcp add -s local` / `-s user` so keys
  land in `~/.claude.json`, never a repo file. Never `-s project`.

**Consequences:** A secret reaching the shared GitHub repo is caught by CI
before merge. False positives are handled by extending `.gitleaks.toml`, not by
disabling the scan. Rotating a key that was exposed in a chat transcript (e.g.
the Render key pasted during setup) is still a manual step in the provider
dashboard.

---

## ADR-016 — Health check served at `/api/health`

**Status:** Accepted

**Context:** The dashboard polls the backend to show a connection banner. It
polled `/health`. Browser content blockers (uBlock Origin, Brave shields, common
privacy filter lists) drop **any** request whose path ends in `/health` or
`/healthz` — the fetch fails client-side in about a millisecond, before it ever
leaves the browser. Users running such an extension saw a red "Backend not
available" banner while the backend was fully up and the rest of the dashboard
(which calls `/api/*`) worked fine.

**Decision:** Serve the same handler at **both** `/health` and `/api/health`.
The browser uses `/api/health`; `/health` stays for server-side uptime pingers,
which have no content blockers. The client also starts optimistic and only
reports "not available" after two consecutive failed checks, with a 15s timeout
to survive Render free-tier cold starts.

**Consequences:** One extra route registration. Verified in production that
`/health` and `/healthz` are blocked in the browser while `/api/health`,
`/api/prompts` and `/api/evaluations` all reach the server. Any future
browser-facing endpoint should live under `/api/` for the same reason.

---

## ADR-017 — Evaluations run in the background, sampled in parallel

**Status:** Accepted

**Context:** `POST /api/evaluate` was synchronous and sampled the 20-prompt
corpus **one prompt at a time**, holding the HTTP request open for about six
minutes. Browsers and proxies time that out, so the UI showed an error while the
run was actually still going; the evaluation only appeared in the list minutes
later. It also pinned Render's single free-tier instance for the whole run.

**Decision:**

- `POST /api/evaluate` creates the evaluation row, returns immediately with
  `status: "running"`, and does the work in a FastAPI `BackgroundTask`. Clients
  poll `GET /api/evaluations/{id}`; the dashboard polls every 5s.
- Every prompt is sampled concurrently under **one shared semaphore**
  (`EVAL_CONCURRENCY`) instead of a per-prompt one, so the whole corpus is in
  flight at once with a single global cap on Gemini calls.
- Each prompt's raw responses are persisted as that prompt finishes, so progress
  is visible and partial work survives.
- A prompt that fails is skipped (`return_exceptions=True`) rather than sinking
  the whole run; the run only fails if every prompt fails.
- `call_gemini` retries transient 429/5xx a few times with backoff, since
  parallel sampling hits the rate limit harder.

Measured: ~372s → ~113s for a default N = 8 run; the endpoint answers in ~1s.

**Consequences:** The tab no longer has to stay open on one long request. But a
background task is **lost if the worker restarts mid-run** — the row stays
`running` forever. Acceptable for this deliverable; a durable queue (or the
Temporal design from the superseded ADR-004) is the real fix if evaluations ever
need to survive deploys. Raising `EVAL_CONCURRENCY` too far will trip Gemini
rate limits faster than the retry can absorb.

---

## ADR-018 — Local stack runs on Docker Compose

**Status:** Accepted

**Context:** Running the project locally meant installing uv and Bun and
starting two servers by hand. A reviewer should be able to run it in one
command.

**Decision:** A `Dockerfile` per service plus a root `docker-compose.yml`:
`docker compose up --build` serves the backend on :8000 and the frontend on
:3000. There is **no local Postgres** — the containers use the hosted Supabase
credentials from `backend/.env` (see ADR-005 for why local Supabase was dropped).

Two build details worth recording:

- The frontend image installs dependencies with **Bun** (matching the lockfile)
  but builds and serves with **Node**: `bun run build` segfaults on linux/arm64.
- `output: "standalone"` is gated behind `BUILD_STANDALONE=1`, set only by the
  Dockerfile. Vercel does its own output tracing and fails the build with
  `ENOENT next-server.js.nft.json` when standalone output is on.

**Consequences:** Two more Dockerfiles to keep in step with the runtimes. The
containers still need real Supabase and Gemini credentials — there is no fully
offline mode.

---

## ADR-019 — One database for now; per-environment databases deferred

**Status:** Accepted (deferred implementation)

**Context:** Every environment — production, local development, feature
branches, and the deployed preview each PR gets on Vercel — currently reads and
writes the **same** Supabase project (`aeo-engine`). Consequences observed
during the build:

- Evaluations run while testing land in the same table a reviewer sees. Four
  junk rows (two `sony` scratch runs, two duplicates) had to be deleted by hand
  before the demo data was presentable.
- A destructive schema change made while developing would take production with
  it. Nothing prevents it today.
- There is no way to test a migration before it is live.

**Decision for the deliverable:** keep the single database. The blast radius is
one developer and demo data, the cost of a mistake is re-running an evaluation,
and splitting environments hours before the deadline means touching production
credentials for no benefit a reviewer can see.

**Decision for what comes next**, in the order it should be done:

1. **A migration flow first.** `migrations/001_initial_schema.sql` is applied by
   hand in the Supabase SQL editor. Multiple databases without automated
   migrations drift apart within days, which is worse than one database.
   Adopt the Supabase CLI (`supabase migration new` / `db push`) and apply
   migrations from CI.
2. **Then split the environments.** Two options, in preference order:
   - **Supabase Branching** (needs a paid plan, roughly \$0.32/day per active
     branch). A branch is a real Postgres with the migrations applied and its
     own URL and keys. The GitHub integration creates one when a PR opens and
     destroys it on merge — per-PR isolation with no manual work. The
     "Supabase Preview" check already appears on this repo's PRs (currently
     skipping) because the integration is wired but branching is off.
   - **A second free project** for `develop` and feature work, with the current
     project reserved for `main`. Free, but feature branches share one database
     (no per-PR isolation) and migrations must be applied to both.
3. **Wire the credentials per environment:** `SUPABASE_URL` / `SUPABASE_KEY` per
   Render service and per Vercel environment (production vs preview), so the
   deployed preview of a PR talks to that PR's database.

**Consequences of deferring:** development keeps writing to the production
database, so demo data needs occasional manual cleanup and a careless schema
change is genuinely dangerous. This is accepted knowingly for a solo-developer
technical test, and is the first thing to fix if the project continues.

---

## Section 2 — Assumptions (ASM)

Assumptions are things taken as true without full proof. Each carries a risk if
wrong and a trigger that would force a revisit.

---

## ASM-001 — Project-category brands

**Status:** Revised (2026) — superseded in part by ADR-012

**Context:** The evaluation needs a competitive category to measure Win Rate
against. The technical test fixes a focus brand and its competitors.

**Assumption (original):** The focus brand is **Linear**; the category is
project / issue-tracking tools, with competitors **Jira, Asana, ClickUp,
Monday.com** (adjustable). Prompts are authored around this set and used in
inverted pairs (e.g. "Linear vs Jira" and "Jira vs Linear").

**Revision:** Per ADR-012, the engine is now **fully generic** — no hardcoded
brands. The focus brand is a dynamic input (`POST /api/evaluate`), not a
hardcoded constant. The Linear/PM category is only the *default* value, not a
code dependency. The qualitative risk that a brand set does not match how
answer engines frame a space still applies per-evaluation, but no longer
requires a code change to support a new brand/category.

**Consequences:** The prompt corpus, competitor list and grounding fixtures are
generated dynamically per brand/category. Supporting a new brand/category needs
no code change. If the category definition is wrong (missing a real competitor,
including a non-competitor), Share of Voice and Win Rate are skewed — the risk
moves from "hardcoded corpus" to "wrong user input".

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

