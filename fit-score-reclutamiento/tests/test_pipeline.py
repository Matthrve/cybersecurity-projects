"""Pruebas de integración del pipeline completo sobre los CVs de ejemplo (ejemplos/).

No son pruebas unitarias de cada función por separado: validan que el sistema completo
(parsing -> features -> modelo -> anomalías -> duplicados -> fairness) se comporta como
se espera frente a casos reales conocidos, ida y vuelta.
"""
from pathlib import Path

import pytest

from taxonomy import load_taxonomy
from scoring_pipeline import score_candidate, score_batch

EJEMPLOS_DIR = Path(__file__).resolve().parent.parent / "ejemplos"
TAXONOMY = load_taxonomy()


def _vacancy(family_key: str) -> dict:
    family = TAXONOMY["job_families"][family_key]
    return {
        "skills_obligatorias": family["skills_obligatorias"],
        "skills_deseables": family["skills_deseables"],
        "min_experiencia": family["min_experiencia"],
        "educacion_minima": family["educacion_minima"],
        "descripcion": f"Vacante: {family['titulo']}. Buscamos experiencia demostrable en el rol.",
    }


def _read(nombre: str) -> str:
    return (EJEMPLOS_DIR / nombre).read_text(encoding="utf-8")


def test_candidato_fuerte_ciberseguridad_score_alto():
    r = score_candidate("maria", _read("cv_maria_fuerte.txt"), _vacancy("analista_ciberseguridad"))
    assert r["score_pct"] >= 90
    assert r["apto"] is True
    assert r["skills_obligatorias_faltantes"] == []


def test_candidato_debil_ciberseguridad_score_bajo():
    r = score_candidate("carlos", _read("cv_carlos_debil.txt"), _vacancy("analista_ciberseguridad"))
    assert r["score_pct"] <= 20
    assert r["apto"] is False


def test_candidato_pentester_fuerte_score_alto():
    r = score_candidate("andrea", _read("cv_pentester_1_fuerte.txt"), _vacancy("pentester"))
    assert r["score_pct"] >= 90
    assert r["universidad_tier"] == "top"


def test_candidato_fuera_de_perfil_pentester_score_muy_bajo():
    r = score_candidate("carla", _read("cv_pentester_3_mismatch.txt"), _vacancy("pentester"))
    assert r["score_pct"] <= 10
    assert set(r["skills_obligatorias_faltantes"]) == {"pentesting", "owasp", "redes", "linux"}


def test_cv_con_keyword_stuffing_se_marca_como_atipico():
    r = score_candidate("stuffing", _read("cv_stuffing_sospechoso.txt"), _vacancy("analista_ciberseguridad"))
    assert r["anomalia"]["es_atipico"] is True


def test_cvs_casi_identicos_se_detectan_como_duplicados():
    candidatos = [
        {"nombre": "cv_maria_fuerte.txt", "cv_text": _read("cv_maria_fuerte.txt")},
        {"nombre": "cv_maria_duplicado.txt", "cv_text": _read("cv_maria_duplicado.txt")},
        {"nombre": "cv_carlos_debil.txt", "cv_text": _read("cv_carlos_debil.txt")},
    ]
    resultado = score_batch(candidatos, _vacancy("analista_ciberseguridad"))
    pares = {(d["candidato_a"], d["candidato_b"]) for d in resultado["duplicados"]}
    assert ("cv_maria_duplicado.txt", "cv_maria_fuerte.txt") in pares or ("cv_maria_fuerte.txt", "cv_maria_duplicado.txt") in pares
    # el CV muy distinto (Carlos) no debe aparecer en ningún par de duplicados
    nombres_en_pares = {n for par in pares for n in par}
    assert "cv_carlos_debil.txt" not in nombres_en_pares


def test_auditoria_sesgos_no_usa_universidad_ni_brecha_como_input_del_modelo():
    from features import build_feature_vector
    feats = build_feature_vector(_read("cv_maria_fuerte.txt"), _vacancy("analista_ciberseguridad"))
    # las claves usadas para el score del modelo no deben incluir proxies de auditoría
    assert "universidad_tier" not in feats["model_features"]
    assert "brecha_laboral_meses" not in feats["model_features"]


@pytest.mark.parametrize("family_key", list(TAXONOMY["job_families"].keys()))
def test_todas_las_vacantes_predefinidas_tienen_skills_obligatorias(family_key):
    family = TAXONOMY["job_families"][family_key]
    assert len(family["skills_obligatorias"]) > 0
