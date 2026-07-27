@echo off
setlocal enabledelayedexpansion
REM ── LeadFinderAI Stopper ────────────────────────────────────────────
REM Kills the Streamlit process listening on port 8501 using netstat.
REM Falls back to killing all streamlit.exe instances if netstat fails.
REM ────────────────────────────────────────────────────────────────────

set PORT=8501
set FOUND=0

echo Looking for Streamlit on port %PORT%...

for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%PORT% ^| findstr LISTENING') do (
    echo Killing process PID %%a ...
    taskkill /F /PID %%a >nul 2>&1
    if !errorlevel! equ 0 (
        echo Streamlit on port %PORT% has been stopped.
    ) else (
        echo Failed to kill PID %%a — try running as Administrator.
    )
    set FOUND=1
)

if !FOUND! equ 0 (
    echo No process found listening on port %PORT%.
    echo Searching for any streamlit.exe process...
    taskkill /F /IM streamlit.exe >nul 2>&1
    if !errorlevel! equ 0 (
        echo Streamlit process(es) stopped.
    ) else (
        echo No running Streamlit processes found.
    )
)

pause
