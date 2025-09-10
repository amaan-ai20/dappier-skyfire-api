import asyncio
import json
import re
from flask import Blueprint, request, jsonify, Response, stream_with_context
from utils import (
    initialization_status, TOOL_DISPLAY_NAMES
)
from sessions import get_or_create_session_agent

# Create Blueprint for chat endpoint
chat_bp = Blueprint('chat', __name__)

def _iter_items(content):
    """Normalize content to a list for iteration"""
    if content is None:
        return []
    if isinstance(content, (list, tuple)):
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
    
    # Strategy 3: String representation parsing
    try:
        item_str = str(item)
        if 'name=' in item_str:
            # Try to extract name from string representation
            name_match = re.search(r"name='([^']*)'", item_str)
            if name_match:
                name = name_match.group(1)
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
        role = msg.get('role', msg.get('type', 'user'))  # Support both 'role' and 'type' fields
        content = msg.get('content', '')
        
        if role == 'user':
            context_parts.append(f"User: {content}")
        elif role in ['assistant', 'ai']:
            context_parts.append(f"Assistant: {content}")
    
    # Add current message
    context_parts.append(f"\nCurrent user message: {current_message}")
    context_parts.append("\nPlease respond to the current user message, taking into account the conversation history above.")
    
    return "\n".join(context_parts)

@chat_bp.route('/chat', methods=['POST'])
def chat_completion():
    """Chat completion endpoint that uses AutoGen with streaming and session management"""
    try:
        # Check if MCP connections are initialized
        if not initialization_status["initialized"]:
            return jsonify({
                "error": "System not initialized. Please call /initialize endpoint first.",
                "initialization_status": initialization_status
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
            stream_with_context(generate_streaming_response(message, messages_history, session_id)),
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

def generate_streaming_response(message, messages_history=None, session_id=None):
    """Generate streaming response using session-specific AutoGen agent with conversation history"""
    try:
        # Session ID is required
        if not session_id:
            yield f"data: {json.dumps({'error': 'Session ID is required', 'type': 'error'})}\n\n"
            return
        
        # Get session-specific agent
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            session_agent = loop.run_until_complete(get_or_create_session_agent(session_id))
        except Exception as e:
            yield f"data: {json.dumps({'error': f'Failed to get session agent: {str(e)}', 'type': 'error'})}\n\n"
            return
        finally:
            loop.close()
        
        # Build conversation context from history
        conversation_context = build_conversation_context(message, messages_history)
        
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Define async function to stream messages
            async def stream_messages():
                # Use the session-specific agent
                async for chunk in session_agent.run_stream(task=conversation_context):
                    # Handle tool call requests - inform UI which tool is being called
                    if hasattr(chunk, 'type') and chunk.type == 'ToolCallRequestEvent':
                        if hasattr(chunk, 'content'):
                            # Iterate over all items in chunk.content
                            for item in _iter_items(chunk.content):
                                try:
                                    tool_name, tool_args = _extract_name_and_args(item)
                                    if tool_name:
                                        display_name = TOOL_DISPLAY_NAMES.get(tool_name, tool_name)
                                        payload = {
                                            'tool_name': tool_name,
                                            'tool_display_name': display_name,
                                            'type': 'tool_call',
                                            'status': 'calling'
                                        }
                                        # Include arguments when available
                                        if tool_args is not None:
                                            payload['arguments'] = tool_args
                                        yield f"data: {json.dumps(payload)}\n\n"
                                except Exception as e:
                                    pass
                    
                    # Handle tool execution results - inform UI that tool finished
                    elif hasattr(chunk, 'type') and chunk.type == 'ToolCallExecutionEvent':
                        if hasattr(chunk, 'content'):
                            # Iterate over all items in chunk.content
                            for item in _iter_items(chunk.content):
                                try:
                                    tool_name, tool_args = _extract_name_and_args(item)
                                    if tool_name:
                                        display_name = TOOL_DISPLAY_NAMES.get(tool_name, tool_name)
                                        payload = {
                                            'tool_name': tool_name,
                                            'tool_display_name': display_name,
                                            'type': 'tool_call',
                                            'status': 'completed'
                                        }
                                        yield f"data: {json.dumps(payload)}\n\n"
                                except Exception as e:
                                    pass
                    
                    # Handle ModelClientStreamingChunkEvent for token-level streaming
                    elif hasattr(chunk, 'type') and chunk.type == 'ModelClientStreamingChunkEvent':
                        if hasattr(chunk, 'content') and chunk.content:
                            yield f"data: {json.dumps({'content': chunk.content, 'type': 'token'})}\n\n"
                    
                    # Handle TextMessage (complete messages)
                    elif hasattr(chunk, 'type') and chunk.type == 'TextMessage':
                        if hasattr(chunk, 'source') and chunk.source == 'chat_assistant':
                            if hasattr(chunk, 'content') and chunk.content:
                                yield f"data: {json.dumps({'content': chunk.content, 'type': 'message'})}\n\n"
                    
                    # Handle TaskResult (final result)
                    elif hasattr(chunk, 'messages'):
                        # This is the final TaskResult - we can ignore it since we already streamed the content
                        pass
                    
                    # Handle ToolCallSummaryMessage - but extract only the processed response
                    elif hasattr(chunk, 'type') and chunk.type == 'ToolCallSummaryMessage':
                        # This might contain the LLM's processed response after using tools
                        # Let's check if there's useful content here
                        if hasattr(chunk, 'content') and chunk.content:
                            pass
                    
                    # Handle any other chunk types
                    else:
                        pass
            
            # Create async function to handle the streaming
            async def run_streaming():
                async for data in stream_messages():
                    yield data
                # Send completion signal
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
            # Run the async generator in the event loop
            async_gen = run_streaming()
            try:
                while True:
                    data = loop.run_until_complete(async_gen.__anext__())
                    yield data
            except StopAsyncIteration:
                pass
            
        finally:
            loop.close()
            
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e), 'type': 'error'})}\n\n"