@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Please complete the one-time setup in START_HERE.md first.
  pause
  exit /b 1
)
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
