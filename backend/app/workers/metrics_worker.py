import asyncio
import logging
from typing import Dict, Any

from sqlalchemy import select

from app.workers.celery_app import celery_app
from app.core.db import AsyncSessionLocal
from app.models.model_version import ModelVersion
from app.models.production_call import ProductionCall
from app.services.classifier import TaskClassifier
from app.services.cost_calculator import CostCalculator

logger = logging.getLogger(__name__)


async def _process_call_async(payload: Dict[str, Any]):
    """
    Async implementation of the worker task.
    Requires an explicit event loop since Celery is sync.
    """
    model_name = payload.get("model", "unknown")
    input_tokens = payload.get("input_tokens", 0)
    output_tokens = payload.get("output_tokens", 0)
    latency_ms = payload.get("latency_ms", 0.0)
    raw_task_type = payload.get("task_type", "unclassified")
    # For future: prompt content is usually sent here for hashing
    prompt_content = payload.get("prompt", "")

    # 1. Classification
    task_type = TaskClassifier.classify(prompt_content, provided_tag=raw_task_type)

    # 2. Cost Calculation
    cost = CostCalculator.calculate(model_name, input_tokens, output_tokens)

    async with AsyncSessionLocal() as session:
        # 3. Model Version Lookup / Creation (upsert logic stub)
        # In a strict production system, models should be pre-registered. 
        # Here we 'upsert' or fallback for unknown telemetry.
        stmt = select(ModelVersion).where(ModelVersion.provider_model_id == model_name)
        result = await session.execute(stmt)
        model_version = result.scalar_one_or_none()

        if not model_version:
            logger.info("Encountered new model variant %s, auto-registering.", model_name)
            model_version = ModelVersion(provider_model_id=model_name)
            session.add(model_version)
            await session.commit()
            await session.refresh(model_version)

        # 4. Ingest Production Call
        call_record = ProductionCall(
            model_version_id=model_version.id,
            task_type=task_type,
            cost_usd=cost,
            latency_ms=latency_ms
        )
        session.add(call_record)
        await session.commit()
        
        logger.info("Ingested production call: %s | Cost: $%f", model_name, cost)


@celery_app.task(name="app.workers.metrics_worker.process_call")
def process_call(payload: Dict[str, Any]):
    """
    Celery task entrypoint for processing incoming SDK telemetry.
    """
    asyncio.run(_process_call_async(payload))
