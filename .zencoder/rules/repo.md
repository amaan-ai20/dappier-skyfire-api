---
description: Repository Information Overview
alwaysApply: true
---

# Dappier-Skyfire API Information

## Summary
This project is a Flask-based API that integrates Dappier and Skyfire services through a multi-agent system. It provides a bridge between these platforms using AutoGen agents to handle various tasks including real-time search, token creation, and payment processing.

## Structure
- **agents/**: Contains agent implementations for different services (JWT decoder, MCP connector, planning, price calculator, etc.)
- **config/**: Configuration settings for the application
- **routes/**: API endpoints for chat, health checks, initialization, and sessions
- **services/**: Service implementations for MCP and session management
- **utils/**: Helper utilities and common functions

## Language & Runtime
**Language**: Python
**Version**: Python 3.11+
**Framework**: Flask 3.0.0+
**Package Manager**: pip (with pyproject.toml)

## Dependencies
**Main Dependencies**:
- autogen-agentchat >= 0.7.4
- autogen-ext[openai,mcp] >= 0.7.4
- flask >= 3.0.0
- flask-cors >= 6.0.1
- gunicorn >= 23.0.0
- python-dotenv >= 1.0.0

## Build & Installation
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```

## Environment Variables
**Required**:
- OPENAI_API_KEY: API key for OpenAI services
- SKYFIRE_API_KEY: API key for Skyfire MCP server

## API Components
**MCP Servers**:
- Dappier MCP: https://mcp.dappier.com/mcp
- Skyfire MCP: https://mcp.skyfire.xyz/mcp

**Agent System**:
- Planning Agent: Orchestrates tasks between specialized agents
- Skyfire Find Seller Agent: Discovers services on Skyfire network
- Skyfire KYA Agent: Creates KYA tokens for service access
- JWT Decoder Agent: Decodes and analyzes JWT tokens
- MCP Connector Agent: Establishes connections to Dappier MCP
- Dappier Price Calculator Agent: Estimates query execution costs

## Running the Application
```bash
# Development mode
python app.py  # Runs on 0.0.0.0:5000 with debug=True

# Production mode
gunicorn app:app
```

## Session Management
- Maximum sessions: 100
- Session timeout: 3600 seconds (1 hour)
- Cleanup interval: 300 seconds (5 minutes)

## Model Configuration
- Model: gpt-4o
- Temperature: 0.1
- Parallel tool calls: Disabled
- Maximum tool iterations: 10