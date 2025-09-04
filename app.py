import os
import asyncio
import json
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import SseServerParams, mcp_server_tools
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Enable CORS for all routes and origins
CORS(app, origins="*", methods=["GET", "POST", "OPTIONS"], allow_headers=["Content-Type", "Authorization"])

# Initialize AutoGen agent
agent = None
agent_with_tools = None

# Tool display names for UI
TOOL_DISPLAY_NAMES = {
    'real-time-search': 'Real-time Web Search',
    'stock-market-data': 'Stock Market Data',
    'research-papers-search': 'Research Papers Search',
    'benzinga': 'Benzinga Financial News',
    'sports-news': 'Sports News',
    'lifestyle-news': 'Lifestyle News',
    'iheartdogs-ai': 'Dog Care Expert',
    'iheartcats-ai': 'Cat Care Specialist',
    'one-green-planet': 'Sustainability Guide',
    'wish-tv-ai': 'WISH-TV News'
}

async def get_dappier_tools():
    """Get tools from Dappier MCP server with error handling"""
    try:
        # Configure Dappier MCP server parameters
        server_params = SseServerParams(
            url="https://mcp.dappier.com/sse?apiKey=ak_01k194ztkcey3aq7b8k415k0zp"
        )
        
        # Get available tools from the MCP server
        tools = await mcp_server_tools(server_params)
        print(f"Successfully loaded {len(tools)} tools from Dappier MCP server")
        return tools
    except Exception as e:
        print(f"Warning: Could not connect to Dappier MCP server: {str(e)}")
        print("Falling back to OpenAI-only responses")
        return []

async def get_autogen_agent_with_tools():
    """Get AutoGen agent with Dappier MCP tools (async version)"""
    global agent_with_tools
    if agent_with_tools is None:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        # Create OpenAI model client for AutoGen
        model_client = OpenAIChatCompletionClient(
            model="gpt-4o",
            api_key=api_key
        )
        
        # Get Dappier MCP tools
        dappier_tools = await get_dappier_tools()
        
        # Create AutoGen assistant agent with MCP tools using the proper configuration
        if dappier_tools:
            agent_with_tools = AssistantAgent(
                name="chat_assistant",
                model_client=model_client,
                tools=dappier_tools,
                reflect_on_tool_use=True,  # This is key - makes agent reflect on tool results
                max_tool_iterations=10,    # Allow multiple tool calls and reasoning steps
                model_client_stream=True,  # Enable token-level streaming
                system_message="You are a helpful AI assistant with access to Dappier tools for enhanced information retrieval and analysis. When you use tools to get information, you MUST always process and summarize the results in a natural, conversational way. After calling any tool, you must provide a comprehensive response based on the tool's results. Never return raw tool data to users. Always analyze the information from tools and provide a helpful, well-formatted response that directly answers the user's question. Your response should be conversational and informative, making use of the data you retrieved through the tools."
            )
            print("Agent initialized with Dappier MCP tools (with reflection and streaming)")
        else:
            agent_with_tools = AssistantAgent(
                name="chat_assistant",
                model_client=model_client,
                model_client_stream=True,  # Enable token-level streaming
                system_message="You are a helpful AI assistant. Provide clear, concise, and helpful responses to user queries."
            )
            print("Agent initialized without MCP tools (fallback mode with streaming)")
    return agent_with_tools

def get_autogen_agent():
    """Get basic AutoGen agent without MCP tools (sync version for compatibility)"""
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
        
        # Create basic AutoGen assistant agent
        agent = AssistantAgent(
            name="chat_assistant",
            model_client=model_client,
            system_message="You are a helpful AI assistant. Provide clear, concise, and helpful responses to user queries.",
            model_client_stream=True  # Enable token-level streaming
        )
        print("Basic agent initialized (will upgrade to MCP tools in async context)")
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
        # We'll get the agent with tools in the async context
        autogen_agent = None
        
        # Build conversation context from history
        conversation_context = build_conversation_context(message, messages_history)
        
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Define async function to stream messages
            async def stream_messages():
                # Get agent with MCP tools in async context
                nonlocal autogen_agent
                autogen_agent = await get_autogen_agent_with_tools()
                
                async for chunk in autogen_agent.run_stream(task=conversation_context):
                    # Handle tool call requests - inform UI which tool is being called
                    if hasattr(chunk, 'type') and chunk.type == 'ToolCallRequestEvent':
                        if hasattr(chunk, 'content') and chunk.content:
                            # Extract tool name from the function call
                            try:
                                import re
                                tool_match = re.search(r"name='([^']+)'", str(chunk.content))
                                if tool_match:
                                    tool_name = tool_match.group(1)
                                    display_name = TOOL_DISPLAY_NAMES.get(tool_name, tool_name)
                                    yield f"data: {json.dumps({'tool_name': tool_name, 'tool_display_name': display_name, 'type': 'tool_call', 'status': 'calling'})}\n\n"
                            except:
                                pass
                    
                    # Handle tool execution results - inform UI that tool finished
                    elif hasattr(chunk, 'type') and chunk.type == 'ToolCallExecutionEvent':
                        if hasattr(chunk, 'content') and chunk.content:
                            # Extract tool name from the execution result
                            try:
                                import re
                                tool_match = re.search(r"name='([^']+)'", str(chunk.content))
                                if tool_match:
                                    tool_name = tool_match.group(1)
                                    display_name = TOOL_DISPLAY_NAMES.get(tool_name, tool_name)
                                    yield f"data: {json.dumps({'tool_name': tool_name, 'tool_display_name': display_name, 'type': 'tool_call', 'status': 'completed'})}\n\n"
                            except:
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
                            # For debugging - let's see what's in here
                            print(f"DEBUG: ToolCallSummaryMessage content: {str(chunk.content)[:200]}...")
                    
                    # Handle any other chunk types for debugging
                    else:
                        chunk_type = getattr(chunk, 'type', type(chunk).__name__)
                        print(f"DEBUG: Unhandled chunk type: {chunk_type}")
                        if hasattr(chunk, 'content') and chunk.content:
                            print(f"DEBUG: Content preview: {str(chunk.content)[:100]}...")
            
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
        # We'll get the agent with tools in the async context
        autogen_agent = None
        
        # Build conversation context from history
        conversation_context = build_conversation_context(message, messages_history)
        
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Define async function to get agent and run
            async def run_agent():
                nonlocal autogen_agent
                autogen_agent = await get_autogen_agent_with_tools()
                return await autogen_agent.run(task=conversation_context)
            
            # Run the agent
            response = loop.run_until_complete(run_agent())
            
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
