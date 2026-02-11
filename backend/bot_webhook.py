#!/usr/bin/env python3
"""
Telegram Bot with Webhook support for Railway deployment.
Uses FastAPI for native async support.
"""
import os
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

# ===== CRITICAL FIX: Configure logging BEFORE any imports that use logger =====
load_dotenv()

import logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
# ===== Now logger is available for all import error handlers below =====

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
    from backend.stripe_service import create_checkout_session, get_subscription_status, retrieve_subscription, get_subscription_id
    STRIPE_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ Stripe service not available - Premium subscriptions disabled")
    STRIPE_AVAILABLE = False

# Stripe Webhook Router
try:
    from backend.routes.stripe_webhook import router as stripe_webhook_router
    STRIPE_WEBHOOK_AVAILABLE = True
except ImportError:
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
    logger.warning("⚠️ Tier management not available")
    TIER_SYSTEM_AVAILABLE = False
    # Dummy decorators if tier system not available
    def premium_required(func): return func
    def check_rate_limit(func): return func
    def check_position_limit(func): return func
    def check_alert_limit(func): return func
    def check_recommendation_limit(func): return func

# Analytics System (Phase 1.5)
try:
    from backend.analytics_integration import (
        init_analytics,
        track_command,
        track_registration,
        track_conversion
    )
    from backend.routes.analytics import router as analytics_router
    ANALYTICS_AVAILABLE = True
except ImportError as e:
    logger.error(f"❌ Analytics import error: {e}")
    import traceback
    logger.error(f"Full traceback:\n{traceback.format_exc()}")
    logger.warning("⚠️ Analytics system not available")
    ANALYTICS_AVAILABLE = False
    def init_analytics(): return False
    def track_command(*args, **kwargs): pass
    def track_registration(*args, **kwargs): pass
    def track_conversion(*args, **kwargs): pass
    analytics_router = None

# Admin Dashboard Router (Phase 1.5)
try:
    from backend.routes.admin import router as admin_router
    ADMIN_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ Admin dashboard router not available")
    ADMIN_AVAILABLE = False
    admin_router = None

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

# Include Analytics Router (Phase 1.5)
if ANALYTICS_AVAILABLE and analytics_router:
    app.include_router(analytics_router)
    logger.info("✅ Analytics router registered at /analytics")
else:
    logger.warning("⚠️ Analytics router NOT registered")

# Include Admin Dashboard Router (Phase 1.5)
if ADMIN_AVAILABLE and admin_router:
    app.include_router(admin_router)
    logger.info("✅ Admin dashboard router registered at /admin/users")
else:
    logger.warning("⚠️ Admin dashboard router NOT registered")

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
  _FREE: 3 analyses/day | Premium: Unlimited_
• `/recommend` - Get personalized insights
  _FREE: 3 recommendations/week | Premium: Unlimited_

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
    
    # Track registration (Phase 1.5 Analytics)
    if ANALYTICS_AVAILABLE:
        track_registration(user.id, user.username)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    help_text = """📚 **Complete User Guide**

🆓 **FREE vs 💎 PREMIUM**

**FREE Tier:**
• 3 sentiment analyses/day
• 3 portfolio positions max
• 1 crypto with TP/SL alerts
• 3 AI recommendations/week (resets Monday)
_Daily quotas reset at midnight UTC_

**Premium (€9/month):**
• UNLIMITED everything above
• Morning Briefing (daily 8h CET)
• Trade of the Day (daily 8h CET)
• Priority support
💡 _Test FREE first, upgrade when ready!_

──────────────────
🔍 **SENTIMENT ANALYSIS**

`/analyze <text>` - AI sentiment (BULLISH/BEARISH/NEUTRAL)
_FREE: 3/day | Premium: Unlimited_

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

_FREE: 3/week (resets Monday) | Premium: Unlimited_

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
📈 **SUPPORTED CRYPTOS**

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
    
    # Track help command (Phase 1.5 Analytics)
    if ANALYTICS_AVAILABLE:
        track_command('help', user_id, success=True)

@check_rate_limit
async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
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
    
    try:
        urls = extract_urls(user_text)
        if urls:
            await analyze_url(update, urls[0])
        else:
            await analyze_text(update, user_text)
        
        # Track successful analyze
        if ANALYTICS_AVAILABLE:
            track_command('analyze', user_id, success=True)
    
    except Exception as e:
        logger.error(f"❌ /analyze error: {e}")
        # Track failed command
        if ANALYTICS_AVAILABLE:
            track_command('analyze', user_id, success=False, error=str(e))
        raise

async def portfolio_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display user's crypto portfolio holdings with current prices."""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or "User"
    
    if not DB_AVAILABLE:
        await update.message.reply_text(
            "⚠️ **Database Unavailable**\n\n"
            "The database is currently offline or connecting.\n"
            "Please try again in a few minutes.\n\n"
            "You can still use `/analyze` for sentiment!",
            parse_mode='Markdown'
        )
        if ANALYTICS_AVAILABLE:
            track_command('portfolio', user_id, success=False, error='db_offline')
        return
    
    logger.info(f"💼 /portfolio called by user {user_id} (@{username})")
    
    try:
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
                
                pnl_emoji = "🟢" if pnl_percent > 0 else ("🔴" if pnl_percent < 0 else "⚪")
                
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
        
        # Track successful portfolio command
        if ANALYTICS_AVAILABLE:
            track_command('portfolio', user_id, success=True)
        
    except Exception as e:
        logger.error(f"❌ /portfolio error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        await update.message.reply_text(
            "❌ **Error**\n\nSomething went wrong with the database. Please try again.",
            parse_mode='Markdown'
        )
        
        # Track failed command
        if ANALYTICS_AVAILABLE:
            track_command('portfolio', user_id, success=False, error=str(e))

@check_position_limit
async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    if not DB_AVAILABLE:
        await update.message.reply_text("⚠️ Database offline. Cannot add position.", parse_mode='Markdown')
        if ANALYTICS_AVAILABLE:
            track_command('add', user_id, success=False, error='db_offline')
        return
    
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
        
        # Track successful add
        if ANALYTICS_AVAILABLE:
            track_command('add', user_id, success=True)
        
    except Exception as e:
        logger.error(f"❌ /add error: {e}")
        await update.message.reply_text(f"❌ Error adding position. Is {symbol} supported?", parse_mode='Markdown')
        
        # Track failed add
        if ANALYTICS_AVAILABLE:
            track_command('add', user_id, success=False, error=str(e))

async def remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove position (full or partial)."""
    user_id = update.effective_user.id
    
    if not DB_AVAILABLE:
        await update.message.reply_text("⚠️ Database offline.", parse_mode='Markdown')
        if ANALYTICS_AVAILABLE:
            track_command('remove', user_id, success=False, error='db_offline')
        return
    
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
            if ANALYTICS_AVAILABLE:
                track_command('remove', user_id, success=False, error=error_msg)
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
        
        # Track successful remove
        if ANALYTICS_AVAILABLE:
            track_command('remove', user_id, success=True)
        
    except Exception as e:
        logger.error(f"❌ /remove error: {e}")
        await update.message.reply_text("❌ Error removing position.", parse_mode='Markdown')
        
        # Track failed remove
        if ANALYTICS_AVAILABLE:
            track_command('remove', user_id, success=False, error=str(e))

async def sell_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sell position and record realized P&L."""
    user_id = update.effective_user.id
    
    if not DB_AVAILABLE:
        await update.message.reply_text("⚠️ Database offline.", parse_mode='Markdown')
        if ANALYTICS_AVAILABLE:
            track_command('sell', user_id, success=False, error='db_offline')
        return
    
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
            if ANALYTICS_AVAILABLE:
                track_command('sell', user_id, success=False, error=error_msg)
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
        
        # Track successful sell
        if ANALYTICS_AVAILABLE:
            track_command('sell', user_id, success=True)
        
    except Exception as e:
        logger.error(f"❌ /sell error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        await update.message.reply_text("❌ Error executing sale.", parse_mode='Markdown')
        
        # Track failed sell
        if ANALYTICS_AVAILABLE:
            track_command('sell', user_id, success=False, error=str(e))

async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show enriched portfolio summary with realized/unrealized P&L."""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or "User"
    
    if not DB_AVAILABLE:
        await update.message.reply_text("⚠️ Database offline.", parse_mode='Markdown')
        if ANALYTICS_AVAILABLE:
            track_command('summary', user_id, success=False, error='db_offline')
        return
    
    try:
        summary = portfolio_manager.get_enriched_summary(user_id, username)
        
        if summary["num_positions"] == 0:
            await update.message.reply_text(
                "📊 **Portfolio Empty**\n\nUse `/add BTC 0.5 45000` to start tracking!",
                parse_mode='Markdown'
            )
            if ANALYTICS_AVAILABLE:
                track_command('summary', user_id, success=True)
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
        
        if summary["best_performer"]:
            best = summary["best_performer"]
            worst = summary["worst_performer"]
            response += f"\n🏆 **Best performer:** `{best['symbol']}` ({best['pnl_percent']:+.2f}%)\n"
            response += f"📉 **Worst performer:** `{worst['symbol']}` ({worst['pnl_percent']:+.2f}%)\n"
        
        div_score = summary["diversification_score"]
        div_emoji = "🟢" if div_score >= 80 else ("🟡" if div_score >= 50 else "🔴")
        response += f"\n{div_emoji} **Diversification:** {div_score}% ({summary['num_positions']} positions)\n"
        
        response += f"\n_Use `/portfolio` for detailed breakdown_"
        
        await update.message.reply_text(response, parse_mode='Markdown', disable_web_page_preview=True)
        logger.info(f"✅ /summary sent to {user_id}")
        
        # Track successful summary
        if ANALYTICS_AVAILABLE:
            track_command('summary', user_id, success=True)
        
    except Exception as e:
        logger.error(f"❌ /summary error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        await update.message.reply_text("❌ Error generating summary.", parse_mode='Markdown')
        
        # Track failed summary
        if ANALYTICS_AVAILABLE:
            track_command('summary', user_id, success=False, error=str(e))

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show last 5 transactions with enhanced formatting."""
    user_id = update.effective_user.id
    
    if not DB_AVAILABLE:
        await update.message.reply_text("⚠️ Database offline.", parse_mode='Markdown')
        if ANALYTICS_AVAILABLE:
            track_command('history', user_id, success=False, error='db_offline')
        return
        
    try:
        transactions = portfolio_manager.get_transactions(user_id, limit=5)
        if not transactions:
            await update.message.reply_text("📃 No transactions yet.\n\nUse `/add BTC 0.5 45000` to get started!", parse_mode='Markdown')
            if ANALYTICS_AVAILABLE:
                track_command('history', user_id, success=True)
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
            
            if 'pnl' in tx and tx['pnl'] is not None:
                pnl_emoji = "🟢" if tx['pnl'] > 0 else "🔴"
                response += f"\n   {pnl_emoji} P&L: `{tx['pnl']:+,.2f} USD`"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        logger.info(f"✅ /history sent to {user_id}")
        
        # Track successful history
        if ANALYTICS_AVAILABLE:
            track_command('history', user_id, success=True)
        
    except Exception as e:
        logger.error(f"❌ /history error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        await update.message.reply_text("❌ Error loading history.", parse_mode='Markdown')
        
        # Track failed history
        if ANALYTICS_AVAILABLE:
            track_command('history', user_id, success=False, error=str(e))

# ===== PRICE ALERTS COMMANDS WITH TP/SL =====

@check_alert_limit
async def setalert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set TP/SL price alerts for a crypto."""
    user_id = update.effective_user.id
    
    if not DB_AVAILABLE:
        await update.message.reply_text("⚠️ Database offline. Cannot set alert.", parse_mode='Markdown')
        if ANALYTICS_AVAILABLE:
            track_command('setalert', user_id, success=False, error='db_offline')
        return
    
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
    
    if not is_symbol_supported(symbol):
        await update.message.reply_text(
            f"❌ **{symbol} not supported**\n\n"
            "Supported cryptos: BTC, ETH, SOL, BNB, XRP, ADA, AVAX, DOT, MATIC, LINK, UNI, ATOM, LTC, BCH, XLM",
            parse_mode='Markdown'
        )
        return
    
    current_price = get_crypto_price(symbol)
    
    if current_price is None:
        await update.message.reply_text(
            f"⚠️ **Price API Temporarily Unavailable**\n\n"
            f"Cannot fetch current price for **{symbol}** right now.\n"
            f"This is likely a temporary CoinGecko API issue.\n\n"
            f"💡 **Please try again in a few minutes.**",
            parse_mode='Markdown'
        )
        if ANALYTICS_AVAILABLE:
            track_command('setalert', user_id, success=False, error='price_unavailable')
        return
    
    if alert_type == 'tp' and price <= current_price:
        await update.message.reply_text(
            f"⚠️ **Invalid TP**\n\n"
            f"Take Profit must be **above** current price.\n\n"
            f"Current price: `{format_price(current_price)}`\n"
            f"Your TP: `{format_price(price)}`\n\n"
            f"💡 Set a higher price for TP (e.g., `{format_price(current_price * 1.1)}`)",
            parse_mode='Markdown'
        )
        if ANALYTICS_AVAILABLE:
            track_command('setalert', user_id, success=False, error='invalid_tp_price')
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
        if ANALYTICS_AVAILABLE:
            track_command('setalert', user_id, success=False, error='invalid_sl_price')
        return
    
    position = redis_storage.get_position(user_id, symbol)
    warning_msg = ""
    if not position and alert_type == 'sl':
        warning_msg = "\n⚠️ _You don't hold this asset in your portfolio_\n"
    
    existing_alert = redis_storage.get_alert(user_id, symbol)
    if existing_alert:
        if alert_type == 'tp' and existing_alert.get('tp'):
            await update.message.reply_text(
                f"⚠️ **TP Already Exists**\n\n"
                f"**{symbol}** already has a Take Profit at `{format_price(existing_alert['tp'])}`\n\n"
                f"To modify, use: `/removealert {symbol}` first, then set new alert.",
                parse_mode='Markdown'
            )
            if ANALYTICS_AVAILABLE:
                track_command('setalert', user_id, success=False, error='tp_exists')
            return
        
        if alert_type == 'sl' and existing_alert.get('sl'):
            await update.message.reply_text(
                f"⚠️ **SL Already Exists**\n\n"
                f"**{symbol}** already has a Stop Loss at `{format_price(existing_alert['sl'])}`\n\n"
                f"To modify, use: `/removealert {symbol}` first, then set new alert.",
                parse_mode='Markdown'
            )
            if ANALYTICS_AVAILABLE:
                track_command('setalert', user_id, success=False, error='sl_exists')
            return
    
    try:
        tp_value = price if alert_type == 'tp' else None
        sl_value = price if alert_type == 'sl' else None
        
        result = redis_storage.set_alert(user_id, symbol, tp=tp_value, sl=sl_value, update_only=True)
        
        if result["success"]:
            alert = result["alert"]
            
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
            
            # Track successful setalert
            if ANALYTICS_AVAILABLE:
                track_command('setalert', user_id, success=True)
        else:
            await update.message.reply_text(f"❌ {result['message']}", parse_mode='Markdown')
            if ANALYTICS_AVAILABLE:
                track_command('setalert', user_id, success=False, error=result['message'])
    
    except Exception as e:
        logger.error(f"❌ /setalert error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        await update.message.reply_text("❌ Error setting alert.", parse_mode='Markdown')
        
        # Track failed setalert
        if ANALYTICS_AVAILABLE:
            track_command('setalert', user_id, success=False, error=str(e))

async def listalerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all active TP/SL price alerts."""
    user_id = update.effective_user.id
    
    if not DB_AVAILABLE:
        await update.message.reply_text("⚠️ Database offline.", parse_mode='Markdown')
        if ANALYTICS_AVAILABLE:
            track_command('listalerts', user_id, success=False, error='db_offline')
        return
    
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
        
        # Track successful listalerts
        if ANALYTICS_AVAILABLE:
            track_command('listalerts', user_id, success=True)
    
    except Exception as e:
        logger.error(f"❌ /listalerts error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        await update.message.reply_text("❌ Error loading alerts.", parse_mode='Markdown')
        
        # Track failed listalerts
        if ANALYTICS_AVAILABLE:
            track_command('listalerts', user_id, success=False, error=str(e))

async def removealert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove all price alerts (TP and SL) for a crypto."""
    user_id = update.effective_user.id
    
    if not DB_AVAILABLE:
        await update.message.reply_text("⚠️ Database offline.", parse_mode='Markdown')
        if ANALYTICS_AVAILABLE:
            track_command('removealert', user_id, success=False, error='db_offline')
        return
    
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
        alert = redis_storage.get_alert(user_id, symbol)
        
        if not alert:
            await update.message.reply_text(
                f"⚠️ No alert found for **{symbol}**.\n\n"
                f"Use `/listalerts` to see your active alerts.",
                parse_mode='Markdown'
            )
            if ANALYTICS_AVAILABLE:
                track_command('removealert', user_id, success=False, error='alert_not_found')
            return
        
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
            
            # Track successful removealert
            if ANALYTICS_AVAILABLE:
                track_command('removealert', user_id, success=True)
        else:
            await update.message.reply_text("❌ Error removing alert. Please try again.", parse_mode='Markdown')
            if ANALYTICS_AVAILABLE:
                track_command('removealert', user_id, success=False, error='removal_failed')
    
    except Exception as e:
        logger.error(f"❌ /removealert error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        await update.message.reply_text("❌ Error removing alert.", parse_mode='Markdown')
        
        # Track failed removealert
        if ANALYTICS_AVAILABLE:
            track_command('removealert', user_id, success=False, error=str(e))

# ===== AI RECOMMENDATIONS COMMAND (FEATURE 4) =====

@check_recommendation_limit
async def recommend_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Wrapper for AI recommendations handler."""
    user_id = update.effective_user.id
    
    try:
        await recommend_handler_fn(
            update, 
            context, 
            DB_AVAILABLE, 
            portfolio_manager, 
            is_symbol_supported, 
            format_price
        )
        
        # Track successful recommend
        if ANALYTICS_AVAILABLE:
            track_command('recommend', user_id, success=True)
    
    except Exception as e:
        logger.error(f"❌ /recommend error: {e}")
        
        # Track failed recommend
        if ANALYTICS_AVAILABLE:
            track_command('recommend', user_id, success=False, error=str(e))
        raise

# ===== STRIPE PREMIUM SUBSCRIPTION COMMANDS =====

async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /subscribe - Create Stripe checkout session."""
    user_id = update.effective_chat.id
    username = update.effective_user.username
    
    if not STRIPE_AVAILABLE:
        await update.message.reply_text(
            "⚠️ **Premium subscriptions temporarily unavailable**\n\n"
            "Please try again later or contact support.",
            parse_mode='Markdown'
        )
        if ANALYTICS_AVAILABLE:
            track_command('subscribe', user_id, success=False, error='stripe_unavailable')
        return
    
    logger.info(f"💳 /subscribe called by user {user_id} (@{username})")
    
    status = get_subscription_status(user_id)
    
    if status == 'premium':
        await update.message.reply_text(
            "✅ **You're already Premium!**\n\n"
            "Use `/manage` to manage your subscription.",
            parse_mode='Markdown'
        )
        if ANALYTICS_AVAILABLE:
            track_command('subscribe', user_id, success=False, error='already_premium')
        return
    
    result = create_checkout_session(
        user_id=user_id,
        username=username
    )
    
    if result['success']:
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
        
        logger.info(f"✅ Checkout session created for user {user_id}: {result['session_id']}")
        
        # Track successful subscribe click
        if ANALYTICS_AVAILABLE:
            track_command('subscribe', user_id, success=True)
    
    else:
        logger.error(f"❌ Failed to create checkout session: {result['error']}")
        await update.message.reply_text(
            "❌ **Payment setup error**\n\n"
            "Sorry, we couldn't create your payment session. "
            "Please try again later or contact support.\n\n"
            f"Error: {result['error']}",
            parse_mode='Markdown'
        )
        
        # Track failed subscribe
        if ANALYTICS_AVAILABLE:
            track_command('subscribe', user_id, success=False, error=result['error'])

async def manage_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /manage - Manage existing subscription.
    
    Handles 2 scenarios:
    1. Premium via Stripe subscription (shows Stripe details)
    2. Premium manually granted (no Stripe subscription)
    """
    user_id = update.effective_chat.id
    
    if not STRIPE_AVAILABLE:
        await update.message.reply_text(
            "⚠️ **Subscription management temporarily unavailable**\n\n"
            "Please try again later or contact support.",
            parse_mode='Markdown'
        )
        if ANALYTICS_AVAILABLE:
            track_command('manage', user_id, success=False, error='stripe_unavailable')
        return
    
    status = get_subscription_status(user_id)
    
    if status != 'premium':
        await update.message.reply_text(
            "⚠️ **You don't have an active subscription**\n\n"
            "Use `/subscribe` to upgrade to Premium!",
            parse_mode='Markdown'
        )
        if ANALYTICS_AVAILABLE:
            track_command('manage', user_id, success=False, error='not_premium')
        return
    
    # Check if user has Stripe subscription ID
    subscription_id = get_subscription_id(user_id)
    
    if not subscription_id:
        # User is Premium but NO Stripe subscription (manual Premium)
        await update.message.reply_text(
            "✅ **Premium Access Active**\n\n"
            "**Status:** Premium (Manually Granted)\n"
            "**Type:** Administrative Access\n\n"
            "💎 You have full Premium features without a Stripe subscription.\n\n"
            "This typically means:\n"
            "• You're a tester/developer\n"
            "• You received promotional access\n"
            "• Your subscription was manually activated\n\n"
            "📧 For questions, contact support at:\n"
            "contact.sentinellabs@gmail.com",
            parse_mode='Markdown'
        )
        
        # Track successful manage (manual Premium)
        if ANALYTICS_AVAILABLE:
            track_command('manage', user_id, success=True)
        return
    
    # User has Stripe subscription - retrieve details
    sub_result = retrieve_subscription(user_id)
    
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
            "📧 contact.sentinellabs@gmail.com\n\n"
            "_We'll add a self-service portal soon!_"
        )
        
        await update.message.reply_text(message_text, parse_mode='Markdown')
        
        # Track successful manage
        if ANALYTICS_AVAILABLE:
            track_command('manage', user_id, success=True)
    else:
        # Failed to retrieve Stripe subscription
        error_msg = sub_result.get('error', 'unknown')
        logger.warning(f"⚠️ Could not retrieve Stripe subscription for user {user_id}: {error_msg}")
        
        await update.message.reply_text(
            "❌ **Could not retrieve subscription details**\n\n"
            "This may be a temporary issue. Please try again later.\n\n"
            "If the problem persists, contact support at:\n"
            "📧 contact.sentinellabs@gmail.com",
            parse_mode='Markdown'
        )
        
        # Track failed manage
        if ANALYTICS_AVAILABLE:
            track_command('manage', user_id, success=False, error=error_msg)

# ===== GDPR DATA COMMANDS =====

async def mydata_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Export user data (GDPR Right to Access - Art. 15)."""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or "User"
    
    if not DB_AVAILABLE:
        await update.message.reply_text("⚠️ Database offline.", parse_mode='Markdown')
        if ANALYTICS_AVAILABLE:
            track_command('mydata', user_id, success=False, error='db_offline')
        return
    
    try:
        profile = redis_storage.get_user_profile(user_id) or {"user_id": user_id, "username": username}
        positions = redis_storage.get_all_positions(user_id)
        alerts = redis_storage.get_alerts(user_id)
        transactions = redis_storage.get_transactions(user_id, limit=100)
        realized_pnl = redis_storage.get_realized_pnl(user_id)
        
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
                "contact": "contact.sentinellabs@gmail.com"
            }
        }
        
        json_output = json.dumps(data_export, indent=2, ensure_ascii=False)
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
        
        # Track successful mydata
        if ANALYTICS_AVAILABLE:
            track_command('mydata', user_id, success=True)
        
    except Exception as e:
        logger.error(f"❌ /mydata error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        await update.message.reply_text("❌ Error exporting data.", parse_mode='Markdown')
        
        # Track failed mydata
        if ANALYTICS_AVAILABLE:
            track_command('mydata', user_id, success=False, error=str(e))

async def deletedata_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete all user data (GDPR Right to Erasure - Art. 17)."""
    user_id = update.effective_user.id
    
    if not DB_AVAILABLE:
        await update.message.reply_text("⚠️ Database offline.", parse_mode='Markdown')
        if ANALYTICS_AVAILABLE:
            track_command('deletedata', user_id, success=False, error='db_offline')
        return
    
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
    
    if len(context.args) == 0:
        await update.message.reply_text(confirmation_text, parse_mode='Markdown')
        if ANALYTICS_AVAILABLE:
            track_command('deletedata', user_id, success=False, error='awaiting_confirmation')
        return
    
    if len(context.args) == 1 and context.args[0].upper() == "CONFIRM":
        try:
            positions = redis_storage.get_all_positions(user_id)
            for symbol in positions.keys():
                redis_storage.delete_position(user_id, symbol)
            
            alerts = redis_storage.get_alerts(user_id)
            for symbol in alerts.keys():
                redis_storage.remove_alert(user_id, symbol)
            
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
            
            # Track successful deletedata
            if ANALYTICS_AVAILABLE:
                track_command('deletedata', user_id, success=True)
            
        except Exception as e:
            logger.error(f"❌ /deletedata error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            await update.message.reply_text("❌ Error deleting data. Please try again.", parse_mode='Markdown')
            
            # Track failed deletedata
            if ANALYTICS_AVAILABLE:
                track_command('deletedata', user_id, success=False, error=str(e))
    else:
        await update.message.reply_text(
            "⚠️ Invalid confirmation.\n\nUse: `/deletedata CONFIRM`",
            parse_mode='Markdown'
        )
        if ANALYTICS_AVAILABLE:
            track_command('deletedata', user_id, success=False, error='invalid_confirmation')

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
    return {"status": "ok", "message": "Sentiment Trading Bot Running", "db": DB_AVAILABLE, "stripe": STRIPE_AVAILABLE, "analytics": ANALYTICS_AVAILABLE}

@app.get("/health")
async def health():
    return {
        "status": "ok", 
        "db_connected": DB_AVAILABLE,
        "stripe_enabled": STRIPE_AVAILABLE,
        "analytics_enabled": ANALYTICS_AVAILABLE,
        "features": {
            "sentiment": "online",
            "portfolio": "online" if DB_AVAILABLE else "offline",
            "alerts": "online" if DB_AVAILABLE else "offline",
            "premium": "online" if STRIPE_AVAILABLE else "offline",
            "analytics": "online" if ANALYTICS_AVAILABLE else "offline"
        }
    }

# LEGAL PAGES ROUTES
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

# ANALYTICS DASHBOARD ROUTES (Phase 1.5)
@app.get("/dashboard", response_class=HTMLResponse)
async def analytics_dashboard():
    """Serve Analytics Dashboard."""
    try:
        dashboard_dir = os.path.join(os.path.dirname(__file__), 'dashboard')
        dashboard_path = os.path.join(dashboard_dir, 'index.html')
        with open(dashboard_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Analytics Dashboard</h1><p>Dashboard not found</p>"

@app.get("/dashboard/styles.css")
async def dashboard_styles():
    """Serve dashboard CSS."""
    try:
        dashboard_dir = os.path.join(os.path.dirname(__file__), 'dashboard')
        css_path = os.path.join(dashboard_dir, 'styles.css')
        with open(css_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return Response(content=content, media_type="text/css")
    except FileNotFoundError:
        return Response(content="/* CSS not found */", media_type="text/css")

@app.get("/dashboard/dashboard.js")
async def dashboard_script():
    """Serve dashboard JavaScript."""
    try:
        dashboard_dir = os.path.join(os.path.dirname(__file__), 'dashboard')
        js_path = os.path.join(dashboard_dir, 'dashboard.js')
        with open(js_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return Response(content=content, media_type="application/javascript")
    except FileNotFoundError:
        return Response(content="// JS not found", media_type="application/javascript")

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
    
    application.add_handler(CommandHandler("setalert", setalert_command))
    application.add_handler(CommandHandler("listalerts", listalerts_command))
    application.add_handler(CommandHandler("removealert", removealert_command))
    
    application.add_handler(CommandHandler("recommend", recommend_command))
    
    application.add_handler(CommandHandler("subscribe", subscribe_command))
    application.add_handler(CommandHandler("manage", manage_command))
    
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
    
    if STRIPE_AVAILABLE:
        logger.info("✅ Stripe integration enabled")
    else:
        logger.warning("⚠️ Stripe integration disabled")
    
    if TIER_SYSTEM_AVAILABLE:
        logger.info("✅ Tier management system enabled (Free/Premium limits active)")
    else:
        logger.warning("⚠️ Tier management system disabled (all features unlimited)")
    
    # Initialize Analytics System (Phase 1.5)
    if ANALYTICS_AVAILABLE:
        analytics_init = init_analytics()
        if analytics_init:
            logger.info("✅ Analytics system initialized")
        else:
            logger.warning("⚠️ Analytics system failed to initialize")
    else:
        logger.warning("⚠️ Analytics system not available")
    
    await setup_application()
    logger.info("✅ Server ready")

@app.on_event("shutdown")
async def shutdown():
    if application:
        await application.stop()
        await application.shutdown()
