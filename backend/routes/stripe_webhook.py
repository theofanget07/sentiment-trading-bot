#!/usr/bin/env python3
"""
FastAPI Webhook Endpoint for Stripe Events.

Handles incoming Stripe webhooks:
- checkout.session.completed
- customer.subscription.created/updated/deleted
- invoice.payment_succeeded/failed

Author: Theo Fanget
Date: 06 February 2026
"""
from fastapi import APIRouter, Request, HTTPException, Header
from typing import Optional
import logging

# Import Stripe service
try:
    from backend.stripe_service import process_webhook
    STRIPE_SERVICE_AVAILABLE = True
except ImportError:
    logging.error("Could not import stripe_service")
    STRIPE_SERVICE_AVAILABLE = False

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/webhook",
    tags=["webhooks"]
)


@router.post("/stripe")
async def stripe_webhook_handler(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="Stripe-Signature")
):
    """
    Stripe webhook endpoint.
    
    This endpoint receives and processes Stripe webhook events.
    
    URL: POST /webhook/stripe
    
    Headers:
        - Stripe-Signature: Stripe webhook signature for verification
    
    Body:
        Raw Stripe event payload (JSON)
    
    Returns:
        JSON response with status
    
    Example webhook events:
        - checkout.session.completed: User completed payment
        - customer.subscription.created: New subscription created
        - customer.subscription.deleted: Subscription cancelled
        - invoice.payment_succeeded: Recurring payment succeeded
        - invoice.payment_failed: Payment failed
    """
    if not STRIPE_SERVICE_AVAILABLE:
        logger.error("Stripe service not available")
        raise HTTPException(status_code=500, detail="Stripe service not configured")
    
    # Check signature header
    if not stripe_signature:
        logger.error("Missing Stripe-Signature header")
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")
    
    try:
        # Get raw body
        payload = await request.body()
        payload_str = payload.decode('utf-8')
        
        logger.info(f"📥 Received Stripe webhook (signature: {stripe_signature[:20]}...)")
        
        # Process webhook using stripe_service
        result = process_webhook(payload_str, stripe_signature)
        
        if result['success']:
            logger.info(f"✅ Webhook processed: {result['event_type']}")
            return {
                "status": "success",
                "event_type": result['event_type'],
                "message": result['message']
            }
        else:
            logger.error(f"❌ Webhook processing failed: {result['message']}")
            raise HTTPException(status_code=400, detail=result['message'])
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    
    except Exception as e:
        logger.error(f"❌ Unexpected error processing webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/stripe/health")
async def stripe_webhook_health():
    """
    Health check endpoint for Stripe webhook.
    
    Returns:
        JSON with status
    """
    return {
        "status": "healthy",
        "service": "stripe_webhook",
        "available": STRIPE_SERVICE_AVAILABLE
    }
