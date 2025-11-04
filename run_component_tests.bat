@echo off
echo ========================================
echo  SENTIMENT ARENA - COMPONENT TESTING
echo ========================================
echo.
echo This script will test each component individually
echo to identify issues before running full trading.
echo.
echo Press any key to start testing...
pause >nul

cd /d "%~dp0"

echo.
echo Starting comprehensive component tests...
echo.

python scripts/comprehensive_component_test.py

echo.
echo Component testing complete.
echo.
echo If tests failed, please fix the issues before running full trading.
echo.
pause