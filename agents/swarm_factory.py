"""
Swarm Factory - Creates and configures the 9-step workflow swarm with 8 agents
"""
from autogen_agentchat.teams import Swarm
from autogen_agentchat.conditions import TextMentionTermination
from agents.planning_agent import create_planning_agent
from agents.skyfire_find_seller_agent import create_skyfire_find_seller_agent
from agents.skyfire_kya_agent import create_skyfire_kya_agent
from agents.jwt_decoder_agent import create_jwt_decoder_agent
from agents.mcp_connector_agent import create_mcp_connector_agent
from agents.dappier_price_calculator_agent import create_dappier_price_calculator_agent
from agents.skyfire_kya_payment_token_agent import create_skyfire_kya_payment_token_agent
from agents.dappier_agent import create_dappier_agent
from services.mcp_service import get_cached_tools


async def create_session_swarm():
    """Create a new Swarm instance for 9-step workflow with 8 agents"""
    cached_tools = get_cached_tools()
    skyfire_tools = cached_tools["skyfire"]
    
    planning_agent = create_planning_agent()
    skyfire_find_seller_agent = create_skyfire_find_seller_agent(skyfire_tools)
    skyfire_kya_agent = create_skyfire_kya_agent(skyfire_tools)
    jwt_decoder_agent = create_jwt_decoder_agent()
    mcp_connector_agent = create_mcp_connector_agent()
    dappier_price_calculator_agent = create_dappier_price_calculator_agent()
    skyfire_kya_payment_token_agent = create_skyfire_kya_payment_token_agent(skyfire_tools)
    dappier_agent = create_dappier_agent(cached_tools["dappier"])
    
    swarm = Swarm(
        participants=[
            planning_agent, 
            skyfire_find_seller_agent, 
            skyfire_kya_agent, 
            jwt_decoder_agent, 
            mcp_connector_agent,
            dappier_price_calculator_agent,
            skyfire_kya_payment_token_agent,
            dappier_agent
        ],
        termination_condition=TextMentionTermination("TERMINATE")
    )
    
    print(f"9-step Skyfire-Dappier integration workflow created with 8 agents")
    print(f"Available Skyfire tools: {len(skyfire_tools)}")
    print(f"Available Dappier tools: {len(cached_tools['dappier'])}")
    
    return swarm
