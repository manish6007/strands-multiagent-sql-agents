import logging
import json
import pandas as pd
from backend.app.agents.base import BaseAgent
from backend.app.mcp.client import execute_sql_query
from backend.app.services.bedrock_service import bedrock_service

logger = logging.getLogger("app.agents.execution")

EXECUTION_SYSTEM_PROMPT = """You are a Database Execution Agent.
Your job is to execute SQL queries on the Amazon Athena database via your tools, examine results, handle errors, and perform self-healing query corrections when query execution fails.
"""

class ExecutionAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Execution_Agent",
            system_prompt=EXECUTION_SYSTEM_PROMPT,
            tools=[execute_sql_query]
        )

    def execute_query(self, sql_query: str, session_id: str = "default_session", retries: int = 1) -> dict:
        """Execute the SQL query. If it fails, attempt to auto-correct using LLM and retry."""
        logger.info(f"Execution Agent running query: {sql_query}")
        
        current_sql = sql_query
        attempt = 0
        
        while attempt <= retries:
            try:
                # 1. Execute query via MCP tool
                json_results = execute_sql_query(sql=current_sql)
                
                # Check if it returned a database error string
                if json_results.startswith("Error"):
                    raise Exception(json_results)
                    
                # Parse to list of dicts
                records = json.loads(json_results)
                logger.info(f"Query succeeded on attempt {attempt}. Returned {len(records)} records.")
                
                return {
                    "success": True,
                    "sql": current_sql,
                    "records": records,
                    "row_count": len(records),
                    "error": None
                }
            except Exception as e:
                logger.warning(f"Query execution failed on attempt {attempt}: {e}")
                attempt += 1
                
                if attempt > retries:
                    # No more retries, return failure details
                    return {
                        "success": False,
                        "sql": current_sql,
                        "records": [],
                        "row_count": 0,
                        "error": str(e)
                    }
                
                # Auto-correct query using Bedrock
                logger.info("Attempting auto-correction of the failed query...")
                current_sql = self._auto_correct_query(current_sql, str(e))
                logger.info(f"Corrected SQL to retry:\n{current_sql}")

    def _auto_correct_query(self, failed_sql: str, error_message: str) -> str:
        """Use Bedrock to analyze the error message and correct the SQL statement."""
        prompt = f"""The following SQL query executed on Amazon Athena failed:
Query:
{failed_sql}

Error Message:
{error_message}

Correct this query so it runs successfully on Presto SQL / Amazon Athena.
Ensure table names are only customers, products, orders, order_items, sales_summary, or regions.
Return ONLY the corrected SQL query. Do not add explanations or wrapping.
"""
        corrected = bedrock_service.generate_text(
            prompt=prompt,
            system_prompt="You are a senior database query repair expert. Fix the SQL statement. Return ONLY the SQL query.",
        ).strip()
        
        # Clean potential markdown block wrapping
        if corrected.startswith("```"):
            lines = corrected.splitlines()
            if lines[0].startswith("```sql") or lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            corrected = "\n".join(lines).strip()
            
        return corrected
