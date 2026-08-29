"""Recomendaciones de upskilling para candidatos 'casi aptos' — convierte un rechazo en un plan de mejora."""
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CASI_APTO_MIN, CASI_APTO_MAX = 40, 70
MAX_RECOMENDACIONES = 3


def _load_resources() -> dict:
    with open(DATA_DIR / "upskilling_resources.json", encoding="utf-8") as f:
        return json.load(f)


def recommend(feats: dict, score_pct: float) -> list[dict]:
    if not (CASI_APTO_MIN <= score_pct <= CASI_APTO_MAX):
        return []

    resources = _load_resources()
    skills_gap = feats["skills_obligatorias_faltantes"] + feats["skills_deseables_faltantes"]

    recomendaciones = []
    for skill in skills_gap:
        if skill in resources:
            recomendaciones.append({"skill_faltante": skill, "recurso_sugerido": resources[skill]})
        if len(recomendaciones) >= MAX_RECOMENDACIONES:
            break
    return recomendaciones
