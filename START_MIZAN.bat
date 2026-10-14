@echo off
setlocal
title MIZAN - starting
cd /d "%~dp0"

rem Find a usable Python: the "py" launcher first, then "python".
set "PYCMD="
where py >nul 2>nul && set "PYCMD=py -3"
if not defined PYCMD (
  where python >nul 2>nul && set "PYCMD=python"
)
if not defined PYCMD (
  echo.
  echo [MIZAN] Python was not found.
  echo         Install Python 3.12 from https://www.python.org/downloads/
  echo         and tick "Add python.exe to PATH", then double-click START_MIZAN.bat again.
  echo         Details: SETUP_WINDOWS.md
  echo.
  pause
  exit /b 1
)

%PYCMD% launcher.py %*
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo.
  echo [MIZAN] Stopped with an error ^(code %RC%^). See the messages above and SETUP_WINDOWS.md.
  pause
)
exit /b %RC%
