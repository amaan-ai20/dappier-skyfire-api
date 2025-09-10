import os
from datetime import datetime
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

# Global variables that will be imported by other modules
session_agents = {}  # Dictionary to store session-specific agents
session_metadata = {}  # Store session metadata

# Global tool cache to avoid duplicate initialization
cached_tools = {
    "dappier": [],
    "skyfire": [],
    "all_tools": []
}

initialization_status = {
    "initialized": False,
    "initializing": False,
    "error": None,
    "dappier": {"status": "not_connected", "tools": [], "error": None},
    "skyfire": {"status": "not_connected", "tools": [], "error": None},
    "total_tools": 0,
    "initialized_at": None
}

# Session management configuration
SESSION_CONFIG = {
    "max_sessions": 100,  # Maximum number of concurrent sessions
    "session_timeout": 3600,  # Session timeout in seconds (1 hour)
    "cleanup_interval": 300  # Cleanup interval in seconds (5 minutes)
}

# Tool display names for UI
TOOL_DISPLAY_NAMES = {
    # Dappier tools
    'real-time-search': 'Real Time Search',
    'stock-market-data': 'Stock Market Data',
    'research-papers-search': 'Research Papers Search',
    'benzinga': 'Benzinga',
    'sports-news': 'Sports News',
    'lifestyle-news': 'Lifestyle News',
    'iheartdogs-ai': 'Iheartdogs AI',
    'iheartcats-ai': 'Iheartcats AI',
    'one-green-planet': 'One Green Planet',
    'wish-tv-ai': 'Wish TV AI',
    # Skyfire tools
    'find-sellers': 'Find Sellers',
    'create-kya-token': 'Create KYA Token',
    'create-pay-token': 'Create Pay Token',
    'create-kya-payment-token': 'Create KYA Payment Token',
    'get-current-datetime': 'Get Current Datetime'
}

def clear_tool_cache():
    """Clear the cached tools (useful for re-initialization)"""
    global cached_tools
    cached_tools = {
        "dappier": [],
        "skyfire": [],
        "all_tools": []
    }

async def create_session_agent():
    """Create a new agent instance for a session"""
    global cached_tools
    
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
        
        # Use cached tools to avoid duplicate initialization
        all_tools = cached_tools["all_tools"]
        
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



