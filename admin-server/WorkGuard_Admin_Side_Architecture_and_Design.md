# WorkGuard — Admin-Side Architecture & System Design

## 1. Purpose

This document focuses exclusively on the **Admin PC / Admin-side system** of WorkGuard.

The employee-side monitoring, buffering, encryption, and LAN-transfer implementation is intentionally omitted from this version.

The Admin side is responsible for:

- Receiving encrypted session packages.
- Decrypting and validating incoming data.
- Persisting authoritative data in PostgreSQL.
- Creating and maintaining embeddings.
- Maintaining the FAISS vector index.
- Orchestrating LangGraph agents.
- Running the local Ollama LLM.
- Producing analysis, security findings, and reports.
- Serving the Admin Dashboard and chatbot.

---

# 2. Admin-Side Architecture

```text
                 ┌─────────────────────────────┐
                 │       Employee PCs          │
                 │  Encrypted session payloads  │
                 └──────────────┬──────────────┘
                                │
                                │ LAN
                                ▼
                 ┌─────────────────────────────┐
                 │      Admin Ingestion        │
                 │                             │
                 │ Receive → Decrypt → Validate│
                 │ → Deduplicate → Store       │
                 └──────────────┬──────────────┘
                                │
                                ▼
                 ┌─────────────────────────────┐
                 │         PostgreSQL          │
                 │      System of Record       │
                 └──────────────┬──────────────┘
                                │
                    ┌───────────┴──────────┐
                    ▼                      |
          ┌──────────────────┐             |
          │ Embedding /      │             |
          │ Indexing Pipeline│             |
          └────────┬─────────┘             |
                   ▼                       |
              ┌─────────┐                  │
              │  FAISS  │                  │
              │ Vectors │                  │
              └────┬────┘                  │
                   │                       │
                   ▼                       ▼
          ┌─────────────────────────────────────┐
          │             LangGraph               │
          │           Agent Orchestration       │
          │                                     │
          │ Supervisor / Router                 │
          │      │                              │
          │      ├── Knowledge Agent            │
          │      ├── Session Analysis Agent     │
          │      ├── Security Agent             │
          │      └── Reporting Agent            │
          └────────────────┬────────────────────┘
                           │
                           ▼
                    ┌────────────┐
                    │   Ollama   │
                    │ Local LLM  │
                    └─────┬──────┘
                          │
                          ▼
                ┌─────────────────────┐
                │ Admin Dashboard /   │
                │ Admin Chatbot       │
                └─────────────────────┘
```

---

# 3. Admin Ingestion Layer

The Admin PC receives encrypted session packages over the LAN.

The ingestion pipeline is:

```text
Receive
  ↓
Authenticate / identify source
  ↓
Decrypt AES-256-GCM
  ↓
Validate payload/schema
  ↓
Deduplicate using session_id
  ↓
Insert into PostgreSQL
  ↓
Trigger / queue indexing
```

The ingestion layer should not send raw, unvalidated data directly to the agents.

---

# 4. PostgreSQL — System of Record

PostgreSQL is the authoritative structured data store on the Admin PC.

The recommended model is relational rather than storing the entire session only as one JSON blob.

A raw JSONB copy can optionally be retained for traceability/audit purposes.

## Core relationships

```text
employees
    │
    └──────< sessions
                │
                └──────< events

sessions
    │
    └──────< application_usage

sessions
    │
    └──────< security_findings

sessions
    │
    └──────< analysis_results
```

---

# 5. Recommended PostgreSQL Schema

## 5.1 employees

Stores employee/device identity.

Suggested fields:

```text
employee_id       PK
employee_name
device_id
created_at
updated_at
```

---

## 5.2 sessions

Stores one finalized work session.

Suggested fields:

```text
session_id        PK
employee_id       FK
start_time
end_time
duration_seconds
created_at
schema_version
raw_payload       JSONB   (optional backup/audit copy)
```

---

## 5.3 events

Stores individual activity events.

Suggested fields:

```text
event_id          PK
session_id        FK
employee_id       FK
event_type
source
timestamp
pid               nullable
process_name      nullable
file_path         nullable
event_data        JSONB
```

The schema supports the project's active monitoring sources such as:

- pywin32 application activity
- psutil process activity
- watchdog filesystem activity

Git events are intentionally excluded because Git monitoring was removed from the project scope.

---

## 5.4 application_usage

Stores calculated application focus information.

Suggested fields:

```text
id                PK
session_id        FK
process_name
pid
duration_seconds
```

Example:

```text
sess_123
Code.exe
13.0
```

---

## 5.5 security_findings

Stores Security Agent results.

Suggested fields:

```text
finding_id
session_id
employee_id
risk_level
risk_score
finding_type
description
requires_review
created_at
```

This separates AI-generated security findings from the raw monitoring events.

---

## 5.6 analysis_results

Stores structured Session Analysis Agent output.

Suggested fields:

```text
analysis_id
session_id
employee_id
summary
primary_application
activity_pattern
findings JSONB
created_at
```

---

# 6. Embedding / Indexing Pipeline

FAISS is **not** the system of record.

PostgreSQL remains authoritative.

The indexing pipeline creates a semantic retrieval representation from selected PostgreSQL data.

```text
PostgreSQL
     ↓
Select indexable records
     ↓
Build text representation
     ↓
Embedding model
     ↓
Vector
     ↓
FAISS
```

The text representation can combine information such as:

```text
Employee
Session
Time
Duration
Applications
Application usage
Relevant process activity
Relevant file activity
Session analysis
Security findings
```

The exact embedding content should be finalized according to retrieval requirements.

---

# 7. FAISS

FAISS is the vector similarity search layer.

It is used for **semantic retrieval**, not as a replacement for PostgreSQL.

## PostgreSQL is used for

```text
How many sessions did employee X have?
How long did employee X work?
What was the total duration?
Which applications were used?
When did a specific event occur?
```

## FAISS is used for

```text
Find activity similar to this activity.
Find historically similar sessions.
Find sessions with similar behavioral patterns.
Retrieve semantically relevant context for an agent.
```

FAISS can therefore be exposed as a retrieval tool to whichever agent needs semantic search.

It is not exclusively owned by the Knowledge Agent.

---

# 8. LangGraph Agent Layer

LangGraph orchestrates the multi-agent workflow.

The current agent architecture contains:

1. Supervisor / Router
2. Knowledge Agent
3. Session Analysis Agent
4. Security Agent
5. Reporting Agent

The Supervisor determines which specialized agent(s) should handle an administrator's request.

---

# 9. Supervisor / Router

The Supervisor is the orchestration component.

Responsibilities:

- Understand the administrator's request.
- Determine which agent is appropriate.
- Route the task.
- Allow multiple agents to participate when necessary.
- Combine workflow outputs.
- Pass results to the Reporting Agent when a human-readable response is required.

Examples:

```text
"What happened in Omar's session?"
             ↓
        Supervisor
             ↓
   Session Analysis Agent
```

```text
"Was anything suspicious?"
             ↓
        Supervisor
             ↓
      Security Agent
```

```text
"Generate Omar's weekly report."
             ↓
        Supervisor
             ↓
Session Analysis + Security
             ↓
      Reporting Agent
```

---

# 10. Knowledge Agent

## Purpose

The Knowledge Agent answers factual/contextual questions using information already stored by the system.

It is primarily retrieval-oriented.

## Tools/data sources

It can use:

- PostgreSQL
- FAISS
- Ollama

## Typical flow

```text
Admin question
      ↓
Knowledge Agent
      │
      ├── PostgreSQL query
      │
      └── FAISS semantic retrieval
              ↓
        Relevant context
              ↓
           Ollama
              ↓
        Grounded answer
```

### Example

Question:

> "What applications does Omar commonly use for development?"

The Knowledge Agent retrieves relevant historical activity and generates an answer grounded in that retrieved data.

### Important distinction

The Knowledge Agent is **not the RAG pipeline itself**.

The indexing pipeline puts information into FAISS.

The Knowledge Agent consumes retrieval results from FAISS when it needs them.

---

# 11. Session Analysis Agent

## Purpose

The Session Analysis Agent determines what happened during a session or activity period.

Its central question is:

> "What happened?"

## Inputs

Potential inputs:

- PostgreSQL session records
- PostgreSQL event records
- Application usage
- Process activity
- File activity
- Relevant historical context from FAISS

## Example output

```json
{
  "session_id": "sess_xxxxx",
  "duration_seconds": 5400,
  "primary_application": "Code.exe",
  "application_usage": {},
  "activity_pattern": "development-oriented",
  "findings": []
}
```

The agent should produce structured findings rather than only free-form text.

---

# 12. Security Agent

## Purpose

The Security Agent determines whether observed activity contains suspicious patterns, anomalies, or configured policy violations.

Its central question is:

> "Is anything concerning?"

It is important to distinguish this from the underlying cybersecurity infrastructure.

## Security infrastructure handles

- Encryption
- Authentication
- Secure transport
- Payload validation
- Access control

## Security Agent handles

- Activity anomaly analysis
- Pattern analysis
- Security-related correlations
- Risk assessment
- Policy-oriented reasoning

---

# 13. Security Agent Inputs

The Security Agent can use:

```text
PostgreSQL
    +
FAISS historical context
    +
psutil process information
    +
watchdog file activity
    +
pywin32 application activity
```

This enables activity correlation.

Example:

```text
Unusual process
      +
Unusual file activity
      +
Unusual application activity
      ↓
Security Agent
      ↓
Potential anomaly
```

---

# 14. Security Agent — Rules + AI

The Security Agent should not rely entirely on the LLM to decide whether activity is malicious.

Recommended design:

```text
Stored activity
     ↓
Deterministic security rules
     ↓
Potential security signals
     +
Historical retrieval
     ↓
Security Agent
     ↓
Ollama
     ↓
Risk assessment
```

This gives the LLM contextual reasoning while deterministic rules provide predictable security signals.

---

# 15. Security Agent Output

Prefer structured output.

Example:

```json
{
  "session_id": "sess_xxxxx",
  "risk_level": "LOW",
  "risk_score": 12,
  "findings": [],
  "anomalies": [],
  "policy_violations": [],
  "reasoning_summary": "Activity appears consistent with normal activity.",
  "requires_admin_review": false
}
```

Suspicious example:

```json
{
  "session_id": "sess_xxxxx",
  "risk_level": "HIGH",
  "risk_score": 87,
  "findings": [
    {
      "type": "unusual_process_activity",
      "severity": "HIGH",
      "description": "Previously uncommon process observed alongside unusual file activity."
    }
  ],
  "anomalies": [],
  "policy_violations": [],
  "reasoning_summary": "Activity differs significantly from historical patterns.",
  "requires_admin_review": true
}
```

The exact scoring model should be defined during implementation rather than allowing arbitrary LLM-generated scores.

---

# 16. Reporting Agent

## Purpose

The Reporting Agent converts structured information into administrator-friendly reports and summaries.

Its central question is:

> "How should we communicate the results?"

It should generally consume outputs from other agents rather than independently re-analyzing all raw events.

## Inputs

Potential inputs:

- Session Analysis Agent output
- Security Agent output
- Knowledge Agent results
- PostgreSQL metrics

## Example

Input:

```text
Session duration: 90 minutes
Primary application: Code.exe
Risk: LOW
Security findings: None
```

Output:

```text
Omar's 90-minute session was primarily focused on
development activity, with Code.exe being the primary
application. No significant security concerns were
identified during the session.
```

---

# 17. Why Session Analysis and Reporting Are Separate

They answer different questions.

### Session Analysis

> "What does the activity indicate?"

### Reporting

> "How should we present those findings?"

This separation prevents duplicate analysis and keeps the multi-agent architecture modular.

---

# 18. Why Knowledge and Session Analysis Are Separate

The Knowledge Agent is retrieval-oriented.

The Session Analysis Agent is analysis-oriented.

### Knowledge Agent

```text
"What applications has Omar used recently?"
```

### Session Analysis Agent

```text
"What happened during Omar's 10:00–11:00 session?"
```

The Knowledge Agent retrieves relevant knowledge.

The Session Analysis Agent interprets a session/activity period.

---

# 19. Admin Dashboard Data Strategy

The dashboard should **not depend exclusively on LLM-generated text**.

For numerical/structured information, query PostgreSQL directly.

Example:

```text
PostgreSQL
 ├── Total sessions
 ├── Total activity duration
 ├── Application usage
 ├── File events
 └── Security findings
```

The agents provide:

```text
 ├── Explanations
 ├── Summaries
 ├── Context
 ├── Security reasoning
 └── Natural-language responses
```

This prevents the LLM from becoming the authoritative source for simple numerical data.

---

# 20. Dashboard Architecture

```text
                  PostgreSQL
                 /                          /                    Structured data       Agent results
              │                    │
              ▼                    ▼
        Dashboard API        LangGraph/Ollama
              │                    │
              └─────────┬──────────┘
                        ▼
                 Admin Dashboard
                        │
                        ▼
                     Chatbot
```

The dashboard can display:

- Employee list
- Session history
- Session duration
- Application usage
- Activity timelines
- Security alerts
- Risk levels
- AI-generated summaries
- Reports
- Natural-language chatbot responses

---

# 21. Admin Chatbot

The chatbot is the administrator's natural-language interface.

It should not directly manipulate the database.

Instead:

```text
Admin
  ↓
Chatbot
  ↓
LangGraph Supervisor
  ↓
Appropriate Agent(s)
  ↓
PostgreSQL / FAISS / tools
  ↓
Ollama
  ↓
Response
```

Example:

> "Show me employees who had high-risk sessions this week."

Supervisor → Security/Knowledge tools → PostgreSQL → result.

Example:

> "Explain why Omar's session was flagged."

Supervisor → Security Agent → PostgreSQL + historical retrieval → explanation.

---

# 22. Ollama

Ollama provides the local LLM runtime on the Admin PC.

The LLM is used for:

- Natural-language reasoning
- Contextual analysis
- Security explanation
- Report generation
- Chatbot responses

The agents are responsible for retrieving and structuring the correct data before passing appropriate context to the LLM.

---

# 23. End-to-End Admin Flow

```text
Encrypted LAN payload
        ↓
Admin Ingestion
        ↓
AES-256-GCM Decryption
        ↓
Payload Validation
        ↓
PostgreSQL
        ↓
 ┌─────────────────────┐
 │ Structured Queries  │
 └──────────┬──────────┘
            │
            ├──────────────► Dashboard API
            │
            ▼
     Embedding Pipeline
            ↓
      Embedding Model
            ↓
          FAISS
            ↓
     Semantic Retrieval
            │
            ▼
     LangGraph Agents
            │
      ┌─────┼─────┐
      ▼     ▼     ▼
 Knowledge Analysis Security
      │     │     │
      └─────┼─────┘
            ▼
      Reporting Agent
            ↓
          Ollama
            ↓
   Dashboard / Chatbot
```

---

# 24. Example: Security Query

Admin asks:

> "Was there any suspicious activity in Omar's sessions today?"

Flow:

```text
Admin
  ↓
LangGraph Supervisor
  ↓
Security Agent
  ↓
PostgreSQL
  ├── today's sessions
  ├── events
  ├── process activity
  └── file activity
  ↓
FAISS
  └── historically similar activity
  ↓
Security rules
  ↓
Ollama
  ↓
Structured risk assessment
  ↓
Reporting Agent
  ↓
Admin Dashboard
```

---

# 25. Example: Weekly Report

Admin asks:

> "Generate Omar's weekly report."

Flow:

```text
Admin
  ↓
Supervisor
  ↓
Session Analysis Agent
  ↓
PostgreSQL + FAISS
  ↓
Session/activity findings
  ↓
Security Agent
  ↓
Security findings
  ↓
Reporting Agent
  ↓
Ollama
  ↓
Weekly report
```

---

# 26. Data Authority Model

The system should maintain a strict hierarchy:

```text
PostgreSQL
    │
    │ authoritative structured data
    ▼
Embedding / Indexing Pipeline
    │
    ▼
FAISS
    │
    │ semantic retrieval
    ▼
LangGraph Agents
    │
    │ reasoning/orchestration
    ▼
Ollama
    │
    │ natural-language generation
    ▼
Dashboard / Chatbot
```

Therefore:

- PostgreSQL is the source of truth.
- FAISS is a retrieval index.
- Agents reason over retrieved/queried data.
- Ollama generates language and contextual reasoning.
- The dashboard presents authoritative metrics plus AI-generated insights.

---

# 27. Admin-Side Component Responsibilities

| Component | Responsibility |
|---|---|
| Admin Ingestion | Receive, decrypt, validate and ingest employee payloads |
| PostgreSQL | Authoritative structured storage |
| Embedding Pipeline | Convert selected records into vectors |
| FAISS | Semantic similarity retrieval |
| LangGraph | Agent orchestration |
| Supervisor | Route requests/workflows |
| Knowledge Agent | Retrieve and answer factual/contextual questions |
| Session Analysis Agent | Analyze activity/session behavior |
| Security Agent | Detect/analyze suspicious patterns |
| Reporting Agent | Turn findings into reports/summaries |
| Ollama | Local LLM inference |
| Dashboard API | Serve structured and AI-derived data |
| Dashboard | Visual presentation |
| Chatbot | Natural-language admin interface |

---

# 28. Recommended Admin-Side Project Structure

The Admin-side implementation should be organized into clear layers so that ingestion, storage, retrieval, agent orchestration, LLM inference, and presentation remain separate. The recommended structure is:

```text
workguard-admin/
│
├── main.py
├── requirements.txt
├── .env
├── README.md
│
├── config/
│   └── config.yaml
│
├── database/
│   ├── connection.py
│   ├── models.py
│   ├── repositories.py
│   └── schema.sql
│
├── ingestion/
│   ├── receiver.py
│   ├── decryptor.py
│   └── session_ingestor.py
│
├── embeddings/
│   ├── embedder.py
│   ├── faiss_store.py
│   └── indexer.py
│
├── agents/
│   ├── graph.py
│   ├── state.py
│   ├── supervisor_agent.py
│   ├── knowledge_agent.py
│   ├── session_analysis_agent.py
│   ├── security_agent.py
│   └── reporting_agent.py
│
├── tools/
│   ├── postgres_tools.py
│   ├── faiss_tools.py
│   ├── session_tools.py
│   └── security_tools.py
│
├── llm/
│   └── ollama_client.py
│
├── api/
│   ├── app.py
│   ├── schemas.py
│   └── routes/
│       ├── sessions.py
│       ├── employees.py
│       ├── analytics.py
│       ├── security.py
│       └── chat.py
│
├── dashboard/
│   └── ...
│
├── vector_store/
│   └── faiss/
│
├── logs/
│
└── tests/
    ├── test_database.py
    ├── test_ingestion.py
    ├── test_embeddings.py
    ├── test_agents.py
    └── test_api.py
```

## 28.1 Responsibility of Each Layer

| Directory | Responsibility |
|---|---|
| `database/` | PostgreSQL connection, schema, models, repositories and database access |
| `ingestion/` | Receive encrypted packages, decrypt AES-256-GCM payloads, validate and ingest sessions |
| `embeddings/` | Build embeddings and maintain the FAISS index |
| `agents/` | LangGraph state, graph and the five agent roles |
| `tools/` | Controlled tools through which agents access PostgreSQL, FAISS and security/session data |
| `llm/` | Ollama/Qwen3 local LLM integration |
| `api/` | Backend API for structured dashboard data and AI functionality |
| `dashboard/` | Admin-facing visual interface |
| `vector_store/` | Persistent FAISS index files and associated vector metadata |
| `tests/` | Component and integration tests |

### Architectural rule

Agents should **not directly access PostgreSQL or FAISS implementation details**. They should use controlled tools from `tools/`. This keeps permissions, queries, retrieval logic and validation centralized and makes the LangGraph workflow easier to test and secure.

The resulting Admin-side flow is:

```text
Encrypted Session
       ↓
ingestion/
       ↓
Decrypt + Validate
       ↓
database/ → PostgreSQL
       │
       ├──────────────→ api/ → Dashboard
       │
       ↓
embeddings/ → FAISS
       │
       ↓
tools/
       │
       ↓
agents/ → LangGraph
       │
       ├── Knowledge Agent
       ├── Session Analysis Agent
       ├── Security Agent
       └── Reporting Agent
       │
       ↓
llm/ → Ollama / Qwen3
       │
       ↓
Dashboard / Chatbot
```

---

# 28. Recommended Admin-Side Implementation Order

Build the Admin side in layers:

```text
1. PostgreSQL schema
        ↓
2. Admin ingestion endpoint
        ↓
3. AES-256-GCM decryption
        ↓
4. Payload validation
        ↓
5. PostgreSQL persistence
        ↓
6. Database query/service layer
        ↓
7. Embedding pipeline
        ↓
8. FAISS index
        ↓
9. FAISS retrieval tool
        ↓
10. LangGraph Supervisor
        ↓
11. Knowledge Agent
        ↓
12. Session Analysis Agent
        ↓
13. Security Agent
        ↓
14. Reporting Agent
        ↓
15. Ollama integration
        ↓
16. Dashboard API
        ↓
17. Admin Dashboard
        ↓
18. Chatbot
        ↓
19. End-to-end testing
```

---

# 29. Key Architectural Principle

> **PostgreSQL is authoritative; FAISS is for semantic retrieval; LangGraph orchestrates agents; Ollama performs local LLM inference; agents interpret/reason over retrieved data; the dashboard presents both authoritative structured data and AI-generated insights.**

The LLM should never be treated as the database.

The vector database/index should never replace PostgreSQL.

The agents should not blindly analyze raw data without retrieval/query tools.

The dashboard should not use an LLM to calculate basic authoritative metrics that PostgreSQL can provide directly.
