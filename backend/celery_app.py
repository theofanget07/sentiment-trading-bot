"""Celery configuration and background tasks."""
import os
from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

# Redis URL for Celery broker
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Celery app
app = Celery(
    "sentiment_bot",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=['tasks']  # Import tasks module
)

# Celery configuration
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=100,
)

# Celery Beat schedule for periodic tasks
app.conf.beat_schedule = {
    # Fetch news every 30 minutes
    'fetch-crypto-news': {
        'task': 'tasks.fetch_news_task',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
    },
    # Analyze unanalyzed articles every hour
    'analyze-articles': {
        'task': 'tasks.analyze_articles_task',
        'schedule': crontab(minute=0),  # Every hour at :00
    },
    # Send daily digest at 8:00 AM UTC
    'send-daily-digest': {
        'task': 'tasks.send_daily_digest_task',
        'schedule': crontab(hour=8, minute=0),  # 8:00 AM UTC
    },
    # Post high-confidence signals to Telegram channel every 2 hours
    'post-telegram-signals': {
        'task': 'tasks.post_telegram_signals_task',
        'schedule': crontab(minute=0, hour='*/2'),  # Every 2 hours
    },
    # Clean old data weekly (Sunday at 3:00 AM)
    'cleanup-old-data': {
        'task': 'tasks.cleanup_old_data_task',
        'schedule': crontab(hour=3, minute=0, day_of_week=0),  # Sunday 3 AM
    },
}

if __name__ == '__main__':
    logger.info("🚀 Starting Celery worker...")
    app.start()
