"""
Planning Agent - The orchestrator that delegates to Skyfire and verifies task completion
"""
import os
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import Handoff
from autogen_ext.models.openai import OpenAIChatCompletionClient
from config.settings import MODEL_CONFIG


def create_planning_agent():
    """Create the Planning Agent (orchestrator)"""
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
    
    planning_agent = AssistantAgent(
        name="planning_agent",
        model_client=model_client,
        handoffs=[
            Handoff(target="skyfire_find_seller_agent", description="Handoff to Skyfire agent to search for Dappier services")
        ],
        model_client_stream=True,
        reflect_on_tool_use=True,
        max_tool_iterations=MODEL_CONFIG["max_tool_iterations"],
        system_message="""You are the Planning Agent - Step 1 of our 9-step workflow.

WORKFLOW CONTEXT:
Step 1 (YOU): Analyze query → Hand off to Skyfire Find Seller Agent
Step 2: Skyfire Find Seller Agent finds Dappier Search Service → Hands off to Skyfire KYA Agent
Step 3: Skyfire KYA Agent creates KYA token → Hands off to JWT Decoder Agent
Step 4: JWT Decoder Agent decodes KYA token → Hands off to MCP Connector Agent
Step 5: MCP Connector Agent connects to Dappier MCP server → Hands off to Dappier Price Calculator Agent
Step 6: Dappier Price Calculator Agent estimates query cost → Hands off to Skyfire KYA Payment Token Agent
Step 7: Skyfire KYA Payment Token Agent creates payment token → Hands off to JWT Decoder Agent
Step 8: JWT Decoder Agent decodes payment token → Hands off to Dappier Agent
Step 9: Dappier Agent executes user query → Returns to you
Step 1 (YOU): Verify task completion and query results → TERMINATE

YOUR ROLE:
- For real-time information requests: Hand off to skyfire_find_seller_agent
- When dappier_agent returns with query results: Review the complete workflow results and user query response, then immediately use TERMINATE
- For non real-time queries: Answer directly and TERMINATE

CRITICAL: Always use TERMINATE after dappier_agent returns to you with the final query results. Do not continue the conversation.

Real-time queries include: news, weather, stocks, research papers, breaking news, current events."""
    )
    
    return planning_agent
