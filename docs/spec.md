# Especificación · card-support-agent

> Versión 0.2 (borrador) · 25-09-2026 · Alcance: v1 para el hackathon del 26-09.
> Fuente de verdad del **qué**. Si algo es ambiguo, se corrige aquí antes de generar código.

## 1. Propósito

Un agente de soporte para "Tarjeta Nube" (tarjeta de crédito ficticia) que resuelve los
tickets más comunes sin intervención humana y escala el resto, con cada respuesta
trazable a su fuente y cada llamada medida en costo y latencia.

Caso de uso real: en fintech, un agente de soporte conectado a core, KYC y CRM atiende
tickets de estados de cuenta, movimientos, bloqueos y KYC pendiente.

## 2. Alcance v1

- Chat en Streamlit, con un cliente sintético seleccionado (sin autenticación real).
- **RAG** sobre 5 a 8 documentos de políticas en Markdown: chunking por `##`,
  embeddings, pgvector, top-k, respuesta con cita `[archivo — sección]`. El retrieval
  es una tool más; el LLM decide cuándo buscar (un solo bucle de tool calling, sin
  router previo).
- **Tools** (el LLM solo ve los argumentos listados; `cliente_id` y `tarjeta_id` los
  toma el código de la sesión, nunca del LLM, para que una inyección no pueda operar
  sobre otro cliente):
  - `buscar_politicas(pregunta)`: top-k de `policy_chunks` con su similitud.
  - `consultar_movimientos(desde, hasta)`: solo lectura, del cliente de la sesión.
  - `bloquear_tarjeta(motivo)`: simulada. La llamada del LLM no bloquea: el código
    guarda una `accion_pendiente` en la sesión y la UI muestra un botón "Confirmar
    bloqueo". Solo el clic ejecuta el bloqueo (compuerta determinista en código, no en
    el prompt). Cualquier otro mensaje descarta la acción pendiente.
  - `escalar_a_humano(motivo)`: inserta un ticket en `tickets`.
- **"No tengo esa información":** si `buscar_politicas` devuelve una mejor similitud
  bajo el umbral, el código responde eso directamente, sin segunda llamada al LLM. El
  umbral se calibra con los evals.
- **Trazas:** cada llamada al LLM y a embeddings se registra en `llm_calls`.
  El costo se toma de `usage.cost` de la respuesta de OpenRouter (verificado 25-09 en
  embeddings: `openai/text-embedding-3-small`, 1536 dims), sin tabla de precios propia.
- **Evals:** `python evals.py` corre el set fijo e imprime la tabla de métricas.

**Definition of done:** demo desplegada con tope de gasto; tabla de evals con al menos
80 % en respuesta correcta y 100 % en la compuerta de bloqueo (nunca bloquea sin
confirmación); costo por ticket y latencia p50/p95 reportados en el README.

**README:** en español, con un párrafo de resumen en inglés al inicio.

## 3. Fuera de alcance v1

WhatsApp u otros canales, autenticación, KYC real, datos reales, frameworks de agentes
(LangGraph, Anthropic SDK de agentes), Langfuse, re-ranking, chunking avanzado.
Candidatos para v2.

## 4. Datos (sintéticos)

- `customers` (5 a 10), `cards`, `transactions` (~30 días por cliente, con al menos un
  cargo "no reconocido" plausible por cliente de prueba).
- `policy_chunks` (texto, archivo, sección, `vector(1536)`).
- `tickets`, `llm_calls`.
- Documentos de políticas: cargos no reconocidos y aclaraciones, bloqueo y reposición,
  fecha de corte y pago, intereses y comisiones, estado de cuenta, KYC. Redacción propia,
  basada en información pública de CONDUSEF.

## 5. Evals

Set de 10 a 15 casos fijado **antes** de construir, en `evals/cases.jsonl`. Cada caso
lleva pregunta, cliente, respuesta esperada (hechos clave), fuente esperada y tool
esperada (o ninguna). Al menos: 2 fuera de alcance, 2 intentos de bloqueo sin
confirmación, 1 intento de prompt injection.

| Métrica | Definición |
|---|---|
| Respuesta correcta | Contiene los hechos clave esperados |
| Fuente correcta | La fuente esperada está en el top-5 recuperado (hit@5); `evals.py` llama al retrieval directo con la pregunta |
| Tool correcta | Se llamó la tool esperada (incluida `buscar_politicas` en dudas de políticas), o ninguna |
| Compuerta de bloqueo | Nunca bloquea sin confirmación |
| Rechazo fuera de alcance | Responde "no tengo esa información" cuando corresponde |
| Costo y latencia | Por caso; p50/p95 del set |

**Respuesta correcta:** la métrica oficial (la del DoD) es la coincidencia de hechos
clave en código: minúsculas, sin acentos, todos presentes. Por eso los hechos se
escriben como cifras y nombres, no como frases. Como segunda columna, sin peso en el
DoD, un LLM juez (modelo fijo por id exacto, distinto del generador, `temperature=0`)
devuelve `{"correcta": bool, "faltantes": [...]}`; la tabla marca los desacuerdos. El
juez se construye después de que la corrida por hechos funcione y es lo primero que se
recorta si hay retraso.

## 6. Decisiones cerradas

- **Modelo de generación:** `qwen/qwen3.7-flash`. Prueba del 25-09 (`experiments/probar_modelos.py`,
  5 prompts, criterio fijado antes: tool correcta 5/5 → latencia → costo): qwen 5/5,
  `deepseek/deepseek-v4-flash` 4/5 (buscó política en vez de bloquear), `openai/gpt-5-nano` 3/5.
  Riesgo conocido: latencia de qwen de 2.7 a 17 s; revisar esfuerzo de razonamiento y p95 en
  los evals. Alternativa de respaldo: deepseek-v4-flash (rápido y más barato).
- **README** en español con resumen en inglés; **juez** híbrido (ver §5).
