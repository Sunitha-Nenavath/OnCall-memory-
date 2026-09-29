@echo off
:: ==============================================================================
:: OnCallMemory - Incident Response Agent Launcher
:: ==============================================================================
TITLE OnCallMemory Launcher

echo ==============================================================================
echo                      OnCallMemory Agent Launcher                            
echo ==============================================================================
echo.

:: Check for .env file
if not exist .env (
    echo [!] .env file not found. Copying .env.example to .env ...
    copy .env.example .env
    echo [*] Created .env from .env.example
    echo.
)

:: Option to seed memory if requested
if "%1"=="--seed" (
    echo [*] Seeding Hindsight memory with sample incidents...
    python data/seed_memory.py
    echo.
)

echo [*] Starting FastAPI Backend on http://127.0.0.1:8000 ...
start "OnCallMemory - Backend API" cmd /k "python backend/main.py"

echo [*] Waiting 3 seconds for backend to start...
timeout /t 3 /nobreak >nul

echo [*] Starting Streamlit Frontend on http://localhost:8501 ...
start "OnCallMemory - Streamlit Dashboard" cmd /k "streamlit run frontend/app.py"

echo.
echo ==============================================================================
echo [*] OnCallMemory services launched!
echo     - Backend API:  http://127.0.0.1:8000
echo     - Interactive Docs: http://127.0.0.1:8000/docs
echo     - Frontend Dashboard: http://localhost:8501
echo.
echo Leave the terminal windows open while using the application.
echo ==============================================================================
