@echo off
echo Starting Interactive Albedo Analysis Dashboard...
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8+ and try again
    pause
    exit /b 1
)

REM Run the dashboard
python run_dashboard.py

REM Keep window open if there's an error
if errorlevel 1 (
    echo.
    echo Dashboard exited with error. Check the output above.
    pause
)