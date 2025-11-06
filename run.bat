@echo off
echo ========================================
echo Taxi Service Backend - Quick Start
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
    echo.
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate
echo.

REM Check if .env exists
if not exist ".env" (
    echo ERROR: .env file not found!
    echo Please copy .env.example to .env and configure it.
    echo.
    pause
    exit /b 1
)

REM Install/update dependencies
echo Checking dependencies...
pip install -q -r requirements.txt
echo Dependencies installed.
echo.

REM Start the application
echo ========================================
echo Starting Taxi Service API...
echo Server will be available at: http://localhost:8000
echo API Documentation: http://localhost:8000/docs
echo ========================================
echo.
echo Press Ctrl+C to stop the server
echo.

python main.py
