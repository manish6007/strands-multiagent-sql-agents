import logging
from backend.app.agents.base import BaseAgent
from backend.app.mcp.client import semantic_search_glossary

logger = logging.getLogger("app.agents.rag")

RAG_SYSTEM_PROMPT = """You are an Enterprise RAG Agent.
Your role is to retrieve the business glossary meanings, KPI definitions, schema documentation, and business calculations relevant to the user's analytics query.

Use the provided semantic_search_glossary tool to search the knowledge repository.
Enrich the user's prompt by formatting the retrieved glossary facts, and return this consolidated information.
Do not generate any SQL. Only return context.
"""

class RAGAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="RAG_Agent",
            system_prompt=RAG_SYSTEM_PROMPT,
            tools=[semantic_search_glossary]
        )

    def retrieve_context(self, question: str, session_id: str = "default_session") -> str:
        """Call semantic search to find glossary context and return it."""
        logger.info(f"RAG Agent retrieving context for: {question}")
        
        # We can perform a semantic search call directly using our MCP client tool
        try:
            mcp_results = semantic_search_glossary(query=question, limit=3)
            logger.info("Semantic search completed successfully via MCP tool.")
            return mcp_results
        except Exception as e:
            logger.warning(f"MCP semantic search failed, trying agent reasoning loop: {e}")
            prompt = f"Retrieve and summarize glossary context for the question: '{question}' using your semantic search tool."
            return self.execute(prompt, session_id=session_id)
