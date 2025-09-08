import os
from datetime import datetime
from typing import List, Dict, Any
from autogen_ext.tools.mcp import StreamableHttpServerParams, mcp_server_tools
from config.config import TOOL_DISPLAY_NAMES


class MCPService:
    """Client for managing MCP server connections and tools"""
    
    def __init__(self):
        self.cached_tools = {
            "dappier": [],
            "skyfire": [],
            "all_tools": []
        }
        
        self.initialization_status = {
            "initialized": False,
            "initializing": False,
            "error": None,
            "dappier": {"status": "not_connected", "tools": [], "error": None, "count": 0},
            "skyfire": {"status": "not_connected", "tools": [], "error": None, "count": 0},
            "total_tools": 0,
            "initialized_at": None
        }
    
    def clear_tool_cache(self):
        """Clear the cached tools (useful for re-initialization)"""
        self.cached_tools = {
            "dappier": [],
            "skyfire": [],
            "all_tools": []
        }
    
    async def get_dappier_tools(self) -> List[Any]:
        """Get tools from Dappier MCP server with error handling"""
        try:
            self.initialization_status["dappier"]["status"] = "connecting"
            
            # Configure Dappier MCP server parameters
            server_params = StreamableHttpServerParams(
                url="https://mcp.dappier.com/mcp?apiKey=ak_01k194ztkcey3aq7b8k415k0zp"
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
            
            self.initialization_status["dappier"] = {
                "status": "connected",
                "tools": tool_info,
                "error": None,
                "count": len(tools)
            }
            
            print(f"Successfully loaded {len(tools)} tools from Dappier MCP server")
            return tools
            
        except Exception as e:
            error_msg = str(e)
            self.initialization_status["dappier"] = {
                "status": "error",
                "tools": [],
                "error": error_msg,
                "count": 0
            }
            print(f"Failed to load Dappier tools: {error_msg}")
            return []
    
    async def get_skyfire_tools(self) -> List[Any]:
        """Get tools from Skyfire MCP server with error handling"""
        try:
            # Get Skyfire API key from environment
            skyfire_api_key = os.getenv('SKYFIRE_API_KEY')
            if not skyfire_api_key:
                self.initialization_status["skyfire"] = {
                    "status": "error",
                    "tools": [],
                    "error": "SKYFIRE_API_KEY environment variable not found",
                    "count": 0
                }
                print("Skyfire API key not found in environment variables")
                return []
            
            self.initialization_status["skyfire"]["status"] = "connecting"
            
            # Configure Skyfire MCP server parameters
            server_params = StreamableHttpServerParams(
                url="https://mcp.skyfire.xyz/mcp",
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
            
            self.initialization_status["skyfire"] = {
                "status": "connected",
                "tools": tool_info,
                "error": None,
                "count": len(tools)
            }
            
            print(f"Successfully loaded {len(tools)} tools from Skyfire MCP server")
            return tools
            
        except Exception as e:
            error_msg = str(e)
            self.initialization_status["skyfire"] = {
                "status": "error",
                "tools": [],
                "error": error_msg,
                "count": 0
            }
            print(f"Failed to load Skyfire tools: {error_msg}")
            return []
    
    async def initialize_mcp_connections(self) -> bool:
        """Initialize MCP server connections (tools will be used for session agents)"""
        try:
            self.initialization_status["initializing"] = True
            
            # Check for OpenAI API key
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                error_msg = "OPENAI_API_KEY environment variable is required"
                self.initialization_status["error"] = error_msg
                raise ValueError(error_msg)
            
            # Initialize MCP server connections
            dappier_tools = await self.get_dappier_tools()
            skyfire_tools = await self.get_skyfire_tools()
            
            # Cache the tools for reuse in session agents
            self.cached_tools["dappier"] = dappier_tools if dappier_tools else []
            self.cached_tools["skyfire"] = skyfire_tools if skyfire_tools else []
            
            # Combine all tools for easy access
            all_tools = []
            if dappier_tools:
                all_tools.extend(dappier_tools)
            if skyfire_tools:
                all_tools.extend(skyfire_tools)
            self.cached_tools["all_tools"] = all_tools
            
            # Count total available tools
            total_tools = len(all_tools)
            self.initialization_status["total_tools"] = total_tools
            
            # Mark initialization as complete
            self.initialization_status["initialized"] = True
            self.initialization_status["initializing"] = False
            self.initialization_status["initialized_at"] = datetime.now().isoformat()
            self.initialization_status["error"] = None
            
            print(f"MCP connections initialized with {total_tools} total tools available")
            return True
            
        except Exception as e:
            error_msg = str(e)
            self.initialization_status["initialized"] = False
            self.initialization_status["initializing"] = False
            self.initialization_status["error"] = error_msg
            print(f"Failed to initialize MCP connections: {error_msg}")
            return False
    
    def is_initialized(self) -> bool:
        """Check if MCP connections are initialized"""
        return self.initialization_status["initialized"]
    
    def is_initializing(self) -> bool:
        """Check if MCP connections are currently being initialized"""
        return self.initialization_status["initializing"]
    
    def get_initialization_status(self) -> Dict[str, Any]:
        """Get the current initialization status"""
        return self.initialization_status.copy()
    
    def get_all_tools(self) -> List[Any]:
        """Get all cached tools"""
        return self.cached_tools["all_tools"]
    
    def get_dappier_tools_cached(self) -> List[Any]:
        """Get cached Dappier tools"""
        return self.cached_tools["dappier"]
    
    def get_skyfire_tools_cached(self) -> List[Any]:
        """Get cached Skyfire tools"""
        return self.cached_tools["skyfire"]
    
    def get_tool_count(self) -> int:
        """Get total number of available tools"""
        return len(self.cached_tools["all_tools"])
    
    def reset_initialization_status(self):
        """Reset initialization status for fresh initialization"""
        self.initialization_status = {
            "initialized": False,
            "initializing": False,
            "error": None,
            "dappier": {"status": "not_connected", "tools": [], "error": None, "count": 0},
            "skyfire": {"status": "not_connected", "tools": [], "error": None, "count": 0},
            "total_tools": 0,
            "initialized_at": None
        }