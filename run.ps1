# ==============================================================================
# OnCallMemory - Incident Response Agent PowerShell Launcher
# ==============================================================================

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "                     OnCallMemory Agent Launcher                            " -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host ""

# Check for .env file
if (-not (Test-Path ".env")) {
    Write-Host "[!] .env file not found. Copying .env.example to .env..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "[*] Created .env from .env.example" -ForegroundColor Green
    Write-Host ""
}

param (
    [switch]$Seed
)

if ($Seed) {
    Write-Host "[*] Seeding Hindsight memory with sample incidents..." -ForegroundColor Yellow
    python data/seed_memory.py
    Write-Host ""
}

Write-Host "[*] Starting FastAPI Backend on http://127.0.0.1:8000..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python backend/main.py"

Start-Sleep -Seconds 3

Write-Host "[*] Starting Streamlit Frontend on http://localhost:8501..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "streamlit run frontend/app.py"

Write-Host ""
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "[*] OnCallMemory services launched!" -ForegroundColor Green
Write-Host "    - Backend API:       http://127.0.0.1:8000" -ForegroundColor White
Write-Host "    - Interactive Docs:  http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host "    - Frontend UI:       http://localhost:8501" -ForegroundColor White
Write-Host "==============================================================================" -ForegroundColor Cyan
