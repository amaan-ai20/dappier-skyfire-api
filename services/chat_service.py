import asyncio
import json
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from .session_service import SessionService
from .mcp_service import MCPService
from config.config import TOOL_DISPLAY_NAMES
import os


class ChatService:
    """Service class for handling chat operations and agent management"""
    
    def __init__(self, session_manager: SessionService, mcp_client: MCPService):
        self.session_manager = session_manager
        self.mcp_client = mcp_client
    
    async def create_session_agent(self):
        """Create a new agent instance for a session"""
        try:
            # Check for OpenAI API key
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable is required")
            
            # Create OpenAI model client for AutoGen
            model_client = OpenAIChatCompletionClient(
                model="gpt-4o",
                api_key=api_key
            )
            
            # Use cached tools from MCP client
            all_tools = self.mcp_client.get_all_tools()
            
            # Create AutoGen assistant agent with MCP tools
            if all_tools:
                session_agent = AssistantAgent(
                    name="chat_assistant",
                    model_client=model_client,
                    tools=all_tools,
                    reflect_on_tool_use=True,
                    max_tool_iterations=10,
                    model_client_stream=True,
                    system_message="You are a helpful AI assistant with access to both Dappier and Skyfire tools for enhanced information retrieval and analysis. When you use tools to get information, you MUST always process and summarize the results in a natural, conversational way. After calling any tool, you must provide a comprehensive response based on the tool's results. Never return raw tool data to users. Always analyze the information from tools and provide a helpful, well-formatted response that directly answers the user's question. Your response should be conversational and informative, making use of the data you retrieved through the tools."
                )
            else:
                session_agent = AssistantAgent(
                    name="chat_assistant",
                    model_client=model_client,
                    model_client_stream=True,
                    system_message="You are a helpful AI assistant. Provide clear, concise, and helpful responses to user queries."
                )
            
            return session_agent
            
        except Exception as e:
            print(f"Failed to create session agent: {str(e)}")
            raise
    
    async def get_or_create_session_agent(self, session_id: str):
        """Get existing session agent or create a new one"""
        # Check if MCP client is initialized
        if not self.mcp_client.is_initialized():
            raise ValueError("MCP client not initialized. Please initialize first.")
        
        # Get or create session agent using session manager
        if not self.session_manager.has_agent(session_id):
            print(f"Creating new session agent for session: {session_id}")
            session_agent = await self.create_session_agent()
            self.session_manager.set_agent(session_id, session_agent)
        
        # Update session activity
        self.session_manager.update_session_activity(session_id)
        
        return self.session_manager.get_agent(session_id)
    
    def build_conversation_context(self, current_message: str, messages_history=None):
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
    
    def _iter_items(self, content):
        """Normalize content to a list for iteration"""
        if content is None:
            return []
        if isinstance(content, (list, tuple)):
            return content
        return [content]
    
    def _extract_name_and_args(self, item):
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
    
    def generate_streaming_response(self, message: str, messages_history=None, session_id=None):
        """Generate streaming response using session-specific AutoGen agent with conversation history"""
        try:
            # Session ID is required
            if not session_id:
                yield f"data: {json.dumps({'error': 'Session ID is required', 'type': 'error'})}\n\n"
                return
            
            # Get session-specific agent
            try:
                session_agent = self.session_manager.get_agent(session_id)
                if not session_agent:
                    # Create new event loop for agent creation
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        session_agent = loop.run_until_complete(self.get_or_create_session_agent(session_id))
                    finally:
                        loop.close()
            except Exception as e:
                yield f"data: {json.dumps({'error': f'Failed to get session agent: {str(e)}', 'type': 'error'})}\n\n"
                return
            
            # Build conversation context from history
            conversation_context = self.build_conversation_context(message, messages_history)
            
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Run the streaming in the event loop
                async def async_streaming():
                    # Use the session-specific agent
                    async for chunk in session_agent.run_stream(task=conversation_context):
                        # Handle tool call requests - inform UI which tool is being called
                        if hasattr(chunk, 'type') and chunk.type == 'ToolCallRequestEvent':
                            if hasattr(chunk, 'content'):
                                # Iterate over all items in chunk.content
                                for item in self._iter_items(chunk.content):
                                    try:
                                        tool_name, tool_args = self._extract_name_and_args(item)
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
                                for item in self._iter_items(chunk.content):
                                    try:
                                        tool_name, tool_args = self._extract_name_and_args(item)
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
                    
                    # Send completion signal
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
                
                # Convert async generator to sync generator
                async_gen = async_streaming()
                while True:
                    try:
                        data = loop.run_until_complete(async_gen.__anext__())
                        yield data
                    except StopAsyncIteration:
                        break
                
            finally:
                loop.close()
                
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e), 'type': 'error'})}\n\n"