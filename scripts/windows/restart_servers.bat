@echo off
REM Restart MCP Servers (Windows)

echo ========================================
echo Restarting MCP Servers
echo ========================================
echo.

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Restart servers using daemon
python mcp_server_daemon.py restart

echo.
pause
