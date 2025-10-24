@echo off
echo ========================================
echo   Sentiment Arena - Starting All Services
echo ========================================
echo.

cd "%~dp0"

echo [1/3] Checking database...
if not exist "sentiment_arena.db" (
    echo Database not found. Initializing...
    call venv\Scripts\activate.bat
    python backend/database/init_db.py
    echo.
)

echo [2/3] Initializing demo data...
call venv\Scripts\activate.bat
python scripts/init_demo_data.py
echo.

echo [3/3] Starting servers...
echo.
echo Starting Backend in new window...
start "Sentiment Arena - Backend" cmd /k start_backend.bat

echo Waiting for backend to start...
timeout /t 5 /nobreak > nul

echo Starting Frontend in new window...
start "Sentiment Arena - Frontend" cmd /k start_frontend.bat

echo.
echo ========================================
echo   Services Starting!
echo ========================================
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo API Docs: http://localhost:8000/docs
echo.
echo Press any key to exit this window...
pause > nul
