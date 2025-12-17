@echo off
REM Start MCP Server Watchdog (Windows)
REM This monitors servers and automatically restarts them if they crash

echo ========================================
echo Starting MCP Server Watchdog
echo ========================================
echo.
echo The watchdog will monitor all servers and automatically
echo restart them if they crash or become unresponsive.
echo.
echo Press Ctrl+C to stop the watchdog.
echo.
echo ========================================
echo.

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Start watchdog
python mcp_server_watchdog.py

pause
