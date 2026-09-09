# Quick Start Guide - WorkGuard Admin Server

## Prerequisites
- Python 3.10+
- PostgreSQL 12+
- Ollama (download from https://ollama.ai)

## Installation (5 minutes)

```bash
# 1. Navigate to admin-server directory
cd admin-server

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your actual PostgreSQL credentials and encryption key

# 5. Verify setup
python verify_startup.py

# 6. Run the server
uvicorn main:app --reload
```

Server runs on `http://localhost:8000`

## First Time Setup

### Generate Encryption Key
```bash
python -c "import os; import base64; key = base64.b64encode(os.urandom(32)).decode(); print(f'WORKGUARD_AES_KEY_BASE64={key}')"
```
Copy this value into your `.env` file

### Setup PostgreSQL
```bash
createdb workguard
```
Database schema is created automatically on first server run.

### Start Ollama
```bash
ollama serve
# In another terminal: ollama pull llama2
```

## Testing the Server

### Health Check
```bash
curl http://localhost:8000/health
```

### View API Documentation
Open browser to: `http://localhost:8000/docs`

## Connecting Employee Client

Employee clients send encrypted sessions to:
```
POST http://admin-host:8000/api/v1/sessions
```

The encryption key in the client must match `WORKGUARD_AES_KEY_BASE64` in your .env

## Common Tasks

### View all sessions
```bash
curl http://localhost:8000/api/v1/sessions
```

### View dashboard statistics
```bash
curl http://localhost:8000/api/v1/analytics/dashboard
```

### Get employee list
```bash
curl http://localhost:8000/api/v1/employees
```

### Check current errors
Look in database `reports` table for `errors` field

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Database connection refused | Check PostgreSQL is running and credentials in .env |
| Ollama not available | Start Ollama with `ollama serve` |
| Encryption key mismatch | Verify employee client and admin .env have same AES key |
| FAISS index errors | Delete `vector_store/` directory and it will rebuild |

## Architecture Summary

```
Employee Client (encrypted session)
           ↓
Ingestion (decrypt, validate)
           ↓
PostgreSQL (persist)
           ↓
LangGraph Agent Pipeline
  ├─ Supervisor
  ├─ Session Analysis
  ├─ Knowledge (retrieval)
  ├─ Security (anomaly detection)
  └─ Reporting
           ↓
Reports & Analytics API
```

## Documentation

- Full architecture: [WorkGuard_Admin_Side_Architecture_and_Design.md](WorkGuard_Admin_Side_Architecture_and_Design.md)
- Complete README: [README.md](README.md)
- Code structure: See `agents/`, `tools/`, `database/`, `api/` directories

## Support

For detailed information, see README.md in this directory.
