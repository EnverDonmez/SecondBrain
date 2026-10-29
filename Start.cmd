@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Start.ps1" -Background
if errorlevel 1 (
    echo Second Brain could not start. Review the message above.
    pause
    exit /b 1
)
start "" "http://127.0.0.1:8765"
