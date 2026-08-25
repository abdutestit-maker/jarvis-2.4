@echo off
set "ROOT=%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%ROOT%Start-JARVIS.ps1"
pause
