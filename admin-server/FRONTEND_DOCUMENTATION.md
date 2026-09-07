# WorkGuard Admin Console — Frontend Documentation & Setup Guide

This document provides complete instructions for setting up, configuring, running, and developing the **WorkGuard Admin Frontend** on a new machine using **Visual Studio Code**.

---

## 1. System Architecture Overview

WorkGuard is an offline / LAN-based employee work-session monitoring and AI analytics platform. The frontend is strictly an **Admin-side workstation dashboard** communicating with the local FastAPI backend.

```
[ LAN Employee Workstations ]
             │ (Encrypted AES-256-GCM session packages)
             ▼
[ FastAPI Admin Server ] (Port 8000)
    ├── Ingestion & Decryption
    ├── File Store & PostgreSQL
    ├── LangGraph Agentic Pipeline & Ollama Local LLM
    └── REST API Endpoints (/api/v1/*, /health)
             ▲
             │ (HTTP / JSON via Vite Proxy)
             ▼
[ React Admin Frontend ] (Port 5173)
    ├──  Apple iOS / macOS HIG Glassmorphism UI
    ├── 8 Dedicated Enterprise Analytics Pages
    └── Centralized API Service Layer
```

---

## 2. Prerequisites for a New System

Before running the project on a new system, ensure the following tools are installed:

| Requirement | Minimum Version | Recommended | Purpose |
| :--- | :--- | :--- | :--- |
| **Node.js** | `v18.0.0+` | `v20.x` or `v22.x` (LTS) | JavaScript runtime for Vite and React |
| **npm** | `v9.0.0+` | `v10.x` | Node package manager (included with Node.js) |
| **Python** | `3.10+` | `3.11` or `3.12` | Required to run the local FastAPI backend |
| **VS Code** | Latest | Latest | Code editor |

### Recommended VS Code Extensions
- **ES7+ React/Redux/React-Native snippets** (`dsznajder.es7-react-js-snippets`)
- **Prettier - Code formatter** (`esbenp.prettier-vscode`)
- **Python** (`ms-python.python`)

---

## 3. Fresh Setup Instructions in VS Code (Step-by-Step)

Follow these exact steps when opening the repository on a new computer.

### Step 1: Open Project in VS Code
1. Open VS Code.
2. Select **File > Open Folder...** and select the root directory: `admin-server`.
3. Open the integrated terminal using <kbd>Ctrl</kbd> + <kbd>\`</kbd> (or <kbd>Cmd</kbd> + <kbd>\`</kbd> on macOS).

---

### Step 2: Start the FastAPI Admin Backend

The frontend requires the backend running on `http://127.0.0.1:8000` to serve real telemetry data.

#### On Windows (PowerShell / Command Prompt):
```powershell
# 1. Create Python virtual environment (if not already present)
python -m venv venv

# 2. If PowerShell blocks script execution, run:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# 3. Activate the virtual environment
.\venv\Scripts\Activate.ps1
# (or in CMD: .\venv\Scripts\activate.bat)

# 4. Install Python dependencies
pip install -r requirements.txt

# 5. Start the FastAPI admin server
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

#### On Linux / macOS:
```bash
# 1. Create Python virtual environment (if not already present)
python3 -m venv venv

# 2. Activate the virtual environment
source venv/bin/activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Start the FastAPI admin server
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

> **Verification**: Open `http://localhost:8000/health` in your browser. You should see:  
> `{"status":"online","server":"WorkGuard Admin Server"}`.

---

### Step 3: Setup and Launch the React Frontend

Open a **second terminal tab** in VS Code (<kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>5</kbd> or click the **`+`** icon in the terminal panel).

```bash
# 1. Navigate into the frontend directory
cd frontend

# 2. Install Node.js dependencies
npm install

# 3. Start the Vite development server
npm run dev
```

The terminal will display:
```
  VITE v8.2.2  ready in 180 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: http://<your-lan-ip>:5173/
```

Open **`http://localhost:5173`** in your browser to access the console.

---

## 4. Frontend NPM Commands Reference

Run all commands from inside the `frontend/` directory:

| Command | Description |
| :--- | :--- |
| `npm run dev` | Starts the local development server with Hot Module Replacement (HMR). |
| `npm run build` | Compiles TypeScript (`tsc -b`) and bundles for production into `frontend/dist/`. |
| `npm run preview` | Runs a local web server to preview the production bundle generated in `dist/`. |

---

## 5. Application Structure & Directory Sitemap

```
frontend/
├── index.html              # HTML shell with Inter typography and WorkGuard icon
├── package.json            # Dependencies: React 19, React Router 7, Lucide Icons, Vite
├── tsconfig.json           # Root TypeScript configuration
├── tsconfig.app.json       # Strict application TS rules (verbatimModuleSyntax enabled)
├── vite.config.ts          # Vite configuration with automatic proxy to FastAPI (port 8000)
├── README.md               # Quick-reference overview
└── src/
    ├── main.tsx            # Application entrypoint
    ├── App.tsx             # Declarative React Router route definitions
    ├── index.css           # Complete Apple iOS/macOS HIG design system & tokens
    │
    ├── types/
    │   └── index.ts        # Comprehensive TypeScript interfaces for all data models
    │
    ├── services/           # Centralized API service layer
    │   ├── api.ts          # Base HTTP client with error formatting
    │   ├── dashboardApi.ts # Dashboard queries
    │   ├── employeeApi.ts  # Employee list and profile queries
    │   ├── sessionApi.ts   # Session package registry and details queries
    │   ├── securityApi.ts  # Security anomaly events and incident queries
    │   ├── reportApi.ts    # AI agentic report queries
    │   └── chatApi.ts      # Copilot conversational assistant queries
    │
    ├── components/
    │   ├── layout/         # Shell containers
    │   │   ├── Sidebar.tsx # Translucent glassmorphism navigation sidebar
    │   │   ├── TopBar.tsx  # Header with live sync clock & manual refresh
    │   │   └── Layout.tsx  # Root container with React Router <Outlet />
    │   │
    │   ├── common/         # Standardized UI building blocks
    │   │   ├── StatCard.tsx      # Standard metric KPI card
    │   │   ├── StatusBadge.tsx   # Active / Away / Inactive status chip
    │   │   ├── SeverityBadge.tsx # CRITICAL / HIGH / MEDIUM / LOW incident badge
    │   │   ├── LoadingState.tsx  # Pulse loading indicator
    │   │   ├── ErrorState.tsx    # Retryable error panel
    │   │   └── EmptyState.tsx    # Clean empty-data display
    │   │
    │   ├── charts/
    │   │   └── ApplicationUsageChart.tsx # Horizontal breakdown of app durations
    │   │
    │   ├── sessions/
    │   │   └── SessionTimeline.tsx       # Human-readable event timeline formatter
    │   │
    │   └── ai/
    │       ├── AIInsightCard.tsx         # Strictly separates Observed Data from AI Insights
    │       └── SourceReference.tsx       # Clickable RAG citation pills
    │
    └── pages/              # 8 Dedicated Enterprise Pages
        ├── Dashboard.tsx       # Route: /
        ├── Employees.tsx       # Route: /employees
        ├── EmployeeDetails.tsx # Route: /employees/:employeeId
        ├── Sessions.tsx        # Route: /sessions
        ├── SessionDetails.tsx  # Route: /sessions/:sessionId
        ├── Security.tsx        # Route: /security
        ├── Reports.tsx         # Route: /reports
        └── Chat.tsx            # Route: /chat
```

---

## 6. Page Navigation & Features

| Route | Page | Key Features |
| :--- | :--- | :--- |
| `/` | **Dashboard** | 5 live KPI cards (Total Employees, Active Employees, Total Sessions, Total Activity Time, Security Alerts), workforce overview table, app usage distribution, recent sessions feed, and AI overview banner. |
| `/employees` | **Employees** | Searchable employee registry with real-time status badges, session counts, active hours, and alert counters. |
| `/employees/:employeeId` | **Employee Profile** | Individual employee analytics, application duration chart, session history table, associated security incidents, and AI behavioral observations. |
| `/sessions` | **Sessions Registry** | Full tabular index of work-session packages, duration formatting, event counts, start/end timestamps, sorting, and employee filters. |
| `/sessions/:sessionId` | **Session Details** | Deep session inspection: Application Focus Summary, human-readable chronological event timeline (`17:54:13 App.exe Focused`), and collapsible raw JSON drawer. |
| `/security` | **Security Operations Center** | Incident severity breakdown (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`), detection events table, and slide-over incident investigation modal. |
| `/reports` | **AI Intelligence Reports** | Synthesized agentic reports with strict separation between **Raw Observed Data** and **AI-Generated Interpretation**, AI confidence %, and evidence session citations. |
| `/chat` | **WorkGuard Copilot** | Conversational AI telemetry assistant with suggested prompt pills, streaming answers, and clickable RAG source citations. |

---

## 7. Backend API Contract

The frontend does not communicate directly with databases. All queries pass through the centralized `src/services/` layer to FastAPI:

| Endpoint | Method | Response Structure | Description |
| :--- | :--- | :--- | :--- |
| `/health` | `GET` | `{"status": "online", "server": "WorkGuard Admin Server"}` | Server health & online indicator. |
| `/api/v1/dashboard` | `GET` | `{"kpis": {...}, "workforce": [...], "application_usage": [...], "recent_sessions": [...], "security_alerts": [...]}` | Full high-level dashboard data. |
| `/api/v1/employees` | `GET` | `[{"employee_id": "...", "employee_name": "...", "sessions_count": 5, "total_active_time_seconds": 18000, "status": "Active", "security_alert_count": 0}]` | Workforce directory list. |
| `/api/v1/employees/{id}` | `GET` | `{...Employee, "applications_used": {...}, "session_history": [...], "security_events": [...], "ai_observations": [...]}` | Single employee profile. |
| `/api/v1/sessions` | `GET` | `[{"session_id": "...", "employee_id": "...", "start_time": "...", "end_time": "...", "duration_seconds": 3600, "events_count": 42}]` | Session registry list. |
| `/api/v1/sessions/{id}` | `GET` | `{"session_id": "...", "focus_summary": {...}, "events": [...], "raw_envelope": {...}}` | Detailed session package with timeline. |
| `/api/v1/security/events`| `GET` | `[{"event_id": "...", "severity": "HIGH", "detection_type": "...", "evidence": "...", "related_session_id": "..."}]` | Incident alert events. |
| `/api/v1/reports` | `GET` | `[{"report_id": "...", "overall_assessment": "...", "key_observations": [...], "ai_confidence": 88, "evidence_sessions": [...]}]` | Agentic reports. |
| `/api/v1/chat` | `POST` | `{"response": "...", "sources": ["sess_123"]}` | Copilot natural language query. |

---

## 8. Troubleshooting & Common Issues

### 1. Backend Shows "Connection Refused" or "Offline" Badge
- **Cause**: The FastAPI server is not running on port 8000.
- **Fix**: Open a terminal in `admin-server` and run `python -m uvicorn main:app --host 0.0.0.0 --port 8000`.

### 2. PowerShell Error: "Execution of scripts is disabled on this system"
- **Cause**: Windows default PowerShell execution policy prevents running virtual environment scripts.
- **Fix**: Run in PowerShell:
  ```powershell
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  ```
  Then re-run `.\venv\Scripts\Activate.ps1`.

### 3. Port 5173 or Port 8000 Is Already in Use
- **Cause**: Another process is occupying the port.
- **Fix**:
  - **Linux / macOS**: `kill -9 $(lsof -t -i:5173)` or `kill -9 $(lsof -t -i:8000)`
  - **Windows**: `netstat -ano | findstr :5173` then `taskkill /PID <PID> /F`

### 4. `TypeError: Cannot read properties of undefined`
- **Cause**: An empty session or non-standard session event payload was ingested.
- **Fix**: The frontend handles null/undefined arrays via fallback guards (`Array.isArray(session.events) ? session.events : []`). Verify backend session files in `verified_sessions/` are valid JSON.

### 5. AI Chatbot Returns Fallback Synthesis
- **Cause**: Local Ollama service is not running or the model (`llama3:latest`) is not pulled.
- **Fix**: Install Ollama (`https://ollama.com`), run `ollama run llama3:latest`, and restart the FastAPI server. If Ollama is absent, the backend safely uses deterministic LangGraph heuristic summaries.

---

## 9. Design System & Theme Customization

WorkGuard uses **CSS Variables** defined in `src/index.css` matching Apple Human Interface Guidelines:

- **Accent Colors**: Apple Blue (`#007AFF`), Apple Green (`#34C759`), Apple Indigo (`#5856D6`), Apple Orange (`#FF9500`), Apple Red (`#FF3B30`).
- **Surface Elevation**: Frosted glass panels with `backdrop-filter: blur(28px) saturate(180%)`.
- **Themes**: Switch between Dark and Light mode via the sidebar toggle. Theme selection is stored in `localStorage` under `workguard-theme`.
