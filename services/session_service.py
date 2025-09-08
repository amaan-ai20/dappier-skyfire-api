import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from config.config import SESSION_CONFIG


class SessionService:
    """Manages user sessions and their associated agents"""
    
    def __init__(self):
        self.session_agents: Dict[str, Any] = {}  # Dictionary to store session-specific agents
        self.session_metadata: Dict[str, Dict] = {}  # Store session metadata
    
    def generate_session_id(self) -> str:
        """Generate a unique session ID"""
        return f"sess_{uuid.uuid4().hex[:16]}"
    
    def create_session(self) -> str:
        """Create a new session and return its ID"""
        # Clean up expired sessions
        self.cleanup_expired_sessions()
        
        # Check if we've reached the maximum number of sessions
        if len(self.session_agents) >= SESSION_CONFIG['max_sessions']:
            # Remove the oldest session
            oldest_session = min(
                self.session_metadata.keys(), 
                key=lambda k: self.session_metadata[k]['last_activity']
            )
            self.delete_session(oldest_session)
            print(f"Removed oldest session to make room: {oldest_session}")
        
        # Generate new session ID
        session_id = self.generate_session_id()
        
        # Initialize session metadata
        current_time = datetime.now().timestamp()
        self.session_metadata[session_id] = {
            'created_at': current_time,
            'last_activity': current_time,
            'message_count': 0
        }
        
        return session_id
    
    def has_session(self, session_id: str) -> bool:
        """Check if session exists"""
        return session_id in self.session_metadata
    
    def has_agent(self, session_id: str) -> bool:
        """Check if session has an associated agent"""
        return session_id in self.session_agents
    
    def get_agent(self, session_id: str) -> Optional[Any]:
        """Get agent for a session"""
        return self.session_agents.get(session_id)
    
    def set_agent(self, session_id: str, agent: Any) -> None:
        """Set agent for a session"""
        self.session_agents[session_id] = agent
    
    def update_session_activity(self, session_id: str) -> None:
        """Update session activity timestamp and message count"""
        current_time = datetime.now().timestamp()
        
        if session_id not in self.session_metadata:
            # Create session metadata if it doesn't exist
            self.session_metadata[session_id] = {
                'created_at': current_time,
                'last_activity': current_time,
                'message_count': 0
            }
        else:
            # Update existing session
            self.session_metadata[session_id]['last_activity'] = current_time
            self.session_metadata[session_id]['message_count'] += 1
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session and its associated agent"""
        deleted = False
        
        if session_id in self.session_agents:
            del self.session_agents[session_id]
            deleted = True
        
        if session_id in self.session_metadata:
            del self.session_metadata[session_id]
            deleted = True
        
        return deleted
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions and return count of cleaned sessions"""
        current_time = datetime.now().timestamp()
        
        expired_sessions = []
        for session_id, metadata in self.session_metadata.items():
            if current_time - metadata['last_activity'] > SESSION_CONFIG['session_timeout']:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            self.delete_session(session_id)
            print(f"Cleaned up expired session: {session_id}")
        
        return len(expired_sessions)
    
    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """Get information about a specific session"""
        if session_id not in self.session_metadata:
            return None
        
        metadata = self.session_metadata[session_id]
        return {
            "session_id": session_id,
            "created_at": datetime.fromtimestamp(metadata['created_at']).isoformat(),
            "last_activity": datetime.fromtimestamp(metadata['last_activity']).isoformat(),
            "message_count": metadata['message_count'],
            "has_agent": session_id in self.session_agents
        }
    
    def get_all_sessions_info(self) -> List[Dict]:
        """Get information about all active sessions"""
        # Clean up expired sessions before reporting
        self.cleanup_expired_sessions()
        
        sessions_info = []
        for session_id in self.session_metadata.keys():
            session_info = self.get_session_info(session_id)
            if session_info:
                sessions_info.append(session_info)
        
        return sessions_info
    
    def get_session_count(self) -> int:
        """Get the number of active sessions"""
        return len(self.session_agents)
    
    def get_session_stats(self) -> Dict:
        """Get session statistics"""
        self.cleanup_expired_sessions()
        
        return {
            "active_sessions": len(self.session_agents),
            "max_sessions": SESSION_CONFIG['max_sessions'],
            "session_timeout": SESSION_CONFIG['session_timeout'],
            "cleanup_interval": SESSION_CONFIG['cleanup_interval']
        }