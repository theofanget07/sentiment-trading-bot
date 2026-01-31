#!/usr/bin/env python3
"""
Telegram Bot with Webhook support for Railway deployment.
Uses FastAPI for native async support.
"""
import os
import logging
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

import sys
sys.path.insert(0, os.path.dirname(__file__))

from sentiment_analyzer import analyze_sentiment
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
/portfolio - View holdings (coming soon)
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
    logger.error(f"Error: {context.error}")

@app.get("/health")
async def health():
    return {"status": "ok", "mode": "webhook"}

@app.get("/db-status")
async def db_status():
    """
    Debug endpoint to verify PostgreSQL tables exist.
    Returns list of tables and connection status.
    """
    try:
        from database import engine
        from sqlalchemy import inspect
        
        # Get inspector
        inspector = inspect(engine)
        
        # Get all table names
        tables = inspector.get_table_names()
        
        # Check for portfolio tables
        portfolio_tables = [
            'user_positions',
            'position_transactions', 
            'position_recommendations',
            'daily_digests'
        ]
        
        portfolio_status = {
            table: (table in tables) for table in portfolio_tables
        }
        
        return {
            "status": "connected",
            "database_url": os.getenv('DATABASE_URL', 'Not set')[:50] + "...",
            "total_tables": len(tables),
            "all_tables": sorted(tables),
            "portfolio_tables_status": portfolio_status,
            "portfolio_ready": all(portfolio_status.values()),
            "message": "✅ All portfolio tables exist!" if all(portfolio_status.values()) else "⚠️ Some portfolio tables missing"
        }
        
    except Exception as e:
        logger.error(f"DB status check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": "❌ Database connection failed"
        }

@app.post(f"/{TELEGRAM_TOKEN}")
async def webhook(request: Request):
    """Handle incoming Telegram updates via webhook."""
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        
        # Process update directly with application
        await application.process_update(update)
        
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return Response(status_code=500)

async def setup_application():
    """Initialize the Telegram application."""
    global application
    
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not found!")
        raise ValueError("TELEGRAM_BOT_TOKEN required")
    
    # Build application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("analyze", analyze_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)
    
    # Initialize application
    await application.initialize()
    await application.start()
    
    # Set webhook
    if WEBHOOK_URL:
        webhook_url = f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}"
        logger.info(f"Setting webhook to: {webhook_url}")
        await application.bot.set_webhook(url=webhook_url)
    
    logger.info("🤖 Bot ready in webhook mode")

def init_database_schema():
    """Initialize portfolio database tables (synchronous function)."""
    logger.info("========================================")
    logger.info("🚀 Initializing Portfolio Database")
    logger.info("========================================")
    
    try:
        from init_portfolio_tables import init_portfolio_tables
        success = init_portfolio_tables()
        
        if success:
            logger.info("✅ Portfolio database ready")
        else:
            logger.warning("⚠️  Portfolio init returned False (tables may already exist)")
        
        logger.info("========================================")
        return success
        
    except Exception as e:
        logger.error(f"❌ Portfolio database init failed: {e}")
        logger.info("⚠️  Continuing anyway (tables may already exist)")
        logger.info("========================================")
        return False

@app.on_event("startup")
async def startup():
    """Run on application startup."""
    # Initialize database tables BEFORE starting bot
    init_database_schema()
    
    # Then start Telegram bot
    await setup_application()
    logger.info("🚀 FastAPI server started")

@app.on_event("shutdown")
async def shutdown():
    """Run on application shutdown."""
    if application:
        await application.stop()
        await application.shutdown()
    logger.info("🚫Bot stopped")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
