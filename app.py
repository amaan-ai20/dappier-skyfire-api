import os
import asyncio
import json
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import Swarm
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.base import Handoff
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import StreamableHttpServerParams, mcp_server_tools
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Enable CORS for all routes and origins
CORS(app, origins="*", methods=["GET", "POST", "OPTIONS"], allow_headers=["Content-Type", "Authorization"])

# Session-based swarm management
session_swarms = {}  # Dictionary to store session-specific swarms
session_metadata = {}  # Store session metadata

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

# Session management configuration
SESSION_CONFIG = {
    "max_sessions": 100,
    "session_timeout": 3600,
    "cleanup_interval": 300
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

def clear_tool_cache():
    """Clear the cached tools (useful for re-initialization)"""
    global cached_tools
    cached_tools = {
        "dappier": [],
        "skyfire": [],
        "all_tools": []
    }

def clear_session_cache():
    """Clear all cached sessions to force recreation with updated configuration"""
    global session_swarms, session_metadata
    session_swarms.clear()
    session_metadata.clear()
    print("Cleared all session caches - new sessions will use updated configuration")

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

async def create_session_swarm():
    """Create a new Swarm instance for a session"""
    global cached_tools
    
    try:
        # Check for OpenAI API key
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        # Create OpenAI model client for AutoGen
        model_client = OpenAIChatCompletionClient(
            model="gpt-4o",
            api_key=api_key,
            parallel_tool_calls=False,  # Disable parallel tool calls to avoid multiple handoffs
            temperature=0.0  # Deterministic behavior for consistent agent responses
        )
        
        # Get cached tools
        dappier_tools = cached_tools["dappier"]
        skyfire_tools = cached_tools["skyfire"]
        
        # Create the Planning Agent (orchestrator)
        planning_agent = AssistantAgent(
            name="planning_agent",
            model_client=model_client,
            handoffs=[
                Handoff(target="dappier_agent", description="Handoff to Dappier agent for real-time search, news, research papers, or content queries"),
                Handoff(target="skyfire_agent", description="Handoff to Skyfire agent for network operations, token creation, or payment processing or finding sellers on skyfire.")
            ],
            reflect_on_tool_use=True,
            max_tool_iterations=10,
            system_message="""You are the Planning Agent - the orchestrator of this team and general assistant.
            
Your role is to:
1. Analyze incoming requests and determine which specialized agent should handle them
2. Delegate tasks to the appropriate agent based on their capabilities
3. Handle general questions and assistance that don't require specialized tools
4. Ensure smooth coordination between agents

Available specialized agents and their capabilities:
- **Dappier Agent**: Handles real-time search, news (financial, sports, lifestyle), research papers, and specialized content (pets, sustainability)
- **Skyfire Agent**: Manages network operations, token creation (KYA, PAY), and payment processing

IMPORTANT WORKFLOW:
- For requests requiring specialized tools: delegate to the appropriate agent
- For general questions: handle them directly
- When an agent hands back to you after completing a task: 
  * If they provided clear output, acknowledge it and use TERMINATE
  * If they didn't provide output, ask them to explain what they accomplished before terminating
- When you complete a task directly: use TERMINATE immediately after your response
- NEVER continue the conversation unnecessarily - always end with TERMINATE when the user's request is fulfilled
- Ensure the user always receives meaningful output about what was accomplished

Use TERMINATE when the task is complete."""
        )
        
        # Create the Dappier Agent with Dappier tools
        dappier_agent = AssistantAgent(
            name="dappier_agent",
            model_client=model_client,
            tools=dappier_tools if dappier_tools else [],
            handoffs=[
                Handoff(target="planning_agent", description="Return to Planning agent after completing task")
            ],
            reflect_on_tool_use=True,
            max_tool_iterations=10,
            system_message="""You are the Dappier Agent - specialized in real-time information retrieval.

Your capabilities include:
- Real-time web search for latest news, weather, deals
- Stock market data and financial news
- Research papers from arXiv
- News from various sources (Benzinga, sports, lifestyle, WISH-TV)
- Specialized content (iHeartDogs, iHeartCats, One Green Planet)

CRITICAL WORKFLOW - Follow these steps in order:
1. Use the appropriate tool to gather the requested information
2. ALWAYS analyze and process the tool results
3. ALWAYS provide a comprehensive, well-formatted response message with the information gathered
4. ONLY AFTER providing your response message, hand off back to the planning_agent

IMPORTANT RULES:
- Never return raw tool data - always analyze and provide helpful, well-formatted responses
- You MUST provide a response message before any handoff
- Do NOT continue the conversation or ask follow-up questions after your response
- You can ONLY handoff back to the planning_agent. Do not attempt to handoff to other agents.
- If a tool call fails, explain what went wrong and suggest alternatives before handing back"""
        )
        
        # Create the Skyfire Agent with Skyfire tools
        skyfire_agent = AssistantAgent(
            name="skyfire_agent",
            model_client=model_client,
            tools=skyfire_tools if skyfire_tools else [],
            handoffs=[
                Handoff(target="planning_agent", description="Return to Planning agent after completing task")
            ],
            reflect_on_tool_use=True,
            max_tool_iterations=10,
            system_message="""You are the Skyfire Agent - specialized in network operations and token management.

Your capabilities include:
- Finding sellers on the Skyfire network
- Creating KYA (Know Your Agent) tokens for authentication
- Creating PAY tokens for transactions (deducts from wallet)
- Creating combined KYA+PAY tokens
- Getting current date/time information

CRITICAL WORKFLOW - Follow these steps in order:
1. Use the appropriate tools to complete the requested operations
2. ALWAYS analyze and process the tool results carefully
3. ALWAYS provide a comprehensive, well-formatted response message with the results
4. ONLY AFTER providing your response message, hand off back to the planning_agent

IMPORTANT RULES:
- Seller Service ID is equal to ID. Never ever use Seller.Id, use Id.
- Handle all token and payment operations carefully (PAY tokens deduct money from wallets)
- You MUST provide a detailed response message before any handoff
- Include specific details: token IDs, seller information, timestamps, etc.
- Explain clearly what was accomplished and any important information
- Do NOT continue the conversation or ask follow-up questions after your response
- You can ONLY handoff back to the planning_agent. Do not attempt to handoff to other agents.
- If a tool call fails, explain what went wrong and suggest alternatives before handing back"""
        )
        
        # Create termination condition
        termination = TextMentionTermination("TERMINATE")
        
        # Create the Swarm team
        swarm = Swarm(
            participants=[planning_agent, dappier_agent, skyfire_agent],
            termination_condition=termination
        )
        
        return swarm
        
    except Exception as e:
        print(f"Failed to create session swarm: {str(e)}")
        raise

def cleanup_expired_sessions():
    """Clean up expired sessions"""
    global session_swarms, session_metadata
    current_time = datetime.now().timestamp()
    
    expired_sessions = []
    for session_id, metadata in session_metadata.items():
        if current_time - metadata['last_activity'] > SESSION_CONFIG['session_timeout']:
            expired_sessions.append(session_id)
    
    for session_id in expired_sessions:
        if session_id in session_swarms:
            del session_swarms[session_id]
        if session_id in session_metadata:
            del session_metadata[session_id]
        print(f"Cleaned up expired session: {session_id}")
    
    return len(expired_sessions)

async def create_new_session_swarm(session_id):
    """Always create a new session swarm (used by initialize endpoint)"""
    global session_swarms, session_metadata
    
    # Clean up expired sessions periodically
    cleanup_expired_sessions()
    
    # Check if global initialization is complete
    if not initialization_status["initialized"]:
        raise ValueError("System not initialized. Please call /initialize endpoint first.")
    
    # Remove any existing session with this ID (safety measure)
    if session_id in session_swarms:
        del session_swarms[session_id]
    if session_id in session_metadata:
        del session_metadata[session_id]
    
    # Check if we've reached the maximum number of sessions
    if len(session_swarms) >= SESSION_CONFIG['max_sessions']:
        # Remove the oldest session
        oldest_session = min(session_metadata.keys(), key=lambda k: session_metadata[k]['last_activity'])
        if oldest_session in session_swarms:
            del session_swarms[oldest_session]
        if oldest_session in session_metadata:
            del session_metadata[oldest_session]
        print(f"Removed oldest session to make room: {oldest_session}")
    
    # Create new session metadata
    current_time = datetime.now().timestamp()
    session_metadata[session_id] = {
        'created_at': current_time,
        'last_activity': current_time,
        'message_count': 0
    }
    
    # Always create a new session swarm
    print(f"Creating new session swarm for session: {session_id}")
    session_swarms[session_id] = await create_session_swarm()
    
    return session_swarms[session_id]

async def get_or_create_session_swarm(session_id):
    """Get existing session swarm or create a new one"""
    global session_swarms, session_metadata
    
    # Clean up expired sessions periodically
    cleanup_expired_sessions()
    
    # Check if we've reached the maximum number of sessions
    if len(session_swarms) >= SESSION_CONFIG['max_sessions'] and session_id not in session_swarms:
        # Remove the oldest session
        oldest_session = min(session_metadata.keys(), key=lambda k: session_metadata[k]['last_activity'])
        if oldest_session in session_swarms:
            del session_swarms[oldest_session]
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
    
    # Get or create session swarm
    if session_id not in session_swarms:
        # Check if global initialization is complete
        if not initialization_status["initialized"]:
            raise ValueError("System not initialized. Please call /initialize endpoint first.")
        
        print(f"Creating new session swarm for session: {session_id}")
        session_swarms[session_id] = await create_session_swarm()
    
    return session_swarms[session_id]

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
        role = msg.get('role', 'user')
        content = msg.get('content', '')
        
        # Skip empty content messages (like handoff messages with empty content)
        if not content or content.strip() == "":
            continue
            
        # Skip transfer/handoff messages that are just internal coordination
        if content.startswith("Transferring from") and "to" in content:
            continue
        
        if role == 'user':
            context_parts.append(f"User: {content}")
        elif role == 'assistant':
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
        "service": "Flask AutoGen Swarm API with Dappier & Skyfire MCP Integration",
        "framework": "Microsoft AutoGen with Swarm Pattern",
        "model": "gpt-4o",
        "architecture": "Swarm with Planning, Dappier, Skyfire, and General agents",
        "session_management": {
            "enabled": True,
            "active_sessions": len(session_swarms),
            "max_sessions": SESSION_CONFIG['max_sessions'],
            "session_timeout": SESSION_CONFIG['session_timeout']
        },
        "mcp_servers": {
            "dappier": "https://mcp.dappier.com/mcp",
            "skyfire": "https://mcp.skyfire.xyz/mcp"
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
        
        # Create session swarm immediately - always create new, never reuse
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            session_swarm = loop.run_until_complete(create_new_session_swarm(session_id))
            
            return jsonify({
                "status": "success",
                "message": "Session initialized successfully with Swarm architecture",
                "session_id": session_id,
                "initialization_status": initialization_status,
                "session_info": {
                    "created_at": datetime.now().isoformat(),
                    "swarm_ready": True,
                    "agents": ["planning_agent", "dappier_agent", "skyfire_agent"]
                }
            })
            
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Failed to create session swarm: {str(e)}",
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
        "initialization_status": initialization_status,
        "swarm_architecture": {
            "agents": [
                {"name": "planning_agent", "role": "orchestrator and general assistance"},
                {"name": "dappier_agent", "role": "real-time information"},
                {"name": "skyfire_agent", "role": "network operations"}
            ]
        }
    })

@app.route('/sessions/clear', methods=['POST'])
def clear_sessions():
    """Clear all cached sessions to force recreation with updated configuration"""
    try:
        clear_session_cache()
        return jsonify({
            "status": "success",
            "message": "All sessions cleared successfully. New sessions will use updated configuration."
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to clear sessions: {str(e)}"
        }), 500

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
        
        # Create session swarm
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            session_swarm = loop.run_until_complete(get_or_create_session_swarm(session_id))
            
            return jsonify({
                "status": "success",
                "message": "New session created successfully with Swarm",
                "session_id": session_id,
                "session_info": {
                    "created_at": datetime.now().isoformat(),
                    "swarm_ready": True,
                    "agents": ["planning_agent", "dappier_agent", "skyfire_agent"]
                }
            })
            
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Failed to create session swarm: {str(e)}"
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
    global session_swarms, session_metadata
    
    # Clean up expired sessions before reporting
    cleanup_expired_sessions()
    
    sessions_info = []
    for session_id, metadata in session_metadata.items():
        sessions_info.append({
            "session_id": session_id,
            "created_at": datetime.fromtimestamp(metadata['created_at']).isoformat(),
            "last_activity": datetime.fromtimestamp(metadata['last_activity']).isoformat(),
            "message_count": metadata['message_count'],
            "has_swarm": session_id in session_swarms
        })
    
    return jsonify({
        "status": "success",
        "active_sessions": len(session_swarms),
        "max_sessions": SESSION_CONFIG['max_sessions'],
        "session_timeout": SESSION_CONFIG['session_timeout'],
        "sessions": sessions_info
    })

@app.route('/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """Delete a specific session"""
    global session_swarms, session_metadata
    
    if session_id in session_swarms:
        del session_swarms[session_id]
    
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
        "active_sessions": len(session_swarms)
    })

@app.route('/chat', methods=['POST'])
def chat_completion():
    """Chat completion endpoint that uses AutoGen Swarm with streaming and session management"""
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
        
        # Use streaming with session-based swarm
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
    """Generate streaming response using session-specific AutoGen Swarm with conversation history"""
    try:
        # Session ID is required
        if not session_id:
            yield f"data: {json.dumps({'error': 'Session ID is required', 'type': 'error'})}\n\n"
            return
        
        # Get session-specific swarm
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            session_swarm = loop.run_until_complete(get_or_create_session_swarm(session_id))
        except Exception as e:
            yield f"data: {json.dumps({'error': f'Failed to get session swarm: {str(e)}', 'type': 'error'})}\n\n"
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
                # Use the session-specific swarm
                async for chunk in session_swarm.run_stream(task=conversation_context):
                    # Handle HandoffMessage - inform UI about agent handoffs
                    if hasattr(chunk, 'type') and chunk.type == 'HandoffMessage':
                        if hasattr(chunk, 'source') and hasattr(chunk, 'target'):
                            yield f"data: {json.dumps({'type': 'handoff', 'from': chunk.source, 'to': chunk.target, 'content': getattr(chunk, 'content', '')})}\n\n"
                    
                    # Handle tool call requests - inform UI which tool is being called
                    elif hasattr(chunk, 'type') and chunk.type == 'ToolCallRequestEvent':
                        if hasattr(chunk, 'content'):
                            # Iterate over all items in chunk.content
                            for item in _iter_items(chunk.content):
                                try:
                                    tool_name, tool_args = _extract_name_and_args(item)
                                    if tool_name:
                                        # Skip handoff tools (transfer_to_X)
                                        if not tool_name.startswith('transfer_to_'):
                                            display_name = TOOL_DISPLAY_NAMES.get(tool_name, tool_name)
                                            payload = {
                                                'tool_name': tool_name,
                                                'tool_display_name': display_name,
                                                'type': 'tool_call',
                                                'status': 'calling',
                                                'agent': getattr(chunk, 'source', 'unknown')
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
                                    # Extract tool name from FunctionExecutionResult
                                    tool_name = None
                                    
                                    # Check if this is a FunctionExecutionResult with a name attribute
                                    if hasattr(item, 'name') and hasattr(item, 'call_id'):
                                        tool_name = item.name
                                    else:
                                        # Fallback to the original extraction method
                                        tool_name, tool_args = _extract_name_and_args(item)
                                    
                                    # Send completion status for actual tools (not handoffs)
                                    if tool_name and not tool_name.startswith('transfer_to_'):
                                        display_name = TOOL_DISPLAY_NAMES.get(tool_name, tool_name)
                                        
                                        # Extract tool output/result
                                        tool_output = None
                                        if hasattr(item, 'content'):
                                            tool_output = item.content
                                        elif hasattr(item, 'result'):
                                            tool_output = item.result
                                        
                                        payload = {
                                            'tool_name': tool_name,
                                            'tool_display_name': display_name,
                                            'type': 'tool_call',
                                            'status': 'completed',
                                            'agent': getattr(chunk, 'source', 'unknown'),
                                            'output': tool_output,
                                        }
                                        # Include arguments when available
                                        if tool_args is not None:
                                            payload['arguments'] = tool_args
                                        yield f"data: {json.dumps(payload)}\n\n"
                                except Exception as e:
                                    print(f"Error processing tool execution event: {e}")
                                    pass
                    
                    # Handle ModelClientStreamingChunkEvent for token-level streaming
                    elif hasattr(chunk, 'type') and chunk.type == 'ModelClientStreamingChunkEvent':
                        if hasattr(chunk, 'content') and chunk.content:
                            agent_source = getattr(chunk, 'source', 'unknown')
                            yield f"data: {json.dumps({'content': chunk.content, 'type': 'token', 'agent': agent_source})}\n\n"
                    
                    # Handle TextMessage (complete messages)
                    elif hasattr(chunk, 'type') and chunk.type == 'TextMessage':
                        if hasattr(chunk, 'source'):
                            # Get the agent source
                            agent_source = chunk.source
                            if hasattr(chunk, 'content') and chunk.content:
                                # Don't stream handoff messages or internal tool messages
                                if not chunk.content.startswith('Transferred to'):
                                    yield f"data: {json.dumps({'content': chunk.content, 'type': 'message', 'agent': agent_source})}\n\n"
                    
                    # Handle TaskResult (final result)
                    elif hasattr(chunk, 'messages'):
                        # This is the final TaskResult - we can extract termination reason
                        if hasattr(chunk, 'stop_reason'):
                            yield f"data: {json.dumps({'type': 'completion', 'stop_reason': chunk.stop_reason})}\n\n"
            
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
    print("Starting Flask AutoGen Swarm API with Dappier & Skyfire MCP Integration")
    print("Server will be available at: http://localhost:5000")
    print("Architecture: Swarm pattern with Planning, Dappier, Skyfire, and General agents")
    app.run(host='0.0.0.0', port=5000, debug=True)
