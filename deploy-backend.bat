@echo off
echo ========================================
echo Content Repurposing Platform - Backend
echo ========================================
echo.

echo Activating virtual environment...
call .venv\Scripts\activate

echo.
echo Installing/updating dependencies...
pip install -r requirements.txt

echo.
echo Running tests...
pytest tests/ -v

echo.
echo Deploying infrastructure to AWS...
cdk deploy --all --app "python infrastructure/app.py"

echo.
echo ========================================
echo Deployment Complete!
echo ========================================
echo.
echo IMPORTANT: Copy the API Gateway URL from the output above
echo and update it in frontend/.env file
echo.
pause
