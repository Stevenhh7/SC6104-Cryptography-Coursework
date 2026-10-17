@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set "PRESENTATION_PYTHON=python"
if exist "%~dp0..\..\.venv\Scripts\python.exe" set "PRESENTATION_PYTHON=%~dp0..\..\.venv\Scripts\python.exe"
if exist "%~dp0..\.venv\Scripts\python.exe" set "PRESENTATION_PYTHON=%~dp0..\.venv\Scripts\python.exe"
if exist "%~dp0.venv\Scripts\python.exe" set "PRESENTATION_PYTHON=%~dp0.venv\Scripts\python.exe"
"%PRESENTATION_PYTHON%" -u -X utf8 "%~dp0scripts\presentation_server.py" --open-browser %*
if errorlevel 1 (
  echo Presentation server stopped with an error. See presentation\README.md.
  pause
)
