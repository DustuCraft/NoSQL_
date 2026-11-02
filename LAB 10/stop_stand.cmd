@echo off
rem Stops the MongoLab10 stand (watchdog + all three mongod instances).
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop_stand.ps1"
echo.
pause
