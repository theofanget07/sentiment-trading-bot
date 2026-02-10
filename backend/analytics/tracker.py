"""
AnalyticsTracker - Core Event Tracking System
Captures all user actions and stores them efficiently in Redis
"""

import logging
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import redis
from functools import wraps

logger = logging.getLogger(__name__)


class AnalyticsTracker:
    """
    Core analytics tracker for all user events.
    
    Events tracked:
    - Command usage (analyze, recommend, portfolio, etc.)
    - User registrations (/start)
    - Conversions (Free → Premium)
    - Errors and failures
    - API calls (latency, costs)
    """
    
    # Define user errors that should NOT trigger alerts
    USER_ERRORS = {
        'position_not_found',
        'alert_not_found',
        'invalid_arguments',
        'invalid_symbol',
        'invalid_price',
        'invalid_quantity',
        'insufficient_balance',
        'awaiting_confirmation',
        'already_premium',
        'not_premium',
        'tp_exists',
        'sl_exists',
        'invalid_tp_price',
        'invalid_sl_price',
        'price_unavailable'  # Temporary API issues, not system errors
    }
    
    def __init__(self, redis_client: redis.Redis):
        """
        Initialize the analytics tracker.
        
        Args:
            redis_client: Redis connection instance
        """
        self.redis = redis_client
        logger.info("✅ AnalyticsTracker initialized")
    
    def track_event(
        self,
        event_type: str,
        user_id: int,
        data: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """
        Track a user event.
        
        Args:
            event_type: Type of event (e.g., 'command', 'conversion', 'error')
            user_id: Telegram user ID
            data: Additional event data
            timestamp: Event timestamp (defaults to now)
        
        Returns:
            bool: Success status
        """
        try:
            if timestamp is None:
                timestamp = datetime.now(timezone.utc)
            
            date_key = timestamp.strftime("%Y-%m-%d")
            hour_key = timestamp.strftime("%Y-%m-%d-%H")
            
            # Build event payload
            event = {
                "event_type": event_type,
                "user_id": user_id,
                "timestamp": timestamp.isoformat(),
                "data": data or {}
            }
            
            # Store event in Redis (TTL 30 days)
            event_key = f"events:{date_key}:{event_type}:{user_id}:{timestamp.timestamp()}"
            self.redis.setex(
                event_key,
                30 * 24 * 60 * 60,  # 30 days
                json.dumps(event)
            )
            
            # Increment counters for quick queries
            self.redis.incr(f"count:events:{date_key}")
            self.redis.incr(f"count:events:{date_key}:{event_type}")
            self.redis.incr(f"count:events:{hour_key}:{event_type}")
            
            # Track active users
            self.redis.sadd(f"users:active:{date_key}", user_id)
            self.redis.sadd(f"users:active:hour:{hour_key}", user_id)
            
            # Set TTL on counters (31 days to be safe)
            for key in [
                f"count:events:{date_key}",
                f"count:events:{date_key}:{event_type}",
                f"count:events:{hour_key}:{event_type}",
                f"users:active:{date_key}",
                f"users:active:hour:{hour_key}"
            ]:
                self.redis.expire(key, 31 * 24 * 60 * 60)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to track event {event_type}: {e}")
            return False
    
    def _is_user_error(self, error: Optional[str]) -> bool:
        """
        Determine if an error is a user error (not a system error).
        
        Args:
            error: Error message or code
        
        Returns:
            bool: True if user error, False if system error
        """
        if not error:
            return False
        
        error_lower = error.lower()
        
        # Check against known user error patterns
        for user_error_pattern in self.USER_ERRORS:
            if user_error_pattern in error_lower:
                return True
        
        # Additional patterns
        user_error_indicators = [
            'not found',
            'invalid',
            'must be',
            'cannot',
            'already',
            'awaiting',
            'usage:',
            'example:',
            'please provide'
        ]
        
        for indicator in user_error_indicators:
            if indicator in error_lower:
                return True
        
        return False
    
    def track_command(
        self,
        command: str,
        user_id: int,
        success: bool = True,
        latency_ms: Optional[float] = None,
        error: Optional[str] = None
    ) -> bool:
        """
        Track a bot command execution.
        
        Args:
            command: Command name (e.g., 'analyze', 'portfolio')
            user_id: Telegram user ID
            success: Whether the command succeeded
            latency_ms: Command execution time in milliseconds
            error: Error message if failed
        
        Returns:
            bool: Success status
        """
        data = {
            "command": command,
            "success": success,
            "latency_ms": latency_ms,
            "error": error
        }
        
        # Categorize error type
        if success:
            event_type = "command_success"
        else:
            # Distinguish between user errors and system errors
            is_user_error = self._is_user_error(error)
            event_type = "command_user_error" if is_user_error else "command_system_error"
            
            # Log for debugging
            if is_user_error:
                logger.debug(f"👤 User error in {command}: {error}")
            else:
                logger.warning(f"⚠️ System error in {command}: {error}")
        
        return self.track_event(event_type, user_id, data)
    
    def track_conversion(
        self,
        user_id: int,
        from_tier: str = "free",
        to_tier: str = "premium",
        subscription_id: Optional[str] = None,
        amount: Optional[float] = None
    ) -> bool:
        """
        Track a user conversion (Free → Premium).
        
        Args:
            user_id: Telegram user ID
            from_tier: Source tier
            to_tier: Target tier
            subscription_id: Stripe subscription ID
            amount: Monthly subscription amount
        
        Returns:
            bool: Success status
        """
        data = {
            "from_tier": from_tier,
            "to_tier": to_tier,
            "subscription_id": subscription_id,
            "amount": amount
        }
        
        # Track conversion event
        success = self.track_event("conversion", user_id, data)
        
        if success:
            # Add to premium users set
            date_key = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            self.redis.sadd(f"users:premium:{date_key}", user_id)
            self.redis.sadd("users:premium:all", user_id)
            self.redis.expire(f"users:premium:{date_key}", 31 * 24 * 60 * 60)
        
        return success
    
    def track_registration(
        self,
        user_id: int,
        username: Optional[str] = None,
        referral_source: Optional[str] = None
    ) -> bool:
        """
        Track a new user registration.
        
        Args:
            user_id: Telegram user ID
            username: Telegram username
            referral_source: How user found the bot
        
        Returns:
            bool: Success status
        """
        data = {
            "username": username,
            "referral_source": referral_source
        }
        
        success = self.track_event("registration", user_id, data)
        
        if success:
            # Add to registered users set
            date_key = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            self.redis.sadd(f"users:registered:{date_key}", user_id)
            self.redis.sadd("users:registered:all", user_id)
            self.redis.expire(f"users:registered:{date_key}", 31 * 24 * 60 * 60)
        
        return success
    
    def track_api_call(
        self,
        api_name: str,
        user_id: int,
        latency_ms: float,
        success: bool = True,
        cost_usd: Optional[float] = None,
        error: Optional[str] = None
    ) -> bool:
        """
        Track external API calls (OpenAI, CoinGecko, etc.).
        
        Args:
            api_name: API name (e.g., 'perplexity', 'coingecko')
            user_id: Telegram user ID
            latency_ms: API call latency in milliseconds
            success: Whether the call succeeded
            cost_usd: API call cost in USD
            error: Error message if failed
        
        Returns:
            bool: Success status
        """
        data = {
            "api_name": api_name,
            "latency_ms": latency_ms,
            "success": success,
            "cost_usd": cost_usd,
            "error": error
        }
        
        event_type = f"api_call_{api_name}"
        success_status = self.track_event(event_type, user_id, data)
        
        # Track API costs
        if success_status and cost_usd is not None:
            date_key = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            self.redis.incrbyfloat(f"cost:api:{api_name}:{date_key}", cost_usd)
            self.redis.incrbyfloat(f"cost:api:total:{date_key}", cost_usd)
            self.redis.expire(f"cost:api:{api_name}:{date_key}", 31 * 24 * 60 * 60)
            self.redis.expire(f"cost:api:total:{date_key}", 31 * 24 * 60 * 60)
        
        return success_status


def track_command_decorator(tracker: AnalyticsTracker):
    """
    Decorator to automatically track command execution.
    
    Usage:
        @track_command_decorator(tracker)
        async def analyze_command(update, context):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(update, context, *args, **kwargs):
            start_time = datetime.now()
            user_id = update.effective_user.id
            command = func.__name__.replace('_command', '').replace('_handler', '')
            
            try:
                result = await func(update, context, *args, **kwargs)
                
                # Track success
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                tracker.track_command(
                    command=command,
                    user_id=user_id,
                    success=True,
                    latency_ms=latency_ms
                )
                
                return result
                
            except Exception as e:
                # Track error
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                tracker.track_command(
                    command=command,
                    user_id=user_id,
                    success=False,
                    latency_ms=latency_ms,
                    error=str(e)
                )
                raise
        
        return wrapper
    return decorator
