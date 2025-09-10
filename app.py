from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Import blueprints
from sessions import sessions_bp
from initialize import initialize_bp
from chat import chat_bp

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Enable CORS for all routes and origins
CORS(app, origins="*", methods=["GET", "POST", "OPTIONS"], allow_headers=["Content-Type", "Authorization"])

# Register blueprints
app.register_blueprint(sessions_bp)
app.register_blueprint(initialize_bp)
app.register_blueprint(chat_bp)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy", 
        "service": "Flask AutoGen API with Dappier & Skyfire MCP Integration",
        "framework": "Microsoft AutoGen",
        "model": "gpt-4o",
        "mcp_servers": {
            "dappier": "https://mcp.dappier.com/mcp",
            "skyfire": "https://mcp.skyfire.xyz/mcp"
        },
        "endpoints": {
            "health": "/health (GET)",
            "initialize": "/initialize (POST)",
            "status": "/status (GET)",
            "chat": "/chat (POST)",
            "session_new": "/sessions/new (POST)",
            "session_list": "/sessions (GET)",
            "session_delete": "/sessions/<session_id> (DELETE)",
            "session_cleanup": "/sessions/cleanup (POST)"
        }
    })

if __name__ == '__main__':
    print("Starting Flask AutoGen API with Dappier & Skyfire MCP Integration")
    print("Server will be available at: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)