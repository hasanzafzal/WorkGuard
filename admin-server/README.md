# WorkGuard Admin Server

The WorkGuard Admin Server is the central hub for session ingestion, decryption, storage, and AI-powered analysis. It receives encrypted session packages from employee clients, validates and persists them, and runs a multi-agent AI pipeline to generate structured reports and security assessments.

## Architecture Overview

The Admin Server follows the architecture specified in [WorkGuard_Admin_Side_Architecture_and_Design.md](WorkGuard_Admin_Side_Architecture_and_Design.md).

### Key Components

1. **Ingestion Layer** (`ingestion/`)
   - Receives encrypted session packages over HTTP
   - Validates AES-256-GCM authentication
   - Decrypts payloads using shared encryption key

2. **Database Layer** (`database/`)
   - PostgreSQL as authoritative system of record
   - Tables: employees, sessions, session_events, reports, vector_metadata
   - Repository pattern for data access

3. **Tools Layer** (`tools/`)
   - `postgres_tools.py` - Controlled access to PostgreSQL data
   - `faiss_tools.py` - FAISS vector store integration for semantic retrieval

4. **Embeddings Layer** (`embeddings/`)
   - Sentence-transformers for text-to-vector conversion
   - Builds semantic embeddings from session data
   - FAISS index for similarity search

5. **LLM Layer** (`llm/`)
   - Ollama integration for local LLM inference
   - Configurable model selection
   - Used by agents for reasoning and analysis

6. **Agent Layer** (`agents/`)
   - **Supervisor** - Routes requests and validates sessions
   - **Session Analysis Agent** - Analyzes what happened during a session
   - **Knowledge Agent** - Retrieves historical context and factual data
   - **Security Agent** - Detects suspicious patterns and anomalies
   - **Reporting Agent** - Converts findings into administrator-friendly reports
   - **Workflow** - LangGraph orchestration of the agent pipeline

7. **API Layer** (`api/`)
   - RESTful endpoints for dashboard data
   - Session queries, employee lists, reports, analytics
   - Built with FastAPI

## Setup and Installation

### Prerequisites

- Python 3.10+
- PostgreSQL 12+
- Ollama (for local LLM inference)

### Installation Steps

1. **Create and activate virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your actual configuration
   ```

   Key configuration:
   - `DB_*`: PostgreSQL connection details
   - `WORKGUARD_AES_KEY_BASE64`: Shared encryption key (must match employee client key)
   - `WORKGUARD_OLLAMA_*`: Ollama LLM configuration

4. **Generate encryption key** (if needed):
   ```bash
   python -c "import os; import base64; print(base64.b64encode(os.urandom(32)).decode())"
   ```

5. **Initialize database:**
   The database schema is automatically initialized on first server startup.

### Running the Server

```bash
# Development mode with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Production mode
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app
```

Server will be available at `http://localhost:8000`

### Health Check

```bash
curl http://localhost:8000/health
```

## API Endpoints

### Session Ingestion

```
POST /api/v1/sessions
```
Receive and validate an encrypted employee session package.

**Request:**
```json
{
  "session_id": "sess_xxxxx",
  "employee_id": "emp_xxxxx",
  "created_at": "2024-01-01T12:00:00Z",
  "encryption": {
    "algorithm": "AES-256-GCM",
    "nonce": "base64-encoded-nonce",
    "ciphertext": "base64-encoded-ciphertext"
  }
}
```

**Response:**
```json
{
  "status": "received",
  "session_id": "sess_xxxxx",
  "received_at": "2024-01-01T12:00:05Z"
}
```

### Sessions

```
GET /api/v1/sessions              # List sessions with pagination
GET /api/v1/sessions/{session_id} # Get specific session
```

### Employees

```
GET /api/v1/employees  # List employees
```

### Reports

```
GET /api/v1/reports              # List reports
GET /api/v1/reports/{session_id} # Get report for session
```

### Analytics

```
GET /api/v1/analytics/dashboard  # Dashboard statistics
```

## Agent Workflow

When a session is received:

1. **Supervisor** validates the session and initializes the workflow
2. **Session Analysis Agent** determines what happened during the session
3. **Knowledge Agent** retrieves historical context and employee data
4. **Security Agent** analyzes for suspicious patterns and anomalies
5. **Reporting Agent** converts findings into a structured report
6. Report is persisted to PostgreSQL and session is marked as processed

Each agent updates the workflow state with its findings, which are combined into a final comprehensive report.

## Database Schema

### employees
- `employee_id` (PK): Unique employee identifier
- `employee_name`: Human-readable name
- `first_seen`: When first activity was recorded
- `last_seen`: When most recent activity occurred

### sessions
- `session_id` (PK): Unique session identifier
- `employee_id` (FK): Reference to employee
- `start_time`, `end_time`: Session duration
- `duration_seconds`: Total seconds
- `focus_summary`: JSONB of application usage
- `metadata`: JSONB for session metadata
- `status`: 'received', 'processed', or 'failed'

### session_events
- `event_id` (PK): Unique event identifier
- `session_id` (FK): Reference to session
- `event_type`: Type of monitoring event
- `source`: Where the event came from
- `timestamp`: When the event occurred
- `data`: JSONB event data

### reports
- `report_id` (PK): Auto-increment
- `session_id` (FK): Reference to session
- `employee_id` (FK): Reference to employee
- `summary`: Analysis summary text
- `productivity_assessment`: productivity assessment
- `security`: JSONB security findings
- `errors`: JSONB list of processing errors

### vector_metadata
- `vector_id` (PK): FAISS vector ID
- `session_id` (FK): Reference to session
- `embedding_model`: Which model was used
- `indexed_at`: When the vector was created

## FAISS Vector Store

Sessions are embedded and indexed in FAISS for semantic similarity search. The vector store enables:

- Finding historically similar sessions
- Retrieving context for anomaly analysis
- Semantic chatbot queries

Vector store location: `vector_store/`

## Configuration Reference

| Variable | Purpose | Example |
|----------|---------|---------|
| `DB_HOST` | PostgreSQL host | `localhost` |
| `DB_PORT` | PostgreSQL port | `5432` |
| `DB_NAME` | Database name | `workguard` |
| `DB_USER` | PostgreSQL user | `postgres` |
| `DB_PASSWORD` | PostgreSQL password | (set in .env) |
| `WORKGUARD_AES_KEY_BASE64` | Encryption key (Base64) | (generate and set in .env) |
| `WORKGUARD_OLLAMA_URL` | Ollama server URL | `http://localhost:11434` |
| `WORKGUARD_OLLAMA_MODEL` | Model to use | `llama2:latest` |
| `WORKGUARD_EMBEDDING_MODEL` | Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |

## Troubleshooting

### Database Connection Issues
- Verify PostgreSQL is running: `psql -U postgres -h localhost`
- Check credentials in `.env`
- Ensure database exists: `createdb workguard`

### Ollama Not Available
- Verify Ollama is running: `curl http://localhost:11434/api/tags`
- Check `WORKGUARD_OLLAMA_URL` configuration
- Pull model if missing: `ollama pull llama2`

### Encryption Key Mismatch
- Ensure the key in `.env` matches the key configured on employee clients
- Key must be a Base64-encoded 32-byte value

### FAISS Index Errors
- Vector store files in `vector_store/` may be corrupted
- Delete `vector_store/` directory and rebuild: `POST /api/v1/indexing/rebuild`

## Development Notes

### Module Structure
- All imports use relative imports from the admin-server root
- `agents/` contains the LangGraph nodes
- `tools/` provides controlled access to data sources
- `database/` handles all PostgreSQL interactions
- `ingestion/` handles encryption/decryption

### Adding New Agents
1. Create agent function in `agents/`
2. Import and add to workflow in `agents/workflow.py`
3. Update state routing logic as needed

### Testing
Run tests from the admin-server directory:
```bash
pytest tests/
```

## Performance Considerations

- Session embedding happens asynchronously on background thread
- FAISS index is memory-mapped for efficiency
- PostgreSQL indexes are created on common query fields
- API responses are paginated (default 50 items)

## Security

- All session data in transit is encrypted with AES-256-GCM
- Payload authentication prevents tampering
- PostgreSQL should be restricted to local connections or private network
- Ollama LLM access should be restricted to admin network
- Never commit `.env` file or actual encryption keys to version control

## License

WorkGuard Admin Server is part of the WorkGuard project.
