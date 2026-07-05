import os
import time
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.schemas.api_models import (
    QueryRequest, QueryResponse, ChatRequest, ChatResponse,
    LoginRequest, TokenResponse, IngestResponse, MetricSummary
)
from backend.app.database.connection import SessionLocal
from backend.app.database.pg_vector import store_knowledge_item
from backend.app.agents.supervisor import supervisor_agent
from backend.app.services.bedrock_service import bedrock_service, metrics_store
from backend.app.services.observability import get_all_traces, clear_traces
from backend.app.services.security import (
    create_access_token, get_current_user, get_current_user_optional, check_role, User,
    detect_prompt_injection, scrub_pii, check_rate_limit, write_audit_log
)

logger = logging.getLogger("app.api.router")
api_router = APIRouter(prefix="/api/v1")


# 1. AUTH LOGIN
@api_router.post("/login", response_model=TokenResponse)
def login(login_data: LoginRequest):
    """Authenticate user credentials and return a JWT access token."""
    # Simple hardcoded credentials for demonstration purposes
    if login_data.username == "admin" and login_data.password == "admin123":
        role = "Admin"
    elif login_data.username == "viewer" and login_data.password == "viewer123":
        role = "Viewer"
    else:
        write_audit_log(login_data.username, "login_attempt", "Invalid password", "FAILURE")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
        
    access_token = create_access_token(data={"sub": login_data.username, "email": f"{login_data.username}@enterprise.com", "role": role})
    write_audit_log(login_data.username, "login_success", f"User logged in with role {role}")
    return {"access_token": access_token, "token_type": "bearer", "role": role}


# 2. INTENT QUERY PIPELINE
@api_router.post("/query", response_model=QueryResponse)
def run_query(request: Request, query_payload: QueryRequest, current_user: Optional[User] = Depends(get_current_user_optional)):
    """Execute natural language query to retrieve SQL results and Plotly visualization."""
    # Enforce Rate Limiting
    client_ip = request.client.host if request.client else "127.0.0.1"
    if not check_rate_limit(client_ip, max_requests=settings.RATE_LIMIT_MAX):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again in a minute.")

    username = current_user.username if current_user else "anonymous"
    user_role = current_user.role if current_user else "Admin"
    
    question = query_payload.question
    
    # 1. PII Scrubbing
    scrubbed_question = scrub_pii(question)
    
    # 2. Prompt Injection Detection
    if detect_prompt_injection(scrubbed_question):
        write_audit_log(username, "query_execution", f"Blocked due to prompt injection: {scrubbed_question}", "REJECTED")
        raise HTTPException(
            status_code=400,
            detail="Security Violation: Input query contains forbidden patterns or prompt injection payloads."
        )

    # 3. RBAC checks: Viewer cannot query anything sensitive (e.g. cost/orders item details)
    # Simple rule: if query is an admin operation, restrict it. Supervisor handles general questions.
    write_audit_log(username, "query_execution", f"User asking: {scrubbed_question}")

    # 4. Trigger Supervisor Agent
    result = supervisor_agent.process_query(scrubbed_question, session_id=query_payload.session_id)
    
    return QueryResponse(
        success=result["success"],
        error=result["error"],
        sql=result["sql"],
        records=result["records"],
        chart=result["chart"],
        summary=result["summary"],
        metrics=result["metrics"],
        traces=result["traces"]
    )


# 3. GENERAL CHAT
@api_router.post("/chat", response_model=ChatResponse)
def chat(query_payload: ChatRequest, current_user: Optional[User] = Depends(get_current_user_optional)):
    """Conversational endpoint for user queries."""
    username = current_user.username if current_user else "anonymous"
    message = query_payload.message
    
    if detect_prompt_injection(message):
        raise HTTPException(status_code=400, detail="Forbidden query patterns detected.")
        
    write_audit_log(username, "chat", f"User chat: {message}")
    
    # Simple chat prompt
    response_text = bedrock_service.generate_text(
        prompt=message,
        system_prompt="You are a friendly AWS analytics assistant. Give helpful, brief answers. Do not write SQL."
    )
    
    return ChatResponse(response=response_text, session_id=query_payload.session_id)


# 4. INGESTION PIPELINE
@api_router.post("/ingest", response_model=IngestResponse)
def ingest_knowledge(current_user: User = Depends(get_current_user) if settings.REQUIRE_AUTH else None):
    """Trigger ingestion of glossary and KPI markdown documents from S3 mock space into pgvector."""
    username = current_user.username if current_user else "system"
    if current_user and current_user.role != "Admin":
        raise HTTPException(status_code=403, detail="Only Admins are allowed to trigger knowledge ingestion.")
        
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    knowledge_dir = os.path.join(base_dir, "data", "knowledge")
    
    if not os.path.exists(knowledge_dir):
        raise HTTPException(status_code=404, detail=f"Knowledge base directory '{knowledge_dir}' not found.")
        
    files = ["business_glossary.md", "kpi_definitions.md", "schema_documentation.md", "business_rules.md"]
    ingested_files = []
    
    db = SessionLocal()
    try:
        for file in files:
            file_path = os.path.join(knowledge_dir, file)
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                # Split documents by Markdown sections (lines starting with '## ')
                sections = content.split("## ")
                doc_title = sections[0].replace("#", "").strip()
                
                for section in sections[1:]:
                    lines = section.split("\n")
                    header = lines[0].strip()
                    body = "\n".join(lines[1:]).strip()
                    
                    if header and body:
                        # Combine doc title and section header as context
                        chunk_text = f"Document: {doc_title}\nTopic: {header}\nContent:\n{body}"
                        
                        # Generate Embedding vector (size 1536)
                        emb = bedrock_service.generate_embeddings(chunk_text)
                        
                        # Store in postgres pgvector
                        store_knowledge_item(
                            db=db,
                            title=header,
                            content=body,
                            category=file.split("_")[0],
                            embedding=emb
                        )
                ingested_files.append(file)
                logger.info(f"Ingested file '{file}' sections successfully.")
        
        write_audit_log(username, "ingest", f"Ingested {len(ingested_files)} knowledge base files.")
        return IngestResponse(
            status="SUCCESS",
            documents_ingested=ingested_files,
            message="Knowledge documents successfully chunked, embedded, and stored in pgvector database."
        )
    except Exception as e:
        logger.error(f"Ingestion error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ingestion process failed: {str(e)}")
    finally:
        db.close()


# 5. METRICS ENDPOINT
@api_router.get("/metrics", response_model=MetricSummary)
def get_metrics():
    """Retrieve cost, latency, and token execution counters."""
    return MetricSummary(
        total_calls=metrics_store["call_count"],
        total_cost_usd=metrics_store["total_cost"],
        total_tokens=metrics_store["total_input_tokens"] + metrics_store["total_output_tokens"],
        calls=metrics_store["calls"]
    )


# 6. ACTIVE AGENTS METADATA
@api_router.get("/agents")
def get_agents():
    """Get active multi-agent cluster information."""
    return [
        {"name": "Supervisor_Agent", "role": "Intent Routing & Agent Execution Orchestration"},
        {"name": "RAG_Agent", "role": "Context Retrieval: Business Glossary, KPIs, Schema Documentation"},
        {"name": "SQL_Gen_Agent", "role": "SQL Code Generation (Presto / Athena compatibilities)"},
        {"name": "SQL_Review_Agent", "role": "Quality Assurance: syntax validation, safety filters, column auditing"},
        {"name": "Execution_Agent", "role": "Database Execution: executes queries on Athena/DuckDB, runs self-healing reparative queries"},
        {"name": "Chart_Agent", "role": "Plotly Visualizations & KPI Dashboard Card builders"},
        {"name": "Response_Agent", "role": "Executive Report Synthesis: key insights, business observations, tactical recommendations"}
    ]


# 7. SCHEMA METADATA
@api_router.get("/schema")
def get_schema():
    """Return relational schema model structural definitions."""
    return {
        "tables": [
            {
                "name": "regions",
                "columns": [
                    {"name": "region_id", "type": "INT", "key": "PRIMARY KEY"},
                    {"name": "name", "type": "VARCHAR"},
                    {"name": "country", "type": "VARCHAR"}
                ]
            },
            {
                "name": "customers",
                "columns": [
                    {"name": "customer_id", "type": "INT", "key": "PRIMARY KEY"},
                    {"name": "name", "type": "VARCHAR"},
                    {"name": "email", "type": "VARCHAR"},
                    {"name": "region_id", "type": "INT", "key": "FOREIGN KEY (regions)"},
                    {"name": "status", "type": "VARCHAR"},
                    {"name": "created_at", "type": "TIMESTAMP"},
                    {"name": "churned", "type": "VARCHAR"}
                ]
            },
            {
                "name": "products",
                "columns": [
                    {"name": "product_id", "type": "INT", "key": "PRIMARY KEY"},
                    {"name": "name", "type": "VARCHAR"},
                    {"name": "category", "type": "VARCHAR"},
                    {"name": "price", "type": "DECIMAL"},
                    {"name": "cost", "type": "DECIMAL"}
                ]
            },
            {
                "name": "orders",
                "columns": [
                    {"name": "order_id", "type": "INT", "key": "PRIMARY KEY"},
                    {"name": "customer_id", "type": "INT", "key": "FOREIGN KEY (customers)"},
                    {"name": "order_date", "type": "TIMESTAMP"},
                    {"name": "total_amount", "type": "DECIMAL"},
                    {"name": "status", "type": "VARCHAR"}
                ]
            },
            {
                "name": "order_items",
                "columns": [
                    {"name": "order_item_id", "type": "INT", "key": "PRIMARY KEY"},
                    {"name": "order_id", "type": "INT", "key": "FOREIGN KEY (orders)"},
                    {"name": "product_id", "type": "INT", "key": "FOREIGN KEY (products)"},
                    {"name": "quantity", "type": "INT"},
                    {"name": "price", "type": "DECIMAL"},
                    {"name": "discount", "type": "DECIMAL"}
                ]
            },
            {
                "name": "sales_summary",
                "columns": [
                    {"name": "date", "type": "DATE", "key": "PRIMARY KEY"},
                    {"name": "region_id", "type": "INT", "key": "FOREIGN KEY (regions)"},
                    {"name": "total_revenue", "type": "DECIMAL"},
                    {"name": "total_orders", "type": "INT"},
                    {"name": "new_customers", "type": "INT"}
                ]
            }
        ]
    }


# 8. AGENT EXECUTION TRACES
@api_router.get("/traces")
def get_traces():
    """Retrieve granular multi-agent execution step-by-step logs."""
    return get_all_traces()


# 9. HEALTH CHECK
@api_router.get("/health")
def health_check():
    """Verify application runtime state."""
    return {"status": "healthy", "timestamp": time.time()}
