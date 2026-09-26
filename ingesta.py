import os
import time
from datetime import date
from pathlib import Path

import psycopg
from openai import OpenAI

POLITICAS = Path("docs/politicas")
MODELO_EMBEDDINGS = "openai/text-embedding-3-small"

client = OpenAI(base_url="https://openrouter.ai/api/v1",
                api_key=os.environ["OPENROUTER_API_KEY"])


def leer_chunks():
    """Parte cada política por secciones `##`; descarta el preámbulo previo a la primera."""
    chunks = []

    for ruta in sorted(POLITICAS.glob("*.md")):
        titulo = ""
        seccion = ""
        cuerpo = []

        def cerrar():
            if seccion:
                texto = "\n".join(cuerpo).strip()
                chunks.append({
                    "archivo": ruta.name,
                    "seccion": seccion,
                    # El encabezado distingue secciones homónimas (hay dos "Reposición").
                    "texto": f"{titulo} — {seccion}\n\n{texto}",
                })

        for linea in ruta.read_text(encoding="utf-8").splitlines():
            if linea.startswith("## "):
                cerrar()
                seccion = linea[3:].strip()
                cuerpo = []
            elif linea.startswith("# "):
                titulo = linea[2:].strip()
            elif seccion:
                cuerpo.append(linea)

        cerrar()

    return chunks


def embeber(textos):
    """Una sola llamada para todos los textos; devuelve los vectores y las métricas."""
    t0 = time.perf_counter()
    resp = client.embeddings.create(model=MODELO_EMBEDDINGS, input=textos)
    latencia_ms = int((time.perf_counter() - t0) * 1000)

    vectores = [d.embedding for d in sorted(resp.data, key=lambda d: d.index)]
    metricas = {
        "tokens": resp.usage.prompt_tokens,
        "costo": getattr(resp.usage, "cost", None) or 0,
        "latencia_ms": latencia_ms,
    }
    return vectores, metricas


def guardar(chunks, vectores, metricas):
    """Reemplaza policy_chunks y registra el costo, todo en una transacción."""
    filas = [(c["archivo"], c["seccion"], c["texto"], str(v))
             for c, v in zip(chunks, vectores, strict=True)]

    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            # delete + insert (no upsert): una sección borrada o renombrada no deja filas viejas.
            cur.execute("delete from policy_chunks")
            cur.executemany(
                "insert into policy_chunks (archivo, seccion, texto, embedding) "
                "values (%s, %s, %s, %s::extensions.vector)",
                filas,
            )
            cur.execute(
                "insert into llm_calls (session_id, origen, tipo, modelo, prompt_tokens, "
                "costo_usd, latencia_ms) values (%s, 'ingesta', 'embedding', %s, %s, %s, %s)",
                (f"ingesta-{date.today()}", MODELO_EMBEDDINGS,
                 metricas["tokens"], metricas["costo"], metricas["latencia_ms"]),
            )


if __name__ == "__main__":
    chunks = leer_chunks()
    vectores, metricas = embeber([c["texto"] for c in chunks])
    assert all(len(v) == 1536 for v in vectores), "dimensión distinta a vector(1536)"
    guardar(chunks, vectores, metricas)
    print(f"{len(chunks)} chunks guardados · {metricas['tokens']} tokens · "
          f"${metricas['costo']:.8f} USD · {metricas['latencia_ms']} ms")
