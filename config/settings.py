"""
Configuration settings for the Dappier-Skyfire API

DEMONSTRATION NOTE:
This configuration file contains real settings for both Skyfire and Dappier MCP servers.
The MCP server URLs are actual endpoints that the application connects to:
- Dappier MCP Server: Real connection using DAPPIER_API_KEY for authentication
- Skyfire MCP Server: Real connection to Skyfire's production MCP endpoint

All tool configurations and session management settings are production-ready.
The only mocked component is the pricing data returned by one tool in the MCP Connector Agent.

IMPORTANT DEMONSTRATION DETAIL:
The Dappier MCP server connection uses Dappier's API key directly (not Skyfire tokens),
but the payment/charging for Dappier service usage flows through Skyfire's payment infrastructure.
This hybrid approach demonstrates how Skyfire can act as a payment layer for third-party services
while maintaining direct service connectivity for optimal performance.
"""
import os

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
        "url": f"https://mcp.dappier.com/mcp?apiKey={os.getenv('DAPPIER_API_KEY')}"
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