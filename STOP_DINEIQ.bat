@echo off
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5000" ^| findstr "LISTENING"') do taskkill /PID %%a /F >nul 2>&1
echo DineIQ local server stopped if it was running on port 5000.
pause
