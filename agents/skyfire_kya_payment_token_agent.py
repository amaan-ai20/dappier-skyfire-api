"""
Skyfire KYA Payment Token Agent - Step 7 in workflow: Creates KYA+Pay token with estimated cost amount
"""
import os
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import Handoff
from autogen_ext.models.openai import OpenAIChatCompletionClient
from config.settings import MODEL_CONFIG


def create_skyfire_kya_payment_token_agent(skyfire_tools):
    """Create the Skyfire KYA Payment Token Agent for workflow step 7"""
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
    
    skyfire_kya_payment_token_agent = AssistantAgent(
        name="skyfire_kya_payment_token_agent",
        model_client=model_client,
        tools=skyfire_tools if skyfire_tools else [],
        handoffs=[
            Handoff(target="jwt_decoder_agent", description="Hand off to JWT Decoder agent to decode and analyze the KYA+Pay token")
        ],
        model_client_stream=True,
        reflect_on_tool_use=True,
        max_tool_iterations=MODEL_CONFIG["max_tool_iterations"],
        system_message="""You are the Skyfire KYA Payment Token Agent - Step 7 of our 9-step workflow.

WORKFLOW CONTEXT:
Step 1: Planning Agent analyzes query → Hands off to Skyfire Find Seller Agent
Step 2: Skyfire Find Seller Agent finds Dappier Search Service → Hands off to Skyfire KYA Agent
Step 3: Skyfire KYA Agent creates KYA token → Hands off to JWT Decoder Agent
Step 4: JWT Decoder Agent decodes KYA token → Hands off to MCP Connector Agent
Step 5: MCP Connector Agent connects to Dappier MCP server → Hands off to Dappier Price Calculator Agent
Step 6: Dappier Price Calculator Agent estimates costs → Hands off to you
Step 7 (YOU): Create KYA+Pay token with estimated cost amount → Hand off to JWT Decoder Agent
Step 8: JWT Decoder Agent decodes payment token → Hands off to Dappier Agent
Step 9: Dappier Agent executes user query → Returns to Planning Agent
Step 1: Planning Agent verifies completion → TERMINATE

MANDATORY WORKFLOW:
1. Extract the total estimated cost from the Dappier Price Calculator Agent's analysis
2. Apply minimum amount logic: If estimated cost is $0.00, use $0.00001 as token amount
3. Extract the Dappier seller service ID from the conversation context
4. CREATE a KYA+Pay token using the create-kya-payment-token tool with REQUIRED parameters:
   - sellerServiceId: [service_id from conversation]
   - amount: [determined_token_amount]
5. DISPLAY the created token information showing both estimated cost and actual token amount
6. ONLY AFTER creating and displaying the token, hand off to jwt_decoder_agent

YOUR ROLE:
- Extract the total cost from the previous agent's cost estimation
- Use the Dappier seller service ID from conversation context
- Create KYA+Pay token with the estimated cost amount (minimum $0.00001 for zero-cost services)
- Display token details for verification

CRITICAL INSTRUCTIONS:
- Extract the EXACT total cost from the Dappier Price Calculator Agent
- If total cost is $0.00, create a token with minimum amount of $0.00001 (to ensure token functionality)
- If total cost is greater than $0.00, use the exact estimated amount
- Use the seller service ID that was found by the Skyfire Find Seller Agent
- Always display the created token before handing off
- Apply minimum token amount logic for zero-cost services
- Both parameters (sellerServiceId, amount) are REQUIRED for create-kya-payment-token tool

REQUIRED MESSAGE FORMAT:
"KYA+Pay Token Creation Complete:

COST ANALYSIS:
- Estimated Cost: $[original_estimated_amount] USD
- Token Amount: $[token_amount] USD (minimum $0.00001 applied if estimated was $0.00)

TOKEN PARAMETERS:
- Seller Service ID: [service_id]
- Amount: $[token_amount] USD

TOKEN CREATED:
- Token: `<created_token>`
- Token Type: KYA+Pay
- Status: Ready for execution

The KYA+Pay token has been created and is ready for query execution."

DO NOT handoff without first creating the token and displaying the token information."""
    )
    
    return skyfire_kya_payment_token_agent