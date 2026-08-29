"""Detección de CVs duplicados/plagiados dentro de un mismo lote de candidatos."""
import numpy as np

from features import _embedding_model

SIMILARITY_THRESHOLD = 0.93


def find_duplicates(candidatos: list[dict]) -> list[dict]:
    """`candidatos` = [{"nombre": str, "cv_text": str}, ...]. Devuelve pares sospechosos."""
    if len(candidatos) < 2:
        return []

    model = _embedding_model()
    textos = [c["cv_text"] for c in candidatos]
    embeddings = model.encode(textos, normalize_embeddings=True)

    pares_sospechosos = []
    for i in range(len(candidatos)):
        for j in range(i + 1, len(candidatos)):
            similitud = float(np.dot(embeddings[i], embeddings[j]))
            if similitud >= SIMILARITY_THRESHOLD:
                pares_sospechosos.append({
                    "candidato_a": candidatos[i]["nombre"],
                    "candidato_b": candidatos[j]["nombre"],
                    "similitud": round(similitud, 3),
                })
    return sorted(pares_sospechosos, key=lambda x: -x["similitud"])
