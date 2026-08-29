"""Pruebas de los controles de seguridad: autenticación de administrador y sanitización de CSV."""
from auth import check_admin_password
from ui import build_csv, _csv_safe


def test_password_correcta_pasa():
    assert check_admin_password("admin123") is True


def test_password_incorrecta_falla():
    assert check_admin_password("cualquier-otra-cosa") is False


def test_password_vacia_falla():
    assert check_admin_password("") is False


def test_csv_safe_neutraliza_formulas_de_excel():
    for payload in ["=cmd|'/c calc'!A1", "+1+1", "-2+3", "@SUM(1,2)"]:
        safe = _csv_safe(payload)
        assert safe.startswith("'")
        assert safe[1:] == payload


def test_csv_safe_no_toca_texto_normal():
    assert _csv_safe("Juan Perez.pdf") == "Juan Perez.pdf"


def test_build_csv_sanitiza_nombre_de_archivo_malicioso():
    candidatos = [{
        "nombre": "=HYPERLINK(\"http://evil.example\",\"click\")",
        "score_pct": 50.0,
        "apto": False,
        "anomalia": {"es_atipico": False},
        "anios_experiencia": 1,
        "nivel_educativo": "pregrado",
        "universidad_tier": "desconocida",
        "skills_detectadas": [],
        "skills_obligatorias_faltantes": [],
        "skills_deseables_faltantes": [],
        "justificacion": "texto normal",
    }]
    csv_text = build_csv(candidatos)
    assert "'=HYPERLINK" in csv_text
    # nunca debe quedar una celda que empiece literalmente con '=' tras el nombre del candidato
    primera_fila_datos = csv_text.strip().split("\n")[1]
    assert not primera_fila_datos.startswith("=")
