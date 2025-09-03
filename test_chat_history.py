#!/usr/bin/env python3
"""
Test script to verify chat history functionality
"""
import requests
import json

# Test configuration
BASE_URL = "http://localhost:5000"
CHAT_ENDPOINT = f"{BASE_URL}/chat"

def test_chat_without_history():
    """Test chat without conversation history"""
    print("🧪 Testing chat without history...")
    
    payload = {
        "message": "Hello, what's your name?",
        "stream": False
    }
    
    response = requests.post(CHAT_ENDPOINT, json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    print()

def test_chat_with_history():
    """Test chat with conversation history"""
    print("🧪 Testing chat with conversation history...")
    
    # Simulate a conversation history
    messages_history = [
        {
            "role": "user",
            "content": "Hello, what's your name?"
        },
        {
            "role": "assistant", 
            "content": "Hello! I'm Claude, an AI assistant created by Anthropic. How can I help you today?"
        },
        {
            "role": "user",
            "content": "What's the weather like?"
        },
        {
            "role": "assistant",
            "content": "I don't have access to real-time weather data. To get current weather information, I'd recommend checking a weather website like Weather.com or using a weather app on your device."
        }
    ]
    
    payload = {
        "message": "Can you remember what we talked about earlier?",
        "messages": messages_history,
        "stream": False
    }
    
    response = requests.post(CHAT_ENDPOINT, json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    print()

def test_chat_with_streaming():
    """Test streaming chat with history"""
    print("🧪 Testing streaming chat with history...")
    
    messages_history = [
        {
            "role": "user",
            "content": "Tell me about Python"
        },
        {
            "role": "assistant",
            "content": "Python is a high-level, interpreted programming language known for its simplicity and readability."
        }
    ]
    
    payload = {
        "message": "Can you give me more details about what we just discussed?",
        "messages": messages_history,
        "stream": True
    }
    
    response = requests.post(CHAT_ENDPOINT, json=payload, stream=True)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        print("Streaming response:")
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    try:
                        data = json.loads(line_str[6:])  # Remove 'data: ' prefix
                        if data.get('type') == 'token':
                            print(data.get('content', ''), end='', flush=True)
                        elif data.get('type') == 'done':
                            print("\n✅ Streaming complete")
                            break
                    except json.JSONDecodeError:
                        continue
    else:
        print(f"Error: {response.text}")
    print()

def test_health_check():
    """Test health check endpoint"""
    print("🧪 Testing health check...")
    
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

if __name__ == "__main__":
    print("🚀 Starting chat history tests...\n")
    
    try:
        # Test health check first
        test_health_check()
        
        # Test different scenarios
        test_chat_without_history()
        test_chat_with_history()
        test_chat_with_streaming()
        
        print("✅ All tests completed!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to the server. Make sure the Flask app is running on localhost:5000")
    except Exception as e:
        print(f"❌ Error: {e}")