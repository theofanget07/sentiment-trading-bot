#!/usr/bin/env python3
"""
Feature 4: AI-Powered Trading Recommendations Handler
Handles /recommend command for personalized trading advice.
"""

import logging
import re
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


def clean_perplexity_citations(text: str) -> str:
    """
    Remove citation numbers like [1], [2], [1][2], etc. from Perplexity AI response.
    Also cleans up extra spaces and improves formatting.
    """
    # Remove citations like [1], [2], [1][2][3], etc.
    cleaned = re.sub(r'\[\d+\]', '', text)
    
    # Remove multiple consecutive spaces
    cleaned = re.sub(r' +', ' ', cleaned)
    
    # Clean up spaces before punctuation
    cleaned = re.sub(r' +([.,;:!?])', r'\1', cleaned)
    
    # Remove trailing spaces from lines
    cleaned = '\n'.join(line.rstrip() for line in cleaned.split('\n'))
    
    return cleaned.strip()


def format_ai_analysis(reasoning: str) -> str:
    """
    Format AI reasoning for Telegram with proper markdown.
    Telegram only supports: **bold**, _italic_, `code`, [links](url)
    Does NOT support: # headers, ## subheaders
    """
    cleaned = clean_perplexity_citations(reasoning)
    
    # Remove markdown headers (# and ##) and replace with bold
    cleaned = re.sub(r'^#{1,6}\s+(.+)$', r'**\1**', cleaned, flags=re.MULTILINE)
    
    # Split into paragraphs
    paragraphs = [p.strip() for p in cleaned.split('\n\n') if p.strip()]
    
    formatted = []
    for para in paragraphs:
        # Bold section labels (text before colon)
        if ':' in para and not para.startswith('http'):
            # Check if it looks like a section header
            parts = para.split(':', 1)
            if len(parts[0]) < 60 and '\n' not in parts[0]:
                # Make the label bold
                formatted.append(f"**{parts[0].strip()}:**{parts[1]}")
                continue
        
        formatted.append(para)
    
    return '\n\n'.join(formatted)


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
            "• `/recommend` - Analyze all positions\n"
            "• `/recommend BTC` - Analyze Bitcoin only",
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
        
        # Send recommendations with clean formatting
        for rec in all_recommendations:
            emoji_map = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}
            rec_emoji = emoji_map.get(rec["recommendation"], "⚪")
            
            # P&L visual indicators
            pnl_emoji = "🟢" if rec["pnl_percent"] > 0 else ("🔴" if rec["pnl_percent"] < 0 else "⚪")
            pnl_label = "PROFIT" if rec["pnl_percent"] > 0 else ("LOSS" if rec["pnl_percent"] < 0 else "BREAK-EVEN")
            
            # Format AI analysis (removes citations and markdown headers)
            formatted_reasoning = format_ai_analysis(rec["reasoning"])
            
            # Build clean, readable response
            response = f"{rec_emoji} **AI RECOMMENDATION \u2014 {rec['symbol']}**\n\n"
            
            # Position summary
            response += f"💼 **YOUR POSITION**\n\n"
            response += f"Quantity: `{rec['qty']:.8g}` {rec['symbol']}\n"
            response += f"Entry: `{format_price(rec['avg_price'])}` → Current: `{format_price(rec['current_price'])}`\n"
            response += f"{pnl_emoji} **{pnl_label}:** `{rec['pnl_usd']:+,.2f} USD` _({rec['pnl_percent']:+.2f}%)_\n\n"
            
            # Recommendation
            response += f"🎯 **RECOMMENDATION: {rec['recommendation']}**\n"
            response += f"🔒 _Confidence: {rec['confidence']}%_\n\n"
            
            response += f"────────\n\n"
            
            # AI Analysis
            response += f"🤖 **AI ANALYSIS**\n\n{formatted_reasoning}\n\n"
            
            response += f"────────\n\n"
            
            # Disclaimer
            response += f"⚠️ **DISCLAIMER**\n\n"
            response += f"_This is **informational only**, NOT financial advice._\n\n"
            response += f"🛑 **Risks:** High volatility, possible total loss\n"
            response += f"📊 Past performance ≠ future results\n"
            response += f"🔍 **Always DYOR** \u2014 Consult a licensed advisor\n\n"
            response += f"_Powered by [Perplexity AI](https://www.perplexity.ai) | `/summary` for full portfolio_"
            
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
