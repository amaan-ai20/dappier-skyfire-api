"""
MCP (Model Context Protocol) service for managing connections to Dappier and Skyfire servers

DEMONSTRATION OVERVIEW:
This service manages connections to both Dappier and Skyfire MCP servers with different levels of functionality:

REAL CONNECTIONS:
- Dappier MCP Server: Makes actual connections to https://mcp.dappier.com/mcp
- Skyfire MCP Server: Makes actual connections to https://mcp.skyfire.xyz/mcp
- Both use real API keys and return functional tools for production use

DEMONSTRATION SETUP:
- The Dappier connection uses a real API key but the payment/charging is handled through Skyfire
- This demonstrates how Skyfire can act as a payment layer for third-party services
- Users pay through Skyfire tokens while accessing real Dappier data and tools
- The integration showcases a complete payment-enabled AI service ecosystem
"""
import os
from datetime import datetime
from autogen_ext.tools.mcp import StreamableHttpServerParams, mcp_server_tools
from config.settings import MCP_SERVERS, TOOL_DISPLAY_NAMES


# Global tool cache to avoid duplicate initialization
cached_tools = {
    "dappier": [],
    "skyfire": [],
    "all_tools": []
}

initialization_status = {
    "initialized": False,
    "initializing": False,
    "error": None,
    "dappier": {"status": "not_connected", "tools": [], "error": None},
    "skyfire": {"status": "not_connected", "tools": [], "error": None},
    "total_tools": 0,
    "initialized_at": None
}


def clear_tool_cache():
    """Clear the cached tools (useful for re-initialization)"""
    global cached_tools
    cached_tools = {
        "dappier": [],
        "skyfire": [],
        "all_tools": []
    }


async def get_dappier_tools():
    """Get tools from Dappier MCP server with error handling"""
    global initialization_status
    
    try:
        initialization_status["dappier"]["status"] = "connecting"
        
        # Configure Dappier MCP server parameters
        server_params = StreamableHttpServerParams(
            url=MCP_SERVERS["dappier"]["url"]
        )
        
        # Get available tools from the MCP server
        tools = await mcp_server_tools(server_params)
        
        # Extract tool names, display names, and descriptions
        tool_info = []
        for tool in tools:
            tool_name = getattr(tool, 'name', str(tool)[:30])
            tool_description = getattr(tool, 'description', '')
            display_name = TOOL_DISPLAY_NAMES.get(tool_name, tool_name)
            tool_info.append({
                "name": tool_name,
                "display_name": display_name,
                "description": tool_description
            })
        
        initialization_status["dappier"] = {
            "status": "connected",
            "tools": tool_info,
            "error": None,
            "count": len(tools)
        }
        
        print(f"Successfully loaded {len(tools)} tools from Dappier MCP server")
        return tools
        
    except Exception as e:
        error_msg = str(e)
        initialization_status["dappier"] = {
            "status": "error",
            "tools": [],
            "error": error_msg,
            "count": 0
        }
        print(f"Failed to load Dappier tools: {error_msg}")
        return []


async def get_skyfire_tools():
    """Get tools from Skyfire MCP server with error handling"""
    global initialization_status
    
    try:
        # Get Skyfire API key from environment
        skyfire_api_key = os.getenv('SKYFIRE_API_KEY')
        if not skyfire_api_key:
            initialization_status["skyfire"] = {
                "status": "error",
                "tools": [],
                "error": "SKYFIRE_API_KEY environment variable not found",
                "count": 0
            }
            print("Skyfire API key not found in environment variables")
            return []
        
        initialization_status["skyfire"]["status"] = "connecting"
        
        # Configure Skyfire MCP server parameters
        server_params = StreamableHttpServerParams(
            url=MCP_SERVERS["skyfire"]["url"],
            headers={"skyfire-api-key": skyfire_api_key}
        )
        
        # Get available tools from the MCP server
        tools = await mcp_server_tools(server_params)
        
        # Extract tool names, display names, and descriptions
        tool_info = []
        for tool in tools:
            tool_name = getattr(tool, 'name', str(tool)[:30])
            tool_description = getattr(tool, 'description', '')
            display_name = TOOL_DISPLAY_NAMES.get(tool_name, tool_name)
            tool_info.append({
                "name": tool_name,
                "display_name": display_name,
                "description": tool_description
            })
        
        initialization_status["skyfire"] = {
            "status": "connected",
            "tools": tool_info,
            "error": None,
            "count": len(tools)
        }
        
        print(f"Successfully loaded {len(tools)} tools from Skyfire MCP server")
        return tools
        
    except Exception as e:
        error_msg = str(e)
        initialization_status["skyfire"] = {
            "status": "error",
            "tools": [],
            "error": error_msg,
            "count": 0
        }
        print(f"Failed to load Skyfire tools: {error_msg}")
        return []


async def initialize_mcp_connections():
    """Initialize MCP server connections (tools will be used for session agents)"""
    global initialization_status, cached_tools
    
    try:
        initialization_status["initializing"] = True
        
        # Check for OpenAI API key
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            error_msg = "OPENAI_API_KEY environment variable is required"
            initialization_status["error"] = error_msg
            raise ValueError(error_msg)
        
        # Initialize MCP server connections
        dappier_tools = await get_dappier_tools()
        skyfire_tools = await get_skyfire_tools()
        
        # Cache the tools for reuse in session agents
        cached_tools["dappier"] = dappier_tools if dappier_tools else []
        cached_tools["skyfire"] = skyfire_tools if skyfire_tools else []
        
        # Combine all tools for easy access
        all_tools = []
        if dappier_tools:
            all_tools.extend(dappier_tools)
        if skyfire_tools:
            all_tools.extend(skyfire_tools)
        cached_tools["all_tools"] = all_tools
        
        # Count total available tools
        total_tools = len(all_tools)
        initialization_status["total_tools"] = total_tools
        
        # Mark initialization as complete
        initialization_status["initialized"] = True
        initialization_status["initializing"] = False
        initialization_status["initialized_at"] = datetime.now().isoformat()
        initialization_status["error"] = None
        
        print(f"MCP connections initialized with {total_tools} total tools available")
        return True
        
    except Exception as e:
        error_msg = str(e)
        initialization_status["initialized"] = False
        initialization_status["initializing"] = False
        initialization_status["error"] = error_msg
        print(f"Failed to initialize MCP connections: {error_msg}")
        return False


def get_cached_tools():
    """Get cached tools"""
    return cached_tools


def get_initialization_status():
    """Get current initialization status"""
    return initialization_status