"""Savings Analyst Agent - Compares simulations and calculates interest savings."""

from agents import Agent

from app.agents.schemas import AnalysisSummary


def _load_prompt() -> str:
    with open("app/prompts/savings_analyst.txt", "r") as f:
        return f.read()


savings_analyst_agent = Agent(
    name="SavingsAnalystAgent",
    instructions=_load_prompt(),
    model="gpt-5-nano",
    output_type=AnalysisSummary,
)
