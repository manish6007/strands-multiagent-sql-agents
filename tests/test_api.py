import pytest
import os
from fastapi.testclient import TestClient

# Ensure test configurations
os.environ["LOCAL_DEV"] = "true"
os.environ["MOCK_LLM"] = "true"
os.environ["REQUIRE_AUTH"] = "false"

from backend.app.main import app

client = TestClient(app)

def test_health_check_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json().get("status") == "healthy"

def test_agents_metadata_endpoint():
    response = client.get("/api/v1/agents")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) > 0

def test_schema_endpoint():
    response = client.get("/api/v1/schema")
    assert response.status_code == 200
    assert "tables" in response.json()
    assert len(response.json()["tables"]) > 0

def test_traces_endpoint():
    response = client.get("/api/v1/traces")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_metrics_endpoint():
    response = client.get("/api/v1/metrics")
    assert response.status_code == 200
    assert "total_calls" in response.json()

def test_query_execution_endpoint():
    payload = {
        "question": "Show revenue growth for the last 12 months",
        "session_id": "test_session_api"
    }
    response = client.post("/api/v1/query", json=payload)
    assert response.status_code == 200
    json_data = response.json()
    assert json_data.get("success") is True
    assert "sql" in json_data
    assert "summary" in json_data
