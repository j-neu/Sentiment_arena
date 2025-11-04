@echo off
echo ========================================
echo  SENTIMENT ARENA - QUICK DIAGNOSTICS
echo ========================================
echo.
echo This script will quickly check for common issues:
echo - API configuration
echo - Database connectivity  
echo - Market data availability
echo - Model configuration
echo.
echo Press any key to start diagnostics...
pause >nul

cd /d "%~dp0"

echo.
echo Running quick diagnostics...
echo.

python scripts/quick_diagnostics.py

echo.
echo Diagnostics complete.
echo.
pause