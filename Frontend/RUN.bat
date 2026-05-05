@echo off
title DECEPTRON Launcher
setlocal enabledelayedexpansion

:START
cls
echo =============================
echo      Starting DECEPTRON
echo =============================
echo.

:: Validate Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.9+ and ensure it's in your PATH.
    pause
    exit /b 1
)

cd /d "%~dp0"
if errorlevel 1 (
    echo [ERROR] Failed to change to script directory.
    pause
    exit /b 1
)

:: Check if virtual environment exists
if not exist "myenv\" (
    echo [INFO] Virtual environment not found.
    echo [INFO] Creating virtual environment...
    python -m venv myenv

    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )

    echo [INFO] Activating environment...
    call myenv\Scripts\activate.bat

    if errorlevel 1 (
        echo [ERROR] Failed to activate virtual environment.
        pause
        exit /b 1
    )

    echo [INFO] Installing requirements...
    pip install -r requirements.txt

    if errorlevel 1 (
        echo [ERROR] Failed to install requirements.
        echo Make sure requirements.txt exists and is valid.
        pause
        exit /b 1
    )
) else (
    echo [INFO] Virtual environment found. Activating...
    call myenv\Scripts\activate.bat
    
    if errorlevel 1 (
        echo [ERROR] Failed to activate virtual environment.
        echo The virtual environment may be corrupted. Try deleting the 'myenv' folder and re-running this script.
        pause
        exit /b 1
    )
)

echo [INFO] Running application...
echo.

:: Run the main application with error handling and restart capability
call python main.py
set PYTHON_EXIT_CODE=!errorlevel!

if !PYTHON_EXIT_CODE! equ 0 (
    echo.
    echo [INFO] Application exited normally.
) else (
    echo.
    echo [ERROR] Application exited with code !PYTHON_EXIT_CODE!.
    echo Attempting to restart in 5 seconds... Press Ctrl+C to cancel.
    timeout /t 5 /nobreak >nul
    goto START
)

echo.
echo Application closed normally.
pause
