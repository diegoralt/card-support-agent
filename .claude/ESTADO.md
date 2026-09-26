# Estado — card-support-agent

> Punto de retomada. Se sobrescribe cada sesión, no se acumula.
> Última actualización: 2026-09-26 (spec v0.3: seis huecos cerrados)

## Estado actual

- `docs/spec.md` v0.3 cierra top-5, criterios de escalación, regla de búsqueda obligatoria,
  historial append-only (prompt caching, `cached_tokens` en trazas), ticket = sesión y
  tope de 20 mensajes por sesión. Antes ya cerraba: RAG como tool `buscar_politicas` con umbral en
  código, bloqueo con botón + `accion_pendiente`, ids desde la sesión, juez híbrido,
  modelo `qwen/qwen3.7-flash` (respaldo `deepseek/deepseek-v4-flash`).
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

1. El usuario revisa las políticas y el seed, y luego escribe `evals/cases.jsonl` (10–15 casos, spec §5) a partir de las políticas y
   del encabezado de `db/seed.sql`, con apoyo de Claude.
2. Proyecto de Supabase: esquema (`customers`, `cards`, `transactions`, `policy_chunks`,
   `tickets`, `llm_calls`) con la skill `nueva-migracion-supabase`; las columnas deben
   coincidir con `db/seed.sql`; `llm_calls` con `session_id` y `cached_tokens`. Luego cargar el seed.
3. `requirements.txt` cuando se agreguen dependencias (hoy solo `openai`).

El sábado (~12 h): 0–2 ingesta · 2–4 retrieval, citas y umbral · 4–6.5 bucle de tools,
compuerta, escalación · 6.5–8 `llm_calls` y `evals.py` (juez al final) · 8–10 Streamlit,
deploy, tope de gasto · 10–12 README y margen. Si hay retraso: primero el juez, luego el
pulido de la escalación, luego `consultar_movimientos`; evals por hechos y trazas nunca.

## Decisiones abiertas

- Repo remoto: dónde y si se publica al terminar el evento o tras revisar el README.
