"""
Persistencia local del historial de evaluaciones (SQLite, sin dependencias
externas). Convierte el prototipo de "encuesta de una sola vez" en una
herramienta a la que se vuelve: guarda cada evaluación con fecha, permite
ver la tendencia del riesgo en el tiempo, y sirve de base tanto para los
recordatorios proactivos (¿cuánto hace que no te evalúas?) como para un
futuro reentrenamiento del modelo con datos reales de uso.

Todo se guarda únicamente en data/historial.db, en el propio equipo del
usuario. Nada se envía a servidores externos.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

RUTA_DB = Path(__file__).resolve().parent.parent / "data" / "historial.db"

PERFIL_POR_DEFECTO = "default"


def _conectar() -> sqlite3.Connection:
    RUTA_DB.parent.mkdir(parents=True, exist_ok=True)
    conexion = sqlite3.connect(RUTA_DB)
    conexion.row_factory = sqlite3.Row
    return conexion


def inicializar_db() -> None:
    with _conectar() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS evaluaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                perfil TEXT NOT NULL DEFAULT 'default',
                respuestas_json TEXT NOT NULL,
                puntaje_global INTEGER NOT NULL,
                categoria_reglas TEXT NOT NULL,
                categoria_ml TEXT NOT NULL,
                confianza_ml REAL NOT NULL,
                puntaje_contrasenas INTEGER NOT NULL,
                puntaje_actualizaciones INTEGER NOT NULL,
                puntaje_redes INTEGER NOT NULL,
                puntaje_respaldo INTEGER NOT NULL,
                puntaje_dispositivo INTEGER NOT NULL DEFAULT 0
            )
        """)


def guardar_evaluacion(
    respuestas: dict,
    evaluacion: dict,
    categoria_ml: str,
    confianza_ml: float,
    categoria_reglas: str,
    perfil: str = PERFIL_POR_DEFECTO,
) -> None:
    inicializar_db()
    puntajes = evaluacion["puntajes_por_categoria"]
    with _conectar() as con:
        con.execute(
            """
            INSERT INTO evaluaciones (
                fecha, perfil, respuestas_json, puntaje_global,
                categoria_reglas, categoria_ml, confianza_ml,
                puntaje_contrasenas, puntaje_actualizaciones, puntaje_redes, puntaje_respaldo, puntaje_dispositivo
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                perfil,
                json.dumps(respuestas, ensure_ascii=False),
                evaluacion["puntaje_global_reglas"],
                categoria_reglas,
                categoria_ml,
                confianza_ml,
                puntajes["contraseñas"],
                puntajes["actualizaciones"],
                puntajes["redes"],
                puntajes["respaldo"],
                puntajes["dispositivo"],
            ),
        )


def obtener_historial(perfil: str = PERFIL_POR_DEFECTO, limite: int = 200) -> list[dict]:
    inicializar_db()
    with _conectar() as con:
        filas = con.execute(
            """
            SELECT * FROM evaluaciones
            WHERE perfil = ?
            ORDER BY fecha ASC
            LIMIT ?
            """,
            (perfil, limite),
        ).fetchall()
    return [dict(f) for f in filas]


def ultima_evaluacion(perfil: str = PERFIL_POR_DEFECTO) -> dict | None:
    historial = obtener_historial(perfil)
    return historial[-1] if historial else None


def dias_desde_ultima_evaluacion(perfil: str = PERFIL_POR_DEFECTO) -> int | None:
    ultima = ultima_evaluacion(perfil)
    if ultima is None:
        return None
    fecha = datetime.fromisoformat(ultima["fecha"])
    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - fecha).days


def borrar_historial(perfil: str = PERFIL_POR_DEFECTO) -> None:
    inicializar_db()
    with _conectar() as con:
        con.execute("DELETE FROM evaluaciones WHERE perfil = ?", (perfil,))
