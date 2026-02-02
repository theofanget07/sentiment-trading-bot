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

I'm your AI-powered crypto sentiment analyzer powered by Perplexity AI.

**Available commands:**
/start - Show this message
/help - Get help
/analyze <text> - Analyze crypto news sentiment
/portfolio - View your crypto holdings

**NEW! 🔥 URL Support:**
Send me any crypto news article URL and I'll automatically extract and analyze it!

**Examples:**
`/analyze Bitcoin hits new ATH as institutions buy`

Or just paste a URL:
`https://coindesk.com/markets/bitcoin-rally`

**Deployed on Railway** - Running 24/7 🚀
"""
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📚 **Help - Sentiment Trading Bot**

**How to use:**
1. Send me crypto news text
2. Or send me a URL from CoinDesk, CoinTelegraph, etc.
3. Or use `/analyze <your text or URL>`
4. I'll analyze sentiment with Perplexity AI

**Commands:**
/start - Welcome message
/help - This help
/analyze - Analyze sentiment
/portfolio - View your holdings
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = ' '.join(context.args)
    if not user_text or len(user_text) < 10:
        await update.message.reply_text(
            "⚠️ Please provide text to analyze.\\n\\n"
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
    """Display user's crypto portfolio holdings."""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or "User"
    
    logger.info(f"💼 /portfolio called by user {user_id} (@{username})")
    
    try:
        # Get portfolio from JSON storage
        portfolio = portfolio_manager.get_portfolio(user_id, username)
        
        response = "💼 **Your Crypto Portfolio**\\n\\n"
        
        if not portfolio["positions"]:
            response += "_Your portfolio is empty._\\n\\n"
            response += "To add positions, use:\\n"
            response += "`/add BTC 0.01 98000`\\n"
        else:
            for symbol, pos in portfolio["positions"].items():
                qty = pos["quantity"]
                price = pos["avg_price"]
                value = qty * price
                response += f"**{symbol}**\\n"
                response += f"  • Quantity: `{qty}`\\n"
                response += f"  • Avg Price: `${price:,.2f}`\\n"
                response += f"  • Value: `${value:,.2f}`\\n\\n"
            
            response += f"**Total Value:** `${portfolio['total_value_usd']:,.2f}`"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        logger.info(f"✅ /portfolio response sent to {user_id}")
        
    except Exception as e:
        logger.error(f"❌ /portfolio error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        await update.message.reply_text(
            "❌ **Error**\\n\\nSomething went wrong. Please try again.",
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
            f"💬 You said: _{user_message}_\\n\\nUse `/analyze` for sentiment analysis!",
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
    return {"status": "ok", "mode": "webhook", "storage": "json"}

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
    application.add_handler(CommandHandler("portfolio", portfolio_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)
    
    logger.info("✅ Handlers registered: /start /help /analyze /portfolio")
    
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
    
    logger.info("🤖 Bot ready with JSON storage")

@app.on_event("startup")
async def startup():
    """Run on application startup."""
    logger.info("🚀 FastAPI startup - JSON storage mode")
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
