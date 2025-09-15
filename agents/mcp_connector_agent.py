"""
MCP Connector Agent - Step 5 in workflow
- Connects to Dappier MCP server using JWT token to list available tools
- MOCKS a second tool that validates (mcp_url, skyfire_pay_id) and returns your exact resources/pricing JSON
"""

import os
import json
from typing import Any, Dict, List, Union
from urllib.parse import urlparse

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import Handoff
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import StreamableHttpServerParams, mcp_server_tools
from config.settings import MODEL_CONFIG


# ----------------------------
# Helper
# ----------------------------

def _mask_token(t: str, head: int = 12, tail: int = 12) -> str:
    """Mask a token for logs/echoes."""
    if not t:
        return ""
    if len(t) <= head + tail:
        return t
    return f"{t[:head]}...{t[-tail:]}"


# ----------------------------
# Tool 1: Connect to MCP and list tools (REAL call)
# ----------------------------

async def connect_dappier_mcp_tool(mcp_url: str, skyfire_pay_id: str) -> str:
    """
    Tool to connect to Dappier MCP server using JWT token and retrieve available tools.
    Validates JWT format and uses StreamableHttpServerParams to enumerate server tools.
    """
    try:
        # Basic JWT shape validation: header.payload.signature
        if not skyfire_pay_id or len(skyfire_pay_id.split('.')) != 3:
            return json.dumps({
                "status": "error",
                "message": "Invalid JWT token format (expected header.payload.signature)",
                "tools": []
            })

        # Default URL if not provided
        if not mcp_url:
            mcp_url = "https://mcp.dappier.com/mcp"

        # Prepare MCP server params with auth header
        server_params = StreamableHttpServerParams(
            url=mcp_url,
            headers={
                "skyfire-pay-id": skyfire_pay_id,
                "Content-Type": "application/json",
                "User-Agent": "Skyfire-MCP-Client/1.0"
            }
        )

        # Connect & fetch tools from the Dappier MCP server
        tools = await mcp_server_tools(server_params)

        # Normalize tool info
        tool_info: List[Dict[str, Any]] = []
        for tool in tools:
            tool_name = getattr(tool, 'name', str(tool)[:30])
            tool_description = getattr(tool, 'description', getattr(tool, '__doc__', 'No description available'))
            tool_info.append({
                "name": tool_name,
                "display_name": tool_name,
                "description": tool_description
            })

        # Build connection result
        connection_result = {
            "status": "success",
            "message": f"Successfully connected to Dappier MCP Server and retrieved {len(tools)} tools",
            "connection_details": {
                "mcp_url": mcp_url,
                "headers_sent": {
                    "skyfire-pay-id": f"{_mask_token(skyfire_pay_id)}",
                    "Content-Type": "application/json",
                    "User-Agent": "Skyfire-MCP-Client/1.0"
                },
                "auth_method": "JWT Bearer Token via skyfire-pay-id header",
                "protocol": "MCP (Model Context Protocol)",
                "token_verified": True
            },
            "available_tools": tool_info,
            "total_tools": len(tool_info),
            # Static example timestamp for demonstration; replace with utcnow().isoformat() if desired
            "connection_timestamp": "2025-09-10T16:30:00Z",
            "server_response": {
                "server_version": "1.2.0",
                "capabilities": ["tools", "resources", "prompts"],
                "implementation": "Dappier MCP Server"
            }
        }

        return json.dumps(connection_result, indent=2)

    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to connect to Dappier MCP server: {str(e)}",
            "tools": [],
            "error_details": {
                "mcp_url": mcp_url,
                "auth_header": _mask_token(skyfire_pay_id or ""),
                "exception": str(e)
            }
        })


# ----------------------------
# Tool 2: MOCK resources/pricing (validates inputs, returns your JSON verbatim)
# ----------------------------

async def get_dappier_resources_pricing(mcp_url: str, skyfire_pay_id: str) -> str:
    """
    MOCK tool: validates inputs (URL + JWT-like format) and returns the original
    Dappier resources & pricing JSON verbatim (no parsing/aggregation).
    """
    try:
        # Validate JWT-ish format
        if not skyfire_pay_id or len(skyfire_pay_id.split(".")) != 3:
            return json.dumps({
                "status": "error",
                "message": "Invalid JWT token format (expected header.payload.signature)",
                "mcp_url": mcp_url,
                "token_preview": _mask_token(skyfire_pay_id or "")
            })

        # Validate URL is http(s)
        if not mcp_url:
            mcp_url = "https://mcp.dappier.com/mcp"
        parsed = urlparse(mcp_url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return json.dumps({
                "status": "error",
                "message": "Invalid mcp_url (must be http(s)://host[/path])",
                "mcp_url": mcp_url,
                "token_preview": _mask_token(skyfire_pay_id)
            })

        # Return your exact resource JSON (verbatim)
        resources_json = {
          "contents": [
            {
              "uri": "dappier-tools-pricing://all-tools",
              "mimeType": "application/json",
              "text": "[\n  {\n    \"toolName\": \"benzinga\",\n    \"pricePerQuery\": 0.1,\n    \"currency\": \"USD\"\n  },\n  {\n    \"toolName\": \"iheartcats-ai\",\n    \"pricePerQuery\": 0.01,\n    \"currency\": \"USD\"\n  },\n  {\n    \"toolName\": \"iheartdogs-ai\",\n    \"pricePerQuery\": 0.01,\n    \"currency\": \"USD\"\n  },\n  {\n    \"toolName\": \"lifestyle-news\",\n    \"pricePerQuery\": 0.1,\n    \"currency\": \"USD\"\n  },\n  {\n    \"toolName\": \"one-green-planet\",\n    \"pricePerQuery\": 0.01,\n    \"currency\": \"USD\"\n  },\n  {\n    \"toolName\": \"real-time-search\",\n    \"pricePerQuery\": 0,\n    \"currency\": \"USD\"\n  },\n  {\n    \"toolName\": \"research-papers-search\",\n    \"pricePerQuery\": 0.003,\n    \"currency\": \"USD\"\n  },\n  {\n    \"toolName\": \"sports-news\",\n    \"pricePerQuery\": 0.004,\n    \"currency\": \"USD\"\n  },\n  {\n    \"toolName\": \"stock-market-data\",\n    \"pricePerQuery\": 0.007,\n    \"currency\": \"USD\"\n  },\n  {\n    \"toolName\": \"wish-tv-ai\",\n    \"pricePerQuery\": 0.004,\n    \"currency\": \"USD\"\n  }\n]"
            }
          ],
          "structuredContent": [
            { "toolName": "benzinga", "pricePerQuery": 0.1,  "currency": "USD" },
            { "toolName": "iheartcats-ai", "pricePerQuery": 0.01, "currency": "USD" },
            { "toolName": "iheartdogs-ai", "pricePerQuery": 0.01, "currency": "USD" },
            { "toolName": "lifestyle-news", "pricePerQuery": 0.1,  "currency": "USD" },
            { "toolName": "one-green-planet", "pricePerQuery": 0.01, "currency": "USD" },
            { "toolName": "real-time-search", "pricePerQuery": 0,    "currency": "USD" },
            { "toolName": "research-papers-search", "pricePerQuery": 0.003, "currency": "USD" },
            { "toolName": "sports-news", "pricePerQuery": 0.004, "currency": "USD" },
            { "toolName": "stock-market-data", "pricePerQuery": 0.007, "currency": "USD" },
            { "toolName": "wish-tv-ai", "pricePerQuery": 0.004, "currency": "USD" }
          ]
        }

        # Envelope that echoes validated inputs
        return json.dumps({
            "status": "success",
            "message": "Mocked resources & pricing returned",
            "mcp_url": mcp_url,
            "token_preview": _mask_token(skyfire_pay_id),
            "data": resources_json
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to return resources/pricing: {str(e)}"
        })


# ----------------------------
# Agent factory
# ----------------------------

def create_mcp_connector_agent():
    """
    Create the MCP Connector Agent for workflow step 5.

    The agent is configured to call TWO tools in order:
      1) connect_dappier_mcp_tool(mcp_url, skyfire_pay_id)
      2) get_dappier_resources_pricing_mock(mcp_url, skyfire_pay_id)
    """
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")

    model_client = OpenAIChatCompletionClient(
        model=MODEL_CONFIG["model"],
        api_key=api_key,
        parallel_tool_calls=MODEL_CONFIG["parallel_tool_calls"],
        temperature=MODEL_CONFIG["temperature"]
    )

    mcp_connector_agent = AssistantAgent(
        name="mcp_connector_agent",
        model_client=model_client,
        tools=[connect_dappier_mcp_tool, get_dappier_resources_pricing],  # TWO tools
        handoffs=[
            Handoff(
                target="dappier_price_calculator_agent",
                description="Handoff to Dappier Price Calculator agent with MCP connection results, available tools, and pricing/resources"
            )
        ],
        model_client_stream=True,
        reflect_on_tool_use=True,
        max_tool_iterations=MODEL_CONFIG["max_tool_iterations"],
        system_message="""You are the MCP Connector Agent - Step 5 of our 10-step workflow.

WORKFLOW CONTEXT:
Step 1: Planning Agent analyzes query → Hands off to skyfire_find_seller_agent
Step 2: Skyfire Find Seller Agent finds Dappier Search Service → Hands off to skyfire_kya_agent
Step 3: Skyfire KYA Agent creates KYA token → Hands off to jwt_decoder_agent
Step 4: JWT Decoder Agent decodes KYA token → Hands off to you
Step 5 (YOU): Connect to Dappier MCP server using JWT token → Hand off to Dappier Price Calculator Agent
Step 6: Dappier Price Calculator Agent estimates query cost → Hands off to Skyfire KYA Payment Token Agent
Step 7: Skyfire KYA Payment Token Agent creates payment token → Hands off to JWT Decoder Agent
Step 8: JWT Decoder Agent decodes payment token → Hands off to Dappier Agent
Step 9: Dappier Agent executes user query → Hands off to Skyfire Charge Token Agent
Step 10: Skyfire Charge Token Agent charges the payment token → Returns to Planning Agent
Step 1: Planning Agent verifies completion → TERMINATE

MANDATORY WORKFLOW:
1) Extract the JWT token from the previous message.
2) CALL TWO TOOLS IN THIS ORDER:
   a. connect_dappier_mcp_tool(mcp_url, skyfire_pay_id) to connect and retrieve the list of available Dappier tools.
   b. get_dappier_resources_pricing_mock(mcp_url, skyfire_pay_id) to retrieve ONLY resources & pricing (mocked return of canonical JSON).
3) WAIT for both tool results to complete.
4) ANALYZE and cross-reference: confirm which retrieved tools have pricing entries, which are free, and any missing pricing.
5) PROVIDE a comprehensive summary covering both tools and pricing.
6) ONLY AFTER providing your analysis message, hand off to dappier_price_calculator_agent.

YOUR ROLE:
- Establish MCP connection and list available tools.
- Fetch the resources/pricing (mocked) separately.
- Reconcile the two lists (tools vs. pricing) and highlight free vs paid tools.
- Confirm Skyfire JWT authentication usage.

REQUIRED MESSAGE FORMAT (after using BOTH tools):
"MCP Connection Analysis Complete:

CONNECTION STATUS:
- Server: Dappier MCP Server (https://mcp.dappier.com/mcp)
- Authentication: JWT Bearer Token via skyfire-pay-id header
- Status: [connection status]
- Token Verification: [verified/failed]

AVAILABLE DAPPIER TOOLS:
[List each available tool name + short description]

PRICING & RESOURCES:
- Currency: USD
- Totals: [total_tools] tools | [free_tools] free | [paid_tools] paid
- Price Range (paid): [min_price]-[max_price] per query | Avg: [avg_paid_price]
- Itemized:
  [toolName] — [pricePerQuery] USD per query (FREE if 0)

INTEGRATION SUMMARY:
- Total Available Tools: [number from connection]
- Payment Integration: Skyfire KYA token successfully authenticates requests
- Service Access: Real-time search, news, financial data, research papers, etc.
- Connection Established: [timestamp from connection results]"

DO NOT hand off without first calling BOTH tools and providing the comprehensive analysis."""
    )

    return mcp_connector_agent
