#!/usr/bin/env python3
"""
Feature 4: AI-Powered Trading Recommendations Handler
Handles /recommend command for personalized trading advice.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def recommend_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    DB_AVAILABLE,
    portfolio_manager,
    is_symbol_supported,
    format_price
):
    """Get AI-powered trading recommendations for portfolio positions."""
    if not DB_AVAILABLE:
        await update.message.reply_text(
            "⚠️ Database offline. Cannot generate recommendations.", 
            parse_mode='Markdown'
        )
        return
    
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or "User"
    
    # Parse optional argument (specific crypto)
    specific_crypto = None
    if len(context.args) == 1:
        specific_crypto = context.args[0].upper()
        if not is_symbol_supported(specific_crypto):
            await update.message.reply_text(
                f"❌ **{specific_crypto} not supported**\n\n"
                "Supported cryptos: BTC, ETH, SOL, BNB, XRP, ADA, AVAX, DOT, MATIC, LINK, UNI, ATOM, LTC, BCH, XLM",
                parse_mode='Markdown'
            )
            return
    elif len(context.args) > 1:
        await update.message.reply_text(
            "⚠️ **Usage:** `/recommend [SYMBOL]`\n\n"
            "**Examples:**\n"
            "`/recommend` - Analyze all positions\n"
            "`/recommend BTC` - Analyze Bitcoin only",
            parse_mode='Markdown'
        )
        return
    
    logger.info(f"🤖 /recommend called by user {user_id} (@{username}), crypto: {specific_crypto or 'ALL'}")
    
    try:
        portfolio = portfolio_manager.get_portfolio_with_prices(user_id, username)
        
        if not portfolio["positions"]:
            await update.message.reply_text(
                "💼 **Portfolio Empty**\n\n"
                "No positions to analyze. Add a position first with:\n"
                "`/add BTC 1 45000`",
                parse_mode='Markdown'
            )
            return
        
        if specific_crypto:
            if specific_crypto not in portfolio["positions"]:
                await update.message.reply_text(
                    f"⚠️ **No {specific_crypto} Position**\n\n"
                    f"You don't hold {specific_crypto}. Add it first with:\n"
                    f"`/add {specific_crypto} <qty> <price>`",
                    parse_mode='Markdown'
                )
                return
            positions_to_analyze = {specific_crypto: portfolio["positions"][specific_crypto]}
        else:
            positions_to_analyze = portfolio["positions"]
        
        analyzing_msg = await update.message.reply_text(
            f"🤖 **Analyzing {len(positions_to_analyze)} position(s)...**\n\n"
            f"_This may take 3-10 seconds_",
            parse_mode='Markdown'
        )
        
        try:
            from backend.services.perplexity_client import get_perplexity_client
            perplexity = get_perplexity_client()
        except Exception as e:
            logger.error(f"❌ Failed to load Perplexity client: {e}")
            await analyzing_msg.edit_text(
                "❌ **AI Service Unavailable**\n\n"
                "Perplexity API is not configured or unavailable.\n"
                "Please try again later.",
                parse_mode='Markdown'
            )
            return
        
        all_recommendations = []
        
        for symbol, pos in positions_to_analyze.items():
            try:
                qty = pos["quantity"]
                avg_price = pos["avg_price"]
                current_price = pos["current_price"]
                pnl_usd = pos["pnl_usd"]
                pnl_percent = pos["pnl_percent"]
                
                if not current_price or current_price == 0:
                    logger.warning(f"Skipping {symbol}: no valid current price")
                    continue
                
                position_data = {
                    "qty": qty,
                    "avg_price": avg_price,
                    "current_price": current_price,
                    "pnl_pct": pnl_percent,
                }
                
                recommendation = perplexity.get_market_recommendation(
                    crypto_symbol=symbol,
                    position_data=position_data,
                )
                
                all_recommendations.append({
                    "symbol": symbol,
                    "qty": qty,
                    "avg_price": avg_price,
                    "current_price": current_price,
                    "pnl_usd": pnl_usd,
                    "pnl_percent": pnl_percent,
                    "recommendation": recommendation["recommendation"],
                    "reasoning": recommendation["reasoning"],
                    "confidence": recommendation["confidence"],
                })
            
            except Exception as e:
                logger.error(f"❌ Error generating recommendation for {symbol}: {e}")
        
        await analyzing_msg.delete()
        
        if not all_recommendations:
            await update.message.reply_text(
                "❌ **Analysis Failed**\n\n"
                "Could not generate recommendations. Please try again.",
                parse_mode='Markdown'
            )
            return
        
        for rec in all_recommendations:
            emoji_map = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}
            rec_emoji = emoji_map.get(rec["recommendation"], "⚪")
            
            response = f"{rec_emoji} **AI RECOMMENDATION - {rec['symbol']}**\n"
            response += f"\n━━━━━━━━━━━━━━━━━━\n"
            response += f"💼 **YOUR POSITION**\n"
            response += f"━━━━━━━━━━━━━━━━━━\n\n"
            response += f"• Quantity: `{rec['qty']:.8g}`\n"
            response += f"• Entry Price: `{format_price(rec['avg_price'])}`\n"
            response += f"• Current Price: `{format_price(rec['current_price'])}`\n"
            response += f"• P&L: `{rec['pnl_usd']:+,.2f} USD ({rec['pnl_percent']:+.2f}%)`\n"
            response += f"\n━━━━━━━━━━━━━━━━━━\n"
            response += f"🎯 **RECOMMENDATION: {rec['recommendation']}**\n"
            response += f"🔒 Confidence: **{rec['confidence']}%**\n"
            response += f"━━━━━━━━━━━━━━━━━━\n\n"
            response += f"📊 **AI Analysis:**\n\n{rec['reasoning']}\n"
            response += f"\n⚠️ **DISCLAIMER**\n"
            response += f"This AI recommendation is for **informational purposes ONLY** and does **NOT** constitute financial advice.\n\n"
            response += f"• Cryptocurrency trading involves **substantial risk of loss**\n"
            response += f"• You may **lose your entire investment**\n"
            response += f"• Always conduct your own research (DYOR)\n"
            response += f"• Consult a licensed financial advisor\n\n"
            response += f"_Powered by [Perplexity AI](https://www.perplexity.ai)_\n"
            response += f"_Use `/summary` for portfolio overview_"
            
            await update.message.reply_text(response, parse_mode='Markdown', disable_web_page_preview=True)
        
        logger.info(f"✅ /recommend sent {len(all_recommendations)} recommendation(s) to {user_id}")
    
    except Exception as e:
        logger.error(f"❌ /recommend error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        await update.message.reply_text(
            "❌ **Error Generating Recommendations**\n\n"
            "Something went wrong. Please try again.",
            parse_mode='Markdown'
        )
