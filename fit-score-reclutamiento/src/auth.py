"""Autenticación mínima para RRHH: proteger la edición/creación de vacantes con contraseña.

Solo se compara un hash SHA-256 — la contraseña en texto plano nunca se guarda ni se compara
directamente. El hash real vive en .streamlit/secrets.toml (gitignored); el valor de abajo es
únicamente un fallback para que la demo funcione si ese archivo no existe.
"""
import hashlib

import streamlit as st

# Fallback de demo == sha256("admin123"). Cambiar la contraseña real en .streamlit/secrets.toml.
_DEMO_HASH = "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9"


def _expected_hash() -> str:
    try:
        return st.secrets["admin_password_hash"]
    except Exception:
        return _DEMO_HASH


def check_admin_password(password: str) -> bool:
    if not password:
        return False
    return hashlib.sha256(password.encode("utf-8")).hexdigest() == _expected_hash()


def render_admin_gate() -> bool:
    """Renderiza el widget de desbloqueo en el sidebar y devuelve si la edición está permitida."""
    unlocked = st.session_state.get("admin_unlocked", False)

    if unlocked:
        st.success("🔓 Edición de vacante desbloqueada para esta sesión.")
        if st.button("Bloquear edición", use_container_width=True):
            st.session_state["admin_unlocked"] = False
            st.rerun()
        return True

    with st.form("admin_login", clear_on_submit=True):
        pw_input = st.text_input("Contraseña de administrador (RRHH)", type="password")
        submitted = st.form_submit_button("🔓 Desbloquear edición", use_container_width=True)
    if submitted:
        if check_admin_password(pw_input):
            st.session_state["admin_unlocked"] = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta.")

    st.caption(
        "🔒 Sin desbloquear puedes usar los puestos predefinidos tal cual, pero no editarlos "
        "ni crear uno nuevo — solo un administrador de RRHH puede cambiar los requisitos de "
        "una vacante."
    )
    return False
