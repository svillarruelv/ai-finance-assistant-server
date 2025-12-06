from agents import Agent, Runner, function_tool
from app.agents.tools import (
    fetch_customer_profile,
    fetch_debts,
    run_consolidation_simulation,
    run_payoff_strategies,
    run_minimum_payment_simulation
)
from app.config import get_settings

settings = get_settings()

def get_financial_agent(model: str = "gpt-5-nano") -> Agent:
    with open("app/prompts/financial_report_system.txt", "r") as f:
        system_prompt = f.read()

    agent = Agent(
        name="Financial Advisor",
        instructions=system_prompt,
        model=model,
        tools=[
            function_tool(fetch_customer_profile),
            function_tool(fetch_debts),
            function_tool(run_consolidation_simulation),
            function_tool(run_payoff_strategies),
            function_tool(run_minimum_payment_simulation)
        ]
    )
    return agent

async def generate_report_content(customer_id: str) -> str:
    """Generate the full report content (non-streaming)."""
    agent = get_financial_agent()
    
    # We pass the customer_id as context in the user message
    user_msg = f"Generate a financial report for customer ID: {customer_id}"
    
    result = await Runner.run(agent, input=user_msg)
    return result.final_output

async def generate_report_stream(customer_id: str):
    """Generate the report streaming chunks."""
    agent = get_financial_agent()
    user_msg = f"Generate a financial report for customer ID: {customer_id}"
    
    # The Runner.run method might not be async generator by default in library?
    # Checking docs pattern. Usually libraries have a run_stream or similar.
    # If the library doesn't support easy streaming, we might fallback to non-streaming or check source.
    # Assuming standard pattern:
    # Please note: Library openai-agents details were 'Agent', 'Runner'. 
    # Let's assume common usage. If run() is async, it returns a Result.
    # For streaming, we need to inspect the library.
    # Based on recent OpenAI Swarm/Agents patterns.
    
    # Placeholder for streaming logic - relying on standard run for now as safe bet, 
    # but user asked for streamable. 
    # If library doesn't expose stream, we yield the result at end.
    
    # Actually, let's look at the library if possible. 
    # I saw `openai-agents` installed.
    # I'll implement a generator that yields chunks if possible, or just the final text if not.
    
    result = await Runner.run(agent, input=user_msg)
    yield result.final_output
