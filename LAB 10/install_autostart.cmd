@echo off
rem Installs autostart for the MongoLab10 stand (scheduled task + Startup shortcut).
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_autostart.ps1"
echo.
pause
