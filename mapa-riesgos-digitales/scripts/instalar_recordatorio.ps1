# Registra una tarea programada de Windows que corre recordatorio.ps1 una
# vez por semana. Este script MODIFICA el sistema (crea una tarea
# persistente en el Programador de tareas) — ejecutalo vos mismo cuando
# quieras activarlo; no se ejecuta solo.
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File scripts\instalar_recordatorio.ps1
#
# Para quitarlo más tarde, corré scripts\desinstalar_recordatorio.ps1.

$nombreTarea = "MapaRiesgosDigitales_Recordatorio"
$raiz = Split-Path -Parent $PSScriptRoot
$scriptRecordatorio = Join-Path $raiz "scripts\recordatorio.ps1"

$accion = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$scriptRecordatorio`""

$disparador = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 9am

Register-ScheduledTask -TaskName $nombreTarea `
    -Action $accion `
    -Trigger $disparador `
    -Description "Recuerda reevaluar tus hábitos en el Mapa de Riesgos Digitales si pasó demasiado tiempo desde la última vez." `
    -Force

Write-Host "Tarea '$nombreTarea' registrada: se ejecutará todos los lunes a las 9:00."
Write-Host "Para quitarla: powershell -ExecutionPolicy Bypass -File scripts\desinstalar_recordatorio.ps1"
