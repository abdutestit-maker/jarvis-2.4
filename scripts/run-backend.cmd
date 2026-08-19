@echo off
setlocal
pushd "%~dp0.."
set "JARVIS_PYTHON="
rem Prefer a runtime that actually imports llama_cpp. The old user venv can
rem exist without the local model dependency and would start a dead backend.
if defined JARVIS_PYTHON if exist "%JARVIS_PYTHON%" (
  "%JARVIS_PYTHON%" -c "import llama_cpp" >nul 2>nul
  if errorlevel 1 set "JARVIS_PYTHON="
)
for %%P in (
  "%CD%\runtime\python.exe"
  "%CD%\.venv\Scripts\python.exe"
  "%USERPROFILE%\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe"
  "%USERPROFILE%\venv\Scripts\python.exe"
) do (
  if not defined JARVIS_PYTHON if exist "%%~P" (
    "%%~P" -c "import llama_cpp" >nul 2>nul
    if not errorlevel 1 set "JARVIS_PYTHON=%%~P"
  )
)
if not defined JARVIS_PYTHON set "JARVIS_PYTHON=python"
echo Starting JARVIS backend from %CD%
"%JARVIS_PYTHON%" -m core.ws_server
set "EXIT_CODE=%ERRORLEVEL%"
popd
exit /b %EXIT_CODE%
