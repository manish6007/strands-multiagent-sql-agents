import pytest
import os

# Set environment variables for testing
os.environ["LOCAL_DEV"] = "true"
os.environ["MOCK_LLM"] = "true"

from backend.app.agents.supervisor import supervisor_agent
from backend.app.agents.rag import RAGAgent
from backend.app.agents.sql_gen import SQLGenAgent
from backend.app.agents.sql_review import SQLReviewAgent
from backend.app.agents.execution import ExecutionAgent
from backend.app.agents.chart import ChartAgent
from backend.app.agents.response import ResponseAgent

def test_rag_agent_retrieve_context():
    agent = RAGAgent()
    context = agent.retrieve_context("Show active customers")
    assert context is not None
    assert "Active Customer" in context or "active" in context.lower()

def test_sql_gen_agent():
    agent = SQLGenAgent()
    sql = agent.generate_sql("Show customers growth", "mock context")
    assert sql is not None
    assert "SELECT" in sql

def test_sql_review_agent():
    agent = SQLReviewAgent()
    review = agent.review_sql("SELECT * FROM customers")
    assert review is not None
    assert review.get("status") in ["APPROVED", "REJECTED"]

def test_execution_agent():
    agent = ExecutionAgent()
    # Query should execute on local DuckDB mock layer
    res = agent.execute_query("SELECT * FROM regions LIMIT 2")
    assert res is not None
    assert res.get("success") is True
    assert len(res.get("records", [])) > 0

def test_chart_agent():
    agent = ChartAgent()
    records = [{"region_id": 1, "revenue": 5000.0}, {"region_id": 2, "revenue": 7500.0}]
    chart_res = agent.generate_chart(records)
    assert chart_res is not None
    assert chart_res.get("chart_type") in ["Bar", "Pie", "Line", "KPI Card"]
    assert "fig_json" in chart_res

def test_response_agent():
    agent = ResponseAgent()
    records = [{"customer_id": 1001, "name": "John Doe 1001"}]
    summary = agent.generate_final_response("Who is top customer?", "SELECT * FROM customers", records)
    assert summary is not None
    assert "Executive Summary" in summary

def test_supervisor_agent_pipeline():
    result = supervisor_agent.process_query("Show me top 10 customers by revenue")
    assert result is not None
    assert result.get("success") is True
    assert result.get("sql") is not None
    assert len(result.get("records", [])) > 0
    assert "metrics" in result
