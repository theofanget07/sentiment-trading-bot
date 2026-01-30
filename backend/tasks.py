"""Celery background tasks."""
from backend.celery_app import app
from backend.news_fetcher import NewsFetcher
from backend.sentiment_analyzer import SentimentAnalyzer
from backend.database import get_db_session
from backend.models import Article, User, Analysis, SentimentEnum, SubscriptionLevel
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

@app.task(name='tasks.fetch_news_task')
def fetch_news_task():
    """
    Fetch crypto news from RSS feeds and Reddit.
    Runs every 30 minutes.
    """
    logger.info("🔍 Starting news fetch task...")
    
    try:
        fetcher = NewsFetcher()
        stats = fetcher.fetch_and_save_all(hours_back=1)  # Last 1 hour to avoid duplicates
        
        logger.info(f"✅ News fetch completed: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"❌ News fetch failed: {e}")
        raise

@app.task(name='tasks.analyze_articles_task')
def analyze_articles_task(batch_size: int = 20):
    """
    Analyze unanalyzed articles in the database.
    Runs every hour.
    
    Args:
        batch_size: Number of articles to analyze per run (default 20)
    """
    logger.info("🧠 Starting article analysis task...")
    
    try:
        analyzer = SentimentAnalyzer()
        analyzed_count = 0
        
        with get_db_session() as db:
            # Get unanalyzed articles
            unanalyzed = db.query(Article).filter(
                Article.is_analyzed == False
            ).limit(batch_size).all()
            
            logger.info(f"📄 Found {len(unanalyzed)} unanalyzed articles")
            
            for article in unanalyzed:
                try:
                    # Analyze article title + content
                    text_to_analyze = f"{article.title}. {article.content[:500]}"
                    result = analyzer.analyze(text_to_analyze)
                    
                    # Update article with sentiment
                    article.sentiment = SentimentEnum[result['sentiment'].upper()]
                    article.confidence = result['confidence']
                    article.reasoning = result['reasoning']
                    article.is_analyzed = True
                    article.analyzed_at = datetime.now()
                    
                    analyzed_count += 1
                    logger.info(
                        f"  ✅ {article.title[:50]}... -> "
                        f"{result['sentiment'].upper()} ({result['confidence']:.0%})"
                    )
                    
                except Exception as e:
                    logger.error(f"  ❌ Error analyzing article {article.id}: {e}")
                    continue
            
            db.commit()
        
        logger.info(f"✅ Analyzed {analyzed_count} articles")
        return {'analyzed': analyzed_count}
        
    except Exception as e:
        logger.error(f"❌ Article analysis failed: {e}")
        raise

@app.task(name='tasks.send_daily_digest_task')
def send_daily_digest_task():
    """
    Send daily email digest to premium users.
    Runs daily at 8:00 AM UTC.
    """
    logger.info("📧 Starting daily digest task...")
    
    try:
        # Import here to avoid circular imports
        from backend.email_service import EmailService
        
        email_service = EmailService()
        sent_count = 0
        
        with get_db_session() as db:
            # Get premium users with email
            premium_users = db.query(User).filter(
                User.subscription_level == SubscriptionLevel.PREMIUM,
                User.email.isnot(None),
                User.is_active == True
            ).all()
            
            logger.info(f"👥 Found {len(premium_users)} premium users")
            
            # Get top articles from last 24 hours
            yesterday = datetime.now() - timedelta(days=1)
            top_articles = db.query(Article).filter(
                Article.is_analyzed == True,
                Article.analyzed_at >= yesterday,
                Article.confidence >= 0.7  # Only high confidence
            ).order_by(
                Article.confidence.desc()
            ).limit(10).all()
            
            logger.info(f"📊 Found {len(top_articles)} high-confidence articles")
            
            if not top_articles:
                logger.warning("⚠️ No articles to send in digest")
                return {'sent': 0, 'reason': 'no_articles'}
            
            # Send digest to each premium user
            for user in premium_users:
                try:
                    success = email_service.send_daily_digest(
                        user_email=user.email,
                        articles=top_articles
                    )
                    
                    if success:
                        sent_count += 1
                        logger.info(f"  ✅ Sent digest to {user.email}")
                    else:
                        logger.warning(f"  ⚠️ Failed to send digest to {user.email}")
                        
                except Exception as e:
                    logger.error(f"  ❌ Error sending to {user.email}: {e}")
                    continue
        
        logger.info(f"✅ Sent {sent_count} digests")
        return {'sent': sent_count}
        
    except Exception as e:
        logger.error(f"❌ Daily digest task failed: {e}")
        raise

@app.task(name='tasks.post_telegram_signals_task')
def post_telegram_signals_task():
    """
    Post high-confidence signals to Telegram channel.
    Runs every 2 hours.
    """
    logger.info("📱 Starting Telegram signals task...")
    
    try:
        # Import here to avoid circular imports
        from backend.channel_broadcaster import ChannelBroadcaster
        
        broadcaster = ChannelBroadcaster()
        
        with get_db_session() as db:
            # Get high-confidence articles from last 2 hours not yet posted
            two_hours_ago = datetime.now() - timedelta(hours=2)
            
            high_confidence = db.query(Article).filter(
                Article.is_analyzed == True,
                Article.analyzed_at >= two_hours_ago,
                Article.confidence >= 0.80  # Only very high confidence
            ).order_by(
                Article.confidence.desc()
            ).limit(5).all()
            
            logger.info(f"📈 Found {len(high_confidence)} high-confidence articles")
            
            posted_count = 0
            for article in high_confidence:
                try:
                    success = broadcaster.post_signal(article)
                    if success:
                        posted_count += 1
                        logger.info(f"  ✅ Posted: {article.title[:50]}...")
                    else:
                        logger.warning(f"  ⚠️ Failed to post: {article.title[:50]}...")
                        
                except Exception as e:
                    logger.error(f"  ❌ Error posting article {article.id}: {e}")
                    continue
        
        logger.info(f"✅ Posted {posted_count} signals to Telegram")
        return {'posted': posted_count}
        
    except Exception as e:
        logger.error(f"❌ Telegram signals task failed: {e}")
        raise

@app.task(name='tasks.cleanup_old_data_task')
def cleanup_old_data_task(days_to_keep: int = 30):
    """
    Clean up old articles and analyses.
    Runs weekly on Sunday at 3:00 AM.
    
    Args:
        days_to_keep: Number of days to keep data (default 30)
    """
    logger.info("🧹 Starting cleanup task...")
    
    try:
        with get_db_session() as db:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            # Delete old articles
            deleted_articles = db.query(Article).filter(
                Article.fetched_at < cutoff_date
            ).delete(synchronize_session=False)
            
            # Delete old analyses
            deleted_analyses = db.query(Analysis).filter(
                Analysis.analyzed_at < cutoff_date
            ).delete(synchronize_session=False)
            
            db.commit()
            
            logger.info(
                f"✅ Cleanup complete: "
                f"{deleted_articles} articles, {deleted_analyses} analyses deleted"
            )
            
            return {
                'deleted_articles': deleted_articles,
                'deleted_analyses': deleted_analyses,
            }
            
    except Exception as e:
        logger.error(f"❌ Cleanup task failed: {e}")
        raise

if __name__ == "__main__":
    # Test tasks when run directly
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("🧪 Testing tasks...")
    print("\n1. Fetch news:")
    result = fetch_news_task()
    print(f"   Result: {result}")
    
    print("\n2. Analyze articles:")
    result = analyze_articles_task(batch_size=5)
    print(f"   Result: {result}")
    
    print("\n✅ Tests complete!")
