# Estado — card-support-agent

> Punto de retomada. Se sobrescribe cada sesión, no se acumula.
> Última actualización: 2026-09-26 (agente con tool calling funcionando en local)

## Estado actual

- Convención de idioma en `CLAUDE.md`: identificadores en inglés; comentarios, docstrings,
  descripciones de tools, prompts y UI en español. Todo el código, esquema, seed, evals y
  spec ya la siguen (`experiments/` se deja como registro histórico, con nombres viejos).
- `docs/spec.md` v0.5: top-5, escalación, historial append-only, ticket = sesión, tope 20
  mensajes, bloqueo en estado de sesión (no en `cards`), límites del bucle (5 iteraciones,
  500 caracteres, timeout 30 s, validación de fechas), `origin` y `tools` en `llm_calls`,
  RLS sin políticas para anon, aviso de datos ficticios, evals con 3 corridas a
  temperature 0, umbral 0.38 con segunda línea en el prompt.
- Tools: `search_policies(question)`, `get_transactions(from_date, to_date)`,
  `block_card(reason)` → `pending_action`, `escalate_to_human(reason)`.
- `evals/cases.jsonl`: 23 casos (claves `type`, `customer_id`, `prior_messages`,
  `question`, `facts`, `forbidden`, `source`, `tool`, `no_pending`).
- `supabase/migrations/20260926120000_initial_schema.sql`: 6 tablas, pgvector HNSW coseno,
  RLS sin políticas, grants revocados. Solo en local (editable hasta el primer push).
  App por Postgres directo (psycopg), no REST.
- `ingest.py`: 32 chunks por `##` con encabezado de contexto, una llamada de embeddings
  (2,728 tokens, $0.0000546), delete + insert en transacción, fila en `llm_calls`.
- `retrieval.py`: `search_policies(question, session_id, origin)`, `above_threshold()`,
  `as_context()`. `python retrieval.py` recalibra: hit@5 12/12; traslape (en alcance min
  0.396 pol-09, fuera max 0.463 fa-03) → THRESHOLD=0.38.
- `agent.py` (generado por Claude a pedido): `start_session(customer_id, origin)`,
  `chat(session, text)` → `{text, pending_action, tools, error}`, `confirm_block(session)`
  (única vía de bloqueo, para el botón de la UI). 4 tools con ids de la sesión, umbral en
  código, límites (5 iteraciones, 500 caracteres, 20 mensajes, 30 s totales vía hilo,
  90 días), trazas en `llm_calls`, `TODAY` fijo 2026-09-26, `reasoning.effort=low`.
  `python -u agent.py <cliente>` es un REPL de prueba (`/confirmar` = botón). Prueba de
  humo: 6/6 conductas correctas, p50 4.3 s / p95 6.9 s, caché funcionando.
- `.env` del usuario configurado (clave OpenRouter con límite duro $3, sin reinicio).
- Repo git local en `main`, sin remoto.

## Siguiente acción

1. `evals.py` (bloque 6.5–8 h): corre `evals/cases.jsonl` contra `agent.chat` con
   `origin='eval'`, 3 corridas por caso, normalización (minúsculas, sin acentos, sin comas
   ni `$`), hechos con alternativas, `forbidden`, `tool` (ausente = no se evalúa),
   `no_pending`, chequeos estructurales (sesión no bloqueada; `llm_calls.tools` con el
   `customer_id` de la sesión), hit@5 por retrieval directo, costo y p50/p95 por
   `session_id`. Juez LLM al final (lo primero que se recorta).
2. Proyecto remoto de Supabase (usuario: crear, `supabase login`, `link`); Claude hace
   `db push --dry-run`, push y seed. `DATABASE_URL` del session pooler. Puede esperar al
   bloque de deploy.

El sábado (~12 h): 0–2 ingesta · 2–4 retrieval, citas y umbral · 4–6.5 bucle de tools,
compuerta, escalación · 6.5–8 `llm_calls` y `evals.py` (juez al final) · 8–10 Streamlit,
deploy, tope de gasto · 10–12 README y margen. Si hay retraso: primero el juez, luego el
pulido de la escalación, luego `get_transactions`; evals por hechos y trazas nunca.

## Decisiones abiertas

- Repo remoto: dónde y si se publica al terminar el evento o tras revisar el README.
