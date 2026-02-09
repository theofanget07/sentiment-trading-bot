#!/usr/bin/env python3
"""
Telegram Bot with Webhook support for Railway deployment.
Uses FastAPI for native async support.
"""
import os
import logging
import json
from datetime import datetime
from io import BytesIO
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

import sys
sys.path.insert(0, os.path.dirname(__file__))

from sentiment_analyzer import analyze_sentiment

# Global DB Status
DB_AVAILABLE = False

# Fix: Use absolute import for Railway deployment
try:
    from backend.portfolio_manager import portfolio_manager
    from backend import redis_storage
except ImportError:
    # Fallback for local development
    from portfolio_manager import portfolio_manager
    import redis_storage

try:
    from backend.crypto_prices import format_price, get_crypto_price, is_symbol_supported
except ImportError:
    from crypto_prices import format_price, get_crypto_price, is_symbol_supported

try:
    from article_scraper import extract_article, extract_urls
except ImportError:
    def extract_article(url): return None
    def extract_urls(text): return []

# Feature 4: AI Recommendations handler
try:
    from backend.recommend_handler import recommend_command as recommend_handler_fn
except ImportError:
    from recommend_handler import recommend_command as recommend_handler_fn

# Stripe integration for Premium subscriptions
try:
    from backend.stripe_service import create_checkout_session, get_subscription_status, retrieve_subscription
    STRIPE_AVAILABLE = True
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("⚠️ Stripe service not available - Premium subscriptions disabled")
    STRIPE_AVAILABLE = False

# Stripe Webhook Router
try:
    from backend.routes.stripe_webhook import router as stripe_webhook_router
    STRIPE_WEBHOOK_AVAILABLE = True
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("⚠️ Stripe webhook router not available")
    STRIPE_WEBHOOK_AVAILABLE = False
    stripe_webhook_router = None

# Free/Premium Tier Management
try:
    from backend.tier_manager import tier_manager
    from backend.decorators import (
        premium_required,
        check_rate_limit,
        check_position_limit,
        check_alert_limit,
        check_recommendation_limit
    )
    TIER_SYSTEM_AVAILABLE = True
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("⚠️ Tier management not available")
    TIER_SYSTEM_AVAILABLE = False
    # Dummy decorators if tier system not available
    def premium_required(func): return func
    def check_rate_limit(func): return func
    def check_position_limit(func): return func
    def check_alert_limit(func): return func
    def check_recommendation_limit(func): return func

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
PORT = int(os.getenv('PORT', 8080))

app = FastAPI()
application = None

# Include Stripe Webhook Router
if STRIPE_WEBHOOK_AVAILABLE and stripe_webhook_router:
    app.include_router(stripe_webhook_router)
    logger.info("✅ Stripe webhook router registered at /webhook/stripe")
else:
    logger.warning("⚠️ Stripe webhook router NOT registered - payments won't be processed")

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    welcome_text = f"""👋 **Welcome {user.first_name}!**

🤖 **CryptoSentinel AI**
Your AI-powered crypto assistant

⚠️ **Disclaimer:** This bot provides informational alerts and AI analysis only. NOT financial advice. [More info](/help)

──────────────────
🎯 **MAIN COMMANDS**

📊 **Sentiment Analysis**
• `/analyze` - AI-powered market analysis
  _FREE: 5 analyses/day | Premium: Unlimited_
• `/recommend` - Get personalized insights
  _FREE: 3 recommendations/day | Premium: Unlimited_

💼 **Portfolio Tracking**
• `/portfolio` - View your positions & P&L
• `/add` - Add a crypto position
  _FREE: 3 positions max | Premium: Unlimited_
• `/sell` - Sell and record profit/loss
• `/summary` - Complete performance report
• `/history` - Transaction history

🔔 **Price Alerts (TP/SL)**
• `/setalert` - Set Take Profit or Stop Loss
  _FREE: 1 crypto with alerts (test) | Premium: Unlimited_
• `/listalerts` - View all your alerts
• `/removealert` - Delete an alert

💎 **Premium Features (€9/month)**
✅ Unlimited analyses & recommendations
✅ Unlimited portfolio positions
✅ Unlimited price alerts (TP/SL)
✅ Morning Briefing (daily 8h00 CET)
✅ Trade of the Day (daily 8h00 CET)

💳 **Subscription**
• `/subscribe` - Upgrade to Premium
• `/manage` - Manage your subscription

🔒 **Privacy & Data (GDPR)**
• `/mydata` - Export all your data
• `/deletedata` - Permanently delete account

──────────────────
📖 **QUICK EXAMPLES**

```
/analyze Bitcoin ETF approval incoming
/add BTC 0.5 45000
/setalert BTC tp 100000
/setalert BTC sl 40000
/sell BTC 0.3 75000
/recommend
```

──────────────────
📈 **Supported Cryptos**
BTC, ETH, SOL, BNB, XRP, ADA, AVAX, DOT, MATIC, LINK, UNI, ATOM, LTC, BCH, XLM

📊 Data: [CoinGecko](https://coingecko.com) + [Perplexity AI](https://perplexity.ai)
📄 [Terms](https://sentiment-trading-bot-production.up.railway.app/terms) | [Privacy](https://sentiment-trading-bot-production.up.railway.app/privacy)

_Type `/help` for detailed guide with Free limits_
"""
    await update.message.reply_text(welcome_text, parse_mode='Markdown', disable_web_page_preview=True)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """📚 **Complete User Guide**

🆓 **FREE vs 💎 PREMIUM**

**FREE Tier:**
• 5 sentiment analyses/day
• 3 portfolio positions max
• 1 crypto with TP/SL alerts
• 3 AI recommendations/day
_Quotas reset daily at midnight UTC_

**Premium (€9/month):**
• UNLIMITED everything above
• Morning Briefing (daily 8h CET)
• Trade of the Day (daily 8h CET)
• Priority support
💡 _Test FREE first, upgrade when ready!_

──────────────────
🔍 **SENTIMENT ANALYSIS**

`/analyze <text>` - AI sentiment (BULLISH/BEARISH/NEUTRAL)
_FREE: 5/day | Premium: Unlimited_

Examples:
• `/analyze Bitcoin ETF approval`
• Send article URL (auto-scrape)
• Send text 30+ chars (auto-analyze)

──────────────────
💼 **PORTFOLIO**

Track crypto holdings with real-time P&L

Commands:
• `/add BTC 1 45000` - Add/update position
• `/portfolio` - View all positions
• `/remove BTC 0.3` - Remove partial/full
• `/sell BTC 0.5 75000` - Sell & record P&L
• `/summary` - Performance analytics
• `/history` - Last 5 transactions

_FREE: 3 positions | Premium: Unlimited_

──────────────────
🔔 **PRICE ALERTS (TP/SL)**

Set Take Profit & Stop Loss alerts (checked every 15min)

Commands:
• `/setalert BTC tp 100000` - Take Profit
• `/setalert BTC sl 40000` - Stop Loss
• `/listalerts` - View all alerts
• `/removealert BTC` - Delete alerts

💡 _You can set BOTH TP & SL for same crypto!_

_FREE: 1 crypto | Premium: Unlimited_

──────────────────
🤖 **AI RECOMMENDATIONS**

`/recommend` - Get personalized portfolio insights:
• Diversification analysis
• Risk assessment
• Market sentiment for your holdings

_FREE: 3/day | Premium: Unlimited_

⚠️ _Informational only, NOT financial advice_

──────────────────
💎 **PREMIUM-ONLY**

**Morning Briefing** (8h CET daily)
• Market overview & sentiment
• Top movers & key news

**Trade of the Day** (8h CET daily)
• AI-selected opportunity
• Entry/exit suggestions

🚀 _Upgrade: `/subscribe` for €9/month_

──────────────────
💳 **SUBSCRIPTION**

• `/subscribe` - Upgrade to Premium
• `/manage` - View/manage subscription
• Secure Stripe payments
• Cancel anytime

──────────────────
🔒 **GDPR DATA RIGHTS**

• `/mydata` - Download all your data (JSON)
• `/deletedata CONFIRM` - Delete account

**Your Rights:**
• Access (Art. 15) - Export everything
• Erasure (Art. 17) - Delete everything
• Portability (Art. 20) - JSON format
• Auto-deletion after 180 days inactivity

[Privacy Policy](https://sentiment-trading-bot-production.up.railway.app/privacy)

──────────────────
📊 **SUPPORTED CRYPTOS**

BTC, ETH, SOL, BNB, XRP, ADA, AVAX, DOT, MATIC, LINK, UNI, ATOM, LTC, BCH, XLM

──────────────────
⚠️ **DISCLAIMER**

This bot provides informational services ONLY.
• NOT financial advice
• Crypto = HIGH RISK
• You may lose ENTIRE investment
• Always DYOR (Do Your Own Research)

[Terms of Service](https://sentiment-trading-bot-production.up.railway.app/terms)

_Back to main menu: `/start`_
"""
    await update.message.reply_text(help_text, parse_mode='Markdown', disable_web_page_preview=True)

@check_rate_limit
async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = ' '.join(context.args)
    if not user_text or len(user_text) < 10:
        await update.message.reply_text(
            "⚠️ Please provide text to analyze.\n\n"
            "**Examples:**\n"
            "`/analyze Bitcoin surges as ETFs see record inflows`\n"
            "`/analyze Ethereum merge completes successfully`",
            parse_mode='Markdown'
        )
        return
    
    urls = extract_urls(user_text)
    if urls:
        await analyze_url(update, urls[0])
    else:
        await analyze_text(update, user_text)

async def portfolio_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display user's crypto portfolio holdings with current prices."""
    if not DB_AVAILABLE:
        await update.message.reply_text(
            "⚠️ **Database Unavailable**\n\n"
            "The database is currently offline or connecting.\n"
            "Please try again in a few minutes.\n\n"
            "You can still use `/analyze` for sentiment!",
            parse_mode='Markdown'
        )
        return

    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or "User"
    
    logger.info(f"💼 /portfolio called by user {user_id} (@{username})")
    
    try:
        # Get portfolio with current prices
        portfolio = portfolio_manager.get_portfolio_with_prices(user_id, username)
        
        if not portfolio["positions"]:
            response = "💼 **Your Crypto Portfolio**\n\n"
            response += "_Your portfolio is empty._\n\n"
            response += "**Add positions with:**\n"
            response += "`/add BTC 0.5 45000`\n"
            response += "`/add ETH 10 2500`\n\n"
            response += "**Supported cryptos:**\n"
            response += "BTC, ETH, SOL, BNB, XRP, ADA, AVAX, DOT, MATIC, LINK, UNI, ATOM, LTC, BCH, XLM"
        else:
            response = "💼 **Your Crypto Portfolio**\n"
            response += "_Prices updated in real-time via CoinGecko_\n"
            
            for symbol, pos in portfolio["positions"].items():
                qty = pos["quantity"]
                avg_price = pos["avg_price"]
                current_price = pos["current_price"]
                current_value = pos["current_value"]
                pnl_usd = pos["pnl_usd"]
                pnl_percent = pos["pnl_percent"]
                
                # Choose emoji based on P&L
                pnl_emoji = "🟢" if pnl_percent > 0 else ("🔴" if pnl_percent < 0 else "⚪")
                
                # Check if price is available
                if current_price is None or current_price == 0:
                    price_display = "n/a (price feed error)"
                    pnl_display = "n/a"
                else:
                    price_display = format_price(current_price)
                    pnl_display = f"{pnl_usd:+,.2f} USD ({pnl_percent:+.2f}%)"
                
                response += f"\n**{symbol}** {pnl_emoji}\n"
                response += f"  • Quantity: `{qty:.8g}`\n"
                response += f"  • Avg Price: `{format_price(avg_price)}`\n"
                response += f"  • Current: `{price_display}`\n"
                response += f"  • Value: `{format_price(current_value) if current_value else 'n/a'}`\n"
                response += f"  • P&L: `{pnl_display}`"
            
            response += f"\n\n**Total Value:** `{format_price(portfolio['total_current_value'])}`"
            response += "\n\n_Prices by CoinGecko_"
        
        await update.message.reply_text(response, parse_mode='Markdown', disable_web_page_preview=True)
        logger.info(f"✅ /portfolio response sent to {user_id}")
        
    except Exception as e:
        logger.error(f"❌ /portfolio error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        await update.message.reply_text(
            "❌ **Error**\n\nSomething went wrong with the database. Please try again.",
            parse_mode='Markdown'
        )

@check_position_limit
async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not DB_AVAILABLE:
        await update.message.reply_text("⚠️ Database offline. Cannot add position.", parse_mode='Markdown')
        return

    """Add a crypto position to portfolio."""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    # Validate arguments
    if len(context.args) != 3:
        await update.message.reply_text(
            "⚠️ **Usage:** `/add <symbol> <quantity> <price>`\n\n"
            "**Examples:**\n"
            "`/add BTC 0.5 45000` - Buy 0.5 BTC at $45,000\n"
            "`/add ETH 10 2500` - Buy 10 ETH at $2,500",
            parse_mode='Markdown'
        )
        return
    
    symbol = context.args[0].upper()
    
    try:
        quantity = float(context.args[1])
        price = float(context.args[2])
    except ValueError:
        await update.message.reply_text("❌ Quantity and price must be numbers.", parse_mode='Markdown')
        return
    
    if quantity <= 0 or price <= 0:
        await update.message.reply_text("❌ Values must be positive.", parse_mode='Markdown')
        return
    
    try:
        result = portfolio_manager.add_position(user_id, symbol, quantity, price, username)
        current_price = get_crypto_price(symbol)
        
        response = f"✅ **Position {result['action'].capitalize()}**\n\n"
        response += f"**{symbol}**\n"
        response += f"  • Quantity: `{result['quantity']:.8g}`\n"
        response += f"  • Avg Price: `{format_price(result['avg_price'])}`\n"
        
        if current_price:
            current_value = result['quantity'] * current_price
            pnl_usd = current_value - (result['quantity'] * result['avg_price'])
            pnl_percent = ((current_price - result['avg_price']) / result['avg_price']) * 100
            
            response += f"\n📊 **Current Status:**\n"
            response += f"  • P&L: `{pnl_usd:+,.2f} USD ({pnl_percent:+.2f}%)`"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        logger.info(f"✅ /add {symbol} for user {user_id}")
        
    except Exception as e:
        logger.error(f"❌ /add error: {e}")
        await update.message.reply_text(f"❌ Error adding position. Is {symbol} supported?", parse_mode='Markdown')

async def remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove position (full or partial)."""
    if not DB_AVAILABLE:
        await update.message.reply_text("⚠️ Database offline.", parse_mode='Markdown')
        return

    user_id = update.effective_user.id
    
    if len(context.args) < 1 or len(context.args) > 2:
        await update.message.reply_text(
            "⚠️ **Usage:** `/remove <symbol> [quantity]`\n\n"
            "**Examples:**\n"
            "`/remove BTC` - Remove all BTC\n"
            "`/remove BTC 0.5` - Remove only 0.5 BTC",
            parse_mode='Markdown'
        )
        return
    
    symbol = context.args[0].upper()
    quantity = None
    
    # Parse optional quantity
    if len(context.args) == 2:
        try:
            quantity = float(context.args[1])
            if quantity <= 0:
                await update.message.reply_text("❌ Quantity must be positive.", parse_mode='Markdown')
                return
        except ValueError:
            await update.message.reply_text("❌ Quantity must be a number.", parse_mode='Markdown')
            return
    
    try:
        result = portfolio_manager.remove_position(user_id, symbol, quantity)
        
        if not result["success"]:
            error_msg = result.get("error", "Unknown error")
            await update.message.reply_text(f"⚠️ {error_msg}", parse_mode='Markdown')
            return
        
        if result["action"] == "full_remove":
            response = f"✅ **Position Removed**\n\n"
            response += f"`{symbol}` fully removed from portfolio.\n"
            response += f"Quantity removed: `{result['quantity_removed']:.8g}`"
        else:
            response = f"✅ **Partial Removal**\n\n"
            response += f"**{symbol}**\n"
            response += f"  • Removed: `{result['quantity_removed']:.8g}`\n"
            response += f"  • Remaining: `{result['quantity_remaining']:.8g}`"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        logger.info(f"✅ /remove {symbol} for user {user_id}")
        
    except Exception as e:
        logger.error(f"❌ /remove error: {e}")
        await update.message.reply_text("❌ Error removing position.", parse_mode='Markdown')

async def sell_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sell position and record realized P&L."""
    if not DB_AVAILABLE:
        await update.message.reply_text("⚠️ Database offline.", parse_mode='Markdown')
        return

    user_id = update.effective_user.id
    
    if len(context.args) != 3:
        await update.message.reply_text(
            "⚠️ **Usage:** `/sell <symbol> <quantity> <sell_price>`\n\n"
            "**Examples:**\n"
            "`/sell BTC 0.5 75000` - Sell 0.5 BTC at $75,000\n"
            "`/sell ETH 5 3500` - Sell 5 ETH at $3,500\n\n"
            "💡 Automatically records realized P&L for tracking",
            parse_mode='Markdown'
        )
        return
    
    symbol = context.args[0].upper()
    
    try:
        quantity = float(context.args[1])
        sell_price = float(context.args[2])
    except ValueError:
        await update.message.reply_text("❌ Quantity and price must be numbers.", parse_mode='Markdown')
        return
    
    if quantity <= 0 or sell_price <= 0:
        await update.message.reply_text("❌ Values must be positive.", parse_mode='Markdown')
        return
    
    try:
        result = portfolio_manager.sell_position(user_id, symbol, quantity, sell_price)
        
        if not result["success"]:
            error_msg = result.get("error", "Unknown error")
            await update.message.reply_text(f"⚠️ {error_msg}", parse_mode='Markdown')
            return
        
        pnl = result["pnl_realized"]
        pnl_emoji = "🟢" if pnl > 0 else ("🔴" if pnl < 0 else "⚪")
        
        response = f"{pnl_emoji} **SALE EXECUTED**\n\n"
        response += f"**{symbol}**\n"
        response += f"  • Quantity sold: `{result['quantity_sold']:.8g}`\n"
        response += f"  • Buy price: `{format_price(result['buy_price'])}`\n"
        response += f"  • Sell price: `{format_price(result['sell_price'])}`\n"
        response += f"  • **P&L Realized: `{pnl:+,.2f} USD ({result['pnl_percent']:+.2f}%)`**\n"
        
        if result["quantity_remaining"] > 0:
            response += f"\nℹ️ Remaining position: `{result['quantity_remaining']:.8g} {symbol}`"
        else:
            response += f"\n✅ Position fully closed"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        logger.info(f"✅ /sell {symbol} for user {user_id}: P&L {pnl:+.2f}")
        
    except Exception as e:
        logger.error(f"❌ /sell error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        await update.message.reply_text("❌ Error executing sale.", parse_mode='Markdown')

async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show enriched portfolio summary with realized/unrealized P&L."""
    if not DB_AVAILABLE:
        await update.message.reply_text("⚠️ Database offline.", parse_mode='Markdown')
        return

    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or "User"
    
    try:
        summary = portfolio_manager.get_enriched_summary(user_id, username)
        
        if summary["num_positions"] == 0:
            await update.message.reply_text(
                "📊 **Portfolio Empty**\n\nUse `/add BTC 0.5 45000` to start tracking!",
                parse_mode='Markdown'
            )
            return
        
        total_pnl = summary["total_pnl"]
        overall_emoji = "🚀" if total_pnl > 0 else "📉"
        
        response = f"{overall_emoji} **PORTFOLIO ANALYTICS**\n"
        response += f"\n──────────────────\n"
        response += f"📊 **GLOBAL PERFORMANCE**\n"
        response += f"──────────────────\n\n"
        response += f"💰 **Total P&L: `{total_pnl:+,.2f} USD`**\n"
        response += f"  • Unrealized: `{summary['unrealized_pnl']:+,.2f} USD ({summary['unrealized_pnl_percent']:+.2f}%)`\n"
        response += f"  • Realized: `{summary['realized_pnl']:+,.2f} USD`\n\n"
        response += f"💵 **Capital:**\n"
        response += f"  • Invested: `{format_price(summary['total_invested'])}`\n"
        response += f"  • Current value: `{format_price(summary['total_current_value'])}`\n"
        response += f"  • Active positions: `{summary['num_positions']}`\n"
        
        # Best/worst performers
        if summary["best_performer"]:
            best = summary["best_performer"]
            worst = summary["worst_performer"]
            response += f"\n🏆 **Best performer:** `{best['symbol']}` ({best['pnl_percent']:+.2f}%)\n"
            response += f"📉 **Worst performer:** `{worst['symbol']}` ({worst['pnl_percent']:+.2f}%)\n"
        
        # Diversification
        div_score = summary["diversification_score"]
        div_emoji = "🟢" if div_score >= 80 else ("🟡" if div_score >= 50 else "🔴")
        response += f"\n{div_emoji} **Diversification:** {div_score}% ({summary['num_positions']} positions)\n"
        
        response += f"\n_Use `/portfolio` for detailed breakdown_"
        
        await update.message.reply_text(response, parse_mode='Markdown', disable_web_page_preview=True)
        logger.info(f"✅ /summary sent to {user_id}")
        
    except Exception as e:
        logger.error(f"❌ /summary error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        await update.message.reply_text("❌ Error generating summary.", parse_mode='Markdown')

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show last 5 transactions with enhanced formatting."""
    if not DB_AVAILABLE:
        await update.message.reply_text("⚠️ Database offline.", parse_mode='Markdown')
        return
        
    user_id = update.effective_user.id
    try:
        transactions = portfolio_manager.get_transactions(user_id, limit=5)
        if not transactions:
            await update.message.reply_text("📃 No transactions yet.\n\nUse `/add BTC 0.5 45000` to get started!", parse_mode='Markdown')
            return
        
        response = "📃 **Transaction History**\n"
        response += "_Last 5 operations_\n"
        
        for i, tx in enumerate(transactions, 1):
            action_emoji = {
                "BUY": "🟢",
                "SELL": "🔵",
                "REMOVE": "❌",
                "PARTIAL_REMOVE": "⚠️"
            }.get(tx['action'], "🔹")
            
            response += f"\n**{i}.** {action_emoji} {tx['action']} `{tx['symbol']}`\n"
            response += f"   Qty: `{tx['quantity']:.8g}` @ `{format_price(tx['price'])}`"
            
            # Show P&L for sells
            if 'pnl' in tx and tx['pnl'] is not None:
                pnl_emoji = "🟢" if tx['pnl'] > 0 else "🔴"
                response += f"\n   {pnl_emoji} P&L: `{tx['pnl']:+,.2f} USD`"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        logger.info(f"✅ /history sent to {user_id}")
        
    except Exception as e:
        logger.error(f"❌ /history error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        await update.message.reply_text("❌ Error loading history.", parse_mode='Markdown')

# ===== PRICE ALERTS COMMANDS WITH TP/SL =====

@check_alert_limit
async def setalert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set TP/SL price alerts for a crypto."""
    if not DB_AVAILABLE:
        await update.message.reply_text("⚠️ Database offline. Cannot set alert.", parse_mode='Markdown')
        return
    
    user_id = update.effective_user.id
    
    # Validate arguments: /setalert BTC tp 80000 OR /setalert BTC sl 70000
    if len(context.args) != 3:
        await update.message.reply_text(
            "⚠️ **Usage:** `/setalert <symbol> <tp|sl> <price>`\n\n"
            "**Examples:**\n"
            "`/setalert BTC tp 100000` - Take Profit at $100k\n"
            "`/setalert BTC sl 40000` - Stop Loss at $40k\n"
            "`/setalert ETH tp 5000` - Take Profit ETH at $5k\n\n"
            "💡 **You can set BOTH TP and SL independently**",
            parse_mode='Markdown'
        )
        return
    
    symbol = context.args[0].upper()
    alert_type = context.args[1].lower()
    
    # Validate alert type
    if alert_type not in ['tp', 'sl']:
        await update.message.reply_text(
            "❌ **Invalid alert type**\n\n"
            "Use `tp` for Take Profit or `sl` for Stop Loss\n\n"
            "**Example:** `/setalert BTC tp 80000`",
            parse_mode='Markdown'
        )
        return
    
    try:
        price = float(context.args[2])
    except ValueError:
        await update.message.reply_text("❌ Price must be a number.", parse_mode='Markdown')
        return
    
    if price <= 0:
        await update.message.reply_text("❌ Price must be positive.", parse_mode='Markdown')
        return
    
    # Check if symbol supported
    if not is_symbol_supported(symbol):
        await update.message.reply_text(
            f"❌ **{symbol} not supported**\n\n"
            "Supported cryptos: BTC, ETH, SOL, BNB, XRP, ADA, AVAX, DOT, MATIC, LINK, UNI, ATOM, LTC, BCH, XLM",
            parse_mode='Markdown'
        )
        return
    
    # Fetch current price
    current_price = get_crypto_price(symbol)
    
    if current_price is None:
        await update.message.reply_text(
            f"⚠️ **Price API Temporarily Unavailable**\n\n"
            f"Cannot fetch current price for **{symbol}** right now.\n"
            f"This is likely a temporary CoinGecko API issue.\n\n"
            f"💡 **Please try again in a few minutes.**",
            parse_mode='Markdown'
        )
        return
    
    # VALIDATION: Check price coherence with current price
    if alert_type == 'tp' and price <= current_price:
        await update.message.reply_text(
            f"⚠️ **Invalid TP**\n\n"
            f"Take Profit must be **above** current price.\n\n"
            f"Current price: `{format_price(current_price)}`\n"
            f"Your TP: `{format_price(price)}`\n\n"
            f"💡 Set a higher price for TP (e.g., `{format_price(current_price * 1.1)}`)",
            parse_mode='Markdown'
        )
        return
    
    if alert_type == 'sl' and price >= current_price:
        await update.message.reply_text(
            f"⚠️ **Invalid SL**\n\n"
            f"Stop Loss must be **below** current price.\n\n"
            f"Current price: `{format_price(current_price)}`\n"
            f"Your SL: `{format_price(price)}`\n\n"
            f"💡 Set a lower price for SL (e.g., `{format_price(current_price * 0.9)}`)",
            parse_mode='Markdown'
        )
        return
    
    # Optional: Check if user has position (warning only, not blocking)
    position = redis_storage.get_position(user_id, symbol)
    warning_msg = ""
    if not position and alert_type == 'sl':
        warning_msg = "\n⚠️ _You don't hold this asset in your portfolio_\n"
    
    # Check if alert already exists
    existing_alert = redis_storage.get_alert(user_id, symbol)
    if existing_alert:
        if alert_type == 'tp' and existing_alert.get('tp'):
            await update.message.reply_text(
                f"⚠️ **TP Already Exists**\n\n"
                f"**{symbol}** already has a Take Profit at `{format_price(existing_alert['tp'])}`\n\n"
                f"To modify, use: `/removealert {symbol}` first, then set new alert.",
                parse_mode='Markdown'
            )
            return
        
        if alert_type == 'sl' and existing_alert.get('sl'):
            await update.message.reply_text(
                f"⚠️ **SL Already Exists**\n\n"
                f"**{symbol}** already has a Stop Loss at `{format_price(existing_alert['sl'])}`\n\n"
                f"To modify, use: `/removealert {symbol}` first, then set new alert.",
                parse_mode='Markdown'
            )
            return
    
    # Set alert in Redis
    try:
        tp_value = price if alert_type == 'tp' else None
        sl_value = price if alert_type == 'sl' else None
        
        result = redis_storage.set_alert(user_id, symbol, tp=tp_value, sl=sl_value, update_only=True)
        
        if result["success"]:
            alert = result["alert"]
            
            # Build response
            response = f"✅ **Alert Set!**\n\n"
            response += f"**{symbol}**\n"
            
            if alert.get('tp'):
                diff_tp = ((alert['tp'] - current_price) / current_price) * 100
                response += f"🎯 TP: `{format_price(alert['tp'])}` (+{diff_tp:.1f}%)\n"
            
            if alert.get('sl'):
                diff_sl = ((current_price - alert['sl']) / current_price) * 100
                response += f"🛡️ SL: `{format_price(alert['sl'])}` (-{diff_sl:.1f}%)\n"
            
            response += f"\n📊 Current: `{format_price(current_price)}`"
            response += warning_msg
            response += f"\n\n_Alerts checked every 15 minutes_\n"
            response += f"_Use `/listalerts` to see all your alerts_"
            
            await update.message.reply_text(response, parse_mode='Markdown')
            logger.info(f"✅ Alert set: User {user_id} - {symbol} {alert_type.upper()} @ {price}")
        else:
            await update.message.reply_text(f"❌ {result['message']}", parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"❌ /setalert error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        await update.message.reply_text("❌ Error setting alert.", parse_mode='Markdown')

async def listalerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all active TP/SL price alerts."""
    if not DB_AVAILABLE:
        await update.message.reply_text("⚠️ Database offline.", parse_mode='Markdown')
        return
    
    user_id = update.effective_user.id
    
    try:
        alerts = redis_storage.get_alerts(user_id)
        
        if not alerts:
            response = "🔔 **Your Price Alerts**\n\n"
            response += "_You have no active alerts._\n\n"
            response += "**Set alerts with:**\n"
            response += "`/setalert BTC tp 100000`\n"
            response += "`/setalert BTC sl 40000`"
        else:
            response = "🔔 **Your Price Alerts**\n"
            response += f"_Active alerts: {len(alerts)}_\n"
            
            for symbol, alert_data in alerts.items():
                current_price = get_crypto_price(symbol)
                
                if current_price:
                    response += f"\n{'✅' if current_price else '⚠️'} **{symbol}**\n"
                    response += f"📊 Current: `{format_price(current_price)}`\n"
                    
                    if alert_data.get('tp'):
                        tp = alert_data['tp']
                        diff_tp = ((tp - current_price) / current_price) * 100
                        
                        if current_price >= tp:
                            status_tp = f"✅ **TARGET REACHED!** (+{diff_tp:.1f}%)"
                        else:
                            status_tp = f"⏳ Waiting (+{diff_tp:.1f}% to go)"
                        
                        response += f"🎯 TP: `{format_price(tp)}` - {status_tp}\n"
                    
                    if alert_data.get('sl'):
                        sl = alert_data['sl']
                        diff_sl = ((current_price - sl) / current_price) * 100
                        
                        if current_price <= sl:
                            status_sl = f"🚨 **STOP TRIGGERED!** (-{diff_sl:.1f}%)"
                        else:
                            status_sl = f"⏳ Safe (+{diff_sl:.1f}% margin)"
                        
                        response += f"🛡️ SL: `{format_price(sl)}` - {status_sl}"
                else:
                    response += f"\n⚠️ **{symbol}**\n"
                    response += f"  • Current: _price unavailable_"
            
            response += f"\n\n_Alerts checked every 15 minutes_\n"
            response += f"_Remove with `/removealert <SYMBOL>`_"
        
        await update.message.reply_text(response, parse_mode='Markdown', disable_web_page_preview=True)
        logger.info(f"✅ /listalerts sent to {user_id}")
    
    except Exception as e:
        logger.error(f"❌ /listalerts error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        await update.message.reply_text("❌ Error loading alerts.", parse_mode='Markdown')

async def removealert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove all price alerts (TP and SL) for a crypto."""
    if not DB_AVAILABLE:
        await update.message.reply_text("⚠️ Database offline.", parse_mode='Markdown')
        return
    
    user_id = update.effective_user.id
    
    # Validate arguments
    if len(context.args) != 1:
        await update.message.reply_text(
            "⚠️ **Usage:** `/removealert <symbol>`\n\n"
            "**Example:** `/removealert BTC`\n\n"
            "This will remove BOTH TP and SL alerts for the crypto.",
            parse_mode='Markdown'
        )
        return
    
    symbol = context.args[0].upper()
    
    try:
        # Check if alert exists
        alert = redis_storage.get_alert(user_id, symbol)
        
        if not alert:
            await update.message.reply_text(
                f"⚠️ No alert found for **{symbol}**.\n\n"
                f"Use `/listalerts` to see your active alerts.",
                parse_mode='Markdown'
            )
            return
        
        # Remove alert
        success = redis_storage.remove_alert(user_id, symbol)
        
        if success:
            response = f"✅ **Alerts Removed**\n\n"
            response += f"All alerts for `{symbol}` deleted:\n"
            
            if alert.get('tp'):
                response += f"  • TP: `{format_price(alert['tp'])}`\n"
            if alert.get('sl'):
                response += f"  • SL: `{format_price(alert['sl'])}`\n"
            
            response += f"\n_Use `/setalert` to create new alerts_"
            
            await update.message.reply_text(response, parse_mode='Markdown')
            logger.info(f"✅ Alert removed: User {user_id} - {symbol}")
        else:
            await update.message.reply_text("❌ Error removing alert. Please try again.", parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"❌ /removealert error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        await update.message.reply_text("❌ Error removing alert.", parse_mode='Markdown')

# ===== AI RECOMMENDATIONS COMMAND (FEATURE 4) =====

@check_recommendation_limit
async def recommend_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Wrapper for AI recommendations handler."""
    await recommend_handler_fn(
        update, 
        context, 
        DB_AVAILABLE, 
        portfolio_manager, 
        is_symbol_supported, 
        format_price
    )

# ===== STRIPE PREMIUM SUBSCRIPTION COMMANDS =====

async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /subscribe - Create Stripe checkout session."""
    if not STRIPE_AVAILABLE:
        await update.message.reply_text(
            "⚠️ **Premium subscriptions temporarily unavailable**\n\n"
            "Please try again later or contact support.",
            parse_mode='Markdown'
        )
        return
    
    chat_id = update.effective_chat.id
    username = update.effective_user.username
    
    logger.info(f"💳 /subscribe called by user {chat_id} (@{username})")
    
    # Check if user is already premium
    status = get_subscription_status(chat_id)
    
    if status == 'premium':
        await update.message.reply_text(
            "✅ **You're already Premium!**\n\n"
            "Use `/manage` to manage your subscription.",
            parse_mode='Markdown'
        )
        return
    
    # Create Stripe Checkout session
    result = create_checkout_session(
        user_id=chat_id,
        username=username
    )
    
    if result['success']:
        # Create inline button with payment link
        keyboard = [[
            InlineKeyboardButton(
                "🔥 Subscribe Now - €9/month",
                url=result['url']
            )
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🔒 **Upgrade to Premium**\n\n"
            "**€9/month** - Cancel anytime\n\n"
            "**Premium Features:**\n"
            "✅ Unlimited portfolio tracking\n"
            "✅ AI-powered recommendations\n"
            "✅ Real-time sentiment alerts\n"
            "✅ Advanced analytics\n"
            "✅ Priority support\n\n"
            "*Click below to subscribe securely via Stripe*",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        logger.info(f"✅ Checkout session created for user {chat_id}: {result['session_id']}")
    
    else:
        logger.error(f"❌ Failed to create checkout session: {result['error']}")
        await update.message.reply_text(
            "❌ **Payment setup error**\n\n"
            "Sorry, we couldn't create your payment session. "
            "Please try again later or contact support.\n\n"
            f"Error: {result['error']}",
            parse_mode='Markdown'
        )

async def manage_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /manage - Manage existing subscription."""
    if not STRIPE_AVAILABLE:
        await update.message.reply_text(
            "⚠️ **Subscription management temporarily unavailable**\n\n"
            "Please try again later or contact support.",
            parse_mode='Markdown'
        )
        return
    
    chat_id = update.effective_chat.id
    
    status = get_subscription_status(chat_id)
    
    if status != 'premium':
        await update.message.reply_text(
            "⚠️ **You don't have an active subscription**\n\n"
            "Use `/subscribe` to upgrade to Premium!",
            parse_mode='Markdown'
        )
        return
    
    # Retrieve subscription details
    sub_result = retrieve_subscription(chat_id)
    
    if sub_result['success']:
        sub = sub_result['subscription']
        renewal_date = datetime.fromtimestamp(sub['current_period_end']).strftime('%d %b %Y')
        
        message_text = (
            "✅ **Premium Subscription Active**\n\n"
            f"**Status:** {sub['status'].title()}\n"
            f"**Next renewal:** {renewal_date}\n"
            f"**Price:** €9/month\n\n"
        )
        
        if sub['cancel_at_period_end']:
            cancel_date = datetime.fromtimestamp(sub['cancel_at']).strftime('%d %b %Y')
            message_text += f"⚠️ **Subscription will end on:** {cancel_date}\n\n"
        
        message_text += (
            "To cancel or update your subscription, "
            "please contact support at:\n"
            "📧 cryptosentinel.contact@gmail.com\n\n"
            "_We'll add a self-service portal soon!_"
        )
        
        await update.message.reply_text(message_text, parse_mode='Markdown')
    else:
        await update.message.reply_text(
            "❌ **Could not retrieve subscription details**\n\n"
            "Please contact support for assistance.",
            parse_mode='Markdown'
        )

# ===== GDPR DATA COMMANDS =====

async def mydata_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Export user data (GDPR Right to Access - Art. 15)."""
    if not DB_AVAILABLE:
        await update.message.reply_text("⚠️ Database offline.", parse_mode='Markdown')
        return
    
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or "User"
    
    try:
        # Collect all user data
        profile = redis_storage.get_user_profile(user_id) or {"user_id": user_id, "username": username}
        positions = redis_storage.get_all_positions(user_id)
        alerts = redis_storage.get_alerts(user_id)
        transactions = redis_storage.get_transactions(user_id, limit=100)
        realized_pnl = redis_storage.get_realized_pnl(user_id)
        
        # Build JSON export
        data_export = {
            "profile": profile,
            "positions": positions,
            "alerts": alerts,
            "transactions": transactions,
            "realized_pnl": realized_pnl,
            "export_date": datetime.utcnow().isoformat(),
            "gdpr_info": {
                "right": "GDPR Article 15 - Right to Access",
                "controller": "CryptoSentinel AI, Switzerland",
                "contact": "cryptosentinel.contact@gmail.com"
            }
        }
        
        # Format as readable JSON
        json_output = json.dumps(data_export, indent=2, ensure_ascii=False)
        
        # Send as file
        json_file = BytesIO(json_output.encode('utf-8'))
        json_file.name = f"cryptosentinel_data_{user_id}.json"
        
        await update.message.reply_document(
            document=json_file,
            filename=f"cryptosentinel_data_{user_id}.json",
            caption=(
                "📦 **Your Data Export (GDPR)**\n\n"
                "This file contains ALL your data stored in CryptoSentinel AI:\n"
                "• Profile\n"
                "• Portfolio positions\n"
                "• Price alerts\n"
                "• Transaction history\n"
                "• Realized P&L records\n\n"
                "_This is your RIGHT TO ACCESS under GDPR Article 15._\n\n"
                "📄 [Privacy Policy](https://sentiment-trading-bot-production.up.railway.app/privacy)"
            ),
            parse_mode='Markdown'
        )
        logger.info(f"✅ /mydata export sent to user {user_id}")
        
    except Exception as e:
        logger.error(f"❌ /mydata error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        await update.message.reply_text("❌ Error exporting data.", parse_mode='Markdown')

async def deletedata_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete all user data (GDPR Right to Erasure - Art. 17)."""
    if not DB_AVAILABLE:
        await update.message.reply_text("⚠️ Database offline.", parse_mode='Markdown')
        return
    
    user_id = update.effective_user.id
    
    # Confirmation message
    confirmation_text = (
        "⚠️ **DELETE ALL YOUR DATA?**\n\n"
        "This will PERMANENTLY delete:\n"
        "• Your profile\n"
        "• All portfolio positions\n"
        "• All price alerts\n"
        "• Transaction history\n"
        "• Realized P&L records\n\n"
        "**⚠️ THIS CANNOT BE UNDONE!**\n\n"
        "To confirm, send:\n"
        "`/deletedata CONFIRM`\n\n"
        "_This is your RIGHT TO ERASURE under GDPR Article 17._"
    )
    
    # Check if user provided CONFIRM
    if len(context.args) == 0:
        await update.message.reply_text(confirmation_text, parse_mode='Markdown')
        return
    
    if len(context.args) == 1 and context.args[0].upper() == "CONFIRM":
        try:
            # Delete all user data
            # Get all positions to delete
            positions = redis_storage.get_all_positions(user_id)
            for symbol in positions.keys():
                redis_storage.delete_position(user_id, symbol)
            
            # Get all alerts to delete
            alerts = redis_storage.get_alerts(user_id)
            for symbol in alerts.keys():
                redis_storage.remove_alert(user_id, symbol)
            
            # Delete profile, transactions, realized_pnl
            redis_storage.redis_client.delete(f"user:{user_id}:profile")
            redis_storage.redis_client.delete(f"user:{user_id}:transactions")
            redis_storage.redis_client.delete(f"user:{user_id}:realized_pnl")
            
            response = (
                "✅ **DATA DELETED**\n\n"
                "All your data has been permanently deleted from CryptoSentinel AI.\n\n"
                "This includes:\n"
                "• Profile\n"
                "• Portfolio positions\n"
                "• Price alerts\n"
                "• Transaction history\n"
                "• Realized P&L\n\n"
                "You can start fresh anytime with `/start`.\n\n"
                "Thank you for using CryptoSentinel AI. 👋"
            )
            
            await update.message.reply_text(response, parse_mode='Markdown')
            logger.info(f"✅ /deletedata executed for user {user_id} - ALL DATA DELETED")
            
        except Exception as e:
            logger.error(f"❌ /deletedata error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            await update.message.reply_text("❌ Error deleting data. Please try again.", parse_mode='Markdown')
    else:
        await update.message.reply_text(
            "⚠️ Invalid confirmation.\n\nUse: `/deletedata CONFIRM`",
            parse_mode='Markdown'
        )

# ===== MESSAGE HANDLERS =====

async def analyze_url(update: Update, url: str):
    scraping_msg = await update.message.reply_text("📰 Scraping article...", parse_mode='Markdown')
    try:
        article_text = extract_article(url)
        if not article_text:
            await scraping_msg.delete()
            await update.message.reply_text("❌ Failed to extract article.", parse_mode='Markdown')
            return
        
        await scraping_msg.edit_text("🔍 Analyzing with Perplexity AI...")
        result = analyze_sentiment(article_text)
        
        emoji = {'BULLISH': '🚀', 'BEARISH': '📉', 'NEUTRAL': '➡️'}.get(result['sentiment'], '❓')
        response = f"""
📰 **Article Analysis**

{emoji} **{result['sentiment']}** ({result['confidence']}% confidence)

💡 {result['reasoning']}

_Powered by [Perplexity AI](https://www.perplexity.ai)_
"""
        await scraping_msg.delete()
        await update.message.reply_text(response, parse_mode='Markdown', disable_web_page_preview=True)
    except Exception as e:
        logger.error(f"Error in analyze_url: {e}")
        await scraping_msg.delete()
        await update.message.reply_text("❌ Analysis failed.", parse_mode='Markdown')

async def analyze_text(update: Update, text: str):
    analyzing_msg = await update.message.reply_text("🔍 Analyzing...")
    try:
        result = analyze_sentiment(text)
        emoji = {'BULLISH': '🚀', 'BEARISH': '📉', 'NEUTRAL': '➡️'}.get(result['sentiment'], '❓')
        response = f"""
{emoji} **{result['sentiment']}** ({result['confidence']}%)

💡 {result['reasoning']}

_Powered by [Perplexity AI](https://www.perplexity.ai)_
"""
        await analyzing_msg.delete()
        await update.message.reply_text(response, parse_mode='Markdown', disable_web_page_preview=True)
    except Exception as e:
        logger.error(f"Error: {e}")
        await analyzing_msg.delete()
        await update.message.reply_text("❌ Analysis failed.", parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    urls = extract_urls(user_message)
    if urls:
        await analyze_url(update, urls[0])
        return
    if len(user_message) > 30:
        await analyze_text(update, user_message)
    else:
        await update.message.reply_text(f"💬 You said: _{user_message}_\n\nUse `/analyze` for sentiment analysis!", parse_mode='Markdown')

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Bot error: {context.error}")

# ===== FASTAPI ROUTES =====

@app.get("/")
async def root():
    return {"status": "ok", "message": "Sentiment Trading Bot Running", "db": DB_AVAILABLE, "stripe": STRIPE_AVAILABLE}

@app.get("/health")
async def health():
    # Return 200 even if DB is down, to prevent Railway from killing the bot
    return {
        "status": "ok", 
        "db_connected": DB_AVAILABLE,
        "stripe_enabled": STRIPE_AVAILABLE,
        "features": {
            "sentiment": "online",
            "portfolio": "online" if DB_AVAILABLE else "offline",
            "alerts": "online" if DB_AVAILABLE else "offline",
            "premium": "online" if STRIPE_AVAILABLE else "offline"
        }
    }

# LEGAL PAGES ROUTES (Privacy fix - no GitHub username exposed)
@app.get("/terms", response_class=HTMLResponse)
async def terms_page():
    """Serve Terms of Service page."""
    try:
        templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
        terms_path = os.path.join(templates_dir, 'terms.html')
        with open(terms_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Terms of Service</h1><p>File not found</p>"

@app.get("/privacy", response_class=HTMLResponse)
async def privacy_page():
    """Serve Privacy Policy page."""
    try:
        templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
        privacy_path = os.path.join(templates_dir, 'privacy.html')
        with open(privacy_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Privacy Policy</h1><p>File not found</p>"

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return Response(status_code=500)

@app.get("/webhook")
async def webhook_check():
    return {"status": "ok", "method": "GET", "endpoint": "/webhook"}

async def setup_application():
    global application
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN required")
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Initialize tier_manager and portfolio_manager in bot_data for decorators
    if TIER_SYSTEM_AVAILABLE:
        application.bot_data['tier_manager'] = tier_manager
        application.bot_data['portfolio_manager'] = portfolio_manager
        logger.info("✅ Tier manager initialized in bot_data")
    else:
        logger.warning("⚠️ Tier manager not initialized - all features free")
    
    # Add all command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("analyze", analyze_command))
    application.add_handler(CommandHandler("portfolio", portfolio_command))
    application.add_handler(CommandHandler("add", add_command))
    application.add_handler(CommandHandler("remove", remove_command))
    application.add_handler(CommandHandler("sell", sell_command))
    application.add_handler(CommandHandler("summary", summary_command))
    application.add_handler(CommandHandler("history", history_command))
    
    # Price alerts commands with TP/SL
    application.add_handler(CommandHandler("setalert", setalert_command))
    application.add_handler(CommandHandler("listalerts", listalerts_command))
    application.add_handler(CommandHandler("removealert", removealert_command))
    
    # AI Recommendations (Feature 4)
    application.add_handler(CommandHandler("recommend", recommend_command))
    
    # Premium Subscription (Stripe)
    application.add_handler(CommandHandler("subscribe", subscribe_command))
    application.add_handler(CommandHandler("manage", manage_command))
    
    # GDPR Data Commands
    application.add_handler(CommandHandler("mydata", mydata_command))
    application.add_handler(CommandHandler("deletedata", deletedata_command))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)
    
    await application.initialize()
    await application.start()
    
    if WEBHOOK_URL:
        clean_webhook_url = WEBHOOK_URL.rstrip('/')
        webhook_endpoint = f"{clean_webhook_url}/webhook"
        await application.bot.set_webhook(url=webhook_endpoint)
        logger.info(f"✅ Webhook configured: {webhook_endpoint}")

@app.on_event("startup")
async def startup():
    global DB_AVAILABLE
    logger.info("🚀 FastAPI startup - Redis Mode")
    
    try:
        logger.info("🔥 Testing Redis connection...")
        redis_connected = redis_storage.test_connection()
        
        if redis_connected:
            DB_AVAILABLE = True
            logger.info("✅ Redis connected successfully!")
        else:
            DB_AVAILABLE = False
            logger.warning("⚠️ Bot starting in LIMITED MODE (Sentiment only, no Portfolio/Alerts)")
    except Exception as e:
        logger.error(f"⚠️ Redis connection failed: {e}")
        logger.warning("⚠️ Bot starting in LIMITED MODE (Sentiment only, no Portfolio/Alerts)")
        DB_AVAILABLE = False
    
    # Log Stripe status
    if STRIPE_AVAILABLE:
        logger.info("✅ Stripe integration enabled")
    else:
        logger.warning("⚠️ Stripe integration disabled")
    
    # Log Tier System status
    if TIER_SYSTEM_AVAILABLE:
        logger.info("✅ Tier management system enabled (Free/Premium limits active)")
    else:
        logger.warning("⚠️ Tier management system disabled (all features unlimited)")
    
    await setup_application()
    logger.info("✅ Server ready")

@app.on_event("shutdown")
async def shutdown():
    if application:
        await application.stop()
        await application.shutdown()
