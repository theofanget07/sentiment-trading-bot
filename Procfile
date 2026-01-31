# Procfile for Railway deployment
# Telegram bot with FastAPI webhook mode

# Main service: Bot with automatic DB initialization in startup event
web: python -m uvicorn backend.bot_webhook:app --host 0.0.0.0 --port $PORT
