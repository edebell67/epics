@echo off
setlocal enabledelayedexpansion

echo [SETUP] Starting Strategy Warehouse Marketing Engine setup...

:: Create directories
if not exist logs mkdir logs
if not exist data mkdir data
if not exist verification mkdir verification

:: Environment file
if not exist .env (
    if exist .env.example (
        echo [SETUP] Creating .env from .env.example...
        copy .env.example .env
    ) else (
        echo [WARN] .env.example not found. Please create .env manually.
    )
)

:: Python Virtual Environment
if not exist venv (
    echo [SETUP] Creating Python virtual environment...
    python -m venv venv
)

echo [SETUP] Installing backend dependencies...
call venv\Scripts\activate
pip install -r solution/backend/requirements.txt
echo [SETUP] Initializing local database schema and seed data...
pushd solution\backend
call ..\..\venv\Scripts\python -m src.scripts.init_database
popd

:: Frontend (if directory exists)
if exist solution\frontend (
    echo [SETUP] Installing frontend dependencies...
    cd solution\frontend
    call npm install
    cd ..\..
)

echo [SETUP] Setup complete!
echo [SETUP] To start the backend: call venv\Scripts\activate ^&^& cd solution\backend ^&^& uvicorn src.main:app --reload
pause
