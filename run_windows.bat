@echo off
setlocal
title CashCast launcher
cd /d "%~dp0"
echo ============================================================
echo  CashCast - first-time setup and start (Windows)
echo ============================================================

where python >nul 2>&1
if errorlevel 1 (
  echo Python 3.11 or newer is required. Install it from https://www.python.org/downloads/ and run this file again.
  pause
  exit /b 1
)
where node >nul 2>&1
if errorlevel 1 (
  echo Node.js 22 is required. Install it from https://nodejs.org/ and run this file again.
  pause
  exit /b 1
)

set "PYTHON_ENV=.venv"
if exist ".venv311\Scripts\python.exe" set "PYTHON_ENV=.venv311"
if exist "%PYTHON_ENV%\Scripts\python.exe" (
  "%PYTHON_ENV%\Scripts\python.exe" -c "import sys" >nul 2>&1
  if errorlevel 1 set "PYTHON_ENV=.venv311"
)
if not exist "%PYTHON_ENV%\Scripts\python.exe" (
  echo Creating the Python environment...
  python -m venv "%PYTHON_ENV%"
)
call "%PYTHON_ENV%\Scripts\activate.bat"
echo Installing Python packages (first run takes a few minutes)...
python -m pip install -q -r Backend\requirements-dev.txt
if errorlevel 1 (
  echo Installing the Python packages failed.
  pause
  exit /b 1
)

if not exist ".env" python make_env.py
if not exist "model\cashcast_model.joblib" (
  echo Training the forecast model...
  python model\train.py > nul
)

where docker >nul 2>&1
if errorlevel 1 (
  echo.
  echo Docker was not found. The dashboard works, but Dispatch and alert acknowledgements need MySQL.
  echo Install Docker Desktop and run this file again, or see the README to use your own MySQL.
) else (
  echo Starting MySQL in Docker...
  docker compose up -d mysql
)

if not exist "Frontend\node_modules" (
  echo Installing the frontend packages...
  pushd Frontend
  call npm ci
  popd
)

start "CashCast API (port 8000)" cmd /k "cd /d %~dp0 && call %PYTHON_ENV%\Scripts\activate.bat && python -m uvicorn Backend.main:app --port 8000"
start "CashCast frontend (port 5173)" cmd /k "cd /d %~dp0Frontend && npm run dev"

echo.
echo Waiting for the servers, then opening http://127.0.0.1:5173
timeout /t 12 /nobreak > nul
start "" http://127.0.0.1:5173
echo.
echo Sign in with ops@bankmuscat.demo / demo123 (role: Cash Ops Officer).
echo Close the two server windows to stop CashCast.
pause
