# WorkGuard

WorkGuard consists of a Windows employee monitoring client and a local FastAPI
Admin server. Session packages are encrypted with a shared AES-256-GCM key
before the employee client sends them to the server.

## Run locally

Generate one key and use the exact same value for both processes:

```powershell
.\venv\Scripts\python.exe -c "import base64,secrets; print(base64.b64encode(secrets.token_bytes(32)).decode())"
```

Start the Admin server:

```powershell
cd admin-server
$env:WORKGUARD_AES_KEY_BASE64 = "PASTE_THE_GENERATED_KEY"
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Start the employee client from the repository root:

```powershell
$env:WORKGUARD_AES_KEY_BASE64 = "PASTE_THE_SAME_GENERATED_KEY"
.\venv\Scripts\python.exe .\employee-client\main.py
```

The Admin API is available at `http://127.0.0.1:8000/docs`.

## Dependencies

Install each component's dependencies with its corresponding virtual
environment:

```powershell
.\venv\Scripts\python.exe -m pip install -r .\employee-client\requirements.txt
.\admin-server\.venv\Scripts\python.exe -m pip install -r .\admin-server\requirements.txt
```

AI analysis uses Ollama. Install and run the configured local model (default:
`llama3:latest`) before sending sessions if you want AI-generated reports.

The employee client uses the local Ollama model as a narrow Windows background
task blacklist. In `employee-client/config/monitoring_config.json`, set
`whitelist_mode` to `ollama` and choose the desired `ollama_model`. User-facing
and unknown programs are allowed by default; only programs the model identifies
as default Windows background tasks and that match the built-in Windows core
process blacklist are excluded. This prevents model mistakes from blocking
user applications such as WPS. Set `whitelist_mode` to `disabled` to use the
`monitored_applications` list directly.

## Runtime data

Generated sessions, encrypted buffers, reports, vector indexes, and virtual
environments are intentionally ignored by Git. Existing local data was left
unchanged by this cleanup.
