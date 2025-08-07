@echo off
REM Crypto Trading Bot - Trade Review Launcher (Windows)
REM This script launches the trade review interface

echo Starting Crypto Trading Bot Trade Review...
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python and try again
    pause
    exit /b 1
)

REM Check if the review script exists
if not exist "review_trades.py" (
    echo ERROR: review_trades.py not found
    echo Make sure you're running this from the correct directory
    pause
    exit /b 1
)

REM Run the review script with any arguments passed to this batch file
python review_trades.py %*

REM Keep window open if there was an error
if errorlevel 1 (
    echo.
    echo Script encountered an error. Press any key to close...
    pause >nul
)