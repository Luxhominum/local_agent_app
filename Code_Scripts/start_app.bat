@echo off
title Local AI Automation Hub
cd /d "%~dp0"
echo ==============================================
echo   Starting Local AI Automation Agent Web Hub
echo   Powered by Ollama (100% Local)
echo ==============================================
echo.

:: Ensure Ollama is running
powershell -Command "if (!(Get-Process ollama -ErrorAction SilentlyContinue)) { Start-Process '%LOCALAPPDATA%\Programs\Ollama\ollama.exe' -ArgumentList 'serve' -WindowStyle Hidden; Start-Sleep -Seconds 2 }"

:: Open default browser
start http://localhost:8000

:: Start FastAPI server
python -m uvicorn app:app --host 127.0.0.1 --port 8000
pause
