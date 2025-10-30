"""
MCP Server Initialization
Sets up all MCP servers and integrates with OpenAI Realtime API
"""

import asyncio
import logging
from typing import Optional

from utils.mcp_client import get_mcp_manager
from mcp_servers.web_search_server import WebSearchMCPServer
from mcp_servers.nhs_healthcare_server import NHSHealthcareMCPServer
from mcp_servers.age_uk_services_server import AgeUKServicesMCPServer

logger = logging.getLogger(__name__)


async def initialize_mcp_servers(
    brave_api_key: Optional[str] = None
) -> bool:
    """
    Initialize all MCP servers
    
    Args:
        brave_api_key: Optional Brave Search API key (falls back to DuckDuckGo if not provided)
        
    Returns:
        True if at least one server initialized successfully
    """
    logger.info("🚀 Initializing MCP servers...")
    
    mcp_manager = get_mcp_manager()
    success_count = 0
    
    # 1. Web Search MCP Server
    try:
        logger.info("📡 Initializing Web Search MCP Server...")
        web_search_server = WebSearchMCPServer(brave_api_key=brave_api_key)
        
        if await mcp_manager.register_server(web_search_server):
            success_count += 1
            logger.info("✅ Web Search MCP Server registered (3 tools)")
        else:
            logger.warning("⚠️  Web Search MCP Server failed to register")
            
    except Exception as e:
        logger.error(f"❌ Web Search MCP Server error: {e}", exc_info=True)
    
    # 2. NHS Healthcare MCP Server
    try:
        logger.info("🏥 Initializing NHS Healthcare MCP Server...")
        nhs_server = NHSHealthcareMCPServer()
        
        if await mcp_manager.register_server(nhs_server):
            success_count += 1
            logger.info("✅ NHS Healthcare MCP Server registered (4 tools)")
        else:
            logger.warning("⚠️  NHS Healthcare MCP Server failed to register")
            
    except Exception as e:
        logger.error(f"❌ NHS Healthcare MCP Server error: {e}", exc_info=True)
    
    # 3. Age UK Services MCP Server
    try:
        logger.info("🤝 Initializing Age UK Services MCP Server...")
        age_uk_server = AgeUKServicesMCPServer()
        
        if await mcp_manager.register_server(age_uk_server):
            success_count += 1
            logger.info("✅ Age UK Services MCP Server registered (5 tools)")
        else:
            logger.warning("⚠️  Age UK Services MCP Server failed to register")
            
    except Exception as e:
        logger.error(f"❌ Age UK Services MCP Server error: {e}", exc_info=True)
    
    # Summary
    if success_count > 0:
        logger.info(
            f"🎉 MCP initialization complete! "
            f"{success_count}/3 servers online, "
            f"{len(mcp_manager.tool_registry)} tools available"
        )
        
        # Log available tools
        logger.info("📋 Available MCP tools:")
        for tool_name in sorted(mcp_manager.tool_registry.keys()):
            logger.info(f"   - {tool_name}")
        
        return True
    else:
        logger.error("❌ No MCP servers initialized successfully")
        return False


def get_mcp_tools_for_openai() -> list:
    """
    Get all MCP tools in OpenAI function calling format
    
    Returns:
        List of tool definitions for OpenAI Realtime API
    """
    mcp_manager = get_mcp_manager()
    return mcp_manager.get_all_tools_for_openai()


async def call_mcp_tool(tool_name: str, arguments: dict) -> dict:
    """
    Execute an MCP tool
    
    Args:
        tool_name: Name of tool to execute
        arguments: Tool arguments
        
    Returns:
        Tool execution result
    """
    mcp_manager = get_mcp_manager()
    return await mcp_manager.call_tool(tool_name, arguments)


async def shutdown_mcp_servers():
    """Shutdown all MCP servers"""
    logger.info("🛑 Shutting down MCP servers...")
    mcp_manager = get_mcp_manager()
    await mcp_manager.shutdown()
    logger.info("✅ All MCP servers shut down")


def get_mcp_status() -> dict:
    """
    Get status of all MCP servers
    
    Returns:
        Dict with server status and tool counts
    """
    mcp_manager = get_mcp_manager()
    return mcp_manager.get_server_status()


# Example usage
async def main():
    """Test MCP servers"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Initialize servers
    brave_api_key = os.getenv("BRAVE_API_KEY")  # Optional
    success = await initialize_mcp_servers(brave_api_key=brave_api_key)
    
    if not success:
        print("❌ Failed to initialize MCP servers")
        return
    
    # Test web search
    print("\n🔍 Testing web search...")
    result = await call_mcp_tool(
        "search_web_information",
        {"query": "chiropodist in Middlesbrough", "result_count": 3}
    )
    print(f"Found {result.get('result_count', 0)} results")
    
    # Test NHS services
    print("\n🏥 Testing NHS services...")
    result = await call_mcp_tool(
        "find_nhs_services",
        {"service_type": "pharmacy", "postcode": "TS1 2AQ"}
    )
    print(f"Found {result.get('count', 0)} pharmacies")
    
    # Test Age UK befriending
    print("\n🤝 Testing Age UK befriending...")
    result = await call_mcp_tool(
        "find_befriending_service",
        {"postcode": "TS1 2AQ"}
    )
    print(f"Found {result.get('count', 0)} befriending services")
    
    # Show status
    print("\n📊 MCP Server Status:")
    status = get_mcp_status()
    for server_name, info in status.items():
        print(f"  {server_name}: {'✅' if info['connected'] else '❌'} ({info['tool_count']} tools)")
    
    # Shutdown
    await shutdown_mcp_servers()
    print("\n✅ Test complete!")


if __name__ == "__main__":
    asyncio.run(main())

