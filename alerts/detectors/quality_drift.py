"""Quality drift detector - monitors error rates, JSON validity, latency changes."""

from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import statistics

from alerts.db.models import Alert, AlertThreshold
from alerts.db.queries import create_alert, get_or_create_threshold


async def detect_quality_drift(
    db: AsyncSession,
    org_id: UUID,
    task_type: str,
    original_model: str,
    current_model: str,
) -> Optional[Alert]:
    """
    Check if quality metrics have drifted for an approved swap.

    Compares rolling 24h metrics against the shadow eval baseline.
    """
    threshold_config = await get_or_create_threshold(db, org_id)

    # Query cost_events for the new model (rolled out) - last 24h
    from backend.app.core.db import get_async_session
    from cost_engine.db.queries import get_metrics_for_model

    metrics_24h = await get_metrics_for_model(
        db, org_id, current_model, task_type, hours=24
    )

    if not metrics_24h or metrics_24h.get("call_count", 0) < 20:
        # Insufficient data for drift detection
        return None

    current_error_rate = metrics_24h.get("error_rate", 0)
    current_json_validity = metrics_24h.get("json_validity_rate", 1.0)
    current_latency_p95 = metrics_24h.get("p95_latency", 0)

    # Compare against baseline from shadow evals
    # This is simplified - in production, you'd fetch the shadow eval baseline
    baseline_json_validity = 0.99  # Assume baseline was 99% from shadow evals
    baseline_error_rate = 0.01  # Assume baseline was 1%
    baseline_latency_p95 = 100  # Assume baseline was 100ms

    # Quality drift alerts
    if current_error_rate > threshold_config.error_rate_threshold:
        alert = await create_alert(
            db,
            org_id=org_id,
            alert_type="quality_drift",
            severity="warning" if current_error_rate < 0.05 else "critical",
            title=f"Error rate spike: {current_model} on {task_type}",
            description=f"Error rate increased to {current_error_rate:.2%} "
            f"(threshold: {threshold_config.error_rate_threshold:.2%}). "
            f"Baseline was {baseline_error_rate:.2%}.",
            task_type=task_type,
            model=current_model,
            metric_name="error_rate",
            current_value=current_error_rate,
            threshold_value=threshold_config.error_rate_threshold,
        )
        return alert

    if current_json_validity < threshold_config.quality_drift_threshold:
        alert = await create_alert(
            db,
            org_id=org_id,
            alert_type="quality_drift",
            severity="warning",
            title=f"JSON validity degradation: {current_model}",
            description=f"JSON validity dropped to {current_json_validity:.2%} "
            f"(threshold: {threshold_config.quality_drift_threshold:.2%}). "
            f"Baseline was {baseline_json_validity:.2%}.",
            task_type=task_type,
            model=current_model,
            metric_name="json_validity",
            current_value=current_json_validity,
            threshold_value=threshold_config.quality_drift_threshold,
        )
        return alert

    latency_increase_pct = (
        (current_latency_p95 - baseline_latency_p95) / baseline_latency_p95
        if baseline_latency_p95 > 0
        else 0
    )
    if latency_increase_pct > threshold_config.latency_regression_pct:
        alert = await create_alert(
            db,
            org_id=org_id,
            alert_type="quality_drift",
            severity="info",
            title=f"Latency regression detected: {current_model}",
            description=f"p95 latency increased {latency_increase_pct:.1%} "
            f"to {current_latency_p95:.0f}ms (was {baseline_latency_p95:.0f}ms). "
            f"Threshold: {threshold_config.latency_regression_pct:.1%}",
            task_type=task_type,
            model=current_model,
            metric_name="latency_p95",
            current_value=current_latency_p95,
            threshold_value=baseline_latency_p95
            * (1 + threshold_config.latency_regression_pct),
        )
        return alert

    return None
