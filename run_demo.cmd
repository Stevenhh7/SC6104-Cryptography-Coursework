@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -X utf8 -m rsa_lab demo
) else if exist "..\.venv\Scripts\python.exe" (
  "..\.venv\Scripts\python.exe" -X utf8 -m rsa_lab demo
) else (
  python -X utf8 -m rsa_lab demo
)
if errorlevel 1 echo Demo failed. Please check START_HERE.md.
pause
