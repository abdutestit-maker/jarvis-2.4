@echo off
setlocal
pushd "%~dp0..\jarvis"
echo Starting JARVIS Tauri frontend from %CD%
call npm run tauri:dev
set "EXIT_CODE=%ERRORLEVEL%"
popd
exit /b %EXIT_CODE%
