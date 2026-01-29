# Procfile for Railway deployment
# Defines which processes to run

# Main Telegram bot
web: python bot.py

# Celery worker (processes background tasks)  
worker: python -m celery -A backend.celery_app worker --loglevel=info --concurrency=4

# Celery beat (scheduler for periodic tasks)
beat: python -m celery -A backend.celery_app beat --loglevel=info
