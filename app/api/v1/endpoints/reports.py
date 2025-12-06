from typing import AsyncGenerator
import json

from fastapi import APIRouter, Depends, BackgroundTasks, Query
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db, SessionLocal
from app.models.report import FinancialReport
from app.models.customer import Customer
from app.agents.manager import generate_financial_report as run_pipeline

router = APIRouter()


async def get_existing_report(db: AsyncSession, customer_id: str) -> FinancialReport | None:
    """Check if customer already has a report in the database."""
    # First get customer UUID
    stmt = select(Customer.id).where(Customer.external_id == customer_id)
    cust_uuid = (await db.execute(stmt)).scalar_one_or_none()
    
    if not cust_uuid:
        return None
    
    # Get the most recent report for this customer
    stmt = (
        select(FinancialReport)
        .where(FinancialReport.customer_id == cust_uuid)
        .order_by(desc(FinancialReport.created_at))
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def save_report_to_db(customer_id: str, content: str, metadata: dict | None = None):
    """Background task to save the generated report."""
    async with SessionLocal() as db:
        stmt = select(Customer.id).where(Customer.external_id == customer_id)
        cust_uuid = (await db.execute(stmt)).scalar_one_or_none()
        
        if cust_uuid:
            report = FinancialReport(
                customer_id=cust_uuid,
                content=content,
                metadata_info=metadata
            )
            db.add(report)
            await db.commit()


@router.post("/generate/{customer_id}")
async def generate_financial_report(
    customer_id: str,
    background_tasks: BackgroundTasks,
    reprocess: bool = Query(False, description="Force regeneration of the report, ignoring cached version"),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a comprehensive financial report using the multi-agent pipeline.
    
    **Caching**: If a report already exists for this customer, it will be returned
    from the database to save costs. Use `reprocess=true` to force regeneration.
    
    Pipeline stages:
    1. **Planner**: Analyzes customer and plans simulations
    2. **Simulations**: Runs minimum payment, strategies, and consolidation
    3. **Analysts**: Savings and Risk analysis
    4. **Writer**: Synthesizes into comprehensive report (in Spanish)
    5. **Verifier**: Audits for consistency
    
    Returns the full report with verification status.
    """
    # Check for existing report if not forcing reprocess
    if not reprocess:
        existing_report = await get_existing_report(db, customer_id)
        if existing_report:
            # Return cached report
            metadata = existing_report.metadata_info or {}
            return JSONResponse(content={
                "customer_id": customer_id,
                "cached": True,
                "created_at": existing_report.created_at.isoformat() if existing_report.created_at else None,
                "executive_summary": metadata.get("recommended_strategy", "Ver reporte completo"),
                "recommended_strategy": metadata.get("recommended_strategy", ""),
                "total_savings": metadata.get("total_savings", ""),
                "time_saved_months": metadata.get("time_saved_months", 0),
                "full_report": existing_report.content,
                "verification": {
                    "verified": metadata.get("verified", True),
                    "issues": "",
                    "suggestions": []
                }
            })
    
    # Run the multi-agent pipeline
    report, verification = await run_pipeline(customer_id)
    
    # Schedule DB save
    background_tasks.add_task(
        save_report_to_db, 
        customer_id, 
        report.markdown_report,
        {
            "verified": verification.verified,
            "recommended_strategy": report.recommended_strategy,
            "total_savings": report.total_savings,
            "time_saved_months": report.time_saved_months
        }
    )
    
    # Return structured response
    return JSONResponse(content={
        "customer_id": customer_id,
        "cached": False,
        "executive_summary": report.short_summary,
        "recommended_strategy": report.recommended_strategy,
        "total_savings": report.total_savings,
        "time_saved_months": report.time_saved_months,
        "action_plan": [
            {"step": s.step_number, "action": s.action, "rationale": s.rationale}
            for s in report.action_plan
        ],
        "full_report": report.markdown_report,
        "follow_up_questions": report.follow_up_questions,
        "verification": {
            "verified": verification.verified,
            "issues": verification.issues,
            "suggestions": verification.suggestions
        }
    })



@router.get("/{customer_id}")
async def get_customer_report(
    customer_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get the most recent report for a customer (if exists).
    Returns 404 if no report found.
    """
    existing_report = await get_existing_report(db, customer_id)
    
    if not existing_report:
        return JSONResponse(
            status_code=404,
            content={"error": "No report found for this customer", "customer_id": customer_id}
        )
    
    metadata = existing_report.metadata_info or {}
    return JSONResponse(content={
        "customer_id": customer_id,
        "created_at": existing_report.created_at.isoformat() if existing_report.created_at else None,
        "recommended_strategy": metadata.get("recommended_strategy", ""),
        "total_savings": metadata.get("total_savings", ""),
        "time_saved_months": metadata.get("time_saved_months", 0),
        "verified": metadata.get("verified", True),
        "full_report": existing_report.content
    })
