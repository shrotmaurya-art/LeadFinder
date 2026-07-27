@echo off
REM ── LeadFinderAI Launcher ─────────────────────────────────────────────
REM Uses %~dp0 so this works from any location (shortcut, USB, etc.).
REM Adjust VENV_DIR below if your virtual environment folder is not .venv.
REM ───────────────────────────────────────────────────────────────────────

set VENV_DIR=.venv
set PORT=8501

cd /d "%~dp0..\.." || echo ERROR: Could not find project root & pause & exit /b 1

if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found at %VENV_DIR%\Scripts\activate.bat
    echo   Adjust VENV_DIR at the top of this script if your venv folder is named differently.
    pause
    exit /b 1
)

call "%VENV_DIR%\Scripts\activate.bat"

echo Starting LeadFinderAI dashboard (port %PORT%)...
start "" /min cmd /c "streamlit run ui/dashboard.py --server.headless true"

echo Waiting for server to start...
timeout /t 5 /nobreak >nul

echo Opening browser...
start http://localhost:%PORT%

exit /b 0
