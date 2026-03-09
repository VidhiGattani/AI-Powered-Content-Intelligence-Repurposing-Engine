@echo off
echo ========================================
echo Redeploying Backend with CORS Fixes
echo ========================================
echo.

echo Step 1: Activating Python virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

echo Step 2: Updating Lambda layer with dependencies...
pip install -r lambda-requirements.txt --target lambda_layer/python --upgrade
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo Step 3: Deploying CDK stacks...
cdk deploy --all --require-approval never
if errorlevel 1 (
    echo ERROR: CDK deployment failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo Deployment Complete!
echo ========================================
echo.
echo The backend has been redeployed with CORS fixes.
echo You can now test the frontend again.
echo.
pause
