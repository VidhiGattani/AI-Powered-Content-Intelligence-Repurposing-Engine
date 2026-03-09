@echo off
echo ========================================
echo Content Repurposing Platform - Frontend
echo ========================================
echo.

cd frontend

if not exist "node_modules" (
    echo Installing dependencies...
    call npm install
    echo.
)

if not exist ".env" (
    echo Creating .env file...
    copy .env.example .env
    echo.
    echo IMPORTANT: Edit frontend/.env and set your API Gateway URL
    echo.
    pause
)

echo Starting development server...
echo Frontend will be available at http://localhost:3000
echo.
call npm run dev
