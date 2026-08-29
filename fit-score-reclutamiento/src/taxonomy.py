"""Taxonomía de skills y extracción por coincidencia exacta + fuzzy matching (sin LLM)."""
import json
import re
import unicodedata
from pathlib import Path
from functools import lru_cache

from rapidfuzz import fuzz

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FUZZY_THRESHOLD = 90
TOKEN_RE = re.compile(r"[a-z0-9#\+\.]+")


def strip_accents(text: str) -> str:
    """Normaliza tildes/diéresis (los CVs reales las usan, la taxonomía se define sin ellas)."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


@lru_cache(maxsize=1)
def load_taxonomy() -> dict:
    with open(DATA_DIR / "skills_taxonomy.json", encoding="utf-8") as f:
        return json.load(f)


def tokenize(text: str) -> list[str]:
    text = strip_accents(text.lower())
    tokens = TOKEN_RE.findall(text)
    return [t.strip(".") for t in tokens if t.strip(".")]


def _ngrams(tokens: list[str], n: int) -> list[str]:
    return [" ".join(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]


def _max_alias_words(taxonomy: dict) -> int:
    return max(
        len(alias.split())
        for meta in taxonomy["skills"].values()
        for alias in meta["aliases"]
    )


def extract_skills(text: str) -> dict:
    """Devuelve {skill_id: {"detectado": bool, "evidencia": str, "fuzzy": bool}} para toda la taxonomía."""
    taxonomy = load_taxonomy()
    tokens = tokenize(text)
    max_n = _max_alias_words(taxonomy)
    grams_by_n = {n: set(_ngrams(tokens, n)) for n in range(1, max_n + 1)}

    results = {}
    for skill_id, meta in taxonomy["skills"].items():
        found = False
        evidence = None
        is_fuzzy = False

        for alias in meta["aliases"]:
            alias = strip_accents(alias.lower())
            n = len(alias.split())
            if alias in grams_by_n.get(n, ()):
                found, evidence, is_fuzzy = True, alias, False
                break

        if not found:
            best_score, best_gram = 0, None
            for alias in meta["aliases"]:
                alias = strip_accents(alias.lower())
                n = len(alias.split())
                for gram in grams_by_n.get(n, ()):
                    if abs(len(gram) - len(alias)) > 2:
                        continue
                    score = fuzz.ratio(alias, gram)
                    if score > best_score:
                        best_score, best_gram = score, gram
            if best_score >= FUZZY_THRESHOLD:
                found, evidence, is_fuzzy = True, best_gram, True

        results[skill_id] = {"detectado": found, "evidencia": evidence, "fuzzy": is_fuzzy}
    return results


def skills_detected_set(text: str) -> set[str]:
    detected = extract_skills(text)
    return {skill for skill, info in detected.items() if info["detectado"]}
