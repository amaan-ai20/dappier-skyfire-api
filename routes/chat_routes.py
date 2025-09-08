import asyncio
from flask import Blueprint, request, jsonify, Response, stream_with_context
from services.chat_service import ChatService
from services.session_service import SessionService
from services.mcp_service import MCPService

# Create blueprint for chat routes
chat_bp = Blueprint('chat', __name__)

# Initialize services (these will be injected when the blueprint is registered)
chat_service = None
session_manager = None
mcp_client = None


def init_chat_routes(chat_svc: ChatService, session_mgr: SessionService, mcp_cli: MCPService):
    """Initialize the chat routes with required services"""
    global chat_service, session_manager, mcp_client
    chat_service = chat_svc
    session_manager = session_mgr
    mcp_client = mcp_cli


@chat_bp.route('/chat', methods=['POST'])
def chat_completion():
    """Chat completion endpoint that uses AutoGen with streaming and session management"""
    try:
        # Check if MCP connections are initialized
        if not mcp_client.is_initialized():
            return jsonify({
                "error": "System not initialized. Please call /initialize endpoint first.",
                "initialization_status": mcp_client.get_initialization_status()
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
            stream_with_context(
                chat_service.generate_streaming_response(message, messages_history, session_id)
            ),
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


@chat_bp.route('/initialize', methods=['POST'])
def initialize():
    """Initialize MCP server connections and create a new session"""
    try:
        # Initialize MCP connections if not already done
        if not mcp_client.is_initialized() and not mcp_client.is_initializing():
            # Clear cached tools for fresh initialization
            mcp_client.clear_tool_cache()
            
            # Reset status for fresh initialization
            mcp_client.reset_initialization_status()
            
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Run MCP initialization
                success = loop.run_until_complete(mcp_client.initialize_mcp_connections())
                
                if not success:
                    return jsonify({
                        "status": "error",
                        "message": "Failed to initialize MCP connections",
                        "initialization_status": mcp_client.get_initialization_status()
                    }), 500
                    
            finally:
                loop.close()
        
        # Wait for initialization to complete if in progress
        elif mcp_client.is_initializing():
            # In a real application, you might want to implement proper waiting
            # For now, return that initialization is in progress
            return jsonify({
                "status": "initializing",
                "message": "Initialization is in progress. Please try again in a moment.",
                "initialization_status": mcp_client.get_initialization_status()
            }), 202
        
        # Check if initialization was successful
        if not mcp_client.is_initialized():
            return jsonify({
                "status": "error",
                "message": "System initialization failed",
                "initialization_status": mcp_client.get_initialization_status()
            }), 500
        
        # Generate a new session ID
        session_id = session_manager.create_session()
        
        # Create session agent immediately
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            session_agent = loop.run_until_complete(chat_service.get_or_create_session_agent(session_id))
            
            return jsonify({
                "status": "success",
                "message": "Session initialized successfully",
                "session_id": session_id,
                "initialization_status": mcp_client.get_initialization_status(),
                "session_info": session_manager.get_session_info(session_id)
            })
            
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Failed to create session agent: {str(e)}",
                "initialization_status": mcp_client.get_initialization_status()
            }), 500
            
        finally:
            loop.close()
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Initialization failed: {str(e)}",
            "initialization_status": mcp_client.get_initialization_status()
        }), 500


@chat_bp.route('/status', methods=['GET'])
def get_status():
    """Get current initialization status"""
    return jsonify({
        "status": "success",
        "initialization_status": mcp_client.get_initialization_status()
    })