# Quita la tarea programada creada por instalar_recordatorio.ps1.
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File scripts\desinstalar_recordatorio.ps1

$nombreTarea = "MapaRiesgosDigitales_Recordatorio"

if (Get-ScheduledTask -TaskName $nombreTarea -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $nombreTarea -Confirm:$false
    Write-Host "Tarea '$nombreTarea' eliminada."
} else {
    Write-Host "No se encontró la tarea '$nombreTarea' (puede que ya esté desinstalada)."
}
