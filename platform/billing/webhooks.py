"""
Stripe webhook handler.

Supported events:
  - customer.subscription.created
  - customer.subscription.updated
  - customer.subscription.deleted
  - invoice.payment_failed
  - invoice.payment_succeeded

The handler is mounted as a FastAPI route in platform/api/router.py.
It validates the Stripe-Signature header before processing any event.
"""

import logging
from typing import Any

import stripe
from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from platform.billing.stripe_client import PLAN_TO_PRICE_ID
from platform.config import settings
from platform.db.queries import get_org_by_stripe_customer, update_org_stripe

logger = logging.getLogger(__name__)


def _price_id_to_plan(price_id: str) -> str | None:
    """Reverse-map a Stripe price ID to an internal plan name."""
    for plan, pid in PLAN_TO_PRICE_ID.items():
        if pid and pid == price_id:
            return plan
    return None


async def handle_stripe_webhook(request: Request, db: AsyncSession) -> dict[str, str]:
    """
    Validate and dispatch a Stripe webhook event.

    Called from the POST /webhooks/stripe endpoint.
    Returns {"status": "ok"} on success.
    Raises HTTPException on invalid signature.
    """
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError as exc:
        logger.warning("Invalid Stripe webhook signature: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Stripe signature",
        ) from exc

    event_type: str = event["type"]
    event_data: dict[str, Any] = event["data"]["object"]

    logger.info("Received Stripe event: %s (id=%s)", event_type, event["id"])

    handlers = {
        "customer.subscription.created": _handle_subscription_created,
        "customer.subscription.updated": _handle_subscription_updated,
        "customer.subscription.deleted": _handle_subscription_deleted,
        "invoice.payment_failed": _handle_payment_failed,
        "invoice.payment_succeeded": _handle_payment_succeeded,
    }

    handler = handlers.get(event_type)
    if handler:
        await handler(event_data, db)
    else:
        logger.debug("Unhandled Stripe event type: %s", event_type)

    return {"status": "ok"}


async def _handle_subscription_created(data: dict, db: AsyncSession) -> None:
    customer_id: str = data["customer"]
    subscription_id: str = data["id"]
    price_id: str = data["items"]["data"][0]["price"]["id"]
    plan = _price_id_to_plan(price_id) or "starter"

    org = await get_org_by_stripe_customer(db, customer_id)
    if org is None:
        logger.error("subscription.created: no org for customer %s", customer_id)
        return

    # Find the metered usage item ID if present
    usage_item_id: str | None = None
    for item in data["items"]["data"]:
        if item.get("price", {}).get("recurring", {}).get("usage_type") == "metered":
            usage_item_id = item["id"]
            break

    await update_org_stripe(
        db,
        org.id,
        stripe_subscription_id=subscription_id,
        stripe_usage_item_id=usage_item_id,
        plan=plan,
    )
    logger.info("Org %s subscribed to plan '%s'", org.id, plan)


async def _handle_subscription_updated(data: dict, db: AsyncSession) -> None:
    customer_id: str = data["customer"]
    subscription_id: str = data["id"]
    status_str: str = data["status"]

    org = await get_org_by_stripe_customer(db, customer_id)
    if org is None:
        logger.error("subscription.updated: no org for customer %s", customer_id)
        return

    # Resolve plan from the first price item
    new_plan: str | None = None
    usage_item_id: str | None = None
    for item in data["items"]["data"]:
        price_id = item.get("price", {}).get("id", "")
        if new_plan is None:
            new_plan = _price_id_to_plan(price_id)
        if item.get("price", {}).get("recurring", {}).get("usage_type") == "metered":
            usage_item_id = item["id"]

    # If subscription is no longer active, downgrade to free
    if status_str in ("canceled", "unpaid", "past_due"):
        new_plan = "free"

    await update_org_stripe(
        db,
        org.id,
        stripe_subscription_id=subscription_id,
        stripe_usage_item_id=usage_item_id,
        plan=new_plan,
    )
    logger.info(
        "Org %s subscription updated: plan=%s status=%s", org.id, new_plan, status_str
    )


async def _handle_subscription_deleted(data: dict, db: AsyncSession) -> None:
    customer_id: str = data["customer"]

    org = await get_org_by_stripe_customer(db, customer_id)
    if org is None:
        logger.error("subscription.deleted: no org for customer %s", customer_id)
        return

    await update_org_stripe(
        db,
        org.id,
        stripe_subscription_id=None,
        stripe_usage_item_id=None,
        plan="free",
    )
    logger.info("Org %s subscription cancelled — downgraded to free", org.id)


async def _handle_payment_failed(data: dict, db: AsyncSession) -> None:
    customer_id: str = data["customer"]
    invoice_id: str = data["id"]
    logger.warning(
        "Payment failed for Stripe customer %s (invoice %s)", customer_id, invoice_id
    )
    # TODO: trigger alert email via notification service


async def _handle_payment_succeeded(data: dict, db: AsyncSession) -> None:
    customer_id: str = data["customer"]
    amount_paid: int = data.get("amount_paid", 0)
    logger.info(
        "Payment of %s cents succeeded for customer %s", amount_paid, customer_id
    )
