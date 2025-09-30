# Skyfire-Dappier Multi-Agent Demo

A sophisticated demonstration of payment-enabled AI service integration using Microsoft AutoGen's Swarm pattern to orchestrate a 10-step workflow between Skyfire and Dappier services.

## About the Platforms

### Dappier
Dappier is a platform that connects LLMs and automation frameworks to real-time, rights-cleared data from trusted sources, including web search, finance, and news. By providing enriched, prompt-ready data, Dappier empowers automations with verified and up-to-date information for a wide range of applications.

### Skyfire
Skyfire empowers AI to process payments, verify identities and access essential services without human intervention. From API account creation to monetizing websites, we drive commerce for the world's fastest-growing consumer base: AI agents.

**Dappier Service on Skyfire**: This demo showcases Dappier's seller service listed on the Skyfire directory: https://app.skyfire.xyz/directory/service/81085b79-68d8-4a46-9f8c-63c11a969828

## 🎯 Demo Overview

This application demonstrates how AI agents can seamlessly discover, authenticate, estimate costs, and process payments for third-party services through a sophisticated multi-agent workflow. The demo showcases:

- **Real-time Service Discovery**: Finding Dappier services on the Skyfire network
- **Authentication & Authorization**: Creating and managing JWT tokens for secure access
- **Cost Estimation**: Analyzing pricing for service usage before execution
- **Payment Processing**: Creating and charging payment tokens through Skyfire
- **Service Execution**: Running actual queries on Dappier's data services
- **Multi-Agent Coordination**: Orchestrating complex workflows using AutoGen Swarm

## 🏗️ Architecture

### 10-Step Workflow with 9 Specialized Agents

1. **Planning Agent**: Routes queries and orchestrates the workflow
2. **Skyfire Find Seller Agent**: Discovers Dappier services on Skyfire network
3. **Skyfire KYA Agent**: Creates authentication tokens
4. **JWT Decoder Agent**: Analyzes tokens (used twice in workflow)
5. **MCP Connector Agent**: Establishes Dappier connection + retrieves pricing
6. **Dappier Price Calculator Agent**: Estimates costs using real pricing logic
7. **Skyfire KYA Payment Token Agent**: Creates payment tokens with estimated amounts
8. **JWT Decoder Agent**: Analyzes payment tokens (second usage)
9. **Dappier Agent**: Executes queries using real Dappier tools
10. **Skyfire Charge Token Agent**: Processes payment through Skyfire

### Real vs. Demonstration Components

#### ✅ **Real Functionality**
- **Skyfire MCP Server**: Genuine connections, token creation, and payment processing
- **Dappier MCP Server**: Real connections and tool execution for data retrieval
- **JWT Token System**: Actual token generation, decoding, and authentication
- **Payment Processing**: Real token charging through Skyfire's API
- **Multi-Agent Orchestration**: Production-ready agent coordination using AutoGen Swarm
- **Session Management**: Functional conversation context and streaming responses

#### 🎭 **Mocked for Demonstration**
- **Dappier Pricing Data**: Static pricing JSON to ensure consistent demo experience
- **JWT Signature Verification**: Disabled for demo security reasons

#### 🔄 **Important Demonstration Detail**
While the demo UI visually shows Skyfire tokens being used to connect to Dappier's MCP server, the actual implementation uses Dappier's API key directly for the MCP connection. However, the payment/charging for Dappier service usage flows through Skyfire's infrastructure. This hybrid approach demonstrates how Skyfire can act as a payment layer for third-party services while maintaining optimal direct connectivity.

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- OpenAI API key
- Dappier API key
- Skyfire Seller API key

### Environment Variables

Create a `.env` file in the root directory:

```env
# Required API Keys
OPENAI_API_KEY=your_openai_api_key_here
DAPPIER_API_KEY=your_dappier_api_key_here
SKYFIRE_SELLER_API_KEY=your_skyfire_seller_api_key_here

# Optional Configuration
FLASK_ENV=development
FLASK_DEBUG=True
```

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd dappier-skyfire-api
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   python app.py
   ```

The application will start on `http://localhost:5000`

### Docker Deployment

```bash
# Build the image
docker build -t skyfire-dappier-demo .

# Run the container
docker run -p 5000:5000 --env-file .env skyfire-dappier-demo
```

## 📡 API Endpoints

### Initialize System
```http
POST /initialize
```
Establishes MCP connections and creates a new session.

**Response:**
```json
{
  "status": "success",
  "session_id": "session_12345",
  "initialization_status": {
    "initialized": true,
    "dappier": {"status": "connected", "tools": 10},
    "skyfire": {"status": "connected", "tools": 5}
  }
}
```

### Chat Completion
```http
POST /chat
Content-Type: application/json

{
  "message": "What are the latest news about AI?",
  "session_id": "session_12345",
  "stream": true
}
```

**Response:** Server-sent events stream with agent interactions and results.

### Health Check
```http
GET /health
```

### Session Management
```http
GET /sessions/{session_id}
DELETE /sessions/{session_id}
```

## 🛠️ Technical Implementation

### MCP (Model Context Protocol) Integration

The application integrates with two MCP servers:

- **Skyfire MCP Server**: `https://mcp.skyfire.xyz/mcp`
  - Tools: find-sellers, create-kya-token, create-pay-token, create-kya-payment-token
  
- **Dappier MCP Server**: `https://mcp.dappier.com/mcp`
  - Tools: real-time-search, stock-market-data, research-papers-search, news tools, and more

### Agent Architecture

Each agent is built using Microsoft AutoGen's AssistantAgent with:
- OpenAI GPT model integration
- Tool execution capabilities
- Handoff mechanisms for workflow coordination
- Streaming response support
- Error handling and recovery

### Session Management

- Unique session IDs for conversation isolation
- Session-specific swarm instances
- Automatic cleanup and timeout handling
- Conversation context preservation

## 🔧 Configuration

### Model Configuration (`config/settings.py`)

```python
MODEL_CONFIG = {
    "model": "gpt-4o-mini",
    "temperature": 0.1,
    "parallel_tool_calls": False,
    "max_tool_iterations": 10
}
```

### Session Configuration

```python
SESSION_CONFIG = {
    "max_sessions": 100,
    "session_timeout": 3600,
    "cleanup_interval": 300
}
```

## 🧪 Example Usage

### Simple Query
```bash
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the latest tech news?",
    "session_id": "demo_session_1"
  }'
```

### Complex Financial Query
```bash
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Get me the latest stock data for AAPL and analyze the market trends",
    "session_id": "demo_session_1"
  }'
```



## 🤝 Building Similar Systems

This demo provides a foundation for building payment-enabled AI service integrations. Key patterns demonstrated:

### Service Discovery Pattern
```python
# Finding services on Skyfire network
skyfire_tools = ["find-sellers"]
result = await agent.execute_tool("find-sellers", {"query": "dappier"})
```

### Authentication Pattern
```python
# Creating authentication tokens
kya_token = await agent.execute_tool("create-kya-token", {
    "seller_id": seller_id,
    "buyer_id": buyer_id
})
```

### Payment Pattern
```python
# Creating and charging payment tokens
payment_token = await agent.execute_tool("create-kya-payment-token", {
    "amount": estimated_cost
})
charge_result = await agent.execute_tool("charge-token", {
    "token": payment_token,
    "amount": actual_cost
})
```

### Multi-Agent Coordination
```python
# Using AutoGen Swarm for agent handoffs
handoffs = [
    Handoff(target="next_agent", description="Process next step")
]
```

## 📚 Dependencies

### Core Dependencies
- `flask` - Web framework
- `autogen-agentchat` - Multi-agent framework
- `autogen-ext` - AutoGen extensions for MCP and OpenAI
- `openai` - OpenAI API client
- `requests` - HTTP client for API calls
- `python-dotenv` - Environment variable management

### Development Dependencies
- `flask-cors` - CORS support for development
- `asyncio` - Asynchronous programming support

## 🐛 Troubleshooting

### Common Issues

1. **MCP Connection Failures**
   - Verify API keys are correctly set in `.env`
   - Check network connectivity to MCP servers
   - Review initialization logs for specific errors

2. **Agent Handoff Issues**
   - Ensure all agents are properly registered in the swarm
   - Check agent names match handoff targets
   - Verify tool availability for each agent

3. **Session Management**
   - Sessions timeout after 1 hour by default
   - Use `/initialize` to create new sessions
   - Check session cleanup logs for automatic cleanup

### Debug Mode

Set `FLASK_DEBUG=True` in your `.env` file for detailed error messages and automatic reloading.

## 📄 License

This project is open source and available under the MIT License.

## 🤝 Contributing

Contributions are welcome! This demo serves as a foundation for building sophisticated payment-enabled AI service integrations. Areas for enhancement:

- Additional MCP server integrations
- Enhanced error handling and recovery
- Performance optimizations
- Additional agent capabilities
- UI/Frontend integration

---

**Built with ❤️ to demonstrate the future of payment-enabled AI service integration**