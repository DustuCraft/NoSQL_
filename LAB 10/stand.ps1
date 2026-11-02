# MongoLab10 watchdog: keeps the 3-node replica set alive.
# Restarts a mongod if its port stops answering. Logs to logs\watchdog.log.
$ErrorActionPreference = 'SilentlyContinue'
$base = 'C:\Users\erzan\Documents\deepseek-harness\default-workspace\lab10'
$mongod = 'A:\mongo\bin\mongod.exe'
$logfile = Join-Path $base 'logs\watchdog.log'
$pidfile = Join-Path $base 'logs\watchdog.pid'
$nodes = @(1, 2, 3)

function Write-Log([string]$msg) {
    $line = "{0} {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $msg
    Add-Content -Path $logfile -Value $line -Encoding UTF8
}

function Test-MongoPort([int]$port) {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $task = $client.ConnectAsync('127.0.0.1', $port)
        if ($task.Wait(400) -and $client.Connected) { return $true }
        return $false
    } catch {
        return $false
    } finally {
        $client.Dispose()
    }
}

# refuse to run a second copy
if (Test-Path $pidfile) {
    $old = Get-Content $pidfile -ErrorAction SilentlyContinue
    if ($old -and (Get-Process -Id $old -ErrorAction SilentlyContinue)) {
        Write-Host "watchdog already running (pid $old)"
        exit 0
    }
}
Set-Content -Path $pidfile -Value $PID -Encoding ASCII

try {
    Write-Log 'watchdog started'
    $lastAttempt = @{}
    $pausefile = Join-Path $base 'logs\watchdog.pause'
    while ($true) {
        # a lab run sets logs\watchdog.pause so the watchdog does not fight it
        if (-not (Test-Path $pausefile)) {
            foreach ($i in $nodes) {
                $port = 27100 + $i
                if (-not (Test-MongoPort $port)) {
                    $now = Get-Date
                    $recent = $false
                    if ($lastAttempt.ContainsKey($i)) {
                        if (($now - $lastAttempt[$i]).TotalSeconds -lt 15) { $recent = $true }
                    }
                    if (-not $recent) {
                        $lastAttempt[$i] = $now
                        $cfg = Join-Path $base ("config\rs{0}.cfg" -f $i)
                        Start-Process -FilePath $mongod -ArgumentList '--config', $cfg -WindowStyle Hidden
                        Write-Log ("restart rs{0} (port {1})" -f $i, $port)
                    }
                }
            }
        }
        Start-Sleep -Seconds 5
    }
} finally {
    Remove-Item -Path $pidfile -ErrorAction SilentlyContinue
    Write-Log 'watchdog stopped'
}
