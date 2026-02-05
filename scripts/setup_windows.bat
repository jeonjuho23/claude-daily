@echo off
REM Daily-Bot Windows Setup Script
REM Creates Task Scheduler task with wake-from-sleep capability

setlocal enabledelayedexpansion

echo ================================================
echo Daily-Bot Windows Setup
echo ================================================

REM Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.11+ and try again
    exit /b 1
)

REM Get script directory
set SCRIPT_DIR=%~dp0
set PROJECT_DIR=%SCRIPT_DIR%..

REM Create virtual environment if not exists
if not exist "%PROJECT_DIR%\venv" (
    echo Creating virtual environment...
    python -m venv "%PROJECT_DIR%\venv"
)

REM Activate virtual environment
call "%PROJECT_DIR%\venv\Scripts\activate.bat"

REM Install dependencies
echo Installing dependencies...
pip install -r "%PROJECT_DIR%\requirements.txt" --quiet

REM Check for .env file
if not exist "%PROJECT_DIR%\.env" (
    echo.
    echo WARNING: .env file not found!
    echo Please copy .env.example to .env and configure your settings.
    echo.
    copy "%PROJECT_DIR%\.env.example" "%PROJECT_DIR%\.env"
    echo Created .env from template. Please edit it with your API keys.
)

REM Create data directory
if not exist "%PROJECT_DIR%\data" mkdir "%PROJECT_DIR%\data"
if not exist "%PROJECT_DIR%\logs" mkdir "%PROJECT_DIR%\logs"

echo.
echo Setup complete!
echo.
echo To run Daily-Bot manually:
echo   cd "%PROJECT_DIR%"
echo   venv\Scripts\activate
echo   python main.py
echo.
echo To create a scheduled task (requires Administrator):
echo   scripts\install_task.bat
echo.

pause
