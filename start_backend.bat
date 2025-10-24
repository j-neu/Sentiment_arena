@echo off
echo Starting Sentiment Arena Backend...
echo.

cd "%~dp0"

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Start backend server
echo Backend server starting at http://localhost:8000
echo API docs: http://localhost:8000/docs
echo.

python -m uvicorn backend.main:app --reload --port 8000
