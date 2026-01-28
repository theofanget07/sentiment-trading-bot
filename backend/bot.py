import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from sentiment_analyzer import analyze_sentiment

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_text = f"""
🤖 **Sentiment Trading Bot** - Welcome {user.first_name}!

I'm your AI-powered crypto sentiment analyzer powered by Perplexity AI.

**Available commands:**
/start - Show this message
/help - Get help
/analyze <text> - Analyze crypto news sentiment

**Example:**
`/analyze Bitcoin hits new ATH as institutions buy`

**Phase 1** - Week 1 Live Test 🚀
Built by Theo Fanget | Target: €870/month by Week 8
"""
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📚 **Help - Sentiment Trading Bot**

**How to use:**
1. Send me crypto news text
2. Or use `/analyze <your text>`
3. I'll analyze sentiment with Perplexity AI

**Example:**
`/analyze Ethereum upgrade successful, gas fees drop 50%`

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
            "**Example:**\n"
            "`/analyze Bitcoin surges as ETFs see record inflows`",
            parse_mode='Markdown'
        )
        return

    analyzing_msg = await update.message.reply_text("🔍 Analyzing with Perplexity AI...")

    try:
        result = analyze_sentiment(user_text)

        sentiment_emoji = {
            'BULLISH': '🚀',
            'BEARISH': '📉',
            'NEUTRAL': '➡️'
        }
        emoji = sentiment_emoji.get(result['sentiment'], '❓')

        response = f"""
{emoji} **{result['sentiment']}** ({result['confidence']}% confidence)

💡 **Reasoning:**
{result['reasoning']}

📌 **Key Points:**
"""
        for i, point in enumerate(result['key_points'], 1):
            response += f"{i}. {point}\n"

        if result.get('sources'):
            response += "\n📚 **Sources:**\n"
            for source in result['sources'][:2]:
                response += f"• {source}\n"

        response += "\n_Powered by Perplexity AI_"

        await analyzing_msg.delete()
        await update.message.reply_text(response, parse_mode='Markdown', disable_web_page_preview=True)

    except Exception as e:
        logger.error(f"Error in analyze_command: {e}")
        await analyzing_msg.delete()
        await update.message.reply_text(
            "❌ Sorry, analysis failed. Please try again.",
            parse_mode='Markdown'
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text

    if len(user_message) > 20:
        analyzing_msg = await update.message.reply_text("🔍 Auto-analyzing...")
        try:
            result = analyze_sentiment(user_message)

            sentiment_emoji = {
                'BULLISH': '🚀',
                'BEARISH': '📉',
                'NEUTRAL': '➡️'
            }
            emoji = sentiment_emoji.get(result['sentiment'], '❓')

            response = f"""
{emoji} **{result['sentiment']}** ({result['confidence']}%)

{result['reasoning']}

_Use /analyze for detailed analysis_
"""
            await analyzing_msg.delete()
            await update.message.reply_text(response, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Auto-analyze error: {e}")
            await analyzing_msg.delete()
            await update.message.reply_text(
                f"💬 You said: _{user_message}_\n\nUse `/analyze <text>` for sentiment analysis!",
                parse_mode='Markdown'
            )
    else:
        await update.message.reply_text(
            f"💬 You said: _{user_message}_\n\nSend longer text for auto-analysis, or use `/analyze`",
            parse_mode='Markdown'
        )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Exception while handling an update: {context.error}")

def main():
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not found in .env file!")
        return

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("analyze", analyze_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.add_error_handler(error_handler)

    logger.info("🤖 Sentiment Bot starting with Perplexity AI...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
