#!/bin/bash

echo "[SETUP] Starting Strategy Warehouse Marketing Engine setup..."

# Create directories
mkdir -p logs data verification

# Environment file
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo "[SETUP] Creating .env from .env.example..."
        cp .env.example .env
    else
        echo "[WARN] .env.example not found. Please create .env manually."
    fi
fi

# Python Virtual Environment
if [ ! -d "venv" ]; then
    echo "[SETUP] Creating Python virtual environment..."
    python3 -m venv venv
fi

echo "[SETUP] Installing backend dependencies..."
source venv/bin/activate
pip install -r solution/backend/requirements.txt
echo "[SETUP] Initializing local database schema and seed data..."
(
    cd solution/backend
    ../../venv/bin/python -m src.scripts.init_database
)

# Frontend (if directory exists)
if [ -d "solution/frontend" ]; then
    echo "[SETUP] Installing frontend dependencies..."
    cd solution/frontend
    npm install
    cd ../..
fi

echo "[SETUP] Setup complete!"
echo "[SETUP] To start the backend: source venv/bin/activate && cd solution/backend && uvicorn src.main:app --reload"
