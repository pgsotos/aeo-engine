---
name: aeo-api
description: Backend API contract for aeo-engine — endpoints, request/response shapes, and how the evaluation flow works.
---

# aeo-api — Backend API contract for aeo-engine

Use this when building frontend features, testing endpoints, or understanding
how an evaluation flows through the system.

## Base

- Backend runs at `http://localhost:8000` in dev (or the Render URL in prod).
- The frontend reads `NEXT_PUBLIC_BACKEND_URL` from `.env.local`.
- All endpoints live in `backend/src/aeo_engine/main.py`.

## Endpoints

### GET `/health`
Health check. Returns:
```json
{"status": "ok", "gemini_configured": true}
```

### GET `/api/resolve-category?brand=X`
Gemini infers which product categories a brand belongs to. The frontend uses
this to constrain the user's category choice (no free text).
```json
{"brand": "Linear", "categories": ["project management", "issue tracking", "productivity"]}
```

### GET `/api/resolve-competitors?brand=X&category=Y`
Gemini infers the main competitors for a brand in a category, with brief
justifications. Read-only context before evaluation.
```json
{"brand": "Linear", "category": "project management", "competitors": [{"name": "Jira", "reason": "..."}]}
```

### POST `/api/evaluate`
Runs a full evaluation: N runs × M prompts × all brands.

Request body:
```json
{
  "brand": "Linear",
  "category": "project management",
  "competitors": ["Jira", "Asana", "Monday", "Notion"],
  "sampling_n": 8
}
```
- All four analytics rules apply: parallel sampling (N runs), immutability
  (raw stored verbatim), competitive symmetry (inverted pairs), multi-dimension
  (5 prompt types).
- `sampling_n` optional; defaults to `settings.sampling_n` (8).

Response (evaluation completed synchronously):
```json
{
  "evaluation_id": "uuid",
  "status": "completed",
  "brand": "Linear",
  "category": "project management",
  "competitors": ["Jira", "Asana", "Monday", "Notion"],
  "total_prompts": 20,
  "total_responses": 160,
  "total_classifications": 640,
  "metrics_count": 100
}
```
- 5 types × 4 prompts (2 inverted pairs each) = 20 prompts.
- 20 prompts × N=8 runs = 160 responses.
- Each response classified for every brand (5 brands) = 640 classifications.

### GET `/api/evaluations`
List all evaluations, most recent first.

### GET `/api/evaluations/{id}`
Full detail:
```json
{
  "evaluation": {...},
  "metrics": [...],        // per prompt_type × brand, with wilson CI
  "responses": [...],      // raw gemini output
  "classifications": [...] // per brand per response
}
```

### GET `/api/prompts`
Inspect the generated corpus for any brand/category (does not run an
evaluation). Grouped by prompt type.

## Data model

4 tables in Supabase (`migrations/001_initial_schema.sql`):
- `evaluations` — one row per evaluation
- `gemini_responses` — **immutable** raw Gemini output
- `classifications` — per-brand bucket (`direct_winner` / `alternative_mention` / `omitted`)
- `metrics` — per-type Win Rate + Wilson CI

## Golden rules for frontend consumption

- **Never compute metrics in the frontend.** Every number that needs
  calculation comes pre-computed from the backend. The frontend only renders.
- `direct_winner` wins count; `alternative_mention` and `omitted` do not.
- Use the Wilson CI bars from `/api/evaluations/{id}` metrics — do not
  recompute intervals client-side.
