@echo off
setlocal
pushd "%~dp0.."
set "JARVIS_PYTHON=%USERPROFILE%\venv\Scripts\python.exe"
if not exist "%JARVIS_PYTHON%" set "JARVIS_PYTHON=python"
echo Starting JARVIS backend from %CD%
"%JARVIS_PYTHON%" -m core.ws_server
set "EXIT_CODE=%ERRORLEVEL%"
popd
exit /b %EXIT_CODE%
