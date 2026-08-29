import sys
from pathlib import Path

import streamlit as st
import plotly.graph_objects as go

SRC_DIR = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(SRC_DIR))

from taxonomy import load_taxonomy  # noqa: E402
from parsing import extract_text  # noqa: E402
from scoring_pipeline import score_batch  # noqa: E402

from ui import (  # noqa: E402
    CSS, esc, render_hero, render_kpis, render_candidate_card, render_alert,
    render_steps, render_metric_tiles, build_csv,
)
from auth import render_admin_gate  # noqa: E402

st.set_page_config(page_title="Fit Score de Reclutamiento", page_icon="🎯", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)
st.markdown(render_hero(), unsafe_allow_html=True)

taxonomy = load_taxonomy()
job_families = taxonomy["job_families"]
all_skill_ids = sorted(taxonomy["skills"].keys())
niveles_educacion = taxonomy["niveles_educacion"]
NUEVO = "__nuevo__"


def skill_label(skill_id: str) -> str:
    return taxonomy["skills"][skill_id]["aliases"][0]


with st.sidebar:
    st.markdown("### 🧩 1. Vacante")
    family_key = st.selectbox(
        "Partir de un puesto predefinido, o crear uno nuevo",
        options=[NUEVO] + list(job_families.keys()),
        format_func=lambda k: "✏️ Puesto personalizado (nuevo)" if k == NUEVO else job_families[k]["titulo"],
    )

    if st.session_state.get("_last_family_key") != family_key:
        st.session_state["_last_family_key"] = family_key
        st.session_state.pop("resultado", None)
        st.session_state.pop("puesto", None)

    base = job_families.get(family_key, {
        "titulo": "", "skills_obligatorias": [], "skills_deseables": [],
        "min_experiencia": 1, "educacion_minima": "pregrado",
    })

    with st.expander("🔒 Acceso de administrador (RRHH)", expanded=(family_key == NUEVO)):
        admin_unlocked = render_admin_gate()

    campos_bloqueados = not admin_unlocked
    if family_key == NUEVO and campos_bloqueados:
        st.info("Desbloquea el acceso de administrador arriba para crear un puesto nuevo.")

    titulo = st.text_input(
        "Título del puesto", value=base["titulo"], key=f"titulo_{family_key}",
        disabled=campos_bloqueados,
    )

    skills_obligatorias = st.multiselect(
        "Skills obligatorias", options=all_skill_ids, default=base["skills_obligatorias"],
        format_func=skill_label, key=f"obl_{family_key}", disabled=campos_bloqueados,
    )
    skills_deseables = st.multiselect(
        "Skills deseables", options=all_skill_ids, default=base["skills_deseables"],
        format_func=skill_label, key=f"des_{family_key}", disabled=campos_bloqueados,
    )
    col_exp, col_edu = st.columns(2)
    with col_exp:
        min_experiencia = st.number_input(
            "Experiencia mín. (años)", min_value=0, max_value=30,
            value=base["min_experiencia"], key=f"exp_{family_key}", disabled=campos_bloqueados,
        )
    with col_edu:
        educacion_minima = st.selectbox(
            "Educación mínima", options=niveles_educacion,
            index=niveles_educacion.index(base["educacion_minima"]), key=f"edu_{family_key}",
            disabled=campos_bloqueados,
        )

    descripcion_extra = st.text_area(
        "Descripción adicional de la vacante (mejora la similitud semántica)",
        value=f"Buscamos {titulo or 'un/a profesional'} con experiencia demostrable en el rol." if family_key == NUEVO
        else f"Buscamos {base['titulo']} con experiencia demostrable en el rol.",
        key=f"desc_{family_key}", disabled=campos_bloqueados,
    )

    if not skills_obligatorias:
        st.caption("⚠️ Agrega al menos una skill obligatoria para poder evaluar candidatos.")

    st.markdown("### 📎 2. Candidatos")
    archivos = st.file_uploader(
        "Sube uno o varios CVs (PDF, DOCX, TXT)",
        type=["pdf", "docx", "txt"], accept_multiple_files=True,
        label_visibility="visible", key=f"archivos_{family_key}",
    )
    st.caption("Al cambiar de puesto se limpian los CVs y resultados ya revisados.")
    puede_evaluar = bool(archivos) and bool(skills_obligatorias) and bool(titulo.strip())
    evaluar = st.button("⚡ Evaluar candidatos", type="primary", disabled=not puede_evaluar, use_container_width=True)

vacancy = {
    "skills_obligatorias": skills_obligatorias,
    "skills_deseables": skills_deseables,
    "min_experiencia": min_experiencia,
    "educacion_minima": educacion_minima,
    "descripcion": f"Vacante: {titulo}. {descripcion_extra}",
}

if evaluar and puede_evaluar:
    with st.spinner("Extrayendo texto, calculando features y ejecutando el modelo..."):
        candidatos = []
        archivos_con_error = []
        for archivo in archivos:
            try:
                texto = extract_text(archivo)
            except Exception:
                archivos_con_error.append(archivo.name)
                continue
            if not texto.strip():
                archivos_con_error.append(archivo.name)
                continue
            candidatos.append({"nombre": archivo.name, "cv_text": texto})

        if archivos_con_error:
            st.warning(
                "No se pudo leer el contenido de: " + ", ".join(esc(n) for n in archivos_con_error)
                + " — verifica que el archivo no esté corrupto, protegido con contraseña o vacío."
            )

        resultado = score_batch(candidatos, vacancy) if candidatos else None

    if resultado:
        st.session_state["resultado"] = resultado
        st.session_state["puesto"] = titulo

resultado = st.session_state.get("resultado")

if not resultado:
    st.markdown(
        """
        <div style="text-align:center;padding:1.5rem 1rem .5rem;">
          <div style="font-size:1.2rem;color:var(--accent-dark);font-weight:700;">Tres pasos y tienes tu ranking explicado</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(render_steps(), unsafe_allow_html=True)
else:
    st.markdown(render_kpis(resultado["candidatos"], resultado["duplicados"], resultado["auditoria_sesgos"]["alertas"]), unsafe_allow_html=True)

    tab_ranking, tab_analisis, tab_sesgos, tab_duplicados = st.tabs(
        ["📊 Ranking de candidatos", "📈 Análisis general", "⚖️ Auditoría de sesgos", "🔁 Duplicados"]
    )

    with tab_ranking:
        col_titulo, col_descarga = st.columns([3, 1])
        with col_titulo:
            st.markdown(f"#### Ranking para: {esc(st.session_state.get('puesto', ''))}")
        with col_descarga:
            st.download_button(
                "⬇️ Descargar CSV", data=build_csv(resultado["candidatos"]),
                file_name=f"ranking_{st.session_state.get('puesto', 'vacante').replace(' ', '_')}.csv",
                mime="text/csv", use_container_width=True,
            )
        for i, r in enumerate(resultado["candidatos"]):
            st.markdown(render_candidate_card(r, i), unsafe_allow_html=True)
            with st.expander("Ver métricas, justificación y explicación SHAP"):
                shap_data = r["explicacion_shap"]

                st.markdown('<div class="section-title">📐 Métricas individuales</div>', unsafe_allow_html=True)
                st.markdown(render_metric_tiles(shap_data), unsafe_allow_html=True)

                col1, col2 = st.columns([3, 2])
                with col1:
                    st.markdown('<div class="section-title">📝 Justificación</div>', unsafe_allow_html=True)
                    st.write(r["justificacion"])

                    if r["anomalia"]["es_atipico"]:
                        st.markdown(render_alert("warn", f"CV atípico: {esc(r['anomalia']['motivo'])}"), unsafe_allow_html=True)

                    if r["upskilling"]:
                        st.markdown('<div class="section-title">📚 Recomendaciones de upskilling</div>', unsafe_allow_html=True)
                        for rec in r["upskilling"]:
                            st.markdown(f"- **{esc(rec['skill_faltante'])}** → {esc(rec['recurso_sugerido'])}")

                with col2:
                    st.markdown('<div class="section-title">🔍 Contribución al score (SHAP)</div>', unsafe_allow_html=True)
                    fig = go.Figure(go.Bar(
                        x=[c["impacto_shap"] for c in shap_data],
                        y=[c["feature"] for c in shap_data],
                        orientation="h",
                        marker_color=["#16A34A" if c["impacto_shap"] >= 0 else "#DC2626" for c in shap_data],
                    ))
                    fig.update_layout(
                        margin=dict(l=10, r=10, t=10, b=10), height=260,
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#2D3235"),
                    )
                    st.plotly_chart(fig, use_container_width=True)

    with tab_analisis:
        st.markdown("#### Análisis general del lote")
        st.markdown(
            '<p class="section-note">Métricas agregadas sobre todos los candidatos evaluados, '
            "para detectar patrones que un score individual no muestra.</p>",
            unsafe_allow_html=True,
        )
        candidatos_r = resultado["candidatos"]

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown('<div class="section-title">Distribución de scores</div>', unsafe_allow_html=True)
            fig_hist = go.Figure(go.Histogram(
                x=[r["score_pct"] for r in candidatos_r],
                xbins=dict(start=0, end=100, size=10),
                marker_color="#555ABF",
            ))
            fig_hist.update_layout(
                margin=dict(l=10, r=10, t=10, b=10), height=280,
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#2D3235"), xaxis_title="Score (%)", yaxis_title="Candidatos",
                bargap=0.08,
            )
            st.plotly_chart(fig_hist, use_container_width=True)

        with col_b:
            st.markdown('<div class="section-title">Promedio por métrica del modelo</div>', unsafe_allow_html=True)
            sumas, conteos = {}, {}
            for r in candidatos_r:
                for c in r["explicacion_shap"]:
                    sumas[c["feature"]] = sumas.get(c["feature"], 0) + c["valor"]
                    conteos[c["feature"]] = conteos.get(c["feature"], 0) + 1
            etiquetas = list(sumas.keys())
            promedios = [sumas[k] / conteos[k] * 100 for k in etiquetas]
            fig_avg = go.Figure(go.Bar(
                x=promedios, y=etiquetas, orientation="h", marker_color="#74E4A2",
            ))
            fig_avg.update_layout(
                margin=dict(l=10, r=10, t=10, b=10), height=280,
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#2D3235"), xaxis_title="Promedio (%)", xaxis_range=[0, 100],
            )
            st.plotly_chart(fig_avg, use_container_width=True)

        st.markdown('<div class="section-title">Habilidades que más faltan en el lote</div>', unsafe_allow_html=True)
        conteo_faltantes: dict[str, int] = {}
        for r in candidatos_r:
            for skill in r["skills_obligatorias_faltantes"] + r["skills_deseables_faltantes"]:
                conteo_faltantes[skill] = conteo_faltantes.get(skill, 0) + 1

        if not conteo_faltantes:
            st.markdown(render_alert("ok", "Ningún candidato tiene habilidades faltantes en este lote."), unsafe_allow_html=True)
        else:
            top_faltantes = sorted(conteo_faltantes.items(), key=lambda x: -x[1])[:10]
            fig_gaps = go.Figure(go.Bar(
                x=[n for _, n in top_faltantes], y=[esc(s) for s, _ in top_faltantes],
                orientation="h", marker_color="#DC2626",
            ))
            fig_gaps.update_layout(
                margin=dict(l=10, r=10, t=10, b=10), height=max(220, 32 * len(top_faltantes)),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#2D3235"), xaxis_title="Candidatos a los que les falta",
                yaxis=dict(autorange="reversed"),
            )
            st.plotly_chart(fig_gaps, use_container_width=True)
            st.caption(
                "Si una misma habilidad falta en la mayoría del lote, puede ser señal de que el "
                "requisito es poco realista para el mercado actual, o de que conviene ampliar la "
                "búsqueda a otros perfiles."
            )

    with tab_sesgos:
        st.markdown("#### Auditoría de sesgos (regla del 80%)")
        st.markdown(
            '<p class="section-note">Audita proxies estructurales (universidad, brecha laboral) sobre el '
            "RESULTADO del scoring. No se usan como input del modelo. "
            "Ver docs/nota_uso_responsable.md.</p>",
            unsafe_allow_html=True,
        )
        auditoria = resultado["auditoria_sesgos"]

        if auditoria["alertas"]:
            for alerta in auditoria["alertas"]:
                st.markdown(render_alert("danger", esc(alerta)), unsafe_allow_html=True)
        else:
            st.markdown(render_alert("ok", "No se detectaron disparidades por encima del umbral en este lote."), unsafe_allow_html=True)

        def _to_rows(grupo_dict, nombre_col):
            return [
                {
                    nombre_col: grupo,
                    "N candidatos": info["n_candidatos"],
                    "Tasa selección": f"{info['tasa_seleccion']:.0%}",
                    "Ratio vs. mejor grupo": f"{info['ratio_vs_mejor_grupo']:.0%}",
                    "Posible sesgo": "🚩" if info["posible_sesgo"] else "",
                }
                for grupo, info in grupo_dict.items()
            ]

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Por tier de universidad**")
            st.dataframe(_to_rows(auditoria["por_universidad"], "Universidad"), use_container_width=True, hide_index=True)
        with col2:
            st.markdown("**Por brecha laboral**")
            st.dataframe(_to_rows(auditoria["por_brecha_laboral"], "Brecha"), use_container_width=True, hide_index=True)

    with tab_duplicados:
        st.markdown("#### CVs potencialmente duplicados o plagiados entre sí")
        duplicados = resultado["duplicados"]
        if not duplicados:
            st.markdown(render_alert("ok", "No se detectaron pares de CVs sospechosamente similares en este lote."), unsafe_allow_html=True)
        else:
            for d in duplicados:
                st.markdown(
                    render_alert(
                        "warn",
                        f"<b>{esc(d['candidato_a'])}</b> y <b>{esc(d['candidato_b'])}</b> — "
                        f"similitud semántica: {d['similitud']:.0%}",
                    ),
                    unsafe_allow_html=True,
                )
