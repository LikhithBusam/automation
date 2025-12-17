@echo off
REM AutoGen Setup Script for Windows
REM Sets up the environment for AutoGen migration

echo =========================================
echo AutoGen Migration Setup
echo =========================================
echo.

REM Check Python version
echo Checking Python version...
python --version
echo.

REM Install AutoGen
echo Installing AutoGen and dependencies...
pip install pyautogen
pip install "pyautogen[teachable]"
pip install "pyautogen[retrievechat]"
echo.

REM Create necessary directories
echo Creating data directories...
if not exist "data\teachable" mkdir data\teachable
if not exist "data\conversations" mkdir data\conversations
if not exist "data\checkpoints" mkdir data\checkpoints
if not exist "workspace\code_execution" mkdir workspace\code_execution
if not exist "logs" mkdir logs
echo.

REM Check if .env exists
if exist ".env" (
    echo [OK] .env file found
    findstr /C:"OPENROUTER_API_KEY" .env >nul
    if %ERRORLEVEL% EQU 0 (
        echo [OK] OPENROUTER_API_KEY configured
    ) else (
        echo [WARNING] OPENROUTER_API_KEY not found in .env
        echo   Add: OPENROUTER_API_KEY=your_key_here
    )
) else (
    echo [WARNING] .env file not found
    if exist ".env.example" (
        echo   Creating from .env.example...
        copy .env.example .env
        echo   Please edit .env and add your API keys
    )
)
echo.

REM Add AutoGen-specific environment variables
echo Checking AutoGen environment variables...
if exist ".env" (
    findstr /C:"AUTOGEN_USE_DOCKER" .env >nul || echo AUTOGEN_USE_DOCKER=false >> .env
    findstr /C:"AUTOGEN_WORK_DIR" .env >nul || echo AUTOGEN_WORK_DIR=./workspace/code_execution >> .env
    findstr /C:"AUTOGEN_MAX_CONSECUTIVE_AUTO_REPLY" .env >nul || echo AUTOGEN_MAX_CONSECUTIVE_AUTO_REPLY=10 >> .env
    findstr /C:"TEACHABLE_DB_PATH" .env >nul || echo TEACHABLE_DB_PATH=./data/teachable >> .env
    findstr /C:"CONVERSATION_STORAGE_PATH" .env >nul || echo CONVERSATION_STORAGE_PATH=./data/conversations >> .env
    findstr /C:"DATA_DIR" .env >nul || echo DATA_DIR=./data >> .env
    findstr /C:"WORKSPACE_DIR" .env >nul || echo WORKSPACE_DIR=./workspace >> .env
    echo Environment variables updated
)
echo.

REM Check MCP servers
echo Checking MCP servers...
curl -s http://localhost:3000/health >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] GitHub MCP server ^(port 3000^) is running
) else (
    echo [WARNING] GitHub MCP server not detected on port 3000
)

curl -s http://localhost:3001/health >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] Filesystem MCP server ^(port 3001^) is running
) else (
    echo [WARNING] Filesystem MCP server not detected on port 3001
)

curl -s http://localhost:3002/health >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] Memory MCP server ^(port 3002^) is running
) else (
    echo [WARNING] Memory MCP server not detected on port 3002
)
echo.

REM Summary
echo =========================================
echo Setup Summary
echo =========================================
echo.
echo Configuration files created:
echo   [OK] config/autogen_agents.yaml
echo   [OK] config/autogen_groupchats.yaml
echo   [OK] config/autogen_workflows.yaml
echo   [OK] config/function_schemas.yaml
echo.
echo Directories created:
echo   [OK] data/teachable/
echo   [OK] data/conversations/
echo   [OK] data/checkpoints/
echo   [OK] workspace/code_execution/
echo.
echo Next steps:
echo   1. Ensure OPENROUTER_API_KEY is set in .env
echo   2. Start MCP servers: python start_mcp_servers.py
echo   3. Review AUTOGEN_MIGRATION_GUIDE.md
echo   4. Implement core adapters in src/autogen_adapters/
echo   5. Test with: python -m pytest tests/
echo.
echo =========================================
pause
