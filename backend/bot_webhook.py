#!/usr/bin/env python3
"""
Telegram Bot with Webhook support for Railway deployment.
Uses Flask to receive updates instead of polling.
"""
import os
import logging
from dotenv import load_dotenv
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Import handlers from original bot
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
WEBHOOK_URL = os.getenv('WEBHOOK_URL')  # e.g., https://your-app.railway.app
PORT = int(os.getenv('PORT', 8080))

app = Flask(__name__)
application = None

# Command handlers (same as bot.py)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_text = f"""
🤖 **Sentiment Trading Bot** - Welcome {user.first_name}!

I'm your AI-powered crypto sentiment analyzer powered by Perplexity AI.

**Available commands:**
/start - Show this message
/help - Get help
/analyze <text> - Analyze crypto news sentiment

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

async def analyze_url(update: Update, url: str):
    scraping_msg = await update.message.reply_text(f"📰 Scraping article...", parse_mode='Markdown')
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
    logger.error(f"Error: {context.error}")

@app.route('/health', methods=['GET'])
def health():
    return {'status': 'ok', 'mode': 'webhook'}, 200

@app.route(f'/{TELEGRAM_TOKEN}', methods=['POST'])
async def webhook():
    """Handle incoming Telegram updates via webhook."""
    if request.method == 'POST':
        update = Update.de_json(request.get_json(force=True), application.bot)
        await application.update_queue.put(update)
        return 'ok'

def setup_application():
    """Initialize the Telegram application."""
    global application
    
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not found!")
        raise ValueError("TELEGRAM_BOT_TOKEN required")
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("analyze", analyze_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)
    
    # Initialize application
    application.initialize()
    
    # Set webhook
    if WEBHOOK_URL:
        webhook_url = f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}"
        logger.info(f"Setting webhook to: {webhook_url}")
        application.bot.set_webhook(url=webhook_url)
    
    logger.info("🤖 Bot ready in webhook mode")
    return application

if __name__ == '__main__':
    setup_application()
    logger.info(f"Starting Flask server on port {PORT}")
    app.run(host='0.0.0.0', port=PORT)
