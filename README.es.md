# aeo-engine

*[English version](README.md) · [Resumen de decisiones](DECISIONES.md)*

Mide con qué frecuencia una marca es la **respuesta directa** que da Google
Gemini cuando alguien pregunta por una categoría de producto — Answer Engine
Optimization (AEO), no visibilidad web amplia (GEO).

| | |
|---|---|
| **Dashboard** | <https://aeo-engine-pgsotos.vercel.app> |
| **API** | <https://aeo-engine-35ii.onrender.com> · [documentación OpenAPI](https://aeo-engine-35ii.onrender.com/docs) |

El botón **Start here** del dashboard abre la evaluación terminada más reciente,
así que hay resultados reales para leer sin ejecutar nada. Hay diecinueve
evaluaciones almacenadas sobre quince marcas y nueve categorías.

## Qué mide

Cada respuesta de Gemini se clasifica, por marca, en exactamente un grupo:

| Clasificación | Significado |
|---|---|
| `direct_winner` | la marca es la recomendación N.º 1 |
| `alternative_mention` | opción secundaria, o un ítem más de una lista |
| `omitted` | ausente — un competidor se queda con la respuesta directa |

El **Direct Answer Win Rate** es la proporción de corridas clasificadas como
`direct_winner`, reportada con un **intervalo de confianza de Wilson al 95 %** —
porque una sola llamada a la API es una anécdota, no una medición.

Tres cosas hacen que el número sea confiable y no decorativo:

- **Multidimensión.** Cinco tipos de prompt (directo, comparativo, caso de uso,
  característica, negativo) medidos por separado. Una marca que gana
  "Linear vs Jira" puede ser invisible en preguntas sobre una característica
  concreta; un número único lo esconde, el heatmap lo muestra.
- **Simetría competitiva.** Cada prompt se emite en los dos órdenes de marcas
  (pares invertidos), para que la posición en la lista no favorezca a ninguna.
- **N muestras independientes.** Por defecto N = 8 por prompt, 4 prompts por
  tipo → 32 corridas por tipo de prompt por marca, 160 llamadas a Gemini por
  evaluación.

El texto crudo de Gemini se guarda literal y nunca se modifica; cada métrica es
una función pura sobre él, así que cualquier número en pantalla puede rastrearse
hasta la respuesta que lo produjo.

## Estructura del repositorio

```
aeo-engine/
├── backend/             servicio FastAPI (Python 3.12 + uv)
│   ├── src/aeo_engine/  gemini · prompts · classifier · metrics · database
│   └── tests/           suites con pytest-asyncio
├── frontend/            dashboard Next.js 16 (Bun + Tailwind)
├── migrations/          esquema SQL de Supabase
├── docker-compose.yml   stack local — `docker compose up`
├── .claude/             configuración de agentes — agents/, skills/, hooks/
├── .codex/              los mismos hooks, para el entorno Codex
├── .githooks/           validador de mensajes de commit
├── CLAUDE.md            reglas para agentes (Claude Code)
├── AGENTS.md            reglas para agentes (Codex) — mismo contenido
├── DECISIONS.md         registro completo de decisiones (en inglés)
└── DECISIONES.md        resumen de decisiones en español
```

## Requisitos

| Herramienta | Para qué | Instalación |
|---|---|---|
| [uv](https://docs.astral.sh/uv/) | entorno y paquetes de Python | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| [Bun](https://bun.sh) | paquetes y runtime del frontend | `curl -fsSL https://bun.sh/install \| bash` |
| Docker | ejecutar todo con un comando | Docker Desktop, o `colima` |

## Ejecutarlo localmente

> **No hace falta ejecutar nada para ver los resultados.** El dashboard
> desplegado ya tiene diecinueve evaluaciones terminadas. Ejecutarlo en local
> sirve para leer el código con la aplicación delante, o para evaluar tu propia
> marca.

Hace falta aportar dos credenciales propias: una **API key de Gemini** (el motor
que se está midiendo) y un **proyecto de Supabase** (donde se guardan las
respuestas). Ambos tienen capa gratuita. La configuración toma unos diez
minutos.

### 1. API key de Gemini

Creala en <https://aistudio.google.com/apikey>. La capa gratuita alcanza: una
evaluación son 160 pedidos a `gemini-3.6-flash`.

### 2. Proyecto de Supabase

1. Creá un proyecto en <https://supabase.com/dashboard> (capa gratuita).
2. **SQL Editor** → **New query** → pegá todo el contenido de
   `migrations/001_initial_schema.sql` → **Run**. Eso crea las cuatro tablas
   (`evaluations`, `gemini_responses`, `classifications`, `metrics`).
3. **Project Settings → API** → copiá la **Project URL** y la clave
   **anon public**.

Solo el backend habla con Supabase; el navegador nunca lo hace.

### 3. Completar el entorno

```bash
cd backend
cp .env.example .env      # después editalo
```

```bash
SUPABASE_URL=https://<tu-proyecto>.supabase.co
SUPABASE_KEY=<clave anon public>
GEMINI_API_KEY=<tu clave de Gemini>
SAMPLING_N=8
```

### 4. Levantarlo

```bash
docker compose up --build     # desde la raíz del repositorio
```

- frontend → <http://localhost:3000>
- backend → <http://localhost:8000> (documentación OpenAPI en `/docs`)

Tu base arranca vacía, así que "Past Evaluations" también: escribí una marca,
resolvé su categoría y competidores, y corré una evaluación. Toma unos dos
minutos.

No hay contenedor de Postgres local — los contenedores usan el proyecto Supabase
hospedado que configuraste en `backend/.env` (ver ADR-005 y ADR-019 sobre el
porqué). Para apuntar el frontend a otro backend, definí `NEXT_PUBLIC_API_URL`
antes de `docker compose build`; Next.js lo incorpora en tiempo de build.

### Sin Docker

Las mismas credenciales — los pasos 1 a 3 siguen aplicando. Después, en dos
terminales:

```bash
cd backend
uv sync
uv run uvicorn aeo_engine.main:app --reload    # http://localhost:8000
```

```bash
cd frontend
bun install
bun run dev                                    # http://localhost:3000
```

El frontend usa `http://localhost:8000` por defecto, así que para trabajo local
no hace falta un `.env` del frontend.

## API

Documentación interactiva: **[`/docs`](https://aeo-engine-35ii.onrender.com/docs)**
(Swagger UI) y [`/redoc`](https://aeo-engine-35ii.onrender.com/redoc), ambas
generadas a partir de los modelos de las rutas de FastAPI — cada endpoint tiene
un esquema de respuesta tipado. Para obtener la especificación cruda:

```bash
cd backend && uv run python scripts/export_openapi.py   # -> openapi.json
```

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/health` | Estado — también en `/health` para monitores externos (ADR-016) |
| GET | `/api/resolve-category?brand=` | Categorías que Gemini infiere para una marca |
| GET | `/api/resolve-competitors?brand=&category=` | Competidores que infiere Gemini, con motivos |
| POST | `/api/evaluate` | Inicia una evaluación — responde de inmediato, corre en segundo plano |
| GET | `/api/evaluations` | Lista de evaluaciones, más recientes primero |
| GET | `/api/evaluations/{id}` | Detalle completo: métricas, respuestas crudas, clasificaciones |
| GET | `/api/prompts?brand=&category=&competitors=` | Inspeccionar el corpus generado |

### Ejecutar una evaluación desde la API

`POST /api/evaluate` responde en aproximadamente un segundo con
`status: "running"` y hace el trabajo en segundo plano (ADR-017). Consultá el
endpoint de detalle hasta que el estado pase a `completed`; una corrida con
N = 8 toma unos dos minutos.

```bash
API=https://aeo-engine-35ii.onrender.com

# 1. Iniciar una corrida
curl -s -X POST $API/api/evaluate \
  -H 'Content-Type: application/json' \
  -d '{"brand":"Linear","category":"project management tools",
       "competitors":["Jira","Asana","Monday","Notion"],"sampling_n":8}'
# -> {"evaluation_id":"…","status":"running","total_prompts":20,"total_responses":160}

# 2. Consultar hasta que termine
curl -s $API/api/evaluations/<evaluation_id> | jq '.evaluation.status'
```

Nada está fijado a una marca: podés pasar cualquier `brand` / `category` /
`competitors`, o dejar que Gemini los resuelva con los dos endpoints
`resolve-*` (que es lo que hace el formulario del dashboard).

## Cómo se construyó esto

El proyecto se escribió con agentes de IA, y la configuración que hizo eso
posible está versionada junto al código.

**Instrucciones** — `CLAUDE.md` (Claude Code) y `AGENTS.md` (Codex) llevan las
mismas reglas: qué mide el proyecto, las restricciones analíticas que no se
negocian (respuestas crudas inmutables, métricas como funciones puras, muestreo
de N corridas, pares invertidos), las convenciones del stack, y quién puede
escribir dónde.

**Agentes especialistas** — `.claude/agents/team/`, cada uno acotado a un
directorio:

| Agente | Escribe en | Rol |
|---|---|---|
| `backend-agent` | `backend/` | Python, FastAPI, Gemini, métricas |
| `frontend-agent` | `frontend/` | Next.js, TypeScript, dashboard |
| `db-agent` | `migrations/` + Supabase | Esquema, SQL, migraciones |
| `deploy-agent` | `render.yaml`, config de `frontend/` | Render + Vercel |

**Skills** — `.claude/skills/`, cargadas bajo demanda en vez de inflar las
instrucciones base: `aeo-api` (contrato de endpoints), `aeo-testing` (cómo
correr las verificaciones), `aeo-deploy` (Render + Vercel con sus variables de
entorno), `git-flow` (ramas, formato de commits, gobernanza de merge).

**Hooks** — barreras deterministas, porque una regla que el agente tiene que
*recordar* se olvida:

| Hook | Evento | Qué hace |
|---|---|---|
| `owner-guard.sh` | `PreToolUse` | Bloquea escrituras fuera del directorio del agente |
| `ruff-autoformat.sh` | `PostToolUse` | Formatea y lintea Python después de cada edición |
| `conventional-commit.sh` | `commit-msg` de git | Rechaza formato inválido o atribución de IA |
| `gitleaks` | GitHub Actions | Escanea secretos en cada push y PR |

Los mismos scripts de hooks existen bajo `.codex/` para el entorno Codex.

Dos hallazgos que vale registrar, ambos en `DECISIONS.md`: la identidad de un
subagente viene del campo `agent_type` del JSON que el hook recibe por stdin, no
de una variable de entorno; y `PreCommit` no es un evento de Claude Code, así
que la validación de commits corre como hook `commit-msg` real de git mediante
`git config core.hooksPath .githooks`.

## Trabajar en este repositorio

Leé `CLAUDE.md` primero. Los commits son graduales, atómicos y siguen
Conventional Commits. Sin atribución de IA.

### Ramas

Git Flow: `main` → `develop` → `feature/<slug>`. Ramificá desde `develop` y abrí
el PR contra `develop`. Cuando `develop` avanza, hacé **rebase** de tu rama
(`git rebase origin/develop` + `git push --force-with-lease`) — nunca mergees
`develop` hacia adentro. Ver la skill `git-flow` y ADR-013 / ADR-014.

Después de clonar, activá el hook de mensajes de commit:

```bash
git config core.hooksPath .githooks
```

### Secretos

Nunca se commitean credenciales reales. `.env` está en `.gitignore`; solo se
versiona `.env.example` (con valores de ejemplo). Los secretos del backend
(`GEMINI_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`) se configuran en el panel de
Render. `gitleaks` escanea cada push y cada PR
(`.github/workflows/gitleaks.yml`, configurado por `.gitleaks.toml`); podés
correr `gitleaks detect` localmente antes de un push. Ver ADR-015.
