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

# Fix: Use absolute import for Railway deployment
try:
    from backend.portfolio_manager import portfolio_manager
except ImportError:
    # Fallback for local development
    from portfolio_manager import portfolio_manager

try:
    from backend.crypto_prices import format_price, get_crypto_price
except ImportError:
    from crypto_prices import format_price, get_crypto_price

# Import ASYNC database init function
try:
    from backend.database import init_db_async
except ImportError:
    from database import init_db_async

try:
    from article_scraper import extract_article, extract_urls
except ImportError:
    def extract_article(url): return None
    def extract_urls(text): return []

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
    welcome_text = f"""
🤖 **Sentiment Trading Bot** - Welcome {user.first_name}!

I'm your AI-powered crypto sentiment analyzer + portfolio manager.

**📊 Portfolio Commands:**
/portfolio - View your holdings
/add <symbol> <qty> <price> - Add position
/remove <symbol> - Remove position
/summary - Portfolio summary with P&L
/history - Transaction history

**📈 Analysis Commands:**
/analyze <text> - Analyze crypto sentiment
/help - Get help

**Examples:**
`/add BTC 0.5 45000`
`/remove ETH`
`/analyze Bitcoin hits new ATH`

**Deployed on Railway** - Running 24/7 🚀
"""
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📚 **Help - Sentiment Trading Bot**

**Portfolio Management:**
• `/portfolio` - View your holdings
• `/add BTC 0.5 45000` - Add position (symbol, quantity, price)
• `/remove BTC` - Remove entire position
• `/summary` - See total P&L with current prices
• `/history` - View last 10 transactions

**Sentiment Analysis:**
• `/analyze <text>` - Analyze crypto news
• Send me a URL - I'll extract and analyze
• Send long text - Auto-analysis

**Supported Cryptos:**
BTC, ETH, SOL, BNB, XRP, ADA, AVAX, DOT, MATIC, LINK, UNI, ATOM, LTC, BCH, XLM

_Powered by Perplexity AI + CoinGecko_
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

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
            
            for symbol, pos in portfolio["positions"].items():
                qty = pos["quantity"]
                avg_price = pos["avg_price"]
                current_price = pos["current_price"]
                current_value = pos["current_value"]
                pnl_usd = pos["pnl_usd"]
                pnl_percent = pos["pnl_percent"]
                
                # Choose emoji based on P&L
                pnl_emoji = "🟢" if pnl_percent > 0 else ("🔴" if pnl_percent < 0 else "⚪")
                
                response += f"\n**{symbol}** {pnl_emoji}\n"
                response += f"  • Quantity: `{qty:.8g}`\n"
                response += f"  • Avg Price: `{format_price(avg_price)}`\n"
                response += f"  • Current: `{format_price(current_price)}`\n"
                response += f"  • Value: `{format_price(current_value)}`\n"
                response += f"  • P&L: `{pnl_usd:+,.2f} USD ({pnl_percent:+.2f}%)`"
            
            response += f"\n\n**Total Value:** `{format_price(portfolio['total_current_value'])}`"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        logger.info(f"✅ /portfolio response sent to {user_id}")
        
    except Exception as e:
        logger.error(f"❌ /portfolio error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        await update.message.reply_text(
            "❌ **Error**\n\nSomething went wrong. Please try again.",
            parse_mode='Markdown'
        )

async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a crypto position to portfolio.
    
    Usage: /add <symbol> <quantity> <price>
    Example: /add BTC 0.5 45000
    """
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    # Validate arguments
    if len(context.args) != 3:
        await update.message.reply_text(
            "⚠️ **Usage:** `/add <symbol> <quantity> <price>`\n\n"
            "**Example:** `/add BTC 0.5 45000`\n\n"
            "This will add 0.5 BTC bought at $45,000 to your portfolio.",
            parse_mode='Markdown'
        )
        return
    
    symbol = context.args[0].upper()
    
    try:
        quantity = float(context.args[1])
        price = float(context.args[2])
    except ValueError:
        await update.message.reply_text(
            "❌ **Invalid input**\n\n"
            "Quantity and price must be numbers.\n\n"
            "**Example:** `/add BTC 0.5 45000`",
            parse_mode='Markdown'
        )
        return
    
    # Validate positive values
    if quantity <= 0 or price <= 0:
        await update.message.reply_text(
            "❌ Quantity and price must be positive numbers.",
            parse_mode='Markdown'
        )
        return
    
    try:
        # Add position
        result = portfolio_manager.add_position(user_id, symbol, quantity, price, username)
        
        # Get current market price for comparison
        current_price = get_crypto_price(symbol)
        
        response = f"✅ **Position {result['action'].capitalize()}**\n\n"
        response += f"**{symbol}**\n"
        response += f"  • Quantity: `{result['quantity']:.8g}`\n"
        response += f"  • Avg Price: `{format_price(result['avg_price'])}`\n"
        response += f"  • Total Invested: `{format_price(result['quantity'] * result['avg_price'])}`\n"
        
        if current_price:
            current_value = result['quantity'] * current_price
            pnl_usd = current_value - (result['quantity'] * result['avg_price'])
            pnl_percent = ((current_price - result['avg_price']) / result['avg_price']) * 100
            
            response += f"\n📊 **Current Status:**\n"
            response += f"  • Market Price: `{format_price(current_price)}`\n"
            response += f"  • Current Value: `{format_price(current_value)}`\n"
            response += f"  • P&L: `{pnl_usd:+,.2f} USD ({pnl_percent:+.2f}%)`"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        logger.info(f"✅ /add {symbol} for user {user_id} - {result['action']}")
        
    except Exception as e:
        logger.error(f"❌ /add error: {e}")
        await update.message.reply_text(
            f"❌ **Error adding position**\n\n"
            f"Make sure `{symbol}` is a supported crypto.\n\n"
            f"**Supported:** BTC, ETH, SOL, BNB, XRP, ADA, AVAX, DOT, MATIC, LINK, UNI, ATOM, LTC, BCH, XLM",
            parse_mode='Markdown'
        )

async def remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a crypto position from portfolio.
    
    Usage: /remove <symbol>
    Example: /remove BTC
    """
    user_id = update.effective_user.id
    
    # Validate arguments
    if len(context.args) != 1:
        await update.message.reply_text(
            "⚠️ **Usage:** `/remove <symbol>`\n\n"
            "**Example:** `/remove BTC`\n\n"
            "This will remove your entire BTC position.",
            parse_mode='Markdown'
        )
        return
    
    symbol = context.args[0].upper()
    
    try:
        # Remove position
        success = portfolio_manager.remove_position(user_id, symbol)
        
        if success:
            response = f"✅ **Position Removed**\n\n"
            response += f"`{symbol}` has been removed from your portfolio.\n\n"
            response += "Use `/portfolio` to see your updated holdings."
        else:
            response = f"⚠️ **Position Not Found**\n\n"
            response += f"You don't have a `{symbol}` position in your portfolio.\n\n"
            response += "Use `/portfolio` to see your current holdings."
        
        await update.message.reply_text(response, parse_mode='Markdown')
        logger.info(f"✅ /remove {symbol} for user {user_id} - {'success' if success else 'not found'}")
        
    except Exception as e:
        logger.error(f"❌ /remove error: {e}")
        await update.message.reply_text(
            "❌ **Error removing position**\n\nPlease try again.",
            parse_mode='Markdown'
        )

async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show portfolio summary with total P&L."""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or "User"
    
    logger.info(f"📊 /summary called by user {user_id}")
    
    try:
        # Get portfolio with current prices
        portfolio = portfolio_manager.get_portfolio_with_prices(user_id, username)
        
        if not portfolio["positions"]:
            await update.message.reply_text(
                "📊 **Portfolio Summary**\n\n"
                "_Your portfolio is empty._\n\n"
                "Use `/add` to start tracking your crypto positions!",
                parse_mode='Markdown'
            )
            return
        
        # Build summary
        total_invested = portfolio["total_invested"]
        total_current = portfolio["total_current_value"]
        total_pnl = portfolio["total_pnl_usd"]
        total_pnl_pct = portfolio["total_pnl_percent"]
        
        # Overall emoji
        overall_emoji = "🚀" if total_pnl > 0 else ("📉" if total_pnl < 0 else "➡️")
        
        response = f"{overall_emoji} **Portfolio Summary**\n"
        response += f"━━━━━━━━━━━━━━━━━━\n"
        
        # Position breakdown
        response += f"**💼 Positions:** {len(portfolio['positions'])}\n"
        
        # Top 3 gainers/losers
        sorted_positions = sorted(
            portfolio["positions"].items(),
            key=lambda x: x[1]["pnl_percent"],
            reverse=True
        )
        
        if len(sorted_positions) > 0:
            top = sorted_positions[0]
            response += f"**🏆 Top:** `{top[0]}` ({top[1]['pnl_percent']:+.2f}%)\n"
        
        if len(sorted_positions) > 1:
            worst = sorted_positions[-1]
            response += f"**📉 Worst:** `{worst[0]}` ({worst[1]['pnl_percent']:+.2f}%)\n"
        
        # Total stats
        response += f"\n**💰 Total Stats:**\n"
        response += f"• Invested: `{format_price(total_invested)}`\n"
        response += f"• Current: `{format_price(total_current)}`\n"
        response += f"• **P&L: `{total_pnl:+,.2f} USD ({total_pnl_pct:+.2f}%)`**\n"
        response += f"\n_Prices via CoinGecko (cached 5 min)_"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        logger.info(f"✅ /summary sent to user {user_id}")
        
    except Exception as e:
        logger.error(f"❌ /summary error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        await update.message.reply_text(
            "❌ **Error generating summary**\n\nPlease try again.",
            parse_mode='Markdown'
        )

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show transaction history (last 10)."""
    user_id = update.effective_user.id
    
    logger.info(f"📃 /history called by user {user_id}")
    
    try:
        # Get transactions
        transactions = portfolio_manager.get_transactions(user_id, limit=10)
        
        if not transactions:
            await update.message.reply_text(
                "📃 **Transaction History**\n\n"
                "_No transactions yet._\n\n"
                "Use `/add` to start tracking your trades!",
                parse_mode='Markdown'
            )
            return
        
        response = "📃 **Recent Transactions**\n"
        
        for tx in transactions:
            # Parse timestamp
            from datetime import datetime
            ts = datetime.fromisoformat(tx["timestamp"].replace('Z', '+00:00'))
            date_str = ts.strftime("%b %d, %H:%M")
            
            action = tx["action"]
            action_emoji = {"BUY": "🟫", "SELL": "🟫", "REMOVE": "🗑"}.get(action, "➡️")
            
            response += f"\n{action_emoji} **{action}** `{tx['symbol']}`\n"
            response += f"  {date_str} • {tx['quantity']:.8g} @ {format_price(tx['price'])}\n"
            response += f"  Total: `{format_price(tx['total_usd'])}`"
        
        response += f"\n\n_Last {len(transactions)} transaction(s)_"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        logger.info(f"✅ /history sent to user {user_id}")
        
    except Exception as e:
        logger.error(f"❌ /history error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        await update.message.reply_text(
            "❌ **Error loading history**\n\nPlease try again.",
            parse_mode='Markdown'
        )

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

_Powered by Perplexity AI_
"""
        await scraping_msg.delete()
        await update.message.reply_text(response, parse_mode='Markdown')
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

_Powered by Perplexity AI_
"""
        await analyzing_msg.delete()
        await update.message.reply_text(response, parse_mode='Markdown')
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
        await update.message.reply_text(
            f"💬 You said: _{user_message}_\n\nUse `/analyze` for sentiment analysis!",
            parse_mode='Markdown'
        )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Bot error: {context.error}")
    import traceback
    logger.error(''.join(traceback.format_exception(None, context.error, context.error.__traceback__)))

# Root endpoint for health checks
@app.get("/")
async def root():
    return {"status": "ok", "message": "Sentiment Trading Bot Running"}

@app.get("/health")
async def health():
    return {"status": "ok", "mode": "webhook", "storage": "postgresql+json_fallback", "features": ["sentiment", "portfolio", "pnl"]}

# SIMPLIFIED WEBHOOK ENDPOINT (No dynamic path param)
@app.post("/webhook")
async def webhook(request: Request):
    """Handle incoming Telegram updates via simple webhook path."""
    try:
        # Log that we received a request (for debugging)
        logger.info("📩 Webhook request received")
        
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return Response(status_code=500)

@app.get("/webhook")
async def webhook_check():
    """Simple GET check for webhook endpoint"""
    return {"status": "ok", "method": "GET", "endpoint": "/webhook"}

# Catch-all for debugging 404s
@app.api_route("/{path_name:path}", methods=["GET", "POST"])
async def catch_all(request: Request, path_name: str):
    logger.warning(f"⚠️ Unhandled path accessed: {path_name}")
    return {"status": "error", "message": f"Path {path_name} not found"}

async def setup_application():
    """Initialize the Telegram application."""
    global application
    
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not found!")
        raise ValueError("TELEGRAM_BOT_TOKEN required")
    
    logger.info("🔧 Building Telegram application...")
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add handlers
    logger.info("📌 Registering command handlers...")
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("analyze", analyze_command))
    
    # Portfolio commands
    application.add_handler(CommandHandler("portfolio", portfolio_command))
    application.add_handler(CommandHandler("add", add_command))
    application.add_handler(CommandHandler("remove", remove_command))
    application.add_handler(CommandHandler("summary", summary_command))
    application.add_handler(CommandHandler("history", history_command))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)
    
    logger.info("✅ Handlers registered: /start /help /analyze /portfolio /add /remove /summary /history")
    
    # Initialize application
    await application.initialize()
    await application.start()
    
    # Set webhook using the SIMPLIFIED path
    if WEBHOOK_URL:
        # Remove trailing slash if present
        clean_webhook_url = WEBHOOK_URL.rstrip('/')
        webhook_endpoint = f"{clean_webhook_url}/webhook"
        
        logger.info(f"🔗 Setting webhook to SIMPLIFIED URL: {webhook_endpoint}")
        await application.bot.set_webhook(url=webhook_endpoint)
        logger.info("✅ Webhook configured")
    
    logger.info("🤖 Bot ready with PostgreSQL + JSON fallback")

@app.on_event("startup")
async def startup():
    """Run on application startup."""
    logger.info("🚀 FastAPI startup - PostgreSQL + JSON fallback mode")
    
    # Create PostgreSQL tables asynchronously (non-blocking)
    try:
        logger.info("🔨 Initializing database tables (async)...")
        success = await init_db_async()
        if success:
            logger.info("✅ PostgreSQL tables ready - portfolio will use database")
        else:
            logger.warning("⚠️ PostgreSQL init failed - falling back to JSON storage")
    except Exception as e:
        logger.warning(f"⚠️ Database initialization error: {e}")
        logger.info("📁 Continuing with JSON storage fallback")
    
    await setup_application()
    logger.info("✅ Server ready")

@app.on_event("shutdown")
async def shutdown():
    """Run on application shutdown."""
    if application:
        await application.stop()
        await application.shutdown()
    logger.info("🛑 Bot stopped")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)