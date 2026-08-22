"""
Mapa de Riesgos Digitales — backend Flask.

Sirve una página propia (HTML/CSS/JS, sin recargas de página) y expone una
API JSON delgada sobre la misma lógica de src/ que ya usa la versión
Streamlit (app.py): motor de reglas, modelo de ML, plan de acción,
historial local y diagnóstico del sistema. Nada de esa lógica se duplica
ni se modifica acá.

Ejecutar:
    python server.py
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file

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
from reporte_word import generar_reporte_docx  # noqa: E402
from senales_sistema import comparar_con_respuestas, disponible, obtener_senales_sistema  # noqa: E402

app = Flask(__name__)

_modelo = None


def obtener_modelo():
    global _modelo
    if _modelo is None:
        _modelo = cargar_modelo()
    return _modelo


CAMPOS_BOOL = [
    "reutiliza_contraseñas", "usa_gestor", "usa_2fa", "cambia_password_tras_filtracion",
    "actualizaciones_automaticas", "actualiza_apps", "usa_wifi_publico_sin_vpn", "usa_vpn",
    "hace_clic_enlaces_desconocidos", "comparte_red_o_dispositivos", "hace_backups_regulares",
    "backups_automaticos_en_nube", "bloqueo_automatico", "disco_cifrado", "acceso_remoto_habilitado",
]
CAMPOS_NUMERICOS = {"longitud_promedio": (4, 24), "dias_desde_actualizacion": (0, 365)}


def validar_respuestas(payload: dict) -> dict:
    """Convierte y valida el JSON entrante a los tipos que espera reglas.py.
    Lanza ValueError con un mensaje entendible si algo falta o es inválido."""
    if not isinstance(payload, dict):
        raise ValueError("Formato de datos inválido.")

    respuestas = {}
    for campo in CAMPOS_BOOL:
        if campo not in payload:
            raise ValueError(f"Falta el campo '{campo}'.")
        respuestas[campo] = bool(payload[campo])

    for campo, (minimo, maximo) in CAMPOS_NUMERICOS.items():
        if campo not in payload:
            raise ValueError(f"Falta el campo '{campo}'.")
        try:
            valor = int(payload[campo])
        except (TypeError, ValueError):
            raise ValueError(f"El campo '{campo}' debe ser numérico.")
        respuestas[campo] = max(minimo, min(maximo, valor))

    return respuestas


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/evaluar", methods=["POST"])
def api_evaluar():
    payload = request.get_json(force=True, silent=True) or {}
    try:
        respuestas = validar_respuestas(payload)
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400

    evaluacion = evaluar_todo(respuestas)
    try:
        modelo = obtener_modelo()
    except FileNotFoundError as e:
        return jsonify({"ok": False, "error": str(e)}), 500

    prediccion = predecir(modelo, respuestas)
    plan = generar_plan_accion(respuestas, evaluacion)
    categoria_reglas = etiquetar_riesgo(evaluacion["puntaje_global_reglas"])
    categoria_ml = prediccion["categoria_predicha"]
    confianza_ml = prediccion["probabilidades"].get(categoria_ml, 0)

    inicializar_db()
    guardar_evaluacion(respuestas, evaluacion, categoria_ml, confianza_ml, categoria_reglas)

    discrepancias = comparar_con_respuestas(respuestas, payload.get("_senales_sistema") or {})

    return jsonify({
        "ok": True,
        "evaluacion": evaluacion,
        "categoria_reglas": categoria_reglas,
        "prediccion": {
            "categoria_predicha": categoria_ml,
            "probabilidades": prediccion["probabilidades"],
        },
        "plan": plan,
        "discrepancias": discrepancias,
        "categorias": CATEGORIAS,
    })


@app.route("/api/historial", methods=["GET"])
def api_historial():
    inicializar_db()
    filas = obtener_historial()
    return jsonify({"ok": True, "filas": filas})


@app.route("/api/historial/borrar", methods=["POST"])
def api_historial_borrar():
    inicializar_db()
    borrar_historial()
    return jsonify({"ok": True})


@app.route("/api/diagnostico", methods=["GET"])
def api_diagnostico():
    if not disponible():
        return jsonify({"ok": False, "error": "El diagnóstico automático solo está disponible en Windows."})
    resultado = obtener_senales_sistema()
    return jsonify(resultado)


@app.route("/api/reporte", methods=["POST"])
def api_reporte():
    """Genera el reporte como documento Word (.docx) a partir del último
    resultado calculado en el navegador (se lo mandamos de vuelta, no se
    recalcula nada)."""
    datos = request.get_json(force=True, silent=True) or {}
    evaluacion = datos.get("evaluacion")
    prediccion = datos.get("prediccion")
    plan = datos.get("plan", [])
    if not evaluacion or not prediccion:
        return jsonify({"ok": False, "error": "Faltan datos del resultado."}), 400

    buffer = generar_reporte_docx(evaluacion, prediccion, plan)
    nombre_archivo = f"reporte_riesgo_digital_{datetime.now().strftime('%Y%m%d_%H%M')}.docx"

    return send_file(
        buffer,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        as_attachment=True,
        download_name=nombre_archivo,
    )


if __name__ == "__main__":
    inicializar_db()
    app.run(debug=True, port=5000)
