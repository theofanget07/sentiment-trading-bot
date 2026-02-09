"""Celery application configuration for Sentiment Trading Bot.

This module configures Celery for background task processing:
- Worker: Executes async tasks
- Beat: Schedules periodic tasks
- Redis: Message broker and result backend

Features powered by Celery:
1. Price alerts monitoring (every 15 minutes at :02, :17, :32, :47)
2. Morning Briefing (daily at 7:00 UTC = 8:00 CET)
3. AI Recommendations (manual via /recommend command)

Last updated: 2026-02-09 17:00 CET
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
        "backend.tasks.morning_briefing",  # Combined daily digest
    ],
)

# Celery configuration
app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",  # Use UTC for consistency
    enable_utc=True,
    
    # Task execution
    task_track_started=True,
    task_time_limit=600,  # 10 minutes max per task
    task_soft_time_limit=540,  # 9 minutes soft limit
    
    # Worker settings
    worker_prefetch_multiplier=1,  # One task at a time per worker
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks
    
    # Result backend
    result_expires=3600,  # Results expire after 1 hour
    result_backend_transport_options={"master_name": "mymaster"},
    
    # Retry settings
    task_acks_late=True,  # Acknowledge task after execution
    task_reject_on_worker_lost=True,
    
    # Beat scheduler settings
    beat_max_loop_interval=5,  # Check schedule every 5 seconds
)

# Beat schedule for periodic tasks
app.conf.beat_schedule = {
    # Feature 1: Price alerts - every 15 minutes (OFFSET BY 2 MIN to avoid collision)
    "check-price-alerts": {
        "task": "backend.tasks.alerts_checker.check_all_price_alerts",
        "schedule": crontab(minute="2,17,32,47"),  # 07:02, 07:17, 07:32, 07:47 UTC
        "options": {"expires": 600},  # Expire if not run within 10min
    },
    
    # Morning Briefing - daily at 7:00 AM UTC (= 8:00 AM CET)
    # Combines: Daily Insights + Bonus Trade of the Day
    "send-morning-briefing": {
        "task": "backend.tasks.morning_briefing.send_morning_briefing",
        "schedule": crontab(hour=7, minute=0),  # 7:00 UTC = 8:00 CET (UTC+1)
        "options": {
            "expires": 3600,  # Expire after 1h
            "time_limit": 600,  # 10 min timeout
        },
    },
}

# Calculate next morning briefing time
try:
    # Calculate next 7:00 UTC (= 8:00 CET)
    now_utc = datetime.now(timezone.utc)
    
    # Next 7:00 AM UTC
    next_run = now_utc.replace(hour=7, minute=0, second=0, microsecond=0)
    if now_utc.hour >= 7:
        # Already past 7 AM UTC today, schedule for tomorrow
        next_run = next_run + timedelta(days=1)
    
    # Convert to CET for display (UTC+1)
    cet_offset = timezone(timedelta(hours=1))
    next_run_cet = next_run.astimezone(cet_offset)
    next_run_str = next_run_cet.strftime("%Y-%m-%d %H:%M:%S CET")
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
   3. backend.tasks.morning_briefing ⭐ FIXED

⏰ Beat schedules: {len(app.conf.beat_schedule)} tasks configured
   1. check-price-alerts     → Every 15min at :02,:17,:32,:47 ⭐ FIXED COLLISION
   2. send-morning-briefing  → Daily 07:00 UTC (08:00 CET) ⭐ FIXED TIMEZONE

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

🔧 Recent fixes:
   • Fixed timezone: 7:00 UTC = 8:00 CET (was 8:00 UTC = 9:00 CET)
   • Fixed collision: Price alerts offset by 2 min
   • Next fixes: Parallel Perplexity calls + better error handling
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
