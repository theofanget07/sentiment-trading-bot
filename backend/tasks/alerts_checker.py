"""Feature 1: Price Alerts Checker - Celery task.

Monitors user crypto positions and sends alerts when:
- Price reaches +10% profit (take profit alert)
- Price reaches -5% loss (stop loss warning)

Runs every 15 minutes via Celery Beat.
"""

import logging
from typing import List, Dict
from backend.celery_app import app
from backend.redis_storage import RedisStorage
from backend.crypto_prices import get_crypto_price
from backend.services.notification_service import get_notification_service

logger = logging.getLogger(__name__)

# Alert thresholds
PROFIT_ALERT_PCT = 10.0  # Alert at +10% profit
LOSS_ALERT_PCT = -5.0    # Alert at -5% loss


@app.task(name="backend.tasks.alerts_checker.check_all_price_alerts")
def check_all_price_alerts() -> Dict:
    """Check price alerts for all users and send notifications.
    
    Returns:
        Dict with task execution summary
    """
    logger.info("[TASK] Starting price alerts check...")
    
    storage = RedisStorage()
    notification_service = get_notification_service()
    
    alerts_sent = 0
    users_checked = 0
    errors = 0
    
    try:
        # Get all user IDs from Redis
        user_ids = storage.get_all_user_ids()
        logger.info(f"Found {len(user_ids)} users to check")
        
        for user_id in user_ids:
            try:
                users_checked += 1
                chat_id = int(user_id.replace("user:", ""))
                
                # Get user's portfolio
                portfolio = storage.get_portfolio(chat_id)
                if not portfolio:
                    continue
                
                # Check each position
                for symbol, position in portfolio.items():
                    alert_triggered = check_position_alert(
                        chat_id=chat_id,
                        symbol=symbol,
                        position=position,
                        notification_service=notification_service,
                    )
                    
                    if alert_triggered:
                        alerts_sent += 1
            
            except Exception as e:
                logger.error(f"Error checking user {user_id}: {e}")
                errors += 1
        
        result = {
            "status": "completed",
            "users_checked": users_checked,
            "alerts_sent": alerts_sent,
            "errors": errors,
        }
        
        logger.info(f"[TASK] Price alerts check completed: {result}")
        return result
    
    except Exception as e:
        logger.error(f"[TASK] Price alerts check failed: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "users_checked": users_checked,
            "alerts_sent": alerts_sent,
        }


def check_position_alert(
    chat_id: int,
    symbol: str,
    position: Dict,
    notification_service,
) -> bool:
    """Check if a position triggers an alert and send notification.
    
    Args:
        chat_id: User's Telegram chat ID
        symbol: Crypto symbol (e.g., 'BTC')
        position: Position data dict
        notification_service: Notification service instance
    
    Returns:
        True if alert was sent
    """
    try:
        # Get current price
        current_price = get_crypto_price(symbol)
        if not current_price:
            logger.warning(f"Could not fetch price for {symbol}")
            return False
        
        # Calculate P&L
        buy_price = position.get("buy_price", 0)
        qty = position.get("qty", 0)
        
        if buy_price <= 0 or qty <= 0:
            return False
        
        pnl_pct = ((current_price - buy_price) / buy_price) * 100
        pnl_usd = (current_price - buy_price) * qty
        
        # Check if alert threshold is crossed
        should_alert = False
        
        if pnl_pct >= PROFIT_ALERT_PCT:
            should_alert = True
            logger.info(f"PROFIT ALERT: {symbol} for user {chat_id} - {pnl_pct:.2f}%")
        
        elif pnl_pct <= LOSS_ALERT_PCT:
            should_alert = True
            logger.info(f"LOSS ALERT: {symbol} for user {chat_id} - {pnl_pct:.2f}%")
        
        if should_alert:
            # Send alert notification
            success = notification_service.send_price_alert(
                chat_id=chat_id,
                crypto_symbol=symbol,
                current_price=current_price,
                buy_price=buy_price,
                pnl_usd=pnl_usd,
                pnl_pct=pnl_pct,
            )
            
            return success
        
        return False
    
    except Exception as e:
        logger.error(f"Error checking position {symbol} for user {chat_id}: {e}")
        return False


@app.task(name="backend.tasks.alerts_checker.test_alert")
def test_alert(chat_id: int, symbol: str = "BTC") -> Dict:
    """Test task to manually trigger an alert (for testing).
    
    Args:
        chat_id: Telegram chat ID
        symbol: Crypto symbol to test
    
    Returns:
        Dict with test result
    """
    logger.info(f"[TEST] Sending test alert to {chat_id} for {symbol}")
    
    notification_service = get_notification_service()
    
    # Send fake alert
    success = notification_service.send_price_alert(
        chat_id=chat_id,
        crypto_symbol=symbol,
        current_price=95000.0,
        buy_price=85000.0,
        pnl_usd=1000.0,
        pnl_pct=11.76,
    )
    
    return {
        "status": "completed" if success else "failed",
        "chat_id": chat_id,
        "symbol": symbol,
    }
