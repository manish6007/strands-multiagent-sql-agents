import logging
from typing import List, Dict, Any
from backend.app.mcp.servers.athena import athena_mcp
from backend.app.mcp.servers.postgres import postgres_mcp
from backend.app.mcp.servers.s3 import s3_mcp

logger = logging.getLogger("app.mcp.registry")

class MCPRegistry:
    """Consolidated registry mapping MCP tools to their execution instances."""
    
    def __init__(self):
        self.servers = {
            "athena": athena_mcp,
            "postgres": postgres_mcp,
            "s3": s3_mcp
        }
        
    def list_all_tools(self) -> List[Dict[str, Any]]:
        """Combine tools across all registered MCP servers into a single list."""
        all_tools = []
        for server_name, server in self.servers.items():
            for tool in server.get_tools():
                # Enforce server tag for namespacing if desired
                # Let's keep names unique as defined
                all_tools.append({
                    "name": tool["name"],
                    "description": f"[{server_name.upper()}] {tool['description']}",
                    "input_schema": tool["input_schema"],
                    "server": server_name
                })
        return all_tools

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Find the corresponding server for the requested tool and execute it."""
        logger.info(f"MCP Call: Invoking tool '{tool_name}' with args {arguments}")
        
        for server_name, server in self.servers.items():
            for tool in server.get_tools():
                if tool["name"] == tool_name:
                    return server.call_tool(tool_name, arguments)
                    
        return f"Error: Tool '{tool_name}' was not found in any registered MCP server."

# Instantiate global registry
mcp_registry = MCPRegistry()
