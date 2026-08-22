"""
Plan de acción priorizado: convierte la lista plana de alertas del motor de
reglas en una hoja de ruta ordenada por impacto real, simulando "qué pasaría
si corrigieras este hábito" en vez de solo describir el problema.

Cada alerta de reglas.py ya trae los cambios concretos que la resolverían
(alerta["cambios_sugeridos"]). Aquí aplicamos ese cambio sobre una copia de
las respuestas del usuario, volvemos a correr el motor de reglas, y medimos
cuánto baja el puntaje global. Combinado con un esfuerzo estimado por hábito
(reglas.ESFUERZO_POR_CAMPO), priorizamos primero los "quick wins": alto
impacto con bajo esfuerzo.
"""

from __future__ import annotations

from reglas import ESFUERZO_POR_CAMPO, evaluar_todo

PESO_ESFUERZO = {"bajo": 1, "medio": 2, "alto": 3}


def simular_cambio(respuestas: dict, cambios: dict) -> dict:
    """Recalcula el puntaje global si se aplicaran los `cambios` indicados."""
    respuestas_simuladas = {**respuestas, **cambios}
    return evaluar_todo(respuestas_simuladas)


def generar_plan_accion(respuestas: dict, evaluacion: dict) -> list[dict]:
    """Devuelve las alertas ordenadas por prioridad (impacto / esfuerzo),
    cada una con el puntaje proyectado si se resolviera."""
    puntaje_actual = evaluacion["puntaje_global_reglas"]
    plan = []

    for alerta in evaluacion["alertas"]:
        simulacion = simular_cambio(respuestas, alerta["cambios_sugeridos"])
        puntaje_resultante = simulacion["puntaje_global_reglas"]
        impacto = max(0, puntaje_actual - puntaje_resultante)

        campos = list(alerta["cambios_sugeridos"].keys())
        esfuerzos = [ESFUERZO_POR_CAMPO.get(c, "medio") for c in campos]
        esfuerzo = max(esfuerzos, key=lambda e: PESO_ESFUERZO[e]) if esfuerzos else "medio"
        prioridad = impacto / PESO_ESFUERZO[esfuerzo]

        plan.append({
            **alerta,
            "puntaje_actual": puntaje_actual,
            "puntaje_resultante": puntaje_resultante,
            "impacto": impacto,
            "esfuerzo": esfuerzo,
            "prioridad": round(prioridad, 2),
        })

    plan.sort(key=lambda p: p["prioridad"], reverse=True)
    return plan
