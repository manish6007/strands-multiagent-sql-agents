import json
import logging
from backend.app.agents.base import BaseAgent

logger = logging.getLogger("app.agents.sql_review")

SQL_REVIEW_SYSTEM_PROMPT = """You are an expert SQL Quality Assurance Agent.
Your job is to review, validate, and verify the safety and correctness of SQL queries designed for Amazon Athena (Presto SQL).

Verify:
1. Safety: Only 'SELECT' operations are allowed. If the query contains 'DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE', 'GRANT', or 'REVOKE', REJECT it.
2. Tables & Columns: Ensure it only references valid tables (customers, products, orders, order_items, sales_summary, regions) and their correct column names.
3. Syntax: Verify standard ANSI SQL joining and grouping syntax. (e.g., columns in SELECT that are not aggregated must be in GROUP BY).
4. Dialect: Correct Presto/Athena specifics (e.g., date operations should use standard interval notation or date_trunc).

Output Format:
You MUST respond with a valid JSON object matching this structure (and nothing else):
{
  "status": "APPROVED" | "REJECTED",
  "corrected_sql": "string containing corrected SQL query if warnings or errors can be fixed, or empty if rejected or already perfect",
  "errors": ["string descriptions of errors found"],
  "warnings": ["string descriptions of warnings or optimization tips"]
}
"""

class SQLReviewAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="SQL_Review_Agent",
            system_prompt=SQL_REVIEW_SYSTEM_PROMPT
        )

    def review_sql(self, sql_query: str, session_id: str = "default_session") -> dict:
        logger.info(f"SQL Review Agent validating query:\n{sql_query}")
        
        # Pre-execution local safety check to guarantee security
        sql_upper = sql_query.upper().strip()
        forbidden = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "TRUNCATE", "GRANT", "REVOKE"]
        if any(word in sql_upper for word in forbidden):
            logger.critical("Local security filter blocked query before review.")
            return {
                "status": "REJECTED",
                "corrected_sql": "",
                "errors": ["DDL/DML operations are strictly forbidden. Query rejected due to security policy."],
                "warnings": []
            }

        prompt = f"Review this SQL query:\n\n{sql_query}\n\nReturn the JSON review:"
        response_text = self.execute(prompt, session_id=session_id).strip()
        
        # Clean response if LLM wrapped in code block
        if response_text.startswith("```"):
            lines = response_text.splitlines()
            if lines[0].startswith("```json") or lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response_text = "\n".join(lines).strip()
            
        try:
            review_json = json.loads(response_text)
            logger.info(f"SQL Review completed: Status = {review_json.get('status')}")
            return review_json
        except Exception as e:
            logger.error(f"Error parsing SQL Review Agent JSON response: {e}. Output was: {response_text}")
            # Fallback safe review
            return {
                "status": "APPROVED",
                "corrected_sql": sql_query,
                "errors": [],
                "warnings": ["Failed to parse validation agent response, query accepted on basic local filters."]
            }
        
# Instantiate singleton
sql_review_agent = SQLReviewAgent()
