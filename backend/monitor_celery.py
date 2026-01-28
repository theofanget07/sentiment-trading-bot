#!/usr/bin/env python
"""Monitor Celery tasks and database stats."""
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
import logging

load_dotenv()

from database import get_db_session
from models import Article, Analysis, User, SentimentEnum

logger = logging.getLogger(__name__)

def print_section(title: str):
    """Print formatted section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def get_database_stats():
    """Get current database statistics."""
    print_section("📊 DATABASE STATS")
    
    with get_db_session() as db:
        # Total articles
        total_articles = db.query(Article).count()
        print(f"Total Articles: {total_articles}")
        
        # Analyzed articles
        analyzed = db.query(Article).filter(Article.is_analyzed == True).count()
        unanalyzed = total_articles - analyzed
        print(f"Analyzed: {analyzed} ({(analyzed/total_articles*100 if total_articles else 0):.1f}%)")
        print(f"Unanalyzed: {unanalyzed}")
        
        # Sentiment distribution
        print("\nSentiment Distribution:")
        for sentiment in SentimentEnum:
            count = db.query(Article).filter(
                Article.sentiment == sentiment
            ).count()
            if count > 0:
                print(f"  {sentiment.name}: {count}")
        
        # Recent articles (last 2 hours)
        two_hours_ago = datetime.now() - timedelta(hours=2)
        recent = db.query(Article).filter(
            Article.fetched_at >= two_hours_ago
        ).count()
        print(f"\nFetched last 2h: {recent}")
        
        # Recent analyses (last 2 hours)
        recent_analyzed = db.query(Article).filter(
            Article.analyzed_at >= two_hours_ago,
            Article.is_analyzed == True
        ).count()
        print(f"Analyzed last 2h: {recent_analyzed}")
        
        # High confidence articles
        high_conf = db.query(Article).filter(
            Article.confidence >= 0.80,
            Article.is_analyzed == True
        ).count()
        print(f"\nHigh confidence (≥80%): {high_conf}")
        
        # Average confidence
        articles_with_conf = db.query(Article).filter(
            Article.confidence.isnot(None)
        ).all()
        if articles_with_conf:
            avg_conf = sum(a.confidence for a in articles_with_conf) / len(articles_with_conf)
            print(f"Average confidence: {avg_conf:.1%}")
        
        # Users
        total_users = db.query(User).count()
        print(f"\nTotal Users: {total_users}")
        
        # Total analyses
        total_analyses = db.query(Analysis).count()
        print(f"Total Analyses: {total_analyses}")

def get_recent_articles(limit: int = 10):
    """Display recent articles with sentiment."""
    print_section(f"📰 LAST {limit} ANALYZED ARTICLES")
    
    with get_db_session() as db:
        recent = db.query(Article).filter(
            Article.is_analyzed == True
        ).order_by(
            Article.analyzed_at.desc()
        ).limit(limit).all()
        
        if not recent:
            print("⚠️  No analyzed articles yet")
            return
        
        for i, article in enumerate(recent, 1):
            sentiment_emoji = {
                SentimentEnum.BULLISH: "📈",
                SentimentEnum.BEARISH: "📉",
                SentimentEnum.NEUTRAL: "➡️"
            }.get(article.sentiment, "❓")
            
            print(f"{i}. {sentiment_emoji} {article.sentiment.name} ({article.confidence:.0%})")
            print(f"   {article.title[:70]}...")
            print(f"   Source: {article.source} | {article.analyzed_at.strftime('%Y-%m-%d %H:%M')}")
            print()

def get_celery_scheduled_tasks():
    """Display Celery Beat scheduled tasks."""
    print_section("⏰ CELERY BEAT SCHEDULE")
    
    from celery_app import app
    
    for name, task in app.conf.beat_schedule.items():
        print(f"• {name}")
        print(f"  Task: {task['task']}")
        print(f"  Schedule: {task['schedule']}")
        print()

def check_system_health():
    """Check system health status."""
    print_section("✅ SYSTEM HEALTH CHECK")
    
    checks = []
    
    # Check Redis
    try:
        import redis
        r = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        r.ping()
        checks.append(("✅", "Redis", "Connected"))
    except Exception as e:
        checks.append(("❌", "Redis", f"Error: {e}"))
    
    # Check PostgreSQL
    try:
        with get_db_session() as db:
            db.execute("SELECT 1")
        checks.append(("✅", "PostgreSQL", "Connected"))
    except Exception as e:
        checks.append(("❌", "PostgreSQL", f"Error: {e}"))
    
    # Check environment variables
    required_vars = [
        "DATABASE_URL",
        "REDIS_URL",
        "PERPLEXITY_API_KEY",
        "TELEGRAM_BOT_TOKEN"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        checks.append(("⚠️ ", "Environment", f"Missing: {', '.join(missing_vars)}"))
    else:
        checks.append(("✅", "Environment", "All variables set"))
    
    # Display checks
    for emoji, component, status in checks:
        print(f"{emoji} {component}: {status}")

def main():
    """Main monitoring function."""
    print("\n" + "="*60)
    print("  🚀 SENTIMENT TRADING BOT - CELERY MONITOR")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*60)
    
    try:
        check_system_health()
        get_celery_scheduled_tasks()
        get_database_stats()
        get_recent_articles(limit=5)
        
        print_section("🎯 NEXT STEPS")
        print("• Run this script anytime: python monitor_celery.py")
        print("• Check Celery logs in the terminal where you started it")
        print("• Watch database grow with: watch -n 10 'python monitor_celery.py'")
        print("")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.WARNING,
        format='%(message)s'
    )
    main()
