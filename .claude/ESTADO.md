# Estado — card-support-agent

> Punto de retomada. Se sobrescribe cada sesión, no se acumula.
> Última actualización: 2026-09-26 (demo desplegada y verificada en Streamlit Cloud)

## Estado actual

- Convención de idioma en `CLAUDE.md`: identificadores en inglés; comentarios, docstrings,
  descripciones de tools, prompts y UI en español. Todo el código, esquema, seed, evals y
  spec ya la siguen (`experiments/` se deja como registro histórico, con nombres viejos).
- `docs/spec.md` v0.6: top-5, escalación, historial append-only, ticket = sesión, tope 20
  mensajes, bloqueo en estado de sesión (no en `cards`), límites del bucle (5 iteraciones,
  500 caracteres, timeout 30 s, validación de fechas), `origin` y `tools` en `llm_calls`,
  RLS sin políticas para anon, aviso de datos ficticios, evals con 3 corridas a
  temperature 0, umbral 0.38 con segunda línea en el prompt, reasoning effort low,
  fecha de demo fija, re-llamar `block_card` ante confirmación por texto.
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
- `evals.py`: 23 casos × 3 corridas en 6 hilos (~1:45 min, ~$0.008). `python evals.py
  [ids]` filtra. Resultados en `evals/results/`: base 81 % respuesta correcta; corrida 2
  (tras 3 correcciones del medidor declaradas en spec §5) 95 %, compuerta 100 %, tool
  100 %, hit@5 12/12, fuera de alcance 100 %, $0.00012/ticket, p50 5.3 s, p95 16.9 s,
  1/69 timeouts. Fallo real persistente: pol-07 (premisa falsa / timeout).
- `app.py` (Streamlit 1.64): selector de cliente, chat, botón "Confirmar bloqueo" (única
  vía a `confirm_block`), aviso de datos ficticios, contador de 20 mensajes,
  `origin='demo'`. Verificado con `streamlit.testing.v1.AppTest` (flujo de bloqueo).
  Local: `set -a; source .env; set +a; .venv/bin/streamlit run app.py`.
- Supabase remoto: proyecto `card-support-agent` (ref `vzgrhasjncqocycdenfn`, us-east-1),
  enlazado. Migración + seed aplicados (migration list local = remoto), ingesta hecha (32
  chunks), anon REST → `permission denied` en todas las tablas, agente probado contra
  remoto. Se pausó `dr-kings-ia` (tope de 2 proyectos gratis).
- `.env`: `OPENROUTER_API_KEY` (límite duro $3), `DATABASE_URL` (local),
  `SUPABASE_DB_PASSWORD` y `REMOTE_DATABASE_URL` (session pooler). Para correr algo contra
  remoto: `DATABASE_URL="$REMOTE_DATABASE_URL" ...`.
- Repo en GitHub: https://github.com/diegoralt/card-support-agent (**público**, cuenta
  `gh` diegoralt, único colaborador), `main` con upstream `origin/main`. Historial
  revisado: sin secretos. Ruleset `protect-main`: sin borrado ni force push. Actions,
  wiki y projects desactivados. Externos solo pueden hacer fork/issues/PRs.
- Demo: https://card-support-agent.streamlit.app/ (cuenta Streamlit diegoralt, rama
  `main`, `app.py`, Python 3.12, secrets `OPENROUTER_API_KEY` y `DATABASE_URL` remoto).
  Verificada: bloqueo solo tras el botón, 2 filas `origin='demo'` en `llm_calls`
  (block_card 10 s / $0.00013). Tope de gasto = límite duro $3 de la clave.

## Siguiente acción

1. README (bloque 10–12 h): resumen en inglés, arquitectura, tabla de evals (base y
   corrida 2 con changelog), costo por ticket, p50/p95, hallazgos (qwen, umbral), URL de
   la demo.

El sábado (~12 h): 0–2 ingesta · 2–4 retrieval, citas y umbral · 4–6.5 bucle de tools,
compuerta, escalación · 6.5–8 `llm_calls` y `evals.py` (juez al final) · 8–10 Streamlit,
deploy, tope de gasto · 10–12 README y margen. Si hay retraso: primero el juez, luego el
pulido de la escalación, luego `get_transactions`; evals por hechos y trazas nunca.

## Decisiones abiertas

- Latencia p95 ~17 s (blq-02, pol-07, blq-01: razonamiento largo) y ~1/69 timeouts de 30 s.
  Opciones: aceptar y reportar; probar deepseek-v4-flash (respaldo de la spec) en los
  evals; o subir el límite. Pendiente de decidir con el usuario.
- Juez LLM (segunda columna, sin peso en el DoD): después de la UI si hay tiempo.

