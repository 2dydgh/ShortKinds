@echo off
echo ========================================
echo Short Kinds - Modern Web App Launcher
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo Error: Failed to create virtual environment
        echo Please make sure Python is installed
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo.
echo Installing dependencies...
pip install -r backend\requirements.txt
if errorlevel 1 (
    echo Error: Failed to install dependencies
    pause
    exit /b 1
)

REM Start server
echo.
echo ========================================
echo Starting FastAPI server...
echo.
echo Open your browser and go to:
echo http://localhost:8000
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

pause
