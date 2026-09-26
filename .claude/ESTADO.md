# Estado — card-support-agent

> Punto de retomada. Se sobrescribe cada sesión, no se acumula.
> Última actualización: 2026-09-26 (spec v0.4 + 23 casos de eval)

## Estado actual

- `docs/spec.md` v0.4: además de v0.3 (top-5, escalación, historial append-only, ticket =
  sesión, tope 20 mensajes), fija bloqueo en estado de sesión (no en `cards`), límites
  del bucle (5 iteraciones, 500 caracteres, timeout 30 s, validación de fechas), `origen`
  y `tools` en `llm_calls`, RLS sin políticas para anon, aviso de datos ficticios, evals
  con 3 corridas a temperature 0 y campos `previos`, `sin_pendiente`, hechos alternativos.
- `evals/cases.jsonl`: 23 casos (9 política, 3 movimientos, 2 escalación, 4 compuerta,
  2 injection, 3 fuera de alcance), validados contra políticas y seed. Sin commit: el
  usuario los está revisando.
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

1. El usuario termina de revisar `evals/cases.jsonl` y la spec v0.4; luego commit. Puntos
   frágiles conocidos: alternativas de pol-08 y mov-03; `prohibidos` de inj-02 se
   completa con fragmentos del system prompt cuando exista.
2. Proyecto de Supabase: esquema (`customers`, `cards`, `transactions`, `policy_chunks`,
   `tickets`, `llm_calls`) con la skill `nueva-migracion-supabase`; las columnas deben
   coincidir con `db/seed.sql`; `llm_calls` con `session_id`, `origen`, `cached_tokens` y `tools`;
   `tickets` con `origen`; RLS en todas. Luego cargar el seed.
3. `requirements.txt` cuando se agreguen dependencias (hoy solo `openai`).

El sábado (~12 h): 0–2 ingesta · 2–4 retrieval, citas y umbral · 4–6.5 bucle de tools,
compuerta, escalación · 6.5–8 `llm_calls` y `evals.py` (juez al final) · 8–10 Streamlit,
deploy, tope de gasto · 10–12 README y margen. Si hay retraso: primero el juez, luego el
pulido de la escalación, luego `consultar_movimientos`; evals por hechos y trazas nunca.

## Decisiones abiertas

- Repo remoto: dónde y si se publica al terminar el evento o tras revisar el README.
