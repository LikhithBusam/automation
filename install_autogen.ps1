# Install pyautogen in virtual environment
Write-Host "Installing pyautogen in virtual environment..." -ForegroundColor Cyan
Write-Host ""

# Activate virtual environment
& ".\venv\Scripts\Activate.ps1"

# Install pyautogen (version < 0.3 for compatibility)
Write-Host "Installing pyautogen..." -ForegroundColor Yellow
pip install "pyautogen<0.3.0"

Write-Host ""
Write-Host "Installation complete!" -ForegroundColor Green
Write-Host ""

# Test import
Write-Host "Testing import..." -ForegroundColor Yellow
python -c "from autogen import AssistantAgent, UserProxyAgent, GroupChatManager; print('SUCCESS: AutoGen imported correctly!')"

Write-Host ""
Write-Host "You can now run: python main.py" -ForegroundColor Green
