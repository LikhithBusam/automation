@echo off
echo Installing pyautogen in virtual environment...
echo.

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install pyautogen
echo Installing pyautogen...
pip install "pyautogen<0.3.0"

echo.
echo Installation complete!
echo.
echo Testing import...
python -c "from autogen import AssistantAgent, UserProxyAgent, GroupChatManager; print('SUCCESS: AutoGen imported correctly!')"

pause
