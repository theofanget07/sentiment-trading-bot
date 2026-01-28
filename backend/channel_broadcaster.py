"""Telegram channel broadcaster for posting sentiment signals."""
import os
from telegram import Bot
from telegram.constants import ParseMode
from dotenv import load_dotenv
import logging
from datetime import datetime

from models import Article

load_dotenv()
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")  # e.g., @your_channel or -1001234567890

class ChannelBroadcaster:
    """Broadcast trading signals to Telegram channel."""
    
    def __init__(self):
        """Initialize Telegram bot for channel posting."""
        if not TELEGRAM_BOT_TOKEN:
            logger.error("❌ TELEGRAM_BOT_TOKEN not set")
            self.bot = None
        elif not TELEGRAM_CHANNEL_ID:
            logger.error("❌ TELEGRAM_CHANNEL_ID not set")
            self.bot = None
        else:
            try:
                self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
                logger.info("✅ Telegram bot initialized for channel broadcasting")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Telegram bot: {e}")
                self.bot = None
    
    def _format_signal_message(self, article: Article) -> str:
        """Format article as a trading signal message.
        
        Args:
            article: Article object to format
            
        Returns:
            Formatted message string with Markdown
        """
        # Sentiment emoji and action
        if article.sentiment.value == 'bullish':
            emoji = "📈"
            action = "BUY SIGNAL"
            color_emoji = "🟢"  # green circle
        elif article.sentiment.value == 'bearish':
            emoji = "📉"
            action = "SELL SIGNAL"
            color_emoji = "🔴"  # red circle
        else:
            emoji = "➡️"
            action = "NEUTRAL"
            color_emoji = "⚪"  # white circle
        
        # Confidence bar
        confidence_pct = int(article.confidence * 100)
        bars = "█" * (confidence_pct // 10)
        confidence_bar = f"{bars} {confidence_pct}%"
        
        # Format message with Markdown
        message = f"""
{color_emoji} **{action}** {emoji}

📰 **{article.title}**

🧠 **Analysis:**
{article.reasoning[:300]}{'...' if len(article.reasoning) > 300 else ''}

📊 **Confidence:** {confidence_bar}
⏱ **Time:** {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}
🎯 **Source:** {article.source}

🔗 [Read Full Article]({article.url})

⚠️ *This is AI-generated analysis, not financial advice. Always DYOR.*
"""
        
        return message.strip()
    
    def _format_recommendation(self, article: Article) -> str:
        """Generate trading recommendation based on sentiment.
        
        Args:
            article: Article object
            
        Returns:
            Recommendation string
        """
        confidence = article.confidence
        
        if article.sentiment.value == 'bullish':
            if confidence >= 0.90:
                return "🔥 **STRONG BUY** - Very high confidence"
            elif confidence >= 0.80:
                return "🟢 **BUY** - High confidence"
            else:
                return "🔵 **WATCH** - Moderate bullish sentiment"
        
        elif article.sentiment.value == 'bearish':
            if confidence >= 0.90:
                return "⚠️ **STRONG SELL** - Very high confidence"
            elif confidence >= 0.80:
                return "🔴 **SELL** - High confidence"
            else:
                return "🟡 **WATCH** - Moderate bearish sentiment"
        
        else:
            return "⚪ **HOLD** - Neutral sentiment"
    
    def post_signal(self, article: Article) -> bool:
        """Post a trading signal to the Telegram channel.
        
        Args:
            article: Article object to post
            
        Returns:
            True if posted successfully, False otherwise
        """
        if not self.bot:
            logger.warning("⚠️ Cannot post signal: Bot not initialized")
            return False
        
        try:
            # Format message
            message = self._format_signal_message(article)
            recommendation = self._format_recommendation(article)
            
            # Add recommendation to message
            full_message = f"{message}\n\n🎯 **Recommendation:** {recommendation}"
            
            # Send to channel
            self.bot.send_message(
                chat_id=TELEGRAM_CHANNEL_ID,
                text=full_message,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=False,
            )
            
            logger.info(f"✅ Posted signal to channel: {article.title[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to post signal: {e}")
            return False
    
    def post_daily_summary(self, articles: list, overall_sentiment: str) -> bool:
        """Post a daily summary to the channel.
        
        Args:
            articles: List of Article objects from today
            overall_sentiment: Overall sentiment (BULLISH/BEARISH/NEUTRAL)
            
        Returns:
            True if posted successfully
        """
        if not self.bot:
            logger.warning("⚠️ Cannot post summary: Bot not initialized")
            return False
        
        try:
            # Count sentiments
            bullish = len([a for a in articles if a.sentiment.value == 'bullish'])
            bearish = len([a for a in articles if a.sentiment.value == 'bearish'])
            neutral = len([a for a in articles if a.sentiment.value == 'neutral'])
            
            # Overall emoji
            if overall_sentiment == "BULLISH":
                emoji = "📈🟢"
            elif overall_sentiment == "BEARISH":
                emoji = "📉🔴"
            else:
                emoji = "➡️⚪"
            
            message = f"""
📅 **DAILY MARKET SUMMARY** - {datetime.now().strftime('%B %d, %Y')}

{emoji} **Overall Sentiment: {overall_sentiment}**

📊 **Today's Analysis:**
• 🟢 Bullish: {bullish} articles
• 🔴 Bearish: {bearish} articles
• ⚪ Neutral: {neutral} articles
📝 Total analyzed: {len(articles)}

🔔 **Key Takeaway:**
{'Market showing positive momentum' if overall_sentiment == 'BULLISH' else 'Market showing negative momentum' if overall_sentiment == 'BEARISH' else 'Market in consolidation phase'}

🔍 Stay tuned for high-confidence signals throughout the day!

⚠️ *AI-powered sentiment analysis - Not financial advice*
"""
            
            self.bot.send_message(
                chat_id=TELEGRAM_CHANNEL_ID,
                text=message.strip(),
                parse_mode=ParseMode.MARKDOWN,
            )
            
            logger.info("✅ Posted daily summary to channel")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to post daily summary: {e}")
            return False
    
    def send_test_message(self) -> bool:
        """Send a test message to verify channel configuration.
        
        Returns:
            True if test message sent successfully
        """
        if not self.bot:
            logger.error("❌ Bot not initialized")
            return False
        
        try:
            test_message = """
🧪 **TEST MESSAGE**

Your Telegram channel is configured correctly!

✅ Bot can post to this channel
✅ Ready to broadcast signals
"""
            
            self.bot.send_message(
                chat_id=TELEGRAM_CHANNEL_ID,
                text=test_message.strip(),
                parse_mode=ParseMode.MARKDOWN,
            )
            
            logger.info("✅ Test message sent to channel")
            return True
            
        except Exception as e:
            logger.error(f"❌ Test message failed: {e}")
            return False

if __name__ == "__main__":
    # Test broadcaster when run directly
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    broadcaster = ChannelBroadcaster()
    
    if broadcaster.bot:
        print("🧪 Sending test message to channel...")
        result = broadcaster.send_test_message()
        print(f"\n✅ Test result: {'SUCCESS' if result else 'FAILED'}")
    else:
        print("❌ Bot not configured. Check TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID")
