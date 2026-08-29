"""Ingeniería de features: cobertura de skills, experiencia, educación y similitud semántica.

Diseño deliberado: los proxies usados para la auditoría de sesgos (universidad, brecha
laboral) NO entran como input del modelo de scoring — se calculan aparte y solo se usan
en fairness.py para auditar el resultado, nunca para producirlo. Ver docs/nota_uso_responsable.md.
"""
import re
from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

from taxonomy import skills_detected_set, strip_accents

NIVELES_EDUCACION = ["ninguno", "tecnico", "pregrado", "posgrado"]

UNIVERSIDADES_TIER = {
    "top": ["escuela politecnica nacional", "epn", "universidad san francisco de quito", "usfq",
            "escuela superior politecnica del litoral", "espol", "universidad de las fuerzas armadas", "espe"],
    "media": ["pontificia universidad catolica del ecuador", "puce", "universidad central del ecuador",
              "universidad tecnica particular de loja", "utpl", "universidad de cuenca"],
}

EXPERIENCE_YEAR_RE = re.compile(r"(\d+)\s*(?:\+)?\s*años?\s+de\s+experiencia", re.IGNORECASE)
DATE_RANGE_RE = re.compile(
    r"(20\d{2}|19\d{2})\s*[-–—]\s*(20\d{2}|19\d{2}|presente|actualidad)", re.IGNORECASE
)

EDUCATION_KEYWORDS = {
    # Frases específicas de declaración de título — no palabras sueltas, para no confundir
    # "ingeniería en Sistemas" (título) con "ingeniería inversa" o "ingeniería social" (skills),
    # ni "técnico en Redes" (título) con "soporte técnico" (una tarea, no un título).
    "posgrado": ["maestria en", "master en", "phd en", "doctorado en", "msc en", "estudios de posgrado"],
    "pregrado": ["ingenieria en", "licenciatura en", "titulo de ingeniero", "titulo profesional",
                 "pregrado completo", "titulo universitario"],
    "tecnico": ["tecnologo en", "titulo de tecnologo", "carrera tecnica", "instituto tecnico superior"],
}


@lru_cache(maxsize=1)
def _embedding_model() -> SentenceTransformer:
    return SentenceTransformer("all-MiniLM-L6-v2")


def semantic_similarity(text_a: str, text_b: str) -> float:
    model = _embedding_model()
    emb = model.encode([text_a, text_b], normalize_embeddings=True)
    return float(np.dot(emb[0], emb[1]))


def parse_experience_years(text: str) -> float:
    match = EXPERIENCE_YEAR_RE.search(text)
    if match:
        return float(match.group(1))

    ranges = DATE_RANGE_RE.findall(text)
    if not ranges:
        return 0.0
    total_months = 0
    for start, end in ranges:
        start_year = int(start)
        end_year = 2026 if end.lower() in ("presente", "actualidad") else int(end)
        total_months += max(0, (end_year - start_year) * 12)
    return round(total_months / 12, 1)


def parse_employment_gap_months(text: str) -> int:
    ranges = DATE_RANGE_RE.findall(text)
    periods = []
    for start, end in ranges:
        start_year = int(start)
        end_year = 2026 if end.lower() in ("presente", "actualidad") else int(end)
        periods.append((start_year, end_year))
    periods.sort()
    max_gap_years = 0
    for (_, prev_end), (next_start, _) in zip(periods, periods[1:]):
        max_gap_years = max(max_gap_years, next_start - prev_end)
    return max(0, max_gap_years) * 12


def parse_education_level(text: str) -> str:
    lowered = strip_accents(text.lower())
    for level in ("posgrado", "pregrado", "tecnico"):
        if any(strip_accents(kw) in lowered for kw in EDUCATION_KEYWORDS[level]):
            return level
    return "ninguno"


def _university_name_matches(name: str, lowered_text: str) -> bool:
    name = strip_accents(name)
    if " " in name:
        return name in lowered_text
    # Nombres cortos (siglas: epn, espe, usfq...) deben calzar como palabra completa,
    # si no "espe" hace falso positivo dentro de "especializarse".
    return re.search(rf"\b{re.escape(name)}\b", lowered_text) is not None


def parse_university_tier(text: str) -> str:
    lowered = strip_accents(text.lower())
    for tier, names in UNIVERSIDADES_TIER.items():
        if any(_university_name_matches(name, lowered) for name in names):
            return tier
    if "universidad" in lowered or "instituto" in lowered:
        return "otra"
    return "desconocida"


def build_feature_vector(cv_text: str, vacancy: dict) -> dict:
    """`vacancy` = {skills_obligatorias, skills_deseables, min_experiencia, educacion_minima, descripcion}"""
    detected = skills_detected_set(cv_text)
    obligatorias = set(vacancy["skills_obligatorias"])
    deseables = set(vacancy["skills_deseables"])

    coverage_obligatorias = len(detected & obligatorias) / len(obligatorias) if obligatorias else 1.0
    coverage_deseables = len(detected & deseables) / len(deseables) if deseables else 0.0

    years = parse_experience_years(cv_text)
    min_years = vacancy.get("min_experiencia", 0)
    experiencia_ratio = min(years / min_years, 1.5) if min_years else 1.0

    education = parse_education_level(cv_text)
    education_rank = NIVELES_EDUCACION.index(education)
    required_rank = NIVELES_EDUCACION.index(vacancy.get("educacion_minima", "ninguno"))
    educacion_match = 1.0 if education_rank >= required_rank else education_rank / max(required_rank, 1)

    similitud = semantic_similarity(cv_text, vacancy.get("descripcion", ""))

    model_features = {
        "coverage_obligatorias": coverage_obligatorias,
        "coverage_deseables": coverage_deseables,
        "experiencia_ratio": experiencia_ratio,
        "educacion_match": educacion_match,
        "similitud_semantica": similitud,
    }
    audit_only_fields = {
        "anios_experiencia": years,
        "nivel_educativo": education,
        "universidad_tier": parse_university_tier(cv_text),
        "brecha_laboral_meses": parse_employment_gap_months(cv_text),
    }
    return {
        "model_features": model_features,
        "audit_only_fields": audit_only_fields,
        "skills_detectadas": sorted(detected),
        "skills_obligatorias_faltantes": sorted(obligatorias - detected),
        "skills_deseables_faltantes": sorted(deseables - detected),
    }
