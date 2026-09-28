# Estado — card-support-agent

> Punto de retomada. Se sobrescribe cada sesión, no se acumula.
> Última actualización: 2026-09-28 (auditoría de seguridad; C1 y migración remota pendientes del usuario)

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
- Supabase remoto: proyecto `card-support-agent` (ref en `supabase/.temp`, no en el repo),
  enlazado. Migración + seed aplicados (migration list local = remoto), ingesta hecha (32
  chunks), anon REST → `permission denied` en todas las tablas, agente probado contra
  remoto.
- `.env`: `OPENROUTER_API_KEY` (con límite de crédito duro), `DATABASE_URL` (local),
  `SUPABASE_DB_PASSWORD` y `REMOTE_DATABASE_URL` (session pooler). Para correr algo contra
  remoto: `DATABASE_URL="$REMOTE_DATABASE_URL" ...`.
- Repo en GitHub: https://github.com/diegoralt/card-support-agent (**público**, cuenta
  `gh` diegoralt, único colaborador), `main` con upstream `origin/main`. Historial
  revisado: sin secretos. Ruleset `protect-main`: sin borrado ni force push. Actions,
  wiki y projects desactivados. Externos solo pueden hacer fork/issues/PRs.
- UI (26-09, generada por Claude): tema en `.streamlit/config.toml` (añil #2E3F8F, fondo
  #EEF2F5, Bricolage Grotesque + Figtree), tarjeta en HTML que pasa a gris con marca
  roja "Bloqueada", ejemplos clicables en pantalla vacía, citas como badge con título de
  la política, línea de tools por respuesta, folio del ticket junto a la tarjeta (consulta `tickets` por
  `session_id`), selector de cliente en la página (no en la barra lateral,
  que en celular se oculta), contador de espera propio en español (hilo en `app.py`,
  `chat()` no usa st), aviso emergente al crear un ticket. El botón se llama "Confirmar bloqueo" porque
  el system prompt lo nombra así. Probado en local (escritorio y 390 px) y en la demo pública (política, bloqueo con
  botón, aclaración → ticket #2 con `origin='demo'`). Captura en `docs/demo.png` (README).
- Demo: https://card-support-agent.streamlit.app/ (cuenta Streamlit diegoralt, rama
  `main`, `app.py`, Python 3.12, secrets `OPENROUTER_API_KEY` y `DATABASE_URL` remoto).
  Verificada: bloqueo solo tras el botón, 2 filas `origin='demo'` en `llm_calls`
  (block_card 10 s / $0.00013). Tope de gasto = límite de crédito de la clave + tope diario en `app.py`.


## Siguiente acción

Auditoría de seguridad del 28-09 antes de publicar en LinkedIn. Hecho por Claude: secret
scanning + push protection + Dependabot en GitHub; `showErrorDetails = "none"`; validación
de tipo de args de tools; tope diario global `DAILY_BUDGET_USD = 0.50` en `app.py`;
migración `20260928120000_demo_app_role.sql` (rol `demo_app` de mínimo privilegio con
políticas RLS propias; probada en local, dry-run remoto = solo esa). Pendiente del usuario:
1. C1: la clave de OpenRouter del `.env` EXPIRÓ (401). Crear otra (30 días, límite duro),
   ponerla en `.env` y en los secrets de Streamlit; luego `python ingest.py` en local
   (el `db reset` de la migración vació `policy_chunks` local).
2. Aplicar la migración en remoto (`supabase db push`; el clasificador de Claude Code lo
   bloqueó), fijar contraseña de `demo_app` fuera del repo y cambiar `DATABASE_URL` de
   Streamlit a `demo_app.<ref>` con `?sslmode=require`. Luego Claude verifica la demo.
3. 2FA en GitHub, Supabase y OpenRouter; despertar la demo antes de publicar (dormida
   tarda >2.5 min en arrancar).

El sábado (~12 h): 0–2 ingesta · 2–4 retrieval, citas y umbral · 4–6.5 bucle de tools,
compuerta, escalación · 6.5–8 `llm_calls` y `evals.py` (juez al final) · 8–10 Streamlit,
deploy, tope de gasto · 10–12 README y margen. Si hay retraso: primero el juez, luego el
pulido de la escalación, luego `get_transactions`; evals por hechos y trazas nunca.

## Decisiones abiertas

- Ninguna bloqueante.
