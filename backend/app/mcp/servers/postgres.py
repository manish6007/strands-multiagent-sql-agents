import logging
from backend.app.database.connection import SessionLocal
from backend.app.database.pg_vector import query_vector_db
from backend.app.services.bedrock_service import bedrock_service

logger = logging.getLogger("app.mcp.servers.postgres")

class PostgresMCPServer:
    """MCP Server exposing pgvector semantic search capabilities."""
    
    def __init__(self):
        self.name = "postgres_mcp_server"
        self.description = "Exposes semantic search tools on top of the PostgreSQL pgvector database containing glossary terms, KPIs, and schema definitions."

    def get_tools(self) -> list[dict]:
        return [
            {
                "name": "semantic_search_glossary",
                "description": "Perform a semantic vector similarity search on the business glossary, KPI definitions, and database schemas.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search term or user intent (e.g. 'Active Customer definition' or 'Revenue KPI')."
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Number of matching documents to return. Defaults to 3.",
                            "default": 3
                        }
                    },
                    "required": ["query"]
                }
            }
        ]

    def call_tool(self, name: str, arguments: dict) -> str:
        if name == "semantic_search_glossary":
            query = arguments.get("query", "")
            limit = arguments.get("limit", 3)
            
            if not query:
                return "Error: No search query provided."
                
            try:
                # 1. Generate query embedding
                embedding = bedrock_service.generate_embeddings(query)
                
                # 2. Query Postgres
                db = SessionLocal()
                try:
                    results = query_vector_db(db, embedding, limit=limit)
                    import json
                    return json.dumps(results)
                finally:
                    db.close()
            except Exception as e:
                logger.error(f"MCP Postgres search error: {e}")
                return f"Error executing semantic search: {str(e)}"
        else:
            return f"Error: Tool '{name}' not found on Postgres MCP Server."

# Instantiate server
postgres_mcp = PostgresMCPServer()
