# Dev-mode: local mocks and run instructions

This folder contains a minimal mock server to emulate Bedrock (Claude), embeddings, and Transcribe so you can run the project locally without incurring Bedrock/Transcribe charges.

Quick steps (Windows PowerShell):

1. Create and activate a virtual environment:
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

2. Install dev requirements and start the mock server:
```powershell
pip install -r dev\requirements-dev.txt
uvicorn dev.mock_server:app --reload --port 8080
```

3. Configure environment variables for dev (example):
```powershell
$env:BEDROCK_ENDPOINT = "http://localhost:8080/bedrock/invoke"
$env:EMBEDDING_ENDPOINT = "http://localhost:8080/embeddings"
$env:TRANSCRIBE_ENDPOINT = "http://localhost:8080/transcribe"
```

4. Run the frontend locally:
```powershell
cd frontend
npm install
npm run dev
```

Notes:
- The mock server returns deterministic pseudo-embeddings (length 1536) and simple mocked text responses.
- Replace mock endpoints with real AWS endpoints before production deploy.
- If you prefer LocalStack for more complete AWS emulation, install and configure LocalStack/Docker instead.
