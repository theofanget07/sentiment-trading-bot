"""Morning Briefing - Comprehensive daily crypto digest.

Combines Daily Insights + Bonus Trade into ONE message sent at 8:00 AM CET.

Includes:
1. Portfolio Summary (total value, 24h change, top performer)
2. AI Position Advice (personalized BUY/HOLD/SELL for each position)
3. Bonus Trade of the Day (best opportunity from all supported cryptos)
4. Market News Summary

Replaces:
- Feature 4: AI Recommendations (now manual via /recommend)
- Feature 5: Daily Insights
- Feature 5 Bonus: Bonus Trade of the Day

Runs daily at 8:00 AM CET via Celery Beat.

Last updated: 2026-02-08 18:10 CET
"""

import logging
from typing import Dict, List, Optional
from backend.celery_app import app
from backend.redis_storage import RedisStorage
from backend.crypto_prices import get_crypto_price, get_multiple_prices, SYMBOL_TO_ID, format_price
from backend.services.perplexity_client import get_perplexity_client
from backend.services.notification_service import get_notification_service
import time

logger = logging.getLogger(__name__)

# All supported crypto symbols for Bonus Trade analysis
SUPPORTED_CRYPTOS = list(SYMBOL_TO_ID.keys())


@app.task(name="backend.tasks.morning_briefing.send_morning_briefing")
def send_morning_briefing() -> Dict:
    """Send comprehensive morning briefing to all users.
    
    Returns:
        Dict with task execution summary
    """
    logger.info("="*70)
    logger.info("[MORNING BRIEFING] 🌅 Starting Morning Briefing task...")
    logger.info(f"[MORNING BRIEFING] Task started at: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    logger.info("="*70)
    
    storage = RedisStorage()
    perplexity = get_perplexity_client()
    notification_service = get_notification_service()
    
    briefings_sent = 0
    users_processed = 0
    errors = 0
    skipped_no_portfolio = 0
    skipped_errors = 0
    
    # Step 1: Find Bonus Trade of the Day (same for ALL users)
    logger.info("[MORNING BRIEFING] 📊 Step 1/3: Analyzing Bonus Trade of the Day...")
    bonus_trade = find_bonus_trade_of_day(perplexity)
    
    if not bonus_trade:
        logger.warning("[MORNING BRIEFING] ⚠️ No Bonus Trade found, using fallback")
        # Use fallback instead of aborting
        bonus_trade = {
            "symbol": "BTC",
            "action": "HOLD",
            "entry_price": 0,
            "reasoning": "Markets are consolidating. Wait for clearer signals before entering new positions.",
            "confidence": 50,
            "risk_level": "MEDIUM",
            "score": 50,
        }
    
    logger.info(
        f"[MORNING BRIEFING] 🏆 Bonus Trade: {bonus_trade['symbol']} - "
        f"{bonus_trade['action']} (Confidence: {bonus_trade['confidence']}%)"
    )
    
    # Step 2: Send personalized briefing to each user
    logger.info("[MORNING BRIEFING] 👥 Step 2/3: Processing users...")
    try:
        user_ids = storage.get_all_user_ids()
        logger.info(f"[MORNING BRIEFING] Found {len(user_ids)} users to process")
        
        if not user_ids:
            logger.warning("[MORNING BRIEFING] No users found in database")
            return {
                "status": "completed",
                "users_processed": 0,
                "briefings_sent": 0,
                "note": "No users in database",
            }
        
        for user_id in user_ids:
            try:
                users_processed += 1
                chat_id = int(user_id.replace("user:", ""))
                
                logger.info(f"[MORNING BRIEFING] ➡️ Processing user {chat_id} ({users_processed}/{len(user_ids)})...")
                
                # Get user's portfolio
                portfolio = storage.get_portfolio(chat_id)
                if not portfolio or len(portfolio) == 0:
                    logger.info(f"[MORNING BRIEFING] User {chat_id} has no portfolio, skipping")
                    skipped_no_portfolio += 1
                    continue
                
                logger.info(f"[MORNING BRIEFING] User {chat_id} has {len(portfolio)} positions: {list(portfolio.keys())}")
                
                # Get username
                username = storage.get_user_data(chat_id, "username") or "User"
                
                # Calculate portfolio metrics
                logger.info(f"[MORNING BRIEFING] Calculating metrics for user {chat_id}...")
                metrics = calculate_portfolio_metrics(portfolio)
                
                if not metrics:
                    logger.warning(
                        f"[MORNING BRIEFING] ⚠️ Could not calculate metrics for user {chat_id} (API issues), "
                        "will send briefing with limited data"
                    )
                    # Send briefing anyway with degraded mode
                    metrics = {
                        "total_value": 0,
                        "change_24h": 0,
                        "change_24h_pct": 0,
                        "best_performer": "N/A",
                        "best_performer_pct": 0,
                    }
                else:
                    logger.info(
                        f"[MORNING BRIEFING] ✅ User {chat_id} metrics: "
                        f"Value=${metrics['total_value']:.2f}, Change={metrics['change_24h_pct']:+.2f}%"
                    )
                
                # Get market news summary
                logger.info(f"[MORNING BRIEFING] Fetching news for user {chat_id}...")
                symbols = list(portfolio.keys())
                try:
                    news_summary = perplexity.get_crypto_news_summary(symbols)
                    logger.info(f"[MORNING BRIEFING] ✅ News fetched ({len(news_summary)} chars)")
                except Exception as e:
                    logger.error(f"[MORNING BRIEFING] News fetch failed for user {chat_id}: {e}")
                    news_summary = "Market news unavailable at this time. Check CoinGecko or CoinMarketCap for latest updates."
                
                # Generate AI advice for each position
                logger.info(f"[MORNING BRIEFING] Generating AI advice for user {chat_id}...")
                try:
                    position_advice = generate_position_advice(portfolio, perplexity)
                    logger.info(f"[MORNING BRIEFING] ✅ Generated {len(position_advice)} advice items")
                except Exception as e:
                    logger.error(f"[MORNING BRIEFING] Advice generation failed for user {chat_id}: {e}")
                    position_advice = []
                
                # Send comprehensive morning briefing
                logger.info(f"[MORNING BRIEFING] 📨 Sending briefing to user {chat_id}...")
                success = notification_service.send_morning_briefing(
                    chat_id=chat_id,
                    username=username,
                    total_value=metrics["total_value"],
                    change_24h=metrics["change_24h"],
                    change_24h_pct=metrics["change_24h_pct"],
                    best_performer=metrics["best_performer"],
                    best_performer_pct=metrics["best_performer_pct"],
                    position_advice=position_advice,
                    bonus_trade=bonus_trade,
                    news_summary=news_summary,
                )
                
                if success:
                    briefings_sent += 1
                    logger.info(f"[MORNING BRIEFING] ✅ Successfully sent to user {chat_id}")
                else:
                    logger.error(f"[MORNING BRIEFING] ❌ Failed to send to user {chat_id}")
                    errors += 1
            
            except Exception as e:
                logger.error(
                    f"[MORNING BRIEFING] ❌ Error processing user {user_id}: {e}",
                    exc_info=True
                )
                errors += 1
        
        result = {
            "status": "completed",
            "users_processed": users_processed,
            "briefings_sent": briefings_sent,
            "skipped_no_portfolio": skipped_no_portfolio,
            "skipped_errors": skipped_errors,
            "errors": errors,
            "bonus_trade": {
                "symbol": bonus_trade["symbol"],
                "action": bonus_trade["action"],
                "confidence": bonus_trade["confidence"],
            },
        }
        
        logger.info("="*70)
        logger.info(
            f"[MORNING BRIEFING] ✅ Task completed: "
            f"{briefings_sent}/{users_processed} sent, "
            f"{skipped_no_portfolio} no portfolio, "
            f"{errors} errors"
        )
        logger.info("="*70)
        return result
    
    except Exception as e:
        logger.error("="*70)
        logger.error(f"[MORNING BRIEFING] ❌ Task failed: {e}", exc_info=True)
        logger.error("="*70)
        return {
            "status": "failed",
            "error": str(e),
            "users_processed": users_processed,
            "briefings_sent": briefings_sent,
        }


def find_bonus_trade_of_day(perplexity) -> Optional[Dict]:
    """Find the best crypto trading opportunity of the day.
    
    Analyzes all supported cryptos and selects the highest-conviction BUY signal.
    
    Args:
        perplexity: Perplexity client instance
    
    Returns:
        Dict with symbol, action, entry_price, reasoning, confidence, risk_level
        or None if no opportunity found
    """
    try:
        logger.info(f"[BONUS TRADE] 🔍 Fetching prices for {len(SUPPORTED_CRYPTOS)} cryptos...")
        prices = get_multiple_prices(SUPPORTED_CRYPTOS, force_refresh=False)  # Use cache!
        
        valid_cryptos = [symbol for symbol, price in prices.items() if price is not None and price > 0]
        logger.info(f"[BONUS TRADE] ✅ Got prices for {len(valid_cryptos)}/{len(SUPPORTED_CRYPTOS)} cryptos")
        
        if len(valid_cryptos) < 3:
            logger.error(f"[BONUS TRADE] ❌ Too few prices available ({len(valid_cryptos)}), aborting")
            return None
        
        # Limit to top 5 by market cap for faster analysis
        top_cryptos = ["BTC", "ETH", "SOL", "BNB", "XRP"]
        analysis_cryptos = [c for c in top_cryptos if c in valid_cryptos]
        
        if not analysis_cryptos:
            analysis_cryptos = valid_cryptos[:5]  # Fallback to first 5 available
        
        logger.info(f"[BONUS TRADE] 🔍 Analyzing {len(analysis_cryptos)} cryptos: {analysis_cryptos}")
        
        # Analyze opportunities
        logger.info("[BONUS TRADE] 🤖 Analyzing trading opportunities with Perplexity AI...")
        opportunities = []
        
        for symbol in analysis_cryptos:
            try:
                analysis = analyze_trade_opportunity(
                    symbol=symbol,
                    current_price=prices[symbol],
                    perplexity=perplexity,
                )
                
                if analysis:
                    opportunities.append(analysis)
                    logger.info(
                        f"[BONUS TRADE] {symbol}: Score={analysis['score']:.0f}, "
                        f"Confidence={analysis['confidence']}%, Action={analysis['action']}"
                    )
                else:
                    logger.info(f"[BONUS TRADE] {symbol}: No strong signal")
            
            except Exception as e:
                logger.error(f"[BONUS TRADE] ❌ Error analyzing {symbol}: {e}")
                continue
        
        if not opportunities:
            logger.error("[BONUS TRADE] ❌ No opportunities identified")
            return None
        
        # Select BEST opportunity (highest score)
        best_trade = max(opportunities, key=lambda x: x['score'])
        logger.info(
            f"[BONUS TRADE] 🏆 WINNER: {best_trade['symbol']} with score {best_trade['score']:.0f}"
        )
        
        return best_trade
    
    except Exception as e:
        logger.error(f"[BONUS TRADE] ❌ Failed to find bonus trade: {e}", exc_info=True)
        return None


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
        Dict with analysis or None if not a BUY opportunity
    """
    try:
        prompt = f"""
Analyze {symbol} as a potential "Trade of the Day" opportunity:

Current Price: ${current_price:,.2f}

Provide analysis covering:

1. **Trading Recommendation**: BUY/SELL/HOLD
2. **Confidence Score**: 0-100 (how confident in this trade)
3. **Entry Strategy**: Optimal entry price range
4. **Price Targets**: Take-profit levels (TP1, TP2, TP3)
5. **Stop Loss**: Risk management level
6. **Key Catalysts**: Top 3 reasons for this opportunity
7. **Risk Level**: LOW/MEDIUM/HIGH

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
        
        # Only consider BUY opportunities with >60% confidence
        if action != "BUY" or confidence < 60:
            return None
        
        # Calculate opportunity score
        score = calculate_opportunity_score(confidence, risk_level)
        
        return {
            "symbol": symbol,
            "action": action,
            "entry_price": current_price,
            "reasoning": content,
            "confidence": confidence,
            "risk_level": risk_level,
            "score": score,
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
    import re
    
    # Look for patterns like "Confidence: 75" or "75%"
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


def calculate_opportunity_score(confidence: int, risk_level: str) -> float:
    """Calculate overall opportunity score (0-100) for ranking.
    
    Args:
        confidence: AI confidence (0-100)
        risk_level: LOW/MEDIUM/HIGH
    
    Returns:
        Score from 0-100
    """
    score = confidence
    
    # Adjust for risk (prefer lower risk)
    risk_multipliers = {
        "LOW": 1.1,
        "MEDIUM": 1.0,
        "HIGH": 0.9,
    }
    score *= risk_multipliers.get(risk_level, 1.0)
    
    return min(score, 100.0)


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
        
        prices_fetched = 0
        prices_failed = 0
        
        logger.info(f"[METRICS] Fetching prices for {len(portfolio)} positions...")
        
        for symbol, position in portfolio.items():
            # Get current price with cache
            current_price = get_crypto_price(symbol, force_refresh=False)
            if not current_price or current_price <= 0:
                logger.warning(f"[METRICS] ⚠️ Could not fetch price for {symbol}, skipping position")
                prices_failed += 1
                continue
            
            prices_fetched += 1
            logger.debug(f"[METRICS] {symbol}: ${current_price:,.2f}")
            
            buy_price = position.get("buy_price", 0)
            qty = position.get("qty", 0)
            
            if buy_price <= 0 or qty <= 0:
                logger.warning(f"[METRICS] Invalid position data for {symbol}: buy_price={buy_price}, qty={qty}")
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
        
        logger.info(
            f"[METRICS] Prices: {prices_fetched} fetched, {prices_failed} failed out of {len(portfolio)} total"
        )
        
        # Allow partial success (at least 50% of prices)
        if prices_fetched == 0 or prices_fetched < len(portfolio) * 0.5:
            logger.warning(
                f"[METRICS] ❌ Too few prices available ({prices_fetched}/{len(portfolio)}), "
                "cannot calculate reliable metrics"
            )
            return None
        
        # Calculate 24h change (approximation using current P&L)
        change_24h = total_value - total_cost
        change_24h_pct = ((total_value - total_cost) / total_cost) * 100 if total_cost > 0 else 0
        
        logger.info(
            f"[METRICS] ✅ Portfolio: ${total_value:,.2f}, Change: {change_24h_pct:+.2f}%, "
            f"Best: {best_performer} ({best_performer_pct:+.2f}%)"
        )
        
        return {
            "total_value": total_value,
            "change_24h": change_24h,
            "change_24h_pct": change_24h_pct,
            "best_performer": best_performer or "N/A",
            "best_performer_pct": best_performer_pct if best_performer else 0,
        }
    
    except Exception as e:
        logger.error(f"[METRICS] ❌ Error calculating portfolio metrics: {e}", exc_info=True)
        return None


def generate_position_advice(portfolio: Dict, perplexity) -> List[Dict]:
    """Generate AI-powered advice for each portfolio position.
    
    Args:
        portfolio: User's portfolio dict
        perplexity: Perplexity client instance
    
    Returns:
        List of dicts with symbol, pnl_pct, current_price, and advice
    """
    advice_list = []
    
    try:
        logger.info(f"[ADVICE] Generating advice for {len(portfolio)} positions...")
        
        for symbol, position in portfolio.items():
            try:
                # Get current price
                current_price = get_crypto_price(symbol, force_refresh=False)
                if not current_price or current_price <= 0:
                    logger.warning(f"[ADVICE] Skipping advice for {symbol}: price unavailable")
                    continue
                
                buy_price = position.get("buy_price", 0)
                qty = position.get("qty", 0)
                
                if buy_price <= 0 or qty <= 0:
                    logger.warning(f"[ADVICE] Skipping advice for {symbol}: invalid position data")
                    continue
                
                # Calculate P&L
                pnl_pct = ((current_price - buy_price) / buy_price) * 100
                
                # Generate concise advice using Perplexity
                advice_text = get_quick_position_advice(
                    perplexity, symbol, current_price, buy_price, pnl_pct
                )
                
                advice_list.append({
                    "symbol": symbol,
                    "pnl_pct": pnl_pct,
                    "current_price": current_price,
                    "buy_price": buy_price,
                    "advice": advice_text,
                })
                
                logger.info(f"[ADVICE] ✅ {symbol}: {advice_text[:50]}...")
            
            except Exception as e:
                logger.error(f"[ADVICE] ❌ Error generating advice for {symbol}: {e}")
                continue
        
        logger.info(f"[ADVICE] ✅ Generated {len(advice_list)}/{len(portfolio)} advice items")
        return advice_list
    
    except Exception as e:
        logger.error(f"[ADVICE] ❌ Error generating position advice: {e}", exc_info=True)
        return []


def get_quick_position_advice(
    perplexity, symbol: str, current_price: float, buy_price: float, pnl_pct: float
) -> str:
    """Get quick AI advice for a single position.
    
    Args:
        perplexity: Perplexity client
        symbol: Crypto symbol
        current_price: Current market price
        buy_price: User's buy price
        pnl_pct: P&L percentage
    
    Returns:
        Short advice string (1-2 sentences)
    """
    try:
        import requests
        import os
        
        prompt = f"""
Provide a brief 1-sentence trading advice for this {symbol} position:
- Buy Price: ${buy_price:,.2f}
- Current Price: ${current_price:,.2f}
- P&L: {pnl_pct:+.1f}%

Give ONE short actionable recommendation (HOLD/BUY MORE/TAKE PROFIT) based on current market conditions.
Format: "[ACTION]: [brief reason]."
Example: "HOLD: Strong support at $40k, target $50k."
""".strip()
        
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={
                "Authorization": f"Bearer {os.getenv('PERPLEXITY_API_KEY')}",
                "Content-Type": "application/json",
            },
            json={
                "model": "sonar",
                "messages": [
                    {"role": "system", "content": "You are a concise crypto trading advisor."},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=15,
        )
        response.raise_for_status()
        
        data = response.json()
        advice = data["choices"][0]["message"]["content"].strip()
        
        # Extract first sentence if multiple
        if "." in advice:
            advice = advice.split(".")[0] + "."
        
        # Limit to 120 chars for readability
        if len(advice) > 120:
            advice = advice[:117] + "..."
        
        return advice
    
    except Exception as e:
        logger.error(f"[ADVICE] Error getting quick advice for {symbol}: {e}")
        
        # Fallback to rule-based advice
        if pnl_pct > 20:
            return "TAKE PROFIT: Consider selling 30-50% to secure gains."
        elif pnl_pct > 10:
            return "HOLD: Strong position, monitor resistance levels."
        elif pnl_pct > 0:
            return "HOLD: In profit, wait for clearer trend."
        elif pnl_pct > -10:
            return "HOLD: Small drawdown, avoid panic selling."
        else:
            return "REVIEW: Consider stop-loss to limit further losses."
