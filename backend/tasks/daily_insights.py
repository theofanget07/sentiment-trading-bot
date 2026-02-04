"""Feature 5: Daily Portfolio Insights - Celery task.

Sends daily portfolio summary to each user including:
- Total portfolio value
- 24h change
- Best/worst performers
- Market news summary

Runs daily at 8:00 AM CET via Celery Beat.
"""

import logging
from typing import Dict, List, Tuple
from backend.celery_app import app
from backend.redis_storage import RedisStorage
from backend.crypto_prices import get_crypto_price
from backend.services.perplexity_client import get_perplexity_client
from backend.services.notification_service import get_notification_service

logger = logging.getLogger(__name__)


@app.task(name="backend.tasks.daily_insights.send_daily_portfolio_insights")
def send_daily_portfolio_insights() -> Dict:
    """Send daily portfolio insights to all users.
    
    Returns:
        Dict with task execution summary
    """
    logger.info("[TASK] Starting daily portfolio insights...")
    
    storage = RedisStorage()
    perplexity = get_perplexity_client()
    notification_service = get_notification_service()
    
    insights_sent = 0
    users_processed = 0
    errors = 0
    
    try:
        # Get all user IDs
        user_ids = storage.get_all_user_ids()
        logger.info(f"Sending daily insights to {len(user_ids)} users")
        
        for user_id in user_ids:
            try:
                users_processed += 1
                chat_id = int(user_id.replace("user:", ""))
                
                # Get user's portfolio
                portfolio = storage.get_portfolio(chat_id)
                if not portfolio:
                    logger.debug(f"User {chat_id} has no portfolio, skipping")
                    continue
                
                # Get username (from Redis or default)
                username = storage.get_user_data(chat_id, "username") or "User"
                
                # Calculate portfolio metrics
                metrics = calculate_portfolio_metrics(portfolio)
                
                if not metrics:
                    logger.warning(f"Could not calculate metrics for user {chat_id}")
                    continue
                
                # Get market news summary
                symbols = list(portfolio.keys())
                news_summary = perplexity.get_crypto_news_summary(symbols)
                
                # Send daily insight notification
                success = notification_service.send_daily_insight(
                    chat_id=chat_id,
                    username=username,
                    total_value=metrics["total_value"],
                    change_24h=metrics["change_24h"],
                    change_24h_pct=metrics["change_24h_pct"],
                    best_performer=metrics["best_performer"],
                    best_performer_pct=metrics["best_performer_pct"],
                    news_summary=news_summary,
                )
                
                if success:
                    insights_sent += 1
                    logger.info(f"Sent daily insight to user {chat_id}")
            
            except Exception as e:
                logger.error(f"Error processing daily insight for user {user_id}: {e}")
                errors += 1
        
        result = {
            "status": "completed",
            "users_processed": users_processed,
            "insights_sent": insights_sent,
            "errors": errors,
        }
        
        logger.info(f"[TASK] Daily portfolio insights completed: {result}")
        return result
    
    except Exception as e:
        logger.error(f"[TASK] Daily portfolio insights failed: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "users_processed": users_processed,
            "insights_sent": insights_sent,
        }


def calculate_portfolio_metrics(portfolio: Dict) -> Dict | None:
    """Calculate portfolio performance metrics.
    
    Args:
        portfolio: User's portfolio dict
    
    Returns:
        Dict with total_value, change_24h, best_performer, etc. or None if error
    """
    try:
        total_value = 0.0
        total_cost = 0.0
        best_performer = None
        best_performer_pct = -999.0
        
        for symbol, position in portfolio.items():
            # Get current price
            current_price = get_crypto_price(symbol)
            if not current_price:
                logger.warning(f"Could not fetch price for {symbol}, skipping")
                continue
            
            buy_price = position.get("buy_price", 0)
            qty = position.get("qty", 0)
            
            if buy_price <= 0 or qty <= 0:
                continue
            
            # Calculate position value
            position_value = current_price * qty
            position_cost = buy_price * qty
            
            total_value += position_value
            total_cost += position_cost
            
            # Track best performer
            pnl_pct = ((current_price - buy_price) / buy_price) * 100
            if pnl_pct > best_performer_pct:
                best_performer = symbol
                best_performer_pct = pnl_pct
        
        if total_value == 0:
            return None
        
        # Calculate 24h change (approximation using current P&L)
        change_24h = total_value - total_cost
        change_24h_pct = ((total_value - total_cost) / total_cost) * 100 if total_cost > 0 else 0
        
        return {
            "total_value": total_value,
            "change_24h": change_24h,
            "change_24h_pct": change_24h_pct,
            "best_performer": best_performer or "N/A",
            "best_performer_pct": best_performer_pct if best_performer else 0,
        }
    
    except Exception as e:
        logger.error(f"Error calculating portfolio metrics: {e}")
        return None


@app.task(name="backend.tasks.daily_insights.test_daily_insight")
def test_daily_insight(chat_id: int) -> Dict:
    """Test task to manually send a daily insight (for testing).
    
    Args:
        chat_id: Telegram chat ID
    
    Returns:
        Dict with test result
    """
    logger.info(f"[TEST] Sending test daily insight to {chat_id}")
    
    notification_service = get_notification_service()
    
    # Send fake daily insight
    success = notification_service.send_daily_insight(
        chat_id=chat_id,
        username="TestUser",
        total_value=105000.0,
        change_24h=5000.0,
        change_24h_pct=5.0,
        best_performer="BTC",
        best_performer_pct=12.5,
        news_summary="BTC surged 12% on positive ETF news. ETH gained 8% following " "successful network upgrade.",
    )
    
    return {
        "status": "completed" if success else "failed",
        "chat_id": chat_id,
    }
