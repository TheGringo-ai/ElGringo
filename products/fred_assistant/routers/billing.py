"""Billing router — Stripe customer/subscription management."""

from fastapi import APIRouter, HTTPException, Request

from products.fred_assistant.models import AppCustomerCreate
from products.fred_assistant.services import billing_service

router = APIRouter(prefix="/billing", tags=["billing"])


@router.post("/customers")
def create_customer(data: AppCustomerCreate):
    result = billing_service.create_customer(data.model_dump())
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.get("/revenue")
def get_revenue():
    return billing_service.get_revenue_summary()


@router.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    result = billing_service.handle_webhook(payload, sig)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result
