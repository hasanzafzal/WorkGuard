# WorkGuard Admin Front-End

A modern, responsive React administration console for the **WorkGuard** system, designed following **Apple iOS / macOS Human Interface Guidelines (HIG)** with sleek glassmorphism, SF Pro / Inter typography, refined system colors, and real-time LAN telemetry analytics.

---

## Features & Pages

1. **Workforce Dashboard (`/`)**: 5 core KPI metric cards (Total Employees, Active Employees, Total Sessions, Total Activity Time, Security Alerts), workforce overview table, application usage chart, recent sessions, and AI overview.
2. **Employees Directory (`/employees`)**: Searchable and filterable employee registry with active duration, session count, real-time status chips, and security alert badges.
3. **Employee Details Profile (`/employees/:employeeId`)**: Individual employee analytics, application duration breakdown, session history, associated security incidents, and AI behavioral observations.
4. **Sessions Registry (`/sessions`)**: Full tabular index of work-session packages, duration calculation, event counts, start/end timestamps, and sorting.
5. **Session Details (`/sessions/:sessionId`)**: Deep session inspection with Application Focus Summary, human-readable chronological event timeline (`17:54:13 App.exe Focused`), and collapsible raw JSON drawer.
6. **Security Operations Center (`/security`)**: Severity breakdown (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`), detection events table, and slide-over incident investigation modal.
7. **AI Intelligence Reports (`/reports`)**: Synthesized agentic reports strictly distinguishing **Raw Observed Data** from **AI-Generated Interpretation**, AI confidence %, and evidence session citations.
8. **WorkGuard Copilot (`/chat`)**: Conversational AI telemetry assistant with suggested prompt pills, streaming answers, and clickable RAG source citations.

---

## Directory Structure

```
frontend/
├── index.html              # HTML entrypoint with WorkGuard branding
├── package.json            # Dependencies (React 19, React Router, Lucide, Vite)
├── tsconfig.json           # TypeScript configuration
├── vite.config.ts          # Vite configuration with backend proxy
└── src/
    ├── main.tsx            # Application root
    ├── App.tsx             # React Router routing configuration
    ├── index.css           # Apple macOS / iOS HIG design tokens & glassmorphism
    ├── types/
    │   └── index.ts        # Comprehensive TypeScript interfaces
    ├── services/           # Centralized API service layer (direct FastAPI integration)
    │   ├── api.ts          # Base HTTP client with error handling
    │   ├── dashboardApi.ts # Dashboard queries
    │   ├── employeeApi.ts  # Employee queries
    │   ├── sessionApi.ts   # Session queries
    │   ├── securityApi.ts  # Security event queries
    │   ├── reportApi.ts    # AI agent report queries
    │   └── chatApi.ts      # Copilot chat queries
    ├── components/
    │   ├── common/         # StatCard, StatusBadge, SeverityBadge, LoadingState, etc.
    │   ├── charts/         # ApplicationUsageChart
    │   ├── sessions/       # SessionTimeline
    │   ├── ai/             # AIInsightCard, SourceReference
    │   └── layout/         # Sidebar, TopBar, Layout
    └── pages/
        ├── Dashboard.tsx
        ├── Employees.tsx
        ├── EmployeeDetails.tsx
        ├── Sessions.tsx
        ├── SessionDetails.tsx
        ├── Security.tsx
        ├── Reports.tsx
        └── Chat.tsx
```

---

## Getting Started

### Development
```bash
npm install
npm run dev
```

### Production Build
```bash
npm run build
```
