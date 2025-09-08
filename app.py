from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

# Import services
from services.session_service import SessionService
from services.mcp_service import MCPService
from services.chat_service import ChatService

# Import route blueprints
from routes.chat_routes import chat_bp, init_chat_routes
from routes.session_routes import session_bp, init_session_routes
from routes.health_routes import health_bp, init_health_routes

# Import configuration
from config.config import API_CONFIG, CORS_CONFIG, APP_INFO

# Load environment variables
load_dotenv()


def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Enable CORS for all routes and origins
    CORS(app, **CORS_CONFIG)
    
    # Initialize services
    session_manager = SessionService()
    mcp_client = MCPService()
    chat_service = ChatService(session_manager, mcp_client)
    
    # Initialize route blueprints with services
    init_chat_routes(chat_service, session_manager, mcp_client)
    init_session_routes(chat_service, session_manager, mcp_client)
    init_health_routes(session_manager, mcp_client)
    
    # Register blueprints
    app.register_blueprint(chat_bp)
    app.register_blueprint(session_bp)
    app.register_blueprint(health_bp)
    
    return app


def main():
    """Main entry point for the application"""
    app = create_app()
    
    print(f"Starting {APP_INFO['name']}")
    print(f"Framework: {APP_INFO['framework']}")
    print(f"Version: {APP_INFO['version']}")
    print(f"Server will be available at: http://{API_CONFIG['host']}:{API_CONFIG['port']}")
    print("\nAvailable endpoints:")
    print("  POST /initialize - Initialize MCP connections and create first session")
    print("  POST /sessions/new - Create a new session")
    print("  POST /chat - Send chat messages (requires session_id)")
    print("  GET /sessions - List all active sessions")
    print("  GET /sessions/<id> - Get specific session info")
    print("  DELETE /sessions/<id> - Delete a specific session")
    print("  POST /sessions/cleanup - Clean up expired sessions")
    print("  GET /sessions/stats - Get session statistics")
    print("  GET /status - Get initialization status")
    print("  GET /health - Health check")
    print("  GET /info - System information")
    print("  GET /tools - Available tools information")
    
    app.run(
        host=API_CONFIG["host"],
        port=API_CONFIG["port"],
        debug=API_CONFIG["debug"]
    )


if __name__ == '__main__':
    main()
