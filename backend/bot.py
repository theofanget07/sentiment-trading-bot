import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get tokens from .env
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message when /start is issued."""
    user = update.effective_user
    welcome_text = f"""
🤖 **Sentiment Trading Bot** - Welcome {user.first_name}!

I'm your AI-powered crypto sentiment analyzer.

**Available commands:**
/start - Show this message
/help - Get help
/analyze - Analyze crypto news sentiment (coming soon)

**Phase 1 MVP** - Week 1 Test
This is a test bot. Full features coming in Week 2-3!

Built by Theo Fanget
Target: €870/month by Week 8 🚀
"""
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message when /help is issued."""
    help_text = """
📚 **Help - Sentiment Trading Bot**

**Commands:**
/start - Welcome message
/help - This help message
/analyze - Analyze sentiment (coming Week 2)

**Roadmap:**
- Week 1: Basic bot ✅
- Week 2: Sentiment analysis with Claude AI
- Week 3: Monetization + launch

Questions? Contact: theofanget@gmail.com
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Echo any message (temporary - will be sentiment analysis)."""
    user_message = update.message.text
    response = f"📝 You said: *{user_message}*\n\nSentiment analysis coming in Week 2!"
    await update.message.reply_text(response, parse_mode='Markdown')

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Log errors caused by updates."""
    logger.error(f"Exception while handling an update: {context.error}")

def main():
    """Start the bot."""
    # Check if token exists
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not found in .env file!")
        return
    
    # Create application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # Add message handler (echo for now)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start bot
    logger.info("🤖 Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
