# Procfile for Railway deployment
# Defines which processes to run

# Main Telegram bot
web: cd backend && python bot.py

# Celery worker (processes background tasks)
worker: cd backend && celery -A celery_app worker --loglevel=info --concurrency=4

# Celery beat (scheduler for periodic tasks)
beat: cd backend && celery -A celery_app beat --loglevel=info
