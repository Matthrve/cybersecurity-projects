# Lee señales reales de seguridad del equipo Windows y las devuelve como JSON.
# Cada chequeo está aislado en su propio try/catch: si uno falla (por permisos,
# versión de Windows, módulo ausente, etc.) devuelve $null para ese campo en
# vez de abortar todo el diagnóstico. No hace ningún cambio en el sistema,
# solo lectura.

$resultado = [ordered]@{
    actualizaciones_automaticas = $null
    dias_desde_actualizacion    = $null
    firewall_activo             = $null
    antivirus_activo            = $null
    proteccion_tiempo_real      = $null
    bloqueo_automatico          = $null
    disco_cifrado               = $null
    acceso_remoto_habilitado    = $null
    errores                     = @()
}

try {
    $au = (New-Object -ComObject "Microsoft.Update.AutoUpdate").Settings
    # NotificationLevel: 4 = descarga e instala automáticamente
    $resultado.actualizaciones_automaticas = ($au.NotificationLevel -eq 4)
} catch {
    $resultado.errores += "actualizaciones_automaticas: $($_.Exception.Message)"
}

try {
    $ultimoHotfix = Get-HotFix -ErrorAction Stop |
        Sort-Object InstalledOn -Descending |
        Select-Object -First 1 -ExpandProperty InstalledOn
    if ($ultimoHotfix) {
        $resultado.dias_desde_actualizacion = [int]((Get-Date) - $ultimoHotfix).TotalDays
    }
} catch {
    $resultado.errores += "dias_desde_actualizacion: $($_.Exception.Message)"
}

try {
    $perfiles = Get-NetFirewallProfile -ErrorAction Stop
    $resultado.firewall_activo = -not ($perfiles.Enabled -contains $false)
} catch {
    $resultado.errores += "firewall_activo: $($_.Exception.Message)"
}

try {
    $defender = Get-MpComputerStatus -ErrorAction Stop
    $resultado.antivirus_activo = [bool]$defender.AntivirusEnabled
    $resultado.proteccion_tiempo_real = [bool]$defender.RealTimeProtectionEnabled
} catch {
    $resultado.errores += "antivirus_defender: $($_.Exception.Message)"
}

try {
    # Heurística: pantalla protegida con contraseña y con un tiempo de espera
    # razonable (<=10 min). No detecta bloqueo por política de energía/Hello,
    # así que puede dar falso "no" en equipos que igual están protegidos.
    $desktop = Get-ItemProperty -Path "HKCU:\Control Panel\Desktop" -ErrorAction Stop
    $activo = $desktop.ScreenSaveActive -eq "1"
    $seguro = $desktop.ScreenSaverIsSecure -eq "1"
    $timeout = [int]($desktop.ScreenSaveTimeOut)
    $resultado.bloqueo_automatico = ($activo -and $seguro -and $timeout -gt 0 -and $timeout -le 600)
} catch {
    $resultado.errores += "bloqueo_automatico: $($_.Exception.Message)"
}

try {
    $volumen = Get-BitLockerVolume -MountPoint $env:SystemDrive -ErrorAction Stop
    $resultado.disco_cifrado = ($volumen.ProtectionStatus -eq "On" -or [int]$volumen.ProtectionStatus -eq 1)
} catch {
    $resultado.errores += "disco_cifrado: $($_.Exception.Message) (puede requerir permisos de administrador)"
}

try {
    $ts = Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server" -ErrorAction Stop
    # fDenyTSConnections: 0 = Escritorio remoto habilitado, 1 = deshabilitado
    $resultado.acceso_remoto_habilitado = ($ts.fDenyTSConnections -eq 0)
} catch {
    $resultado.errores += "acceso_remoto_habilitado: $($_.Exception.Message)"
}

$resultado | ConvertTo-Json -Compress
