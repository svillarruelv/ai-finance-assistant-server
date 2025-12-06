"""Risk Analyst Agent - Identifies financial risks and red flags."""

from agents import Agent

from app.agents.schemas import AnalysisSummary


def _load_prompt() -> str:
    with open("app/prompts/risk_analyst.txt", "r") as f:
        return f.read()


risk_analyst_agent = Agent(
    name="RiskAnalystAgent",
    instructions=_load_prompt(),
    model="gpt-5-nano",
    output_type=AnalysisSummary,
)
