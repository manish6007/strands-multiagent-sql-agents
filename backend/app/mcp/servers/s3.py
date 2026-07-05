import os
import logging

logger = logging.getLogger("app.mcp.servers.s3")

class S3MCPServer:
    """MCP Server simulating S3 bucket document retrieval operations."""
    
    def __init__(self):
        self.name = "s3_mcp_server"
        self.description = "Provides access to raw files stored in the analytics knowledge base bucket (simulated locally under data/knowledge)."

    def get_tools(self) -> list[dict]:
        return [
            {
                "name": "retrieve_knowledge_document",
                "description": "Fetch the full raw text content of a knowledge document by its file name (e.g. 'business_glossary.md', 'kpi_definitions.md', 'schema_documentation.md', 'business_rules.md').",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "document_name": {
                            "type": "string",
                            "description": "The exact name of the file to load."
                        }
                    },
                    "required": ["document_name"]
                }
            }
        ]

    def call_tool(self, name: str, arguments: dict) -> str:
        if name == "retrieve_knowledge_document":
            doc_name = arguments.get("document_name", "")
            if not doc_name:
                return "Error: No document name provided."
            
            # Clean path to prevent directory traversal
            clean_name = os.path.basename(doc_name)
            
            # Determine path
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            doc_path = os.path.join(base_dir, "data", "knowledge", clean_name)
            
            if not os.path.exists(doc_path):
                return f"Error: Document '{clean_name}' not found in S3 knowledge bucket."
                
            try:
                with open(doc_path, "r", encoding="utf-8") as f:
                    content = f.read()
                return content
            except Exception as e:
                logger.error(f"MCP S3 file read error: {e}")
                return f"Error reading document: {str(e)}"
        else:
            return f"Error: Tool '{name}' not found on S3 MCP Server."

# Instantiate server
s3_mcp = S3MCPServer()
