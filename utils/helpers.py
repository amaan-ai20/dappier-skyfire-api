"""
Utility functions for the Dappier-Skyfire API
"""
import json
import uuid
from datetime import datetime


def generate_session_id():
    """Generate a unique session ID"""
    return f"sess_{uuid.uuid4().hex[:16]}"


def _iter_items(content):
    """Safely iterate over content that might be a list or single item"""
    if isinstance(content, list):
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