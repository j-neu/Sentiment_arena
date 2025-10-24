@echo off
REM ===================================================================
REM Sentiment Arena - Persistent Backend Runner
REM ===================================================================
REM This script keeps the backend running 24/7 with auto-restart
REM Perfect for 1-week local testing on Windows
REM ===================================================================

setlocal enabledelayedexpansion

echo.
echo ========================================
echo   Sentiment Arena - Backend Runner
echo ========================================
echo.
echo Starting persistent backend service...
echo This will run until you close this window
echo.
echo The backend will:
echo   - Run trading at 8:30 AM CET (pre-market)
echo   - Run trading at 2:00 PM CET (afternoon)
echo   - Update positions every 15 minutes
echo   - Auto-restart if crashes
echo.
echo Press Ctrl+C to stop
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please run: python -m venv venv
    echo Then run: venv\Scripts\activate
    echo Then run: pip install -r requirements.txt
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Check if dependencies are installed
python -c "import fastapi" 2>nul
if errorlevel 1 (
    echo ERROR: Dependencies not installed!
    echo Please run: pip install -r requirements.txt
    pause
    exit /b 1
)

:RESTART_LOOP
    echo [%date% %time%] Starting backend...
    echo.

    REM Run backend with uvicorn
    python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

    REM If we get here, the server stopped
    set EXIT_CODE=%errorlevel%

    echo.
    echo ========================================
    echo Backend stopped with exit code: !EXIT_CODE!
    echo ========================================
    echo.

    REM Check if it was intentional (Ctrl+C) or a crash
    if !EXIT_CODE! EQU 0 (
        echo Server shut down cleanly.
        goto END
    )

    REM Auto-restart after crash
    echo Backend crashed! Auto-restarting in 10 seconds...
    echo Press Ctrl+C now to cancel restart
    timeout /t 10 /nobreak

    echo.
    echo Restarting backend...
    echo.
    goto RESTART_LOOP

:END
echo.
echo Backend service stopped.
pause
