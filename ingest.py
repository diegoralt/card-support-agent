import os
import time
from datetime import date
from pathlib import Path

import psycopg
from openai import OpenAI

POLICIES_DIR = Path("docs/politicas")
EMBEDDING_MODEL = "openai/text-embedding-3-small"

client = OpenAI(base_url="https://openrouter.ai/api/v1",
                api_key=os.environ["OPENROUTER_API_KEY"])


def read_chunks():
    """Parte cada política por secciones `##`; descarta el preámbulo previo a la primera."""
    chunks = []

    for path in sorted(POLICIES_DIR.glob("*.md")):
        title = ""
        section = ""
        body = []

        def close_section():
            if section:
                text = "\n".join(body).strip()
                chunks.append({
                    "file": path.name,
                    "section": section,
                    # El encabezado distingue secciones homónimas (hay dos "Reposición").
                    "content": f"{title} — {section}\n\n{text}",
                })

        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("## "):
                close_section()
                section = line[3:].strip()
                body = []
            elif line.startswith("# "):
                title = line[2:].strip()
            elif section:
                body.append(line)

        close_section()

    return chunks


def embed(texts):
    """Una sola llamada para todos los textos; devuelve los vectores y las métricas."""
    t0 = time.perf_counter()
    resp = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    latency_ms = int((time.perf_counter() - t0) * 1000)

    vectors = [d.embedding for d in sorted(resp.data, key=lambda d: d.index)]
    metrics = {
        "tokens": resp.usage.prompt_tokens,
        "cost": getattr(resp.usage, "cost", None) or 0,
        "latency_ms": latency_ms,
    }
    return vectors, metrics


def save_chunks(chunks, vectors, metrics):
    """Reemplaza policy_chunks y registra el costo, todo en una transacción."""
    rows = [(c["file"], c["section"], c["content"], str(v))
            for c, v in zip(chunks, vectors, strict=True)]

    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            # delete + insert (no upsert): una sección borrada o renombrada no deja filas viejas.
            cur.execute("delete from policy_chunks")
            cur.executemany(
                "insert into policy_chunks (file, section, content, embedding) "
                "values (%s, %s, %s, %s::extensions.vector)",
                rows,
            )
            cur.execute(
                "insert into llm_calls (session_id, origin, kind, model, prompt_tokens, "
                "cost_usd, latency_ms) values (%s, 'ingest', 'embedding', %s, %s, %s, %s)",
                (f"ingest-{date.today()}", EMBEDDING_MODEL,
                 metrics["tokens"], metrics["cost"], metrics["latency_ms"]),
            )


if __name__ == "__main__":
    chunks = read_chunks()
    vectors, metrics = embed([c["content"] for c in chunks])
    assert all(len(v) == 1536 for v in vectors), "dimensión distinta a vector(1536)"
    save_chunks(chunks, vectors, metrics)
    print(f"{len(chunks)} chunks guardados · {metrics['tokens']} tokens · "
          f"${metrics['cost']:.8f} USD · {metrics['latency_ms']} ms")
