@echo off
rem Starts the MongoLab10 watchdog (keeps the 3-node replica set alive).
powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0stand.ps1"
