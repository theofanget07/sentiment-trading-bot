"""Telegram notification service for async message delivery.

Provides utilities to send Telegram notifications from Celery tasks:
- Price alerts
- AI recommendations
- Daily insights
"""

import os
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)


class TelegramNotificationService:
    """Service for sending Telegram notifications asynchronously."""
    
    def __init__(self, bot_token: Optional[str] = None):
        """Initialize Telegram notification service.
        
        Args:
            bot_token: Telegram bot token (defaults to TELEGRAM_BOT_TOKEN env var)
        """
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN not provided")
        
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: str = "Markdown",
        disable_web_page_preview: bool = True,
    ) -> bool:
        """Send a text message to a Telegram chat.
        
        Args:
            chat_id: Telegram chat ID
            text: Message text
            parse_mode: Parse mode (Markdown or HTML)
            disable_web_page_preview: Disable link previews
        
        Returns:
            True if message sent successfully, False otherwise
        """
        try:
            response = requests.post(
                f"{self.base_url}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": parse_mode,
                    "disable_web_page_preview": disable_web_page_preview,
                },
                timeout=10,
            )
            response.raise_for_status()
            logger.info(f"Message sent successfully to chat_id={chat_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to send message to chat_id={chat_id}: {e}")
            return False
    
    def send_price_alert(
        self,
        chat_id: int,
        crypto_symbol: str,
        current_price: float,
        buy_price: float,
        pnl_usd: float,
        pnl_pct: float,
    ) -> bool:
        """Send a price alert notification.
        
        Args:
            chat_id: Telegram chat ID
            crypto_symbol: Crypto symbol (e.g., 'BTC')
            current_price: Current market price
            buy_price: User's buy price
            pnl_usd: P&L in USD
            pnl_pct: P&L percentage
        
        Returns:
            True if sent successfully
        """
        emoji = "🚨" if pnl_pct >= 10 or pnl_pct <= -5 else "⚠️"
        direction = "📈" if pnl_pct > 0 else "📉"
        
        message = f"""
{emoji} **PRICE ALERT: {crypto_symbol}** {direction}

📊 Position Details:
• Buy Price: `${buy_price:,.2f}`
• Current: `${current_price:,.2f}`
• Change: `{pnl_pct:+.2f}%`
• Unrealized P&L: `${pnl_usd:+,.2f} USD`

💡 Consider reviewing your position.
        """.strip()
        
        return self.send_message(chat_id, message)
    
    def send_daily_insight(
        self,
        chat_id: int,
        username: str,
        total_value: float,
        change_24h: float,
        change_24h_pct: float,
        best_performer: str,
        best_performer_pct: float,
        news_summary: str,
    ) -> bool:
        """Send daily portfolio insight notification.
        
        Args:
            chat_id: Telegram chat ID
            username: User's first name
            total_value: Total portfolio value
            change_24h: 24h change in USD
            change_24h_pct: 24h change percentage
            best_performer: Best performing crypto
            best_performer_pct: Best performer % change
            news_summary: Market news summary
        
        Returns:
            True if sent successfully
        """
        emoji_time = "🌅"
        emoji_trend = "📈" if change_24h > 0 else "📉" if change_24h < 0 else "➡️"
        
        message = f"""
{emoji_time} **Good morning {username}!**

📊 **PORTFOLIO UPDATE (24h)**
━━━━━━━━━━━━━━━━━━

💰 Total Value: `${total_value:,.2f}`
{emoji_trend} 24h Change: `${change_24h:+,.2f}` (`{change_24h_pct:+.2f}%`)

🏆 Top Performer:
• **{best_performer}**: `{best_performer_pct:+.2f}%`

📰 **Market News:**
{news_summary}

━━━━━━━━━━━━━━━━━━
Have a great day! 🚀
        """.strip()
        
        return self.send_message(chat_id, message)
    
    def send_ai_recommendation(
        self,
        chat_id: int,
        crypto_symbol: str,
        recommendation: str,
        reasoning: str,
        confidence: int,
    ) -> bool:
        """Send AI recommendation notification.
        
        Args:
            chat_id: Telegram chat ID
            crypto_symbol: Crypto symbol
            recommendation: BUY/SELL/HOLD
            reasoning: AI reasoning
            confidence: Confidence score (0-100)
        
        Returns:
            True if sent successfully
        """
        emoji_map = {
            "BUY": "🟢",
            "SELL": "🔴",
            "HOLD": "🟡",
        }
        emoji = emoji_map.get(recommendation, "⚪")
        
        message = f"""
🤖 **AI RECOMMENDATION: {crypto_symbol}**

{emoji} **Action:** {recommendation}
🎯 **Confidence:** {confidence}%

📝 **Analysis:**
{reasoning}

⚠️ _This is AI-generated advice. Always do your own research._
        """.strip()
        
        return self.send_message(chat_id, message)


# Singleton instance
_service = None


def get_notification_service() -> TelegramNotificationService:
    """Get or create Telegram notification service singleton."""
    global _service
    if _service is None:
        _service = TelegramNotificationService()
    return _service
