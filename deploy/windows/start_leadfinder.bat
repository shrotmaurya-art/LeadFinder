@echo off
setlocal
set VENV_DIR=.venv
set PORT=8501

echo [1/5] Script folder: %~dp0
cd /d "%~dp0..\.."
if errorlevel 1 (
    echo ERROR: Could not cd to project root from %~dp0..\..
    pause
    exit /b 1
)

echo [2/5] Project root resolved to: %cd%

if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo ERROR: venv not found at %cd%\%VENV_DIR%\Scripts\activate.bat
    echo Contents of current directory:
    dir /b
    pause
    exit /b 1
)

echo [3/5] Found venv, activating...
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
    echo ERROR: venv activation failed
    pause
    exit /b 1
)

echo [4/5] Activated. Starting Streamlit on port %PORT%...
start "LeadFinderAI" /min cmd /k "streamlit run ui/dashboard.py --server.headless true"

echo [5/5] Waiting for server, then opening browser...
timeout /t 6 /nobreak >nul
start http://localhost:%PORT%

echo Done. If the browser didn't open, visit http://localhost:%PORT% manually.
exit /b 0