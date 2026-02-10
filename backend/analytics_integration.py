"""
Analytics Integration Helper
Helps integrate analytics tracking into bot_webhook.py
"""

import logging
from backend.analytics.tracker import AnalyticsTracker
from backend.redis_storage import get_redis_client

logger = logging.getLogger(__name__)

# Global analytics tracker instance
analytics_tracker = None

def init_analytics():
    """
    Initialize analytics tracker.
    Call this in bot_webhook.py startup.
    """
    global analytics_tracker
    
    try:
        redis_client = get_redis_client()
        analytics_tracker = AnalyticsTracker(redis_client)
        logger.info("✅ Analytics tracking initialized")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize analytics: {e}")
        analytics_tracker = None
        return False

def track_command(command_name: str, user_id: int, success: bool = True, error: str = None):
    """
    Track a command execution.
    
    Args:
        command_name: Name of command (e.g., 'analyze', 'portfolio')
        user_id: Telegram user ID
        success: Whether command succeeded
        error: Error message if failed
    """
    if analytics_tracker:
        analytics_tracker.track_command(
            command=command_name,
            user_id=user_id,
            success=success,
            error=error
        )

def track_registration(user_id: int, username: str = None):
    """
    Track a new user registration.
    Call this in /start handler.
    """
    if analytics_tracker:
        analytics_tracker.track_registration(
            user_id=user_id,
            username=username
        )

def track_conversion(user_id: int, subscription_id: str = None, amount: float = 9.0):
    """
    Track a Free → Premium conversion.
    Call this in Stripe webhook handler.
    """
    if analytics_tracker:
        analytics_tracker.track_conversion(
            user_id=user_id,
            subscription_id=subscription_id,
            amount=amount
        )

def track_api_call(api_name: str, user_id: int, latency_ms: float, success: bool = True, cost_usd: float = None):
    """
    Track external API calls (Perplexity, CoinGecko, etc.).
    """
    if analytics_tracker:
        analytics_tracker.track_api_call(
            api_name=api_name,
            user_id=user_id,
            latency_ms=latency_ms,
            success=success,
            cost_usd=cost_usd
        )
