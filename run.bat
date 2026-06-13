@echo off
REM ============================================================
REM  Scam Guardian - start everything in ONE process
REM  (FastAPI API + Telegram bot + autonomous email monitor).
REM  Double-click this file, or run it from a terminal.
REM  It auto-restarts if the process crashes.
REM  To stop: press Ctrl+C, then answer Y to "Terminate batch job".
REM ============================================================

setlocal enableextensions
cd /d "%~dp0backend"

set "PYTHONUTF8=1"
set "PYTHONPATH=%CD%"
set "PY=.venv\Scripts\python.exe"

if not exist "%PY%" (
  echo [ERROR] Virtual environment not found at backend\.venv
  echo.
  echo Create it once with:
  echo     cd backend
  echo     python -m venv .venv
  echo     .venv\Scripts\python -m pip install -e .
  echo.
  pause
  exit /b 1
)

if not exist ".env" (
  echo [WARNING] backend\.env not found.
  echo Copy .env.example to .env and fill in your keys first.
  echo.
)

:loop
echo.
echo ============================================================
echo   Scam Guardian is starting...   (press Ctrl+C to stop)
echo   API docs:  http://localhost:8000/docs
echo ============================================================
echo.
"%PY%" -m app
echo.
echo [Scam Guardian stopped or crashed - restarting in 5 seconds.]
echo [Press Ctrl+C now to quit completely.]
timeout /t 5 >nul
goto loop
