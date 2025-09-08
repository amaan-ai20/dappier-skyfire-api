import asyncio
from flask import Blueprint, jsonify
from datetime import datetime
from services.chat_service import ChatService
from services.session_service import SessionService
from services.mcp_service import MCPService

# Create blueprint for session routes
session_bp = Blueprint('session', __name__)

# Initialize services (these will be injected when the blueprint is registered)
chat_service = None
session_manager = None
mcp_client = None


def init_session_routes(chat_svc: ChatService, session_mgr: SessionService, mcp_cli: MCPService):
    """Initialize the session routes with required services"""
    global chat_service, session_manager, mcp_client
    chat_service = chat_svc
    session_manager = session_mgr
    mcp_client = mcp_cli


@session_bp.route('/sessions/new', methods=['POST'])
def create_new_session():
    """Create a new session (requires system to be initialized)"""
    # Check if system is initialized
    if not mcp_client.is_initialized():
        return jsonify({
            "status": "error",
            "message": "System not initialized. Please call /initialize endpoint first.",
            "initialization_status": mcp_client.get_initialization_status()
        }), 400
    
    try:
        # Generate a new session ID
        session_id = session_manager.create_session()
        
        # Create session agent
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            session_agent = loop.run_until_complete(chat_service.get_or_create_session_agent(session_id))
            
            return jsonify({
                "status": "success",
                "message": "New session created successfully",
                "session_id": session_id,
                "session_info": session_manager.get_session_info(session_id)
            })
            
        except Exception as e:
            # Clean up session if agent creation failed
            session_manager.delete_session(session_id)
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


@session_bp.route('/sessions', methods=['GET'])
def get_sessions():
    """Get information about active sessions"""
    # Get sessions info and stats
    sessions_info = session_manager.get_all_sessions_info()
    session_stats = session_manager.get_session_stats()
    
    return jsonify({
        "status": "success",
        **session_stats,
        "sessions": sessions_info
    })


@session_bp.route('/sessions/<session_id>', methods=['GET'])
def get_session(session_id):
    """Get information about a specific session"""
    session_info = session_manager.get_session_info(session_id)
    
    if session_info is None:
        return jsonify({
            "status": "error",
            "message": f"Session {session_id} not found"
        }), 404
    
    return jsonify({
        "status": "success",
        "session": session_info
    })


@session_bp.route('/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """Delete a specific session"""
    deleted = session_manager.delete_session(session_id)
    
    if deleted:
        return jsonify({
            "status": "success",
            "message": f"Session {session_id} deleted successfully"
        })
    else:
        return jsonify({
            "status": "error",
            "message": f"Session {session_id} not found"
        }), 404


@session_bp.route('/sessions/cleanup', methods=['POST'])
def cleanup_sessions():
    """Manually trigger session cleanup"""
    cleaned_count = session_manager.cleanup_expired_sessions()
    
    return jsonify({
        "status": "success",
        "message": f"Cleaned up {cleaned_count} expired sessions",
        "active_sessions": session_manager.get_session_count(),
        "session_stats": session_manager.get_session_stats()
    })


@session_bp.route('/sessions/stats', methods=['GET'])
def get_session_stats():
    """Get session statistics"""
    stats = session_manager.get_session_stats()
    
    return jsonify({
        "status": "success",
        "stats": stats,
        "timestamp": datetime.now().isoformat()
    })