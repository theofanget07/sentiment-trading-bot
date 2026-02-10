#!/usr/bin/env python3
"""
Stripe Integration Service for CryptoSentinel AI Premium Subscriptions.

PRODUCTION-READY ENHANCEMENTS:
1. Grace Period: 3-day grace for failed payments
2. Idempotency: Webhook deduplication
3. Retry Logic: Exponential backoff
4. Monitoring: Admin alerts via Telegram
5. Validation: Enhanced webhook security

Handles:
- Checkout Session creation (€9/month recurring)
- Webhook processing (payment success, subscription events)
- Subscription management (create, cancel, retrieve)
- Integration with Redis for user subscription status

Author: Theo Fanget
Date: 10 February 2026 (Enhanced)
"""
import os
import stripe
import logging
import json
import time
import hashlib
from typing import Dict, Optional, Callable, Any
from datetime import datetime, timedelta
from functools import wraps

# Setup logging with structured format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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

# Admin alert configuration
ADMIN_TELEGRAM_CHAT_ID = os.getenv('ADMIN_TELEGRAM_CHAT_ID')  # Your Telegram user ID for alerts
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Grace period configuration (3 days for payment failures)
GRACE_PERIOD_DAYS = 3

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


# ===== IMPROVEMENT 4: MONITORING & ALERTING =====

def send_admin_alert(message: str, level: str = "ERROR"):
    """Send alert to admin via Telegram.
    
    Args:
        message: Alert message
        level: Alert level (INFO, WARNING, ERROR, CRITICAL)
    """
    if not ADMIN_TELEGRAM_CHAT_ID or not TELEGRAM_BOT_TOKEN:
        logger.debug("Admin alerts not configured - skipping")
        return
    
    try:
        import requests
        
        emoji_map = {
            "INFO": "ℹ️",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "CRITICAL": "🚨"
        }
        
        emoji = emoji_map.get(level, "📢")
        
        # Build message with HTML formatting (works better than Markdown)
        alert_text = f"{emoji} <b>{level}</b>\n\n{message}\n\n<i>Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</i>"
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": ADMIN_TELEGRAM_CHAT_ID,
            "text": alert_text,
            "parse_mode": "HTML"  # HTML mode handles line breaks better
        }
        
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code == 200:
            logger.debug(f"Admin alert sent: {level}")
        else:
            logger.warning(f"Failed to send admin alert: {response.status_code}")
    
    except Exception as e:
        logger.error(f"Error sending admin alert: {e}")


def log_structured(event_type: str, data: Dict, level: str = "INFO"):
    """Log structured JSON for better monitoring.
    
    Args:
        event_type: Type of event (e.g., 'payment_success', 'webhook_error')
        data: Event data
        level: Log level
    """
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "data": data,
        "level": level
    }
    
    log_message = json.dumps(log_entry)
    
    if level == "INFO":
        logger.info(log_message)
    elif level == "WARNING":
        logger.warning(log_message)
    elif level == "ERROR":
        logger.error(log_message)
    elif level == "CRITICAL":
        logger.critical(log_message)


# ===== IMPROVEMENT 3: RETRY LOGIC =====

def retry_stripe_call(max_retries: int = 3, backoff_factor: float = 2.0):
    """Decorator for retrying Stripe API calls with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Exponential backoff multiplier
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            retries = 0
            while retries <= max_retries:
                try:
                    return func(*args, **kwargs)
                
                except stripe.error.RateLimitError as e:
                    if retries == max_retries:
                        log_structured("stripe_rate_limit", {
                            "function": func.__name__,
                            "retries": retries,
                            "error": str(e)
                        }, "ERROR")
                        raise
                    
                    wait_time = backoff_factor ** retries
                    logger.warning(f"Rate limit hit, retrying in {wait_time}s... (attempt {retries + 1}/{max_retries})")
                    time.sleep(wait_time)
                    retries += 1
                
                except stripe.error.APIConnectionError as e:
                    if retries == max_retries:
                        log_structured("stripe_connection_error", {
                            "function": func.__name__,
                            "retries": retries,
                            "error": str(e)
                        }, "ERROR")
                        raise
                    
                    wait_time = backoff_factor ** retries
                    logger.warning(f"API connection error, retrying in {wait_time}s... (attempt {retries + 1}/{max_retries})")
                    time.sleep(wait_time)
                    retries += 1
                
                except Exception as e:
                    # Don't retry on other exceptions
                    log_structured("stripe_unexpected_error", {
                        "function": func.__name__,
                        "error": str(e),
                        "type": type(e).__name__
                    }, "ERROR")
                    raise
        
        return wrapper
    return decorator


# ===== IMPROVEMENT 2: IDEMPOTENCY =====

def webhook_idempotency_check(event_id: str) -> bool:
    """Check if webhook event has already been processed.
    
    Args:
        event_id: Stripe event ID
    
    Returns:
        True if event is new (not processed), False if duplicate
    """
    if not REDIS_AVAILABLE:
        logger.warning("Redis not available - idempotency check skipped")
        return True
    
    try:
        # Check if event ID exists in Redis
        key = f"stripe:webhook:processed:{event_id}"
        exists = redis_client.exists(key)
        
        if exists:
            logger.warning(f"🔁 Duplicate webhook detected: {event_id}")
            log_structured("webhook_duplicate", {"event_id": event_id}, "WARNING")
            return False
        
        # Mark event as processed (expire after 7 days)
        redis_client.setex(key, 7 * 24 * 60 * 60, "1")
        return True
    
    except Exception as e:
        logger.error(f"Error checking webhook idempotency: {e}")
        # On error, allow processing (fail open)
        return True


# ===== IMPROVEMENT 5: VALIDATION =====

def validate_webhook_data(event_data: Dict, required_fields: list) -> bool:
    """Validate webhook event data.
    
    Args:
        event_data: Webhook event data
        required_fields: List of required field names
    
    Returns:
        True if valid, False otherwise
    """
    try:
        # Check required fields exist
        for field in required_fields:
            if field not in event_data or event_data[field] is None:
                logger.error(f"Missing required field: {field}")
                return False
        
        # Validate metadata if present
        if 'metadata' in event_data:
            metadata = event_data['metadata']
            if 'telegram_user_id' in metadata:
                user_id = metadata['telegram_user_id']
                # Validate user ID is numeric
                try:
                    int(user_id)
                except ValueError:
                    logger.error(f"Invalid telegram_user_id: {user_id}")
                    return False
        
        return True
    
    except Exception as e:
        logger.error(f"Error validating webhook data: {e}")
        return False


# ===== IMPROVEMENT 1: GRACE PERIOD MANAGEMENT =====

def set_grace_period(user_id: int, invoice_id: str) -> bool:
    """Set grace period for user after payment failure.
    
    Args:
        user_id: Telegram user ID
        invoice_id: Stripe invoice ID
    
    Returns:
        True if successful
    """
    if not REDIS_AVAILABLE:
        return False
    
    try:
        grace_end = datetime.utcnow() + timedelta(days=GRACE_PERIOD_DAYS)
        
        # Store grace period info
        redis_client.set(
            f"user:{user_id}:grace_period_end",
            grace_end.isoformat()
        )
        redis_client.set(
            f"user:{user_id}:grace_period_invoice",
            invoice_id
        )
        
        # Don't immediately downgrade - keep as premium during grace
        set_subscription_status(user_id, 'premium')
        
        logger.info(f"⏳ Grace period set for user {user_id} until {grace_end.isoformat()}")
        
        log_structured("grace_period_started", {
            "user_id": user_id,
            "invoice_id": invoice_id,
            "grace_end": grace_end.isoformat()
        }, "INFO")
        
        return True
    
    except Exception as e:
        logger.error(f"Error setting grace period: {e}")
        return False


def check_grace_period_expired(user_id: int) -> bool:
    """Check if user's grace period has expired.
    
    Args:
        user_id: Telegram user ID
    
    Returns:
        True if expired or no grace period, False if still in grace
    """
    if not REDIS_AVAILABLE:
        return True
    
    try:
        grace_end_str = redis_client.get(f"user:{user_id}:grace_period_end")
        
        if not grace_end_str:
            return True  # No grace period
        
        grace_end = datetime.fromisoformat(grace_end_str)
        
        if datetime.utcnow() > grace_end:
            # Grace period expired - downgrade user
            set_subscription_status(user_id, 'free')
            
            # Clean up grace period keys
            redis_client.delete(f"user:{user_id}:grace_period_end")
            redis_client.delete(f"user:{user_id}:grace_period_invoice")
            
            logger.info(f"❌ Grace period expired for user {user_id} - downgraded to Free")
            
            log_structured("grace_period_expired", {
                "user_id": user_id,
                "downgraded_at": datetime.utcnow().isoformat()
            }, "INFO")
            
            return True
        
        return False  # Still in grace period
    
    except Exception as e:
        logger.error(f"Error checking grace period: {e}")
        return True


def notify_user_payment_failed(user_id: int):
    """Send notification to user about payment failure.
    
    Args:
        user_id: Telegram user ID
    """
    try:
        import requests
        
        if not TELEGRAM_BOT_TOKEN:
            return
        
        grace_end_str = redis_client.get(f"user:{user_id}:grace_period_end") if REDIS_AVAILABLE else None
        if grace_end_str:
            grace_end = datetime.fromisoformat(grace_end_str)
            grace_days = (grace_end - datetime.utcnow()).days + 1
        else:
            grace_days = GRACE_PERIOD_DAYS
        
        # Build message with HTML formatting
        message = (
            f"⚠️ <b>Payment Failed</b>\n\n"
            f"Your payment for CryptoSentinel Premium could not be processed.\n\n"
            f"<b>You have {grace_days} days to update your payment method.</b>\n\n"
            f"After {grace_days} days, you will be downgraded to the Free tier.\n\n"
            f"To update your payment: /manage"
        )
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": user_id,
            "text": message,
            "parse_mode": "HTML"  # HTML mode for proper line breaks
        }
        
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code == 200:
            logger.info(f"📧 Payment failure notification sent to user {user_id}")
        
    except Exception as e:
        logger.error(f"Error sending payment failure notification: {e}")


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
        # Check if grace period expired
        check_grace_period_expired(user_id)
        
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
        
        log_structured("subscription_status_changed", {
            "user_id": user_id,
            "status": status
        }, "INFO")
        
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

@retry_stripe_call(max_retries=3)
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
    """
    # Validate Stripe configuration
    if not STRIPE_API_KEY:
        logger.error("Stripe API key not configured")
        send_admin_alert("Stripe API key not configured!", "CRITICAL")
        return {
            'success': False,
            'error': 'Stripe integration not configured',
            'url': None,
            'session_id': None
        }
    
    if not STRIPE_PRICE_ID:
        logger.error("Stripe Price ID not configured")
        send_admin_alert("Stripe Price ID not configured!", "CRITICAL")
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
        
        log_structured("checkout_session_created", {
            "user_id": user_id,
            "session_id": checkout_session.id,
            "customer_id": customer.id
        }, "INFO")
        
        return {
            'success': True,
            'url': checkout_session.url,
            'session_id': checkout_session.id,
            'error': None
        }
        
    except stripe.error.CardError as e:
        logger.error(f"Stripe CardError: {e.user_message}")
        return {
            'success': False,
            'error': f"Card error: {e.user_message}",
            'url': None,
            'session_id': None
        }
    
    except stripe.error.InvalidRequestError as e:
        logger.error(f"Stripe InvalidRequestError: {str(e)}")
        send_admin_alert(f"Stripe InvalidRequestError in checkout: {str(e)}", "ERROR")
        return {
            'success': False,
            'error': 'Invalid request. Please contact support.',
            'url': None,
            'session_id': None
        }
    
    except Exception as e:
        logger.error(f"Unexpected error creating checkout session: {e}", exc_info=True)
        send_admin_alert(f"Unexpected checkout error: {str(e)}", "CRITICAL")
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
        event_id = event['id']
        
        logger.info(f"📥 Received webhook: {event_type} (ID: {event_id})")
        
        # Check for duplicate webhook
        if not webhook_idempotency_check(event_id):
            return {
                'success': True,
                'event_type': event_type,
                'message': f'Duplicate webhook ignored: {event_id}'
            }
        
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
        send_admin_alert(f"Invalid webhook signature detected!", "WARNING")
        return {
            'success': False,
            'event_type': None,
            'message': 'Invalid signature'
        }
    
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        send_admin_alert(f"Webhook processing error: {str(e)}", "ERROR")
        return {
            'success': False,
            'event_type': None,
            'message': f'Error: {str(e)}'
        }


# ===== WEBHOOK EVENT HANDLERS =====

def handle_checkout_completed(session) -> Dict:
    """Handle successful checkout session completion."""
    try:
        # Validate required fields
        if not validate_webhook_data(session, ['metadata', 'customer', 'subscription']):
            return {
                'success': False,
                'event_type': 'checkout.session.completed',
                'message': 'Invalid webhook data'
            }
        
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
        
        # Clear any existing grace period
        if REDIS_AVAILABLE:
            redis_client.delete(f"user:{user_id}:grace_period_end")
            redis_client.delete(f"user:{user_id}:grace_period_invoice")
        
        # Update subscription status to premium
        set_subscription_status(user_id, 'premium')
        
        logger.info(f"✅ Checkout completed: User {user_id} is now Premium!")
        
        log_structured("checkout_completed", {
            "user_id": user_id,
            "customer_id": customer_id,
            "subscription_id": subscription_id
        }, "INFO")
        
        return {
            'success': True,
            'event_type': 'checkout.session.completed',
            'message': f'User {user_id} upgraded to Premium',
            'user_id': user_id
        }
    
    except Exception as e:
        logger.error(f"Error handling checkout completion: {e}", exc_info=True)
        send_admin_alert(f"Checkout completion error for session: {str(e)}", "ERROR")
        return {
            'success': False,
            'event_type': 'checkout.session.completed',
            'message': f'Error: {str(e)}'
        }

def handle_subscription_created(subscription) -> Dict:
    """Handle subscription creation event."""
    try:
        if not validate_webhook_data(subscription, ['metadata', 'id']):
            return {
                'success': False,
                'event_type': 'customer.subscription.created',
                'message': 'Invalid webhook data'
            }
        
        user_id_str = subscription.get('metadata', {}).get('telegram_user_id')
        if not user_id_str:
            logger.warning("No telegram_user_id in subscription metadata")
            return {
                'success': True,
                'event_type': 'customer.subscription.created',
                'message': 'No user ID in metadata'
            }
        
        user_id = int(user_id_str)
        subscription_id = subscription.get('id')
        
        save_subscription_id(user_id, subscription_id)
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
    """Handle subscription update event."""
    try:
        if not validate_webhook_data(subscription, ['metadata', 'status']):
            return {
                'success': False,
                'event_type': 'customer.subscription.updated',
                'message': 'Invalid webhook data'
            }
        
        user_id_str = subscription.get('metadata', {}).get('telegram_user_id')
        if not user_id_str:
            return {
                'success': True,
                'event_type': 'customer.subscription.updated',
                'message': 'No user ID in metadata'
            }
        
        user_id = int(user_id_str)
        status = subscription.get('status')
        
        if status == 'active':
            # Clear grace period if payment succeeded
            if REDIS_AVAILABLE:
                redis_client.delete(f"user:{user_id}:grace_period_end")
                redis_client.delete(f"user:{user_id}:grace_period_invoice")
            set_subscription_status(user_id, 'premium')
            logger.info(f"✅ Subscription active: User {user_id}")
        elif status in ['canceled', 'unpaid']:
            set_subscription_status(user_id, 'cancelled')
            logger.info(f"⚠️ Subscription {status}: User {user_id}")
        elif status == 'past_due':
            # Don't immediately cancel - grace period handles this
            logger.info(f"⏳ Subscription past_due: User {user_id} (grace period active)")
        
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
    """Handle subscription deletion/cancellation event."""
    try:
        if not validate_webhook_data(subscription, ['metadata']):
            return {
                'success': False,
                'event_type': 'customer.subscription.deleted',
                'message': 'Invalid webhook data'
            }
        
        user_id_str = subscription.get('metadata', {}).get('telegram_user_id')
        if not user_id_str:
            return {
                'success': True,
                'event_type': 'customer.subscription.deleted',
                'message': 'No user ID in metadata'
            }
        
        user_id = int(user_id_str)
        
        set_subscription_status(user_id, 'cancelled')
        
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
    """Handle successful payment event."""
    try:
        subscription_id = invoice.get('subscription')
        
        if subscription_id:
            subscription = stripe.Subscription.retrieve(subscription_id)
            user_id_str = subscription.get('metadata', {}).get('telegram_user_id')
            
            if user_id_str:
                user_id = int(user_id_str)
                
                # Clear any grace period
                if REDIS_AVAILABLE:
                    redis_client.delete(f"user:{user_id}:grace_period_end")
                    redis_client.delete(f"user:{user_id}:grace_period_invoice")
                
                set_subscription_status(user_id, 'premium')
                
                logger.info(f"✅ Payment succeeded: User {user_id} - {subscription_id}")
                
                log_structured("payment_succeeded", {
                    "user_id": user_id,
                    "subscription_id": subscription_id,
                    "amount": invoice.get('amount_paid')
                }, "INFO")
                
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
    """Handle failed payment event with grace period."""
    try:
        subscription_id = invoice.get('subscription')
        invoice_id = invoice.get('id')
        
        if subscription_id:
            subscription = stripe.Subscription.retrieve(subscription_id)
            user_id_str = subscription.get('metadata', {}).get('telegram_user_id')
            
            if user_id_str:
                user_id = int(user_id_str)
                
                # Set grace period instead of immediate cancellation
                set_grace_period(user_id, invoice_id)
                
                # Notify user
                notify_user_payment_failed(user_id)
                
                # Alert admin with formatted message
                admin_message = (
                    f"Payment failed for user {user_id}\n"
                    f"Grace period: {GRACE_PERIOD_DAYS} days\n"
                    f"Invoice: {invoice_id}"
                )
                send_admin_alert(admin_message, "WARNING")
                
                logger.warning(f"⚠️ Payment failed: User {user_id} - Grace period started")
                
                log_structured("payment_failed", {
                    "user_id": user_id,
                    "subscription_id": subscription_id,
                    "invoice_id": invoice_id,
                    "grace_period_days": GRACE_PERIOD_DAYS
                }, "WARNING")
                
                return {
                    'success': True,
                    'event_type': 'invoice.payment_failed',
                    'message': f'Payment failed for user {user_id} - grace period started',
                    'user_id': user_id
                }
        
        return {
            'success': True,
            'event_type': 'invoice.payment_failed',
            'message': 'Payment failed (no user ID)'
        }
    
    except Exception as e:
        logger.error(f"Error handling payment failure: {e}", exc_info=True)
        send_admin_alert(f"Error handling payment failure: {str(e)}", "ERROR")
        return {
            'success': False,
            'event_type': 'invoice.payment_failed',
            'message': f'Error: {str(e)}'
        }


# ===== SUBSCRIPTION MANAGEMENT =====

@retry_stripe_call(max_retries=3)
def cancel_subscription(user_id: int) -> Dict:
    """Cancel a user's subscription."""
    try:
        subscription_id = get_subscription_id(user_id)
        
        if not subscription_id:
            return {
                'success': False,
                'message': 'No active subscription found'
            }
        
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

@retry_stripe_call(max_retries=3)
def retrieve_subscription(user_id: int) -> Dict:
    """Retrieve subscription details for a user."""
    try:
        subscription_id = get_subscription_id(user_id)
        
        if not subscription_id:
            return {
                'success': False,
                'message': 'No subscription found',
                'subscription': None
            }
        
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

@retry_stripe_call(max_retries=3)
def test_stripe_connection() -> bool:
    """Test Stripe API connection."""
    if not STRIPE_API_KEY:
        logger.error("Stripe API key not configured")
        return False
    
    try:
        account = stripe.Account.retrieve()
        logger.info(f"✅ Stripe connection successful: {account.id}")
        return True
    except Exception as e:
        logger.error(f"❌ Stripe connection failed: {e}")
        send_admin_alert(f"Stripe connection test failed: {str(e)}", "CRITICAL")
        return False


if __name__ == "__main__":
    print("="*60)
    print("STRIPE SERVICE TEST - ENHANCED VERSION")
    print("="*60)
    
    print("\n1. Testing Stripe connection...")
    if test_stripe_connection():
        print("   ✅ Stripe connection OK")
    else:
        print("   ❌ Stripe connection FAILED")
    
    if REDIS_AVAILABLE:
        print("\n2. Testing Redis connection...")
        try:
            redis_client.ping()
            print("   ✅ Redis connection OK")
        except Exception as e:
            print(f"   ❌ Redis connection FAILED: {e}")
    else:
        print("\n2. Redis not available")
    
    print("\n3. Configuration:")
    print(f"   STRIPE_API_KEY: {'✅ Set' if STRIPE_API_KEY else '❌ Not set'}")
    print(f"   STRIPE_WEBHOOK_SECRET: {'✅ Set' if STRIPE_WEBHOOK_SECRET else '❌ Not set'}")
    print(f"   STRIPE_PRICE_ID: {STRIPE_PRICE_ID if STRIPE_PRICE_ID else '❌ Not set'}")
    print(f"   ADMIN_TELEGRAM_CHAT_ID: {'✅ Set' if ADMIN_TELEGRAM_CHAT_ID else '❌ Not set'}")
    print(f"   GRACE_PERIOD_DAYS: {GRACE_PERIOD_DAYS}")
    
    print("\n4. New Features:")
    print("   ✅ Grace Period (3 days)")
    print("   ✅ Webhook Idempotency")
    print("   ✅ Retry Logic (3 attempts)")
    print("   ✅ Admin Alerts")
    print("   ✅ Enhanced Validation")
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)
