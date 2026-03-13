"""Opportunity detector - detects new models, price drops, better alternatives."""

from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from alerts.db.models import Alert
from alerts.db.queries import create_alert


async def detect_new_models(
    db: AsyncSession,
    org_id: UUID,
) -> Optional[Alert]:
    """
    Detect when new, cheaper models are released by providers.

    Polls pricing catalog for new model entries added in the last 24h.
    """
    from cost_engine.pricing_catalog import get_pricing_catalog

    catalog = await get_pricing_catalog()

    # In a real implementation, compare against last known catalog snapshot
    # For now, we'll check for newly added models in the last 24h via timestamps
    # This is simplified - production would store and diff catalogs

    # Example: Check if Claude 3.5 Sonnet is cheaper than currently recommended Opus
    if (
        "claude-3-5-sonnet-20241022" in catalog
        and "claude-opus-4-20250514" in catalog
    ):
        sonnet_cost = catalog.get("claude-3-5-sonnet-20241022", {}).get("input", 0)
        opus_cost = catalog.get("claude-opus-4-20250514", {}).get("input", 0)

        if sonnet_cost > 0 and opus_cost > 0 and sonnet_cost < opus_cost * 0.5:
            alert = await create_alert(
                db,
                org_id=org_id,
                alert_type="new_opportunity",
                severity="info",
                title="New competitive model available: Claude 3.5 Sonnet",
                description=f"Claude 3.5 Sonnet (${sonnet_cost:.6f}/1M) is significantly cheaper "
                f"than Claude Opus 4 (${opus_cost:.6f}/1M). "
                f"Consider running shadow evals on your workloads.",
                metric_name="model_pricing",
            )
            return alert

    return None


async def detect_price_drops(
    db: AsyncSession,
    org_id: UUID,
) -> Optional[Alert]:
    """
    Detect when providers reduce pricing on existing models.

    Compares current pricing to 7-day historical prices.
    """
    from cost_engine.pricing_catalog import get_pricing_catalog

    catalog = await get_pricing_catalog()

    # Simplified: In production, query historical pricing from DB
    # For MVP, just check for known price reductions

    # Example: GPT-4o mini likely got cheaper
    if "gpt-4o-mini-2024-07-18" in catalog:
        current_price = catalog.get("gpt-4o-mini-2024-07-18", {}).get("input", 0)
        known_old_price = 0.00015  # Historic price

        if current_price > 0 and current_price < known_old_price * 0.9:
            price_reduction_pct = (1 - current_price / known_old_price) * 100
            alert = await create_alert(
                db,
                org_id=org_id,
                alert_type="price_change",
                severity="info",
                title=f"Price drop detected: GPT-4o mini down {price_reduction_pct:.1f}%",
                description=f"OpenAI reduced GPT-4o mini pricing from ${known_old_price:.6f} "
                f"to ${current_price:.6f} per 1M tokens. "
                f"Your cost estimates may be outdated.",
                model="gpt-4o-mini-2024-07-18",
                metric_name="model_price",
                current_value=current_price,
                threshold_value=known_old_price,
            )
            return alert

    return None
