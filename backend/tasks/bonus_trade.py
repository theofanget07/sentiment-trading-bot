"""Feature 5 BONUS: Bonus Trade of the Day - Celery task.

Analyzes ALL supported cryptos daily and identifies the best trading opportunity:
- Scans 15 cryptos using Perplexity AI market analysis
- Evaluates momentum, sentiment, technicals, and news
- Sends top recommendation to all users at 8:00 AM CET
- Includes entry price, confidence score, and reasoning

Runs daily at 8:00 AM CET via Celery Beat (together with daily insights).
"""

import logging
from typing import Dict, List, Optional
from backend.celery_app import app
from backend.redis_storage import RedisStorage
from backend.crypto_prices import get_multiple_prices, SYMBOL_TO_ID, format_price
from backend.services.perplexity_client import get_perplexity_client
from backend.services.notification_service import get_notification_service

logger = logging.getLogger(__name__)

# All supported crypto symbols
SUPPORTED_CRYPTOS = list(SYMBOL_TO_ID.keys())


@app.task(name="backend.tasks.bonus_trade.send_bonus_trade_of_day")
def send_bonus_trade_of_day() -> Dict:
    """Find and send the best crypto trade opportunity of the day to all users.
    
    Returns:
        Dict with task execution summary
    """
    logger.info("[BONUS TRADE] Starting Bonus Trade of the Day analysis...")
    
    storage = RedisStorage()
    perplexity = get_perplexity_client()
    notification_service = get_notification_service()
    
    users_notified = 0
    errors = 0
    
    try:
        # Step 1: Get current prices for all cryptos
        logger.info(f"[BONUS TRADE] Fetching prices for {len(SUPPORTED_CRYPTOS)} cryptos...")
        prices = get_multiple_prices(SUPPORTED_CRYPTOS, force_refresh=True)
        
        valid_cryptos = [symbol for symbol, price in prices.items() if price is not None]
        logger.info(f"[BONUS TRADE] Got prices for {len(valid_cryptos)}/{len(SUPPORTED_CRYPTOS)} cryptos")
        
        if len(valid_cryptos) < 5:
            logger.error("[BONUS TRADE] Too few prices available, aborting")
            return {
                "status": "failed",
                "error": "Insufficient price data",
                "users_notified": 0,
            }
        
        # Step 2: Analyze each crypto and score opportunities
        logger.info("[BONUS TRADE] Analyzing trading opportunities with Perplexity AI...")
        opportunities = []
        
        for symbol in valid_cryptos:
            try:
                analysis = analyze_trade_opportunity(
                    symbol=symbol,
                    current_price=prices[symbol],
                    perplexity=perplexity,
                )
                
                if analysis:
                    opportunities.append(analysis)
                    logger.info(
                        f"[BONUS TRADE] {symbol}: Score={analysis['score']}, "
                        f"Action={analysis['action']}, Confidence={analysis['confidence']}%"
                    )
            
            except Exception as e:
                logger.error(f"[BONUS TRADE] Error analyzing {symbol}: {e}")
                continue
        
        if not opportunities:
            logger.error("[BONUS TRADE] No opportunities identified")
            return {
                "status": "failed",
                "error": "No opportunities found",
                "users_notified": 0,
            }
        
        # Step 3: Select the BEST opportunity (highest score)
        best_trade = max(opportunities, key=lambda x: x['score'])
        logger.info(
            f"[BONUS TRADE] 🏆 WINNER: {best_trade['symbol']} with score {best_trade['score']}"
        )
        
        # Step 4: Send to all users
        user_ids = storage.get_all_user_ids()
        logger.info(f"[BONUS TRADE] Sending to {len(user_ids)} users...")
        
        for user_id in user_ids:
            try:
                chat_id = int(user_id.replace("user:", ""))
                
                success = notification_service.send_bonus_trade(
                    chat_id=chat_id,
                    symbol=best_trade['symbol'],
                    action=best_trade['action'],
                    entry_price=best_trade['entry_price'],
                    target_price=best_trade.get('target_price'),
                    stop_loss=best_trade.get('stop_loss'),
                    reasoning=best_trade['reasoning'],
                    confidence=best_trade['confidence'],
                    risk_level=best_trade['risk_level'],
                )
                
                if success:
                    users_notified += 1
            
            except Exception as e:
                logger.error(f"[BONUS TRADE] Error sending to user {user_id}: {e}")
                errors += 1
        
        result = {
            "status": "completed",
            "bonus_trade": {
                "symbol": best_trade['symbol'],
                "action": best_trade['action'],
                "score": best_trade['score'],
                "confidence": best_trade['confidence'],
            },
            "users_notified": users_notified,
            "errors": errors,
        }
        
        logger.info(f"[BONUS TRADE] Task completed: {result}")
        return result
    
    except Exception as e:
        logger.error(f"[BONUS TRADE] Task failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "status": "failed",
            "error": str(e),
            "users_notified": users_notified,
        }


def analyze_trade_opportunity(
    symbol: str,
    current_price: float,
    perplexity,
) -> Optional[Dict]:
    """Analyze a single crypto for trading opportunity using Perplexity AI.
    
    Args:
        symbol: Crypto symbol (e.g., 'BTC')
        current_price: Current USD price
        perplexity: Perplexity client instance
    
    Returns:
        Dict with analysis or None if error
    """
    try:
        # Build AI prompt for comprehensive analysis
        prompt = f"""
Analyze {symbol} as a potential "Trade of the Day" opportunity:

Current Price: ${current_price:,.2f}

Provide a comprehensive analysis covering:

1. **Trading Recommendation**: BUY/SELL/HOLD
2. **Confidence Score**: 0-100 (how confident in this trade)
3. **Entry Strategy**: Optimal entry price range
4. **Price Targets**: Take-profit levels
5. **Stop Loss**: Risk management level
6. **Key Catalysts**: Top 3 reasons for this opportunity
7. **Risk Level**: LOW/MEDIUM/HIGH
8. **Time Horizon**: SHORT (1-3 days), MEDIUM (1-2 weeks), LONG (1+ month)

Focus on:
- Recent news and developments (last 24-48 hours)
- Technical momentum and key levels
- Market sentiment shifts
- Volume and liquidity analysis

Be specific and actionable for retail traders.
"""
        
        import requests
        response = requests.post(
            f"{perplexity.base_url}/chat/completions",
            headers=perplexity.headers,
            json={
                "model": "sonar",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a professional crypto trading analyst specializing in identifying high-conviction trade setups."
                    },
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=45,
        )
        response.raise_for_status()
        
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        
        # Parse AI response
        action = extract_action(content)
        confidence = extract_confidence(content)
        risk_level = extract_risk_level(content)
        
        # Only consider BUY opportunities for simplicity
        if action != "BUY" or confidence < 60:
            return None
        
        # Calculate opportunity score (0-100)
        score = calculate_opportunity_score(
            confidence=confidence,
            risk_level=risk_level,
            current_price=current_price,
        )
        
        return {
            "symbol": symbol,
            "action": action,
            "entry_price": current_price,
            "target_price": None,  # Can be extracted from content if needed
            "stop_loss": None,  # Can be extracted from content if needed
            "reasoning": content,
            "confidence": confidence,
            "risk_level": risk_level,
            "score": score,
            "raw_analysis": content,
        }
    
    except Exception as e:
        logger.error(f"Error analyzing {symbol}: {e}")
        return None


def extract_action(content: str) -> str:
    """Extract trading action (BUY/SELL/HOLD) from AI response."""
    content_upper = content.upper()
    
    if "BUY" in content_upper:
        return "BUY"
    elif "SELL" in content_upper:
        return "SELL"
    else:
        return "HOLD"


def extract_confidence(content: str) -> int:
    """Extract confidence score from AI response."""
    # Look for patterns like "Confidence: 75" or "75%"
    import re
    
    # Try "Confidence: XX" or "Confidence Score: XX"
    match = re.search(r'[Cc]onfidence[^\d]*?(\d{1,3})', content)
    if match:
        try:
            confidence = int(match.group(1))
            if 0 <= confidence <= 100:
                return confidence
        except:
            pass
    
    # Default medium confidence
    return 70


def extract_risk_level(content: str) -> str:
    """Extract risk level from AI response."""
    content_upper = content.upper()
    
    if "LOW" in content_upper and "RISK" in content_upper:
        return "LOW"
    elif "HIGH" in content_upper and "RISK" in content_upper:
        return "HIGH"
    else:
        return "MEDIUM"


def calculate_opportunity_score(
    confidence: int,
    risk_level: str,
    current_price: float,
) -> float:
    """Calculate overall opportunity score (0-100) for ranking.
    
    Args:
        confidence: AI confidence (0-100)
        risk_level: LOW/MEDIUM/HIGH
        current_price: Current price (used for tie-breaking)
    
    Returns:
        Score from 0-100
    """
    # Base score from confidence
    score = confidence
    
    # Adjust for risk (prefer lower risk)
    risk_multipliers = {
        "LOW": 1.1,
        "MEDIUM": 1.0,
        "HIGH": 0.9,
    }
    score *= risk_multipliers.get(risk_level, 1.0)
    
    # Cap at 100
    return min(score, 100.0)


@app.task(name="backend.tasks.bonus_trade.test_bonus_trade")
def test_bonus_trade(chat_id: int) -> Dict:
    """Test task to manually send a bonus trade (for testing).
    
    Args:
        chat_id: Telegram chat ID
    
    Returns:
        Dict with test result
    """
    logger.info(f"[TEST] Generating test Bonus Trade for chat {chat_id}")
    
    notification_service = get_notification_service()
    
    # Send fake bonus trade
    success = notification_service.send_bonus_trade(
        chat_id=chat_id,
        symbol="BTC",
        action="BUY",
        entry_price=95000.0,
        target_price=105000.0,
        stop_loss=92000.0,
        reasoning=(
            "**Bitcoin is showing strong bullish momentum:**\n\n"
            "• ETF inflows hitting all-time highs\n"
            "• Breaking through key resistance at $94,500\n"
            "• Positive funding rates indicating market confidence\n\n"
            "**Technical Setup**: Clean breakout with volume confirmation. "
            "RSI shows room to run before overbought."
        ),
        confidence=85,
        risk_level="MEDIUM",
    )
    
    return {
        "status": "completed" if success else "failed",
        "chat_id": chat_id,
        "symbol": "BTC",
    }
