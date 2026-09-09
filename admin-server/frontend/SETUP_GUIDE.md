# WorkGuard Admin Frontend — VS Code Quickstart & Setup Guide

This guide contains step-by-step commands to run the WorkGuard Admin Frontend in **Visual Studio Code** on a fresh system.

For full architectural documentation, refer to the root [FRONTEND_DOCUMENTATION.md](../FRONTEND_DOCUMENTATION.md).

---

## 1. Prerequisites
- **Node.js** v18+ or v20+ (LTS recommended)
- **Python** 3.10+ (for the local FastAPI backend)
- **VS Code**

---

## 2. Quickstart Execution Commands

### Terminal 1: Launch FastAPI Backend (from `admin-server/` root)

#### Windows (PowerShell):
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

#### macOS / Linux:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

### Terminal 2: Launch React Frontend (from `frontend/` directory)

```bash
cd frontend
npm install
npm run dev
```

The console will open at **`http://localhost:5173`**.

---

## 3. Production Build Command

```bash
cd frontend
npm run build
```
Build output is generated into `frontend/dist/`.
