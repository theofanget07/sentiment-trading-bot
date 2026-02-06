"""Telegram notification service for async message delivery.

Provides utilities to send Telegram notifications from Celery tasks:
- Price alerts
- AI recommendations
- Daily insights with position advice
- Bonus Trade of the Day
- Morning Briefing (combines Daily Insights + Bonus Trade)
"""

import os
import logging
import requests
from typing import Optional, List, Dict

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
    
    def send_morning_briefing(
        self,
        chat_id: int,
        username: str,
        total_value: float,
        change_24h: float,
        change_24h_pct: float,
        best_performer: str,
        best_performer_pct: float,
        position_advice: List[Dict],
        bonus_trade: Dict,
        news_summary: str,
    ) -> bool:
        """Send comprehensive Morning Briefing combining Daily Insights + Bonus Trade.
        
        Args:
            chat_id: Telegram chat ID
            username: User's first name
            total_value: Total portfolio value
            change_24h: 24h change in USD
            change_24h_pct: 24h change percentage
            best_performer: Best performing crypto
            best_performer_pct: Best performer % change
            position_advice: List of position advice dicts
            bonus_trade: Dict with bonus trade details (symbol, action, entry_price, etc.)
            news_summary: Market news summary
        
        Returns:
            True if sent successfully
        """
        emoji_time = "🌅"
        emoji_trend = "📈" if change_24h > 0 else "📉" if change_24h < 0 else "➡️"
        
        # Build comprehensive morning message
        message = f"""{emoji_time} **GOOD MORNING BRIEFING**

📋 **YOUR PORTFOLIO (24h)**
━━━━━━━━━━━━━━━━━━

💰 Total Value: `${total_value:,.2f}`
{emoji_trend} 24h Change: `${change_24h:+,.2f}` (`{change_24h_pct:+.2f}%`)

🏆 Top Performer: **{best_performer}** (`{best_performer_pct:+.2f}%`)
""".strip()
        
        # Add position advice
        if position_advice and len(position_advice) > 0:
            message += "\n\n━━━━━━━━━━━━━━━━━━\n\n🎯 **AI POSITION ADVICE**\n"
            for advice in position_advice:
                symbol = advice.get("symbol", "???")
                pnl_pct = advice.get("pnl_pct", 0)
                current_price = advice.get("current_price", 0)
                advice_text = advice.get("advice", "No advice available")
                
                pnl_emoji = "🟢" if pnl_pct > 0 else "🔴" if pnl_pct < -5 else "🟡"
                
                message += f"\n{pnl_emoji} **{symbol}** (`{pnl_pct:+.1f}%`) | `${current_price:,.2f}`\n"
                message += f"   💡 {advice_text}\n"
            
            message += "\n💬 _Want detailed analysis? Use /recommend [CRYPTO]_"
        
        # Add Bonus Trade section
        message += "\n\n━━━━━━━━━━━━━━━━━━\n\n🏆 **BONUS TRADE OF THE DAY**\n"
        
        symbol = bonus_trade.get("symbol", "???")
        action = bonus_trade.get("action", "BUY")
        entry_price = bonus_trade.get("entry_price", 0)
        confidence = bonus_trade.get("confidence", 70)
        risk_level = bonus_trade.get("risk_level", "MEDIUM")
        reasoning = bonus_trade.get("reasoning", "")
        
        # Action emoji
        action_emoji = "📈" if action == "BUY" else "📉" if action == "SELL" else "⚪"
        
        # Risk emoji
        risk_emoji = {
            "LOW": "🟢",
            "MEDIUM": "🟡",
            "HIGH": "🔴",
        }.get(risk_level, "⚪")
        
        message += f"\n{action_emoji} **{symbol} - {action}**"
        message += f"\n💰 Entry: `${entry_price:,.2f}`"
        message += f"\n\n📋 Confidence: **{confidence}%** | {risk_emoji} Risk: **{risk_level}**"
        
        # Extract key points from reasoning
        key_points = self._extract_key_points(reasoning, max_points=3)
        
        if key_points:
            message += "\n\n💡 **Why this trade:**"
            for point in key_points:
                message += f"\n• {point}"
        
        message += "\n\n⚠️ _AI-generated. DYOR. Manage risk._"
        
        # Add market news
        message += f"""

━━━━━━━━━━━━━━━━━━

📰 **Market News:**
{news_summary}

Have a profitable day! 🚀
""".strip()
        
        return self.send_message(chat_id, message)
    
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

📋 Position Details:
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
        position_advice: Optional[List[Dict]] = None,
    ) -> bool:
        """Send daily portfolio insight notification with AI position advice.
        
        DEPRECATED: Use send_morning_briefing() instead (combines with bonus trade).
        Kept for backward compatibility.
        
        Args:
            chat_id: Telegram chat ID
            username: User's first name
            total_value: Total portfolio value
            change_24h: 24h change in USD
            change_24h_pct: 24h change percentage
            best_performer: Best performing crypto
            best_performer_pct: Best performer % change
            news_summary: Market news summary
            position_advice: List of position advice dicts (optional)
        
        Returns:
            True if sent successfully
        """
        emoji_time = "🌅"
        emoji_trend = "📈" if change_24h > 0 else "📉" if change_24h < 0 else "➡️"
        
        # Build base message
        message = f"""
{emoji_time} **Good morning {username}!**

📋 **PORTFOLIO UPDATE (24h)**
━━━━━━━━━━━━━━━━━━

💰 Total Value: `${total_value:,.2f}`
{emoji_trend} 24h Change: `${change_24h:+,.2f}` (`{change_24h_pct:+.2f}%`)

🏆 Top Performer:
• **{best_performer}**: `{best_performer_pct:+.2f}%`
        """.strip()
        
        # Add position advice if available
        if position_advice and len(position_advice) > 0:
            message += "\n\n🎯 **AI POSITION ADVICE:**\n"
            for advice in position_advice:
                symbol = advice.get("symbol", "???")
                pnl_pct = advice.get("pnl_pct", 0)
                advice_text = advice.get("advice", "No advice available")
                
                pnl_emoji = "🟢" if pnl_pct > 0 else "🔴" if pnl_pct < -5 else "🟡"
                
                message += f"\n{pnl_emoji} **{symbol}** (`{pnl_pct:+.1f}%`)\n"
                message += f"   💡 {advice_text}\n"
        
        # Add news summary
        message += f"""

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
    
    def send_bonus_trade(
        self,
        chat_id: int,
        symbol: str,
        action: str,
        entry_price: float,
        reasoning: str,
        confidence: int,
        risk_level: str,
        target_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
    ) -> bool:
        """Send Bonus Trade of the Day notification.
        
        DEPRECATED: Use send_morning_briefing() instead (combines with daily insights).
        Kept for backward compatibility.
        
        Args:
            chat_id: Telegram chat ID
            symbol: Crypto symbol (e.g., 'BTC')
            action: Trading action (BUY/SELL)
            entry_price: Recommended entry price
            reasoning: AI analysis and reasoning
            confidence: Confidence score (0-100)
            risk_level: Risk level (LOW/MEDIUM/HIGH)
            target_price: Take-profit target (optional)
            stop_loss: Stop-loss level (optional)
        
        Returns:
            True if sent successfully
        """
        # Risk level emoji
        risk_emoji = {
            "LOW": "🟢",
            "MEDIUM": "🟡",
            "HIGH": "🔴",
        }.get(risk_level, "⚪")
        
        # Action emoji
        action_emoji = "📈" if action == "BUY" else "📉" if action == "SELL" else "⚪"
        
        # Build message header
        message = f"""
🏆 **BONUS TRADE OF THE DAY**

{action_emoji} **{symbol} - {action}**
💰 Entry: `${entry_price:,.2f}`
        """.strip()
        
        # Add target & stop loss with potential gains/losses
        if target_price:
            potential_gain = ((target_price - entry_price) / entry_price) * 100
            message += f"\n🎯 Target: `${target_price:,.2f}` 🟢 `+{potential_gain:.1f}%`"
        
        if stop_loss:
            potential_loss = ((stop_loss - entry_price) / entry_price) * 100
            message += f"\n🛑 Stop: `${stop_loss:,.2f}` 🔴 `{potential_loss:.1f}%`"
        
        # Confidence and risk
        message += f"\n\n📋 Confidence: **{confidence}%** | {risk_emoji} Risk: **{risk_level}**"
        
        # Extract and format key points from reasoning (max 3 bullets)
        key_points = self._extract_key_points(reasoning, max_points=3)
        
        if key_points:
            message += "\n\n💡 **Why this trade:**"
            for point in key_points:
                message += f"\n• {point}"
        
        # Compact disclaimer
        message += "\n\n⚠️ _AI-generated. DYOR. Manage risk._"
        
        return self.send_message(chat_id, message)
    
    def _extract_key_points(self, reasoning: str, max_points: int = 3) -> List[str]:
        """Extract key bullet points from AI reasoning.
        
        Args:
            reasoning: Full AI analysis text
            max_points: Maximum number of points to extract
        
        Returns:
            List of concise key points (max 60 chars each)
        """
        # Look for bullet points or numbered lists
        import re
        
        # Pattern for bullets: "• point" or "- point" or "* point"
        bullet_pattern = r"^[•\-\*]\s+(.+)$"
        
        # Pattern for numbered: "1. point" or "1) point"
        numbered_pattern = r"^\d+[.)]\s+(.+)$"
        
        points = []
        
        for line in reasoning.split("\n"):
            line = line.strip()
            
            # Check bullet patterns
            match = re.match(bullet_pattern, line)
            if not match:
                match = re.match(numbered_pattern, line)
            
            if match:
                point = match.group(1).strip()
                
                # Clean up markdown
                point = re.sub(r"\*\*(.+?)\*\*", r"\1", point)  # Remove **bold**
                point = re.sub(r"__(.+?)__", r"\1", point)  # Remove __underline__
                
                # Shorten if needed
                if len(point) > 60:
                    point = point[:57] + "..."
                
                points.append(point)
                
                if len(points) >= max_points:
                    break
        
        # If no bullets found, try to extract first 3 sentences
        if not points:
            sentences = re.split(r"[.!?]\s+", reasoning)
            for sentence in sentences[:max_points]:
                sentence = sentence.strip()
                if len(sentence) > 10:  # Skip very short sentences
                    if len(sentence) > 60:
                        sentence = sentence[:57] + "..."
                    points.append(sentence)
        
        return points


# Singleton instance
_service = None


def get_notification_service() -> TelegramNotificationService:
    """Get or create Telegram notification service singleton."""
    global _service
    if _service is None:
        _service = TelegramNotificationService()
    return _service
