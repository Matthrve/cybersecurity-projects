"""Genera data/synthetic_dataset.csv: CVs y vacantes sintéticas con etiqueta ground-truth transparente.

Metodología de etiquetado (documentada para la defensa, ver README.md):
El label de "fit" se calcula con una fórmula ponderada explícita sobre
cobertura de skills, experiencia y educación (+ruido gaussiano, para que la
frontera no sea perfectamente separable). La similitud semántica por
embeddings NO forma parte de esa fórmula: es una señal "libre" que el modelo
puede aprovechar para generalizar mejor que la heurística que generó el label,
igual que pasaría con un dataset real donde el reclutador no ve explícitamente
un número de similitud semántica al etiquetar.
"""
import json
import random
from pathlib import Path

import pandas as pd

from taxonomy import load_taxonomy
from features import build_feature_vector

random.seed(42)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CANDIDATES_PER_FAMILY = 160
LABEL_THRESHOLD = 0.62
NOISE_STD = 0.08

UNIVERSIDADES = {
    "top": ["Escuela Politécnica Nacional", "Universidad San Francisco de Quito",
            "Escuela Superior Politécnica del Litoral"],
    "media": ["Pontificia Universidad Católica del Ecuador", "Universidad Central del Ecuador"],
    "otra": ["Universidad de Otavalo", "Instituto Tecnológico Superior Central Técnico"],
    "desconocida": [],
}

EXPERIENCE_TEMPLATES = [
    "{empresa} ({inicio} - {fin}): {actividad}",
]
ACTIVIDADES = [
    "Desarrollo y mantenimiento de soluciones usando {skills}.",
    "Responsable de proyectos que involucraron {skills}.",
    "Colaboración en equipo multidisciplinario aplicando {skills}.",
    "Diseño e implementación de soluciones con {skills}.",
]
EMPRESAS = ["TechCorp", "Soluciones Andinas", "Nubelix", "DataWorks", "SecureNet", "Innovatech", "CloudPeak"]


def _sample_skills(taxonomy: dict, vacancy: dict, overlap_level: str) -> set[str]:
    obligatorias = set(vacancy["skills_obligatorias"])
    deseables = set(vacancy["skills_deseables"])
    all_skills = set(taxonomy["skills"].keys())
    ajenas = all_skills - obligatorias - deseables

    if overlap_level == "alto":
        picked = set(random.sample(sorted(obligatorias), k=len(obligatorias))) if obligatorias else set()
        picked |= set(random.sample(sorted(deseables), k=min(len(deseables), random.randint(1, len(deseables) or 1)))) if deseables else set()
    elif overlap_level == "medio":
        picked = set(random.sample(sorted(obligatorias), k=max(1, len(obligatorias) // 2))) if obligatorias else set()
        picked |= set(random.sample(sorted(deseables), k=random.randint(0, max(1, len(deseables) // 2)))) if deseables else set()
    else:  # bajo
        picked = set(random.sample(sorted(obligatorias), k=random.randint(0, max(1, len(obligatorias) // 3)))) if obligatorias else set()

    picked |= set(random.sample(sorted(ajenas), k=random.randint(1, 4)))
    return picked


def _build_cv_text(skills: set[str], experiencia_anios: float, educacion: str, universidad_tier: str,
                    brecha_meses: int, taxonomy: dict) -> str:
    skill_labels = []
    for s in skills:
        aliases = taxonomy["skills"][s]["aliases"]
        skill_labels.append(random.choice(aliases))

    lineas = []
    if random.random() < 0.7:
        lineas.append(f"Resumen: profesional con {int(experiencia_anios)} años de experiencia.")

    fin_actual = 2026
    inicio = fin_actual - int(experiencia_anios) if experiencia_anios >= 1 else fin_actual - 1
    if brecha_meses >= 12 and experiencia_anios >= 2:
        mid = inicio + (fin_actual - inicio) // 2
        gap_years = brecha_meses // 12
        periodos = [(inicio, mid), (mid + gap_years, fin_actual)]
    else:
        periodos = [(inicio, fin_actual)]

    for start, end in periodos:
        empresa = random.choice(EMPRESAS)
        actividad = random.choice(ACTIVIDADES).format(skills=", ".join(skill_labels[:4]) or "tareas generales")
        fin_txt = "presente" if end >= fin_actual else str(end)
        lineas.append(EXPERIENCE_TEMPLATES[0].format(empresa=empresa, inicio=start, fin=fin_txt, actividad=actividad))

    educ_txt = {
        "posgrado": "Maestría en su área de especialización.",
        "pregrado": "Ingeniería en su área de especialización (pregrado completo).",
        "tecnico": "Tecnólogo en su área de especialización.",
        "ninguno": "",
    }[educacion]
    if educ_txt:
        universidad = random.choice(UNIVERSIDADES[universidad_tier]) if UNIVERSIDADES[universidad_tier] else ""
        lineas.append(f"Educación: {educ_txt} {('- ' + universidad) if universidad else ''}".strip())

    lineas.append("Habilidades: " + ", ".join(skill_labels))
    return "\n".join(lineas)


def _vacancy_descripcion(taxonomy: dict, family_key: str, family: dict) -> str:
    obligatorias = [taxonomy["skills"][s]["aliases"][0] for s in family["skills_obligatorias"]]
    deseables = [taxonomy["skills"][s]["aliases"][0] for s in family["skills_deseables"]]
    return (
        f"Vacante: {family['titulo']}. Buscamos experiencia mínima de {family['min_experiencia']} años, "
        f"educación mínima {family['educacion_minima']}. Requisitos obligatorios: {', '.join(obligatorias)}. "
        f"Deseables: {', '.join(deseables)}."
    )


def generate(n_per_family: int = CANDIDATES_PER_FAMILY) -> pd.DataFrame:
    taxonomy = load_taxonomy()
    rows = []
    cv_id = 0

    for family_key, family in taxonomy["job_families"].items():
        vacancy = {
            "skills_obligatorias": family["skills_obligatorias"],
            "skills_deseables": family["skills_deseables"],
            "min_experiencia": family["min_experiencia"],
            "educacion_minima": family["educacion_minima"],
            "descripcion": _vacancy_descripcion(taxonomy, family_key, family),
        }

        for _ in range(n_per_family):
            cv_id += 1
            overlap_level = random.choices(["alto", "medio", "bajo"], weights=[0.35, 0.4, 0.25])[0]
            skills = _sample_skills(taxonomy, vacancy, overlap_level)

            base_exp = family["min_experiencia"]
            experiencia_anios = max(0, round(random.gauss(base_exp, 1.8), 1))
            educacion = random.choices(
                ["ninguno", "tecnico", "pregrado", "posgrado"], weights=[0.1, 0.2, 0.5, 0.2]
            )[0]
            universidad_tier = random.choices(
                ["top", "media", "otra", "desconocida"], weights=[0.2, 0.25, 0.35, 0.2]
            )[0]
            brecha_meses = random.choices([0, 6, 14, 24], weights=[0.6, 0.15, 0.15, 0.1])[0]

            cv_text = _build_cv_text(skills, experiencia_anios, educacion, universidad_tier, brecha_meses, taxonomy)
            feats = build_feature_vector(cv_text, vacancy)
            mf = feats["model_features"]

            raw_score = (
                0.45 * mf["coverage_obligatorias"]
                + 0.25 * mf["coverage_deseables"]
                + 0.15 * min(mf["experiencia_ratio"], 1.2) / 1.2
                + 0.15 * mf["educacion_match"]
            )
            noisy_score = raw_score + random.gauss(0, NOISE_STD)
            label = int(noisy_score >= LABEL_THRESHOLD)

            rows.append({
                "cv_id": cv_id,
                "job_family": family_key,
                **mf,
                "label": label,
                **feats["audit_only_fields"],
                "n_skills_detectadas": len(feats["skills_detectadas"]),
                "n_palabras_cv": len(cv_text.split()),
            })

        print(f"[synthetic_data] {family_key}: {n_per_family} candidatos generados")

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = generate()
    out_path = DATA_DIR / "synthetic_dataset.csv"
    df.to_csv(out_path, index=False)
    print(f"[synthetic_data] Guardado {len(df)} filas en {out_path}")
    print(f"[synthetic_data] Balance de clases:\n{df['label'].value_counts(normalize=True)}")
