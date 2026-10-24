@echo off
title OmniPitch - Live Match Intelligence Platform
color 0B
cd /d "%~dp0"

echo =====================================================================
echo           OmniPitch - Personalized Match Intelligence
echo                     Microsoft AI Hackathon
echo =====================================================================
echo.
echo [*] Checking Python virtual environment...

if exist ".venv\Scripts\python.exe" (
    echo [*] Virtual environment verified: .venv
) else (
    echo [!] Virtual environment not found. Initializing .venv...
    python -m venv .venv
    echo [*] Installing dependencies...
    .venv\Scripts\pip.exe install -e ".[dev]"
)

echo [*] Starting OmniPitch API and Web Server...
echo [*] Dashboard URL: http://127.0.0.1:8000
echo [*] Opening your browser in 2 seconds...
echo.
echo =====================================================================
echo  Press Ctrl+C in this terminal window to stop the server at any time.
echo =====================================================================
echo.

:: Open browser after 2 seconds in background
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:8000/"

:: Start FastAPI application with Uvicorn
.venv\Scripts\uvicorn.exe omnipitch.api:app --host 127.0.0.1 --port 8000 --reload

echo.
echo Server stopped.
pause
