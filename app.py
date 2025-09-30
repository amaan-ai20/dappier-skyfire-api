"""
Flask AutoGen Swarm API with Dappier & Skyfire MCP Integration
Modular architecture with separated concerns

SKYFIRE-DAPPIER DEMO APPLICATION
================================

This application demonstrates a sophisticated integration between Skyfire and Dappier services
through a 10-step multi-agent workflow using Microsoft AutoGen's Swarm pattern.

DEMONSTRATION COMPONENTS:
========================

REAL FUNCTIONALITY:
- Skyfire MCP Server: Real connections, token creation, and payment processing
- Dappier MCP Server: Real connections and tool execution for data retrieval
- JWT Token System: Real token generation, decoding, and authentication
- Payment Processing: Actual token charging through Skyfire's API
- Multi-Agent Orchestration: Production-ready agent coordination

MOCKED FOR DEMONSTRATION:
- Dappier Pricing Data: Static pricing JSON to ensure consistent demo experience
- Service Discovery: Dappier Search Service is part of demo setup

WORKFLOW OVERVIEW:
=================
1. Planning Agent: Routes queries and orchestrates workflow
2. Skyfire Find Seller: Discovers Dappier services on Skyfire network
3. Skyfire KYA Agent: Creates authentication tokens
4. JWT Decoder: Analyzes tokens (used twice in workflow)
5. MCP Connector: Establishes Dappier connection + retrieves pricing
6. Price Calculator: Estimates costs using real pricing logic
7. Payment Token Agent: Creates payment tokens with estimated amounts
8. JWT Decoder: Analyzes payment tokens
9. Dappier Agent: Executes queries using real Dappier tools
10. Charge Token Agent: Processes payment through Skyfire

KEY DEMONSTRATION POINTS:
========================
- Payment-enabled AI service integration
- Cross-platform authentication and authorization
- Real-time cost estimation and payment processing
- Multi-agent coordination for complex workflows
- Production-ready architecture with Docker deployment

IMPORTANT DEMONSTRATION DETAIL:
===============================
While the demo UI visually shows Skyfire tokens being used to connect to Dappier's MCP server,
the actual implementation uses Dappier's API key directly for the MCP connection.
However, the payment/charging for Dappier service usage flows through Skyfire's infrastructure.
This hybrid approach demonstrates how Skyfire can act as a payment layer for third-party services
while maintaining optimal direct connectivity to those services.
"""
import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

# Import route blueprints
from routes.health import health_bp
from routes.initialization import init_bp
from routes.sessions import sessions_bp
from routes.chat import chat_bp

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__)

# Configure CORS origins based on environment
def get_allowed_origins():
    """Get allowed CORS origins based on environment"""
    # Check if we're in production (you can adjust this logic based on your deployment)
    is_production = os.getenv('FLASK_ENV') == 'production' or os.getenv('ENVIRONMENT') == 'production'
    
    if is_production:
        # Production: only allow the production domain
        return ["https://skyfire-demo.dappier.com"]
    else:
        # Development: allow local development server
        return ["http://localhost:5173"]

# Enable CORS with environment-specific origins
allowed_origins = get_allowed_origins()
CORS(app, origins=allowed_origins, methods=["GET", "POST", "DELETE", "OPTIONS"], allow_headers=["Content-Type", "Authorization"])

# Register blueprints
app.register_blueprint(health_bp)
app.register_blueprint(init_bp)
app.register_blueprint(sessions_bp)
app.register_blueprint(chat_bp)


if __name__ == '__main__':
    print("Starting Flask AutoGen Swarm API with Dappier & Skyfire MCP Integration")
    print("Server will be available at: http://localhost:5000")
    print("Architecture: Modular Swarm pattern with Planning, Dappier, and Skyfire agents")
    print("\nEndpoints:")
    print("  GET  /health - Health check")
    print("  GET  /status - Initialization status")
    print("  POST /initialize - Initialize MCP connections and create first session")
    print("  POST /sessions/new - Create new session")
    print("  GET  /sessions - List active sessions")
    print("  DELETE /sessions/<id> - Delete specific session")
    print("  POST /sessions/cleanup - Clean up expired sessions")
    print("  POST /sessions/clear - Clear all sessions")
    print("  POST /chat - Chat with streaming response")
    app.run(host='0.0.0.0', port=5000)