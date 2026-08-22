"""
Capa de Machine Learning del Mapa de Riesgos Digitales.

Usa un RandomForest pequeño (IA "ligera": entrena en segundos, sin GPU,
totalmente interpretable vía importancia de variables) para clasificar
el riesgo global de un perfil de hábitos en Bajo/Medio/Alto a partir de
las respuestas crudas del cuestionario.

La idea de diseño es que las reglas (reglas.py) dan el detalle explicable
por categoría, y el modelo aporta una lectura de patrón conjunto que no
depende de una fórmula lineal fija -- por ejemplo, puede aprender que
cierta combinación de hábitos es más riesgosa de lo que la suma simple
de puntos sugeriría.
"""

from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

RUTA_MODELO = Path(__file__).resolve().parent.parent / "models" / "modelo_riesgo.joblib"

COLUMNAS_BOOL = [
    "reutiliza_contraseñas",
    "usa_gestor",
    "usa_2fa",
    "cambia_password_tras_filtracion",
    "actualizaciones_automaticas",
    "actualiza_apps",
    "usa_wifi_publico_sin_vpn",
    "usa_vpn",
    "hace_clic_enlaces_desconocidos",
    "comparte_red_o_dispositivos",
    "hace_backups_regulares",
    "backups_automaticos_en_nube",
    "bloqueo_automatico",
    "disco_cifrado",
    "acceso_remoto_habilitado",
]
COLUMNAS_NUMERICAS = ["longitud_promedio", "dias_desde_actualizacion"]
COLUMNAS_FEATURES = COLUMNAS_BOOL + COLUMNAS_NUMERICAS
COLUMNA_OBJETIVO = "riesgo_categoria"


def _preparar_x(df: pd.DataFrame) -> pd.DataFrame:
    x = df[COLUMNAS_FEATURES].copy()
    for col in COLUMNAS_BOOL:
        x[col] = x[col].astype(int)
    return x


def entrenar(df: pd.DataFrame, semilla: int = 42) -> dict:
    x = _preparar_x(df)
    y = df[COLUMNA_OBJETIVO]

    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.2, random_state=semilla, stratify=y
    )

    modelo = RandomForestClassifier(
        n_estimators=150,
        max_depth=8,
        min_samples_leaf=3,
        random_state=semilla,
        class_weight="balanced",
    )
    modelo.fit(x_train, y_train)

    y_pred = modelo.predict(x_test)
    reporte = classification_report(y_test, y_pred, output_dict=True)
    exactitud = accuracy_score(y_test, y_pred)

    importancias = dict(zip(COLUMNAS_FEATURES, modelo.feature_importances_))

    return {
        "modelo": modelo,
        "exactitud": exactitud,
        "reporte": reporte,
        "importancias": importancias,
    }


def guardar_modelo(modelo: RandomForestClassifier, ruta: Path = RUTA_MODELO) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(modelo, ruta)


def cargar_modelo(ruta: Path = RUTA_MODELO) -> RandomForestClassifier:
    if not ruta.exists():
        raise FileNotFoundError(
            f"No se encontró el modelo en {ruta}. Ejecuta primero: python src/entrenar_modelo.py"
        )
    return joblib.load(ruta)


def predecir(modelo: RandomForestClassifier, respuestas: dict) -> dict:
    fila = pd.DataFrame([respuestas])
    x = _preparar_x(fila)
    prediccion = modelo.predict(x)[0]
    probabilidades = dict(zip(modelo.classes_, modelo.predict_proba(x)[0]))
    return {"categoria_predicha": prediccion, "probabilidades": probabilidades}
