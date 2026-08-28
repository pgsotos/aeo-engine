# aeo-engine — Project Scope

## The challenge

Measure **how often Linear appears as the direct answer** when users ask
**Gemini** about project management tools. Deploy a working app at a public URL.

## Parameters

| Element | Value |
|---|---|
| Focus brand | Linear |
| Category | Project management tools |
| Competitors | Jira, Asana, Monday, Notion |
| AI engine | Gemini (`gemini-3.6-flash`) |
| Deadline | Friday August 28, before noon |

## Creative angle: Multi-dimension + Uncertainty

Instead of a single "which tool is best" query, we test **5 prompt types** to
map WHERE Linear's visibility is strong and where it's weak:

| Type | Example | What it measures |
|---|---|---|
| Direct | "What's the best PM tool?" | General recommendation position |
| Comparative | "Linear vs Jira, which one?" | Head-to-head competitiveness |
| Use-case | "Best tool for a 10-person startup?" | Context-specific relevance |
| Feature | "Best keyboard-driven PM tool?" | Attribute-specific strength |
| Negative | "Why NOT use Linear?" | Resilience to negative framing |

Each prompt runs **8 independent times** (N=8) with a Wilson score confidence
interval — because the enunciado says "los modelos son probabilísticos" and
we take that seriously.

## Current status

| Component | Status |
|---|---|
| Backend (FastAPI + Gemini) | ✅ Deployed on Render, 12 tests passing |
| Supabase schema | ✅ 4 tables, `gemini_responses` append-only |
| Gemini connection | ✅ Live, `gemini-3.6-flash` |
| Frontend dashboard | ✅ Deployed on Vercel — heatmap, CI bars, response drill-down |
| Deployment | ✅ Public URLs, autodeploy from `main` |
| Local run | ✅ `docker compose up` |

**Live:** dashboard at <https://aeo-engine-pgsotos.vercel.app>,
API at <https://aeo-engine-35ii.onrender.com> (`/docs` for OpenAPI).

The engine is generic — any brand and category can be evaluated, with
competitors resolved by Gemini. 16 evaluations across 14 brands and 8
categories have been run against the live API.

## Stack

| Layer | Choice | Why |
|---|---|---|
| Backend | Python + FastAPI + uv | Project stack requirement |
| Frontend | Next.js + Bun | Project stack requirement |
| Database | Supabase (hosted Postgres) | Simple, hosted, no local infra |
| AI engine | Gemini API (`gemini-3.6-flash`) | Required by challenge |
