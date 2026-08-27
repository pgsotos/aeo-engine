# aeo-engine — Objetivo Real del Desafío

## El encargo (resumen ejecutivo)

Medir **cómo aparece Linear** cuando un usuario le pregunta a **Gemini** sobre
herramientas de gestión de proyectos. No es un ranking de Google: es un
análisis de respuestas generadas por IA.

## ¿Qué significa esto en la práctica?

1. **Preguntarle a Gemini** con prompts variados sobre la categoría
2. **Guardar las respuestas crudas** (inmutabilidad total)
3. **Clasificar cada respuesta** en: Direct Winner / Alternative Mention / Omitted
4. **Calcular el Win Rate** con intervalo de confianza (N runs independientes)
5. **Mostrar los resultados** en una URL accesible

## Parámetros del desafío

| Elemento | Valor |
|---|---|
| Marca focus | Linear |
| Categoría | Herramientas de gestión de proyectos |
| Competidores | Jira, Asana, Monday, Notion |
| Motor IA | Gemini (API Key proporcionada) |
| Deadline | Viernes 28 agosto, antes del mediodía |

## Stack mínimo viable

| Capa | Tecnología | Por qué |
|---|---|---|
| Backend | Python + FastAPI + uv | Lo que el stack del proyecto pide |
| Frontend | Next.js + Bun | Lo que el stack del proyecto pide |
| Datos | SQLite | Simple, sin infra extra, suficiente para el scope |
| Motor IA | Gemini API | El motor que el desafío requiere |

## Lo que NO necesitamos (para este scope)

- ❌ ClickHouse (SQLite alcanza para una evaluación)
- ❌ Temporal.io (asyncio + asyncio.gather para N runs paralelas)
- ❌ Redis (no hay broker needed)
- ❌ Agent team de 5 agentes (somos uno desarrollando)
- ❌ Branch governance estricta (es un technical test, no un equipo de 10)

## Lo que SÍ conservamos del framework existente

- ✅ DECISIONS.md (formato decided/assumed/left-out — genuinamente bueno)
- ✅ CLAUDE.md (reglas analíticas — correcto)
- ✅ Git history con Conventional Commits
- ✅ El concepto de N-run sampling con confidence intervals
- ✅ La clasificación Direct Winner / Alternative / Omitted
- ✅ Competitive symmetry (prompts invertidos)

## Cronograma estimado

| Día | Entregable |
|---|---|
| Hoy | Backend: Gemini client + classifier + API |
| Mañana | Frontend: dashboard + visualizaciones |
| Jueves | Integration + deployment + polish |
| Viernes AM | Buffer para fixes + deploy final |
