import logging
from backend.app.agents.base import BaseAgent

logger = logging.getLogger("app.agents.sql_gen")

SQL_GEN_SYSTEM_PROMPT = """You are a Staff AI Engineer and Senior Database Specialist.
Your task is to convert a natural language business question into an executable SQL query compatible with Amazon Athena (Presto SQL dialect).

Use the following schema documentation and context to formulate the query:
1. customers (customer_id, name, email, region_id, status ['Active', 'Inactive'], created_at, churned ['Yes', 'No'])
2. products (product_id, name, category, price, cost)
3. orders (order_id, customer_id, order_date, total_amount, status ['Completed', 'Pending', 'Cancelled', 'Returned'])
4. order_items (order_item_id, order_id, product_id, quantity, price, discount [0.0 to 1.0])
5. sales_summary (date, region_id, total_revenue, total_orders, new_customers)
6. regions (region_id, name, country)

Business Rules:
- Revenue calculation: quantity * price * (1 - discount) from order_items OR sum(total_amount) from orders where status='Completed'.
- Active Customers: customers.status = 'Active' OR customers with at least one order in the last 90 days.
- Churned: customers.churned = 'Yes'.
- Exclude 'Cancelled' or 'Returned' orders from revenue calculations unless specifically requested.

Output Formatting Rules:
- Return ONLY the executable SQL query.
- Do NOT wrap the query in markdown (like ```sql).
- Do NOT include any introductory or concluding text. Just return the SQL string.
"""

class SQLGenAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="SQL_Gen_Agent",
            system_prompt=SQL_GEN_SYSTEM_PROMPT
        )

    def generate_sql(self, question: str, retrieved_context: str, session_id: str = "default_session") -> str:
        logger.info(f"SQL Gen Agent writing query for question: {question}")
        prompt = f"""Business Question: {question}
Retrieved Glossary & Schema Context:
{retrieved_context}

Provide the SQL query now:"""
        
        sql = self.execute(prompt, session_id=session_id).strip()
        
        # Clean markdown code blocks if the LLM hallucinated them despite instructions
        if sql.startswith("```"):
            lines = sql.splitlines()
            if lines[0].startswith("```sql") or lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            sql = "\n".join(lines).strip()
            
        logger.info(f"Generated SQL: {sql}")
        return sql
