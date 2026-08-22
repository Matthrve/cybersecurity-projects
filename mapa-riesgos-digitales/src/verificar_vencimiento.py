"""
Utilidad de línea de comandos usada por scripts/recordatorio.ps1: imprime
cuántos días pasaron desde la última evaluación guardada (o "sin_evaluaciones"
si todavía no hay ninguna) y termina. No imprime nada más, para que el
script de PowerShell pueda leer la salida directamente.

Ejecutar:
    python src/verificar_vencimiento.py
"""

from __future__ import annotations

from historial import dias_desde_ultima_evaluacion

if __name__ == "__main__":
    dias = dias_desde_ultima_evaluacion()
    print("sin_evaluaciones" if dias is None else dias)
