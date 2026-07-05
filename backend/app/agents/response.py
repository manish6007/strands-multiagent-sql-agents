import logging
from backend.app.agents.base import BaseAgent

logger = logging.getLogger("app.agents.response")

RESPONSE_SYSTEM_PROMPT = """You are a Principal AWS Solutions Architect, Enterprise Architect, and Senior Business Analyst.
Your role is to write a comprehensive, professional executive summary, key insights list, and tactical business recommendations based on user questions and database query results.

Tone Guide:
- Business-friendly, authoritative, and analytical.
- Address the user's business context.
- Use clean Markdown styling with bold headers, bullet lists, and code blocks for metrics if appropriate.

Include the following sections in your output:
1. Executive Summary: High level summary of what the data shows in 2-3 sentences.
2. Key Insights: Bullet points of the primary takeaways (e.g. ratios, maximums, spikes).
3. Strategic Recommendations: 2-3 actionable business suggestions based on the trends.
"""

class ResponseAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Response_Agent",
            system_prompt=RESPONSE_SYSTEM_PROMPT
        )

    def generate_final_response(self, question: str, sql_used: str, records: list[dict], session_id: str = "default_session") -> str:
        logger.info(f"Response Agent writing final summary for question: {question}")
        
        prompt = f"""User Question: {question}
SQL Query Executed:
{sql_used}

Query Results (JSON data):
{records}

Generate the executive report:"""
        
        return self.execute(prompt, session_id=session_id)
