"""
Genera un dataset sintético de hábitos digitales para entrenar el modelo de ML.

Cada fila simula el cuestionario de un usuario. Usamos el propio motor de
reglas (reglas.py) para calcular un puntaje de riesgo "real" de cada perfil
simulado, le sumamos ruido aleatorio (para imitar que la vida real no es tan
limpia como una fórmula) y lo convertimos en una categoría de riesgo
(Bajo/Medio/Alto). El modelo de ML luego aprende a predecir esa categoría
a partir de las respuestas crudas, sin ver los puntajes de las reglas.

Ejecutar:
    python src/generar_dataset.py
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from reglas import evaluar_todo

N_PERFILES = 1200
SEMILLA = 42


def generar_perfil(rng: np.random.Generator) -> dict:
    # Sesgo aleatorio por perfil: simula que hay personas más o menos
    # cuidadosas en general (sus respuestas no son totalmente independientes).
    cuidado = rng.beta(2, 2)  # 0 = descuidado, 1 = muy cuidadoso

    def booleano(prob_si_cuidadoso: float, prob_si_descuidado: float) -> bool:
        p = prob_si_descuidado + cuidado * (prob_si_cuidadoso - prob_si_descuidado)
        return bool(rng.random() < p)

    return {
        # Contraseñas
        "reutiliza_contraseñas": booleano(0.10, 0.85),
        "longitud_promedio": int(np.clip(rng.normal(8 + cuidado * 10, 3), 4, 24)),
        "usa_gestor": booleano(0.75, 0.05),
        "usa_2fa": booleano(0.85, 0.05),
        "cambia_password_tras_filtracion": booleano(0.80, 0.10),
        # Actualizaciones
        "actualizaciones_automaticas": booleano(0.85, 0.15),
        "dias_desde_actualizacion": int(np.clip(rng.exponential(10 + (1 - cuidado) * 80), 0, 365)),
        "actualiza_apps": booleano(0.85, 0.15),
        # Redes
        "usa_wifi_publico_sin_vpn": booleano(0.10, 0.75),
        "usa_vpn": booleano(0.60, 0.05),
        "hace_clic_enlaces_desconocidos": booleano(0.03, 0.45),
        "comparte_red_o_dispositivos": booleano(0.10, 0.55),
        # Respaldo
        "hace_backups_regulares": booleano(0.80, 0.10),
        "backups_automaticos_en_nube": booleano(0.70, 0.10),
        # Dispositivo (acceso físico)
        "bloqueo_automatico": booleano(0.85, 0.15),
        "disco_cifrado": booleano(0.55, 0.05),
        "acceso_remoto_habilitado": booleano(0.05, 0.20),
    }


def etiquetar_riesgo(puntaje_con_ruido: float) -> str:
    if puntaje_con_ruido < 35:
        return "Bajo"
    if puntaje_con_ruido < 65:
        return "Medio"
    return "Alto"


def generar_dataset(n: int = N_PERFILES, semilla: int = SEMILLA) -> pd.DataFrame:
    rng = np.random.default_rng(semilla)
    filas = []

    for _ in range(n):
        perfil = generar_perfil(rng)
        evaluacion = evaluar_todo(perfil)

        ruido = rng.normal(0, 8)  # variabilidad que las reglas no capturan del todo
        puntaje_con_ruido = float(np.clip(evaluacion["puntaje_global_reglas"] + ruido, 0, 100))

        fila = dict(perfil)
        fila["riesgo_categoria"] = etiquetar_riesgo(puntaje_con_ruido)
        filas.append(fila)

    return pd.DataFrame(filas)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")

    df = generar_dataset()
    salida = "data/habitos_dataset.csv"
    df.to_csv(salida, index=False)
    print(f"Dataset generado: {salida} ({len(df)} perfiles)")
    print(df["riesgo_categoria"].value_counts())
