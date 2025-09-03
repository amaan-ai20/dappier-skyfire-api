# Overview

This is a Flask-based REST API that serves as a wrapper around OpenAI's GPT models. The application provides a simple HTTP interface for chat completions, allowing clients to send messages and receive AI-generated responses. It's designed as a lightweight microservice that can be easily deployed and integrated into larger systems.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Web Framework
- **Flask**: Chosen for its simplicity and lightweight nature, perfect for a microservice API
- **RESTful Design**: Implements standard HTTP methods and JSON communication
- **Single-file Architecture**: Keeps the codebase simple and maintainable for this focused use case

## API Design
- **Health Check Endpoint** (`/health`): Provides service monitoring capabilities
- **Chat Completion Endpoint** (`/chat`): Main functionality for OpenAI interactions
- **JSON Communication**: Standard request/response format for easy integration
- **Error Handling**: Structured error responses with appropriate HTTP status codes

## Configuration Management
- **Environment Variables**: Uses `.env` files for sensitive configuration like API keys
- **python-dotenv**: Handles loading of environment variables in development
- **Lazy Client Initialization**: OpenAI client is created only when needed to optimize startup time

## Request Processing
- **Flexible Parameters**: Supports customizable model selection, token limits, and temperature settings
- **Validation**: Input validation ensures required fields are present
- **Default Values**: Sensible defaults (gpt-3.5-turbo, 150 tokens, 0.7 temperature) for optional parameters

# External Dependencies

## AI Service
- **OpenAI API**: Primary dependency for chat completion functionality
- **Authentication**: Requires OPENAI_API_KEY environment variable
- **Models Supported**: Configurable model selection with gpt-3.5-turbo as default

## Python Libraries
- **Flask**: Web framework for HTTP request handling
- **openai**: Official OpenAI Python client library
- **python-dotenv**: Environment variable management

## Runtime Requirements
- **Python Environment**: Requires Python runtime with pip package management
- **Environment Configuration**: Needs proper setup of environment variables for API keys