@echo off
REM ===================================================================
REM Sentiment Arena - Manual Trading Session
REM ===================================================================
REM Quick launcher for manual trading sessions
REM ===================================================================

echo.
echo ========================================
echo   Manual Trading Session
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Run the manual trading script
python scripts\manual_trading_session.py %*

echo.
pause
