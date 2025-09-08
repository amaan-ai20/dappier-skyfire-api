import os
import asyncio
import json
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import StreamableHttpServerParams, mcp_server_tools
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Enable CORS for all routes and origins
CORS(app, origins="*", methods=["GET", "POST", "OPTIONS"], allow_headers=["Content-Type", "Authorization"])

# Session-based agent management
session_agents = {}  # Dictionary to store session-specific agents
session_metadata = {}  # Store session metadata
initialization_status = {
    "initialized": False,
    "initializing": False,
    "error": None,
    "dappier": {"status": "not_connected", "tools": [], "error": None},
    "skyfire": {"status": "not_connected", "tools": [], "error": None},
    "total_tools": 0,
    "initialized_at": None
}

# Session management configuration
SESSION_CONFIG = {
    "max_sessions": 100,  # Maximum number of concurrent sessions
    "session_timeout": 3600,  # Session timeout in seconds (1 hour)
    "cleanup_interval": 300  # Cleanup interval in seconds (5 minutes)
}

# Tool display names for UI
TOOL_DISPLAY_NAMES = {
    # Dappier tools
    'real-time-search': 'Real Time Search',
    'stock-market-data': 'Stock Market Data',
    'research-papers-search': 'Research Papers Search',
    'benzinga': 'Benzinga',
    'sports-news': 'Sports News',
    'lifestyle-news': 'Lifestyle News',
    'iheartdogs-ai': 'Iheartdogs AI',
    'iheartcats-ai': 'Iheartcats AI',
    'one-green-planet': 'One Green Planet',
    'wish-tv-ai': 'Wish TV AI',
    # Skyfire tools
    'find-sellers': 'Find Sellers',
    'create-kya-token': 'Create KYA Token',
    'create-pay-token': 'Create Pay Token',
    'create-kya-payment-token': 'Create KYA Payment Token',
    'get-current-datetime': 'Get Current Datetime'
}

def generate_session_id():
    """Generate a unique session ID"""
    return f"sess_{uuid.uuid4().hex[:16]}"

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
    global initialization_status
    
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
        
        # Count total available tools
        total_tools = 0
        if dappier_tools:
            total_tools += len(dappier_tools)
        if skyfire_tools:
            total_tools += len(skyfire_tools)
        
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

async def create_session_agent():
    """Create a new agent instance for a session"""
    try:
        # Check for OpenAI API key
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        # Create OpenAI model client for AutoGen
        model_client = OpenAIChatCompletionClient(
            model="gpt-4o",
            api_key=api_key
        )
        
        # Get tools from both MCP servers (reuse existing connections if available)
        dappier_tools = await get_dappier_tools()
        skyfire_tools = await get_skyfire_tools()
        
        # Combine all tools
        all_tools = []
        if dappier_tools:
            all_tools.extend(dappier_tools)
        if skyfire_tools:
            all_tools.extend(skyfire_tools)
        
        # Create AutoGen assistant agent with MCP tools
        if all_tools:
            session_agent = AssistantAgent(
                name="chat_assistant",
                model_client=model_client,
                tools=all_tools,
                reflect_on_tool_use=True,
                max_tool_iterations=10,
                model_client_stream=True,
                system_message="You are a helpful AI assistant with access to both Dappier and Skyfire tools for enhanced information retrieval and analysis. When you use tools to get information, you MUST always process and summarize the results in a natural, conversational way. After calling any tool, you must provide a comprehensive response based on the tool's results. Never return raw tool data to users. Always analyze the information from tools and provide a helpful, well-formatted response that directly answers the user's question. Your response should be conversational and informative, making use of the data you retrieved through the tools."
            )
        else:
            session_agent = AssistantAgent(
                name="chat_assistant",
                model_client=model_client,
                model_client_stream=True,
                system_message="You are a helpful AI assistant. Provide clear, concise, and helpful responses to user queries."
            )
        
        return session_agent
        
    except Exception as e:
        print(f"Failed to create session agent: {str(e)}")
        raise

def cleanup_expired_sessions():
    """Clean up expired sessions"""
    global session_agents, session_metadata
    current_time = datetime.now().timestamp()
    
    expired_sessions = []
    for session_id, metadata in session_metadata.items():
        if current_time - metadata['last_activity'] > SESSION_CONFIG['session_timeout']:
            expired_sessions.append(session_id)
    
    for session_id in expired_sessions:
        if session_id in session_agents:
            del session_agents[session_id]
        if session_id in session_metadata:
            del session_metadata[session_id]
        print(f"Cleaned up expired session: {session_id}")
    
    return len(expired_sessions)

async def get_or_create_session_agent(session_id):
    """Get existing session agent or create a new one"""
    global session_agents, session_metadata
    
    # Clean up expired sessions periodically
    cleanup_expired_sessions()
    
    # Check if we've reached the maximum number of sessions
    if len(session_agents) >= SESSION_CONFIG['max_sessions'] and session_id not in session_agents:
        # Remove the oldest session
        oldest_session = min(session_metadata.keys(), key=lambda k: session_metadata[k]['last_activity'])
        if oldest_session in session_agents:
            del session_agents[oldest_session]
        if oldest_session in session_metadata:
            del session_metadata[oldest_session]
        print(f"Removed oldest session to make room: {oldest_session}")
    
    # Update session metadata
    current_time = datetime.now().timestamp()
    if session_id not in session_metadata:
        session_metadata[session_id] = {
            'created_at': current_time,
            'last_activity': current_time,
            'message_count': 0
        }
    else:
        session_metadata[session_id]['last_activity'] = current_time
        session_metadata[session_id]['message_count'] += 1
    
    # Get or create session agent
    if session_id not in session_agents:
        # Check if global initialization is complete
        if not initialization_status["initialized"]:
            raise ValueError("System not initialized. Please call /initialize endpoint first.")
        
        print(f"Creating new session agent for session: {session_id}")
        session_agents[session_id] = await create_session_agent()
    
    return session_agents[session_id]

def _iter_items(content):
    """Normalize content to a list for iteration"""
    if content is None:
        return []
    if isinstance(content, (list, tuple)):
        return content
    return [content]

def _extract_name_and_args(item):
    """Extract name and arguments from an item using multiple fallback strategies"""
    name = None
    args = None
    
    # Strategy 1: Attribute access
    try:
        name = getattr(item, 'name', None)
        args = getattr(item, 'arguments', None)
        if name:
            return name, args
    except:
        pass
    
    # Strategy 2: Dict access
    try:
        if hasattr(item, 'get'):
            name = item.get('name')
            args = item.get('arguments')
            if name:
                return name, args
    except:
        pass
    
    # Strategy 3: JSON string fallback
    try:
        if isinstance(item, str):
            parsed = json.loads(item)
            name = parsed.get('name')
            args = parsed.get('arguments')
            if name:
                return name, args
    except:
        pass
    
    return name, args

def build_conversation_context(current_message, messages_history=None):
    """Build conversation context from message history and current message"""
    if not messages_history or len(messages_history) == 0:
        # No history, just return the current message
        return current_message
    
    # Build conversation context from history
    context_parts = []
    
    # Add conversation history
    context_parts.append("Previous conversation:")
    for msg in messages_history:
        role = msg.get('role', msg.get('type', 'user'))  # Support both 'role' and 'type' fields
        content = msg.get('content', '')
        
        if role == 'user':
            context_parts.append(f"User: {content}")
        elif role in ['assistant', 'ai']:
            context_parts.append(f"Assistant: {content}")
    
    # Add current message
    context_parts.append(f"\nCurrent user message: {current_message}")
    context_parts.append("\nPlease respond to the current user message, taking into account the conversation history above.")
    
    return "\n".join(context_parts)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy", 
        "service": "Flask AutoGen API with Dappier & Skyfire MCP Integration",
        "framework": "Microsoft AutoGen",
        "model": "gpt-4o",
        "session_management": {
            "enabled": True,
            "active_sessions": len(session_agents),
            "max_sessions": SESSION_CONFIG['max_sessions'],
            "session_timeout": SESSION_CONFIG['session_timeout']
        },
        "mcp_servers": {
            "dappier": "https://mcp.dappier.com/sse",
            "skyfire": "https://mcp.skyfire.xyz/sse"
        },
        "endpoints": {
            "initialize": "/initialize (POST - creates first session)",
            "new_session": "/sessions/new (POST - creates additional session)",
            "chat": "/chat (POST - requires session_id)",
            "sessions": "/sessions (GET - list sessions)",
            "session_delete": "/sessions/<session_id> (DELETE)",
            "session_cleanup": "/sessions/cleanup (POST)"
        }
    })

@app.route('/initialize', methods=['POST'])
def initialize():
    """Initialize MCP server connections and create a new session"""
    global initialization_status
    
    try:
        # Initialize MCP connections if not already done
        if not initialization_status["initialized"] and not initialization_status["initializing"]:
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

@app.route('/status', methods=['GET'])
def get_status():
    """Get current initialization status"""
    return jsonify({
        "status": "success",
        "initialization_status": initialization_status
    })

@app.route('/sessions/new', methods=['POST'])
def create_new_session():
    """Create a new session (requires system to be initialized)"""
    global initialization_status
    
    # Check if system is initialized
    if not initialization_status["initialized"]:
        return jsonify({
            "status": "error",
            "message": "System not initialized. Please call /initialize endpoint first.",
            "initialization_status": initialization_status
        }), 400
    
    try:
        # Generate a new session ID
        session_id = generate_session_id()
        
        # Create session agent
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            session_agent = loop.run_until_complete(get_or_create_session_agent(session_id))
            
            return jsonify({
                "status": "success",
                "message": "New session created successfully",
                "session_id": session_id,
                "session_info": {
                    "created_at": datetime.now().isoformat(),
                    "agent_ready": True
                }
            })
            
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Failed to create session agent: {str(e)}"
            }), 500
            
        finally:
            loop.close()
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to create new session: {str(e)}"
        }), 500

@app.route('/sessions', methods=['GET'])
def get_sessions():
    """Get information about active sessions"""
    global session_agents, session_metadata
    
    # Clean up expired sessions before reporting
    cleanup_expired_sessions()
    
    sessions_info = []
    for session_id, metadata in session_metadata.items():
        sessions_info.append({
            "session_id": session_id,
            "created_at": datetime.fromtimestamp(metadata['created_at']).isoformat(),
            "last_activity": datetime.fromtimestamp(metadata['last_activity']).isoformat(),
            "message_count": metadata['message_count'],
            "has_agent": session_id in session_agents
        })
    
    return jsonify({
        "status": "success",
        "active_sessions": len(session_agents),
        "max_sessions": SESSION_CONFIG['max_sessions'],
        "session_timeout": SESSION_CONFIG['session_timeout'],
        "sessions": sessions_info
    })

@app.route('/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """Delete a specific session"""
    global session_agents, session_metadata
    
    if session_id in session_agents:
        del session_agents[session_id]
    
    if session_id in session_metadata:
        del session_metadata[session_id]
    
    return jsonify({
        "status": "success",
        "message": f"Session {session_id} deleted successfully"
    })

@app.route('/sessions/cleanup', methods=['POST'])
def cleanup_sessions():
    """Manually trigger session cleanup"""
    cleaned_count = cleanup_expired_sessions()
    
    return jsonify({
        "status": "success",
        "message": f"Cleaned up {cleaned_count} expired sessions",
        "active_sessions": len(session_agents)
    })

@app.route('/chat', methods=['POST'])
def chat_completion():
    """Chat completion endpoint that uses AutoGen with streaming and session management"""
    try:
        # Check if MCP connections are initialized
        if not initialization_status["initialized"]:
            return jsonify({
                "error": "System not initialized. Please call /initialize endpoint first.",
                "initialization_status": initialization_status
            }), 400
        
        # Get the request data
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        # Extract message from request
        message = data.get('message')
        if not message:
            return jsonify({"error": "Message field is required"}), 400
        
        # Extract session ID from request (required for session management)
        session_id = data.get('session_id')
        if not session_id:
            return jsonify({"error": "session_id field is required for session management"}), 400
        
        # Validate session ID format (basic validation)
        if not isinstance(session_id, str) or len(session_id.strip()) == 0:
            return jsonify({"error": "session_id must be a non-empty string"}), 400
        
        session_id = session_id.strip()
        
        # Extract conversation history from request (optional)
        messages_history = data.get('messages', [])
        
        # Use streaming with session-based agent
        return Response(
            stream_with_context(generate_streaming_response(message, messages_history, session_id)),
            mimetype='text/plain',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive'
            }
        )
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

def generate_streaming_response(message, messages_history=None, session_id=None):
    """Generate streaming response using session-specific AutoGen agent with conversation history"""
    try:
        # Session ID is required
        if not session_id:
            yield f"data: {json.dumps({'error': 'Session ID is required', 'type': 'error'})}\n\n"
            return
        
        # Get session-specific agent
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            session_agent = loop.run_until_complete(get_or_create_session_agent(session_id))
        except Exception as e:
            yield f"data: {json.dumps({'error': f'Failed to get session agent: {str(e)}', 'type': 'error'})}\n\n"
            return
        finally:
            loop.close()
        
        # Build conversation context from history
        conversation_context = build_conversation_context(message, messages_history)
        
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Define async function to stream messages
            async def stream_messages():
                # Use the session-specific agent
                async for chunk in session_agent.run_stream(task=conversation_context):
                    if hasattr(chunk, 'type') and chunk.type != 'ModelClientStreamingChunkEvent':
                        print(chunk)
                    # Handle tool call requests - inform UI which tool is being called
                    if hasattr(chunk, 'type') and chunk.type == 'ToolCallRequestEvent':
                        if hasattr(chunk, 'content'):
                            # Iterate over all items in chunk.content
                            for item in _iter_items(chunk.content):
                                try:
                                    tool_name, tool_args = _extract_name_and_args(item)
                                    if tool_name:
                                        display_name = TOOL_DISPLAY_NAMES.get(tool_name, tool_name)
                                        payload = {
                                            'tool_name': tool_name,
                                            'tool_display_name': display_name,
                                            'type': 'tool_call',
                                            'status': 'calling'
                                        }
                                        # Include arguments when available
                                        if tool_args is not None:
                                            payload['arguments'] = tool_args
                                        yield f"data: {json.dumps(payload)}\n\n"
                                except Exception as e:
                                    pass
                    
                    # Handle tool execution results - inform UI that tool finished
                    elif hasattr(chunk, 'type') and chunk.type == 'ToolCallExecutionEvent':
                        if hasattr(chunk, 'content'):
                            # Iterate over all items in chunk.content
                            for item in _iter_items(chunk.content):
                                try:
                                    tool_name, tool_args = _extract_name_and_args(item)
                                    if tool_name:
                                        display_name = TOOL_DISPLAY_NAMES.get(tool_name, tool_name)
                                        payload = {
                                            'tool_name': tool_name,
                                            'tool_display_name': display_name,
                                            'type': 'tool_call',
                                            'status': 'completed'
                                        }
                                        yield f"data: {json.dumps(payload)}\n\n"
                                except Exception as e:
                                    pass
                    
                    # Handle ModelClientStreamingChunkEvent for token-level streaming
                    elif hasattr(chunk, 'type') and chunk.type == 'ModelClientStreamingChunkEvent':
                        if hasattr(chunk, 'content') and chunk.content:
                            yield f"data: {json.dumps({'content': chunk.content, 'type': 'token'})}\n\n"
                    
                    # Handle TextMessage (complete messages)
                    elif hasattr(chunk, 'type') and chunk.type == 'TextMessage':
                        if hasattr(chunk, 'source') and chunk.source == 'chat_assistant':
                            if hasattr(chunk, 'content') and chunk.content:
                                yield f"data: {json.dumps({'content': chunk.content, 'type': 'message'})}\n\n"
                    
                    # Handle TaskResult (final result)
                    elif hasattr(chunk, 'messages'):
                        # This is the final TaskResult - we can ignore it since we already streamed the content
                        pass
                    
                    # Handle ToolCallSummaryMessage - but extract only the processed response
                    elif hasattr(chunk, 'type') and chunk.type == 'ToolCallSummaryMessage':
                        # This might contain the LLM's processed response after using tools
                        # Let's check if there's useful content here
                        if hasattr(chunk, 'content') and chunk.content:
                            pass
                    
                    # Handle any other chunk types
                    else:
                        pass
            
            # Create async function to handle the streaming
            async def run_streaming():
                async for data in stream_messages():
                    yield data
                # Send completion signal
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
            # Run the async generator in the event loop
            async_gen = run_streaming()
            try:
                while True:
                    data = loop.run_until_complete(async_gen.__anext__())
                    yield data
            except StopAsyncIteration:
                pass
            
        finally:
            loop.close()
            
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e), 'type': 'error'})}\n\n"



if __name__ == '__main__':
    print("Starting Flask AutoGen API with Dappier & Skyfire MCP Integration")
    print("Server will be available at: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
