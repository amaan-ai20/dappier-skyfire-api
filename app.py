import os
from flask import Flask, request, jsonify
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Initialize OpenAI client
client = None

def get_openai_client():
    global client
    if client is None:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        client = OpenAI(api_key=api_key)
    return client

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "Flask OpenAI API"})

@app.route('/chat', methods=['POST'])
def chat_completion():
    """Chat completion endpoint that uses OpenAI's API"""
    try:
        # Get the request data
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        # Extract message from request
        message = data.get('message')
        if not message:
            return jsonify({"error": "Message field is required"}), 400
        
        # Get optional parameters with defaults
        model = data.get('model', 'gpt-3.5-turbo')
        max_tokens = data.get('max_tokens', 150)
        temperature = data.get('temperature', 0.7)
        
        # Get OpenAI client
        openai_client = get_openai_client()
        
        # Make request to OpenAI
        response = openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": message}
            ],
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        # Extract response content
        ai_response = response.choices[0].message.content
        
        # Build response data
        response_data = {
            "response": ai_response,
            "model": model
        }
        
        # Add usage information if available
        if hasattr(response, 'usage') and response.usage:
            response_data["usage"] = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        
        return jsonify(response_data)
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/', methods=['GET'])
def home():
    """Home endpoint with API usage information"""
    return jsonify({
        "message": "Flask OpenAI API",
        "endpoints": {
            "GET /": "This help message",
            "GET /health": "Health check",
            "POST /chat": "Chat completion endpoint"
        },
        "usage": {
            "chat_endpoint": {
                "method": "POST",
                "required_fields": ["message"],
                "optional_fields": ["model", "max_tokens", "temperature"],
                "example": {
                    "message": "Hello, how are you?",
                    "model": "gpt-3.5-turbo",
                    "max_tokens": 150,
                    "temperature": 0.7
                }
            }
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)