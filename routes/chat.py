"""
Chat completion endpoint with streaming support
"""
import asyncio
import json
from flask import Blueprint, request, jsonify, Response, stream_with_context
from services.mcp_service import get_initialization_status
from services.session_service import get_or_create_session_swarm
from utils.helpers import build_conversation_context, _iter_items, _extract_name_and_args, filter_initialization_status_for_client
from config.settings import TOOL_DISPLAY_NAMES

chat_bp = Blueprint('chat', __name__)


@chat_bp.route('/chat', methods=['POST'])
def chat_completion():
    """Chat completion endpoint that uses AutoGen Swarm with streaming and session management"""
    try:
        # Check if MCP connections are initialized
        initialization_status = get_initialization_status()
        if not initialization_status["initialized"]:
            return jsonify({
                "error": "System not initialized. Please call /initialize endpoint first.",
                "initialization_status": filter_initialization_status_for_client(initialization_status)
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
        
        # Return streaming response
        return Response(
            stream_with_context(stream_chat_response(session_id, message, messages_history)),
            mimetype='text/plain',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'POST'
            }
        )
        
    except Exception as e:
        return jsonify({"error": f"Request processing failed: {str(e)}"}), 500


def stream_chat_response(session_id, message, messages_history):
    """Generator function for streaming chat responses"""
    try:
        # Get or create session swarm
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            session_swarm = loop.run_until_complete(get_or_create_session_swarm(session_id))
        except Exception as e:
            yield f"data: {json.dumps({'error': f'Failed to get session swarm: {str(e)}', 'type': 'error'})}\n\n"
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
                # Use the session-specific swarm
                async for chunk in session_swarm.run_stream(task=conversation_context):
                    # Handle HandoffMessage - inform UI about agent handoffs
                    if hasattr(chunk, 'type') and chunk.type == 'HandoffMessage':
                        if hasattr(chunk, 'source') and hasattr(chunk, 'target'):
                            yield f"data: {json.dumps({'type': 'handoff', 'from': chunk.source, 'to': chunk.target, 'content': getattr(chunk, 'content', '')})}\n\n"
                    
                    # Handle tool call requests - inform UI which tool is being called
                    elif hasattr(chunk, 'type') and chunk.type == 'ToolCallRequestEvent':
                        if hasattr(chunk, 'content'):
                            # Iterate over all items in chunk.content
                            for item in _iter_items(chunk.content):
                                try:
                                    tool_name, tool_args = _extract_name_and_args(item)
                                    if tool_name:
                                        # Skip handoff tools (transfer_to_X)
                                        if not tool_name.startswith('transfer_to_'):
                                            display_name = TOOL_DISPLAY_NAMES.get(tool_name, tool_name)
                                            payload = {
                                                'tool_name': tool_name,
                                                'tool_display_name': display_name,
                                                'type': 'tool_call',
                                                'status': 'calling',
                                                'agent': getattr(chunk, 'source', 'unknown')
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
                                    # Extract tool name from FunctionExecutionResult
                                    tool_name = None
                                    
                                    # Check if this is a FunctionExecutionResult with a name attribute
                                    if hasattr(item, 'name') and hasattr(item, 'call_id'):
                                        tool_name = item.name
                                    else:
                                        # Fallback to the original extraction method
                                        tool_name, tool_args = _extract_name_and_args(item)
                                    
                                    # Send completion status for actual tools (not handoffs)
                                    if tool_name and not tool_name.startswith('transfer_to_'):
                                        display_name = TOOL_DISPLAY_NAMES.get(tool_name, tool_name)
                                        
                                        # Extract tool output/result
                                        tool_output = None
                                        if hasattr(item, 'content'):
                                            tool_output = item.content
                                        elif hasattr(item, 'result'):
                                            tool_output = item.result
                                        
                                        payload = {
                                            'tool_name': tool_name,
                                            'tool_display_name': display_name,
                                            'type': 'tool_call',
                                            'status': 'completed',
                                            'agent': getattr(chunk, 'source', 'unknown'),
                                            'output': tool_output,
                                        }
                                        # Include arguments when available
                                        if tool_args is not None:
                                            payload['arguments'] = tool_args
                                        yield f"data: {json.dumps(payload)}\n\n"
                                except Exception as e:
                                    print(f"Error processing tool execution event: {e}")
                                    pass
                    
                    # Handle ModelClientStreamingChunkEvent for token-level streaming
                    elif hasattr(chunk, 'type') and chunk.type == 'ModelClientStreamingChunkEvent':
                        if hasattr(chunk, 'content') and chunk.content:
                            agent_source = getattr(chunk, 'source', 'unknown')
                            yield f"data: {json.dumps({'content': chunk.content, 'type': 'token', 'agent': agent_source})}\n\n"
                    
                    # Handle TextMessage (complete messages)
                    elif hasattr(chunk, 'type') and chunk.type == 'TextMessage':
                        if hasattr(chunk, 'source'):
                            # Get the agent source
                            agent_source = chunk.source
                            if hasattr(chunk, 'content') and chunk.content:
                                # Don't stream handoff messages or internal tool messages
                                if not chunk.content.startswith('Transferred to'):
                                    yield f"data: {json.dumps({'content': chunk.content, 'type': 'message', 'agent': agent_source})}\n\n"
                    
                    # Handle TaskResult (final result)
                    elif hasattr(chunk, 'messages'):
                        # This is the final TaskResult - we can extract termination reason
                        if hasattr(chunk, 'stop_reason'):
                            yield f"data: {json.dumps({'type': 'completion', 'stop_reason': chunk.stop_reason})}\n\n"
            
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