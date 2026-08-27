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
| Backend (FastAPI + Gemini) | ✅ Working, tested |
| Supabase schema | ✅ 4 tables created |
| Gemini connection | ✅ Verified with live API |
| Frontend dashboard | 🔲 In progress |
| Deployment | 🔲 Pending |

## Stack

| Layer | Choice | Why |
|---|---|---|
| Backend | Python + FastAPI + uv | Project stack requirement |
| Frontend | Next.js + Bun | Project stack requirement |
| Database | Supabase (hosted Postgres) | Simple, hosted, no local infra |
| AI engine | Gemini API (`gemini-3.6-flash`) | Required by challenge |
