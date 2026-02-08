"""Celery application configuration for Sentiment Trading Bot.

This module configures Celery for background task processing:
- Worker: Executes async tasks
- Beat: Schedules periodic tasks
- Redis: Message broker and result backend

Features powered by Celery:
1. Price alerts monitoring (every 15 minutes)
2. Morning Briefing (daily at 8am) - combines Daily Insights + Bonus Trade
3. AI Recommendations (manual via /recommend command)

Last updated: 2026-02-08 19:50 CET
"""

import os
import sys
import logging
from celery import Celery
from celery.schedules import crontab
from datetime import datetime, timedelta, timezone

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
    task_time_limit=600,  # 10 minutes max per task (increased for morning briefing)
    task_soft_time_limit=540,  # 9 minutes soft limit
    
    # Worker settings
    worker_prefetch_multiplier=1,  # One task at a time per worker
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks (reduced)
    
    # Result backend
    result_expires=3600,  # Results expire after 1 hour
    result_backend_transport_options={"master_name": "mymaster"},
    
    # Retry settings
    task_acks_late=True,  # Acknowledge task after execution
    task_reject_on_worker_lost=True,
    
    # Beat scheduler settings
    beat_max_loop_interval=5,  # Check schedule every 5 seconds (default is 5)
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
        "schedule": crontab(hour=8, minute=0),  # 8:00 AM CET daily
        "options": {
            "expires": 3600,  # Expire after 1h
            "time_limit": 600,  # 10 min timeout
        },
    },
}

# Calculate next morning briefing time (using UTC+1 for CET)
try:
    # CET = UTC+1 (Europe/Zurich)
    cet_offset = timezone(timedelta(hours=1))
    now_cet = datetime.now(cet_offset)
    
    # Next 8:00 AM CET
    next_run = now_cet.replace(hour=8, minute=0, second=0, microsecond=0)
    if now_cet.hour >= 8:
        # Already past 8 AM today, schedule for tomorrow
        next_run = next_run + timedelta(days=1)
    
    next_run_str = next_run.strftime("%Y-%m-%d %H:%M:%S %Z")
except Exception as e:
    next_run_str = "(calculation error)"
    logger.error(f"Error calculating next run time: {e}")

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

🎯 Next morning briefing: {next_run_str}

⚙️  Settings:
   • Timezone: {app.conf.timezone}
   • Task time limit: {app.conf.task_time_limit}s
   • Beat check interval: {app.conf.beat_max_loop_interval}s
{'='*70}
"""

# Print to stderr (guaranteed to appear in logs)
print(config_banner, file=sys.stderr, flush=True)

# Also log it
logger.info("Celery configuration loaded successfully")
logger.info(f"Tasks: {len(app.conf.include)} modules, Schedules: {len(app.conf.beat_schedule)} tasks")
logger.info(f"Next morning briefing scheduled for: {next_run_str}")

if __name__ == "__main__":
    app.start()
