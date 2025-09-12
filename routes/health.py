"""
Health check and status endpoints
"""
from flask import Blueprint, jsonify
from services.mcp_service import get_initialization_status
from services.session_service import get_session_info
from config.settings import SESSION_CONFIG, MCP_SERVERS

health_bp = Blueprint('health', __name__)


@health_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    session_info = get_session_info()
    
    return jsonify({
        "status": "healthy", 
        "service": "Flask AutoGen Swarm API with Dappier & Skyfire MCP Integration",
        "framework": "Microsoft AutoGen with Swarm Pattern",
        "model": "gpt-4o",
        "architecture": "Swarm with Planning, Dappier, Skyfire, and General agents",
        "session_management": {
            "enabled": True,
            "active_sessions": session_info["active_sessions"],
            "max_sessions": SESSION_CONFIG['max_sessions'],
            "session_timeout": SESSION_CONFIG['session_timeout']
        },
        "mcp_servers": {
            "dappier": MCP_SERVERS["dappier"]["url"],
            "skyfire": MCP_SERVERS["skyfire"]["url"]
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


@health_bp.route('/status', methods=['GET'])
def get_status():
    """Get current initialization status"""
    initialization_status = get_initialization_status()
    
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