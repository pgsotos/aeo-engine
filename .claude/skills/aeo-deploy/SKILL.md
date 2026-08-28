---
name: aeo-deploy
description: Deployment workflow for aeo-engine — Render (backend API) and Vercel (frontend) with the full env var setup.
---

# aeo-deploy — Deployment for aeo-engine

Use this when deploying, configuring environments, or diagnosing why a
deployment is failing.

## Architecture

| Piece | Platform | Notes |
|---|---|---|
| Backend API (FastAPI) | [Render](https://render.com) | `render.yaml` at repo root |
| Frontend (Next.js) | [Vercel](https://vercel.com) | point Vercel at `frontend/` |
| Database | Supabase (hosted) | reachable via `SUPABASE_URL` + `SUPABASE_KEY` |

## Env vars

| Var | Used by | Where to set |
|---|---|---|
| `GEMINI_API_KEY` | backend | Render dashboard (secret) |
| `SUPABASE_URL` | backend | Render dashboard (secret) |
| `SUPABASE_KEY` | backend | Render dashboard (secret) |
| `NEXT_PUBLIC_API_URL` | frontend | Vercel env vars |

Backend `.env.example`:
```
GEMINI_API_KEY=
SUPABASE_URL=
SUPABASE_KEY=
SAMPLING_N=8
```

Frontend `.env.example`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Render backend

`render.yaml`:
```yaml
services:
  - type: web
    name: aeo-engine-api
    runtime: python
    buildCommand: cd backend && uv sync --frozen
    startCommand: cd backend && uv run uvicorn aeo_engine.main:app --host 0.0.0.0 --port $PORT
```

Deploy via the Render dashboard (or `render deploy`). Set the 3 secrets there.
Smoke-test `GET /health`.

## Vercel frontend

1. Import the repo in Vercel, set Root Directory to `frontend/`.
2. Framework: Next.js (auto-detected). Build: `bun run build`.
3. Set `NEXT_PUBLIC_API_URL` to the Render URL.
4. Deploy.

## Checklist before "it's live"

1. `GET /health` on Render returns `{"status": "ok", "gemini_configured": true}`.
2. Supabase tables exist (`list_tables` via the Supabase MCP tool).
3. Backend can reach Supabase and Gemini (test an evaluation).
4. Frontend renders and can trigger an evaluation from the UI.
5. CORS is open (backend uses `allow_origins=["*"]` in dev; revisit for prod).
