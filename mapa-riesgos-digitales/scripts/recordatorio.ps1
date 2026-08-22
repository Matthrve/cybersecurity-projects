# Recordatorio proactivo del Mapa de Riesgos Digitales.
#
# Pensado para ejecutarse periódicamente vía el Programador de tareas de
# Windows (ver instalar_recordatorio.ps1). Consulta el historial local de
# evaluaciones y, si pasaron demasiados días desde la última (o nunca se
# hizo ninguna), muestra un aviso emergente invitando a reevaluar. No hace
# ningún cambio en el sistema ni abre la app automáticamente.

param(
    [int]$UmbralDias = 30
)

$raiz = Split-Path -Parent $PSScriptRoot
$python = Join-Path $raiz "venv\Scripts\python.exe"
$script = Join-Path $raiz "src\verificar_vencimiento.py"

if (-not (Test-Path $python)) {
    Write-Error "No se encontró el entorno virtual en $python. Ejecuta primero la instalación del proyecto."
    exit 1
}

$salida = & $python $script
$salida = $salida.Trim()

$avisar = $false
$mensaje = ""

if ($salida -eq "sin_evaluaciones") {
    $avisar = $true
    $mensaje = "Todavía no registraste ninguna evaluación en el Mapa de Riesgos Digitales. Tomate 3 minutos para revisar tus hábitos de seguridad."
} else {
    $dias = [int]$salida
    if ($dias -ge $UmbralDias) {
        $avisar = $true
        $mensaje = "Han pasado $dias días desde tu última evaluación de riesgos digitales. Tus respuestas pueden estar desactualizadas: vale la pena repetirla."
    }
}

if ($avisar) {
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show(
        $mensaje,
        "Mapa de Riesgos Digitales",
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Warning
    ) | Out-Null
}
