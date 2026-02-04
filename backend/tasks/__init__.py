"""Tasks package - Celery background tasks.

This package contains:
- alerts_checker.py: Feature 1 - Price alerts monitoring (every 15min)
- ai_recommender.py: Feature 4 - AI recommendations engine (daily)
- daily_insights.py: Feature 5 - Daily portfolio summary (8am)

All Celery tasks should be placed here with clear separation.
Each task should be idempotent and include proper error handling.
"""
