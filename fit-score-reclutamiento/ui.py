"""Capa visual: CSS inyectado + componentes HTML reutilizables. No toca la lógica del pipeline."""
import csv
import html as _html
import io


def esc(text) -> str:
    return _html.escape(str(text))


_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _csv_safe(value) -> str:
    """Evita CSV/Formula injection: un nombre de archivo como '=cmd|...'!A1' no debe
    interpretarse como fórmula al abrir el CSV en Excel/Sheets."""
    text = str(value)
    if text.startswith(_FORMULA_PREFIXES):
        return "'" + text
    return text


def build_csv(candidatos: list[dict]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "Candidato", "Score (%)", "Apto", "Atipico", "Anios experiencia", "Nivel educativo",
        "Universidad (tier)", "Skills detectadas", "Skills obligatorias faltantes",
        "Skills deseables faltantes", "Justificacion",
    ])
    for r in candidatos:
        writer.writerow([
            _csv_safe(r["nombre"]), f"{r['score_pct']:.1f}", "Si" if r["apto"] else "No",
            "Si" if r["anomalia"]["es_atipico"] else "No", r["anios_experiencia"], r["nivel_educativo"],
            r["universidad_tier"], "; ".join(r["skills_detectadas"]),
            "; ".join(r["skills_obligatorias_faltantes"]), "; ".join(r["skills_deseables_faltantes"]),
            _csv_safe(r["justificacion"]),
        ])
    return buffer.getvalue()


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;600;700;800&display=swap');

:root {
  --bg: #F5F6F7;
  --surface: #FFFFFF;
  --surface-2: #F0F1FE;
  --border: #E5E7EB;
  --text: #2D3235;
  --muted: #6B7280;
  --accent: #555ABF;
  --accent-dark: #31325C;
  --accent-soft: rgba(85,90,191,.35);
  --cta: #74E4A2;
  --cta-hover: #5FD891;
  --good: #16A34A;
  --warn: #D97706;
  --bad: #DC2626;
  --ease: cubic-bezier(.22,1,.36,1);
}

html, body, [class*="css"] { font-family: 'Source Sans 3', -apple-system, sans-serif; }
h1, h2, h3, h4, .brand-font { font-family: 'Source Sans 3', sans-serif !important; font-weight: 700 !important; }
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3,
[data-testid="stMarkdownContainer"] h4 { font-family: 'Source Sans 3', sans-serif !important; font-weight: 700 !important; }

@keyframes fadeInUp { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: translateY(0); } }
@keyframes growWidth { from { width: 0; } to { width: var(--w); } }
@keyframes pulseDot { 0%,100% { opacity: .5; transform: scale(1); } 50% { opacity: 1; transform: scale(1.25); } }
@keyframes floatSlow { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-6px); } }
@keyframes shimmer { 0% { background-position: -200% 0; } 100% { background-position: 200% 0; } }

* { transition-timing-function: var(--ease); }
.block-container { padding-top: 1.6rem; max-width: 1180px; }

/* ---- Hero: degradado índigo -> periwinkle, como onlinecv.es ---- */
.hero {
  position: relative; overflow: hidden;
  background: linear-gradient(90deg, var(--accent-dark) 0%, var(--accent) 100%);
  border-radius: 24px; padding: 2.4rem 2.6rem; margin-bottom: 1.6rem;
  animation: fadeInUp .6s var(--ease) both;
  box-shadow: 0 20px 45px -20px rgba(49,50,92,.55);
}
.hero::after {
  content: ""; position: absolute; right: -60px; top: -60px; width: 260px; height: 260px;
  background: radial-gradient(circle, rgba(116,228,162,.35), transparent 70%);
  border-radius: 50%; animation: floatSlow 6s ease-in-out infinite;
}
.hero .eyebrow {
  display: inline-flex; align-items: center; gap: .45rem;
  color: #C9CCFF; font-size: .78rem; font-weight: 700; letter-spacing: .09em; text-transform: uppercase;
}
.hero .eyebrow .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--cta); animation: pulseDot 1.8s infinite; }
.hero h1 { font-size: 2.15rem; font-weight: 800; margin: .55rem 0 .6rem; color: #fff; letter-spacing: -.01em; position: relative; }
.hero p.subtitle { color: #E4E5FB; font-size: 1.03rem; max-width: 780px; line-height: 1.55; margin: 0; position: relative; }
.chip-row { display: flex; gap: .55rem; flex-wrap: wrap; margin-top: 1.25rem; position: relative; }
.chip {
  background: rgba(255,255,255,.12); border: 1px solid rgba(255,255,255,.22); backdrop-filter: blur(2px);
  padding: .45rem .9rem; border-radius: 999px; font-size: .82rem; font-weight: 600; color: #fff;
  transition: all .25s var(--ease); white-space: nowrap;
}
.chip:hover { transform: translateY(-3px) scale(1.03); background: rgba(116,228,162,.25); border-color: var(--cta); }

/* ---- KPI cards ---- */
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(155px, 1fr)); gap: .9rem; margin: 0 0 1.6rem; }
.kpi-card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 16px; padding: 1rem 1.1rem; animation: fadeInUp .5s var(--ease) both;
  box-shadow: 0 2px 8px rgba(45,50,53,.05);
  transition: transform .22s var(--ease), box-shadow .22s var(--ease);
}
.kpi-card:hover { transform: translateY(-3px); box-shadow: 0 14px 28px -12px rgba(85,90,191,.28); }
.kpi-card .kpi-value { font-size: 1.75rem; font-weight: 800; color: var(--accent-dark); line-height: 1.1; }
.kpi-card .kpi-label { color: var(--muted); font-size: .74rem; text-transform: uppercase; letter-spacing: .06em; margin-top: .2rem; }

/* ---- Candidate cards ---- */
.cand-card {
  background: var(--surface); border: 1px solid var(--border); border-radius: 18px;
  padding: 1.1rem 1.3rem; margin-bottom: .6rem; animation: fadeInUp .5s var(--ease) both;
  box-shadow: 0 2px 8px rgba(45,50,53,.05);
  transition: transform .2s var(--ease), box-shadow .2s var(--ease), border-color .2s var(--ease);
}
.cand-card:hover { transform: translateY(-3px); border-color: var(--accent-soft); box-shadow: 0 16px 32px -14px rgba(85,90,191,.3); }
.cand-name { font-weight: 700; font-size: 1.06rem; color: var(--accent-dark); }
.cand-score { font-size: 1.9rem; font-weight: 800; line-height: 1; text-align: right; }
.cand-score-label { color: var(--muted); font-size: .7rem; text-align: right; margin-top: .15rem; }
.progress-track { height: 9px; border-radius: 999px; background: var(--surface-2); overflow: hidden; margin: .6rem 0 .4rem; }
.progress-fill { height: 100%; border-radius: 999px; animation: growWidth 1.1s var(--ease) both; }

.badge {
  display: inline-flex; align-items: center; gap: .3rem; padding: .2rem .6rem;
  border-radius: 999px; font-size: .71rem; font-weight: 700; letter-spacing: .01em; margin-right: .3rem;
  transition: transform .15s var(--ease);
}
.badge:hover { transform: translateY(-1px); }
.badge-ok { background: rgba(22,163,74,.12); color: #15803D; border: 1px solid rgba(22,163,74,.3); }
.badge-no { background: rgba(220,38,38,.1); color: #B91C1C; border: 1px solid rgba(220,38,38,.28); }
.badge-warn { background: rgba(217,119,6,.12); color: #B45309; border: 1px solid rgba(217,119,6,.3); }

.pill {
  display: inline-block; background: var(--surface-2); border: 1px solid var(--border);
  padding: .15rem .55rem; border-radius: 999px; font-size: .71rem; margin: .12rem .22rem .12rem 0; color: var(--text);
  transition: transform .15s var(--ease);
}
.pill:hover { transform: translateY(-1px); }
.pill-have { background: rgba(22,163,74,.08); border-color: rgba(22,163,74,.25); color: #15803D; }
.pill-missing { background: rgba(220,38,38,.06); border-color: rgba(220,38,38,.2); color: #B91C1C; }

/* ---- Alert cards ---- */
.alert {
  border-radius: 14px; padding: .85rem 1.05rem; margin-bottom: .55rem; border: 1px solid;
  display: flex; gap: .55rem; align-items: flex-start; animation: fadeInUp .4s var(--ease) both; font-size: .92rem;
  transition: transform .18s var(--ease);
}
.alert:hover { transform: translateX(2px); }
.alert-danger { background: rgba(220,38,38,.06); border-color: rgba(220,38,38,.22); color: #991B1B; }
.alert-ok { background: rgba(22,163,74,.07); border-color: rgba(22,163,74,.22); color: #166534; }
.alert-warn { background: rgba(217,119,6,.08); border-color: rgba(217,119,6,.24); color: #92400E; }
.section-note { color: var(--muted); font-size: .88rem; margin-bottom: .9rem; }

/* ---- Pasos "cómo funciona" ---- */
.steps-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 1.1rem; margin: 1.6rem 0; }
.step-card {
  text-align: center; padding: 1.6rem 1.1rem; animation: fadeInUp .5s var(--ease) both;
}
.step-num {
  width: 46px; height: 46px; margin: 0 auto .8rem; border-radius: 50%;
  background: linear-gradient(135deg, var(--accent-dark), var(--accent));
  color: #fff; font-weight: 800; font-size: 1.1rem; display: flex; align-items: center; justify-content: center;
  box-shadow: 0 8px 18px -8px rgba(85,90,191,.55); transition: transform .25s var(--ease);
}
.step-card:hover .step-num { transform: scale(1.1) rotate(-4deg); }
.step-title { font-weight: 700; color: var(--accent-dark); margin-bottom: .3rem; }
.step-desc { color: var(--muted); font-size: .88rem; line-height: 1.45; }

/* ---- Native widget touch-ups ---- */
section[data-testid="stSidebar"] { background: var(--surface); border-right: 1px solid var(--border); }
[data-testid="stFileUploaderDropzone"] {
  border: 1.5px dashed var(--accent-soft) !important; border-radius: 16px !important;
  background: var(--surface-2) !important; transition: all .25s var(--ease);
}
[data-testid="stFileUploaderDropzone"]:hover { border-color: var(--accent) !important; background: #E9EAFD !important; transform: scale(1.01); }

.stButton > button[kind="primary"] {
  background: var(--cta) !important; color: var(--accent-dark) !important; border: none !important;
  border-radius: 999px !important; font-weight: 700 !important; padding: .6rem 1.5rem !important;
  transition: all .22s var(--ease) !important; box-shadow: 0 4px 12px rgba(116,228,162,.4) !important;
}
.stButton > button[kind="primary"]:hover {
  background: var(--cta-hover) !important; transform: translateY(-2px) scale(1.02);
  box-shadow: 0 10px 22px rgba(116,228,162,.55) !important;
}
.stButton > button[kind="primary"]:active { transform: translateY(0) scale(.97); }
.stButton > button:not([kind="primary"]) { border-radius: 999px !important; transition: all .2s var(--ease) !important; }
.stButton > button:not([kind="primary"]):hover { transform: translateY(-1px); border-color: var(--accent) !important; color: var(--accent) !important; }

[data-testid="stDownloadButton"] > button {
  border-radius: 999px !important; transition: all .22s var(--ease) !important;
}
[data-testid="stDownloadButton"] > button:hover { transform: translateY(-2px); box-shadow: 0 8px 18px rgba(85,90,191,.2); }

[data-baseweb="tab-list"] { gap: .3rem; }
[data-baseweb="tab"] { border-radius: 10px 10px 0 0 !important; transition: all .2s var(--ease) !important; }
[data-testid="stExpander"] { border-radius: 14px !important; transition: box-shadow .2s var(--ease); }
[data-testid="stExpander"]:hover { box-shadow: 0 6px 18px rgba(45,50,53,.06); }

/* ---- Métricas individuales (por candidato) ---- */
.metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: .65rem; margin: .3rem 0 1.1rem; }
.metric-tile {
  background: var(--surface-2); border: 1px solid var(--border); border-radius: 12px;
  padding: .75rem .85rem; position: relative; animation: fadeInUp .4s var(--ease) both;
  transition: transform .18s var(--ease), box-shadow .18s var(--ease);
}
.metric-tile:hover { transform: translateY(-2px); box-shadow: 0 8px 16px rgba(45,50,53,.08); }
.metric-tile-dot { width: 8px; height: 8px; border-radius: 50%; position: absolute; top: .8rem; right: .8rem; }
.metric-tile-label { color: var(--muted); font-size: .7rem; margin-bottom: .35rem; padding-right: 1rem; line-height: 1.25; }
.metric-tile-value { font-size: 1.3rem; font-weight: 800; color: var(--accent-dark); }
.section-title { font-weight: 700; color: var(--accent-dark); font-size: .95rem; margin: .2rem 0 .5rem; }
</style>
"""


def score_tier(score_pct: float):
    if score_pct >= 70:
        return "#16A34A"
    if score_pct >= 40:
        return "#D97706"
    return "#DC2626"


def render_metric_tiles(shap_data: list[dict]) -> str:
    """Métricas individuales del candidato, separadas de la justificación narrativa."""
    tiles = []
    for i, c in enumerate(shap_data):
        color = "#16A34A" if c["impacto_shap"] >= 0 else "#DC2626"
        tiles.append(
            f'<div class="metric-tile" style="animation-delay:{i * 0.05}s">'
            f'<div class="metric-tile-dot" style="background:{color}"></div>'
            f'<div class="metric-tile-label">{esc(c["feature"])}</div>'
            f'<div class="metric-tile-value">{c["valor"] * 100:.0f}%</div>'
            f'</div>'
        )
    return f'<div class="metrics-grid">{"".join(tiles)}</div>'


def render_steps() -> str:
    steps = [
        ("1", "Configura la vacante", "Elige un puesto predefinido o crea uno nuevo con sus habilidades, experiencia y educación requeridas."),
        ("2", "Sube los CVs", "Arrastra uno o varios currículums en PDF, DOCX o TXT — se procesan en memoria, nunca se guardan."),
        ("3", "Obtén el ranking explicado", "Cada candidato recibe un score, su justificación, alertas de auditoría y recomendaciones."),
    ]
    cards = "".join(
        f'<div class="step-card" style="animation-delay:{i*0.1}s">'
        f'<div class="step-num">{n}</div>'
        f'<div class="step-title">{esc(t)}</div>'
        f'<div class="step-desc">{esc(d)}</div></div>'
        for i, (n, t, d) in enumerate(steps)
    )
    return f'<div class="steps-row">{cards}</div>'


def render_hero() -> str:
    chips = [
        "🧠 Modelo de ML entrenado (91% accuracy)",
        "🔍 Explicable con SHAP",
        "🛡️ Auditoría de sesgos automática",
        "🔁 Detección de CVs duplicados",
        "💯 100% local, sin API externa",
    ]
    chips_html = "".join(f'<span class="chip">{c}</span>' for c in chips)
    return f"""
    <div class="hero">
      <div class="eyebrow"><span class="dot"></span> Reclutamiento asistido por IA</div>
      <h1>Sistema Inteligente de Cribado y Auditoría de Talento</h1>
      <p class="subtitle">Convierte cientos de CVs en un ranking explicable en segundos: un modelo entrenado
      calcula el ajuste real al puesto, justifica cada decisión, detecta fraude entre candidatos y audita
      sus propios resultados en busca de sesgos — antes de que un humano descarte a nadie por error.</p>
      <div class="chip-row">{chips_html}</div>
    </div>
    """


def render_kpis(candidatos: list[dict], duplicados: list, alertas_sesgo: list) -> str:
    n = len(candidatos)
    n_aptos = sum(1 for c in candidatos if c["apto"])
    score_prom = sum(c["score_pct"] for c in candidatos) / n if n else 0
    n_alertas = len(duplicados) + len(alertas_sesgo) + sum(1 for c in candidatos if c["anomalia"]["es_atipico"])
    cards = [
        ("Candidatos evaluados", str(n)),
        ("Aptos", f"{n_aptos} / {n}"),
        ("Score promedio", f"{score_prom:.0f}%"),
        ("Alertas de auditoría", str(n_alertas)),
    ]
    cards_html = "".join(
        f'<div class="kpi-card" style="animation-delay:{i*0.05}s">'
        f'<div class="kpi-value">{esc(v)}</div><div class="kpi-label">{esc(k)}</div></div>'
        for i, (k, v) in enumerate(cards)
    )
    return f'<div class="kpi-grid">{cards_html}</div>'


def render_candidate_card(r: dict, idx: int) -> str:
    color = score_tier(r["score_pct"])
    badges = [f'<span class="badge {"badge-ok" if r["apto"] else "badge-no"}">{"✅ Apto" if r["apto"] else "❌ No apto"}</span>']
    if r["anomalia"]["es_atipico"]:
        badges.append('<span class="badge badge-warn">⚠️ Perfil atípico</span>')
    if r["upskilling"]:
        badges.append('<span class="badge badge-warn">📚 Casi apto</span>')

    skills_have = "".join(f'<span class="pill pill-have">{esc(s)}</span>' for s in r["skills_detectadas"][:8])
    faltantes = (r["skills_obligatorias_faltantes"] + r["skills_deseables_faltantes"])[:6]
    skills_missing = "".join(f'<span class="pill pill-missing">{esc(s)}</span>' for s in faltantes)
    missing_block = f'<div style="margin-top:.25rem;">{skills_missing}</div>' if skills_missing else ""

    return f"""
    <div class="cand-card" style="animation-delay:{idx * 0.06}s">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:1rem;flex-wrap:wrap;">
        <div style="flex:1;min-width:220px;">
          <div class="cand-name">{esc(r['nombre'])}</div>
          <div style="margin-top:.4rem;">{''.join(badges)}</div>
        </div>
        <div>
          <div class="cand-score" style="color:{color};">{r['score_pct']:.0f}%</div>
          <div class="cand-score-label">score de ajuste</div>
        </div>
      </div>
      <div class="progress-track"><div class="progress-fill" style="--w:{r['score_pct']}%;background:{color};"></div></div>
      <div style="margin-top:.5rem;">{skills_have}</div>
      {missing_block}
    </div>
    """


def render_alert(kind: str, text: str) -> str:
    icon = {"danger": "🚩", "ok": "✅", "warn": "⚠️"}[kind]
    return f'<div class="alert alert-{kind}">{icon}&nbsp; {text}</div>'
