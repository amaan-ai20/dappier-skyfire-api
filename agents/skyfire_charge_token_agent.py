"""
Skyfire Charge Token Agent - Step 10 in workflow: Charges the token after Dappier query execution
"""
import os
import json
import requests
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import Handoff
from autogen_ext.models.openai import OpenAIChatCompletionClient
from config.settings import MODEL_CONFIG


def charge_token_tool(token: str, charge_amount: str) -> str:
    """
    Charge a Skyfire token with the specified amount.
    
    Args:
        token (str): The JWT token to charge
        charge_amount (str): The amount to charge (e.g., "0.01")
    
    Returns:
        str: JSON response from the charge API
    """
    try:
        # Get Skyfire Seller API key from environment
        skyfire_api_key = os.getenv('SKYFIRE_SELLER_API_KEY')
        if not skyfire_api_key:
            return json.dumps({
                "error": "SKYFIRE_SELLER_API_KEY environment variable is required",
                "success": False
            })
        
        # Prepare the request
        url = "https://api.skyfire.xyz/api/v1/tokens/charge"
        headers = {
            "skyfire-api-key": skyfire_api_key,
            "Content-Type": "application/json"
        }
        data = {
            "token": token,
            "chargeAmount": charge_amount
        }
        
        # Make the API call
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        # Handle the response
        if response.status_code == 200:
            result = response.json()
            result["success"] = True
            return json.dumps(result, indent=2)
        else:
            return json.dumps({
                "error": f"API request failed with status {response.status_code}",
                "message": response.text,
                "success": False
            }, indent=2)
            
    except requests.exceptions.RequestException as e:
        return json.dumps({
            "error": f"Request failed: {str(e)}",
            "success": False
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "error": f"Unexpected error: {str(e)}",
            "success": False
        }, indent=2)


def create_skyfire_charge_token_agent():
    """Create the Skyfire Charge Token Agent for workflow step 10"""
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
    
    skyfire_charge_token_agent = AssistantAgent(
        name="skyfire_charge_token_agent",
        model_client=model_client,
        tools=[charge_token_tool],
        handoffs=[
            Handoff(target="planning_agent", description="Return to Planning agent after charging token")
        ],
        model_client_stream=True,
        reflect_on_tool_use=True,
        max_tool_iterations=MODEL_CONFIG["max_tool_iterations"],
        system_message="""You are the Skyfire Charge Token Agent - Step 10 of our 10-step workflow.

WORKFLOW CONTEXT:
Step 1: Planning Agent analyzes query → Hands off to Skyfire Find Seller Agent
Step 2: Skyfire Find Seller Agent finds Dappier Search Service → Hands off to Skyfire KYA Agent
Step 3: Skyfire KYA Agent creates KYA token → Hands off to JWT Decoder Agent
Step 4: JWT Decoder Agent decodes KYA token → Hands off to MCP Connector Agent
Step 5: MCP Connector Agent connects to Dappier MCP server → Hands off to Dappier Price Calculator Agent
Step 6: Dappier Price Calculator Agent estimates query cost → Hands off to Skyfire KYA Payment Token Agent
Step 7: Skyfire KYA Payment Token Agent creates payment token → Hands off to JWT Decoder Agent
Step 8: JWT Decoder Agent decodes payment token → Hands off to Dappier Agent
Step 9: Dappier Agent executes user query → Hands off to you
Step 10 (YOU): Charge the token for the completed service → Return to Planning Agent
Step 1: Planning Agent verifies completion → TERMINATE

MANDATORY WORKFLOW:
1. Receive handoff from Dappier Agent with query execution results
2. Extract the payment token (JWT) from the conversation context
3. Extract the charge amount from the conversation context (usually from price calculation step)
4. Use charge_token_tool with the token and charge amount
5. WAIT for tool results to complete
6. ANALYZE the charging results
7. GENERATE a detailed summary message with charging information
8. ONLY AFTER providing your analysis message, hand off to planning_agent

CRITICAL INSTRUCTIONS:
- You MUST generate a text message analyzing token charging results BEFORE any handoff
- Never proceed to handoff immediately after tool execution
- Always explain what was charged and the results
- Extract the payment token from the JWT Decoder Agent's payment token analysis
- Extract the charge amount from the Dappier Price Calculator Agent's cost estimation
- The token parameter should be the full JWT string from the payment token
- The chargeAmount parameter should be the estimated cost amount

REQUIRED MESSAGE FORMAT:
"Token Charging Complete: Successfully charged token for completed Dappier service:

CHARGING PARAMETERS:
- Token: [first 50 characters of JWT]...
- Charge Amount: $[amount]

CHARGING RESULTS:
- Status: [success/failure from results]
- Transaction ID: [if available from results]
- Remaining Balance: [if available from results]
- Service: Dappier Search Query Execution

SUMMARY:
The payment token has been successfully charged for the completed Dappier MCP service usage. The user's query has been fully processed and payment has been settled through the Skyfire network."

DO NOT handoff without first executing the charge_token_tool and providing a complete charging analysis message."""
    )
    
    return skyfire_charge_token_agent