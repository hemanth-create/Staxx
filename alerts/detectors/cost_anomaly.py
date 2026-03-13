"""Cost anomaly detector - detects cost spikes and volume changes."""

from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import statistics

from alerts.db.models import Alert, AlertThreshold
from alerts.db.queries import create_alert, get_or_create_threshold


async def detect_cost_spike(
    db: AsyncSession,
    org_id: UUID,
    task_type: Optional[str] = None,
) -> Optional[Alert]:
    """
    Detect abnormal cost spikes using statistical outlier detection.

    Compares today's cost to the rolling 30-day average ± std dev.
    Triggers alert if today > avg + (2 * std_dev).
    """
    threshold_config = await get_or_create_threshold(db, org_id)

    # Query cost data from the last 30 days
    from cost_engine.db.queries import get_daily_costs

    daily_costs = await get_daily_costs(db, org_id, days=30, task_type=task_type)

    if len(daily_costs) < 7:
        # Not enough history
        return None

    costs = [c["total_cost"] for c in daily_costs]
    today_cost = costs[-1]  # Most recent day
    historical_costs = costs[:-1]  # All previous days

    if not historical_costs:
        return None

    mean = statistics.mean(historical_costs)
    stdev = statistics.stdev(historical_costs) if len(historical_costs) > 1 else 0

    threshold = mean + (threshold_config.cost_spike_std_devs * stdev)

    if today_cost > threshold:
        spike_pct = ((today_cost - mean) / mean * 100) if mean > 0 else 0
        alert = await create_alert(
            db,
            org_id=org_id,
            alert_type="cost_spike",
            severity="warning" if spike_pct < 50 else "critical",
            title=f"Cost spike detected: {spike_pct:.0f}% increase",
            description=f"Today's cost: ${today_cost:.2f}. "
            f"30-day average: ${mean:.2f}. "
            f"Increase: {spike_pct:.1f}% ({threshold_config.cost_spike_std_devs} std devs). "
            f"Review for unexpected traffic or price changes.",
            task_type=task_type,
            metric_name="daily_cost",
            current_value=today_cost,
            threshold_value=threshold,
        )
        return alert

    return None


async def detect_volume_drift(
    db: AsyncSession,
    org_id: UUID,
    task_type: Optional[str] = None,
) -> Optional[Alert]:
    """
    Detect significant traffic volume changes.

    If volume changes by ±threshold, alert (affects absolute savings projections).
    """
    threshold_config = await get_or_create_threshold(db, org_id)

    from cost_engine.db.queries import get_daily_call_counts

    daily_counts = await get_daily_call_counts(db, org_id, days=30, task_type=task_type)

    if len(daily_counts) < 7:
        return None

    today_count = daily_counts[-1]
    avg_count = statistics.mean(daily_counts[:-1])

    if avg_count == 0:
        return None

    volume_change_pct = abs((today_count - avg_count) / avg_count)

    if volume_change_pct > threshold_config.volume_change_pct:
        direction = "increased" if today_count > avg_count else "decreased"
        alert = await create_alert(
            db,
            org_id=org_id,
            alert_type="cost_drift",
            severity="info",
            title=f"Volume {direction} {volume_change_pct:.0%}",
            description=f"Call volume {direction} from avg {avg_count:.0f} to {today_count:.0f}. "
            f"This affects your absolute savings projections. "
            f"Threshold: {threshold_config.volume_change_pct:.0%}",
            task_type=task_type,
            metric_name="daily_call_count",
            current_value=today_count,
            threshold_value=avg_count * (1 + threshold_config.volume_change_pct),
        )
        return alert

    return None
