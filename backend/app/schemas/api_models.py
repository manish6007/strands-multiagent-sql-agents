from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class QueryRequest(BaseModel):
    question: str = Field(..., example="Show monthly revenue growth for the last 12 months")
    session_id: str = Field(default="default_session", example="session_123")

class QueryResponse(BaseModel):
    success: bool
    error: Optional[str] = None
    sql: str
    records: List[Dict[str, Any]]
    chart: Dict[str, Any]
    summary: str
    metrics: Dict[str, Any]
    traces: List[Dict[str, Any]]

class ChatRequest(BaseModel):
    message: str = Field(..., example="Hi, what datasets do we have?")
    session_id: str = Field(default="default_session", example="session_123")

class ChatResponse(BaseModel):
    response: str
    session_id: str

class LoginRequest(BaseModel):
    username: str = Field(..., example="admin")
    password: str = Field(..., example="admin123")

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str

class IngestResponse(BaseModel):
    status: str
    documents_ingested: List[str]
    message: str

class MetricSummary(BaseModel):
    total_calls: int
    total_cost_usd: float
    total_tokens: int
    calls: List[Dict[str, Any]]
