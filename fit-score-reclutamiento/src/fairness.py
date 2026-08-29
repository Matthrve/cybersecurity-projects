"""Auditoría de sesgos del resultado del scoring — NO se usa para calcular el score.

Solo audita proxies estructurales ya documentados en la literatura de sesgo en
contratación (prestigio de universidad, brechas de empleo). No infiere género,
etnia ni ninguna característica protegida a partir de nombres o fotos.
Ver docs/nota_uso_responsable.md.
"""
ADVERSE_IMPACT_THRESHOLD = 0.8  # regla del 80% (four-fifths rule)


def _bucket_brecha(meses: int) -> str:
    if meses == 0:
        return "sin_brecha"
    if meses < 12:
        return "brecha_corta (<1 año)"
    return "brecha_larga (>=1 año)"


def _group_rates(candidatos: list[dict], group_key_fn) -> dict:
    grupos: dict[str, list[bool]] = {}
    for c in candidatos:
        key = group_key_fn(c)
        grupos.setdefault(key, []).append(c["apto"])

    tasas = {k: sum(v) / len(v) for k, v in grupos.items() if v}
    max_tasa = max(tasas.values()) if tasas else 0
    resultado = {}
    for grupo, tasa in tasas.items():
        ratio = tasa / max_tasa if max_tasa > 0 else 1.0
        resultado[grupo] = {
            "n_candidatos": len(grupos[grupo]),
            "tasa_seleccion": round(tasa, 3),
            "ratio_vs_mejor_grupo": round(ratio, 3),
            "posible_sesgo": ratio < ADVERSE_IMPACT_THRESHOLD,
        }
    return resultado


def audit_fairness(candidatos_evaluados: list[dict]) -> dict:
    """`candidatos_evaluados` = [{"universidad_tier", "brecha_laboral_meses", "apto": bool}, ...]"""
    por_universidad = _group_rates(candidatos_evaluados, lambda c: c["universidad_tier"])
    por_brecha = _group_rates(candidatos_evaluados, lambda c: _bucket_brecha(c["brecha_laboral_meses"]))

    alertas = []
    for grupo, info in por_universidad.items():
        if info["posible_sesgo"]:
            alertas.append(
                f"Candidatos de universidad tier '{grupo}' tienen una tasa de selección "
                f"{info['ratio_vs_mejor_grupo']:.0%} respecto al grupo con mejor tasa (regla del 80%)."
            )
    for grupo, info in por_brecha.items():
        if info["posible_sesgo"]:
            alertas.append(
                f"Candidatos con '{grupo}' tienen una tasa de selección "
                f"{info['ratio_vs_mejor_grupo']:.0%} respecto al grupo con mejor tasa (regla del 80%)."
            )

    return {"por_universidad": por_universidad, "por_brecha_laboral": por_brecha, "alertas": alertas}
