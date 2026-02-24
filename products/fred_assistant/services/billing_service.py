"""
Billing Service — Stripe integration for App Factory monetization.

Plans: Free ($0), Starter ($29/mo), Pro ($99/mo).
Handles customer creation, subscriptions, webhooks, and revenue reporting.
"""

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Optional

from products.fred_assistant.database import get_conn, log_activity

logger = logging.getLogger(__name__)

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

PLANS = {
    "free": {"name": "Free", "price": 0, "stripe_price_id": ""},
    "starter": {"name": "Starter", "price": 29, "stripe_price_id": os.getenv("STRIPE_STARTER_PRICE_ID", "")},
    "pro": {"name": "Pro", "price": 99, "stripe_price_id": os.getenv("STRIPE_PRO_PRICE_ID", "")},
}


def _now():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def _get_stripe():
    """Lazy-import stripe to avoid hard dependency."""
    try:
        import stripe
        stripe.api_key = STRIPE_SECRET_KEY
        return stripe
    except ImportError:
        logger.warning("stripe package not installed — billing in local-only mode")
        return None


# ── Customer Management ──────────────────────────────────────────────


def create_customer(data: dict) -> dict:
    """Create a customer record, optionally in Stripe."""
    cust_id = str(uuid.uuid4())[:12]
    app_id = data["app_id"]
    name = data["name"]
    email = data.get("email", "")
    plan = data.get("plan", "free")
    mrr = PLANS.get(plan, {}).get("price", 0)

    stripe_customer_id = ""
    stripe = _get_stripe()
    if stripe and STRIPE_SECRET_KEY and email:
        try:
            sc = stripe.Customer.create(name=name, email=email, metadata={"app_id": app_id})
            stripe_customer_id = sc.id
        except Exception as e:
            logger.warning("Stripe customer creation failed: %s", e)

    with get_conn() as conn:
        conn.execute(
            """INSERT INTO app_customers
               (id, app_id, name, email, plan, stripe_customer_id, mrr, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)""",
            (cust_id, app_id, name, email, plan, stripe_customer_id, mrr, _now(), _now()),
        )

    log_activity("billing:create_customer", "app_customer", cust_id, {"app_id": app_id, "plan": plan})

    with get_conn() as conn:
        row = conn.execute("SELECT * FROM app_customers WHERE id = ?", (cust_id,)).fetchone()
    return dict(row) if row else {}


def create_subscription(customer_id: str, plan: str) -> dict:
    """Create or update a subscription for a customer."""
    plan_info = PLANS.get(plan)
    if not plan_info:
        return {"error": f"Unknown plan: {plan}"}

    with get_conn() as conn:
        row = conn.execute("SELECT * FROM app_customers WHERE id = ?", (customer_id,)).fetchone()
        if not row:
            return {"error": "Customer not found"}
        customer = dict(row)

    stripe_sub_id = ""
    stripe = _get_stripe()
    if stripe and STRIPE_SECRET_KEY and customer.get("stripe_customer_id") and plan_info["stripe_price_id"]:
        try:
            sub = stripe.Subscription.create(
                customer=customer["stripe_customer_id"],
                items=[{"price": plan_info["stripe_price_id"]}],
            )
            stripe_sub_id = sub.id
        except Exception as e:
            logger.warning("Stripe subscription creation failed: %s", e)

    mrr = plan_info["price"]
    with get_conn() as conn:
        conn.execute(
            """UPDATE app_customers SET plan = ?, mrr = ?, stripe_subscription_id = ?,
               status = 'active', updated_at = ? WHERE id = ?""",
            (plan, mrr, stripe_sub_id, _now(), customer_id),
        )

    log_activity("billing:create_subscription", "app_customer", customer_id, {"plan": plan})
    return {"status": "ok", "plan": plan, "mrr": mrr}


def cancel_subscription(subscription_id: str) -> dict:
    """Cancel a subscription."""
    stripe = _get_stripe()
    if stripe and STRIPE_SECRET_KEY and subscription_id:
        try:
            stripe.Subscription.cancel(subscription_id)
        except Exception as e:
            logger.warning("Stripe cancel failed: %s", e)

    with get_conn() as conn:
        conn.execute(
            """UPDATE app_customers SET status = 'churned', mrr = 0, updated_at = ?
               WHERE stripe_subscription_id = ?""",
            (_now(), subscription_id),
        )

    log_activity("billing:cancel_subscription", "subscription", subscription_id)
    return {"status": "cancelled"}


# ── Webhook ──────────────────────────────────────────────────────────


def handle_webhook(payload: bytes, sig_header: str) -> dict:
    """Process Stripe webhook events."""
    stripe = _get_stripe()
    if not stripe or not STRIPE_WEBHOOK_SECRET:
        return {"status": "skipped", "reason": "Stripe not configured"}

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        return {"error": f"Webhook verification failed: {e}"}

    event_type = event.get("type", "")

    if event_type == "invoice.paid":
        invoice = event["data"]["object"]
        customer_id = invoice.get("customer", "")
        with get_conn() as conn:
            conn.execute(
                "UPDATE app_customers SET status = 'active', updated_at = ? WHERE stripe_customer_id = ?",
                (_now(), customer_id),
            )
        log_activity("billing:invoice_paid", "webhook", event.get("id", ""))

    elif event_type == "customer.subscription.deleted":
        sub = event["data"]["object"]
        sub_id = sub.get("id", "")
        with get_conn() as conn:
            conn.execute(
                "UPDATE app_customers SET status = 'churned', mrr = 0, updated_at = ? WHERE stripe_subscription_id = ?",
                (_now(), sub_id),
            )
        log_activity("billing:subscription_deleted", "webhook", event.get("id", ""))

    return {"status": "processed", "type": event_type}


# ── Revenue Reporting ────────────────────────────────────────────────


def get_revenue_summary() -> dict:
    """Total MRR, customer count, breakdown by app and plan."""
    with get_conn() as conn:
        # Overall
        overall = conn.execute(
            """SELECT COUNT(*) as total_customers, COALESCE(SUM(mrr), 0) as total_mrr
               FROM app_customers WHERE status != 'churned'"""
        ).fetchone()

        # By app
        by_app = conn.execute(
            """SELECT a.name, a.display_name, COUNT(c.id) as customers, COALESCE(SUM(c.mrr), 0) as mrr
               FROM apps a LEFT JOIN app_customers c ON a.id = c.app_id AND c.status != 'churned'
               GROUP BY a.id ORDER BY mrr DESC"""
        ).fetchall()

        # By plan
        by_plan = conn.execute(
            """SELECT plan, COUNT(*) as customers, COALESCE(SUM(mrr), 0) as mrr
               FROM app_customers WHERE status != 'churned'
               GROUP BY plan ORDER BY mrr DESC"""
        ).fetchall()

    return {
        "total_customers": overall["total_customers"] if overall else 0,
        "total_mrr": overall["total_mrr"] if overall else 0,
        "by_app": [dict(r) for r in by_app],
        "by_plan": [dict(r) for r in by_plan],
        "plans": {k: {"name": v["name"], "price": v["price"]} for k, v in PLANS.items()},
    }
