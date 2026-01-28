import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from sentiment_analyzer import analyze_sentiment
from article_scraper import extract_article, extract_urls, is_valid_url

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

**NEW! 🔥 URL Support:**
Send me any crypto news article URL and I'll automatically extract and analyze it!

**Examples:**
`/analyze Bitcoin hits new ATH as institutions buy`

Or just paste a URL:
`https://coindesk.com/markets/bitcoin-rally`

**Phase 1** - Week 1 Day 3 Live Test 🚀
Built by Theo Fanget | Target: €870/month by Week 8
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

**Supported sites:**
• CoinDesk
• CoinTelegraph
• Bitcoin.com
• Decrypt
• The Block
• CryptoSlate
• And more!

**Examples:**
`/analyze Ethereum upgrade successful, gas fees drop 50%`

Or:
`https://cointelegraph.com/news/bitcoin-price-surge`

**Commands:**
/start - Welcome message
/help - This help
/analyze - Analyze sentiment
"""
    await update.message.reply_text(help_text, parse_mode='Markdown', disable_web_page_preview=True)

async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /analyze command with text or URL support."""
    user_text = ' '.join(context.args)

    if not user_text or len(user_text) < 10:
        await update.message.reply_text(
            "⚠️ Please provide text or URL to analyze.\n\n"
            "**Examples:**\n"
            "`/analyze Bitcoin surges as ETFs see record inflows`\n\n"
            "Or:\n"
            "`/analyze https://coindesk.com/markets/bitcoin-news`",
            parse_mode='Markdown'
        )
        return

    # Check if input contains a URL
    urls = extract_urls(user_text)
    
    if urls:
        # URL detected - scrape and analyze
        await analyze_url(update, urls[0])
    else:
        # Regular text analysis
        await analyze_text(update, user_text)

async def analyze_url(update: Update, url: str, message_to_delete=None):
    """Scrape article from URL and analyze sentiment.
    
    Args:
        update: Telegram update object
        url: Article URL to scrape
        message_to_delete: Optional message to delete after processing
    """
    scraping_msg = await update.message.reply_text(
        f"📰 Scraping article...\n`{url[:50]}...`",
        parse_mode='Markdown'
    )

    try:
        # Extract article text
        article_text = extract_article(url)

        if not article_text:
            await scraping_msg.delete()
            await update.message.reply_text(
                "❌ Failed to extract article. Please check the URL or try another source.\n\n"
                "**Supported sites:** CoinDesk, CoinTelegraph, Bitcoin.com, Decrypt, The Block, etc.",
                parse_mode='Markdown'
            )
            return

        # Update message
        await scraping_msg.edit_text(
            f"✅ Article extracted ({len(article_text)} chars)\n"
            f"🔍 Analyzing with Perplexity AI...",
            parse_mode='Markdown'
        )

        # Analyze sentiment
        result = analyze_sentiment(article_text)

        sentiment_emoji = {
            'BULLISH': '🚀',
            'BEARISH': '📉',
            'NEUTRAL': '➡️'
        }
        emoji = sentiment_emoji.get(result['sentiment'], '❓')

        response = f"""
📰 **Article Analysis**
🔗 {url[:60]}...

{emoji} **{result['sentiment']}** ({result['confidence']}% confidence)

💡 **Reasoning:**
{result['reasoning']}

📌 **Key Points:**
"""
        for i, point in enumerate(result['key_points'], 1):
            response += f"{i}. {point}\n"

        if result.get('sources'):
            response += "\n📚 **Additional Context:**\n"
            for source in result['sources'][:2]:
                response += f"• {source}\n"

        response += "\n_Powered by Perplexity AI | Week 1 Day 3 Test 🚀_"

        await scraping_msg.delete()
        if message_to_delete:
            try:
                await message_to_delete.delete()
            except:
                pass
        
        await update.message.reply_text(response, parse_mode='Markdown', disable_web_page_preview=True)

    except Exception as e:
        logger.error(f"Error in analyze_url: {e}")
        await scraping_msg.delete()
        await update.message.reply_text(
            "❌ Sorry, analysis failed. Please try again or use a different URL.",
            parse_mode='Markdown'
        )

async def analyze_text(update: Update, text: str, message_to_delete=None):
    """Analyze sentiment of provided text.
    
    Args:
        update: Telegram update object
        text: Text to analyze
        message_to_delete: Optional message to delete after processing
    """
    analyzing_msg = await update.message.reply_text("🔍 Analyzing with Perplexity AI...")

    try:
        result = analyze_sentiment(text)

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
        if message_to_delete:
            try:
                await message_to_delete.delete()
            except:
                pass
        
        await update.message.reply_text(response, parse_mode='Markdown', disable_web_page_preview=True)

    except Exception as e:
        logger.error(f"Error in analyze_text: {e}")
        await analyzing_msg.delete()
        await update.message.reply_text(
            "❌ Sorry, analysis failed. Please try again.",
            parse_mode='Markdown'
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all text messages - detect URLs or analyze long text."""
    user_message = update.message.text

    # Check if message contains URL
    urls = extract_urls(user_message)
    
    if urls:
        # URL detected in message - auto-scrape and analyze
        logger.info(f"URL detected: {urls[0]}")
        await analyze_url(update, urls[0])
        return

    # No URL - check if text is long enough for auto-analysis
    if len(user_message) > 30:
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
            f"💬 You said: _{user_message}_\n\n"
            "Send longer text or a URL for auto-analysis, or use `/analyze`",
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

    logger.info("🤖 Sentiment Bot starting with URL scraping support...")
    logger.info("✨ Week 1 Day 3 - URL Scraping Feature Live!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
