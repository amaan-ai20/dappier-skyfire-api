"""
Initialization endpoints for MCP connections and sessions

DEMONSTRATION NOTE:
This endpoint establishes real connections to both Skyfire and Dappier MCP servers.
The initialization process is fully functional and includes:
- Actual MCP server connections using real API keys
- Real tool discovery and caching from both services
- Production-ready error handling and status tracking

The connections established here are genuine - the application communicates with:
- Skyfire MCP Server: Real production endpoint for payment and authentication tools
- Dappier MCP Server: Real production endpoint for data retrieval tools

Only the pricing data returned by one specific tool is mocked for demonstration consistency.

IMPORTANT DEMONSTRATION DETAIL:
The Dappier MCP server connection is established using Dappier's API key directly,
not through Skyfire tokens as shown in the demo UI. However, the payment/charging
for Dappier service usage is processed through Skyfire's payment infrastructure.
This demonstrates Skyfire's role as a payment layer for third-party services.
"""
import asyncio
from datetime import datetime
from flask import Blueprint, jsonify
from services.mcp_service import initialize_mcp_connections, get_initialization_status, clear_tool_cache
from services.session_service import create_new_session_swarm
from utils.helpers import generate_session_id, filter_initialization_status_for_client

init_bp = Blueprint('initialization', __name__)


@init_bp.route('/initialize', methods=['POST'])
def initialize():
    """Initialize MCP server connections and create a new session"""
    initialization_status = get_initialization_status()
    
    try:
        # Initialize MCP connections if not already done
        if not initialization_status["initialized"] and not initialization_status["initializing"]:
            # Clear cached tools for fresh initialization
            clear_tool_cache()
            
            # Reset status for fresh initialization
            initialization_status.update({
                "initialized": False,
                "initializing": True,
                "error": None,
                "dappier": {"status": "not_connected", "tools": [], "error": None},
                "skyfire": {"status": "not_connected", "tools": [], "error": None},
                "total_tools": 0,
                "initialized_at": None
            })
            
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
                        "initialization_status": filter_initialization_status_for_client(get_initialization_status())
                    }), 500
                    
            finally:
                loop.close()
        
        # Wait for initialization to complete if in progress
        elif initialization_status["initializing"]:
            return jsonify({
                "status": "initializing",
                "message": "Initialization is in progress. Please try again in a moment.",
                "initialization_status": filter_initialization_status_for_client(initialization_status)
            }), 202
        
        # Check if initialization was successful
        if not initialization_status["initialized"]:
            return jsonify({
                "status": "error",
                "message": "System initialization failed",
                "initialization_status": filter_initialization_status_for_client(initialization_status)
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
                "initialization_status": filter_initialization_status_for_client(get_initialization_status()),
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
                "initialization_status": filter_initialization_status_for_client(get_initialization_status())
            }), 500
            
        finally:
            loop.close()
            
    except Exception as e:
        # Update initialization status on error
        init_status = get_initialization_status()
        init_status.update({
            "initialized": False,
            "initializing": False,
            "error": str(e)
        })
        
        return jsonify({
            "status": "error",
            "message": f"Initialization failed: {str(e)}",
            "initialization_status": filter_initialization_status_for_client(init_status)
        }), 500