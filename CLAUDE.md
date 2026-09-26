# card-support-agent

Agente de soporte para una tarjeta de crédito ficticia: responde dudas de políticas con
RAG y citas, consulta movimientos, bloquea la tarjeta (simulado) con confirmación
explícita y escala a un humano lo que no puede resolver. Se construye en un hackathon
de un día (sábado 26-09-2026, ~12 h, solo, tema libre; se permite llegar con base de código).

Objetivo de aprendizaje: Python real, RAG, tool calling, evals y observabilidad de LLMs.
La spec vive en `docs/spec.md`; si algo es ambiguo, se corrige ahí antes de generar código.

## Reglas de trabajo (críticas)

- **Modo de aprendizaje.** El usuario escribe las piezas clave: chunking, embeddings e
  ingesta, retrieval, bucle de tool calling, compuerta de confirmación, evals. Claude
  explica, propone el siguiente paso, revisa y corrige; **no genera esas piezas completas**
  salvo que el usuario lo pida explícitamente para un bloque concreto. El usuario viene
  de Kotlin/Java y tiene Python a nivel de scripts sencillos: explicar el idiom de Python
  cuando aparezca por primera vez.
- Claude puede generar sin pedir permiso: boilerplate, datos sintéticos, SQL de esquema,
  UI de Streamlit, README.
- **Datos 100 % sintéticos.** Nada de datos personales reales. El repo será público.
- **Políticas:** redactadas para el proyecto, basadas en información pública (CONDUSEF),
  sin copiar documentos de terceros.
- Secretos solo en `.env` (gitignored). Nunca commitear claves.
- Los evals y las trazas no se recortan por tiempo: son la evidencia del proyecto.

## Stack

| Pieza | Elección |
|---|---|
| Lenguaje | Python 3.12 + venv |
| LLM | OpenRouter vía SDK `openai` (`base_url=https://openrouter.ai/api/v1`) |
| Embeddings | OpenRouter `/api/v1/embeddings`, `text-embedding-3-small` |
| Datos y vectores | Supabase Postgres + pgvector (HNSW, coseno) |
| Agente | Bucle de tool calling escrito a mano, sin framework |
| Evals | Script propio que imprime una tabla de métricas |
| Observabilidad | Tabla `llm_calls` (tokens, latencia, costo, tools, chunks, similitud) |
| UI y demo | Streamlit en Streamlit Community Cloud |

## Presupuesto

Clave de OpenRouter exclusiva del proyecto, con límite de crédito duro. La demo pública
debe tener tope de gasto antes de publicar la URL.
