"""Pydantic schemas for the multi-agent financial report pipeline."""

from pydantic import BaseModel


class SimulationItem(BaseModel):
    """A single simulation to run."""
    simulation_type: str
    """Type: 'minimum_payment', 'strategy_avalanche', 'strategy_snowball', 'consolidation'"""
    
    reason: str
    """Why this simulation is relevant for the customer."""


class SimulationPlan(BaseModel):
    """Output of the Planner Agent - what simulations to run."""
    customer_summary: str
    """Brief summary of the customer's financial situation."""
    
    simulations: list[SimulationItem]
    """List of simulations to execute."""


class SimulationResultItem(BaseModel):
    """Result from a single simulation."""
    simulation_type: str
    total_interest_paid: str
    total_months: int
    monthly_payment: str
    details: dict | None = None


class SimulationResults(BaseModel):
    """Aggregated results from all simulations."""
    customer_id: str
    baseline_interest: str
    baseline_months: int
    results: list[SimulationResultItem]


class AnalysisSummary(BaseModel):
    """Output of sub-analyst agents."""
    summary: str
    """Short text summary for this aspect of the analysis."""
    
    key_findings: list[str]
    """Bullet points of key findings."""


class ActionStep(BaseModel):
    """A single step in the action plan."""
    step_number: int
    action: str
    rationale: str


class FinancialReportData(BaseModel):
    """Final report structure from the Writer Agent."""
    short_summary: str
    """A short 2-3 sentence executive summary."""
    
    recommended_strategy: str
    """The best strategy for this customer."""
    
    total_savings: str
    """Total interest savings compared to minimum payments."""
    
    time_saved_months: int
    """Months saved compared to minimum payments."""
    
    markdown_report: str
    """The full markdown report."""
    
    action_plan: list[ActionStep]
    """Step-by-step action plan for the customer."""
    
    follow_up_questions: list[str]
    """Suggested follow-up questions for further research."""


class VerificationResult(BaseModel):
    """Output of the Verifier Agent."""
    verified: bool
    """Whether the report seems coherent and plausible."""
    
    issues: str
    """If not verified, describe the main issues or concerns."""
    
    suggestions: list[str]
    """Suggestions for improving the report."""
