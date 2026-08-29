"""Pipeline end-to-end: CV + vacante -> score, explicación, anomalías, upskilling.
Y a nivel de lote: ranking, duplicados entre candidatos, auditoría de sesgos.
"""
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd

from features import build_feature_vector
from explainability import explain
from justify import build_justification
from anomaly import score_anomaly
from upskilling import recommend
from duplicates import find_duplicates
from fairness import audit_fairness

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
APTO_THRESHOLD_PCT = 50


@lru_cache(maxsize=1)
def _fit_model_bundle():
    return joblib.load(MODELS_DIR / "fit_score_model.joblib")


def score_candidate(nombre: str, cv_text: str, vacancy: dict) -> dict:
    feats = build_feature_vector(cv_text, vacancy)
    bundle = _fit_model_bundle()
    model, feature_names = bundle["model"], bundle["feature_names"]

    X = pd.DataFrame([[feats["model_features"][f] for f in feature_names]], columns=feature_names)
    score_pct = float(model.predict_proba(X)[0][1] * 100)

    return {
        "nombre": nombre,
        "score_pct": round(score_pct, 1),
        "apto": score_pct >= APTO_THRESHOLD_PCT,
        "justificacion": build_justification(feats, score_pct),
        "explicacion_shap": explain(feats["model_features"]),
        "anomalia": score_anomaly(cv_text),
        "upskilling": recommend(feats, score_pct),
        "skills_detectadas": feats["skills_detectadas"],
        "skills_obligatorias_faltantes": feats["skills_obligatorias_faltantes"],
        "skills_deseables_faltantes": feats["skills_deseables_faltantes"],
        "universidad_tier": feats["audit_only_fields"]["universidad_tier"],
        "brecha_laboral_meses": feats["audit_only_fields"]["brecha_laboral_meses"],
        "anios_experiencia": feats["audit_only_fields"]["anios_experiencia"],
        "nivel_educativo": feats["audit_only_fields"]["nivel_educativo"],
    }


def score_batch(candidatos: list[dict], vacancy: dict) -> dict:
    """`candidatos` = [{"nombre": str, "cv_text": str}, ...]"""
    resultados = [score_candidate(c["nombre"], c["cv_text"], vacancy) for c in candidatos]
    resultados.sort(key=lambda r: -r["score_pct"])

    duplicados = find_duplicates(candidatos)
    auditoria = audit_fairness([
        {"universidad_tier": r["universidad_tier"], "brecha_laboral_meses": r["brecha_laboral_meses"], "apto": r["apto"]}
        for r in resultados
    ])

    return {"candidatos": resultados, "duplicados": duplicados, "auditoria_sesgos": auditoria}
