# Estado — card-support-agent

> Punto de retomada. Se sobrescribe cada sesión, no se acumula.
> Última actualización: 2026-09-26 (esquema local listo; ingesta por empezar)

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

1. El usuario escribe `ingesta.py` contra la BD local (`supabase start` si no está arriba).
   Paso 1 primero: partir `docs/politicas/*.md` por `##` e imprimir 32 chunks
   (5/6/6/5/5/5), descartando lo previo al primer `##`. Claude lo revisa antes de gastar
   en embeddings. Plan acordado: `texto` con encabezado de contexto (título del doc —
   sección; ojo "Reposición" existe en dos docs), una sola llamada de embeddings con
   lista, `delete` + `executemany` en una transacción, fila en `llm_calls` con
   `origen='ingesta'`. Éxito: 32 filas, costo > 0, reejecutar sigue dando 32.
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
