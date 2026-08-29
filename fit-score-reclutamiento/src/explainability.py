"""Explicabilidad del score con SHAP — qué features empujaron el resultado hacia arriba o abajo."""
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd
import shap

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"

FEATURE_LABELS = {
    "coverage_obligatorias": "Cobertura de skills obligatorias",
    "coverage_deseables": "Cobertura de skills deseables",
    "experiencia_ratio": "Años de experiencia vs. requerido",
    "educacion_match": "Nivel educativo vs. requerido",
    "similitud_semantica": "Similitud semántica CV↔vacante",
}


@lru_cache(maxsize=1)
def _load_bundle():
    bundle = joblib.load(MODELS_DIR / "fit_score_model.joblib")
    explainer = shap.TreeExplainer(bundle["model"])
    return bundle, explainer


def explain(feature_values: dict) -> list[dict]:
    bundle, explainer = _load_bundle()
    feature_names = bundle["feature_names"]
    X = pd.DataFrame([[feature_values[f] for f in feature_names]], columns=feature_names)

    shap_values = explainer(X)
    values = shap_values.values[0]
    if values.ndim > 1:  # algunas versiones devuelven [n_features, n_clases]
        values = values[:, -1]

    contribuciones = [
        {
            "feature": FEATURE_LABELS.get(f, f),
            "valor": round(float(feature_values[f]), 3),
            "impacto_shap": round(float(v), 3),
        }
        for f, v in zip(feature_names, values)
    ]
    return sorted(contribuciones, key=lambda c: -abs(c["impacto_shap"]))
