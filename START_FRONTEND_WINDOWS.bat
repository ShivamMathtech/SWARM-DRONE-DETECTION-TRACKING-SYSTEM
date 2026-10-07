@echo off
cd /d "%~dp0frontend"
if not exist "node_modules" (
  echo Please run npm install in the frontend folder first.
  pause
  exit /b 1
)
call npm run dev
pause
