"""
Financial Research Manager - Orchestrates the multi-agent pipeline.

Pipeline Flow:
1. Fetch customer data and debts
2. Plan simulations (Planner Agent)
3. Run simulations in parallel
4. Analyze results (Savings + Risk Analysts)
5. Write report (Writer Agent with analyst tools)
6. Verify report (Verifier Agent)
"""

from __future__ import annotations

import asyncio
from decimal import Decimal

from agents import Runner, RunResult, function_tool

from app.agents.planner_agent import planner_agent
from app.agents.savings_analyst import savings_analyst_agent
from app.agents.risk_analyst import risk_analyst_agent
from app.agents.writer_agent import writer_agent
from app.agents.verifier_agent import verifier_agent
from app.agents.schemas import (
    SimulationPlan,
    SimulationResults,
    SimulationResultItem,
    FinancialReportData,
    VerificationResult,
)
from app.agents.tools import (
    fetch_customer_profile,
    fetch_debts,
    run_minimum_payment_simulation,
    run_consolidation_simulation,
    run_payoff_strategies,
    run_hybrid_strategy,
)


async def _summary_extractor(run_result: RunResult) -> str:
    """Extract summary text from analyst agents for inline use by writer."""
    return str(run_result.final_output.summary)


class FinancialResearchManager:
    """Orchestrates the full financial report generation pipeline."""

    def __init__(self, customer_id: str):
        self.customer_id = customer_id
        self.customer_profile: dict | None = None
        self.debts: dict | None = None
        self.simulation_results: SimulationResults | None = None

    async def run(self) -> tuple[FinancialReportData, VerificationResult]:
        """Execute the full pipeline and return the report + verification."""
        # Step 1: Fetch customer data
        self.customer_profile = await fetch_customer_profile(self.customer_id)
        self.debts = await fetch_debts(self.customer_id)
        
        # Step 2: Plan simulations
        plan = await self._plan_simulations()
        
        # Step 3: Run simulations
        self.simulation_results = await self._run_simulations(plan)
        
        # Step 4: Write report (with analyst sub-agents as tools)
        report = await self._write_report()
        
        # Step 5: Verify report
        verification = await self._verify_report(report)
        
        # Step 6: If verification found issues, re-write the report with fixes
        if not verification.verified and verification.issues:
            report = await self._rewrite_report_with_fixes(report, verification)
            # Re-verify the fixed report
            verification = await self._verify_report(report)
        
        return report, verification

    async def _plan_simulations(self) -> SimulationPlan:
        """Use the planner agent to determine which simulations to run."""
        input_data = f"""
Customer Profile: {self.customer_profile}
Customer Debts: {self.debts}
"""
        result = await Runner.run(planner_agent, input_data)
        return result.final_output_as(SimulationPlan)

    async def _run_simulations(self, plan: SimulationPlan) -> SimulationResults:
        """Execute all planned simulations in parallel."""
        results: list[SimulationResultItem] = []
        
        # Always run these core simulations
        min_payment_task = asyncio.create_task(
            run_minimum_payment_simulation(self.customer_id)
        )
        strategies_task = asyncio.create_task(
            run_payoff_strategies(self.customer_id)
        )
        
        # Conditionally run consolidation
        consolidation_task = None
        for sim in plan.simulations:
            if sim.simulation_type == "consolidation":
                consolidation_task = asyncio.create_task(
                    run_consolidation_simulation(self.customer_id)
                )
                break
        
        # Always run hybrid strategies to compare
        hybrid_avalanche_task = asyncio.create_task(
            run_hybrid_strategy(self.customer_id, "avalanche")
        )
        hybrid_snowball_task = asyncio.create_task(
            run_hybrid_strategy(self.customer_id, "snowball")
        )
        
        # Await all
        min_result = await min_payment_task
        strategies_result = await strategies_task
        
        # Process minimum payment baseline
        baseline_interest = Decimal(min_result.get("total_interest_paid", "0"))
        baseline_months = min_result.get("max_months_to_debt_free", 0)
        
        results.append(SimulationResultItem(
            simulation_type="minimum_payment",
            total_interest_paid=str(baseline_interest),
            total_months=baseline_months,
            monthly_payment="Varies (minimums)",
            details={"products": min_result.get("products", [])}
        ))
        
        # Process strategy results
        for strategy in strategies_result:
            results.append(SimulationResultItem(
                simulation_type=f"strategy_{strategy.get('strategy_name', 'unknown').lower()}",
                total_interest_paid=str(strategy.get("total_interest_paid", "0")),
                total_months=strategy.get("total_months", 0),
                monthly_payment=str(strategy.get("monthly_payment", "0")),
                details=strategy
            ))
        
        # Process consolidation if applicable
        if consolidation_task:
            consolidation_result = await consolidation_task
            if consolidation_result.get("simulations"):
                for sim in consolidation_result["simulations"]:
                    results.append(SimulationResultItem(
                        simulation_type="consolidation",
                        total_interest_paid=str(sim.get("total_interest_paid", "0")),
                        total_months=sim.get("total_months", 0),
                        monthly_payment=str(sim.get("payment_used", "0")),
                        details=sim
                    ))
        
        # Process hybrid strategies
        hybrid_avalanche = await hybrid_avalanche_task
        if hybrid_avalanche.get("available", True) and "error" not in hybrid_avalanche:
            results.append(SimulationResultItem(
                simulation_type="hybrid_consolidate_then_avalanche",
                total_interest_paid=str(hybrid_avalanche.get("total_interest_paid", "0")),
                total_months=hybrid_avalanche.get("total_months", 0),
                monthly_payment=str(hybrid_avalanche.get("monthly_payment", "0")),
                details=hybrid_avalanche
            ))
        
        hybrid_snowball = await hybrid_snowball_task
        if hybrid_snowball.get("available", True) and "error" not in hybrid_snowball:
            results.append(SimulationResultItem(
                simulation_type="hybrid_consolidate_then_snowball",
                total_interest_paid=str(hybrid_snowball.get("total_interest_paid", "0")),
                total_months=hybrid_snowball.get("total_months", 0),
                monthly_payment=str(hybrid_snowball.get("monthly_payment", "0")),
                details=hybrid_snowball
            ))
        
        return SimulationResults(
            customer_id=self.customer_id,
            baseline_interest=str(baseline_interest),
            baseline_months=baseline_months,
            results=results
        )

    async def _write_report(self) -> FinancialReportData:
        """Use the writer agent with analyst sub-agents as tools."""
        # Expose analysts as tools for the writer to call
        savings_tool = savings_analyst_agent.as_tool(
            tool_name="savings_analysis",
            tool_description="Get a detailed analysis of interest savings between strategies",
            custom_output_extractor=_summary_extractor,
        )
        risk_tool = risk_analyst_agent.as_tool(
            tool_name="risk_analysis",
            tool_description="Get a risk assessment of the customer's financial situation",
            custom_output_extractor=_summary_extractor,
        )
        
        # Clone writer with tools
        writer_with_tools = writer_agent.clone(tools=[savings_tool, risk_tool])
        
        input_data = f"""
Customer Profile: {self.customer_profile}
Customer Debts: {self.debts}
Simulation Results: {self.simulation_results.model_dump_json() if self.simulation_results else 'None'}
"""
        result = await Runner.run(writer_with_tools, input_data)
        return result.final_output_as(FinancialReportData)

    async def _rewrite_report_with_fixes(
        self, 
        original_report: FinancialReportData, 
        verification: VerificationResult
    ) -> FinancialReportData:
        """Re-write the report incorporating the verifier's feedback."""
        # Build a prompt that includes the original report and issues to fix
        fix_prompt = f"""
You previously wrote a financial report but the auditor found issues.

ORIGINAL REPORT:
{original_report.markdown_report}

ISSUES FOUND:
{verification.issues}

SUGGESTIONS:
{', '.join(verification.suggestions) if verification.suggestions else 'None'}

SIMULATION DATA (for reference):
{self.simulation_results.model_dump_json() if self.simulation_results else 'None'}

Please REWRITE the report fixing ALL the issues mentioned above.
Keep the same structure and format, but correct the problems identified.
Make sure to output in SPANISH with S/. currency.
"""
        result = await Runner.run(writer_agent, fix_prompt)
        return result.final_output_as(FinancialReportData)

    async def _verify_report(self, report: FinancialReportData) -> VerificationResult:
        """Use the verifier agent to audit the report."""
        result = await Runner.run(verifier_agent, report.markdown_report)
        return result.final_output_as(VerificationResult)


async def generate_financial_report(customer_id: str) -> tuple[FinancialReportData, VerificationResult]:
    """Main entry point for generating a financial report."""
    manager = FinancialResearchManager(customer_id)
    return await manager.run()
