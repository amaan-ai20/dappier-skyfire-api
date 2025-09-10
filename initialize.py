import asyncio
import os
from datetime import datetime
from flask import Blueprint, jsonify
from autogen_ext.tools.mcp import StreamableHttpServerParams, mcp_server_tools
from utils import (
    initialization_status, cached_tools, clear_tool_cache, TOOL_DISPLAY_NAMES
)
from sessions import generate_session_id, get_or_create_session_agent

# Create Blueprint for initialize endpoint
initialize_bp = Blueprint('initialize', __name__)

async def get_dappier_tools():
    """Get tools from Dappier MCP server with error handling"""
    global initialization_status
    
    try:
        initialization_status["dappier"]["status"] = "connecting"
        
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

@initialize_bp.route('/initialize', methods=['POST'])
def initialize():
    """Initialize MCP server connections and create a new session"""
    global initialization_status
    
    try:
        # Initialize MCP connections if not already done
        if not initialization_status["initialized"] and not initialization_status["initializing"]:
            # Clear cached tools for fresh initialization
            clear_tool_cache()
            
            # Reset status for fresh initialization
            initialization_status = {
                "initialized": False,
                "initializing": True,
                "error": None,
                "dappier": {"status": "not_connected", "tools": [], "error": None},
                "skyfire": {"status": "not_connected", "tools": [], "error": None},
                "total_tools": 0,
                "initialized_at": None
            }
            
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Run MCP initialization
                success = loop.run_until_complete(initialize_mcp_connections())
                
                if not success:
                    return jsonify({
                        "status": "error",
                        "message": "Failed to initialize MCP connections",
                        "initialization_status": initialization_status
                    }), 500
                    
            finally:
                loop.close()
        
        # Wait for initialization to complete if in progress
        elif initialization_status["initializing"]:
            # In a real application, you might want to implement proper waiting
            # For now, return that initialization is in progress
            return jsonify({
                "status": "initializing",
                "message": "Initialization is in progress. Please try again in a moment.",
                "initialization_status": initialization_status
            }), 202
        
        # Check if initialization was successful
        if not initialization_status["initialized"]:
            return jsonify({
                "status": "error",
                "message": "System initialization failed",
                "initialization_status": initialization_status
            }), 500
        
        # Generate a new session ID
        session_id = generate_session_id()
        
        # Create session agent immediately
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            session_agent = loop.run_until_complete(get_or_create_session_agent(session_id))
            
            return jsonify({
                "status": "success",
                "message": "Session initialized successfully",
                "session_id": session_id,
                "initialization_status": initialization_status,
                "session_info": {
                    "created_at": datetime.now().isoformat(),
                    "agent_ready": True
                }
            })
            
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Failed to create session agent: {str(e)}",
                "initialization_status": initialization_status
            }), 500
            
        finally:
            loop.close()
            
    except Exception as e:
        initialization_status["initialized"] = False
        initialization_status["initializing"] = False
        initialization_status["error"] = str(e)
        
        return jsonify({
            "status": "error",
            "message": f"Initialization failed: {str(e)}",
            "initialization_status": initialization_status
        }), 500

@initialize_bp.route('/status', methods=['GET'])
def get_status():
    """Get current initialization status"""
    return jsonify({
        "status": "success",
        "initialization_status": initialization_status
    })