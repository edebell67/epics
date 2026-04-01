@echo off
echo Starting Strategy Warehouse Marketing Engine - Admin Panel...

echo Starting Backend...
start "Marketing Backend" cmd /c "cd backend && python -m uvicorn src.main:app --host 0.0.0.0 --port 8000"

echo Starting Frontend...
start "Marketing Frontend" cmd /c "cd frontend && npm run dev"

echo Access the Admin Panel at http://localhost:3000/admin
echo Access the Backend API documentation at http://localhost:8000/docs
pause
