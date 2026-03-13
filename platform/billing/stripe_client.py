"""
Stripe SDK wrapper for Staxx platform billing.

Handles:
  - Customer creation / retrieval
  - Subscription creation and management
  - Metered usage reporting
  - Plan → price ID mapping
"""

import logging
from typing import Optional
from uuid import UUID

import stripe

from platform.config import settings

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY

# ---------------------------------------------------------------------------
# Plan metadata
# ---------------------------------------------------------------------------

PLAN_LIMITS: dict[str, int] = {
    "free": 10_000,
    "starter": 100_000,
    "growth": 1_000_000,
    "enterprise": -1,  # unlimited / custom
}

PLAN_TO_PRICE_ID: dict[str, str] = {
    "starter": settings.STRIPE_PRICE_STARTER,
    "growth": settings.STRIPE_PRICE_GROWTH,
    "enterprise": settings.STRIPE_PRICE_ENTERPRISE,
}


# ---------------------------------------------------------------------------
# Customer management
# ---------------------------------------------------------------------------


async def create_stripe_customer(org_id: UUID, org_name: str, email: str) -> str:
    """
    Create a Stripe Customer for a new org and return the customer ID.
    Attaches org metadata so we can look the org up from webhook events.
    """
    customer = stripe.Customer.create(
        name=org_name,
        email=email,
        metadata={"org_id": str(org_id)},
    )
    logger.info("Created Stripe customer %s for org %s", customer.id, org_id)
    return customer.id


async def get_stripe_customer(customer_id: str) -> stripe.Customer:
    """Retrieve a Stripe Customer object."""
    return stripe.Customer.retrieve(customer_id)


# ---------------------------------------------------------------------------
# Subscription management
# ---------------------------------------------------------------------------


async def create_subscription(
    customer_id: str,
    plan: str,
) -> tuple[str, Optional[str]]:
    """
    Create a Stripe subscription for the given plan.

    Returns:
        (subscription_id, usage_item_id)
        usage_item_id is the subscription item ID for metered billing reporting.
        It is None for plans that use flat-rate pricing (no metered component).
    """
    price_id = PLAN_TO_PRICE_ID.get(plan)
    if not price_id:
        raise ValueError(f"No Stripe price configured for plan '{plan}'")

    subscription = stripe.Subscription.create(
        customer=customer_id,
        items=[{"price": price_id}],
        expand=["items.data"],
    )
    subscription_id = subscription.id

    # For metered prices the subscription item ID is used when reporting usage
    usage_item_id: Optional[str] = None
    for item in subscription["items"]["data"]:
        price = item.get("price", {})
        if price.get("recurring", {}).get("usage_type") == "metered":
            usage_item_id = item["id"]
            break

    logger.info(
        "Created subscription %s (usage_item=%s) for customer %s",
        subscription_id,
        usage_item_id,
        customer_id,
    )
    return subscription_id, usage_item_id


async def cancel_subscription(subscription_id: str) -> None:
    """Cancel a Stripe subscription immediately."""
    stripe.Subscription.cancel(subscription_id)
    logger.info("Cancelled subscription %s", subscription_id)


async def update_subscription_plan(
    subscription_id: str,
    new_plan: str,
) -> tuple[str, Optional[str]]:
    """
    Change the plan on an existing subscription.

    Returns the same (subscription_id, usage_item_id) tuple after updating.
    """
    price_id = PLAN_TO_PRICE_ID.get(new_plan)
    if not price_id:
        raise ValueError(f"No Stripe price configured for plan '{new_plan}'")

    subscription = stripe.Subscription.retrieve(subscription_id, expand=["items.data"])
    existing_item_id = subscription["items"]["data"][0]["id"]

    updated = stripe.Subscription.modify(
        subscription_id,
        items=[{"id": existing_item_id, "price": price_id}],
        proration_behavior="always_invoice",
        expand=["items.data"],
    )

    usage_item_id: Optional[str] = None
    for item in updated["items"]["data"]:
        if item.get("price", {}).get("recurring", {}).get("usage_type") == "metered":
            usage_item_id = item["id"]
            break

    return updated.id, usage_item_id


# ---------------------------------------------------------------------------
# Metered usage reporting
# ---------------------------------------------------------------------------


async def report_usage(
    usage_item_id: str,
    quantity: int,
    idempotency_key: Optional[str] = None,
) -> None:
    """
    Report metered usage to Stripe for a subscription item.

    quantity: number of API requests to report
    idempotency_key: use a stable key (e.g., org_id + billing period) to
                     prevent double-reporting on retries.
    """
    kwargs: dict = {
        "subscription_item": usage_item_id,
        "quantity": quantity,
        "action": "increment",
    }
    if idempotency_key:
        kwargs["idempotency_key"] = idempotency_key

    stripe.SubscriptionItem.create_usage_record(**kwargs)
    logger.info("Reported %d usage units to Stripe item %s", quantity, usage_item_id)


# ---------------------------------------------------------------------------
# Billing portal
# ---------------------------------------------------------------------------


async def create_billing_portal_session(customer_id: str, return_url: str) -> str:
    """
    Create a Stripe Customer Portal session so customers can manage their plan/payment.
    Returns the portal URL.
    """
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
    )
    return session.url
