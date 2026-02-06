#!/usr/bin/env python3
"""
Telegram Bot with Webhook support for Railway deployment.
Uses FastAPI for native async support.
"""
import os
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from telegram import Update
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

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_status = "✅ Online" if DB_AVAILABLE else "⚠️ Offline"
    
    welcome_text = f"""👋 **Welcome {user.first_name}!**

🤖 **CryptoSentinel AI**
Your AI crypto copilot for:
• Sentiment analysis
• Portfolio management
• Price alerts
• P&L tracking

⚠️ **IMPORTANT DISCLAIMER**

CryptoSentinel AI provides INFORMATIONAL ALERTS and AI-powered analysis ONLY.

🚫 This is NOT financial, investment, or trading advice.
🚫 We do NOT manage your funds or execute trades.
✅ You are solely responsible for your trading decisions.

⚠️ **RISKS:**
• Cryptocurrency markets are highly volatile
• You may lose your ENTIRE investment
• Past performance does NOT guarantee future results
• AI recommendations are probabilistic, NOT guaranteed

**NEVER invest more than you can afford to lose.**

━━━━━━━━━━━━━━━━━━
🎯 **SENTIMENT ANALYSIS**

• `/analyze <text>`
  AI analysis of crypto news or ideas.
  _Example: `/analyze Bitcoin hits new ATH after ETF approval`_

• **Send an article link**
  Bot scrapes and analyzes automatically.

• **Send long text** (30+ chars)
  Automatic analysis without command.

━━━━━━━━━━━━━━━━━━
💼 **PORTFOLIO**

• `/portfolio` – View your positions (quantities, prices, P&L)

• `/add <SYMBOL> <quantity> <price>`
  _Example: `/add BTC 0.5 45000`_

• `/remove <SYMBOL> [quantity]`
  _Example: `/remove BTC`_ (full removal)
  _Example: `/remove BTC 0.5`_ (partial removal)

• `/sell <SYMBOL> <quantity> <price>`
  Sell and record **realized P&L**.
  _Example: `/sell BTC 0.5 75000`_

• `/summary` – Global overview (realized + unrealized, best/worst)

• `/history` – Last 5 transactions

━━━━━━━━━━━━━━━━━━
🔔 **PRICE ALERTS (TP/SL)**

• `/setalert <SYMBOL> tp <price>` - Set Take Profit
  _Example: `/setalert BTC tp 80000`_

• `/setalert <SYMBOL> sl <price>` - Set Stop Loss
  _Example: `/setalert BTC sl 70000`_

• `/listalerts` – View your active TP/SL alerts

• `/removealert <SYMBOL>` – Delete all alerts for a symbol
  _Example: `/removealert BTC`_

━━━━━━━━━━━━━━━━━━
🤖 **AI RECOMMENDATIONS**

• `/recommend` – Get personalized AI trading insights
  Based on your portfolio and market sentiment.

━━━━━━━━━━━━━━━━━━
🔒 **YOUR DATA & PRIVACY**

• `/mydata` – Export all your data (GDPR)
• `/deletedata` – Permanently delete your account

We respect your privacy. Read our:
📄 [Terms of Service](https://github.com/theofanget07/sentiment-trading-bot/blob/main/TERMS_OF_SERVICE.md)
🔐 [Privacy Policy](https://github.com/theofanget07/sentiment-trading-bot/blob/main/PRIVACY_POLICY.md)

━━━━━━━━━━━━━━━━━━
📈 **SUPPORTED CRYPTOS**

BTC, ETH, SOL, BNB, XRP, ADA, AVAX, DOT, MATIC, LINK, UNI, ATOM, LTC, BCH, XLM

━━━━━━━━━━━━━━━━━━
ℹ️ **Data Sources**

• Crypto prices: [CoinGecko API](https://www.coingecko.com/en/api)
• AI analysis: [Perplexity AI](https://www.perplexity.ai)

_Prices may be delayed or inaccurate. We do NOT guarantee accuracy._

━━━━━━━━━━━━━━━━━━

**By using this bot, you agree to our Terms of Service and Privacy Policy.**

_Type `/help` for detailed guide_
"""
    await update.message.reply_text(welcome_text, parse_mode='Markdown', disable_web_page_preview=True)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """📚 **Complete Guide - Sentiment Trading Bot**

━━━━━━━━━━━━━━━━━━
🔍 **1. SENTIMENT ANALYSIS**

The bot uses Perplexity AI to analyze crypto sentiment (BULLISH/BEARISH/NEUTRAL) with confidence score.

**Analysis methods:**
• `/analyze <text>` - Analyze provided text
• Send a link - Bot scrapes article automatically
• Send long text - Auto-detection (30+ chars)

**Example result:**
🚀 **BULLISH** (89%)
💡 "Bitcoin shows strong upward momentum with ETF approval..."

━━━━━━━━━━━━━━━━━━
💼 **2. PORTFOLIO MANAGEMENT**

**Add position:**
`/add BTC 1 45000`
→ Adds 1 BTC bought at $45,000
→ If you already hold BTC, recalculates average price

**View portfolio:**
`/portfolio`
→ Displays all positions with:
  • Quantity held
  • Average buy price
  • Current price (real-time)
  • Current value
  • P&L in $ and %

**Remove position (full):**
`/remove BTC`
→ Completely removes BTC position

**Remove position (partial):**
`/remove BTC 0.3`
→ Removes 0.3 BTC, keeps the rest

**Sell position (with P&L tracking):**
`/sell BTC 0.5 75000`
→ Sells 0.5 BTC at $75,000
→ Records realized P&L
→ Keeps remaining position if partial sale

**Global summary:**
`/summary`
→ Shows total P&L across portfolio
→ Realized vs unrealized P&L
→ Best/worst performer
→ Diversification score

**History:**
`/history`
→ Last 5 transactions (BUY/SELL/REMOVE)

━━━━━━━━━━━━━━━━━━
🔔 **3. PRICE ALERTS (TP/SL)**

**Set Take Profit:**
`/setalert BTC tp 80000`
→ Get notified when BTC reaches $80,000 (above current price)

**Set Stop Loss:**
`/setalert BTC sl 70000`
→ Get notified when BTC drops to $70,000 (below current price)

**Set both TP and SL independently:**
`/setalert BTC tp 80000`
`/setalert BTC sl 70000`
→ You can have both active for the same crypto

**View active alerts:**
`/listalerts`
→ Shows all your TP/SL alerts with:
  • Current price
  • Alert price
  • Status (waiting/reached)
  • % to target

**Remove all alerts for a crypto:**
`/removealert BTC`
→ Deletes both TP and SL for BTC

**Validations:**
• TP must be **above** current price
• SL must be **below** current price
• Cannot set duplicate TP or SL (must remove first)

**How it works:**
• Automated monitoring via Celery worker
• Real-time prices from CoinGecko
• Alerts checked every 15 minutes
• Alert triggers once, then auto-deletes

━━━━━━━━━━━━━━━━━━
🤖 **4. AI RECOMMENDATIONS**

`/recommend`
→ Get personalized trading insights based on:
  • Your current portfolio composition
  • Market sentiment analysis
  • Risk assessment

⚠️ **Disclaimer**: AI recommendations are for informational purposes ONLY and do NOT constitute financial advice. Always conduct your own research (DYOR).

━━━━━━━━━━━━━━━━━━
🔒 **5. YOUR DATA & PRIVACY (GDPR)**

**Export your data:**
`/mydata`
→ Download all your data as JSON
→ Includes: portfolio, alerts, transactions

**Delete your account:**
`/deletedata`
→ Permanently delete ALL your data
→ Cannot be undone!

**Auto-deletion:**
→ Inactive accounts are automatically deleted after 180 days

**Your rights:**
• Right to access (GDPR Art. 15)
• Right to erasure (GDPR Art. 17)
• Right to data portability (GDPR Art. 20)

Read more: [Privacy Policy](https://github.com/theofanget07/sentiment-trading-bot/blob/main/PRIVACY_POLICY.md)

━━━━━━━━━━━━━━━━━━
🚀 **AVAILABLE CRYPTOS**

Bitcoin (BTC), Ethereum (ETH), Solana (SOL), Binance Coin (BNB), Ripple (XRP), Cardano (ADA), Avalanche (AVAX), Polkadot (DOT), Polygon (MATIC), Chainlink (LINK), Uniswap (UNI), Cosmos (ATOM), Litecoin (LTC), Bitcoin Cash (BCH), Stellar (XLM)

━━━━━━━━━━━━━━━━━━
🛠️ **TECH INFO**

• **Storage:** Redis (ultra-fast)
• **Prices:** CoinGecko API (real-time)
• **AI:** Perplexity API (sentiment analysis)
• **Automation:** Celery (alerts + insights)
• **Hosting:** Railway (24/7)

━━━━━━━━━━━━━━━━━━
⚠️ **LEGAL DISCLAIMER**

This bot provides informational services ONLY.
• NOT financial advice
• NOT investment recommendations
• Trading crypto involves substantial risk of loss
• You may lose your entire investment
• Always consult a licensed financial advisor

[Terms of Service](https://github.com/theofanget07/sentiment-trading-bot/blob/main/TERMS_OF_SERVICE.md)

_Back to menu: `/start`_
"""
    await update.message.reply_text(help_text, parse_mode='Markdown', disable_web_page_preview=True)

async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = ' '.join(context.args)
    if not user_text or len(user_text) < 10:
        await update.message.reply_text(
            "⚠️ Please provide text to analyze.\n\n"
            "**Example:** `/analyze Bitcoin surges as ETFs see record inflows`",
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
            response += "To add positions, use:\n"
            response += "`/add BTC 0.5 45000`\n\n"
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
            response += "\n\n_Prices powered by [CoinGecko API](https://www.coingecko.com/en/api)_"
        
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
            "**Example:** `/add BTC 0.5 45000`",
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
            "`/remove BTC 0.5` - Remove 0.5 BTC only",
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
            "**Example:** `/sell BTC 0.5 75000`\n"
            "Sells 0.5 BTC at $75,000 and records realized P&L",
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
                "📊 **Portfolio Empty**\n\nUse `/add` to start.",
                parse_mode='Markdown'
            )
            return
        
        total_pnl = summary["total_pnl"]
        overall_emoji = "🚀" if total_pnl > 0 else "📉"
        
        response = f"{overall_emoji} **PORTFOLIO ANALYTICS**\n"
        response += f"\n━━━━━━━━━━━━━━━━━━\n"
        response += f"📊 **GLOBAL PERFORMANCE**\n"
        response += f"━━━━━━━━━━━━━━━━━━\n\n"
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
        response += "\n\n_Prices powered by [CoinGecko API](https://www.coingecko.com/en/api)_"
        
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
            await update.message.reply_text("📃 No transactions yet.", parse_mode='Markdown')
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
            "`/setalert BTC tp 80000` - Set Take Profit at $80,000\n"
            "`/setalert BTC sl 70000` - Set Stop Loss at $70,000\n\n"
            "💡 **You can set both TP and SL independently**",
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
    
    # ✅ AMÉLIORATION: Vérifier le support du symbole AVANT d'appeler l'API
    if not is_symbol_supported(symbol):
        await update.message.reply_text(
            f"❌ **{symbol} not supported**\n\n"
            "Supported cryptos: BTC, ETH, SOL, BNB, XRP, ADA, AVAX, DOT, MATIC, LINK, UNI, ATOM, LTC, BCH, XLM",
            parse_mode='Markdown'
        )
        return
    
    # Fetch current price (with retry logic from crypto_prices.py)
    current_price = get_crypto_price(symbol)
    
    # ✅ AMÉLIORATION: Message distinct si API échoue malgré les retries
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
            response += "Set one with:\n"
            response += "`/setalert BTC tp 80000`\n"
            response += "`/setalert BTC sl 70000`"
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
            response += "\n\n_Prices powered by [CoinGecko API](https://www.coingecko.com/en/api)_"
        
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
            "**Example:** `/removealert BTC`\n"
            "This will remove both TP and SL alerts for BTC",
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
        import json
        data_export = {
            "profile": profile,
            "positions": positions,
            "alerts": alerts,
            "transactions": transactions,
            "realized_pnl": realized_pnl,
            "export_date": datetime.utcnow().isoformat(),
            "gdpr_info": {
                "right": "GDPR Article 15 - Right to Access",
                "controller": "Theo Fanget, Rue du Crêt 7, 1003 Lausanne, Switzerland"
            }
        }
        
        # Format as readable JSON
        json_output = json.dumps(data_export, indent=2, ensure_ascii=False)
        
        # Send as file
        from io import BytesIO
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
                "📄 [Privacy Policy](https://github.com/theofanget07/sentiment-trading-bot/blob/main/PRIVACY_POLICY.md)"
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

@app.get("/")
async def root():
    return {"status": "ok", "message": "Sentiment Trading Bot Running", "db": DB_AVAILABLE}

@app.get("/health")
async def health():
    # Return 200 even if DB is down, to prevent Railway from killing the bot
    return {
        "status": "ok", 
        "db_connected": DB_AVAILABLE,
        "features": {
            "sentiment": "online",
            "portfolio": "online" if DB_AVAILABLE else "offline",
            "alerts": "online" if DB_AVAILABLE else "offline"
        }
    }

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
    
    await setup_application()
    logger.info("✅ Server ready")

@app.on_event("shutdown")
async def shutdown():
    if application:
        await application.stop()
        await application.shutdown()
