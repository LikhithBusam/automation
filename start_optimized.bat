@echo off
REM Optimized startup script for Windows
REM Fast initialization with production configuration

echo ========================================
echo   Intelligent Development Assistant
echo   Optimized Startup (Fast Mode)
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please run: python -m venv venv
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Check if .env file exists
if not exist ".env" (
    echo WARNING: .env file not found!
    echo Creating .env from .env.example...
    copy .env.example .env
    echo.
    echo IMPORTANT: Please edit .env and add your HF_API_TOKEN
    echo Press any key to continue once you've updated .env...
    pause >nul
)

REM Set environment for production
set CONFIG_FILE=config\config.production.yaml

REM Check if production config exists
if not exist "%CONFIG_FILE%" (
    echo ERROR: Production config not found at %CONFIG_FILE%
    echo Please ensure config.production.yaml exists
    exit /b 1
)

echo Starting with optimized configuration...
echo Config: %CONFIG_FILE%
echo.

REM Start the application with production config
python main.py --config %CONFIG_FILE%

REM Deactivate virtual environment on exit
deactivate
