import logging
from backend.app.database.athena_mock import athena_client

logger = logging.getLogger("app.mcp.servers.athena")

class AthenaMCPServer:
    """MCP Server simulating Athena query tool operations."""
    
    def __init__(self):
        self.name = "athena_mcp_server"
        self.description = "Provides read-only query access to the Amazon Athena analytics database tables (customers, products, orders, order_items, sales_summary, regions)."

    def get_tools(self) -> list[dict]:
        return [
            {
                "name": "execute_sql_query",
                "description": "Execute a validated Athena SQL query. Only SELECT statements are permitted.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "sql": {
                            "type": "string",
                            "description": "The exact SQL query string to run."
                        }
                    },
                    "required": ["sql"]
                }
            }
        ]

    def call_tool(self, name: str, arguments: dict) -> str:
        if name == "execute_sql_query":
            sql = arguments.get("sql", "")
            if not sql:
                return "Error: No SQL query provided."
            
            # Additional security check
            sql_upper = sql.upper().strip()
            forbidden = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "TRUNCATE", "REPLACE"]
            if any(word in sql_upper for word in forbidden):
                return "Security Error: DDL and DML operations are strictly forbidden. Only SELECT is allowed."
                
            try:
                df = athena_client.execute_query(sql)
                # Return data in CSV format or JSON
                return df.to_json(orient="records")
            except Exception as e:
                logger.error(f"MCP Athena execution error: {e}")
                return f"Error executing query: {str(e)}"
        else:
            return f"Error: Tool '{name}' not found on Athena MCP Server."

# Instantiate server
athena_mcp = AthenaMCPServer()
