@echo off
REM Check MCP Server Status (Windows)

echo ========================================
echo MCP Server Status
echo ========================================
echo.

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Check server status
python mcp_server_daemon.py status

echo.
pause
