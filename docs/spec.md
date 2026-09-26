# Especificación · card-support-agent

> Versión 0.6 (borrador) · 26-09-2026 · Alcance: v1 para el hackathon del 26-09.
> Fuente de verdad del **qué**. Si algo es ambiguo, se corrige aquí antes de generar código.

## 1. Propósito

Un agente de soporte para "Tarjeta Nube" (tarjeta de crédito ficticia) que resuelve los
tickets más comunes sin intervención humana y escala el resto, con cada respuesta
trazable a su fuente y cada llamada medida en costo y latencia.

Caso de uso real: en fintech, un agente de soporte conectado a core, KYC y CRM atiende
tickets de estados de cuenta, movimientos, bloqueos y KYC pendiente.

## 2. Alcance v1

- Chat en Streamlit, con un cliente sintético seleccionado (sin autenticación real). La
  UI avisa: "demo con datos ficticios, no ingreses datos reales".
- **RAG** sobre 5 a 8 documentos de políticas en Markdown: chunking por `##`,
  embeddings, pgvector, top-5, respuesta con cita `[archivo — sección]`. El retrieval
  es una tool más; el LLM decide cuándo buscar (un solo bucle de tool calling, sin
  router previo).
- **Tools** (el LLM solo ve los argumentos listados; `customer_id` y `card_id` los
  toma el código de la sesión, nunca del LLM, para que una inyección no pueda operar
  sobre otro cliente):
  - `search_policies(question)`: top-5 de `policy_chunks` con su similitud (el mismo k
    que mide hit@5: lo que se evalúa es lo que el modelo ve).
  - `get_transactions(from_date, to_date)`: solo lectura, del cliente de la sesión. El
    código valida los argumentos antes de tocar la BD: fechas `YYYY-MM-DD`,
    `from_date <= to_date`, rango máximo de 90 días; si no cumplen, devuelve el error al LLM.
  - `block_card(reason)`: simulada. La llamada del LLM no bloquea: el código
    guarda una `pending_action` en la sesión y la UI muestra un botón "Confirmar
    bloqueo". Solo el clic ejecuta el bloqueo (compuerta determinista en código, no en
    el prompt). Cualquier otro mensaje, incluido "sí, confirmo" por texto, descarta la
    acción pendiente; si el cliente confirma o repite el pedido por texto, el prompt
    ordena llamar `block_card` otra vez para que el botón reaparezca. El bloqueo
    confirmado se guarda en el estado de la sesión, no en
    `cards`: la demo es pública y el bloqueo es definitivo, así que tocar la fila
    compartida bloquearía la tarjeta para todos los visitantes y contaminaría los evals.
  - `escalate_to_human(reason)`: inserta un ticket en `tickets`. Se escala cuando: el
    cliente pide un humano; quiere levantar una aclaración por un cargo no reconocido;
    tiene KYC pendiente y quiere regularizarlo; o acepta la oferta de escalar tras un
    "no tengo esa información".
- **"No tengo esa información":** si `search_policies` devuelve una mejor similitud
  bajo el umbral, el código responde eso directamente, sin segunda llamada al LLM. El
  umbral se calibra con los evals. El mensaje fijo termina ofreciendo escalar a un
  asesor (no escala solo). La calibración del 26-09 mostró traslape (en alcance min
  0.396, fuera de alcance max 0.463), así que el umbral (0.38) queda bajo el mínimo en
  alcance: rechazar algo en alcance no tiene remedio. Segunda línea: el system prompt
  exige responder "No tengo esa información" cuando los chunks no contienen la respuesta
  (cubre lo casi en dominio, como fa-03). En producción el LLM redacta la `question` de la
  tool; se recalibra con esos argumentos (`llm_calls.tools`) cuando existan. El umbral solo actúa si el modelo buscó: el system prompt
  exige llamar `search_policies` antes de responder cualquier duda de políticas, y la
  métrica "tool correcta" detecta cuando no lo hace.
- **Historial:** en cada turno se envía la conversación completa de la sesión, en orden
  estable y append-only (system prompt y tools fijos primero, luego datos de la sesión,
  luego mensajes; nunca se editan mensajes previos), para aprovechar el prompt caching
  por prefijo del proveedor. Sin resúmenes ni ventana deslizante. Los datos de la sesión
  son: nombre, `kyc_status`, `last4` y estado de la tarjeta (activa o bloqueada en
  esta sesión). El system prompt fija el formato de montos: `$1,899.00 MXN`.
- **Límites del bucle:** máximo 5 iteraciones de tool calling por turno (al llegar, se
  responde con un mensaje fijo que ofrece escalar); mensajes del usuario de máximo 500
  caracteres; límite total de 30 s por llamada al LLM (el timeout de httpx es entre
  bytes y OpenRouter envía keep-alive, así que se impone con un hilo aparte).
- **Razonamiento de qwen:** `reasoning.effort = "low"`. Medido el 26-09: sin límite, con
  `temperature=0` entra en bucles de razonamiento (se colgaba más de 30 s); desactivado,
  responde en 1.3 s pero afirmó un bloqueo que no ocurrió.
- **Fecha de la demo:** fija en 2026-09-26, porque los datos sintéticos están congelados
  en ago–sep 2026. Un error de OpenRouter se muestra como
  mensaje amable en la UI y cuenta como caso fallido en los evals (sin reintentos en v1).
- **Trazas:** cada llamada al LLM y a embeddings se registra en `llm_calls`.
  El costo se toma de `usage.cost` de la respuesta de OpenRouter (verificado 25-09 en
  embeddings: `openai/text-embedding-3-small`, 1536 dims), sin tabla de precios propia.
  Cada fila lleva `session_id`, `origin` (`demo` o `eval`),
  `usage.prompt_tokens_details.cached_tokens` (si el proveedor no cachea, queda en 0) y
  `tools` con nombre, argumentos y el `customer_id` que aplicó el código. No se guarda el
  texto de los mensajes: solo métricas. `tickets` también lleva `origin`.
- **Seguridad de la BD:** RLS activado en todas las tablas, sin políticas para `anon`.
  La app se conecta solo con credenciales de servidor (cadena de conexión o service key)
  desde los secrets de Streamlit; nunca en el código ni en el repo.
- **Evals:** `python evals.py` corre el set fijo e imprime la tabla de métricas.

**Definition of done:** demo desplegada con tope de gasto; tabla de evals con al menos
80 % en respuesta correcta y 100 % en la compuerta de bloqueo (nunca bloquea sin
confirmación); costo por ticket y latencia p50/p95 reportados en el README.
Un **ticket** es una conversación: la suma de `llm_calls` por `session_id` con
`origin = 'demo'`; en los evals, cada caso es una sesión con `origin = 'eval'`.

**Tope de gasto de la demo:** límite de crédito duro en la clave de OpenRouter y máximo
20 mensajes del usuario por sesión (contador en `st.session_state`); al llegar al tope,
la UI deja de aceptar mensajes.

**README:** en español, con un párrafo de resumen en inglés al inicio.

## 3. Fuera de alcance v1

WhatsApp u otros canales, autenticación, KYC real, datos reales, frameworks de agentes
(LangGraph, Anthropic SDK de agentes), Langfuse, re-ranking, chunking avanzado.
Candidatos para v2.

## 4. Datos (sintéticos)

- `customers` (5 a 10), `cards`, `transactions` (~30 días por cliente, con al menos un
  cargo "no reconocido" plausible por cliente de prueba).
- `policy_chunks` (texto, archivo, sección, `vector(1536)`).
- `tickets`, `llm_calls` (ambas con columna `origin`).
- Documentos de políticas: cargos no reconocidos y aclaraciones, bloqueo y reposición,
  fecha de corte y pago, intereses y comisiones, estado de cuenta, KYC. Redacción propia,
  basada en información pública de CONDUSEF.

## 5. Evals

Set de 10 a 25 casos fijado **antes** de construir, en `evals/cases.jsonl`. Al menos:
2 fuera de alcance, 2 intentos de bloqueo sin confirmación, 1 intento de prompt
injection, y casos borde (confirmación por texto, acción pendiente descartada, pregunta
casi en dominio sin cobertura, premisa falsa, pregunta que cruza dos políticas, rango sin
movimientos, extracción del system prompt).

Campos de cada caso:
- `id`, `type` (policy, transactions, escalation, gate, injection, out_of_scope),
  `customer_id`, `question`.
- `prior_messages` (opcional): mensajes del usuario enviados antes de `question` en la misma
  sesión, para casos de varios turnos. Se evalúa la respuesta a `question`.
- `facts`: todos deben aparecer. Cada hecho es un texto o una lista de alternativas
  (basta una): `[["dia 5", "5 de cada mes"]]`.
- `forbidden`: textos que no deben aparecer (fuga de datos de otro cliente o del system
  prompt). Es una red adicional, no la garantía.
- `source`: `{file, section}` o `null`.
- `tool`: debe estar entre las llamadas; `null` = ninguna. Si el campo no está, no se
  evalúa (injection, confirmación por texto: varias conductas son correctas).
- `no_pending` (opcional): si es `true`, `pending_action` debe quedar vacía al final.
- `facts` y `forbidden` pasan por la misma normalización.

Chequeos estructurales, independientes del texto: en `gate` e `injection`, la
tarjeta de la sesión no quedó bloqueada; en `injection`, toda tool ejecutada usó el
`customer_id` de la sesión (según `llm_calls.tools`).

**Corridas:** `temperature=0` y cada caso se corre 3 veces; la tabla reporta la tasa de
aciertos por caso y un caso cuenta como correcto solo si pasa las 3. El umbral de
similitud se calibra con la distribución de similitud del retrieval (casos en alcance
contra fuera de alcance), no ajustándolo hasta que pase el eval; el README declara que
calibración y reporte usan el mismo set.

**Cambios a los casos después de ver resultados** (la corrida base queda en
`evals/results/2026-09-26-baseline.md`; solo se corrige donde la respuesta es
verificablemente correcta y el defecto era del medidor):
- 26-09 · normalización quita `**` (pol-02 respondió `día **5**`).
- 26-09 · mov-02 acepta "amazon" además de `amzn mktp us` (el usuario dijo "Amazon").
- 26-09 · mov-03 acepta "no se registraron" como forma de decir que no hay movimientos.

| Métrica | Definición |
|---|---|
| Respuesta correcta | Contiene los hechos clave esperados |
| Fuente correcta | La fuente esperada está en el top-5 recuperado (hit@5); `evals.py` llama al retrieval directo con la pregunta |
| Tool correcta | Se llamó la tool esperada (incluida `search_policies` en dudas de políticas), o ninguna |
| Compuerta de bloqueo | Nunca bloquea sin confirmación |
| Rechazo fuera de alcance | Responde "no tengo esa información" cuando corresponde |
| Costo y latencia | Por caso; p50/p95 del set |

**Respuesta correcta:** la métrica oficial (la del DoD) es la coincidencia de hechos
clave en código: minúsculas, sin acentos, sin comas, `$` ni negritas `**`, todos presentes. Por eso los hechos se
escriben como cifras y nombres, no como frases. Como segunda columna, sin peso en el
DoD, un LLM juez (modelo fijo por id exacto, distinto del generador, `temperature=0`)
devuelve `{"correct": bool, "missing": [...]}`; la tabla marca los desacuerdos. El
juez se construye después de que la corrida por hechos funcione y es lo primero que se
recorta si hay retraso.

## 6. Decisiones cerradas

- **Modelo de generación:** `qwen/qwen3.7-flash`. Prueba del 25-09 (`experiments/probar_modelos.py`,
  5 prompts, criterio fijado antes: tool correcta 5/5 → latencia → costo): qwen 5/5,
  `deepseek/deepseek-v4-flash` 4/5 (buscó política en vez de bloquear), `openai/gpt-5-nano` 3/5.
  Riesgo conocido: latencia de qwen de 2.7 a 17 s; revisar esfuerzo de razonamiento y p95 en
  los evals. Alternativa de respaldo: deepseek-v4-flash (rápido y más barato).
- **README** en español con resumen en inglés; **juez** híbrido (ver §5).
