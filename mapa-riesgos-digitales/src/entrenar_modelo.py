"""
Entrena el modelo de riesgo a partir de data/habitos_dataset.csv y lo guarda
en models/modelo_riesgo.joblib.

Ejecutar (después de generar el dataset):
    python src/entrenar_modelo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from modelo import entrenar, guardar_modelo

RUTA_DATASET = Path(__file__).resolve().parent.parent / "data" / "habitos_dataset.csv"


def main() -> None:
    # Evita texto ilegible (mojibake) al imprimir tildes/ñ en consolas de
    # Windows que no usan UTF-8 por defecto (cmd.exe, PowerShell clásico).
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    if not RUTA_DATASET.exists():
        raise FileNotFoundError(
            f"No se encontró {RUTA_DATASET}. Ejecuta primero: python src/generar_dataset.py"
        )

    df = pd.read_csv(RUTA_DATASET)
    resultado = entrenar(df)

    print(f"Exactitud en datos de prueba: {resultado['exactitud']:.2%}\n")
    print("Importancia de cada hábito para el modelo:")
    for var, imp in sorted(resultado["importancias"].items(), key=lambda kv: -kv[1]):
        print(f"  {var:35s} {imp:.3f}")

    guardar_modelo(resultado["modelo"])
    print("\nModelo guardado en models/modelo_riesgo.joblib")


if __name__ == "__main__":
    main()
