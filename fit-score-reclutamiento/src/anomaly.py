"""Detección de CVs atípicos (posible keyword-stuffing o texto artificial) con IsolationForest."""
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest

from taxonomy import skills_detected_set

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
ANOMALY_FEATURES = ["densidad_skills"]


def _with_density(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["densidad_skills"] = df["n_skills_detectadas"] / df["n_palabras_cv"].clip(lower=1)
    return df


def train() -> None:
    df = pd.read_csv(DATA_DIR / "synthetic_dataset.csv")
    df = _with_density(df)
    model = IsolationForest(contamination=0.05, random_state=42, n_estimators=200)
    model.fit(df[ANOMALY_FEATURES])
    MODELS_DIR.mkdir(exist_ok=True)
    joblib.dump({"model": model, "feature_names": ANOMALY_FEATURES}, MODELS_DIR / "isolation_forest.joblib")
    print(f"[anomaly] Modelo de anomalías guardado en {MODELS_DIR / 'isolation_forest.joblib'}")


def score_anomaly(cv_text: str) -> dict:
    bundle = joblib.load(MODELS_DIR / "isolation_forest.joblib")
    model, feature_names = bundle["model"], bundle["feature_names"]

    n_skills = len(skills_detected_set(cv_text))
    n_words = max(1, len(cv_text.split()))
    densidad = n_skills / n_words

    all_fields = {"n_skills_detectadas": n_skills, "n_palabras_cv": n_words, "densidad_skills": densidad}
    row = pd.DataFrame([[all_fields[f] for f in feature_names]], columns=feature_names)
    raw_score = model.decision_function(row)[0]
    is_outlier = model.predict(row)[0] == -1

    motivo = None
    if is_outlier:
        if densidad > 0.15:
            motivo = "Densidad de habilidades muy alta respecto al texto — posible keyword-stuffing."
        elif n_words < 30:
            motivo = "Texto demasiado corto para un CV real."
        elif densidad < 0.02:
            motivo = "Densidad de habilidades inusualmente baja — revisar si el CV está incompleto, mal formateado o realmente no aplica al puesto."
        else:
            motivo = "Perfil estadísticamente atípico respecto al resto de candidatos."

    return {"es_atipico": bool(is_outlier), "score_anomalia": float(raw_score), "motivo": motivo}


if __name__ == "__main__":
    train()
