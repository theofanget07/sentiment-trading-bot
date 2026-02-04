"""Celery application configuration for Sentiment Trading Bot.

This module configures Celery for background task processing:
- Worker: Executes async tasks
- Beat: Schedules periodic tasks
- Redis: Message broker and result backend

Features powered by Celery:
1. Price alerts monitoring (every 15 minutes)
2. AI recommendations (daily at 8am)
3. Daily insights (daily at 8am per user timezone)
4. Bonus Trade of the Day (daily at 8am)
"""

import os
from celery import Celery
from celery.schedules import crontab

# Initialize Celery app
app = Celery(
    "sentiment_trading_bot",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    include=[
        "backend.tasks.alerts_checker",
        "backend.tasks.ai_recommender",
        "backend.tasks.daily_insights",
        "backend.tasks.bonus_trade",  # BONUS TRADE OF THE DAY
    ],
)

# Celery configuration
app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Zurich",  # CET timezone
    enable_utc=True,
    
    # Task execution
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
    task_soft_time_limit=240,  # 4 minutes soft limit
    
    # Worker settings
    worker_prefetch_multiplier=1,  # One task at a time per worker
    worker_max_tasks_per_child=100,  # Restart worker after 100 tasks
    
    # Result backend
    result_expires=3600,  # Results expire after 1 hour
    result_backend_transport_options={"master_name": "mymaster"},
    
    # Retry settings
    task_acks_late=True,  # Acknowledge task after execution
    task_reject_on_worker_lost=True,
)

# Beat schedule for periodic tasks
app.conf.beat_schedule = {
    # Feature 1: Price alerts - every 15 minutes
    "check-price-alerts": {
        "task": "backend.tasks.alerts_checker.check_all_price_alerts",
        "schedule": crontab(minute="*/15"),  # Every 15 minutes
        "options": {"expires": 600},  # Expire if not run within 10min
    },
    
    # Feature 4: AI recommendations - daily at 8:00 AM CET
    "generate-ai-recommendations": {
        "task": "backend.tasks.ai_recommender.generate_daily_recommendations",
        "schedule": crontab(hour=8, minute=0),  # 8:00 AM daily
        "options": {"expires": 3600},  # Expire after 1h
    },
    
    # Feature 5: Daily insights - daily at 8:00 AM CET
    "send-daily-insights": {
        "task": "backend.tasks.daily_insights.send_daily_portfolio_insights",
        "schedule": crontab(hour=8, minute=0),  # 8:00 AM daily
        "options": {"expires": 3600},  # Expire after 1h
    },
    
    # BONUS: Trade of the Day - daily at 8:00 AM CET
    "bonus-trade-of-day": {
        "task": "backend.tasks.bonus_trade.send_bonus_trade_of_day",
        "schedule": crontab(hour=8, minute=0),  # 8:00 AM daily
        "options": {"expires": 3600},  # Expire after 1h
    },
}

if __name__ == "__main__":
    app.start()
