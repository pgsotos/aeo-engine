# DECISIONS.md — Decision & Scope Log

*[Resumen en español](DECISIONES.md)*

How `aeo-engine` was built, why it is built that way, and what was knowingly
left undone. Entries keep the number they were written under — 42 references
across the code, the READMEs and merged pull requests point at them — but they
are ordered here by what a reader is looking for, not by when they happened.

Superseded entries are kept. The project pivoted away from a heavy stack
mid-build (ADR-009); that record is part of how it was built, not clutter.

---

## How the engine works

The measurement, in one page. Each claim links to the decision behind it.

**Every Gemini answer is classified, per brand, into exactly one bucket:**

| Bucket | Meaning |
|---|---|
| `direct_winner` | The brand is the #1 solution or recommendation generated for the user. |
| `alternative_mention` | The brand appears only as a secondary option, or as part of a list. |
| `omitted` | The brand is absent — a competitor takes the direct answer. |

**Direct Answer Win Rate** is the share of runs classified `direct_winner`,
reported with a **Wilson score 95% confidence interval** ([ADR-006](#adr-006--n-run-sampling-with-confidence-intervals)).

**How a response becomes a bucket** ([ADR-022](#adr-022--deterministic-classification-not-an-llm-judge)) —
deterministic rules over the raw text, never a second model call. Absent →
`omitted`. Present, and either mentioned in the first 25% of the answer or next
to recommendation language → `direct_winner`, unless a contrast word
(`however`, `although`, `instead`) vetoes it. Everything else →
`alternative_mention`. A judge would be probabilistic, and measuring a
probabilistic system with a probabilistic ruler makes the interval meaningless.

**What gets asked** ([ADR-024](#adr-024--the-prompt-corpus-five-types-inverted-pairs)) —
5 prompt types × 2 base questions × 2 brand orderings = 20 prompts. Every prompt
is issued in both orderings so list position cancels instead of accumulating.
At N = 8 that is 160 Gemini calls and 32 runs per prompt type per brand.

**How it is asked** ([ADR-023](#adr-023--how-the-engine-talks-to-gemini)) —
`gemini-3.6-flash`, temperature **0.7** for sampling (the variance is the
signal) and **0.3** for resolving categories and competitors (those must be
stable), 1024 output tokens, a fresh chat per call so the N samples stay
independent.

**What is kept** ([ADR-005](#adr-005--immutable-oltp-supabase--postgresql--olap-clickhouse)) —
the raw Gemini text, verbatim and never mutated. Every metric is a pure function
over it, so any number on screen can be traced back to the response that
produced it, or recomputed by a different method without re-querying Gemini.

**Nothing is hardcoded to a brand** ([ADR-012](#adr-012--generic-aeo-engine-no-hardcoded-brands)).
Linear is the brief's configuration, not a constant in the code.

---

## Index

### A · Method and measurement — how the AEO number is produced

| | |
|---|---|
| [ADR-002](#adr-002--aeo-focus-not-geo) | AEO, not GEO — direct-answer win rate against the whole category |
| [ADR-022](#adr-022--deterministic-classification-not-an-llm-judge) | Deterministic classification, not an LLM judge — and its failure modes |
| [ADR-024](#adr-024--the-prompt-corpus-five-types-inverted-pairs) | The corpus: five types, two phrasings, inverted pairs |
| [ADR-010](#adr-010--multi-dimension-prompt-analysis) | Why five dimensions instead of one question |
| [ADR-006](#adr-006--n-run-sampling-with-confidence-intervals) | N independent samples with a Wilson score interval |
| [ADR-023](#adr-023--how-the-engine-talks-to-gemini) | Temperature, token budget, and the Chat API |
| [ADR-011](#adr-011--gemini-36-flash-as-the-measured-engine) | `gemini-3.6-flash` as the measured engine |
| [ADR-012](#adr-012--generic-aeo-engine-no-hardcoded-brands) | Generic engine — no hardcoded brands |

### B · Architecture — the stack, and the one abandoned

| | |
|---|---|
| [ADR-009](#adr-009--simplified-stack-for-technical-test-scope) | **The pivot** — FastAPI + Gemini + Supabase, replacing the original heavy stack |
| [ADR-005](#adr-005--immutable-oltp-supabase--postgresql--olap-clickhouse) | Immutable raw responses; the OLAP half superseded |
| [ADR-017](#adr-017--evaluations-run-in-the-background-sampled-in-parallel) | Background evaluations with parallel sampling |
| [ADR-016](#adr-016--health-check-served-at-apihealth) | Health check at `/api/health` — content blockers |
| [ADR-001](#adr-001--single-monorepo) | Single monorepo |
| [ADR-018](#adr-018--local-stack-runs-on-docker-compose) | `docker compose up` for the local stack |
| [ADR-019](#adr-019--one-database-for-now-per-environment-databases-deferred) | One database now; per-environment split deferred |
| [ADR-020](#adr-020--row-level-security-is-off-the-backend-is-the-only-database-client) | RLS off — the backend is the only database client |
| [ADR-003](#adr-003--faststream--redis-for-inter-service-messaging) · [ADR-004](#adr-004--temporalio-for-sampling-orchestration) | *Superseded by ADR-009* — Redis broker, Temporal orchestration |

### C · Process — how the work was done with agents

The brief asks for the agent tooling to be committed; these explain why each
piece exists.

| | |
|---|---|
| [ADR-013](#adr-013--git-flow-branching-main--develop--feature) · [ADR-014](#adr-014--feature-branches-rebase-never-merge) | Branch model; rebase over merge on feature branches |
| [ADR-021](#adr-021--branch-protection-enforces-the-branch-model) | Branch protection makes that model enforced, not aspirational |
| [ADR-015](#adr-015--secret-scanning-and-gitignore-hygiene) | Secret scanning and `.gitignore` hygiene |
| [ADR-007](#adr-007--deferred-scope-accepted-risk) | Scope deferred under deadline, with the risk named |
| [ADR-008](#adr-008--strict-branch-and-pr-governance) | *Superseded by ADR-013 + ADR-021* — the original human-gate governance |

### Assumptions and exclusions

| | |
|---|---|
| [ASM-001](#asm-001--project-category-brands) · [ASM-002](#asm-002--llm-output-variance-is-bounded-and-estimable) | What the brand set and the variance model assume |
| [OOS-001](#oos-001--product-scope-dropped-for-time) … [OOS-004](#oos-004--local-infrastructure-clickhouse-temporal-redis) | What was deliberately left out |

Every entry carries Status, Context, Decision, and Consequences. When an
assumption is invalidated or an excluded item comes back, add a new entry —
never edit history.

---

## Section 1 — Decisions (ADR)

### A · Method and measurement

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

## ADR-022 — Deterministic classification, not an LLM judge

**Status:** Accepted (with known failure modes)

**Context:** Every Gemini answer has to be turned into one of three states per
brand. The obvious approach is to ask a model: send the response back with
"is this brand the top recommendation?" That is what most AEO tooling does.

**Decision:** Classify with **pure functions over the raw text** — no second
model call. `classify_response(raw_text, brand)` is deterministic: same input,
same output, forever.

The rule, in order:

1. **`omitted`** — the brand does not appear. Word-boundary match on the
   normalised text, so "Plane" does not match "planning". Confidence 1.0: the
   absence of a string is not a judgement call.
2. **`direct_winner`** — the brand appears *and* reads as the primary
   recommendation. Two independent signals, either sufficient:
   - **Position** — the first mention falls within the first 25% of the
     response. Answer engines lead with their recommendation.
   - **Language** — a recommendation phrase appears within ±100 characters of
     that mention (`recommend`, `best choice`, `top pick`, `go with`,
     `stands out`, `#1`, …).

   **Contrast words veto it.** If `however`, `but`, `although`, `while`,
   `instead`, `alternative`, `compared to` or `not as` sit in the same window,
   the recommendation language is being used to set up a *contrast* — "Jira is
   the best choice, **although** Linear…" — and position alone must carry the
   call.
3. **`alternative_mention`** — mentioned, but neither of the above. The residual
   category, by design: a brand in a list, a runner-up, a caveat.

**Why not an LLM judge:**

- **Reproducibility.** A judge is itself probabilistic. Measuring a
  non-deterministic system with a non-deterministic ruler makes the confidence
  interval meaningless — you can no longer tell model variance from judge
  variance.
- **Auditability.** Every classification traces to a rule and a character
  offset. The stored `first_mention_position` lets anyone re-derive the verdict
  by eye against the raw text, which is stored verbatim (ADR-005).
- **Cost and time.** A judge would double the API calls: 160 per evaluation
  becomes 320, and the run time with it.
- **The raw text is kept.** If deterministic classification proves too crude,
  every response is still there to be re-classified by any method, without
  re-querying Gemini.

**Known failure modes — this is a heuristic, not a parser:**

- **The 25% threshold is a judgement call**, not a derived constant. A long
  preamble before the recommendation pushes a genuine winner past it; a short
  answer makes almost any mention "early".
- **Keyword lists are English-only** and finite. A recommendation phrased
  outside the list reads as an alternative mention.
- **The contrast veto is positional, not syntactic.** It cannot tell "Linear is
  best, although Jira is cheaper" (Linear wins) from "Jira is best, although
  Linear is faster" (Linear does not) — both have the same words in the same
  window. This is the classifier's weakest point.
- **`confidence_score` is a constant** (1.0 / 0.85 / 0.75) attached to the rule
  that fired, not a calibrated probability. It is honest about which rule
  matched and dishonest as a number; nothing consumes it.

The mitigation is structural rather than clever: N independent samples per
prompt (ADR-006) mean an individual misclassification moves a win rate by
1/32 ≈ 3 percentage points, well inside the reported confidence interval.

---

## ADR-024 — The prompt corpus: five types, inverted pairs

**Status:** Accepted

**Context:** ADR-010 decided *that* the corpus spans five prompt types. This
records *what those prompts actually are* and why the shape is what it is —
the corpus is the instrument, and an instrument nobody can inspect is not a
measurement.

**Decision:** 5 types × 2 base questions × 2 brand orderings = **20 prompts**,
generated from the brand, category and competitor list. At N = 8 that is 160
Gemini calls per evaluation and **32 runs per prompt type per brand** — the
number each heatmap cell reports.

**What each type is asking** (`prompts.py` holds the exact templates):

| Type | Shape of the question | What it exposes |
|---|---|---|
| `direct` | "What is the best {category} tool? Consider {brands}." | Position in an unprompted recommendation |
| `comparative` | "{brand} vs {competitor}: which is better?" | Head-to-head, one competitor at a time |
| `use_case` | "Best tool for a 10-person startup?" | Whether the brand owns a context |
| `feature` | "Best keyboard-driven tool?" | Strength on a specific attribute |
| `negative` | "Why should I *not* use {brand}?" | Whether the brand survives hostile framing |

**Inverted pairs.** Every prompt is issued twice, with the brand list reordered
so the focus brand moves out of first position (`direct-01` and `direct-01-inv`).
Language models are sensitive to order: a brand listed first is more likely to be
named first. Without the inverted half, the metric would partly measure the
prompt, not the model. Both halves score into the same cell, so position bias
cancels instead of accumulating.

**Two base questions per type, not one.** A single phrasing measures that
phrasing. Two different wordings of the same intent separate "the model prefers
this brand" from "the model reacts to this sentence".

**The category is a parameter, never a constant.** Templates interpolate
`{category}` and `{brand_list}`; nothing is hardcoded to Linear or to project
management (ADR-012).

**Consequences:**

- The corpus is inspectable without running anything —
  `GET /api/prompts?brand=…&category=…` returns exactly what would be sent, and
  costs no Gemini calls.
- The grid is fixed at 20 prompts. Adding a type or a base question changes the
  denominator, so results from before and after are not comparable — a change
  here needs a new ADR, not an edit.
- `negative` deserves a caveat: the question invites criticism, so a
  `direct_winner` there means the model defended the brand *while being asked to
  attack it*. The consistently high negative scores across brands should be read
  that way, not as ordinary preference.

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

## ADR-006 — N-run sampling with confidence intervals

**Status:** Accepted

**Context:** LLM outputs are probabilistic. A single call is not a measurement.

**Decision:** Default N = 8 independent runs per prompt. Win Rate and other
metrics are reported with a confidence interval computed over the N runs.
N is configurable per evaluation.

**Consequences:** API cost scales with N. Temporal manages the parallelism and
partial-failure handling so a metric is only emitted when enough runs succeed.

---

## ADR-023 — How the engine talks to Gemini

**Status:** Accepted

**Context:** The measurement is only as good as the call that produces it. Three
settings decide what is actually being measured, and each was chosen rather than
defaulted.

**Decision:**

**Temperature differs by purpose — 0.7 to measure, 0.3 to resolve.**

- **Sampling (0.7).** The whole method rests on the model being probabilistic
  (ADR-006). Sampling at temperature 0 would collapse the N runs into the same
  answer and the confidence interval would be theatre — it would measure nothing
  but the classifier. 0.7 is the variance a real user encounters.
- **Resolution (0.3).** `resolve-category` and `resolve-competitors` are not
  measurements; they are lookups that must give the same competitor set twice in
  a row, or two evaluations of the same brand stop being comparable. Low
  temperature buys that stability.

**Chat API, not `generate_content`.** `client.chats.create(...).send_message(...)`
rather than the Models API. It is the interface Google now recommends, and each
call still opens a fresh chat with no history — so the N samples stay
independent. Nothing carries over between runs; that independence is what the
Wilson interval assumes.

**`max_output_tokens=1024`.** Enough for a recommendation with reasoning, short
enough that 160 calls per evaluation stay affordable and fast. The cost is real
and recorded: a long answer is cut mid-sentence, so a brand that would have been
named in a truncated tail counts as `omitted`. Since the limit applies equally
to every brand and every prompt type, it biases absolute win rates slightly
downward but leaves the comparison between brands intact — and comparison is
what the metric is for.

**Every response records its `model_id`.** Results are only comparable within
one model version (ASM-002), so the version is stored per response rather than
assumed globally.

**Consequences:** The numbers describe `gemini-3.6-flash` at temperature 0.7
with a 1024-token budget — not "Gemini" in the abstract. Changing any of the
three changes what is being measured, which is why they are recorded here rather
than left as literals in `gemini.py`.

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

### B · Architecture

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

## ADR-020 — Row Level Security is off; the backend is the only database client

**Status:** Accepted (with a named residual risk)

**Context:** Supabase reports RLS disabled on all six tables as a critical
advisory: *"anyone with the anon key can read or modify every row."* That
warning assumes the common Supabase shape, where the browser holds the anon key
and queries the database directly.

This project is not built that way. The browser talks only to the FastAPI
backend (`NEXT_PUBLIC_API_URL`); it never imports a Supabase client, and
`SUPABASE_KEY` appears in no frontend file, no `frontend/.env.example`, and no
shipped bundle. The key lives only in server-side environment variables — Render
for production, `backend/.env` locally.

**Decision:** leave RLS off. The trust boundary is the backend, which is the
only database client and the only holder of the key. Enabling RLS without
policies would block that client and take the app down; writing correct policies
is real work, and with a single server-side consumer it would duplicate a
boundary that already exists.

**Residual risk, stated plainly:** this is one layer, not two. If
`SUPABASE_KEY` ever leaked — a misconfigured deploy, a log, a paste — there is
nothing behind it: full read and write on every table. Defence in depth is
absent by choice, not by oversight.

**What would force a revisit:** the browser querying Supabase directly (Realtime
subscriptions, direct reads to skip the API), any multi-tenant or per-user data,
or making the project public with the key in a client bundle. Any of those makes
RLS mandatory, not optional. The enabling SQL is one `ALTER TABLE … ENABLE ROW
LEVEL SECURITY` per table, but it must land together with policies — read for
`anon`, write restricted to the service role — or the application stops working.

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

### C · Process and agent tooling

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
- No direct commits to `main` or `develop`. ADR-021 makes this enforced rather
  than a convention.

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

## ADR-021 — Branch protection enforces the branch model

**Status:** Accepted

**Context:** ADR-008 and ADR-013 both state that nothing is committed directly
to `main` or `develop`. Nothing enforced it. GitHub said so plainly — *"Your
main branch isn't protected"* — and it was right: the releases up to `fb1a93c`
were direct `git push origin main`. A reviewer reading the governance ADRs and
then checking the repository settings would find the rule aspirational.

**Decision:** Enforce it in GitHub.

- **`main`** — classic branch protection: a pull request is required (0
  approvals, since a solo author cannot approve their own PR), the `scan`
  check (gitleaks) must pass, the branch must be up to date, force pushes and
  deletion are blocked, and **the rules apply to administrators**. Exempting
  admins on a single-admin repository would make the protection theatre.
- **`develop`** — a ruleset with the same rules.

**A mistake worth recording:** `required_linear_history` was enabled on `main`
first. It forbids merge commits, so the release PR could only be rebased —
which rewrote the commit and left `main` and `develop` with identical trees and
different SHAs, diverging permanently and getting worse with each release.
Linear history is right for `feature` → `develop`, where ADR-014 already
mandates rebase; it is incompatible with the `develop` → `main` release merge
that Git Flow depends on. It has been turned off on `main`.

**Consequences:** Releases are now pull requests (`develop` → `main`), not
pushes — one more step, and the documented governance is finally true. If an
emergency ever requires a direct push, protection must be removed explicitly and
visibly:

```bash
gh api -X DELETE repos/pgsotos/aeo-engine/branches/main/protection
```

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

**Status:** Superseded by ADR-013 (branch model) and ADR-021 (enforcement)

**Context:** Multiple agents write to one monorepo. Direct commits to `main`
would make ownership violations and unreviewed work land in the trunk.

**Decision (original):** No direct commits to `main`. Every milestone or
sub-task runs on a dedicated branch (`feature/hito-<N>-<slug>`). Merge to `main`
requires an audit by `team-lead` (atomic Conventional Commits, correct per-agent
file ownership, scope matches the milestone) and approval from
`qa-validator-agent` (acceptance criteria met, tests pass).

**Revision:** Every specific in this ADR is now wrong. The `team-lead` and
`qa-validator-agent` agents were removed in the ADR-009 pivot; the
`feature/hito-<N>-*` naming went with the milestone plan; the hook is
`owner-guard.sh`. The branch model that replaced it is ADR-013, and the gate is
no longer a human agent but GitHub branch protection — ADR-021.

The principle survived intact: nothing reaches `main` without review and a
passing check. Only the machinery changed.

**Consequences (original):** Slower than committing straight to trunk, but every
change to `main` is reviewed and attributable.

---

## ADR-014 — Share of Voice and Consistency score (strict AEO methodology)

**Status:** Accepted

**Context:** Direct Answer Win Rate alone punishes presence: a brand mentioned
as an alternative scores zero for the direct answer and is invisible to the
metric. Decision D2 of the strict-AEO design wanted a "consistency" signal for
how stable a brand's DWR is across the five prompt types.

**Decision:**
- **Share of Voice (SoV)** = `win_rate + 0.5 × (alternatives / total)`,
  **clamped to [0, 1]**. The +0.5 alternative weight rewards presence in answers
  without equating an alternative mention to a direct win. The clamp overrides
  the design's natural [0, 1.5] upper bound (user requirement).
  Zero runs return `0.0` instead of a division by zero.
- SoV lives on the **`metrics` table** (it is per brand × prompt_type) as
  `share_of_voice REAL NOT NULL` — existing rows default to NULL until the next
  evaluation writes them (additive migration `002_strict_aeo.sql`).
- **Consistency** = `1 − σ` where σ is the **population standard deviation**
  of the focus brand's five per-type DWR values (`statistics.pstdev`; the five
  prompt types are the full population, not a sample). `NULL` when fewer than
  two per-type rates exist (a single rate has no spread to measure) — resolving
  the ambiguity in the change proposal, which named `0.0`/`1.0` for empty/single
  while the design and tasks said "None if <2 types".
- Consistency lives on the **`evaluations` table** (one value per evaluation),
  NOT on `metrics` — the `metrics.prompt_type` CHECK constraint
  (`IN ('direct','comparative','use_case','feature','negative')`) forbids a
  non-type row.
- DWR stays the **primary** metric; SoV and consistency are complementary.
- Frontend types are `number | null` because pre-migration rows are NULL on the
  wire; the UI renders `—` instead of a number.

**Consequences:** Two new columns (nullable, additive migration), two pure
functions in `metrics.py`, `run_evaluation` persists consistency after
`save_metrics`, and the dashboard shows SoV as a secondary sky-blue bar
underneath the DWR bar.

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
