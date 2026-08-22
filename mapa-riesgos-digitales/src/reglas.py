"""
Motor de reglas del Mapa de Riesgos Digitales.

Cada función evalúa una categoría de hábitos y devuelve:
  - puntaje: 0 (sin riesgo) a 100 (riesgo máximo) para esa categoría
  - alertas: lista de alertas, cada una con severidad, descripción,
    recomendación y los cambios concretos que la resolverían
    (usados por plan_accion.py para simular "qué pasaría si...").

Este motor es la parte "explicable" del sistema: cada punto de riesgo
tiene una causa concreta y una recomendación accionable. El modelo de
ML (ver modelo.py) se entrena por separado para reconocer el patrón
combinado de hábitos y clasificar el riesgo global, pero las alertas
que ve el usuario siempre vienen de aquí.
"""

from __future__ import annotations

CATEGORIAS = ["contraseñas", "actualizaciones", "redes", "respaldo", "dispositivo"]

# Esfuerzo relativo de corregir cada hábito, usado por plan_accion.py para
# priorizar "quick wins" (alto impacto, bajo esfuerzo) sobre cambios que
# cuestan más (ej. dejar de reutilizar contraseñas implica cambiarlas todas).
ESFUERZO_POR_CAMPO = {
    "reutiliza_contraseñas": "alto",
    "longitud_promedio": "medio",
    "usa_gestor": "bajo",
    "usa_2fa": "bajo",
    "cambia_password_tras_filtracion": "bajo",
    "actualizaciones_automaticas": "bajo",
    "dias_desde_actualizacion": "bajo",
    "actualiza_apps": "bajo",
    "usa_wifi_publico_sin_vpn": "medio",
    "usa_vpn": "medio",
    "hace_clic_enlaces_desconocidos": "medio",
    "comparte_red_o_dispositivos": "medio",
    "hace_backups_regulares": "medio",
    "backups_automaticos_en_nube": "bajo",
    "bloqueo_automatico": "bajo",
    "disco_cifrado": "medio",
    "acceso_remoto_habilitado": "bajo",
}


def _clip(valor: float) -> float:
    return max(0.0, min(100.0, valor))


def evaluar_contraseñas(r: dict) -> dict:
    puntaje = 0
    alertas = []

    if r["reutiliza_contraseñas"]:
        puntaje += 30
        alertas.append((
            "alto",
            "Reutilizas la misma contraseña en varios servicios.",
            "Usa una contraseña única por servicio, apoyándote en un gestor de contraseñas.",
            {"reutiliza_contraseñas": False},
        ))

    if r["longitud_promedio"] < 10:
        puntaje += 20
        alertas.append((
            "medio",
            f"Tus contraseñas tienen en promedio {r['longitud_promedio']} caracteres, por debajo de lo recomendado.",
            "Usa contraseñas o frases-contraseña de al menos 14-16 caracteres.",
            {"longitud_promedio": 16},
        ))

    if not r["usa_gestor"]:
        puntaje += 15
        alertas.append((
            "medio",
            "No usas un gestor de contraseñas.",
            "Instala un gestor de contraseñas para generar y guardar contraseñas fuertes y distintas.",
            {"usa_gestor": True},
        ))

    if not r["usa_2fa"]:
        puntaje += 25
        alertas.append((
            "alto",
            "No tienes activada la autenticación en dos pasos (2FA) en tus cuentas principales.",
            "Activa 2FA (app autenticadora o llave física) al menos en correo, banca y redes sociales.",
            {"usa_2fa": True},
        ))

    if not r["cambia_password_tras_filtracion"]:
        puntaje += 10
        alertas.append((
            "bajo",
            "No sueles cambiar tus contraseñas cuando te enteras de una filtración de datos.",
            "Cuando un servicio reporte una filtración, cambia esa contraseña de inmediato (y en cualquier otro sitio donde la hayas reutilizado).",
            {"cambia_password_tras_filtracion": True},
        ))

    return {"puntaje": round(_clip(puntaje)), "alertas": alertas}


def evaluar_actualizaciones(r: dict) -> dict:
    puntaje = 0
    alertas = []

    if not r["actualizaciones_automaticas"]:
        puntaje += 25
        alertas.append((
            "medio",
            "No tienes activadas las actualizaciones automáticas del sistema operativo.",
            "Activa las actualizaciones automáticas para recibir parches de seguridad sin depender de acordarte.",
            {"actualizaciones_automaticas": True},
        ))

    dias = r["dias_desde_actualizacion"]
    if dias > 90:
        puntaje += 40
        severidad = "alto"
    elif dias > 30:
        puntaje += 20
        severidad = "medio"
    else:
        severidad = None
    if severidad:
        alertas.append((
            severidad,
            f"Han pasado {dias} días desde tu última actualización de sistema.",
            "Revisa e instala las actualizaciones pendientes del sistema operativo lo antes posible.",
            {"dias_desde_actualizacion": 0},
        ))

    if not r["actualiza_apps"]:
        puntaje += 15
        alertas.append((
            "bajo",
            "No actualizas tus aplicaciones con regularidad.",
            "Activa las actualizaciones automáticas también para tus aplicaciones y navegador.",
            {"actualiza_apps": True},
        ))

    return {"puntaje": round(_clip(puntaje)), "alertas": alertas}


def evaluar_redes(r: dict) -> dict:
    puntaje = 0
    alertas = []

    if r["usa_wifi_publico_sin_vpn"]:
        puntaje += 30
        alertas.append((
            "alto",
            "Te conectas a redes wifi públicas sin usar VPN.",
            "Evita transacciones sensibles en wifi público, o usa una VPN de confianza al conectarte.",
            {"usa_wifi_publico_sin_vpn": False},
        ))

    if not r["usa_vpn"]:
        puntaje += 10
        alertas.append((
            "bajo",
            "No usas VPN en tu día a día.",
            "Considera usar una VPN, especialmente en redes que no controlas.",
            {"usa_vpn": True},
        ))

    if r["hace_clic_enlaces_desconocidos"]:
        puntaje += 35
        alertas.append((
            "alto",
            "Sueles hacer clic en enlaces o adjuntos de origen desconocido.",
            "Verifica el remitente y la URL antes de hacer clic; ante la duda, no lo abras.",
            {"hace_clic_enlaces_desconocidos": False},
        ))

    if r["comparte_red_o_dispositivos"]:
        puntaje += 15
        alertas.append((
            "medio",
            "Compartes dispositivos o redes sin controles (perfiles separados, contraseña de red, etc.).",
            "Usa perfiles de usuario separados y una red de invitados para dispositivos o personas externas.",
            {"comparte_red_o_dispositivos": False},
        ))

    return {"puntaje": round(_clip(puntaje)), "alertas": alertas}


def evaluar_respaldo(r: dict) -> dict:
    puntaje = 0
    alertas = []

    if not r["hace_backups_regulares"]:
        puntaje += 50
        alertas.append((
            "alto",
            "No haces copias de seguridad de tu información con regularidad.",
            "Programa copias de seguridad periódicas de tus archivos importantes.",
            {"hace_backups_regulares": True},
        ))

    if not r["backups_automaticos_en_nube"]:
        puntaje += 30
        alertas.append((
            "medio",
            "No tienes copias de seguridad automáticas en la nube.",
            "Activa un respaldo automático en la nube como complemento a tu copia local.",
            {"backups_automaticos_en_nube": True},
        ))

    return {"puntaje": round(_clip(puntaje)), "alertas": alertas}


def evaluar_dispositivo(r: dict) -> dict:
    """Riesgo por acceso físico al equipo: a diferencia de las otras
    categorías (orientadas a amenazas remotas), esta cubre qué pasa si
    alguien tiene el dispositivo en la mano (robo, pérdida, descuido)."""
    puntaje = 0
    alertas = []

    if not r["bloqueo_automatico"]:
        puntaje += 40
        alertas.append((
            "alto",
            "Tu pantalla no se bloquea sola (con contraseña o PIN) al dejar el equipo desatendido.",
            "Activa el bloqueo automático con contraseña/PIN tras 1-5 minutos de inactividad.",
            {"bloqueo_automatico": True},
        ))

    if not r["disco_cifrado"]:
        puntaje += 35
        alertas.append((
            "alto",
            "El disco de tu equipo no está cifrado.",
            "Activa BitLocker (o Cifrado de dispositivo) para que tus archivos sean ilegibles si te roban o perdés el equipo.",
            {"disco_cifrado": True},
        ))

    if r["acceso_remoto_habilitado"]:
        puntaje += 25
        alertas.append((
            "medio",
            "Tenés el Escritorio remoto (RDP) u otro acceso remoto habilitado en este equipo.",
            "Desactívalo si no lo usás activamente, o al menos restringilo a una VPN y con 2FA.",
            {"acceso_remoto_habilitado": False},
        ))

    return {"puntaje": round(_clip(puntaje)), "alertas": alertas}


EVALUADORES = {
    "contraseñas": evaluar_contraseñas,
    "actualizaciones": evaluar_actualizaciones,
    "redes": evaluar_redes,
    "respaldo": evaluar_respaldo,
    "dispositivo": evaluar_dispositivo,
}


def evaluar_todo(respuestas: dict) -> dict:
    """Ejecuta las 4 categorías y arma el mapa de riesgo por reglas."""
    resultado = {}
    todas_alertas = []
    for categoria, fn in EVALUADORES.items():
        r = fn(respuestas)
        resultado[categoria] = r["puntaje"]
        for severidad, descripcion, recomendacion, cambios in r["alertas"]:
            todas_alertas.append({
                "categoria": categoria,
                "severidad": severidad,
                "descripcion": descripcion,
                "recomendacion": recomendacion,
                "cambios_sugeridos": cambios,
            })

    orden_severidad = {"alto": 0, "medio": 1, "bajo": 2}
    todas_alertas.sort(key=lambda a: orden_severidad[a["severidad"]])

    puntaje_global = round(sum(resultado.values()) / len(resultado))

    return {
        "puntajes_por_categoria": resultado,
        "puntaje_global_reglas": puntaje_global,
        "alertas": todas_alertas,
    }
