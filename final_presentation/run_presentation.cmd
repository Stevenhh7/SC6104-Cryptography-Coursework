@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -X utf8 scripts\presentation_server.py %*
) else if exist "..\.venv\Scripts\python.exe" (
  "..\.venv\Scripts\python.exe" -X utf8 scripts\presentation_server.py %*
) else (
  python -X utf8 scripts\presentation_server.py %*
)
if errorlevel 1 (
  echo Presentation server stopped with an error. See presentation\README.md.
  pause
)
