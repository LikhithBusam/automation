@echo off
REM Start MCP Servers in Background (Windows)
REM This starts all servers and they will continue running even after closing this window

echo ========================================
echo Starting MCP Servers in Background
echo ========================================
echo.

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Start servers using daemon
python mcp_server_daemon.py start

echo.
echo Servers are now running in the background.
echo You can safely close this window.
echo.
echo To check status: run check_servers.bat
echo To stop servers: run stop_servers.bat
echo.
pause
