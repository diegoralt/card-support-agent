# Estado — card-support-agent

> Punto de retomada. Se sobrescribe cada sesión, no se acumula.
> Última actualización: 2026-09-26 (retrieval y umbral calibrados en local)

## Estado actual

- `docs/spec.md` v0.4: además de v0.3 (top-5, escalación, historial append-only, ticket =
  sesión, tope 20 mensajes), fija bloqueo en estado de sesión (no en `cards`), límites
  del bucle (5 iteraciones, 500 caracteres, timeout 30 s, validación de fechas), `origen`
  y `tools` en `llm_calls`, RLS sin políticas para anon, aviso de datos ficticios, evals
  con 3 corridas a temperature 0 y campos `previos`, `sin_pendiente`, hechos alternativos.
- `evals/cases.jsonl`: 23 casos (9 política, 3 movimientos, 2 escalación, 4 compuerta,
  2 injection, 3 fuera de alcance), validados contra políticas y seed. Commiteados.
- `supabase/`: migración `esquema_inicial` (6 tablas, pgvector HNSW coseno, RLS sin
  políticas, grants revocados a anon/authenticated). Probada en local: `supabase start`
  aplica migración + `db/seed.sql` (config apunta ahí), CHECKs/FK rechazan inválidos,
  coseno correcto, anon recibe `permission denied`. La app se conectará por Postgres
  directo (psycopg), no por REST. `llm_calls.origen` acepta `ingesta` (migración
  inicial editada: aún no se aplicó en remoto).
- `requirements.txt` (openai, psycopg) y `.env.example` (OPENROUTER_API_KEY,
  DATABASE_URL local). Sin `.env` aún: el usuario debe crearlo con su clave nueva.
- `ingesta.py` (generado por Claude a pedido del usuario): 32 chunks por `##` con
  encabezado de contexto, una llamada de embeddings (2,728 tokens, $0.0000546), delete +
  insert en una transacción, fila en `llm_calls`. Reejecutable (sigue en 32). Similitudes
  de prueba: la sección correcta queda arriba con ~0.64–0.68 y el resto ~0.57–0.58
  (margen estrecho: dato para calibrar el umbral).
- `retrieval.py` (generado por Claude a pedido): `buscar_politicas(pregunta, session_id,
  origen)` top-5 por coseno vía índice HNSW, registra embedding + chunks en `llm_calls`;
  `sobre_umbral()`, `como_contexto()` con citas. `python retrieval.py` recalibra: hit@5
  12/12; traslape (en alcance min 0.396 pol-09, fuera max 0.463 fa-03) → UMBRAL=0.38,
  fa-03 lo debe rechazar el LLM por prompt (spec §2).
- pgvector acepta `str(list)` de Python con cast `%s::extensions.vector` (probado).
- Embeddings de OpenRouter verificados (1536 dims, `usage.cost` en la respuesta).
- `experiments/probar_modelos.py`: prueba de modelos escrita por el usuario (qwen 5/5).
- `docs/politicas/`: 6 políticas ficticias con secciones `##` (corte y pago, intereses y
  comisiones, cargos no reconocidos, bloqueo, estado de cuenta, KYC).
- `db/seed.sql` generado por `db/gen_seed.py` (semilla fija): 6 clientes, 6 tarjetas,
  125 transacciones; un cargo no reconocido plantado por cliente (listado en el
  encabezado del seed); cliente 3 con KYC pendiente.
- `.venv` con Python 3.12.14 y `openai`. Repo git local en `main` con commit inicial; sin remoto.
- Clave de OpenRouter expuesta: ya expirada y eliminada.

## Siguiente acción

1. Bucle de tool calling (bloque 4–6.5 h): `agente.py` con las 4 tools (definiciones ya en
   `experiments/probar_modelos.py`), ids desde la sesión, compuerta `accion_pendiente`,
   límites (5 iteraciones, 500 caracteres, timeout 30 s, validación de fechas), system
   prompt con la regla "No tengo esa información" y formato `$1,899.00 MXN`, trazas.
2. Proyecto remoto de Supabase (usuario: crear, `supabase login`, `link`); Claude hace
   `db push --dry-run`, push y seed. `DATABASE_URL` del session pooler. Puede esperar al
   bloque de deploy.
3. `prohibidos` de inj-02 se completa cuando exista el system prompt.

El sábado (~12 h): 0–2 ingesta · 2–4 retrieval, citas y umbral · 4–6.5 bucle de tools,
compuerta, escalación · 6.5–8 `llm_calls` y `evals.py` (juez al final) · 8–10 Streamlit,
deploy, tope de gasto · 10–12 README y margen. Si hay retraso: primero el juez, luego el
pulido de la escalación, luego `consultar_movimientos`; evals por hechos y trazas nunca.

## Decisiones abiertas

- Repo remoto: dónde y si se publica al terminar el evento o tras revisar el README.
