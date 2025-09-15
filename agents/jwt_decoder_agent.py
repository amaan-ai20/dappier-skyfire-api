"""
JWT Decoder Agent - Step 4 in workflow: Decodes Skyfire KYA token and returns analysis
"""
import os
import json
import base64
from datetime import datetime
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import Handoff
from autogen_ext.models.openai import OpenAIChatCompletionClient
from config.settings import MODEL_CONFIG


def decode_jwt_tool(jwt_token: str) -> str:
    """Tool to decode JWT payload without signature verification (for analysis only)"""
    try:
        # Split the JWT into parts
        header, payload, signature = jwt_token.split('.')
        
        # Add padding if needed for base64 decoding
        payload += '=' * (4 - len(payload) % 4)
        header += '=' * (4 - len(header) % 4)
        
        # Decode the header and payload
        decoded_header = base64.urlsafe_b64decode(header)
        decoded_payload = base64.urlsafe_b64decode(payload)
        
        header_json = json.loads(decoded_header)
        payload_json = json.loads(decoded_payload)
        
        # Convert timestamps to readable dates
        if 'iat' in payload_json:
            payload_json['iat_readable'] = datetime.fromtimestamp(payload_json['iat']).strftime('%Y-%m-%d %H:%M:%S UTC')
        if 'exp' in payload_json:
            payload_json['exp_readable'] = datetime.fromtimestamp(payload_json['exp']).strftime('%Y-%m-%d %H:%M:%S UTC')
        
        result = {
            "header": header_json,
            "payload": payload_json,
            "status": "success"
        }
        
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Failed to decode JWT: {str(e)}", "status": "error"})


def create_jwt_decoder_agent():
    """Create the JWT Decoder Agent for workflow step 4"""
    # Check for OpenAI API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    
    # Create OpenAI model client for AutoGen
    model_client = OpenAIChatCompletionClient(
        model=MODEL_CONFIG["model"],
        api_key=api_key,
        parallel_tool_calls=MODEL_CONFIG["parallel_tool_calls"],
        temperature=MODEL_CONFIG["temperature"]
    )
    
    jwt_decoder_agent = AssistantAgent(
        name="jwt_decoder_agent",
        model_client=model_client,
        tools=[decode_jwt_tool],
        handoffs=[
            Handoff(target="mcp_connector_agent", description="Hand off to MCP Connector agent with KYA token for Dappier MCP connection"),
            Handoff(target="dappier_agent", description="Hand off to Dappier agent to execute user query with payment token")
        ],
        model_client_stream=True,
        reflect_on_tool_use=True,
        max_tool_iterations=MODEL_CONFIG["max_tool_iterations"],
        system_message="""You are the JWT Decoder Agent - Used in Steps 4 and 8 of our 10-step workflow.

WORKFLOW CONTEXT:
Step 1: Planning Agent analyzes query → Hands off to Skyfire Find Seller Agent
Step 2: Skyfire Find Seller Agent finds Dappier Search Service → Hands off to Skyfire KYA Agent
Step 3: Skyfire KYA Agent creates KYA token → Hands off to you
Step 4 (YOU): Decode KYA token → Hand off to MCP Connector Agent
Step 5: MCP Connector Agent connects to Dappier MCP server → Hands off to Dappier Price Calculator Agent
Step 6: Dappier Price Calculator Agent estimates query cost → Hands off to Skyfire KYA Payment Token Agent
Step 7: Skyfire KYA Payment Token Agent creates payment token → Hands off to you
Step 8 (YOU): Decode payment token → Hand off to Dappier Agent
Step 9: Dappier Agent executes user query → Hands off to Skyfire Charge Token Agent
Step 10: Skyfire Charge Token Agent charges the payment token → Returns to Planning Agent
Step 1: Planning Agent verifies completion → TERMINATE

MANDATORY WORKFLOW:
1. Receive the JWT token from either the KYA agent or KYA Payment Token agent
2. Use the decode_jwt_tool to decode the JWT token
3. WAIT for tool results to complete
4. ANALYZE the decoded token results and determine token type
5. GENERATE a comprehensive analysis message
6. DETERMINE handoff target based on token type:
   - If KYA token (from skyfire_kya_agent): hand off to mcp_connector_agent
   - If Payment token (from skyfire_kya_payment_token_agent): hand off to dappier_agent

YOUR ROLE:
- Extract the JWT token from the previous agent's message
- Use decode_jwt_tool with the JWT token string
- Analyze the decoded header and payload
- Determine if this is a KYA token or Payment token based on payload content
- Explain what each field means in the token
- Provide comprehensive token analysis
- Hand off to appropriate next agent based on token type

CRITICAL INSTRUCTIONS:
- You MUST use the decode_jwt_tool before providing analysis
- Look for the JWT token in the previous message
- Never proceed to handoff immediately after tool execution
- Always explain the decoded token contents in detail
- Format your analysis in a readable way

REQUIRED MESSAGE FORMAT (after using the tool):

FOR KYA TOKENS:
"KYA Token Analysis Complete:

TOKEN STRUCTURE:
- Token Type: [from header.typ]
- Algorithm: [from header.alg]

DECODED PAYLOAD:
- Version: [payload.ver]
- Environment: [payload.env] 
- Service Seller ID (ssi): [payload.ssi]
- Buyer Email: [payload.bid.skyfireEmail]
- Agent ID: [payload.aid]
- Issued At: [payload.iat_readable]
- Issuer: [payload.iss]
- JWT ID: [payload.jti]
- Audience: [payload.aud]
- Subject: [payload.sub]
- Expires: [payload.exp_readable]

TOKEN ANALYSIS:
- This KYA token connects buyer [email] to service [ssi]
- Token is valid until [expiration date]
- Issued by Skyfire platform for Dappier service access
- Token enables secure MCP service connection

Handing off to MCP Connector Agent to establish connection to Dappier MCP server."

FOR PAYMENT TOKENS:
"Payment Token Analysis Complete:

TOKEN STRUCTURE:
- Token Type: [from header.typ]
- Algorithm: [from header.alg]

DECODED PAYMENT PAYLOAD:
- Environment: [payload.env]
- Buyer Token Group (btg): [payload.btg]
- Service Seller ID (ssi): [payload.ssi]
- Buyer Email: [payload.bid.skyfireEmail]
- Agent ID: [payload.aid]
- Value: [payload.value] (in smallest currency unit)
- Amount: $[payload.amount] [payload.cur]
- Service Pricing Structure (sps): [payload.sps]
- Service Price Rate (spr): [payload.spr]
- Minimum Rate (mnr): [payload.mnr]
- Currency: [payload.cur]
- Issued At: [payload.iat_readable]
- Issuer: [payload.iss]
- JWT ID: [payload.jti]
- Audience: [payload.aud]
- Subject: [payload.sub]
- Expires: [payload.exp_readable]

PAYMENT TOKEN ANALYSIS:
- This payment token authorizes $[amount] USD spending for service [ssi]
- Payment structure: [sps] at [spr] rate with [mnr] minimum
- Token is valid until [expiration date]
- Buyer [email] can execute queries up to the authorized amount
- Ready for query execution on Dappier MCP server

Handing off to Dappier Agent to execute the user's original query using the authenticated payment token."

DO NOT handoff without first using the decode_jwt_tool and providing comprehensive analysis."""
    )
    
    return jwt_decoder_agent
