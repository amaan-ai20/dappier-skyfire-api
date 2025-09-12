"""
Session management endpoints
"""
import asyncio
from datetime import datetime
from flask import Blueprint, jsonify
from services.mcp_service import get_initialization_status
from services.session_service import (
    create_new_session_swarm, 
    get_or_create_session_swarm,
    get_session_info,
    delete_session as delete_session_service,
    cleanup_expired_sessions,
    clear_session_cache
)
from utils.helpers import generate_session_id, filter_initialization_status_for_client

sessions_bp = Blueprint('sessions', __name__)


@sessions_bp.route('/sessions/clear', methods=['POST'])
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


@sessions_bp.route('/sessions/new', methods=['POST'])
def create_new_session():
    """Create a new session (requires system to be initialized)"""
    initialization_status = get_initialization_status()
    
    # Check if system is initialized
    if not initialization_status["initialized"]:
        return jsonify({
            "status": "error",
            "message": "System not initialized. Please call /initialize endpoint first.",
            "initialization_status": filter_initialization_status_for_client(initialization_status)
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


@sessions_bp.route('/sessions', methods=['GET'])
def get_sessions():
    """Get information about active sessions"""
    session_info = get_session_info()
    
    return jsonify({
        "status": "success",
        **session_info
    })


@sessions_bp.route('/sessions/<session_id>', methods=['DELETE'])
def delete_session_endpoint(session_id):
    """Delete a specific session"""
    success = delete_session_service(session_id)
    
    if success:
        return jsonify({
            "status": "success",
            "message": f"Session {session_id} deleted successfully"
        })
    else:
        return jsonify({
            "status": "error",
            "message": f"Failed to delete session {session_id}"
        }), 500


@sessions_bp.route('/sessions/cleanup', methods=['POST'])
def cleanup_sessions():
    """Manually trigger session cleanup"""
    cleaned_count = cleanup_expired_sessions()
    
    return jsonify({
        "status": "success",
        "message": f"Cleaned up {cleaned_count} expired sessions",
        "active_sessions": get_session_info()["active_sessions"]
    })