import json
import os
from datetime import date

import psycopg

from ingesta import MODELO_EMBEDDINGS, embeber

K = 5
# Calibrado con `python retrieval.py` (26-09): en alcance min 0.396 (pol-09), fuera de alcance
# max 0.463 (fa-03); los rangos se traslapan. Se prioriza no rechazar lo que está en alcance
# (ese error no tiene remedio); lo casi en dominio que pase lo rechaza el LLM por prompt.
UMBRAL = 0.38


def buscar_politicas(pregunta, session_id, origen):
    """Top-K chunks por similitud coseno; registra la llamada de embeddings en llm_calls."""
    (vector,), metricas = embeber([pregunta])

    # ponytail: una conexión por búsqueda; pool si la latencia remota pesa.
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        # Se ordena por la distancia (no por la similitud calculada) para que use el índice HNSW.
        filas = conn.execute(
            "select id, archivo, seccion, texto, "
            "1 - (embedding operator(extensions.<=>) %(v)s::extensions.vector) "
            "from policy_chunks "
            "order by embedding operator(extensions.<=>) %(v)s::extensions.vector "
            "limit %(k)s",
            {"v": str(vector), "k": K},
        ).fetchall()

        resultados = [
            {"id": id_, "archivo": archivo, "seccion": seccion, "texto": texto,
             "similitud": similitud, "cita": f"[{archivo} — {seccion}]"}
            for id_, archivo, seccion, texto, similitud in filas
        ]

        conn.execute(
            "insert into llm_calls (session_id, origen, tipo, modelo, prompt_tokens, "
            "costo_usd, latencia_ms, chunks) values (%s, %s, 'embedding', %s, %s, %s, %s, %s)",
            (session_id, origen, MODELO_EMBEDDINGS, metricas["tokens"], metricas["costo"],
             metricas["latencia_ms"],
             json.dumps([{"id": r["id"], "similitud": round(r["similitud"], 4)}
                         for r in resultados])),
        )

    return resultados


def sobre_umbral(resultados):
    """False = el código responde "no tengo esa información" sin volver a llamar al LLM."""
    return bool(resultados) and resultados[0]["similitud"] >= UMBRAL


def como_contexto(resultados):
    """Texto que recibe el LLM como resultado de la tool: cada chunk con su cita."""
    return "\n\n".join(f"{r['cita']}\n{r['texto']}" for r in resultados)


if __name__ == "__main__":
    # Calibración y hit@5: una búsqueda por caso de eval, sin LLM de chat.
    casos = [json.loads(l) for l in open("evals/cases.jsonl", encoding="utf-8")]
    session_id = f"calibracion-{date.today()}"
    en_alcance, fuera = [], []

    for caso in casos:
        res = buscar_politicas(caso["pregunta"], session_id, "eval")
        top = res[0]["similitud"]
        hit = ""
        if caso["fuente"]:
            esperada = (caso["fuente"]["archivo"], caso["fuente"]["seccion"])
            hit = "hit" if esperada in [(r["archivo"], r["seccion"]) for r in res] else "MISS"
            en_alcance.append(top)
        elif caso["tipo"] == "fuera_alcance":
            fuera.append(top)
        print(f"{caso['id']:7} {caso['tipo']:13} top={top:.3f} {hit:4} {res[0]['cita']}")

    print(f"\nen alcance: min={min(en_alcance):.3f}  fuera de alcance: max={max(fuera):.3f}  "
          f"umbral actual={UMBRAL}")
    if min(en_alcance) <= max(fuera):
        print("TRASLAPE: ningún umbral separa ambos grupos; el umbral debe quedar bajo el "
              "mínimo en alcance y el prompt cubre lo casi en dominio.")
    print(f"rechazados en alcance: {sum(t < UMBRAL for t in en_alcance)}/{len(en_alcance)}  "
          f"atrapados fuera de alcance: {sum(t < UMBRAL for t in fuera)}/{len(fuera)}")
