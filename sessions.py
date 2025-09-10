import asyncio
import uuid
from datetime import datetime
from flask import Blueprint, jsonify
from utils import (
    session_agents, session_metadata, initialization_status, SESSION_CONFIG,
    cached_tools, create_session_agent
)

# Create Blueprint for session endpoints
sessions_bp = Blueprint('sessions', __name__)

def generate_session_id():
    """Generate a unique session ID"""
    return f"sess_{uuid.uuid4().hex[:16]}"

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

@sessions_bp.route('/sessions/new', methods=['POST'])
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

@sessions_bp.route('/sessions', methods=['GET'])
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

@sessions_bp.route('/sessions/<session_id>', methods=['DELETE'])
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

@sessions_bp.route('/sessions/cleanup', methods=['POST'])
def cleanup_sessions():
    """Manually trigger session cleanup"""
    cleaned_count = cleanup_expired_sessions()
    
    return jsonify({
        "status": "success",
        "message": f"Cleaned up {cleaned_count} expired sessions",
        "active_sessions": len(session_agents)
    })