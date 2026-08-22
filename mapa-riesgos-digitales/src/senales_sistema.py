"""
Diagnóstico de señales reales del sistema (solo Windows), para contrastar
contra el autoreporte del cuestionario. Ejecuta scripts/senales_sistema.ps1
en un subproceso de PowerShell, de solo lectura, con timeout, y nunca lanza
excepción hacia quien lo llama: cualquier falla se refleja en el resultado
como "no disponible" para ese campo puntual.
"""

from __future__ import annotations

import json
import platform
import subprocess
from pathlib import Path

RUTA_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "senales_sistema.ps1"

CAMPOS_COMPARABLES = {
    "actualizaciones_automaticas": "Actualizaciones automáticas activadas",
    "dias_desde_actualizacion": "Días desde la última actualización",
}

CAMPOS_BOOLEANOS_DIRECTOS = {
    "actualizaciones_automaticas": "Actualizaciones automáticas activadas",
    "bloqueo_automatico": "Bloqueo automático de pantalla",
    "disco_cifrado": "Disco cifrado",
    "acceso_remoto_habilitado": "Acceso remoto (RDP) habilitado",
}


def disponible() -> bool:
    return platform.system() == "Windows"


def obtener_senales_sistema(timeout_segundos: int = 30) -> dict:
    """Devuelve un dict con las señales detectadas. Si algo falla, marca
    'ok': False y deja 'error' con el detalle; nunca lanza excepción."""
    if not disponible():
        return {"ok": False, "error": "El diagnóstico automático solo está disponible en Windows."}

    if not RUTA_SCRIPT.exists():
        return {"ok": False, "error": f"No se encontró {RUTA_SCRIPT}"}

    try:
        proceso = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy", "Bypass",
                "-File", str(RUTA_SCRIPT),
            ],
            capture_output=True,
            text=True,
            timeout=timeout_segundos,
            encoding="utf-8",
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        return {"ok": False, "error": f"No se pudo ejecutar el diagnóstico: {e}"}

    if proceso.returncode != 0 or not proceso.stdout.strip():
        return {"ok": False, "error": proceso.stderr.strip() or "El script no devolvió resultados."}

    try:
        datos = json.loads(proceso.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "error": "No se pudo interpretar la salida del diagnóstico."}

    datos["ok"] = True
    return datos


def comparar_con_respuestas(respuestas: dict, senales: dict) -> list[dict]:
    """Compara lo que el usuario respondió contra lo que se detectó
    realmente, y devuelve las discrepancias encontradas."""
    discrepancias = []
    if not senales.get("ok"):
        return discrepancias

    for campo, etiqueta in CAMPOS_BOOLEANOS_DIRECTOS.items():
        if senales.get(campo) is None:
            continue
        reportado = respuestas.get(campo)
        detectado = senales[campo]
        if reportado is not None and reportado != detectado:
            discrepancias.append({
                "campo": campo,
                "etiqueta": etiqueta,
                "reportado": reportado,
                "detectado": detectado,
            })

    if senales.get("dias_desde_actualizacion") is not None:
        reportado = respuestas.get("dias_desde_actualizacion")
        detectado = senales["dias_desde_actualizacion"]
        if reportado is not None and abs(reportado - detectado) > 15:
            discrepancias.append({
                "campo": "dias_desde_actualizacion",
                "etiqueta": CAMPOS_COMPARABLES["dias_desde_actualizacion"],
                "reportado": reportado,
                "detectado": detectado,
            })

    return discrepancias
