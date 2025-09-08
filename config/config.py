# Configuration settings for the application

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

# API Configuration
API_CONFIG = {
    "host": "0.0.0.0",
    "port": 5000,
    "debug": True
}

# CORS Configuration
CORS_CONFIG = {
    "origins": "*",
    "methods": ["GET", "POST", "OPTIONS"],
    "allow_headers": ["Content-Type", "Authorization"]
}

# OpenAI Configuration
OPENAI_CONFIG = {
    "model": "gpt-4o",
    "max_tool_iterations": 10,
    "reflect_on_tool_use": True,
    "stream": True
}

# MCP Server URLs and Configuration
MCP_CONFIG = {
    "dappier": {
        "url": "https://mcp.dappier.com/mcp?apiKey=ak_01k194ztkcey3aq7b8k415k0zp"
    },
    "skyfire": {
        "url": "https://mcp.skyfire.xyz/mcp",
        "requires_api_key": True,
        "api_key_header": "skyfire-api-key",
        "env_var": "SKYFIRE_API_KEY"
    }
}

# System Messages
SYSTEM_MESSAGES = {
    "default_with_tools": "You are a helpful AI assistant with access to both Dappier and Skyfire tools for enhanced information retrieval and analysis. When you use tools to get information, you MUST always process and summarize the results in a natural, conversational way. After calling any tool, you must provide a comprehensive response based on the tool's results. Never return raw tool data to users. Always analyze the information from tools and provide a helpful, well-formatted response that directly answers the user's question. Your response should be conversational and informative, making use of the data you retrieved through the tools.",
    "default_without_tools": "You are a helpful AI assistant. Provide clear, concise, and helpful responses to user queries."
}

# Application metadata
APP_INFO = {
    "name": "Flask AutoGen API with Dappier & Skyfire MCP Integration",
    "framework": "Microsoft AutoGen",
    "version": "1.0.0",
    "description": "Session-based chat API with MCP tool integration"
}