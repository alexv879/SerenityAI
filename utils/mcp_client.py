"""
MCP (Model Context Protocol) Client Manager
Manages connections to multiple MCP servers and routes tool calls
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
import json

logger = logging.getLogger(__name__)


class MCPTool:
    """Represents a single MCP tool"""
    def __init__(self, name: str, description: str, parameters: Dict, server_name: str):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.server_name = server_name
    
    def to_openai_format(self) -> Dict:
        """Convert to OpenAI function calling format"""
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }


class MCPServer:
    """Base class for MCP servers"""
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.tools: Dict[str, MCPTool] = {}
        self.connected = False
    
    async def connect(self) -> bool:
        """Connect to MCP server"""
        raise NotImplementedError("Subclasses must implement connect()")
    
    async def disconnect(self):
        """Disconnect from MCP server"""
        self.connected = False
    
    async def call_tool(self, tool_name: str, arguments: Dict) -> Any:
        """Execute a tool on this server"""
        raise NotImplementedError("Subclasses must implement call_tool()")
    
    def register_tool(self, tool: MCPTool):
        """Register a tool with this server"""
        self.tools[tool.name] = tool
        logger.info(f"Registered tool '{tool.name}' on server '{self.name}'")


class MCPClientManager:
    """
    Manages multiple MCP servers and routes tool calls
    Integrates with OpenAI Realtime API function calling
    """
    
    def __init__(self):
        self.servers: Dict[str, MCPServer] = {}
        self.tool_registry: Dict[str, str] = {}  # tool_name -> server_name
        logger.info("MCP Client Manager initialized")
    
    async def register_server(self, server: MCPServer) -> bool:
        """
        Register and connect to an MCP server
        
        Args:
            server: MCPServer instance
            
        Returns:
            True if connected successfully
        """
        try:
            connected = await server.connect()
            
            if not connected:
                logger.error(f"Failed to connect to MCP server '{server.name}'")
                return False
            
            self.servers[server.name] = server
            
            # Register all tools from this server
            for tool_name, tool in server.tools.items():
                self.tool_registry[tool_name] = server.name
            
            logger.info(
                f"MCP server '{server.name}' registered with "
                f"{len(server.tools)} tools: {list(server.tools.keys())}"
            )
            return True
            
        except Exception as e:
            logger.error(f"Error registering MCP server '{server.name}': {e}", exc_info=True)
            return False
    
    async def unregister_server(self, server_name: str):
        """Disconnect and remove an MCP server"""
        if server_name in self.servers:
            server = self.servers[server_name]
            await server.disconnect()
            
            # Remove tools from registry
            tools_to_remove = [
                tool_name for tool_name, srv_name in self.tool_registry.items()
                if srv_name == server_name
            ]
            for tool_name in tools_to_remove:
                del self.tool_registry[tool_name]
            
            del self.servers[server_name]
            logger.info(f"MCP server '{server_name}' unregistered")
    
    async def call_tool(self, tool_name: str, arguments: Dict) -> Any:
        """
        Execute a tool via appropriate MCP server
        
        Args:
            tool_name: Name of tool to execute
            arguments: Tool arguments
            
        Returns:
            Tool execution result
        """
        server_name = self.tool_registry.get(tool_name)
        
        if not server_name:
            logger.error(f"Tool '{tool_name}' not found in registry")
            return {"error": f"Tool '{tool_name}' not available"}
        
        server = self.servers.get(server_name)
        
        if not server or not server.connected:
            logger.error(f"Server '{server_name}' for tool '{tool_name}' not connected")
            return {"error": f"Service temporarily unavailable"}
        
        try:
            logger.info(f"Calling tool '{tool_name}' on server '{server_name}' with args: {arguments}")
            result = await server.call_tool(tool_name, arguments)
            logger.info(f"Tool '{tool_name}' completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error calling tool '{tool_name}': {e}", exc_info=True)
            return {"error": str(e)}
    
    def get_all_tools_for_openai(self) -> List[Dict]:
        """
        Get all registered tools in OpenAI function calling format
        
        Returns:
            List of tool definitions for OpenAI Realtime API
        """
        tools = []
        
        for server in self.servers.values():
            for tool in server.tools.values():
                tools.append(tool.to_openai_format())
        
        logger.info(f"Returning {len(tools)} tools for OpenAI: {[t['name'] for t in tools]}")
        return tools
    
    def get_server_status(self) -> Dict[str, Any]:
        """Get status of all MCP servers"""
        return {
            server_name: {
                "connected": server.connected,
                "tools": list(server.tools.keys()),
                "tool_count": len(server.tools)
            }
            for server_name, server in self.servers.items()
        }
    
    async def shutdown(self):
        """Disconnect all MCP servers"""
        logger.info("Shutting down MCP Client Manager")
        
        for server_name in list(self.servers.keys()):
            await self.unregister_server(server_name)
        
        logger.info("All MCP servers disconnected")


# Singleton instance
_mcp_manager: Optional[MCPClientManager] = None
_mcp_manager_lock = asyncio.Lock()


def get_mcp_manager() -> MCPClientManager:
    """
    Get or create singleton MCP Client Manager (synchronous)
    Note: This is synchronous and not fully thread-safe.
    For async contexts, use async initialization patterns.
    """
    global _mcp_manager

    if _mcp_manager is None:
        _mcp_manager = MCPClientManager()

    return _mcp_manager

