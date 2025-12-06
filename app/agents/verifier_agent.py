"""Verifier Agent - Audits the report for consistency and completeness."""

from agents import Agent

from app.agents.schemas import VerificationResult


def _load_prompt() -> str:
    with open("app/prompts/verifier.txt", "r") as f:
        return f.read()


verifier_agent = Agent(
    name="VerificationAgent",
    instructions=_load_prompt(),
    model="gpt-5-nano",
    output_type=VerificationResult,
)
