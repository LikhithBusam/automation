@echo off
REM Stop MCP Servers (Windows)

echo ========================================
echo Stopping MCP Servers
echo ========================================
echo.

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Stop servers using daemon
python mcp_server_daemon.py stop

echo.
pause
