import json
import os
from datetime import date

import psycopg

from ingest import EMBEDDING_MODEL, embed

K = 5
# Calibrado con `python retrieval.py` (26-09): en alcance min 0.396 (pol-09), fuera de alcance
# max 0.463 (fa-03); los rangos se traslapan. Se prioriza no rechazar lo que está en alcance
# (ese error no tiene remedio); lo casi en dominio que pase lo rechaza el LLM por prompt.
THRESHOLD = 0.38


def search_policies(question, session_id, origin):
    """Top-K chunks por similitud coseno; registra la llamada de embeddings en llm_calls."""
    (vector,), metrics = embed([question])

    # ponytail: una conexión por búsqueda; pool si la latencia remota pesa.
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        # Se ordena por la distancia (no por la similitud calculada) para que use el índice HNSW.
        rows = conn.execute(
            "select id, file, section, content, "
            "1 - (embedding operator(extensions.<=>) %(v)s::extensions.vector) "
            "from policy_chunks "
            "order by embedding operator(extensions.<=>) %(v)s::extensions.vector "
            "limit %(k)s",
            {"v": str(vector), "k": K},
        ).fetchall()

        results = [
            {"id": id_, "file": file, "section": section, "content": content,
             "similarity": similarity, "citation": f"[{file} — {section}]"}
            for id_, file, section, content, similarity in rows
        ]

        conn.execute(
            "insert into llm_calls (session_id, origin, kind, model, prompt_tokens, "
            "cost_usd, latency_ms, chunks) values (%s, %s, 'embedding', %s, %s, %s, %s, %s)",
            (session_id, origin, EMBEDDING_MODEL, metrics["tokens"], metrics["cost"],
             metrics["latency_ms"],
             json.dumps([{"id": r["id"], "similarity": round(r["similarity"], 4)}
                         for r in results])),
        )

    return results


def above_threshold(results):
    """False = el código responde "no tengo esa información" sin volver a llamar al LLM."""
    return bool(results) and results[0]["similarity"] >= THRESHOLD


def as_context(results):
    """Texto que recibe el LLM como resultado de la tool: cada chunk con su cita."""
    return "\n\n".join(f"{r['citation']}\n{r['content']}" for r in results)


if __name__ == "__main__":
    # Calibración y hit@5: una búsqueda por caso de eval, sin LLM de chat.
    cases = [json.loads(l) for l in open("evals/cases.jsonl", encoding="utf-8")]
    session_id = f"calibration-{date.today()}"
    in_scope, out_of_scope = [], []

    for case in cases:
        res = search_policies(case["question"], session_id, "eval")
        top = res[0]["similarity"]
        hit = ""
        if case["source"]:
            expected = (case["source"]["file"], case["source"]["section"])
            hit = "hit" if expected in [(r["file"], r["section"]) for r in res] else "MISS"
            in_scope.append(top)
        elif case["type"] == "out_of_scope":
            out_of_scope.append(top)
        print(f"{case['id']:7} {case['type']:13} top={top:.3f} {hit:4} {res[0]['citation']}")

    print(f"\nen alcance: min={min(in_scope):.3f}  fuera de alcance: max={max(out_of_scope):.3f}  "
          f"umbral actual={THRESHOLD}")
    if min(in_scope) <= max(out_of_scope):
        print("TRASLAPE: ningún umbral separa ambos grupos; el umbral debe quedar bajo el "
              "mínimo en alcance y el prompt cubre lo casi en dominio.")
    print(f"rechazados en alcance: {sum(t < THRESHOLD for t in in_scope)}/{len(in_scope)}  "
          f"atrapados fuera de alcance: {sum(t < THRESHOLD for t in out_of_scope)}/{len(out_of_scope)}")
