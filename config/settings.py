"""
Configuration settings for the Dappier-Skyfire API
"""

# Session management configuration
SESSION_CONFIG = {
    "max_sessions": 100,
    "session_timeout": 3600,
    "cleanup_interval": 300
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

# MCP Server URLs
MCP_SERVERS = {
    "dappier": {
        "url": "https://mcp.dappier.com/mcp?apiKey=ak_01k194ztkcey3aq7b8k415k0zp"
    },
    "skyfire": {
        "url": "https://mcp.skyfire.xyz/mcp"
    }
}

# OpenAI Model Configuration
MODEL_CONFIG = {
    "model": "gpt-4o",
    "parallel_tool_calls": False,
    "temperature": 0.1,
    "max_tool_iterations": 10
}