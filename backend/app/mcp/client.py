import logging
from strands import tool
from backend.app.mcp.registry import mcp_registry

logger = logging.getLogger("app.mcp.client")

@tool
def execute_sql_query(sql: str) -> str:
    """Execute a validated Athena SQL query. Only SELECT statements are permitted. Returns database records in JSON formatting."""
    logger.info(f"Agent called execute_sql_query tool via MCP client.")
    return mcp_registry.call_tool("execute_sql_query", {"sql": sql})

@tool
def semantic_search_glossary(query: str, limit: int = 3) -> str:
    """Perform a semantic vector similarity search on the business glossary, KPI definitions, and database schemas to retrieve business definitions. Returns a JSON string of matched items."""
    logger.info(f"Agent called semantic_search_glossary tool via MCP client.")
    return mcp_registry.call_tool("semantic_search_glossary", {"query": query, "limit": limit})

@tool
def retrieve_knowledge_document(document_name: str) -> str:
    """Fetch the full raw text content of a knowledge document by its file name (e.g. 'business_glossary.md', 'kpi_definitions.md', 'schema_documentation.md', 'business_rules.md')."""
    logger.info(f"Agent called retrieve_knowledge_document tool via MCP client.")
    return mcp_registry.call_tool("retrieve_knowledge_document", {"document_name": document_name})
