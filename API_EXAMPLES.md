# Chat API with Conversation History

## Overview

The chat API now supports conversation history, allowing the frontend to send previous messages for context-aware responses. This improves the conversational experience while keeping the backend stateless.

## API Endpoint

`POST /chat`

## Request Format

### Basic Request (No History)
```json
{
  "message": "Hello, how are you?",
  "stream": true
}
```

### Request with Conversation History
```json
{
  "message": "Can you elaborate on that?",
  "messages": [
    {
      "role": "user",
      "content": "What is machine learning?"
    },
    {
      "role": "assistant", 
      "content": "Machine learning is a subset of artificial intelligence that enables computers to learn and improve from experience without being explicitly programmed."
    },
    {
      "role": "user",
      "content": "What are the main types?"
    },
    {
      "role": "assistant",
      "content": "The main types of machine learning are supervised learning, unsupervised learning, and reinforcement learning."
    }
  ],
  "stream": true
}
```

## Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `message` | string | Yes | The current user message |
| `messages` | array | No | Array of previous conversation messages |
| `stream` | boolean | No | Whether to stream the response (default: true) |

### Message Object Format

Each message in the `messages` array should have:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `role` | string | Yes | Either "user" or "assistant" |
| `content` | string | Yes | The message content |

**Note:** The API also supports `type` instead of `role` for backward compatibility.

## Response Format

### Streaming Response (stream: true)
Server-sent events with JSON data:

```
data: {"content": "Hello", "type": "token"}
data: {"content": "!", "type": "token"}
data: {"type": "done"}
```

### Non-streaming Response (stream: false)
```json
{
  "response": "Hello! I'm doing well, thank you for asking. How can I help you today?",
  "model": "gpt-4o",
  "agent": "autogen_assistant"
}
```

## Frontend Implementation Example

### JavaScript/TypeScript
```typescript
interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: Date;
}

class ChatService {
  private messages: ChatMessage[] = [];

  async sendMessage(message: string): Promise<string> {
    // Add user message to history
    this.messages.push({
      role: 'user',
      content: message,
      timestamp: new Date()
    });

    // Send request with conversation history
    const response = await fetch('/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        message: message,
        messages: this.messages.slice(-10), // Send last 10 messages for context
        stream: false
      })
    });

    const data = await response.json();
    
    // Add assistant response to history
    this.messages.push({
      role: 'assistant',
      content: data.response,
      timestamp: new Date()
    });

    return data.response;
  }

  clearHistory() {
    this.messages = [];
  }
}
```

### React Hook Example
```typescript
import { useState, useCallback } from 'react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  id: string;
}

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = useCallback(async (content: string) => {
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: content,
          messages: messages.map(m => ({ role: m.role, content: m.content })),
          stream: false
        })
      });

      const data = await response.json();
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.response
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Chat error:', error);
    } finally {
      setIsLoading(false);
    }
  }, [messages]);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  return {
    messages,
    sendMessage,
    clearMessages,
    isLoading
  };
}
```

## Benefits of Frontend-Managed History

1. **Better UX**: Immediate message display, offline history viewing
2. **Scalability**: Stateless backend, easier horizontal scaling
3. **Performance**: Reduced server memory usage, faster responses
4. **Flexibility**: Frontend controls context length and management
5. **Privacy**: Conversation history stays client-side

## Migration Guide

### From Old API
```json
// Old format
{
  "message": "What did we discuss about Python?"
}
```

### To New API
```json
// New format with context
{
  "message": "What did we discuss about Python?",
  "messages": [
    {
      "role": "user",
      "content": "Tell me about Python programming"
    },
    {
      "role": "assistant",
      "content": "Python is a versatile programming language..."
    }
  ]
}
```

The old format still works - if no `messages` array is provided, the API treats it as a new conversation.