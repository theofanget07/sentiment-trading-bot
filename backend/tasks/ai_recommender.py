"""Feature 4: AI Recommendations Engine - Celery task.

Generates daily AI-powered trading recommendations for each user's portfolio:
- BUY/SELL/HOLD recommendations
- Based on Perplexity AI market analysis
- Considers position performance and market conditions

Runs daily at 8:00 AM CET via Celery Beat.
"""

import logging
from typing import Dict, List
from backend.celery_app import app
from backend.redis_storage import RedisStorage
from backend.crypto_prices import get_crypto_price
from backend.services.perplexity_client import get_perplexity_client
from backend.services.notification_service import get_notification_service

logger = logging.getLogger(__name__)

# Minimum confidence threshold to send recommendation
MIN_CONFIDENCE_THRESHOLD = 60


@app.task(name="backend.tasks.ai_recommender.generate_daily_recommendations")
def generate_daily_recommendations() -> Dict:
    """Generate AI recommendations for all users with portfolios.
    
    Returns:
        Dict with task execution summary
    """
    logger.info("[TASK] Starting AI recommendations generation...")
    
    storage = RedisStorage()
    perplexity = get_perplexity_client()
    notification_service = get_notification_service()
    
    recommendations_sent = 0
    users_processed = 0
    errors = 0
    
    try:
        # Get all user IDs
        user_ids = storage.get_all_user_ids()
        logger.info(f"Processing recommendations for {len(user_ids)} users")
        
        for user_id in user_ids:
            try:
                users_processed += 1
                chat_id = int(user_id.replace("user:", ""))
                
                # Get user's portfolio
                portfolio = storage.get_portfolio(chat_id)
                if not portfolio:
                    logger.debug(f"User {chat_id} has no portfolio, skipping")
                    continue
                
                # Generate recommendations for each position
                for symbol, position in portfolio.items():
                    recommendation = generate_position_recommendation(
                        symbol=symbol,
                        position=position,
                        perplexity=perplexity,
                    )
                    
                    if recommendation and recommendation["confidence"] >= MIN_CONFIDENCE_THRESHOLD:
                        # Send recommendation
                        success = notification_service.send_ai_recommendation(
                            chat_id=chat_id,
                            crypto_symbol=symbol,
                            recommendation=recommendation["recommendation"],
                            reasoning=recommendation["reasoning"],
                            confidence=recommendation["confidence"],
                        )
                        
                        if success:
                            recommendations_sent += 1
                            logger.info(
                                f"Sent {recommendation['recommendation']} "
                                f"recommendation for {symbol} to user {chat_id}"
                            )
            
            except Exception as e:
                logger.error(f"Error processing recommendations for user {user_id}: {e}")
                errors += 1
        
        result = {
            "status": "completed",
            "users_processed": users_processed,
            "recommendations_sent": recommendations_sent,
            "errors": errors,
        }
        
        logger.info(f"[TASK] AI recommendations generation completed: {result}")
        return result
    
    except Exception as e:
        logger.error(f"[TASK] AI recommendations generation failed: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "users_processed": users_processed,
            "recommendations_sent": recommendations_sent,
        }


def generate_position_recommendation(
    symbol: str,
    position: Dict,
    perplexity,
) -> Dict | None:
    """Generate AI recommendation for a single position.
    
    Args:
        symbol: Crypto symbol (e.g., 'BTC')
        position: Position data dict
        perplexity: Perplexity client instance
    
    Returns:
        Dict with recommendation, reasoning, confidence or None if error
    """
    try:
        # Get current price
        current_price = get_crypto_price(symbol)
        if not current_price:
            logger.warning(f"Could not fetch price for {symbol}")
            return None
        
        # Calculate position metrics
        buy_price = position.get("buy_price", 0)
        qty = position.get("qty", 0)
        
        if buy_price <= 0 or qty <= 0:
            return None
        
        pnl_pct = ((current_price - buy_price) / buy_price) * 100
        
        # Prepare position data for AI
        position_data = {
            "qty": qty,
            "avg_price": buy_price,
            "current_price": current_price,
            "pnl_pct": pnl_pct,
        }
        
        # Get AI recommendation from Perplexity
        recommendation = perplexity.get_market_recommendation(
            crypto_symbol=symbol,
            position_data=position_data,
        )
        
        logger.info(
            f"AI recommendation for {symbol}: {recommendation['recommendation']} "
            f"(confidence: {recommendation['confidence']})"
        )
        
        return recommendation
    
    except Exception as e:
        logger.error(f"Error generating recommendation for {symbol}: {e}")
        return None


@app.task(name="backend.tasks.ai_recommender.test_recommendation")
def test_recommendation(chat_id: int, symbol: str = "BTC") -> Dict:
    """Test task to manually generate a recommendation (for testing).
    
    Args:
        chat_id: Telegram chat ID
        symbol: Crypto symbol to test
    
    Returns:
        Dict with test result
    """
    logger.info(f"[TEST] Generating test recommendation for {symbol} to {chat_id}")
    
    perplexity = get_perplexity_client()
    notification_service = get_notification_service()
    
    # Fake position data
    position_data = {
        "qty": 1.0,
        "avg_price": 85000.0,
        "current_price": 95000.0,
        "pnl_pct": 11.76,
    }
    
    # Get AI recommendation
    recommendation = perplexity.get_market_recommendation(
        crypto_symbol=symbol,
        position_data=position_data,
    )
    
    # Send notification
    success = notification_service.send_ai_recommendation(
        chat_id=chat_id,
        crypto_symbol=symbol,
        recommendation=recommendation["recommendation"],
        reasoning=recommendation["reasoning"],
        confidence=recommendation["confidence"],
    )
    
    return {
        "status": "completed" if success else "failed",
        "chat_id": chat_id,
        "symbol": symbol,
        "recommendation": recommendation["recommendation"],
    }
