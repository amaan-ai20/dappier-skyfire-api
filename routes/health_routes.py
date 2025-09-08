from flask import Blueprint, jsonify
from services.session_service import SessionService
from services.mcp_service import MCPService
from config.config import APP_INFO, SESSION_CONFIG, MCP_CONFIG

# Create blueprint for health and system info routes
health_bp = Blueprint('health', __name__)

# Initialize services (these will be injected when the blueprint is registered)
session_manager = None
mcp_client = None


def init_health_routes(session_mgr: SessionService, mcp_cli: MCPService):
    """Initialize the health routes with required services"""
    global session_manager, mcp_client
    session_manager = session_mgr
    mcp_client = mcp_cli


@health_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy", 
        "service": APP_INFO["name"],
        "framework": APP_INFO["framework"],
        "version": APP_INFO["version"],
        "description": APP_INFO["description"],
        "model": "gpt-4o",
        "session_management": {
            "enabled": True,
            "active_sessions": session_manager.get_session_count() if session_manager else 0,
            "max_sessions": SESSION_CONFIG['max_sessions'],
            "session_timeout": SESSION_CONFIG['session_timeout']
        },
        "mcp_servers": {
            "dappier": MCP_CONFIG["dappier"]["url"],
            "skyfire": MCP_CONFIG["skyfire"]["url"]
        },
        "initialization": {
            "initialized": mcp_client.is_initialized() if mcp_client else False,
            "initializing": mcp_client.is_initializing() if mcp_client else False
        },
        "endpoints": {
            "initialize": "/initialize (POST - creates first session)",
            "new_session": "/sessions/new (POST - creates additional session)",
            "chat": "/chat (POST - requires session_id)",
            "sessions": "/sessions (GET - list sessions)",
            "session_get": "/sessions/<session_id> (GET)",
            "session_delete": "/sessions/<session_id> (DELETE)",
            "session_cleanup": "/sessions/cleanup (POST)",
            "session_stats": "/sessions/stats (GET)",
            "status": "/status (GET - initialization status)",
            "health": "/health (GET - this endpoint)"
        }
    })


@health_bp.route('/info', methods=['GET'])
def system_info():
    """Get detailed system information"""
    system_info = {
        "application": APP_INFO,
        "initialization_status": mcp_client.get_initialization_status() if mcp_client else None,
        "session_stats": session_manager.get_session_stats() if session_manager else None,
        "configuration": {
            "session_config": SESSION_CONFIG,
            "mcp_config": {
                "dappier_url": MCP_CONFIG["dappier"]["url"],
                "skyfire_url": MCP_CONFIG["skyfire"]["url"],
                "skyfire_requires_key": MCP_CONFIG["skyfire"]["requires_api_key"]
            }
        }
    }
    
    return jsonify({
        "status": "success",
        "system_info": system_info
    })


@health_bp.route('/tools', methods=['GET'])
def get_tools_info():
    """Get information about available tools"""
    if not mcp_client:
        return jsonify({
            "status": "error",
            "message": "MCP client not initialized"
        }), 500
    
    initialization_status = mcp_client.get_initialization_status()
    
    tools_info = {
        "total_tools": mcp_client.get_tool_count(),
        "dappier": {
            "status": initialization_status["dappier"]["status"],
            "count": initialization_status["dappier"]["count"],
            "tools": initialization_status["dappier"]["tools"],
            "error": initialization_status["dappier"]["error"]
        },
        "skyfire": {
            "status": initialization_status["skyfire"]["status"],
            "count": initialization_status["skyfire"]["count"],
            "tools": initialization_status["skyfire"]["tools"],
            "error": initialization_status["skyfire"]["error"]
        },
        "initialized": initialization_status["initialized"],
        "initialized_at": initialization_status["initialized_at"]
    }
    
    return jsonify({
        "status": "success",
        "tools_info": tools_info
    })