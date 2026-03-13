"""Celery beat scheduler for alert detection tasks."""

import logging
from celery import shared_task
from celery.schedules import schedule
from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from alerts.detectors.quality_drift import detect_quality_drift
from alerts.detectors.cost_anomaly import detect_cost_spike, detect_volume_drift
from alerts.detectors.opportunity import detect_new_models, detect_price_drops
from alerts.notifiers.email import EmailNotifier
from alerts.notifiers.slack import SlackNotifier
from backend.app.workers.celery_app import celery_app
from backend.app.core.db import get_async_session

logger = logging.getLogger(__name__)


@shared_task(name="alerts.check_quality_drift")
async def check_quality_drift_task():
    """
    Check for quality drift on all active swaps (hourly).

    Monitors error rates, JSON validity, latency changes.
    """
    logger.info("Running quality drift detection")

    # Get all active recommendation swaps from DB
    # For each, call detect_quality_drift
    # Send notifications if alert created

    async with get_async_session() as db:
        from recommendations.db.queries import get_all_active_swaps

        swaps = await get_all_active_swaps(db)

        for swap in swaps:
            alert = await detect_quality_drift(
                db,
                swap.org_id,
                swap.task_type,
                swap.current_model,
                swap.recommended_model,
            )

            if alert:
                await db.commit()
                # Notify org
                await notify_org(db, swap.org_id, alert)


@shared_task(name="alerts.check_cost_spikes")
async def check_cost_spikes_task():
    """Check for cost spikes (every 5 minutes)."""
    logger.info("Running cost spike detection")

    async with get_async_session() as db:
        # Get all orgs
        from platform.db.queries import get_all_organizations

        orgs = await get_all_organizations(db)

        for org in orgs:
            alert = await detect_cost_spike(db, org.id)

            if alert:
                await db.commit()
                await notify_org(db, org.id, alert)


@shared_task(name="alerts.check_volume_drift")
async def check_volume_drift_task():
    """Check for volume changes (every 6 hours)."""
    logger.info("Running volume drift detection")

    async with get_async_session() as db:
        from platform.db.queries import get_all_organizations

        orgs = await get_all_organizations(db)

        for org in orgs:
            alert = await detect_volume_drift(db, org.id)

            if alert:
                await db.commit()
                await notify_org(db, org.id, alert)


@shared_task(name="alerts.check_opportunities")
async def check_opportunities_task():
    """Check for new models and price drops (daily)."""
    logger.info("Running opportunity detection")

    async with get_async_session() as db:
        from platform.db.queries import get_all_organizations

        orgs = await get_all_organizations(db)

        for org in orgs:
            # Check new models
            alert = await detect_new_models(db, org.id)

            if alert:
                await db.commit()
                await notify_org(db, org.id, alert)

            # Check price drops
            alert = await detect_price_drops(db, org.id)

            if alert:
                await db.commit()
                await notify_org(db, org.id, alert)


async def notify_org(db: AsyncSession, org_id: str, alert):
    """Send alert notifications to org (email, Slack, webhook)."""
    from platform.db.queries import get_organization_alert_settings

    settings = await get_organization_alert_settings(db, org_id)

    if not settings:
        return

    notifiers = []

    if settings.get("email_enabled"):
        notifiers.append(("email", settings.get("email"), EmailNotifier()))

    if settings.get("slack_enabled"):
        notifiers.append(("slack", settings.get("slack_webhook"), SlackNotifier()))

    if settings.get("webhook_enabled"):
        notifiers.append(
            ("webhook", settings.get("webhook_url"), WebhookNotifier())
        )

    for notifier_type, recipient, notifier in notifiers:
        if recipient:
            try:
                success = await notifier.send(alert, recipient)
                logger.info(
                    f"Alert {alert.id} sent via {notifier_type}: {success}"
                )
            except Exception as e:
                logger.error(f"Failed to notify via {notifier_type}: {e}")


# Celery Beat Schedule
def get_beat_schedule():
    """Return the Celery beat schedule for alerts."""
    return {
        "check-cost-spikes-5min": {
            "task": "alerts.check_cost_spikes",
            "schedule": timedelta(minutes=5),
        },
        "check-quality-drift-1h": {
            "task": "alerts.check_quality_drift",
            "schedule": timedelta(hours=1),
        },
        "check-volume-drift-6h": {
            "task": "alerts.check_volume_drift",
            "schedule": timedelta(hours=6),
        },
        "check-opportunities-24h": {
            "task": "alerts.check_opportunities",
            "schedule": timedelta(hours=24),
        },
    }
