@echo off
REM Start the local mock server and provide environment variable tips
echo Activating virtualenv and starting mock server on port 8080
if exist .venv\Scripts\Activate.ps1 (
  powershell -NoProfile -ExecutionPolicy Bypass -Command ". .venv\Scripts\Activate.ps1; pip install -r dev\requirements-dev.txt; uvicorn dev.mock_server:app --reload --port 8080"
) else (
  echo No virtualenv found. Create one with: python -m venv .venv
  echo Then re-run this script.
)
