#!/usr/bin/env python3
"""
Stripe Integration Service for CryptoSentinel AI Premium Subscriptions.

Handles:
- Checkout Session creation (€9/month recurring)
- Webhook processing (payment success, subscription events)
- Subscription management (create, cancel, retrieve)
- Integration with Redis for user subscription status

Author: Theo Fanget
Date: 06 February 2026
"""
import os
import stripe
import logging
from typing import Dict, Optional
from datetime import datetime
import json

# Setup logging
logger = logging.getLogger(__name__)

# ===== STRIPE CONFIGURATION =====

# Get Stripe API key from environment
STRIPE_API_KEY = os.getenv('STRIPE_API_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')
STRIPE_PRICE_ID = os.getenv('STRIPE_PRICE_ID')  # Price ID for €9/month product

# URLs for success/cancel redirects
STRIPE_SUCCESS_URL = os.getenv(
    'STRIPE_SUCCESS_URL',
    'https://t.me/SentinelAI_CryptoBot?start=payment_success'
)
STRIPE_CANCEL_URL = os.getenv(
    'STRIPE_CANCEL_URL',
    'https://t.me/SentinelAI_CryptoBot?start=payment_cancelled'
)

# Validate configuration
if not STRIPE_API_KEY:
    logger.warning("⚠️ STRIPE_API_KEY not set - Stripe integration disabled")
else:
    stripe.api_key = STRIPE_API_KEY
    logger.info(f"✅ Stripe API configured ({STRIPE_API_KEY[:7]}...)")

if not STRIPE_PRICE_ID:
    logger.warning("⚠️ STRIPE_PRICE_ID not set - using test mode")


# ===== REDIS INTEGRATION (for subscription status) =====

try:
    from backend.redis_storage import redis_client
    REDIS_AVAILABLE = True
    logger.info("✅ Redis client imported successfully")
except ImportError:
    logger.error("❌ Could not import redis_client - subscription status won't be saved")
    redis_client = None
    REDIS_AVAILABLE = False


# ===== SUBSCRIPTION STATUS MANAGEMENT =====

def get_subscription_status(user_id: int) -> str:
    """Get subscription status from Redis.
    
    Args:
        user_id: Telegram user ID
    
    Returns:
        'free' | 'premium' | 'cancelled'
    """
    if not REDIS_AVAILABLE:
        logger.warning("Redis not available - returning 'free'")
        return 'free'
    
    try:
        status = redis_client.get(f"user:{user_id}:subscription_status")
        return status if status else 'free'
    except Exception as e:
        logger.error(f"Error getting subscription status: {e}")
        return 'free'

def set_subscription_status(user_id: int, status: str) -> bool:
    """Set subscription status in Redis.
    
    Args:
        user_id: Telegram user ID
        status: 'free' | 'premium' | 'cancelled'
    
    Returns:
        True if successful
    """
    if not REDIS_AVAILABLE:
        logger.error("Redis not available - cannot save subscription status")
        return False
    
    try:
        redis_client.set(f"user:{user_id}:subscription_status", status)
        logger.info(f"✅ Subscription status updated: User {user_id} -> {status}")
        return True
    except Exception as e:
        logger.error(f"Error setting subscription status: {e}")
        return False

def save_stripe_customer_id(user_id: int, customer_id: str) -> bool:
    """Save Stripe customer ID to Redis.
    
    Args:
        user_id: Telegram user ID
        customer_id: Stripe customer ID (cus_xxxxx)
    
    Returns:
        True if successful
    """
    if not REDIS_AVAILABLE:
        return False
    
    try:
        redis_client.set(f"user:{user_id}:stripe_customer_id", customer_id)
        logger.info(f"✅ Stripe customer ID saved: User {user_id} -> {customer_id}")
        return True
    except Exception as e:
        logger.error(f"Error saving Stripe customer ID: {e}")
        return False

def get_stripe_customer_id(user_id: int) -> Optional[str]:
    """Get Stripe customer ID from Redis.
    
    Args:
        user_id: Telegram user ID
    
    Returns:
        Stripe customer ID or None
    """
    if not REDIS_AVAILABLE:
        return None
    
    try:
        return redis_client.get(f"user:{user_id}:stripe_customer_id")
    except Exception as e:
        logger.error(f"Error getting Stripe customer ID: {e}")
        return None

def save_subscription_id(user_id: int, subscription_id: str) -> bool:
    """Save Stripe subscription ID to Redis.
    
    Args:
        user_id: Telegram user ID
        subscription_id: Stripe subscription ID (sub_xxxxx)
    
    Returns:
        True if successful
    """
    if not REDIS_AVAILABLE:
        return False
    
    try:
        redis_client.set(f"user:{user_id}:subscription_id", subscription_id)
        
        # Also save subscription start date
        start_date = datetime.utcnow().isoformat()
        redis_client.set(f"user:{user_id}:subscription_start", start_date)
        
        logger.info(f"✅ Subscription ID saved: User {user_id} -> {subscription_id}")
        return True
    except Exception as e:
        logger.error(f"Error saving subscription ID: {e}")
        return False

def get_subscription_id(user_id: int) -> Optional[str]:
    """Get Stripe subscription ID from Redis.
    
    Args:
        user_id: Telegram user ID
    
    Returns:
        Stripe subscription ID or None
    """
    if not REDIS_AVAILABLE:
        return None
    
    try:
        return redis_client.get(f"user:{user_id}:subscription_id")
    except Exception as e:
        logger.error(f"Error getting subscription ID: {e}")
        return None


# ===== CHECKOUT SESSION CREATION =====

def create_checkout_session(
    user_id: int,
    username: Optional[str] = None,
    email: Optional[str] = None
) -> Dict:
    """Create a Stripe Checkout Session for Premium subscription.
    
    Args:
        user_id: Telegram user ID
        username: Telegram username (optional)
        email: User email (optional)
    
    Returns:
        Dict with 'success', 'url' (checkout URL), 'session_id', 'error'
    
    Example:
        result = create_checkout_session(123456789, "johndoe")
        if result['success']:
            print(f"Checkout URL: {result['url']}")
    """
    # Validate Stripe configuration
    if not STRIPE_API_KEY:
        logger.error("Stripe API key not configured")
        return {
            'success': False,
            'error': 'Stripe integration not configured',
            'url': None,
            'session_id': None
        }
    
    if not STRIPE_PRICE_ID:
        logger.error("Stripe Price ID not configured")
        return {
            'success': False,
            'error': 'Stripe product not configured',
            'url': None,
            'session_id': None
        }
    
    try:
        # Check if user already has a Stripe customer
        customer_id = get_stripe_customer_id(user_id)
        
        # Prepare customer data
        customer_data = {
            'metadata': {
                'telegram_user_id': str(user_id),
                'telegram_username': username or 'unknown'
            }
        }
        
        if email:
            customer_data['email'] = email
        
        # Create or retrieve Stripe customer
        if customer_id:
            try:
                customer = stripe.Customer.retrieve(customer_id)
                logger.info(f"Using existing Stripe customer: {customer_id}")
            except stripe.error.InvalidRequestError:
                # Customer doesn't exist, create new one
                customer = stripe.Customer.create(**customer_data)
                save_stripe_customer_id(user_id, customer.id)
                logger.info(f"Created new Stripe customer: {customer.id}")
        else:
            customer = stripe.Customer.create(**customer_data)
            save_stripe_customer_id(user_id, customer.id)
            logger.info(f"Created new Stripe customer: {customer.id}")
        
        # Create Checkout Session
        checkout_session = stripe.checkout.Session.create(
            customer=customer.id,
            payment_method_types=['card'],
            line_items=[
                {
                    'price': STRIPE_PRICE_ID,
                    'quantity': 1,
                }
            ],
            mode='subscription',
            success_url=STRIPE_SUCCESS_URL,
            cancel_url=STRIPE_CANCEL_URL,
            metadata={
                'telegram_user_id': str(user_id),
                'telegram_username': username or 'unknown'
            },
            subscription_data={
                'metadata': {
                    'telegram_user_id': str(user_id),
                    'telegram_username': username or 'unknown'
                }
            },
            # Allow promotion codes
            allow_promotion_codes=True,
            # Billing address collection
            billing_address_collection='auto',
        )
        
        logger.info(f"✅ Checkout session created: {checkout_session.id} for user {user_id}")
        
        return {
            'success': True,
            'url': checkout_session.url,
            'session_id': checkout_session.id,
            'error': None
        }
        
    except stripe.error.CardError as e:
        # Card error - user input issue
        logger.error(f"Stripe CardError: {e.user_message}")
        return {
            'success': False,
            'error': f"Card error: {e.user_message}",
            'url': None,
            'session_id': None
        }
    
    except stripe.error.RateLimitError as e:
        # Too many requests
        logger.error(f"Stripe RateLimitError: {str(e)}")
        return {
            'success': False,
            'error': 'Too many requests. Please try again later.',
            'url': None,
            'session_id': None
        }
    
    except stripe.error.InvalidRequestError as e:
        # Invalid parameters
        logger.error(f"Stripe InvalidRequestError: {str(e)}")
        return {
            'success': False,
            'error': 'Invalid request. Please contact support.',
            'url': None,
            'session_id': None
        }
    
    except stripe.error.AuthenticationError as e:
        # Authentication issue
        logger.error(f"Stripe AuthenticationError: {str(e)}")
        return {
            'success': False,
            'error': 'Authentication error. Please contact support.',
            'url': None,
            'session_id': None
        }
    
    except stripe.error.APIConnectionError as e:
        # Network issue
        logger.error(f"Stripe APIConnectionError: {str(e)}")
        return {
            'success': False,
            'error': 'Network error. Please try again.',
            'url': None,
            'session_id': None
        }
    
    except stripe.error.StripeError as e:
        # Generic Stripe error
        logger.error(f"Stripe StripeError: {str(e)}")
        return {
            'success': False,
            'error': 'Payment system error. Please try again.',
            'url': None,
            'session_id': None
        }
    
    except Exception as e:
        # Unexpected error
        logger.error(f"Unexpected error creating checkout session: {e}", exc_info=True)
        return {
            'success': False,
            'error': 'Unexpected error. Please contact support.',
            'url': None,
            'session_id': None
        }


# ===== WEBHOOK PROCESSING =====

def process_webhook(payload: str, sig_header: str) -> Dict:
    """Process Stripe webhook event.
    
    Args:
        payload: Raw webhook payload (as string)
        sig_header: Stripe signature header (X-Stripe-Signature)
    
    Returns:
        Dict with 'success', 'event_type', 'message'
    
    Example:
        result = process_webhook(request.body, request.headers['Stripe-Signature'])
        if result['success']:
            print(f"Processed event: {result['event_type']}")
    """
    if not STRIPE_WEBHOOK_SECRET:
        logger.error("Stripe webhook secret not configured")
        return {
            'success': False,
            'event_type': None,
            'message': 'Webhook secret not configured'
        }
    
    try:
        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
        
        event_type = event['type']
        event_data = event['data']['object']
        
        logger.info(f"📥 Received webhook: {event_type}")
        
        # Handle different event types
        if event_type == 'checkout.session.completed':
            return handle_checkout_completed(event_data)
        
        elif event_type == 'customer.subscription.created':
            return handle_subscription_created(event_data)
        
        elif event_type == 'customer.subscription.updated':
            return handle_subscription_updated(event_data)
        
        elif event_type == 'customer.subscription.deleted':
            return handle_subscription_deleted(event_data)
        
        elif event_type == 'invoice.payment_succeeded':
            return handle_payment_succeeded(event_data)
        
        elif event_type == 'invoice.payment_failed':
            return handle_payment_failed(event_data)
        
        else:
            logger.info(f"Unhandled event type: {event_type}")
            return {
                'success': True,
                'event_type': event_type,
                'message': f'Event {event_type} received but not handled'
            }
    
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid webhook signature: {e}")
        return {
            'success': False,
            'event_type': None,
            'message': 'Invalid signature'
        }
    
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        return {
            'success': False,
            'event_type': None,
            'message': f'Error: {str(e)}'
        }


# ===== WEBHOOK EVENT HANDLERS =====

def handle_checkout_completed(session) -> Dict:
    """Handle successful checkout session completion.
    
    Args:
        session: Stripe Checkout Session object
    
    Returns:
        Dict with result
    """
    try:
        # Extract user ID from metadata
        user_id_str = session.get('metadata', {}).get('telegram_user_id')
        if not user_id_str:
            logger.error("No telegram_user_id in checkout session metadata")
            return {
                'success': False,
                'event_type': 'checkout.session.completed',
                'message': 'No user ID in metadata'
            }
        
        user_id = int(user_id_str)
        customer_id = session.get('customer')
        subscription_id = session.get('subscription')
        
        # Save customer ID
        if customer_id:
            save_stripe_customer_id(user_id, customer_id)
        
        # Save subscription ID
        if subscription_id:
            save_subscription_id(user_id, subscription_id)
        
        # Update subscription status to premium
        set_subscription_status(user_id, 'premium')
        
        logger.info(f"✅ Checkout completed: User {user_id} is now Premium!")
        
        return {
            'success': True,
            'event_type': 'checkout.session.completed',
            'message': f'User {user_id} upgraded to Premium',
            'user_id': user_id
        }
    
    except Exception as e:
        logger.error(f"Error handling checkout completion: {e}", exc_info=True)
        return {
            'success': False,
            'event_type': 'checkout.session.completed',
            'message': f'Error: {str(e)}'
        }

def handle_subscription_created(subscription) -> Dict:
    """Handle subscription creation event.
    
    Args:
        subscription: Stripe Subscription object
    
    Returns:
        Dict with result
    """
    try:
        # Extract user ID from metadata
        user_id_str = subscription.get('metadata', {}).get('telegram_user_id')
        if not user_id_str:
            logger.warning("No telegram_user_id in subscription metadata")
            return {
                'success': True,  # Not an error, just not our subscription
                'event_type': 'customer.subscription.created',
                'message': 'No user ID in metadata'
            }
        
        user_id = int(user_id_str)
        subscription_id = subscription.get('id')
        
        # Save subscription ID
        save_subscription_id(user_id, subscription_id)
        
        # Update status to premium
        set_subscription_status(user_id, 'premium')
        
        logger.info(f"✅ Subscription created: User {user_id} - {subscription_id}")
        
        return {
            'success': True,
            'event_type': 'customer.subscription.created',
            'message': f'Subscription created for user {user_id}',
            'user_id': user_id
        }
    
    except Exception as e:
        logger.error(f"Error handling subscription creation: {e}", exc_info=True)
        return {
            'success': False,
            'event_type': 'customer.subscription.created',
            'message': f'Error: {str(e)}'
        }

def handle_subscription_updated(subscription) -> Dict:
    """Handle subscription update event.
    
    Args:
        subscription: Stripe Subscription object
    
    Returns:
        Dict with result
    """
    try:
        user_id_str = subscription.get('metadata', {}).get('telegram_user_id')
        if not user_id_str:
            return {
                'success': True,
                'event_type': 'customer.subscription.updated',
                'message': 'No user ID in metadata'
            }
        
        user_id = int(user_id_str)
        status = subscription.get('status')
        
        # Update subscription status based on Stripe status
        if status == 'active':
            set_subscription_status(user_id, 'premium')
            logger.info(f"✅ Subscription active: User {user_id}")
        elif status in ['canceled', 'unpaid', 'past_due']:
            set_subscription_status(user_id, 'cancelled')
            logger.info(f"⚠️ Subscription {status}: User {user_id}")
        
        return {
            'success': True,
            'event_type': 'customer.subscription.updated',
            'message': f'Subscription updated for user {user_id}: {status}',
            'user_id': user_id
        }
    
    except Exception as e:
        logger.error(f"Error handling subscription update: {e}", exc_info=True)
        return {
            'success': False,
            'event_type': 'customer.subscription.updated',
            'message': f'Error: {str(e)}'
        }

def handle_subscription_deleted(subscription) -> Dict:
    """Handle subscription deletion/cancellation event.
    
    Args:
        subscription: Stripe Subscription object
    
    Returns:
        Dict with result
    """
    try:
        user_id_str = subscription.get('metadata', {}).get('telegram_user_id')
        if not user_id_str:
            return {
                'success': True,
                'event_type': 'customer.subscription.deleted',
                'message': 'No user ID in metadata'
            }
        
        user_id = int(user_id_str)
        
        # Update status to cancelled
        set_subscription_status(user_id, 'cancelled')
        
        # Save cancellation date
        if REDIS_AVAILABLE:
            cancel_date = datetime.utcnow().isoformat()
            redis_client.set(f"user:{user_id}:subscription_end", cancel_date)
        
        logger.info(f"❌ Subscription cancelled: User {user_id}")
        
        return {
            'success': True,
            'event_type': 'customer.subscription.deleted',
            'message': f'Subscription cancelled for user {user_id}',
            'user_id': user_id
        }
    
    except Exception as e:
        logger.error(f"Error handling subscription deletion: {e}", exc_info=True)
        return {
            'success': False,
            'event_type': 'customer.subscription.deleted',
            'message': f'Error: {str(e)}'
        }

def handle_payment_succeeded(invoice) -> Dict:
    """Handle successful payment event.
    
    Args:
        invoice: Stripe Invoice object
    
    Returns:
        Dict with result
    """
    try:
        subscription_id = invoice.get('subscription')
        
        if subscription_id:
            # Retrieve subscription to get user ID
            subscription = stripe.Subscription.retrieve(subscription_id)
            user_id_str = subscription.get('metadata', {}).get('telegram_user_id')
            
            if user_id_str:
                user_id = int(user_id_str)
                
                # Ensure user is marked as premium
                set_subscription_status(user_id, 'premium')
                
                logger.info(f"✅ Payment succeeded: User {user_id} - {subscription_id}")
                
                return {
                    'success': True,
                    'event_type': 'invoice.payment_succeeded',
                    'message': f'Payment succeeded for user {user_id}',
                    'user_id': user_id
                }
        
        return {
            'success': True,
            'event_type': 'invoice.payment_succeeded',
            'message': 'Payment succeeded (no user ID)'
        }
    
    except Exception as e:
        logger.error(f"Error handling payment success: {e}", exc_info=True)
        return {
            'success': False,
            'event_type': 'invoice.payment_succeeded',
            'message': f'Error: {str(e)}'
        }

def handle_payment_failed(invoice) -> Dict:
    """Handle failed payment event.
    
    Args:
        invoice: Stripe Invoice object
    
    Returns:
        Dict with result
    """
    try:
        subscription_id = invoice.get('subscription')
        
        if subscription_id:
            # Retrieve subscription to get user ID
            subscription = stripe.Subscription.retrieve(subscription_id)
            user_id_str = subscription.get('metadata', {}).get('telegram_user_id')
            
            if user_id_str:
                user_id = int(user_id_str)
                
                # Mark subscription as cancelled due to payment failure
                set_subscription_status(user_id, 'cancelled')
                
                logger.warning(f"⚠️ Payment failed: User {user_id} - {subscription_id}")
                
                return {
                    'success': True,
                    'event_type': 'invoice.payment_failed',
                    'message': f'Payment failed for user {user_id}',
                    'user_id': user_id
                }
        
        return {
            'success': True,
            'event_type': 'invoice.payment_failed',
            'message': 'Payment failed (no user ID)'
        }
    
    except Exception as e:
        logger.error(f"Error handling payment failure: {e}", exc_info=True)
        return {
            'success': False,
            'event_type': 'invoice.payment_failed',
            'message': f'Error: {str(e)}'
        }


# ===== SUBSCRIPTION MANAGEMENT =====

def cancel_subscription(user_id: int) -> Dict:
    """Cancel a user's subscription.
    
    Args:
        user_id: Telegram user ID
    
    Returns:
        Dict with 'success', 'message'
    """
    try:
        subscription_id = get_subscription_id(user_id)
        
        if not subscription_id:
            return {
                'success': False,
                'message': 'No active subscription found'
            }
        
        # Cancel subscription at period end (user keeps access until end of billing period)
        subscription = stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=True
        )
        
        logger.info(f"✅ Subscription cancelled (at period end): User {user_id} - {subscription_id}")
        
        return {
            'success': True,
            'message': 'Subscription will cancel at the end of the billing period',
            'cancel_at': subscription.cancel_at
        }
    
    except stripe.error.InvalidRequestError as e:
        logger.error(f"Stripe error cancelling subscription: {e}")
        return {
            'success': False,
            'message': 'Subscription not found or already cancelled'
        }
    
    except Exception as e:
        logger.error(f"Error cancelling subscription: {e}", exc_info=True)
        return {
            'success': False,
            'message': f'Error: {str(e)}'
        }

def retrieve_subscription(user_id: int) -> Dict:
    """Retrieve subscription details for a user.
    
    Args:
        user_id: Telegram user ID
    
    Returns:
        Dict with subscription details or error
    """
    try:
        subscription_id = get_subscription_id(user_id)
        
        if not subscription_id:
            return {
                'success': False,
                'message': 'No subscription found',
                'subscription': None
            }
        
        # Retrieve from Stripe
        subscription = stripe.Subscription.retrieve(subscription_id)
        
        return {
            'success': True,
            'message': 'Subscription retrieved',
            'subscription': {
                'id': subscription.id,
                'status': subscription.status,
                'current_period_start': subscription.current_period_start,
                'current_period_end': subscription.current_period_end,
                'cancel_at_period_end': subscription.cancel_at_period_end,
                'cancel_at': subscription.cancel_at
            }
        }
    
    except stripe.error.InvalidRequestError as e:
        logger.error(f"Stripe error retrieving subscription: {e}")
        return {
            'success': False,
            'message': 'Subscription not found',
            'subscription': None
        }
    
    except Exception as e:
        logger.error(f"Error retrieving subscription: {e}", exc_info=True)
        return {
            'success': False,
            'message': f'Error: {str(e)}',
            'subscription': None
        }


# ===== TESTING & VALIDATION =====

def test_stripe_connection() -> bool:
    """Test Stripe API connection.
    
    Returns:
        True if connection successful
    """
    if not STRIPE_API_KEY:
        logger.error("Stripe API key not configured")
        return False
    
    try:
        # Try to retrieve account information
        account = stripe.Account.retrieve()
        logger.info(f"✅ Stripe connection successful: {account.id}")
        return True
    except Exception as e:
        logger.error(f"❌ Stripe connection failed: {e}")
        return False


if __name__ == "__main__":
    # Test script when run directly
    print("="*60)
    print("STRIPE SERVICE TEST")
    print("="*60)
    
    # Test Stripe connection
    print("\n1. Testing Stripe connection...")
    if test_stripe_connection():
        print("   ✅ Stripe connection OK")
    else:
        print("   ❌ Stripe connection FAILED")
    
    # Test Redis connection (if available)
    if REDIS_AVAILABLE:
        print("\n2. Testing Redis connection...")
        try:
            redis_client.ping()
            print("   ✅ Redis connection OK")
        except Exception as e:
            print(f"   ❌ Redis connection FAILED: {e}")
    else:
        print("\n2. Redis not available (subscription status won't be saved)")
    
    # Display configuration
    print("\n3. Configuration:")
    print(f"   STRIPE_API_KEY: {'✅ Set' if STRIPE_API_KEY else '❌ Not set'}")
    print(f"   STRIPE_WEBHOOK_SECRET: {'✅ Set' if STRIPE_WEBHOOK_SECRET else '❌ Not set'}")
    print(f"   STRIPE_PRICE_ID: {STRIPE_PRICE_ID if STRIPE_PRICE_ID else '❌ Not set'}")
    print(f"   SUCCESS_URL: {STRIPE_SUCCESS_URL}")
    print(f"   CANCEL_URL: {STRIPE_CANCEL_URL}")
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)
