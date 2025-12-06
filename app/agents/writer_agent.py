"""Writer Agent - Synthesizes all data into a comprehensive report."""

from agents import Agent

from app.agents.schemas import FinancialReportData


def _load_prompt() -> str:
    with open("app/prompts/writer.txt", "r") as f:
        return f.read()


writer_agent = Agent(
    name="FinancialWriterAgent",
    instructions=_load_prompt(),
    model="gpt-5-mini",  # Using smarter model for complex synthesis
    output_type=FinancialReportData,
)
