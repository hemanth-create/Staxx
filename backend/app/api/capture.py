from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy import select, func

from app.core.db import AsyncSessionLocal
from app.models.model_version import ModelVersion
from app.models.production_call import ProductionCall
from app.workers.celery_app import celery_app

router = APIRouter()


@router.post("/capture")
async def capture_telemetry(payload: Dict[str, Any]):
    """
    Ingests telemetry from the SDK (latency, tokens, task tags)
    and pushes to a Celery background queue. Returns immediately.
    """
    # Fire and forget enqueue
    celery_app.send_task("app.workers.metrics_worker.process_call", args=[payload])
    return {"status": "accepted"}


@router.get("/costs/breakdown")
async def get_costs_breakdown() -> Dict[str, Any]:
    """
    Returns a high-level breakdown of costs grouped by task and model.
    MVP endpoint for the dashboard.
    """
    # Execute ad-hoc aggregate query.
    # In a full-scale TimescaleDB deployment this would hit continuous aggregates.
    
    stmt = (
        select(
            ModelVersion.provider_model_id,
            ProductionCall.task_type,
            func.sum(ProductionCall.cost_usd).label("total_cost"),
            func.count(ProductionCall.id).label("call_count")
        )
        .join(ProductionCall)
        .group_by(ModelVersion.provider_model_id, ProductionCall.task_type)
    )
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(stmt)
        rows = result.all()
        
    breakdown = []
    for row in rows:
        breakdown.append({
            "model": row.provider_model_id,
            "task_type": row.task_type,
            "total_cost_usd": row.total_cost,
            "call_count": row.call_count
        })

    return {"breakdown": breakdown}
