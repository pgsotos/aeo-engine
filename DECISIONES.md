# Decisiones — resumen en español

Resumen de por qué el proyecto quedó como quedó. El registro completo, con el
contexto y las consecuencias de cada entrada, está en
**[DECISIONS.md](DECISIONS.md)** (en inglés): 26 ADRs, 2 supuestos y 4
exclusiones, ordenados en tres bloques — método y medición, arquitectura, y
proceso con agentes. Este documento es el mapa; aquel es el territorio.

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
*la recomendación* que el motor genera. Cada respuesta de Gemini se clasifica,
por marca, en exactamente un grupo:

| Grupo | Significado |
|---|---|
| `direct_winner` | La marca es la solución o recomendación N.º 1 generada para el usuario. |
| `alternative_mention` | La marca aparece solo como opción secundaria, o como parte de una lista. |
| `omitted` | La marca está ausente — la competencia se queda con la respuesta directa. |

**Clasificación determinista, no un juez LLM** (ADR-022). La forma habitual de
resolver esto es devolverle la respuesta a un modelo y preguntarle "¿esta marca
es la recomendación principal?". Acá no: la clasificación son **funciones puras
sobre el texto crudo**. Ausente → `omitted`. Presente, y mencionada en el primer
25 % de la respuesta o junto a lenguaje de recomendación → `direct_winner`,
salvo que una palabra de contraste (`however`, `although`, `instead`) lo vete.
El resto → `alternative_mention`.

El motivo es medible: un juez LLM también es probabilístico, y medir un sistema
probabilístico con una regla probabilística vuelve el intervalo de confianza
inútil — deja de poder separarse la varianza del modelo de la del juez. Además
se puede auditar: cada clasificación se remonta a una regla y a una posición de
carácter concreta.

El ADR-022 también dice dónde falla, porque es una heurística y no un parser: el
umbral del 25 % es una elección y no una constante derivada; las listas de
palabras son solo en inglés; y el veto por contraste es posicional, no
sintáctico — no distingue "Linear es mejor, aunque Jira sea más barato" de
"Jira es mejor, aunque Linear sea más rápido". Lo mitiga la estructura, no la
astucia: con N muestras, un error individual mueve el Win Rate 1/32 ≈ 3 puntos,
dentro del intervalo que se reporta.

**Cómo se le habla a Gemini** (ADR-023). La temperatura cambia según el
propósito: **0,7 para muestrear** —la varianza *es* la señal; a temperatura 0
las N corridas colapsarían en la misma respuesta y el intervalo sería
decorativo— y **0,3 para resolver** categorías y competidores, que deben ser
estables o dos evaluaciones de la misma marca dejan de ser comparables. Cada
llamada abre un chat nuevo, sin historial, para que las muestras sean
independientes. El límite de 1024 tokens tiene un costo registrado: una
respuesta larga se corta, y una marca nombrada en la cola truncada cuenta como
`omitted`.

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

Esto resultó ser el hallazgo del proyecto: en las evaluaciones registradas, las
marcas son fuertes en `comparativo` y `negativo` y débiles en `característica`
(Notion 3 %, Canva 9 %, Zoom 6 %). Una métrica única lo habría ocultado.

**El corpus, en concreto** (ADR-024). 5 tipos × 2 preguntas base × 2 órdenes de
marcas = **20 prompts**. Con N = 8 son 160 llamadas a Gemini por evaluación y
**32 corridas por tipo de prompt por marca** — el número que informa cada celda
del heatmap.

**Simetría competitiva** (ADR-024). Cada prompt se emite en los dos órdenes de
marcas. Los modelos de lenguaje son sensibles al orden: una marca listada
primero tiene más chance de ser nombrada primero. Sin la mitad invertida, la
métrica estaría midiendo en parte el prompt y no el modelo. Las dos mitades
suman a la misma celda, así que el sesgo de posición se cancela en vez de
acumularse.

Dos preguntas base por tipo, no una: una sola redacción mide esa redacción. Dos
formas distintas de la misma intención separan "el modelo prefiere esta marca"
de "el modelo reacciona a esta frase".

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
documentado: el modelo de ramas Git Flow (ADR-013), rebase en lugar de merge en
ramas de trabajo (ADR-014), y escaneo de secretos con higiene de `.gitignore`
(ADR-015). El ADR-008 —la gobernanza original, con auditoría de un agente
`team-lead`— quedó superado: esos agentes desaparecieron en el pivote y la
compuerta hoy la aplica GitHub, no una persona.

**La regla ahora se cumple sola** (ADR-021). Los ADR decían "nunca commitear
directo a `main`", pero nada lo impedía: los releases hasta `fb1a93c` fueron
pushes directos. Ahora `main` y `develop` tienen protección — PR obligatorio,
gitleaks en verde, sin force-push ni borrado, y **la restricción alcanza también
a los administradores**: eximirlos en un repositorio con un solo admin
convertiría la protección en decoración.

El ADR-021 también registra un error propio: se activó `required_linear_history`
en `main`, que prohíbe merge commits y por lo tanto rompe el merge de release
`develop → main` que Git Flow necesita. El primer release quedó rebasado y las
dos ramas divergieron con el mismo contenido y distinto hash. Historia lineal
sirve para `feature → develop`; para el release, no.

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

**Las evaluaciones no son reanudables** (ADR-029). Se lanzaron tres
evaluaciones en cinco minutos; cada una limita sus llamadas a Gemini en 25, así
que tres a la vez son ~75 en vuelo. Bajo esa carga empezaron a fallar prompts, y
una corrida quedó guardada con **9 de 20 prompts** y marcada como `completed`:
le faltan enteros los tipos `feature` y `negative`, y su DWR de 48.6% no es
comparable con ninguna evaluación completa.

Conviene separar dos palabras que no son lo mismo: la **concurrencia** es
cuántas llamadas van en paralelo —es la causa—, y la **reanudación** es poder
retomar una corrida cortada por la mitad —es el remedio, y no existe—. Bajar la
concurrencia hace que pase menos seguido; sólo la reanudación lo vuelve
recuperable cuando pasa. El ADR dice qué habría que construir y por qué no se
construyó ahora. Mitigación disponible hoy: correr las evaluaciones de a una.

El ADR también deja medidos los umbrales para que el dashboard avise, en vez de
dejar al usuario mirando un spinner eterno. Sobre 26 evaluaciones completas: con
N = 8 la mediana es **218 s** y la más lenta real **504 s**; con N = 4, 75 s. El
umbral tiene que derivarse de `sampling_n`, no ser una constante. Y hacen falta
**dos**, porque equivocarse cuesta distinto: avisar temprano que algo tarda sólo
genera una preocupación innecesaria, mientras que declarar muerta una corrida
viva invita a abandonarla. De paso, la medición corrige al propio ADR-027: su
margen real es 1.2×, no "varias veces" como dice ahí.

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

**Source Auditor y grounding** (Slice 2, PR #2, ya fusionado). El segundo
slice agrega el **Source Auditor** al dashboard: qué dominios cita cada respuesta
y qué dominio se correlaciona con el Direct Answer Win Rate de la marca foco.
La captura de grounding (con `google_search`) y el ranking por impacto están en
el backend y en la API; el dashboard los muestra por evaluación.

**Una medición que estuvo mal, y su corrección** (ADR-026). La primera versión
de este ADR concluyó que `gemini-3.6-flash` no devuelve grounding utilizable, a
partir de **0/480** respuestas. Era falso. Ese ADR se escribió a las **08:24**;
el código que captura grounding llegó a producción a las **08:32** — midió ceros
que el propio montaje garantizaba. Un A/B controlado sobre el path real de
producción midió **20.8%** de grounding, dentro del rango que ASM-003 asumía.
Se probaron y descartaron dos hipótesis alternativas (el sufijo de citación y la
concurrencia). Queda sin explicar por qué algunas corridas posteriores al deploy
dieron 0%; la sospecha de cuota diaria **no** está confirmada y el ADR no la
afirma. La versión anterior se conserva dentro del ADR: cómo se produjo el error
es la parte útil.

**Executive Summary** (PR #24, ya fusionado). Para que el detalle de una
evaluación sea legible por una persona, se agregó una capa de interpretación
determinista sobre las métricas existentes: veredicto (ganadora / en disputa /
relegada), chips de KPI (win rate + intervalo), fortalezas y debilidades, y quién
está por delante de la marca foco. Es una función pura (`interpret.ts`) sobre
las métricas ya calculadas — no hay un resumen LLM que rompa la auditabilidad.
