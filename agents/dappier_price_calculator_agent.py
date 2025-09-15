"""
Dappier Price Calculator Agent - Step 6 in workflow: Estimates cost of running user query on Dappier MCP server
"""
import os
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import Handoff
from autogen_ext.models.openai import OpenAIChatCompletionClient
from config.settings import MODEL_CONFIG


def create_dappier_price_calculator_agent():
    """Create the Dappier Price Calculator Agent for workflow step 6"""
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
    
    dappier_price_calculator_agent = AssistantAgent(
        name="dappier_price_calculator_agent",
        model_client=model_client,
        handoffs=[
            Handoff(target="skyfire_kya_payment_token_agent", description="Hand off to Skyfire KYA Payment Token Agent to create payment token with estimated cost")
        ],
        model_client_stream=True,
        system_message="""You are the Dappier Price Calculator Agent - Step 6 of our workflow.

YOUR TASK:
1. Find the original user query from the conversation history
2. Review the available Dappier tools and pricing from the MCP Connector Agent
3. Determine which tools would be needed for the user's query
4. Calculate the estimated cost
5. Hand off to skyfire_kya_payment_token_agent

ANALYSIS APPROACH:
- Match the user query type to appropriate Dappier tools
- Use simple reasoning - don't overcomplicate tool selection
- Focus on the most relevant tools for the query
- Provide a clear cost estimate

KEEP IT SIMPLE:
- Only estimate tools that are clearly needed
- Don't over-analyze or suggest unnecessary tools
- Be concise in your reasoning
- Provide a straightforward cost breakdown

FORMAT YOUR RESPONSE:
"Cost Analysis:

Query: [original user query]
Selected Tools: [tool names that would be used]
Reasoning: [brief explanation of why these tools]

Cost Breakdown:
- [tool]: $[cost] USD ([reasoning])
- Total: $[total] USD

Ready to proceed with payment token creation."

Then hand off to skyfire_kya_payment_token_agent."""
    )
    
    return dappier_price_calculator_agent