@echo off
echo ===================================
echo Starting AutoGen System
echo ===================================
echo.

REM Activate virtual environment
if exist "venv\Scripts\activate.bat" (
    echo [1/2] Activating virtual environment...
    call venv\Scripts\activate.bat
    echo [OK] Virtual environment activated
    echo.
) else (
    echo [WARNING] No virtual environment found at venv\Scripts\activate.bat
    echo [WARNING] Using global Python installation
    echo.
)

REM Run main.py
echo [2/2] Starting application...
echo.
python main.py

pause
