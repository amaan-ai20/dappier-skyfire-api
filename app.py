import os
import asyncio
import json
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Enable CORS for all routes and origins
CORS(app, origins="*", methods=["GET", "POST", "OPTIONS"], allow_headers=["Content-Type", "Authorization"])

# Initialize AutoGen agent
agent = None

def get_autogen_agent():
    global agent
    if agent is None:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        # Create OpenAI model client for AutoGen
        model_client = OpenAIChatCompletionClient(
            model="gpt-4o",
            api_key=api_key
        )
        
        # Create AutoGen assistant agent
        agent = AssistantAgent(
            name="chat_assistant",
            model_client=model_client,
            system_message="You are a helpful AI assistant. Provide clear, concise, and helpful responses to user queries.",
            model_client_stream=True  # Enable token-level streaming
        )
    return agent

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

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy", 
        "service": "Flask AutoGen API",
        "framework": "Microsoft AutoGen",
        "model": "gpt-4o"
    })

@app.route('/chat', methods=['POST'])
def chat_completion():
    """Chat completion endpoint that uses AutoGen with streaming"""
    try:
        # Get the request data
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        # Extract message from request
        message = data.get('message')
        if not message:
            return jsonify({"error": "Message field is required"}), 400
        
        # Extract conversation history from request (optional)
        messages_history = data.get('messages', [])
        
        # Check if streaming is requested (default: True)
        stream = data.get('stream', True)
        
        if stream:
            return Response(
                stream_with_context(generate_streaming_response(message, messages_history)),
                mimetype='text/plain',
                headers={
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive'
                }
            )
        else:
            # Non-streaming response
            return Response(
                stream_with_context(generate_complete_response(message, messages_history)),
                mimetype='application/json'
            )
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

def generate_streaming_response(message, messages_history=None):
    """Generate streaming response using AutoGen agent with conversation history"""
    try:
        # Get AutoGen agent
        autogen_agent = get_autogen_agent()
        
        # Build conversation context from history
        conversation_context = build_conversation_context(message, messages_history)
        
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Define async function to stream messages
            async def stream_messages():
                async for chunk in autogen_agent.run_stream(task=conversation_context):
                    # Handle ModelClientStreamingChunkEvent for token-level streaming
                    if hasattr(chunk, 'type') and chunk.type == 'ModelClientStreamingChunkEvent':
                        if hasattr(chunk, 'content') and chunk.content:
                            yield f"data: {json.dumps({'content': chunk.content, 'type': 'token'})}\n\n"
                    
                    # Handle TextMessage (complete messages)
                    elif hasattr(chunk, 'type') and chunk.type == 'TextMessage':
                        if hasattr(chunk, 'source') and chunk.source == 'assistant':
                            if hasattr(chunk, 'content') and chunk.content:
                                yield f"data: {json.dumps({'content': chunk.content, 'type': 'message'})}\n\n"
                    
                    # Handle TaskResult (final result)
                    elif hasattr(chunk, 'messages'):
                        # This is the final TaskResult - we can ignore it since we already streamed the content
                        pass
                    
                    # Handle any other message types
                    else:
                        chunk_type = type(chunk).__name__
                        if hasattr(chunk, 'content') and chunk.content and chunk.content != conversation_context:
                            yield f"data: {json.dumps({'content': str(chunk.content), 'type': chunk_type})}\n\n"
            
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

def generate_complete_response(message, messages_history=None):
    """Generate complete response using AutoGen agent with conversation history"""
    try:
        # Get AutoGen agent
        autogen_agent = get_autogen_agent()
        
        # Build conversation context from history
        conversation_context = build_conversation_context(message, messages_history)
        
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Run the agent
            response = loop.run_until_complete(
                autogen_agent.run(task=conversation_context)
            )
            
            # Extract the response content
            if hasattr(response, 'messages') and response.messages:
                # Get the last message from the agent
                last_message = response.messages[-1]
                if hasattr(last_message, 'content'):
                    ai_response = last_message.content
                else:
                    ai_response = str(last_message)
            else:
                ai_response = str(response)
            
            # Build response data
            response_data = {
                "response": ai_response,
                "model": "gpt-4o",
                "agent": "autogen_assistant"
            }
            
            yield json.dumps(response_data)
            
        finally:
            loop.close()
            
    except Exception as e:
        error_response = {"error": f"An error occurred: {str(e)}"}
        yield json.dumps(error_response)



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
