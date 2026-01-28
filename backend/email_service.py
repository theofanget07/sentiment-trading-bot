"""Email service for sending daily digests using SendGrid."""
import os
from typing import List
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from dotenv import load_dotenv
import logging
from datetime import datetime

from models import Article

load_dotenv()
logger = logging.getLogger(__name__)

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "noreply@sentimentbot.com")
SENDER_NAME = os.getenv("SENDER_NAME", "Sentiment Trading Bot")

class EmailService:
    """Service for sending emails via SendGrid."""
    
    def __init__(self):
        """Initialize SendGrid client."""
        if not SENDGRID_API_KEY:
            logger.warning("⚠️ SENDGRID_API_KEY not set, emails will not be sent")
            self.client = None
        else:
            try:
                self.client = SendGridAPIClient(SENDGRID_API_KEY)
                logger.info("✅ SendGrid client initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize SendGrid: {e}")
                self.client = None
    
    def _generate_digest_html(self, articles: List[Article]) -> str:
        """Generate HTML email template for daily digest.
        
        Args:
            articles: List of Article objects to include
            
        Returns:
            HTML string for email body
        """
        # Calculate sentiment summary
        bullish_count = len([a for a in articles if a.sentiment.value == 'bullish'])
        bearish_count = len([a for a in articles if a.sentiment.value == 'bearish'])
        neutral_count = len([a for a in articles if a.sentiment.value == 'neutral'])
        
        # Determine overall sentiment
        if bullish_count > bearish_count:
            overall_sentiment = "BULLISH 📈"
            sentiment_color = "#10b981"  # green
        elif bearish_count > bullish_count:
            overall_sentiment = "BEARISH 📉"
            sentiment_color = "#ef4444"  # red
        else:
            overall_sentiment = "NEUTRAL ➡️"
            sentiment_color = "#6b7280"  # gray
        
        # Generate article cards
        article_cards = ""
        for i, article in enumerate(articles, 1):
            emoji = "📈" if article.sentiment.value == 'bullish' else "📉" if article.sentiment.value == 'bearish' else "➡️"
            sentiment_class = article.sentiment.value
            
            article_cards += f"""
            <div style="background: #f9fafb; border-left: 4px solid {sentiment_color}; padding: 16px; margin-bottom: 16px; border-radius: 8px;">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                    <h3 style="margin: 0; font-size: 16px; color: #111827;">#{i} {article.title}</h3>
                    <span style="font-size: 20px;">{emoji}</span>
                </div>
                <p style="margin: 8px 0; color: #6b7280; font-size: 14px;">{article.reasoning[:200]}...</p>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 12px;">
                    <span style="background: {sentiment_color}; color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600; text-transform: uppercase;">
                        {article.sentiment.value} - {article.confidence:.0%}
                    </span>
                    <a href="{article.url}" style="color: #3b82f6; text-decoration: none; font-size: 14px;">Read Article →</a>
                </div>
                <p style="margin: 8px 0 0 0; color: #9ca3af; font-size: 12px;">📰 {article.source} | 🕒 {article.published_at.strftime('%Y-%m-%d %H:%M UTC') if article.published_at else 'N/A'}</p>
            </div>
            """
        
        # Full HTML template
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Daily Crypto Sentiment Digest</title>
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #ffffff; margin: 0; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: white;">
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 12px 12px 0 0;">
                    <h1 style="color: white; margin: 0; font-size: 28px;">📈 Daily Crypto Sentiment</h1>
                    <p style="color: rgba(255,255,255,0.9); margin: 8px 0 0 0; font-size: 14px;">{datetime.now().strftime('%A, %B %d, %Y')}</p>
                </div>
                
                <!-- Overall Sentiment -->
                <div style="background: #f3f4f6; padding: 24px; text-align: center;">
                    <p style="margin: 0 0 8px 0; color: #6b7280; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">Overall Market Sentiment</p>
                    <h2 style="margin: 0; color: {sentiment_color}; font-size: 32px; font-weight: 700;">{overall_sentiment}</h2>
                    <p style="margin: 12px 0 0 0; color: #6b7280; font-size: 14px;">
                        📈 {bullish_count} Bullish | ➡️ {neutral_count} Neutral | 📉 {bearish_count} Bearish
                    </p>
                </div>
                
                <!-- Articles -->
                <div style="padding: 24px;">
                    <h2 style="margin: 0 0 20px 0; color: #111827; font-size: 20px;">🎯 Top {len(articles)} High-Confidence Signals</h2>
                    {article_cards}
                </div>
                
                <!-- Footer -->
                <div style="background: #f9fafb; padding: 24px; text-align: center; border-radius: 0 0 12px 12px; border-top: 1px solid #e5e7eb;">
                    <p style="margin: 0 0 12px 0; color: #6b7280; font-size: 14px;">
                        🤖 Powered by AI sentiment analysis | ⚡ Premium subscriber
                    </p>
                    <p style="margin: 0; color: #9ca3af; font-size: 12px;">
                        <a href="#" style="color: #9ca3af; text-decoration: none;">Unsubscribe</a> |
                        <a href="#" style="color: #9ca3af; text-decoration: none;">Manage Preferences</a>
                    </p>
                    <p style="margin: 12px 0 0 0; color: #d1d5db; font-size: 11px;">
                        ⚠️ Disclaimer: This is not financial advice. Always DYOR.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def send_daily_digest(self, user_email: str, articles: List[Article]) -> bool:
        """Send daily digest email to a user.
        
        Args:
            user_email: Email address to send to
            articles: List of Article objects to include
            
        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.client:
            logger.warning(f"⚠️ Cannot send email to {user_email}: SendGrid not configured")
            return False
        
        if not articles:
            logger.warning(f"⚠️ No articles to send to {user_email}")
            return False
        
        try:
            # Generate HTML content
            html_content = self._generate_digest_html(articles)
            
            # Create email
            message = Mail(
                from_email=Email(SENDER_EMAIL, SENDER_NAME),
                to_emails=To(user_email),
                subject=f"📈 Daily Crypto Sentiment - {datetime.now().strftime('%b %d, %Y')}",
                html_content=Content("text/html", html_content)
            )
            
            # Send email
            response = self.client.send(message)
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"✅ Email sent successfully to {user_email} (status: {response.status_code})")
                return True
            else:
                logger.warning(f"⚠️ Email sent with unexpected status {response.status_code} to {user_email}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to send email to {user_email}: {e}")
            return False
    
    def send_test_email(self, test_email: str) -> bool:
        """Send a test email to verify SendGrid configuration.
        
        Args:
            test_email: Email address for testing
            
        Returns:
            True if test email sent successfully
        """
        if not self.client:
            logger.error("❌ SendGrid not configured")
            return False
        
        try:
            message = Mail(
                from_email=Email(SENDER_EMAIL, SENDER_NAME),
                to_emails=To(test_email),
                subject="🧪 Test Email - Sentiment Bot",
                html_content=Content("text/html", """
                    <h1>🎉 Success!</h1>
                    <p>Your SendGrid email service is configured correctly.</p>
                    <p>You're ready to send daily digests!</p>
                """)
            )
            
            response = self.client.send(message)
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"✅ Test email sent to {test_email}")
                return True
            else:
                logger.warning(f"⚠️ Test email status: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Test email failed: {e}")
            return False

if __name__ == "__main__":
    # Test email service when run directly
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    service = EmailService()
    
    # Send test email
    test_address = input("Enter test email address: ")
    if test_address:
        result = service.send_test_email(test_address)
        print(f"\n✅ Test result: {'SUCCESS' if result else 'FAILED'}")
