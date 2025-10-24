@echo off
echo Starting Sentiment Arena Frontend...
echo.

cd "%~dp0frontend"

echo Frontend starting at http://localhost:3000
echo.

npm run dev
