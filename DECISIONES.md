# Decisiones — resumen en español

Resumen de por qué el proyecto quedó como quedó. El registro completo, con el
contexto y las consecuencias de cada entrada, está en
**[DECISIONS.md](DECISIONS.md)** (en inglés): 20 ADRs, 2 supuestos y 4
exclusiones. Este documento es el mapa; aquel es el territorio.

## El encargo

| Elemento | Valor |
|---|---|
| Marca foco | Linear |
| Categoría | Herramientas de gestión de proyectos |
| Competidores | Jira, Asana, Monday, Notion |
| Motor de IA | Gemini (`gemini-3.6-flash`) |
| Entrega | Aplicación desplegada en una URL pública |

Medir con qué frecuencia Linear aparece como la respuesta directa cuando se le
pregunta a Gemini por herramientas de gestión de proyectos.

---

## Lo que se decidió

### Qué se mide, y por qué el número es confiable

**AEO, no GEO** (ADR-002). No se mide presencia web amplia sino si la marca es
*la recomendación* que el motor genera. Cada respuesta se clasifica por marca en
`direct_winner`, `alternative_mention` u `omitted`.

**Un solo llamado no es una medición** (ADR-006). Los modelos son
probabilísticos, así que cada prompt se ejecuta N veces de forma independiente
(N = 8 por defecto) y el Win Rate se reporta con un **intervalo de confianza de
Wilson al 95 %**. Un intervalo ancho es información: significa que no hay
muestras suficientes para afirmar nada.

**Cinco dimensiones, no una pregunta** (ADR-010). Preguntar solo "¿cuál es la
mejor herramienta?" esconde dónde pierde una marca. El corpus cubre cinco tipos:

| Tipo | Ejemplo | Qué mide |
|---|---|---|
| Directo | "¿Cuál es la mejor herramienta?" | Posición en la recomendación general |
| Comparativo | "¿Linear o Jira?" | Competitividad cara a cara |
| Caso de uso | "¿Para una startup de 10 personas?" | Relevancia según contexto |
| Característica | "¿La mejor con atajos de teclado?" | Fuerza en un atributo concreto |
| Negativo | "¿Por qué NO usar Linear?" | Resistencia al encuadre negativo |

Esto resultó ser el hallazgo del proyecto: en las diecinueve evaluaciones, las
marcas son fuertes en `comparativo` y `negativo` y débiles en `característica`
(Notion 3 %, Canva 9 %, Zoom 6 %). Una métrica única lo habría ocultado.

**Simetría competitiva** (ADR-010). Cada prompt se emite en los dos órdenes de
marcas. Si "Linear vs Jira" y "Jira vs Linear" dan resultados distintos, eso es
sesgo de posición, no preferencia — y los pares invertidos lo cancelan.

**Inmutabilidad** (ADR-005). El texto crudo de Gemini se guarda literal y nunca
se modifica; las métricas son funciones puras sobre él. Cualquier número del
dashboard se puede rastrear hasta la respuesta que lo produjo, y recalcular.

**Motor genérico** (ADR-012). Nada está fijado a Linear. Se puede evaluar
cualquier marca y categoría; Gemini resuelve los competidores. Linear es la
configuración del encargo, no una constante del código.

### Arquitectura

**El pivote** (ADR-009). El diseño inicial incluía Temporal.io, Redis, FastStream
y ClickHouse. Para una prueba técnica con plazo corto y un solo desarrollador,
eso era semanas de infraestructura antes de la primera métrica. Se reemplazó por
**FastAPI + Gemini + Supabase**. Los ADR-003, 004 y 005 quedan marcados como
superados: el registro del cambio de rumbo es parte de la historia, no ruido.

**Evaluaciones en segundo plano** (ADR-017). `POST /api/evaluate` mantenía la
petición HTTP abierta unos seis minutos y muestreaba los 20 prompts *uno por
uno*. Los navegadores cortan por timeout. Ahora responde de inmediato con
`status: "running"`, hace el trabajo en una tarea de fondo y muestrea todos los
prompts en paralelo bajo un único semáforo. **De ~372 s a ~113 s.**

**Health check en `/api/health`** (ADR-016). Los bloqueadores de contenido de los
navegadores descartan cualquier ruta que termine en `/health`, así que el
dashboard mostraba "Backend no disponible" con el backend funcionando. Se sirve
en las dos rutas: `/api/health` para el navegador, `/health` para monitores.

**Docker Compose** (ADR-018). `docker compose up` levanta todo. Sin Postgres
local: los contenedores usan el Supabase hospedado.

**Una sola base de datos** (ADR-019). Producción, desarrollo local y las
previsualizaciones de PR comparten el mismo proyecto Supabase. Es una decisión
consciente, no un olvido, y el ADR dice su costo: hubo que borrar a mano filas de
prueba, y un cambio de esquema descuidado tocaría producción. También fija el
orden para arreglarlo: **migraciones automatizadas primero** (varias bases sin
ellas se desincronizan en días), después separar ambientes.

**RLS desactivado** (ADR-020). Supabase lo marca como crítico, pero esa
advertencia asume que el navegador tiene la clave y consulta la base directo.
Acá no: el frontend no importa ningún cliente de Supabase y la clave no viaja en
el bundle. El backend es el único cliente de la base. El riesgo residual queda
dicho sin suavizar: es una capa, no dos.

### Cómo se trabajó

El encargo pide versionar el andamiaje de agentes, así que también está
documentado: gobernanza de ramas y compuerta de merge (ADR-008, ADR-013), rebase
en lugar de merge en ramas de trabajo (ADR-014), y escaneo de secretos con
higiene de `.gitignore` (ADR-015).

---

## Lo que se asumió

**El conjunto de marcas** (ASM-001). El corpus se genera para la marca foco y sus
competidores. Si la categoría está mal definida —falta un competidor real, o
sobra uno que no lo es— el Win Rate y el Share of Voice quedan sesgados. Se
mitiga dejando que Gemini resuelva los competidores en vez de fijarlos a mano.

**La varianza del modelo es acotada y estimable** (ASM-002). Se asume que N = 8
corridas alcanzan para estimar la proporción con un intervalo utilizable, y que
la distribución es estable dentro de una misma evaluación. Los límites conocidos
quedan escritos: con N = 8 los intervalos son anchos para resultados poco
frecuentes, y diferencias chicas entre competidores cercanos **no** son
separables estadísticamente. Comparar entre versiones del modelo o entre
corridas separadas en el tiempo no es válido; por eso cada respuesta guarda su
`model_id` y su marca temporal.

---

## Lo que se dejó afuera

**Otros motores** (OOS-002). Solo Gemini. Cada motor tiene una forma de
respuesta y un modelo de grounding distintos; medir uno bien vale más que medir
cuatro superficialmente. La tabla de respuestas crudas ya guarda cada payload
literal, así que agregar un motor es aditivo.

**Series temporales largas** (OOS-003). Sin tendencias, estacionalidad ni
predicción de saturación. Requiere recolección programada y un histórico que
todavía no existe.

**Infraestructura local** (OOS-004). Sin ClickHouse, Temporal ni Redis — ver el
pivote de ADR-009.

**Alcance de producto recortado por tiempo** (OOS-001). Sin autenticación ni
multi-tenencia, sin evaluaciones programadas, sin alertas, sin editor del corpus
de prompts, sin exportación.

**Dos ramas quedaron abiertas a propósito.** Los PR #1 (Share of Voice +
consistencia entre tipos de prompt) y #2 (Source Auditor: qué búsquedas ejecutó
el motor y qué URL respalda cada fragmento de texto) son profundidad real, pero
son grandes y llegaron cerca del cierre. Se decidió no fusionarlos en lugar de
arriesgar una entrega que funciona.
