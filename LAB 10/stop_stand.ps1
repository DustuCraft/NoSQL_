# Stops the MongoLab10 stand: watchdog + all three mongod instances.
$ErrorActionPreference = 'SilentlyContinue'
$base = 'C:\Users\erzan\Documents\deepseek-harness\default-workspace\lab10'
$py = 'C:\Users\erzan\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'

Write-Host 'Stopping watchdog...'
Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" |
    Where-Object { $_.CommandLine -like '*stand.ps1*' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force }

Write-Host 'Shutting down nodes...'
& $py (Join-Path $base 'tools\shutdown_stand.py')

Write-Host 'Done. To disable autostart, delete the shortcut:'
Write-Host ("  {0}\Microsoft\Windows\Start Menu\Programs\Startup\MongoLab10.lnk" -f $env:APPDATA)
