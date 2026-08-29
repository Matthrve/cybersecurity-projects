"""Entrena el modelo de fit-score (núcleo de IA del proyecto) y lo evalúa con métricas reales."""
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score, classification_report

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MODELS_DIR = Path(__file__).resolve().parent.parent / "models"

MODEL_FEATURES = [
    "coverage_obligatorias",
    "coverage_deseables",
    "experiencia_ratio",
    "educacion_match",
    "similitud_semantica",
]


def main() -> None:
    df = pd.read_csv(DATA_DIR / "synthetic_dataset.csv")
    X = df[MODEL_FEATURES]
    y = df["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = GradientBoostingClassifier(
        n_estimators=150, max_depth=3, learning_rate=0.08, random_state=42
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    print("=== Métricas en holdout (20%) ===")
    print(f"Accuracy: {accuracy_score(y_test, y_pred):.3f}")
    print(f"F1-score: {f1_score(y_test, y_pred):.3f}")
    print(f"ROC-AUC:  {roc_auc_score(y_test, y_proba):.3f}")
    print(classification_report(y_test, y_pred, target_names=["no_apto", "apto"]))

    print("=== Importancia de features ===")
    for feat, imp in sorted(zip(MODEL_FEATURES, model.feature_importances_), key=lambda x: -x[1]):
        print(f"  {feat}: {imp:.3f}")

    MODELS_DIR.mkdir(exist_ok=True)
    joblib.dump({"model": model, "feature_names": MODEL_FEATURES}, MODELS_DIR / "fit_score_model.joblib")
    print(f"\nModelo guardado en {MODELS_DIR / 'fit_score_model.joblib'}")


if __name__ == "__main__":
    main()
