"""
Session management service for handling user sessions and swarms
"""
import time
from datetime import datetime
from config.settings import SESSION_CONFIG
from agents.swarm_factory import create_session_swarm


# Session-based swarm management
session_swarms = {}  # Dictionary to store session-specific swarms
session_metadata = {}  # Store session metadata


def clear_session_cache():
    """Clear all cached sessions to force recreation with updated configuration"""
    global session_swarms, session_metadata
    session_swarms.clear()
    session_metadata.clear()
    print("Cleared all session caches - new sessions will use updated configuration")


def cleanup_expired_sessions():
    """Clean up expired sessions based on timeout"""
    global session_swarms, session_metadata
    
    current_time = time.time()
    expired_sessions = []
    
    for session_id, metadata in session_metadata.items():
        if current_time - metadata['last_activity'] > SESSION_CONFIG['session_timeout']:
            expired_sessions.append(session_id)
    
    # Remove expired sessions
    for session_id in expired_sessions:
        if session_id in session_swarms:
            del session_swarms[session_id]
        if session_id in session_metadata:
            del session_metadata[session_id]
    
    if expired_sessions:
        print(f"Cleaned up {len(expired_sessions)} expired sessions")
    
    return len(expired_sessions)


async def get_or_create_session_swarm(session_id):
    """Get existing session swarm or create a new one"""
    global session_swarms, session_metadata
    
    # Clean up expired sessions first
    cleanup_expired_sessions()
    
    # Check if we've reached the maximum number of sessions
    if len(session_swarms) >= SESSION_CONFIG['max_sessions'] and session_id not in session_swarms:
        # Remove the oldest session to make room
        oldest_session = min(session_metadata.items(), key=lambda x: x[1]['last_activity'])
        oldest_session_id = oldest_session[0]
        if oldest_session_id in session_swarms:
            del session_swarms[oldest_session_id]
        if oldest_session_id in session_metadata:
            del session_metadata[oldest_session_id]
        print(f"Removed oldest session {oldest_session_id} to make room for new session")
    
    # Update session metadata
    current_time = time.time()
    if session_id not in session_metadata:
        session_metadata[session_id] = {
            'created_at': current_time,
            'last_activity': current_time,
            'message_count': 0
        }
    else:
        session_metadata[session_id]['last_activity'] = current_time
        session_metadata[session_id]['message_count'] += 1
    
    # Create new swarm if it doesn't exist
    if session_id not in session_swarms:
        print(f"Creating new swarm for session: {session_id}")
        session_swarm = await create_session_swarm()
        session_swarms[session_id] = session_swarm
        print(f"Session swarm created successfully for session: {session_id}")
    
    return session_swarms[session_id]


async def create_new_session_swarm(session_id):
    """Create a new session swarm (always creates new, never reuses)"""
    global session_swarms, session_metadata
    
    # Clean up expired sessions first
    cleanup_expired_sessions()
    
    # Check if we've reached the maximum number of sessions
    if len(session_swarms) >= SESSION_CONFIG['max_sessions']:
        # Remove the oldest session to make room
        oldest_session = min(session_metadata.items(), key=lambda x: x[1]['last_activity'])
        oldest_session_id = oldest_session[0]
        if oldest_session_id in session_swarms:
            del session_swarms[oldest_session_id]
        if oldest_session_id in session_metadata:
            del session_metadata[oldest_session_id]
        print(f"Removed oldest session {oldest_session_id} to make room for new session")
    
    # Create session metadata
    current_time = time.time()
    session_metadata[session_id] = {
        'created_at': current_time,
        'last_activity': current_time,
        'message_count': 0
    }
    
    # Always create a new swarm
    print(f"Creating new swarm for session: {session_id}")
    session_swarm = await create_session_swarm()
    session_swarms[session_id] = session_swarm
    print(f"Session swarm created successfully for session: {session_id}")
    
    return session_swarm


def get_session_info():
    """Get information about active sessions"""
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
    
    return {
        "active_sessions": len(session_swarms),
        "max_sessions": SESSION_CONFIG['max_sessions'],
        "session_timeout": SESSION_CONFIG['session_timeout'],
        "sessions": sessions_info
    }


def delete_session(session_id):
    """Delete a specific session"""
    global session_swarms, session_metadata
    
    if session_id in session_swarms:
        del session_swarms[session_id]
    
    if session_id in session_metadata:
        del session_metadata[session_id]
    
    return True