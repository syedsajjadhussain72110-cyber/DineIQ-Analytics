@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0SETUP_DINEIQ.ps1"
if errorlevel 1 (
  echo.
  echo DineIQ setup failed. Read the red error above.
  pause
  exit /b 1
)
pause
