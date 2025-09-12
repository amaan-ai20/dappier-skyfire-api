"""
MCP (Model Context Protocol) service for managing connections to Dappier and Skyfire servers
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


async def get_skyfire_tools_direct():
    """Get tools from Skyfire MCP server using direct HTTP requests"""
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
        
        # Use httpx to make direct requests to the MCP server
        import httpx
        import json
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "skyfire-api-key": skyfire_api_key
        }
        
        async with httpx.AsyncClient() as client:
            # First, initialize the MCP session
            init_response = await client.post(
                MCP_SERVERS["skyfire"]["url"],
                json={
                    "jsonrpc": "2.0",
                    "id": "init-1",
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {
                            "name": "dappier-api",
                            "version": "1.0"
                        }
                    }
                },
                headers=headers,
                timeout=30.0
            )
            
            if init_response.status_code < 200 or init_response.status_code >= 300:
                raise Exception(f"MCP initialization failed: {init_response.status_code} - {init_response.text}")
            
            # Get session ID from response header
            session_id = init_response.headers.get("mcp-session-id")
            if not session_id:
                raise Exception("Missing session ID in response header")
            
            # Read SSE response for initialization
            init_data = None
            for line in init_response.text.split('\n'):
                if line.startswith('data: '):
                    data_line = line[6:].strip()  # Remove 'data: ' prefix
                    if data_line:
                        init_data = json.loads(data_line)
                        break
            
            if not init_data:
                raise Exception("No data found in SSE response")
            
            print(f"MCP session initialized with ID: {session_id}")
            
            # Now get the list of tools with session ID
            tools_headers = headers.copy()
            tools_headers["Mcp-Session-Id"] = session_id
            
            tools_response = await client.post(
                MCP_SERVERS["skyfire"]["url"],
                json={
                    "jsonrpc": "2.0",
                    "id": "tools-1",
                    "method": "tools/list",
                    "params": {}
                },
                headers=tools_headers,
                timeout=30.0
            )
            
            if tools_response.status_code < 200 or tools_response.status_code >= 300:
                raise Exception(f"Tools list request failed: {tools_response.status_code} - {tools_response.text}")
            
            # Read SSE response for tools list
            tools_data = None
            for line in tools_response.text.split('\n'):
                if line.startswith('data: '):
                    data_line = line[6:].strip()  # Remove 'data: ' prefix
                    if data_line:
                        tools_data = json.loads(data_line)
                        break
            
            if not tools_data or 'result' not in tools_data or 'tools' not in tools_data['result']:
                raise Exception("Invalid tools response format")
            
            raw_tools = tools_data['result']['tools']
            print(f"Retrieved {len(raw_tools)} raw tools from Skyfire MCP server")
            
            # Debug: Print the first tool to understand the structure
            if raw_tools:
                print(f"Sample tool structure: {raw_tools[0]}")
            
            # Create simple tool wrappers that AutoGen can use
            tools = []
            tool_info = []
            
            # Create tool functions with proper parameter signatures based on schema
            for tool_data in raw_tools:
                tool_name = tool_data.get("name", "unknown")
                tool_description = tool_data.get("description", "")
                tool_input_schema = tool_data.get("inputSchema", {})
                
                # Create function with explicit parameters based on the tool's input schema
                def create_tool_with_schema(name: str, description: str, schema: dict, session_id: str, url: str, api_key: str):
                    from typing import Any, Optional
                    import inspect
                    
                    # Get the properties from the schema
                    properties = schema.get("properties", {})
                    required_props = schema.get("required", [])
                    
                    # Build the function signature dynamically
                    params = []
                    param_types = {}
                    
                    for prop_name, prop_info in properties.items():
                        prop_type = prop_info.get("type", "string")
                        is_required = prop_name in required_props
                        
                        # Map JSON schema types to Python types
                        if prop_type == "string":
                            python_type = "str"
                        elif prop_type == "number":
                            python_type = "float"
                        elif prop_type == "integer":
                            python_type = "int"
                        elif prop_type == "boolean":
                            python_type = "bool"
                        else:
                            python_type = "Any"
                        
                        # Add Optional wrapper if not required
                        if not is_required:
                            python_type = f"Optional[{python_type}]"
                            params.append(f"{prop_name}: {python_type} = None")
                        else:
                            params.append(f"{prop_name}: {python_type}")
                        
                        param_types[prop_name] = python_type
                    
                    # Create the function code dynamically
                    func_name = name.replace('-', '_').replace(' ', '_')
                    param_str = ", ".join(params) if params else ""
                    
                    func_code = f'''
async def {func_name}({param_str}) -> str:
    """Make MCP tool call for {name}: {description}"""
    try:
        import httpx
        import json
        import inspect
        
        # Get the current frame to collect all local variables (parameters)
        frame = inspect.currentframe()
        arguments = {{k: v for k, v in frame.f_locals.items() 
                     if k not in ['httpx', 'json', 'inspect', 'frame'] and v is not None}}
        
        headers = {{
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "skyfire-api-key": "{api_key}",
            "Mcp-Session-Id": "{session_id}"
        }}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "{url}",
                json={{
                    "jsonrpc": "2.0",
                    "id": "call-{name}",
                    "method": "tools/call",
                    "params": {{
                        "name": "{name}",
                        "arguments": arguments
                    }}
                }},
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code < 200 or response.status_code >= 300:
                return f"Error calling {name}: {{response.status_code}} - {{response.text}}"
            
            # Read SSE response
            for line in response.text.split('\\n'):
                if line.startswith('data: '):
                    data_line = line[6:].strip()
                    if data_line:
                        result_data = json.loads(data_line)
                        if 'result' in result_data:
                            return str(result_data['result'])
                        elif 'error' in result_data:
                            return f"Error: {{result_data['error']}}"
            
            return f"No valid response from {name}"
            
    except Exception as e:
        return f"Error calling {name}: {{str(e)}}"
'''
                    
                    # Execute the function code to create the function
                    local_vars = {"Optional": Optional, "Any": Any}
                    exec(func_code, globals(), local_vars)
                    tool_function = local_vars[func_name]
                    
                    # Set function attributes
                    tool_function.__name__ = func_name
                    tool_function.__doc__ = f"{description}"
                    tool_function.name = name
                    tool_function.description = description
                    
                    return tool_function
                
                # Create the tool function with proper schema-based parameters
                tool = create_tool_with_schema(
                    tool_name,
                    tool_description,
                    tool_input_schema,
                    session_id,
                    MCP_SERVERS["skyfire"]["url"],
                    skyfire_api_key
                )
                
                tools.append(tool)
                
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
            
            print(f"Successfully loaded {len(tools)} tools from Skyfire MCP server using direct HTTP")
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


async def get_skyfire_tools():
    """Get tools from Skyfire MCP server with fallback to direct HTTP"""
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
        
        # First try the AutoGen MCP client
        try:
            server_params = StreamableHttpServerParams(
                url=MCP_SERVERS["skyfire"]["url"],
                headers={"skyfire-api-key": skyfire_api_key}
            )
            
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
            
        except Exception as autogen_error:
            print(f"AutoGen MCP client failed: {autogen_error}")
            print("Falling back to direct HTTP client...")
            
            # Fall back to direct HTTP client
            return await get_skyfire_tools_direct()
        
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