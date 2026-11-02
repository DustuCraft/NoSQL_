# Install autostart for the MongoLab10 stand.
# Run this file yourself (right-click -> "Run with PowerShell", or in a PowerShell window).
# Registers a logon scheduled task AND a Startup-folder shortcut.
$ErrorActionPreference = 'Continue'
$base = 'C:\Users\erzan\Documents\deepseek-harness\default-workspace\lab10'
$standScript = Join-Path $base 'stand.ps1'
$ps = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$tr = '-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $standScript + '"'

Write-Host '=== 1. Scheduled task (logon) ==='
try {
    $action = New-ScheduledTaskAction -Execute $ps -Argument $tr -WorkingDirectory $base
    $trigger = New-ScheduledTaskTrigger -AtLogOn
    Register-ScheduledTask -TaskName 'MongoLab10Stand' -Action $action -Trigger $trigger `
        -Description 'MongoDB rsLab10 watchdog (Lab 10)' -Force | Out-Null
    Write-Host '  task MongoLab10Stand created'
    Start-ScheduledTask -TaskName 'MongoLab10Stand'
    Write-Host '  task started'
} catch {
    Write-Host ('  task failed: {0}' -f $_.Exception.Message)
    Write-Host '  (try running this script as Administrator)'
}

Write-Host '=== 2. Startup folder shortcut ==='
try {
    $startup = [Environment]::GetFolderPath('Startup')
    $lnkPath = Join-Path $startup 'MongoLab10.lnk'
    $ws = New-Object -ComObject WScript.Shell
    $lnk = $ws.CreateShortcut($lnkPath)
    $lnk.TargetPath = $ps
    $lnk.Arguments = $tr
    $lnk.WorkingDirectory = $base
    $lnk.Description = 'MongoDB rsLab10 watchdog (Lab 10)'
    $lnk.Save()
    Write-Host ('  shortcut created: {0}' -f $lnkPath)
} catch {
    Write-Host ('  shortcut failed: {0}' -f $_.Exception.Message)
}

Write-Host ''
Write-Host 'Check status: powershell -File "' + (Join-Path $base 'stand.ps1') + '" runs the watchdog.'
Write-Host 'Stop the stand: ' + (Join-Path $base 'stop_stand.ps1')
