"""
Skyfire Find Seller Agent - Step 2 in workflow: Finds Dappier Search Service and hands off to KYA Agent
"""
import os
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import Handoff
from autogen_ext.models.openai import OpenAIChatCompletionClient
from config.settings import MODEL_CONFIG


def create_skyfire_find_seller_agent(skyfire_tools):
    """Create the Skyfire Find Seller Agent for workflow step 2"""
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
    
    skyfire_find_seller_agent = AssistantAgent(
        name="skyfire_find_seller_agent",
        model_client=model_client,
        tools=skyfire_tools if skyfire_tools else [],
        handoffs=[
            Handoff(target="skyfire_kya_agent", description="Handoff to Skyfire KYA agent to create KYA token for Dappier service connection")
        ],
        model_client_stream=True,
        reflect_on_tool_use=True,
        max_tool_iterations=MODEL_CONFIG["max_tool_iterations"],
        system_message="""You are the Skyfire Find Seller Agent - Step 2 of our 9-step workflow.

WORKFLOW CONTEXT:
Step 1: Planning Agent analyzes query → Hands off to you
Step 2 (YOU): Find Dappier Search Service → Hand off to Skyfire KYA Agent
Step 3: Skyfire KYA Agent creates KYA token → Hands off to JWT Decoder Agent
Step 4: JWT Decoder Agent decodes KYA token → Hands off to MCP Connector Agent
Step 5: MCP Connector Agent connects to Dappier MCP server → Hands off to Dappier Price Calculator Agent
Step 6: Dappier Price Calculator Agent estimates query cost → Hands off to Skyfire KYA Payment Token Agent
Step 7: Skyfire KYA Payment Token Agent creates payment token → Hands off to JWT Decoder Agent
Step 8: JWT Decoder Agent decodes payment token → Hands off to Dappier Agent
Step 9: Dappier Agent executes user query → Returns to Planning Agent
Step 1: Planning Agent verifies completion → TERMINATE

MANDATORY WORKFLOW:
1. Use find-sellers tool to search for services on Skyfire network
2. WAIT for tool results to complete
3. ANALYZE the JSON results and identify "Dappier Search" service
4. GENERATE a detailed summary message with service information
5. ONLY AFTER providing your analysis message, hand off to skyfire_kya_agent

CRITICAL INSTRUCTIONS:
- You MUST generate a text message analyzing tool results BEFORE any handoff
- Never proceed to handoff immediately after tool execution
- Always explain what you found in the tool results
- Look specifically for "Dappier Search" service in the JSON response
- Format your analysis with: Name, Description, Seller, Service ID, Price

REQUIRED MESSAGE FORMAT:
"Analysis Complete: I found the Dappier Search Service with these details:
- Service Name: [name from JSON]
- Service ID: [id from JSON]  
- Description: [description from JSON]
- Seller: [seller.name from JSON]
- Price: [price from JSON]
- This service provides [capabilities summary]
Now proceeding to create KYA token..."

DO NOT handoff without first providing this analysis message."""
    )
    
    return skyfire_find_seller_agent
