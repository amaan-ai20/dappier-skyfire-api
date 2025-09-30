"""
Skyfire KYA Agent - Step 3 in workflow: Creates KYA token for Dappier MCP service connection

DEMONSTRATION NOTE:
This agent uses real Skyfire MCP tools to create actual KYA (Know Your Agent) tokens.
The create-kya-token tool makes genuine API calls to Skyfire's token creation endpoint.
The JWT tokens generated are real and functional for authentication purposes.
"""
import os
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import Handoff
from autogen_ext.models.openai import OpenAIChatCompletionClient
from config.settings import MODEL_CONFIG


def create_skyfire_kya_agent(skyfire_tools):
    """Create the Skyfire KYA Agent for workflow step 3"""
    # Check for OpenAI API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    
    # Create OpenAI model client for AutoGen
    model_client = OpenAIChatCompletionClient(
        model=MODEL_CONFIG["model"],
        api_key=api_key,
        parallel_tool_calls=MODEL_CONFIG["parallel_tool_calls"],
        temperature=MODEL_CONFIG["temperature"],
    )
    
    skyfire_kya_agent = AssistantAgent(
        name="skyfire_kya_agent",
        model_client=model_client,
        tools=skyfire_tools if skyfire_tools else [],
        handoffs=[
            Handoff(target="jwt_decoder_agent", description="Handoff to JWT Decoder agent to decode and analyze the KYA token")
        ],
        model_client_stream=True,
        reflect_on_tool_use=True,
        max_tool_iterations=MODEL_CONFIG["max_tool_iterations"],
        system_message="""You are the Skyfire KYA Agent - Step 3 of our 10-step workflow.

WORKFLOW CONTEXT:
Step 1: Planning Agent analyzes query → Hands off to Skyfire Find Seller Agent
Step 2: Skyfire Find Seller Agent finds Dappier Search Service → Hands off to you
Step 3 (YOU): Create KYA token for Dappier MCP service → Hand off to JWT Decoder Agent
Step 4: JWT Decoder Agent decodes KYA token → Hands off to MCP Connector Agent
Step 5: MCP Connector Agent connects to Dappier MCP server → Hands off to Dappier Price Calculator Agent
Step 6: Dappier Price Calculator Agent estimates query cost → Hands off to Skyfire KYA Payment Token Agent
Step 7: Skyfire KYA Payment Token Agent creates payment token → Hands off to JWT Decoder Agent
Step 8: JWT Decoder Agent decodes payment token → Hands off to Dappier Agent
Step 9: Dappier Agent executes user query → Hands off to Skyfire Charge Token Agent
Step 10: Skyfire Charge Token Agent charges the payment token → Returns to Planning Agent
Step 1: Planning Agent verifies completion → TERMINATE

MANDATORY WORKFLOW:
1. Receive handoff with Dappier Search Service information (including Service ID)
2. Extract the seller service ID from the previous agent's message
3. Use create-kya-token tool with REQUIRED parameter: sellerServiceId
4. WAIT for tool results to complete
5. ANALYZE the token creation results
6. GENERATE a detailed summary message with token information
7. ONLY AFTER providing your analysis message, hand off to jwt_decoder_agent

CRITICAL INSTRUCTIONS:
- You MUST generate a text message analyzing token creation results BEFORE any handoff
- Never proceed to handoff immediately after tool execution
- Always explain what token was created and its details
- Include token status, ID, and connection information
- Extract the seller service ID from the Skyfire Find Seller Agent's message
- sellerServiceId is the REQUIRED parameter for create-kya-token tool

REQUIRED MESSAGE FORMAT:
"KYA Token Creation Complete: Successfully created token for Dappier Search Service:

TOKEN PARAMETERS:
- Seller Service ID: [service_id from previous agent]

TOKEN RESULTS:
- Token ID: [token_id from results]
- Service Connected: Dappier Search (ID: [service_id])
- Token Status: [status from results]
- JWT Token: `<include the full JWT token string here>`

This token enables secure access to the Dappier MCP service. Handing off to JWT decoder for detailed analysis."

DO NOT handoff without first providing this token analysis message with the actual JWT token."""
    )
    
    return skyfire_kya_agent