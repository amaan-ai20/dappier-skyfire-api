# Dappier MCP Integration with AutoGen

## Overview

This Flask application now integrates with the Dappier Model Context Protocol (MCP) server, providing the AutoGen agent with access to 10 powerful tools for enhanced information retrieval and analysis.

## 🔧 Available Dappier Tools

The agent now has access to the following tools:

1. **real-time-search** - Perform real-time web search for latest news, weather, travel info, etc. (Free)
2. **stock-market-data** - Real-time financial news, stock prices, and trade updates ($0.007/query)
3. **research-papers-search** - Access 2.4M+ scholarly articles from arXiv ($0.003/query)
4. **benzinga** - AI-powered financial news from Benzinga.com ($0.1/query)
5. **sports-news** - Real-time sports updates from top sources ($0.004/query)
6. **lifestyle-news** - Lifestyle content from leading publications ($0.1/query)
7. **iheartdogs-ai** - Dog care expert content from iHeartDogs.com ($0.01/query)
8. **iheartcats-ai** - Cat care specialist content from iHeartCats.com ($0.01/query)
9. **one-green-planet** - Plant-based diet and sustainability guides ($0.01/query)
10. **wish-tv-ai** - News covering sports, politics, entertainment, etc. ($0.004/query)

## 🚀 How It Works

### Agent Initialization
- The agent automatically attempts to connect to the Dappier MCP server on startup
- If successful, it initializes with all available MCP tools
- If the connection fails, it falls back to standard OpenAI responses
- The agent intelligently decides when to use specific tools based on user queries

### Smart Tool Usage
The agent will automatically use appropriate tools based on the query context:
- **Financial queries** → `stock-market-data` or `benzinga`
- **General news/search** → `real-time-search`
- **Academic research** → `research-papers-search`
- **Sports questions** → `sports-news`
- **Pet care questions** → `iheartdogs-ai` or `iheartcats-ai`
- **Sustainability topics** → `one-green-planet`

## 🔄 Architecture

### Key Components

1. **`get_dappier_tools()`** - Async function that connects to MCP server and retrieves tools
2. **`get_autogen_agent_with_tools()`** - Async function that creates agent with MCP tools
3. **`get_autogen_agent()`** - Sync fallback function for basic agent
4. **Event Loop Management** - Proper handling of async operations in Flask context

### Error Handling & Fallback
- Graceful degradation if MCP server is unavailable
- Detailed logging of connection attempts and failures
- Automatic fallback to OpenAI-only responses
- No disruption to existing functionality

## 📡 API Endpoints

### `/health` - Health Check
Returns service status and confirms MCP integration status.

### `/chat` - Chat Completion
- **Streaming Mode** (default): Real-time token streaming with MCP tool usage visibility
- **Non-streaming Mode**: Complete response with MCP tool integration
- Supports conversation history
- Automatically uses appropriate Dappier tools when relevant
- Provides tool call events for UI feedback

#### Streaming Response Format
The streaming response now includes different event types:

1. **Tool Call Events**: `{"tool_name": "real-time-search", "tool_display_name": "Real-time Web Search", "type": "tool_call", "status": "calling"}`
2. **Tool Completion Events**: `{"tool_name": "real-time-search", "tool_display_name": "Real-time Web Search", "type": "tool_call", "status": "completed"}`
3. **Token Events**: `{"content": "The", "type": "token"}`
4. **Message Events**: `{"content": "Complete response text", "type": "message"}`
5. **Done Event**: `{"type": "done"}`

## 🧪 Testing

### Test Files Included

1. **`test_agent_with_tools.py`** - Tests agent initialization and tool usage
2. **`test_api_with_mcp.py`** - Tests Flask API endpoints with MCP integration

### Running Tests

```bash
# Test agent with tools (requires async environment)
python test_agent_with_tools.py

# Test API endpoints (requires running Flask app)
python app.py  # In one terminal
python test_api_with_mcp.py  # In another terminal
```

## 🔐 Configuration

### MCP Server Connection
- **URL**: `https://mcp.dappier.com/sse?apiKey=ak_01k194ztkcey3aq7b8k415k0zp`
- **Protocol**: Server-Sent Events (SSE)
- **Authentication**: API key included in URL

### Environment Variables
- **OPENAI_API_KEY**: Required for OpenAI model client
- No additional environment variables needed for MCP integration

## 💡 Usage Examples

### Example Queries That Will Use MCP Tools

```python
# Will use real-time-search
"What's the latest news about artificial intelligence?"

# Will use stock-market-data
"What's the current Tesla stock price?"

# Will use research-papers-search  
"Find recent research papers about machine learning"

# Will use sports-news
"What are the latest NBA scores?"

# Will use iheartdogs-ai
"How do I train my puppy to sit?"
```

### API Request Example

```bash
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the latest developments in AI research?",
    "stream": false
  }'
```

## 🔍 Monitoring & Debugging

### Log Messages
- `"Successfully loaded X tools from Dappier MCP server"` - MCP connection successful
- `"Agent initialized with Dappier MCP tools"` - Agent has tools available
- `"Agent initialized without MCP tools (fallback mode)"` - Using fallback mode
- `"Warning: Could not connect to Dappier MCP server"` - Connection failed

### Health Check
The `/health` endpoint provides status information about the service and MCP integration.

## 🚨 Error Handling

The integration includes comprehensive error handling:
- Network connectivity issues with MCP server
- MCP server unavailability
- Tool execution failures
- Event loop management in Flask context
- Graceful fallback to OpenAI-only responses

## 🎯 Benefits

1. **Enhanced Capabilities**: Access to real-time data and specialized knowledge
2. **Automatic Tool Selection**: Agent intelligently chooses appropriate tools
3. **Seamless Integration**: No changes needed to existing API contracts
4. **Robust Fallback**: Continues working even if MCP server is unavailable
5. **Cost-Effective**: Many tools are free or low-cost per query
6. **Specialized Knowledge**: Access to domain-specific content (finance, pets, sports, etc.)

## 🔮 Future Enhancements

Potential improvements:
- Tool usage analytics and monitoring
- Custom tool selection strategies
- Caching of frequently used tool results
- Additional MCP server integrations
- User-specific tool preferences