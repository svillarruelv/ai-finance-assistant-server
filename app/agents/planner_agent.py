"""Planner Agent - Analyzes customer and determines which simulations to run."""

from agents import Agent

from app.agents.schemas import SimulationPlan


def _load_prompt() -> str:
    with open("app/prompts/planner.txt", "r") as f:
        return f.read()


planner_agent = Agent(
    name="FinancialPlannerAgent",
    instructions=_load_prompt(),
    model="gpt-5-nano",
    output_type=SimulationPlan,
)
