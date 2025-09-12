"""
Flask AutoGen Swarm API with Dappier & Skyfire MCP Integration
Modular architecture with separated concerns
"""
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

# Enable CORS for all routes and origins
CORS(app, origins="*", methods=["GET", "POST", "OPTIONS"], allow_headers=["Content-Type", "Authorization"])

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
    app.run(host='0.0.0.0', port=5000, debug=True)