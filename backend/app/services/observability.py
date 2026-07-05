import os
import time
import logging
import json
from typing import Optional, Dict, Any
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource

# Setup basic JSON-friendly console logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger("app.services.observability")

# Initialize OpenTelemetry
trace.set_tracer_provider(
    TracerProvider(
        resource=Resource.create({"service.name": "text-to-sql-analytics-agent"})
    )
)
tracer = trace.get_tracer("analytics-agent-tracer")

# Try to register standard span processors
try:
    # Console span exporter for local debugging
    processor = BatchSpanProcessor(ConsoleSpanExporter())
    trace.get_tracer_provider().add_span_processor(processor)
    logger.info("OpenTelemetry Tracer successfully initialized.")
except Exception as e:
    logger.warning(f"Could not initialize OpenTelemetry span processor: {e}")

# Langfuse Configuration
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "http://localhost:3000")

langfuse_client = None
if LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY:
    try:
        from langfuse import Langfuse
        langfuse_client = Langfuse(
            public_key=LANGFUSE_PUBLIC_KEY,
            secret_key=LANGFUSE_SECRET_KEY,
            host=LANGFUSE_HOST
        )
        logger.info(f"Langfuse client initialized (Host: {LANGFUSE_HOST})")
    except Exception as e:
        logger.warning(f"Could not import or initialize Langfuse: {e}")
else:
    logger.info("Langfuse keys not configured, running without external Langfuse tracing.")

# In-memory execution trace storage for dashboard retrieval
agent_traces = []

def record_agent_trace(
    session_id: str,
    agent_name: str,
    step_name: str,
    input_payload: Any,
    output_payload: Any,
    latency_ms: float,
    status: str = "SUCCESS",
    tokens: int = 0,
    cost: float = 0.0
):
    """Save granular execution trace for an agent step."""
    trace_entry = {
        "timestamp": time.time(),
        "session_id": session_id,
        "agent": agent_name,
        "step": step_name,
        "input": str(input_payload),
        "output": str(output_payload),
        "latency_ms": round(latency_ms, 2),
        "status": status,
        "tokens": tokens,
        "cost": round(cost, 6)
    }
    agent_traces.append(trace_entry)
    
    # Also log in structured JSON format for scraping / container monitoring
    logger.info(f"AGENT_TRACE: {json.dumps(trace_entry)}")
    
    # Record to external trace system if available
    if langfuse_client:
        try:
            langfuse_client.trace(
                name=agent_name,
                user_id=session_id,
                metadata={"step": step_name, "status": status, "cost": cost, "latency": latency_ms},
                input=str(input_payload),
                output=str(output_payload)
            )
        except Exception as ex:
            logger.warning(f"Error logging trace to Langfuse: {ex}")

def get_traces_by_session(session_id: str) -> list[dict]:
    """Retrieve execution history for a particular chat session."""
    return [t for t in agent_traces if t["session_id"] == session_id]

def get_all_traces() -> list[dict]:
    """Retrieve all execution traces."""
    return agent_traces

def clear_traces():
    """Clear memory traces."""
    agent_traces.clear()
