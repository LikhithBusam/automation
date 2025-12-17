# Helper script to run the application with venv activated

Write-Host "Activating virtual environment..." -ForegroundColor Cyan
& ".\venv\Scripts\Activate.ps1"

Write-Host ""
Write-Host "Running application..." -ForegroundColor Green
python main.py
