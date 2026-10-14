@echo off
setlocal
cd /d "%~dp0"
if not exist "runtime\mizan.pid" (
  echo [MIZAN] No running MIZAN server was recorded. Nothing to stop.
  pause
  exit /b 0
)
set /p MIZAN_PID=<"runtime\mizan.pid"
echo [MIZAN] Stopping server process %MIZAN_PID% ...
taskkill /PID %MIZAN_PID% /T /F >nul 2>nul
del /q "runtime\mizan.pid" "runtime\mizan.port" >nul 2>nul
echo [MIZAN] Stopped.
timeout /t 2 >nul
exit /b 0
