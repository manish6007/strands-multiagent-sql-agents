# Agent Design, RAG & Troubleshooting Guide

This guide details the internal execution mechanics of the Strands Agents system, pgvector RAG searches, and troubleshooting steps.

---

## 1. Strands Agent Orchestration Flow
Our multi-agent system uses **Strands Agents** to manage discrete agent boundaries. The `SupervisorAgent` acts as a coordinator:

```
User Question
  │
  ▼
Supervisor Agent
  ├───> [1] RAG Agent (Retrieves metadata via pgvector tools)
  ├───> [2] SQL Gen Agent (Transforms NL + context to Presto/Athena SQL)
  ├───> [3] SQL Review Agent (Checks security, table structure, and parameters)
  │         ├── APPROVED ──> Continues to execution
  │         └── REJECTED ──> Halts execution and returns validation error
  ├───> [4] Execution Agent (Executes SQL on DuckDB/Athena client)
  │         └── Failure ──> LLM Query Repair ──> Retries Execution
  ├───> [5] Chart Agent (Infers format and generates Plotly visualization configs)
  └───> [6] Response Agent (Synthesizes executive summary and action items)
```

---

## 2. RAG (Retrieval-Augmented Generation) Ingestion & Retrieval
The RAG pipeline enhances the SQL generator's schema awareness:

1. **Ingestion**: The `/ingest` API scans markdown glossary documents in `data/knowledge/`, splits them by sections (`##`), converts text chunks into 1536-dimensional vectors using `amazon.titan-embed-text-v1`, and stores them in PostgreSQL `knowledge_base` table with pgvector index.
2. **Retrieval**: When a query is asked, the RAG Agent uses the `semantic_search_glossary` MCP tool. It computes the embedding of the user's question, performs a cosine similarity query (`<=>`), and injects matching definitions (e.g., "Active Customer definition") directly into the SQL Gen prompt.

---

## 3. SQL Self-Healing / Repair Loop
If the database engine rejects a query (due to Presto dialect discrepancies, missing aggregates, or typos), the `ExecutionAgent` captures the error stack:

```
[SQL Execution Failed] ──> Log Error Stack ──> Prompt repair specialist LLM ──> [Self-Correct Query] ──> Retry
```

---

## 4. Troubleshooting Guide

### Issue: "Database write failed, writing to memory fallback"
- **Cause**: Postgres container is not running, pgvector extension is missing, or migrations haven't run.
- **Resolution**: Ensure `docker compose up` completes. Verify database container logs: `docker logs analytics_postgres`. The backend automatically falls back to in-memory similarity searching so the application remains functional.

### Issue: "Access Denied / Forbidden"
- **Cause**: The backend has `REQUIRE_AUTH=true` set, but you are querying without a valid JWT token.
- **Resolution**: Toggle "Enable Security JWT Authentication" in Streamlit sidebar, enter `admin`/`admin123` credentials, and click **Authenticate Token**.

### Issue: "boto3 ClientError: AccessDeniedException when calling Bedrock"
- **Cause**: The container does not have permission to access Bedrock models or your AWS credentials file is missing.
- **Resolution**: Ensure your AWS credentials at `~/.aws/` are valid and the models (Sonnet / Titan) are enabled in your target region (e.g. `us-east-1`). You can toggle `MOCK_LLM=true` in `.env` or in docker compose to test everything fully offline.
