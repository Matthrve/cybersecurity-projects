"""Justificación narrativa del score — sin LLM, cualitativa.

Deliberadamente NO repite los números crudos (esos viven en las métricas individuales,
ver explainability.py) ni la lista de skills detectadas/faltantes (esas ya se muestran
como chips en la tarjeta del candidato). Aquí solo va la interpretación en lenguaje natural.
"""


def build_justification(feats: dict, score_pct: float) -> str:
    mf = feats["model_features"]
    audit = feats["audit_only_fields"]
    faltantes_obl = feats["skills_obligatorias_faltantes"]
    faltantes_des = feats["skills_deseables_faltantes"]

    partes = []

    if score_pct >= 70:
        partes.append("Es una coincidencia sólida para el puesto.")
    elif score_pct >= 40:
        partes.append("Es un candidato parcial: cumple parte de lo requerido, pero no todo.")
    else:
        partes.append("No es un buen ajuste para este puesto en su estado actual.")

    if mf["coverage_obligatorias"] >= 0.99:
        partes.append("Cumple todas las habilidades obligatorias de la vacante.")
    elif faltantes_obl:
        n = len(faltantes_obl)
        partes.append(f"Le falta{'n' if n > 1 else ''} {n} habilidad{'es' if n > 1 else ''} obligatoria{'s' if n > 1 else ''} (ver chips en rojo abajo).")

    if faltantes_des:
        partes.append("También tiene margen de mejora en algunas habilidades deseables.")
    elif mf["coverage_deseables"] > 0:
        partes.append("Además cubre las habilidades deseables detectadas en el texto.")

    partes.append(f"Experiencia estimada: {audit['anios_experiencia']} años, nivel educativo {audit['nivel_educativo']}.")

    if mf["similitud_semantica"] < 0.3:
        partes.append(
            "La redacción del CV tiene baja similitud semántica con la vacante; conviene revisar "
            "manualmente por si el ajuste real es mejor de lo que sugiere el score."
        )

    return " ".join(partes)
