"""Celery application configuration for Sentiment Trading Bot.

This module configures Celery for background task processing:
- Worker: Executes async tasks
- Beat: Schedules periodic tasks
- Redis: Message broker and result backend

Features powered by Celery:
1. Price alerts monitoring (every 15 minutes)
2. Morning Briefing (daily at 8am) - combines Daily Insights + Bonus Trade
3. AI Recommendations (manual via /recommend command)

Last updated: 2026-02-06 10:07 CET
"""

import os
import sys
import logging
from celery import Celery
from celery.schedules import crontab

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Celery app
app = Celery(
    "sentiment_trading_bot",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    include=[
        "backend.tasks.alerts_checker",
        "backend.tasks.ai_recommender",  # Manual /recommend command
        "backend.tasks.morning_briefing",  # NEW: Combined daily digest
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
    
    # NEW: Morning Briefing - daily at 8:00 AM CET
    # Combines: Daily Insights + Bonus Trade of the Day
    # (AI Recommendations now manual via /recommend command)
    "send-morning-briefing": {
        "task": "backend.tasks.morning_briefing.send_morning_briefing",
        "schedule": crontab(hour=8, minute=0),  # 8:00 AM daily
        "options": {"expires": 3600},  # Expire after 1h
    },
}

# Force print configuration info to stderr (always visible in Railway logs)
config_banner = f"""
{'='*70}
🚀 CELERY CONFIGURATION LOADED - MORNING BRIEFING ACTIVE
{'='*70}
📦 Tasks included: {len(app.conf.include)} modules
   1. backend.tasks.alerts_checker
   2. backend.tasks.ai_recommender (manual via /recommend)
   3. backend.tasks.morning_briefing ⭐ NEW

⏰ Beat schedules: {len(app.conf.beat_schedule)} tasks configured
   1. check-price-alerts     → Every 15 minutes
   2. send-morning-briefing  → Daily 08:00 CET ⭐ NEW

📋 Morning Briefing includes:
   ✓ Portfolio metrics (value, 24h change, top performer)
   ✓ AI position advice (personalized BUY/HOLD/SELL)
   ✓ Bonus Trade of the Day (best opportunity)
   ✓ Market news summary

🎯 Next execution: Tomorrow 08:00 CET
{'='*70}
"""

# Print to stderr (guaranteed to appear in logs)
print(config_banner, file=sys.stderr, flush=True)

# Also log it
logger.info("Celery configuration loaded successfully")
logger.info(f"Tasks: {len(app.conf.include)} modules, Schedules: {len(app.conf.beat_schedule)} tasks")

if __name__ == "__main__":
    app.start()
