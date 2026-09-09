# PostgreSQL → Processing → Retrieval → Agents Roadmap

## Current Position

The **Employee PCs → Ingestion → Decryption → Validation → Deduplication → PostgreSQL System of Record** portion is already completed.

**Do not change that completed architecture.**

The next development work starts **after PostgreSQL**.

```text
Employee PCs
     │
     ▼
Admin Ingestion
     │
     ├─ Receive
     ├─ Decrypt
     ├─ Validate
     ├─ Deduplicate
     └─ Store
           │
           ▼
     ┌──────────────┐
     │ PostgreSQL   │
     │    ✅ DONE   │
     └──────┬───────┘
            │
            │  ← START HERE
            ▼
       Processing
            │
       ┌────┴─────┐
       ▼          ▼
    Analytics   Embedding
                  │
                  ▼
                FAISS
                  │
                  ▼
              LangGraph
                  │
          ┌───────┼────────┐
          ▼       ▼        ▼
       Knowledge Session Security
          │       │        │
          └───────┼────────┘
                  ▼
               Ollama
                  │
                  ▼
          Admin Dashboard
```

---

# Phase 1 — PostgreSQL → Processing Pipeline

This is the **immediate next step**.

Do **not** start with LangGraph or agents yet.

Build a background processing pipeline that reads data from PostgreSQL and prepares it for analytics and semantic search.

```text
PostgreSQL
    ↓
Read new/changed records
    ↓
Normalize
    ↓
Transform into analysis documents
    ↓
Generate embeddings
    ↓
Store vectors in FAISS
```

## Example

A PostgreSQL session record:

```json
{
  "employee_id": 123,
  "timestamp": "2026-09-03T08:20:00",
  "application": "VS Code",
  "duration": 1800,
  "window_title": "project/backend"
}
```

can become a searchable document:

```text
Employee 123 used VS Code for 30 minutes.
Window: project/backend.
Time: September 3, 2026 08:20.
```

Then:

```text
Document
   ↓
Embedding Model
   ↓
Vector
   ↓
FAISS
```

## Important Architecture Rule

Keep the original structured record in PostgreSQL.

**FAISS must contain the search representation, not replace PostgreSQL.**

PostgreSQL remains the **System of Record**.

---

# Phase 2 — Embedding Generation and FAISS

The processing pipeline should produce embeddings for documents that need semantic retrieval.

```text
PostgreSQL
     │
     ▼
Processing Pipeline
     │
     ▼
Normalized Document
     │
     ▼
Embedding Model
     │
     ▼
Vector
     │
     ▼
FAISS Index
```

FAISS is responsible for efficient vector similarity search.

PostgreSQL remains responsible for authoritative structured data.

A useful conceptual separation is:

| Component | Responsibility |
|---|---|
| PostgreSQL | Structured source of truth |
| Processing Pipeline | Normalize and transform data |
| Embedding Model | Convert documents to vectors |
| FAISS | Semantic/vector search |

---

# Phase 3 — Create the Retrieval Layer

Before building agents, create a clean retrieval API.

Example interfaces:

```text
search_knowledge(query)
search_employee_activity(employee_id, query)
search_sessions(employee_id, date_range)
```

The architecture becomes:

```text
                 ┌──────────────┐
                 │ PostgreSQL   │
                 └──────┬───────┘
                        │
             ┌──────────┴──────────┐
             ▼                     ▼
       Structured Query       Vector Search
             │                     │
             ▼                     ▼
       Exact Results             FAISS
             │                     │
             └──────────┬──────────┘
                        ▼
                  Agent Tools
```

This creates a clean interface between the data layer and future LangGraph agents.

---

# Phase 4 — Build the Ollama Integration

Once retrieval works, connect the local LLM through Ollama.

Basic flow:

```text
Your Backend
     │
     ▼
   Ollama
     │
     ▼
 Local LLM
```

Do **not** send raw PostgreSQL tables directly to Ollama.

Instead:

```text
PostgreSQL
     ↓
Agent Tool
     ↓
Relevant Data
     ↓
Prompt / Context
     ↓
Ollama
     ↓
Response
```

## Example

Question:

```text
"What did employee 123 do yesterday?"
```

Suppose PostgreSQL contains:

```text
43 session records
12 application records
8 website records
```

The application should first retrieve and structure the relevant information.

For example:

```text
Employee: 123
Date: 2026-09-02

Application usage:
VS Code: 4h 12m
Chrome: 2h 31m
Terminal: 1h 05m

Website activity:
...
```

Then this focused context is sent to Ollama.

```text
Relevant Data
     ↓
Prompt / Context
     ↓
Ollama
     ↓
Natural Language Answer
```

---

# Phase 5 — Build ONE Agent

Do not build all agents at once.

Start with a single **Session Analysis Agent**.

```text
             LangGraph
                 │
                 ▼
        Session Analysis Agent
                 │
          ┌──────┴──────┐
          ▼             ▼
     PostgreSQL       FAISS
          │             │
          └──────┬──────┘
                 ▼
               Ollama
```

## Initial Agent Tools

Give the Session Analysis Agent a small, controlled set of tools:

```text
get_employee()
get_sessions()
get_application_usage()
get_website_activity()
get_daily_summary()
```

## Initial Test Questions

Test the agent with questions such as:

```text
"How much time did employee X spend on VS Code?"

"What applications did X use yesterday?"

"Give me a summary of X's activity."

"Show me X's activity between 9 AM and 12 PM."
```

The goal is to make this agent **reliable before adding more agents**.

---

# Phase 6 — Add the Supervisor

Only after the Session Analysis Agent works reliably should the system introduce a supervisor.

```text
                    User
                     │
                     ▼
                Supervisor
                     │
       ┌─────────────┼─────────────┐
       ▼             ▼             ▼
   Knowledge      Session       Security
     Agent         Agent          Agent
       │             │             │
       └─────────────┼─────────────┘
                     ▼
                 Reporting
                   Agent
```

## Supervisor Responsibility

The Supervisor should primarily:

> Understand the request and decide which agent should handle it.

Example routing:

| Admin Question | Agent |
|---|---|
| "What does our policy say?" | Knowledge |
| "What did Alice do yesterday?" | Session |
| "Was Alice's activity suspicious?" | Security |
| "Generate weekly activity report" | Reporting |

The Supervisor should route requests rather than performing every task itself.

---

# Phase 7 — Add Security Intelligence

Security should be introduced after the Session Agent.

The key architecture is:

```text
PostgreSQL
    ↓
Security Rules / Analytics
    ↓
Suspicious Events
    ↓
Security Agent
    ↓
Ollama
```

## Important Principle

**Detection → Rules / Analytics**

**Explanation → LLM**

Do not make the LLM the sole source of security decisions.

## Example

A rule engine detects:

```text
Large transfer detected
        +
After-hours activity
        +
Unknown application
        ↓
Security Agent
        ↓
Ollama
        ↓
"These events warrant investigation because..."
```

The deterministic/rule-based layer identifies potentially suspicious events.

The LLM explains and contextualizes those events for administrators.

---

# Phase 8 — Reporting Agent

After the core agents are stable, build the Reporting Agent.

```text
PostgreSQL
     │
     ├── Daily statistics
     ├── Application statistics
     ├── Session statistics
     └── Security events
             │
             ▼
       Reporting Agent
             │
             ▼
           Ollama
             │
             ▼
       Human-readable Report
```

The Reporting Agent should consume structured statistics and relevant retrieved information rather than arbitrary raw database tables.

---

# Phase 9 — Admin Chat API

Once the retrieval and agent layers are stable, expose them through an Admin Chat API.

Conceptually:

```text
Admin Dashboard
       │
       ▼
  Admin Chat API
       │
       ▼
   LangGraph
       │
       ├── Knowledge Agent
       ├── Session Agent
       ├── Security Agent
       └── Reporting Agent
       │
       ▼
     Ollama
```

The API becomes the controlled entry point between the dashboard and the agent system.

---

# Phase 10 — Dashboard Integration

The Admin Dashboard should be the presentation layer.

```text
Admin Dashboard
       │
       ▼
Admin Chat API
       │
       ▼
LangGraph
       │
       ▼
Agents
       │
       ├── PostgreSQL
       ├── FAISS
       └── Ollama
```

The dashboard should not directly access FAISS, PostgreSQL internals, or the LLM.

Use backend APIs and controlled tools instead.

---

# Phase 11 — Evaluation and Testing

Before production deployment, test every layer independently and together.

## Processing Tests

Verify:

- New PostgreSQL records are detected.
- Changed records are reprocessed correctly.
- Normalization is deterministic.
- Documents are generated correctly.
- Duplicate vectors are not unnecessarily created.
- Processing failures can be retried.

## Retrieval Tests

Verify:

- Structured queries return exact results.
- Vector searches return relevant documents.
- Employee/date filters are enforced.
- PostgreSQL remains authoritative.

## Agent Tests

Verify questions such as:

```text
"What did employee X do yesterday?"

"How much time did X spend in VS Code?"

"What applications did X use?"

"Show X's activity between 9 AM and 12 PM."
```

Also test invalid, ambiguous, and unauthorized requests.

---

# Phase 12 — Security and Access Controls

Security controls should be implemented before production deployment.

Important areas include:

- Authentication
- Authorization
- Employee-level access controls
- Admin roles
- Tool-level permissions
- Audit logging
- Secure API boundaries
- PostgreSQL access controls
- FAISS access through controlled backend services
- Prompt/context isolation
- Protection against unauthorized data retrieval

The LLM should only receive data that the requesting administrator is authorized to access.

---

# Phase 13 — Production Deployment

After testing and security controls are complete:

```text
Employee PCs
     ↓
Admin Ingestion
     ↓
PostgreSQL
     ↓
Processing Workers
     ├── Analytics
     └── Embeddings
             ↓
           FAISS
             ↓
        Retrieval Layer
             ↓
          LangGraph
             ↓
           Agents
             ↓
           Ollama
             ↓
       Admin Chat API
             ↓
        Admin Dashboard
```

Production concerns include:

- Background workers
- Job queues
- Retry handling
- Monitoring
- Logging
- Metrics
- Database backups
- FAISS index persistence
- Model management
- Resource limits
- Failure recovery
- Deployment automation

---

# Recommended Development Order

Since PostgreSQL is already complete:

```text
✅ 1. Employee → Ingestion
✅ 2. Decryption
✅ 3. Validation
✅ 4. Deduplication
✅ 5. PostgreSQL System of Record

⬇ NEXT

🔨 6. PostgreSQL → Processing Pipeline
🔨 7. Embedding Generation
🔨 8. FAISS Index
🔨 9. Retrieval API
🔨 10. Ollama Integration

⬇ THEN

🔨 11. Session Analysis Agent
🔨 12. LangGraph Supervisor
🔨 13. Knowledge Agent
🔨 14. Security Agent
🔨 15. Reporting Agent

⬇ FINALLY

🔨 16. Admin Chat API
🔨 17. Dashboard Integration
🔨 18. Evaluation / Testing
🔨 19. Security / Access Controls
🔨 20. Production Deployment
```

---

# Final Architecture

One important architectural change is to make the PostgreSQL-to-LangGraph relationship explicit.

Instead of:

```text
PostgreSQL ────────┐
                   ▼
                LangGraph
```

Use:

```text
                 PostgreSQL
                     │
             ┌───────┴────────┐
             │                │
             ▼                ▼
       Structured Tools   Embedding Pipeline
             │                │
             │                ▼
             │              FAISS
             │                │
             └───────┬────────┘
                     ▼
                 LangGraph
                     │
                     ▼
                  Ollama
```

This creates a clear separation of responsibilities:

| Layer | Responsibility |
|---|---|
| **PostgreSQL** | Authoritative structured data |
| **Processing** | Normalize and transform data |
| **FAISS** | Semantic/vector retrieval |
| **Tools** | Controlled access to data |
| **LangGraph** | Workflow orchestration |
| **Agents** | Domain-specific behavior |
| **Ollama** | Local LLM reasoning/generation |
| **Admin Chat API** | Backend interface |
| **Dashboard** | Presentation |

---

# Immediate Next Deliverable

The next concrete engineering task should be:

> **Design and implement the PostgreSQL → Processing → Embedding → FAISS pipeline, including its database/vector schema.**

That pipeline is the bridge between the completed ingestion architecture and the future LangGraph agent system.

**Do not start with agents. Build the data-processing and retrieval foundation first.**
