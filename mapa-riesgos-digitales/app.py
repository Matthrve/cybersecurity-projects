"""
Mapa de Riesgos Digitales — app Streamlit.

Combina un motor de reglas explicable (src/reglas.py) con un modelo de
Machine Learning ligero (src/modelo.py) para evaluar hábitos de
contraseñas, actualizaciones, uso de redes y respaldo, y sugerir mejoras
priorizadas. Guarda cada evaluación en un historial local (src/historial.py)
y, en Windows, puede contrastar tus respuestas contra señales reales del
equipo (src/senales_sistema.py).

Ejecutar:
    streamlit run app.py
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from generar_dataset import etiquetar_riesgo  # noqa: E402
from historial import (  # noqa: E402
    borrar_historial,
    guardar_evaluacion,
    inicializar_db,
    obtener_historial,
)
from modelo import cargar_modelo, predecir  # noqa: E402
from plan_accion import generar_plan_accion  # noqa: E402
from reglas import CATEGORIAS, evaluar_todo  # noqa: E402
from senales_sistema import comparar_con_respuestas, disponible, obtener_senales_sistema  # noqa: E402

st.set_page_config(page_title="Mapa de Riesgos Digitales", page_icon="🛡️", layout="wide")

NOMBRES_CATEGORIA = {
    "contraseñas": "Contraseñas",
    "actualizaciones": "Actualizaciones",
    "redes": "Redes",
    "respaldo": "Respaldo",
    "dispositivo": "Dispositivo",
}
ICONO_CATEGORIA = {
    "contraseñas": "🔑",
    "actualizaciones": "🔄",
    "redes": "📶",
    "respaldo": "💾",
    "dispositivo": "💻",
}
COLOR_RIESGO = {"Bajo": "#16a34a", "Medio": "#d97706", "Alto": "#dc2626"}
FONDO_RIESGO = {"Bajo": "rgba(22,163,74,0.12)", "Medio": "rgba(217,119,6,0.12)", "Alto": "rgba(220,38,38,0.12)"}
ICONO_RIESGO = {"Bajo": "🟢", "Medio": "🟡", "Alto": "🔴"}
ETIQUETA_SEVERIDAD = {"alto": "Alto", "medio": "Medio", "bajo": "Bajo"}
ETIQUETA_ESFUERZO = {"bajo": "🟢 esfuerzo bajo", "medio": "🟡 esfuerzo medio", "alto": "🔴 esfuerzo alto"}

COLOR_SERIE_HISTORIAL = {
    "puntaje_global": "#0f172a",
    "puntaje_contrasenas": "#7c3aed",
    "puntaje_actualizaciones": "#0ea5e9",
    "puntaje_redes": "#f97316",
    "puntaje_respaldo": "#14b8a6",
}


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

html, body, .stApp, .stApp * { font-family: 'Inter', sans-serif; }

/* Oculta el "chrome" por defecto de Streamlit (hamburguesa, Deploy, franja
   de color superior) para que se sienta menos "app de desarrollo" y más
   página terminada. */
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] {
    visibility: hidden;
    height: 0;
}
.block-container, [data-testid="stAppViewBlockContainer"] {
    padding-top: 2rem;
    padding-bottom: 2rem;
    max-width: 1200px;
}

/* Unifica el look de los controles nativos de Streamlit con el resto del
   diseño (por defecto se ven genéricos y desentonan con las tarjetas). */
button[kind="primary"] {
    background: linear-gradient(135deg, #0f172a 0%, #334155 100%) !important;
    border: none !important;
    border-radius: 10px !important;
}
button[kind="primary"]:hover {
    background: linear-gradient(135deg, #1e293b 0%, #475569 100%) !important;
}
[data-testid="stCheckbox"] { margin-bottom: -0.35rem; }
[data-testid="stSlider"] { padding-top: .3rem; padding-bottom: .1rem; }
[data-baseweb="slider"] div[role="slider"] { background-color: #0f172a !important; }
[data-testid="stTabs"] [aria-selected="true"] { color: #0f172a; font-weight: 700; }
[data-testid="stMetricValue"] { font-weight: 800; }

.hero {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 55%, #334155 100%);
    color: #f8fafc;
    padding: 2rem 2.2rem;
    border-radius: 16px;
    margin-bottom: 1.4rem;
}
.hero h1 { margin: 0 0 .4rem 0; font-size: 1.9rem; font-weight: 800; }
.hero p { margin: 0; color: #cbd5e1; font-size: .98rem; line-height: 1.5; max-width: 760px; }
.hero-chips { margin-top: 1rem; display: flex; gap: .6rem; flex-wrap: wrap; }
.hero-chip {
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.15);
    padding: .35rem .8rem;
    border-radius: 999px;
    font-size: .82rem;
    color: #e2e8f0;
}

.card-title {
    font-weight: 700;
    font-size: 1.05rem;
    margin-bottom: .3rem;
    display: flex;
    align-items: center;
    gap: .45rem;
}
.card-hint { color: #64748b; font-size: .82rem; margin: -.2rem 0 .6rem 0; }

.risk-hero {
    border-radius: 16px;
    padding: 1.4rem 1.6rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    flex-wrap: wrap;
}
.risk-hero .label { font-size: .85rem; text-transform: uppercase; letter-spacing: .06em; opacity: .75; }
.risk-hero .value { font-size: 2.2rem; font-weight: 800; line-height: 1.1; }
.risk-hero .sub { font-size: .88rem; margin-top: .2rem; opacity: .85; }

.kpi-row { display: flex; gap: .8rem; flex-wrap: wrap; margin-top: .8rem; }
.kpi {
    flex: 1;
    min-width: 150px;
    border: 1px solid rgba(148,163,184,0.35);
    border-radius: 12px;
    padding: .8rem 1rem;
}
.kpi .kpi-label { font-size: .78rem; color: #64748b; text-transform: uppercase; letter-spacing: .05em; }
.kpi .kpi-value { font-size: 1.5rem; font-weight: 800; margin-top: .15rem; }

.alert-card {
    border-radius: 12px;
    border: 1px solid rgba(148,163,184,0.3);
    border-left: 5px solid var(--sev-color);
    padding: .75rem 1rem;
    margin-bottom: .6rem;
}
.alert-card .cat { font-size: .72rem; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; color: var(--sev-color); }
.alert-card .desc { font-weight: 600; margin: .15rem 0 .3rem 0; }
.alert-card .rec { font-size: .9rem; color: #475569; }
.alert-card .impacto { font-size: .88rem; font-weight: 700; margin-top: .4rem; }

.discrepancia {
    border-radius: 10px;
    border: 1px dashed #d97706;
    background: rgba(217,119,6,0.08);
    padding: .6rem .9rem;
    margin-bottom: .5rem;
    font-size: .9rem;
}

.footer-note { color: #94a3b8; font-size: .8rem; margin-top: 1.5rem; }
</style>
"""


@st.cache_resource
def obtener_modelo():
    return cargar_modelo()


@st.cache_resource
def _asegurar_db():
    inicializar_db()
    return True


def hex_a_rgba(color_hex: str, alpha: float) -> str:
    color_hex = color_hex.lstrip("#")
    r, g, b = (int(color_hex[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def radar_riesgo(puntajes: dict, color: str) -> go.Figure:
    categorias = [NOMBRES_CATEGORIA[c] for c in CATEGORIAS]
    valores = [puntajes[c] for c in CATEGORIAS]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=valores + [valores[0]],
        theta=categorias + [categorias[0]],
        fill="toself",
        name="Riesgo por categoría",
        line=dict(color=color, width=2),
        fillcolor=hex_a_rgba(color, 0.25),
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], gridcolor="rgba(148,163,184,0.35)"),
            angularaxis=dict(gridcolor="rgba(148,163,184,0.35)"),
        ),
        showlegend=False,
        margin=dict(l=40, r=40, t=30, b=30),
        height=340,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def gauge_riesgo(puntaje: int, color: str) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=puntaje,
        number={"suffix": "/100", "font": {"size": 34}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1},
            "bar": {"color": color, "thickness": 0.35},
            "bgcolor": "rgba(0,0,0,0)",
            "steps": [
                {"range": [0, 35], "color": FONDO_RIESGO["Bajo"]},
                {"range": [35, 65], "color": FONDO_RIESGO["Medio"]},
                {"range": [65, 100], "color": FONDO_RIESGO["Alto"]},
            ],
        },
    ))
    fig.update_layout(height=220, margin=dict(l=25, r=25, t=15, b=10), paper_bgcolor="rgba(0,0,0,0)")
    return fig


def barras_confianza(probabilidades: dict) -> go.Figure:
    orden = ["Bajo", "Medio", "Alto"]
    valores = [probabilidades.get(cat, 0) * 100 for cat in orden]
    fig = go.Figure(go.Bar(
        x=valores,
        y=orden,
        orientation="h",
        marker_color=[COLOR_RIESGO[cat] for cat in orden],
        text=[f"{v:.0f}%" for v in valores],
        textposition="outside",
    ))
    fig.update_layout(
        xaxis=dict(range=[0, 100], title=None, showgrid=False, ticksuffix="%"),
        yaxis=dict(title=None),
        height=220,
        margin=dict(l=10, r=25, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def grafico_historial(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["fecha"], y=df["puntaje_global"], mode="lines+markers", name="Global",
        line=dict(color=COLOR_SERIE_HISTORIAL["puntaje_global"], width=3),
        marker=dict(size=7),
    ))
    series = [
        ("puntaje_contrasenas", "Contraseñas"),
        ("puntaje_actualizaciones", "Actualizaciones"),
        ("puntaje_redes", "Redes"),
        ("puntaje_respaldo", "Respaldo"),
    ]
    for campo, nombre in series:
        fig.add_trace(go.Scatter(
            x=df["fecha"], y=df[campo], mode="lines", name=nombre,
            line=dict(color=COLOR_SERIE_HISTORIAL[campo], width=1.5, dash="dot"),
            opacity=0.75,
        ))
    fig.update_layout(
        yaxis=dict(range=[0, 100], title="Puntaje de riesgo", gridcolor="rgba(148,163,184,0.25)"),
        xaxis=dict(title=None),
        height=380,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def render_diagnostico_sistema() -> None:
    with st.expander("🔍 Diagnóstico automático del sistema (opcional, solo Windows)"):
        st.caption(
            "Lee en tu propio equipo el estado real de actualizaciones, firewall y "
            "antivirus para ayudarte a responder con precisión — no se modifica nada, "
            "solo lectura, y el resultado no sale de esta sesión."
        )
        if not disponible():
            st.info("Esta función solo está disponible en Windows.")
            return

        if st.button("Detectar ahora"):
            with st.spinner("Consultando el sistema..."):
                st.session_state["senales_sistema"] = obtener_senales_sistema()

        senales = st.session_state.get("senales_sistema")
        if not senales:
            return

        if not senales.get("ok"):
            st.warning(senales.get("error", "No se pudo completar el diagnóstico."))
            return

        etiquetas_bool = {True: "✅ Sí", False: "❌ No", None: "— no disponible"}

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Actualizaciones automáticas", etiquetas_bool[senales.get("actualizaciones_automaticas")])
        dias = senales.get("dias_desde_actualizacion")
        c2.metric("Días desde última actualización", dias if dias is not None else "—")
        c3.metric("Firewall activo", etiquetas_bool[senales.get("firewall_activo")])
        c4.metric("Antivirus activo", etiquetas_bool[senales.get("antivirus_activo")])

        c5, c6, c7 = st.columns(3)
        c5.metric("Bloqueo automático de pantalla", etiquetas_bool[senales.get("bloqueo_automatico")])
        c6.metric("Disco cifrado", etiquetas_bool[senales.get("disco_cifrado")])
        c7.metric("Acceso remoto (RDP) habilitado", etiquetas_bool[senales.get("acceso_remoto_habilitado")])
        if senales.get("errores"):
            st.caption("Algunos chequeos no se pudieron completar (ej. requieren permisos de administrador): " + "; ".join(senales["errores"]))

        st.caption("Estos valores se usan como sugerencia inicial del formulario de abajo; podés corregirlos si no reflejan tu caso.")


def formulario_respuestas() -> dict | None:
    senales = st.session_state.get("senales_sistema") or {}
    detecciones_ok = senales.get("ok", False)
    default_auto_updates = senales.get("actualizaciones_automaticas") if detecciones_ok else None
    default_dias_update = senales.get("dias_desde_actualizacion") if detecciones_ok else None
    default_bloqueo = senales.get("bloqueo_automatico") if detecciones_ok else None
    default_disco_cifrado = senales.get("disco_cifrado") if detecciones_ok else None
    default_acceso_remoto = senales.get("acceso_remoto_habilitado") if detecciones_ok else None

    with st.form("cuestionario"):
        col1, col2 = st.columns(2)

        with col1:
            with st.container(border=True):
                st.markdown('<div class="card-title">🔑 Contraseñas</div>', unsafe_allow_html=True)
                reutiliza = st.checkbox("Reutilizo la misma contraseña en varios servicios")
                longitud = st.slider("Longitud promedio de mis contraseñas", 4, 24, 10)
                st.caption("Recomendado: 14+ caracteres")
                gestor = st.checkbox("Uso un gestor de contraseñas", value=True)
                dos_fa = st.checkbox("Tengo activado el 2FA en mis cuentas principales", value=True)
                cambia_filtracion = st.checkbox(
                    "Cambio mi contraseña si me entero de una filtración", value=True
                )

            with st.container(border=True):
                st.markdown('<div class="card-title">🔄 Actualizaciones</div>', unsafe_allow_html=True)
                auto_updates = st.checkbox(
                    "Tengo activadas las actualizaciones automáticas del SO",
                    value=default_auto_updates if default_auto_updates is not None else True,
                )
                dias_update = st.slider(
                    "Días desde mi última actualización de sistema", 0, 365,
                    min(default_dias_update, 365) if default_dias_update is not None else 15,
                )
                st.caption("Recomendado: menos de 30 días" + ("  ·  🔍 prellenado con datos reales del equipo" if detecciones_ok else ""))
                apps_updates = st.checkbox("Actualizo mis apps con regularidad", value=True)

            with st.container(border=True):
                st.markdown('<div class="card-title">💻 Dispositivo</div>', unsafe_allow_html=True)
                st.caption("Riesgo si alguien tiene acceso físico a tu equipo (robo, pérdida, descuido).")
                bloqueo_automatico = st.checkbox(
                    "Mi pantalla se bloquea sola (con contraseña o PIN) tras un rato de inactividad",
                    value=default_bloqueo if default_bloqueo is not None else True,
                )
                disco_cifrado = st.checkbox(
                    "El disco de este equipo está cifrado (BitLocker / Cifrado de dispositivo)",
                    value=default_disco_cifrado if default_disco_cifrado is not None else False,
                )
                acceso_remoto = st.checkbox(
                    "Tengo el Escritorio remoto (RDP) u otro acceso remoto habilitado",
                    value=default_acceso_remoto if default_acceso_remoto is not None else False,
                )

        with col2:
            with st.container(border=True):
                st.markdown('<div class="card-title">📶 Redes</div>', unsafe_allow_html=True)
                wifi_sin_vpn = st.checkbox("Me conecto a wifi público sin usar VPN")
                usa_vpn = st.checkbox("Uso VPN habitualmente")
                clic_enlaces = st.checkbox("Hago clic en enlaces/adjuntos de origen desconocido")
                comparte_red = st.checkbox("Comparto dispositivos o red sin controles (perfiles, etc.)")

            with st.container(border=True):
                st.markdown('<div class="card-title">💾 Respaldo</div>', unsafe_allow_html=True)
                backups = st.checkbox("Hago copias de seguridad con regularidad", value=True)
                backups_nube = st.checkbox("Tengo copias de seguridad automáticas en la nube", value=True)

        enviado = st.form_submit_button("🛡️ Generar mi mapa de riesgo", width="stretch", type="primary")

    if not enviado:
        return None

    return {
        "reutiliza_contraseñas": reutiliza,
        "longitud_promedio": longitud,
        "usa_gestor": gestor,
        "usa_2fa": dos_fa,
        "cambia_password_tras_filtracion": cambia_filtracion,
        "actualizaciones_automaticas": auto_updates,
        "dias_desde_actualizacion": dias_update,
        "actualiza_apps": apps_updates,
        "usa_wifi_publico_sin_vpn": wifi_sin_vpn,
        "usa_vpn": usa_vpn,
        "hace_clic_enlaces_desconocidos": clic_enlaces,
        "comparte_red_o_dispositivos": comparte_red,
        "hace_backups_regulares": backups,
        "backups_automaticos_en_nube": backups_nube,
        "bloqueo_automatico": bloqueo_automatico,
        "disco_cifrado": disco_cifrado,
        "acceso_remoto_habilitado": acceso_remoto,
    }


def calcular_resultado(respuestas: dict) -> dict | None:
    """Corre reglas + modelo + plan de acción una sola vez, guarda en el
    historial local y devuelve todo lo necesario para renderizar."""
    evaluacion = evaluar_todo(respuestas)
    try:
        modelo = obtener_modelo()
    except FileNotFoundError as e:
        st.error(str(e))
        return None
    prediccion = predecir(modelo, respuestas)
    plan = generar_plan_accion(respuestas, evaluacion)
    categoria_reglas = etiquetar_riesgo(evaluacion["puntaje_global_reglas"])
    categoria_ml = prediccion["categoria_predicha"]
    confianza_ml = prediccion["probabilidades"].get(categoria_ml, 0)

    _asegurar_db()
    guardar_evaluacion(respuestas, evaluacion, categoria_ml, confianza_ml, categoria_reglas)

    discrepancias = comparar_con_respuestas(respuestas, st.session_state.get("senales_sistema") or {})

    return {
        "respuestas": respuestas,
        "evaluacion": evaluacion,
        "prediccion": prediccion,
        "plan": plan,
        "discrepancias": discrepancias,
    }


def generar_reporte_markdown(resultado: dict) -> str:
    ev = resultado["evaluacion"]
    pred = resultado["prediccion"]
    plan = resultado["plan"]
    categoria_ml = pred["categoria_predicha"]
    confianza = pred["probabilidades"].get(categoria_ml, 0) * 100

    lineas = [
        "# Mapa de Riesgos Digitales — Reporte",
        f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"- **Puntaje de riesgo (reglas):** {ev['puntaje_global_reglas']}/100",
        f"- **Riesgo global (modelo ML):** {categoria_ml} ({confianza:.0f}% de confianza)",
        "",
        "## Puntaje por categoría",
    ]
    for cat in CATEGORIAS:
        lineas.append(f"- {NOMBRES_CATEGORIA[cat]}: {ev['puntajes_por_categoria'][cat]}/100")

    lineas.append("")
    lineas.append("## Plan de acción priorizado")
    if not plan:
        lineas.append("Sin alertas: no se detectaron hábitos de riesgo.")
    for i, item in enumerate(plan, start=1):
        lineas.append(f"{i}. **[{NOMBRES_CATEGORIA[item['categoria']]}]** {item['descripcion']}")
        lineas.append(f"   - Recomendación: {item['recomendacion']}")
        lineas.append(
            f"   - Si se resuelve: {item['puntaje_actual']} → {item['puntaje_resultante']} "
            f"(−{item['impacto']} pts, {item['esfuerzo']} esfuerzo)"
        )

    lineas.append("")
    lineas.append("_Reporte generado localmente. Ningún dato fue enviado a servidores externos._")
    return "\n".join(lineas)


def render_plan_accion(plan: list[dict]) -> None:
    st.markdown('<div class="card-title">🎯 Plan de acción priorizado</div>', unsafe_allow_html=True)
    st.caption("Ordenado por impacto en tu puntaje frente al esfuerzo estimado de aplicarlo. Empezá por los primeros.")

    if not plan:
        st.success("No hay acciones pendientes: no se detectaron hábitos de riesgo.")
        return

    principales = [p for p in plan if p["impacto"] > 0][:5]
    ids_principales = {id(p) for p in principales}
    resto = [p for p in plan if id(p) not in ids_principales]

    for i, item in enumerate(principales, start=1):
        color = COLOR_RIESGO[ETIQUETA_SEVERIDAD[item["severidad"]]]
        st.markdown(
            f"""
            <div class="alert-card" style="--sev-color:{color}">
                <div class="cat">#{i} · {ICONO_CATEGORIA[item['categoria']]} {NOMBRES_CATEGORIA[item['categoria']]} · {ETIQUETA_ESFUERZO[item['esfuerzo']]}</div>
                <div class="desc">{item['descripcion']}</div>
                <div class="rec">➡️ {item['recomendacion']}</div>
                <div class="impacto" style="color:{color}">
                    Si lo resolvés: {item['puntaje_actual']} → {item['puntaje_resultante']} (−{item['impacto']} pts)
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if resto:
        with st.expander(f"Ver el resto del plan ({len(resto)})"):
            for item in resto:
                color = COLOR_RIESGO[ETIQUETA_SEVERIDAD[item["severidad"]]]
                st.markdown(
                    f"""
                    <div class="alert-card" style="--sev-color:{color}">
                        <div class="cat">{ICONO_CATEGORIA[item['categoria']]} {NOMBRES_CATEGORIA[item['categoria']]} · {ETIQUETA_ESFUERZO[item['esfuerzo']]}</div>
                        <div class="desc">{item['descripcion']}</div>
                        <div class="rec">➡️ {item['recomendacion']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def render_alertas_por_severidad(evaluacion: dict, conteo_severidad: dict) -> None:
    st.markdown('<div class="card-title">📋 Todas las alertas</div>', unsafe_allow_html=True)

    if not evaluacion["alertas"]:
        st.success("No se detectaron hábitos de riesgo. ¡Vas muy bien!")
        return

    tab_todas, tab_alto, tab_medio, tab_bajo = st.tabs([
        f"Todas ({len(evaluacion['alertas'])})",
        f"🔴 Alto ({conteo_severidad['alto']})",
        f"🟡 Medio ({conteo_severidad['medio']})",
        f"🔵 Bajo ({conteo_severidad['bajo']})",
    ])
    tabs_por_severidad = {"alto": tab_alto, "medio": tab_medio, "bajo": tab_bajo}

    def render_alerta(alerta: dict) -> None:
        st.markdown(
            f"""
            <div class="alert-card" style="--sev-color:{COLOR_RIESGO[ETIQUETA_SEVERIDAD[alerta['severidad']]]}">
                <div class="cat">{ICONO_CATEGORIA[alerta['categoria']]} {NOMBRES_CATEGORIA[alerta['categoria']]}</div>
                <div class="desc">{alerta['descripcion']}</div>
                <div class="rec">➡️ {alerta['recomendacion']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with tab_todas:
        for alerta in evaluacion["alertas"]:
            render_alerta(alerta)

    for severidad, tab in tabs_por_severidad.items():
        with tab:
            filtradas = [a for a in evaluacion["alertas"] if a["severidad"] == severidad]
            if not filtradas:
                st.info("Sin alertas en este nivel.")
            for alerta in filtradas:
                render_alerta(alerta)


def mostrar_resultados(resultado: dict) -> None:
    evaluacion = resultado["evaluacion"]
    prediccion = resultado["prediccion"]
    categoria_ml = prediccion["categoria_predicha"]
    probabilidades = prediccion["probabilidades"]
    puntaje_reglas = evaluacion["puntaje_global_reglas"]
    categoria_reglas = etiquetar_riesgo(puntaje_reglas)
    confianza = probabilidades.get(categoria_ml, 0) * 100

    conteo_severidad = {"alto": 0, "medio": 0, "bajo": 0}
    for a in evaluacion["alertas"]:
        conteo_severidad[a["severidad"]] += 1

    peor_categoria = max(evaluacion["puntajes_por_categoria"], key=evaluacion["puntajes_por_categoria"].get)

    st.divider()

    if resultado.get("discrepancias"):
        st.markdown("**⚠️ Diferencias entre lo que respondiste y lo detectado en tu sistema:**")
        for d in resultado["discrepancias"]:
            st.markdown(
                f'<div class="discrepancia">{d["etiqueta"]}: respondiste <b>{d["reportado"]}</b>, '
                f'pero el sistema detecta <b>{d["detectado"]}</b>.</div>',
                unsafe_allow_html=True,
            )

    col_gauge, col_hero = st.columns([1, 1.6])
    with col_gauge:
        st.plotly_chart(gauge_riesgo(puntaje_reglas, COLOR_RIESGO[categoria_reglas]), width="stretch")
        st.caption("Puntaje agregado del motor de reglas.")

    with col_hero:
        st.markdown(
            f"""
            <div class="risk-hero" style="background:{FONDO_RIESGO[categoria_ml]}; border: 1px solid {COLOR_RIESGO[categoria_ml]}55;">
                <div>
                    <div class="label">Riesgo global (modelo ML)</div>
                    <div class="value" style="color:{COLOR_RIESGO[categoria_ml]}">
                        {ICONO_RIESGO[categoria_ml]} {categoria_ml}
                    </div>
                    <div class="sub">Confianza del modelo: {confianza:.0f}%</div>
                </div>
            </div>
            <div class="kpi-row">
                <div class="kpi">
                    <div class="kpi-label">Área más riesgosa</div>
                    <div class="kpi-value">{ICONO_CATEGORIA[peor_categoria]} {NOMBRES_CATEGORIA[peor_categoria]}</div>
                </div>
                <div class="kpi">
                    <div class="kpi-label">Alertas altas</div>
                    <div class="kpi-value" style="color:{COLOR_RIESGO['Alto']}">{conteo_severidad['alto']}</div>
                </div>
                <div class="kpi">
                    <div class="kpi-label">Alertas medias</div>
                    <div class="kpi-value" style="color:{COLOR_RIESGO['Medio']}">{conteo_severidad['medio']}</div>
                </div>
                <div class="kpi">
                    <div class="kpi-label">Alertas bajas</div>
                    <div class="kpi-value" style="color:#3b82f6">{conteo_severidad['bajo']}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    col_radar, col_barras = st.columns(2)
    with col_radar:
        st.markdown('<div class="card-title">🗺️ Mapa de riesgo por área</div>', unsafe_allow_html=True)
        st.plotly_chart(radar_riesgo(evaluacion["puntajes_por_categoria"], COLOR_RIESGO[categoria_ml]), width="stretch")
        st.caption("Más hacia afuera = mayor riesgo en esa área.")
    with col_barras:
        st.markdown('<div class="card-title">🤖 Confianza del modelo</div>', unsafe_allow_html=True)
        st.plotly_chart(barras_confianza(probabilidades), width="stretch")
        st.caption("Probabilidad asignada por el modelo a cada categoría de riesgo.")

    render_plan_accion(resultado["plan"])
    render_alertas_por_severidad(evaluacion, conteo_severidad)

    col_reset, col_descarga = st.columns([1, 1])
    with col_reset:
        st.button("🔁 Reiniciar evaluación", on_click=lambda: st.session_state.pop("resultado", None))
    with col_descarga:
        st.download_button(
            "📄 Descargar reporte (Markdown)",
            data=generar_reporte_markdown(resultado),
            file_name=f"reporte_riesgo_{datetime.now().strftime('%Y%m%d')}.md",
            mime="text/markdown",
            width="stretch",
        )


def render_historial() -> None:
    _asegurar_db()
    filas = obtener_historial()

    if not filas:
        st.info(
            "Todavía no tenés evaluaciones guardadas. Completá el cuestionario en la "
            "pestaña **Evaluar** para empezar tu historial."
        )
        return

    df = pd.DataFrame(filas)
    df["fecha"] = pd.to_datetime(df["fecha"])

    ultima = df.iloc[-1]
    primera = df.iloc[0]
    tendencia = int(ultima["puntaje_global"]) - int(primera["puntaje_global"])
    c1, c2, c3 = st.columns(3)
    c1.metric("Evaluaciones guardadas", len(df))
    c2.metric("Puntaje actual", f"{int(ultima['puntaje_global'])}/100")
    c3.metric("Cambio desde la primera evaluación", f"{tendencia:+d} pts", delta=tendencia, delta_color="inverse")

    st.plotly_chart(grafico_historial(df), width="stretch")

    with st.expander("Ver tabla de evaluaciones"):
        tabla = df[["fecha", "puntaje_global", "categoria_reglas", "categoria_ml", "confianza_ml"]] \
            .sort_values("fecha", ascending=False) \
            .rename(columns={
                "fecha": "Fecha", "puntaje_global": "Puntaje", "categoria_reglas": "Categoría (reglas)",
                "categoria_ml": "Categoría (ML)", "confianza_ml": "Confianza ML",
            })
        st.dataframe(tabla, width="stretch", hide_index=True)

    st.divider()
    if st.session_state.get("confirmar_borrado"):
        st.warning("¿Seguro que querés borrar todo tu historial guardado? Esta acción no se puede deshacer.")
        cc1, cc2 = st.columns(2)
        if cc1.button("Sí, borrar todo", type="primary"):
            borrar_historial()
            st.session_state["confirmar_borrado"] = False
            st.rerun()
        if cc2.button("Cancelar"):
            st.session_state["confirmar_borrado"] = False
            st.rerun()
    else:
        if st.button("🗑️ Borrar historial"):
            st.session_state["confirmar_borrado"] = True
            st.rerun()


def render_como_funciona() -> None:
    st.markdown(
        """
        - **Motor de reglas:** cada respuesta se compara contra buenas prácticas de
          seguridad conocidas y genera un puntaje por categoría (0-100) más alertas
          explicables, cada una con su recomendación.
        - **Modelo de ML:** un RandomForest entrenado con perfiles simulados clasifica
          el riesgo global (Bajo/Medio/Alto) a partir de la combinación completa de tus
          respuestas, capturando patrones que una fórmula simple no siempre detecta.
        - **Plan de acción:** cada alerta se simula individualmente (¿cuánto bajaría tu
          puntaje si la resolvieras?) y se ordena por impacto frente a esfuerzo, para
          mostrarte primero los cambios de mayor retorno.
        - **Historial local:** cada evaluación se guarda en `data/historial.db`
          (SQLite, en tu propio equipo) para poder ver la tendencia de tu riesgo en el
          tiempo. Nunca se envía a servidores externos.
        - **Diagnóstico del sistema (Windows):** un script de PowerShell de solo lectura
          contrasta tus respuestas contra el estado real de actualizaciones, firewall y
          antivirus de tu equipo.
        - **Recordatorios proactivos (opcional):** `scripts/instalar_recordatorio.ps1`
          registra una tarea semanal en el Programador de tareas de Windows que te avisa
          si pasó mucho tiempo desde tu última evaluación. No se instala automáticamente
          — corré ese script vos mismo cuando quieras activarlo, y `desinstalar_recordatorio.ps1`
          para quitarlo.
        """
    )


def main() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        """
        <div class="hero">
            <h1>🛡️ Mapa de Riesgos Digitales</h1>
            <p>Responde este breve cuestionario sobre tus hábitos de <b>contraseñas</b>,
            <b>actualizaciones</b>, <b>uso de redes</b> y <b>respaldo</b>. El sistema combina
            reglas de seguridad transparentes con un modelo de Machine Learning ligero,
            un plan de acción priorizado y tu historial de progreso.</p>
            <div class="hero-chips">
                <span class="hero-chip">🔎 Reglas explicables</span>
                <span class="hero-chip">🤖 IA ligera (RandomForest)</span>
                <span class="hero-chip">🎯 Plan de acción con simulación</span>
                <span class="hero-chip">📈 Historial local</span>
                <span class="hero-chip">🔒 100% local, nada se envía</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_evaluar, tab_historial, tab_info = st.tabs(["📋 Evaluar", "📈 Historial", "⚙️ Cómo funciona"])

    with tab_evaluar:
        render_diagnostico_sistema()
        respuestas = formulario_respuestas()
        if respuestas is not None:
            resultado = calcular_resultado(respuestas)
            if resultado is not None:
                st.session_state["resultado"] = resultado

        if "resultado" in st.session_state:
            mostrar_resultados(st.session_state["resultado"])

    with tab_historial:
        render_historial()

    with tab_info:
        render_como_funciona()

    st.markdown(
        '<div class="footer-note">Modelo entrenado con dataset 100% sintético. Tu historial de '
        'respuestas se guarda solo en este equipo (data/historial.db) y nunca se envía a servidores externos.</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
