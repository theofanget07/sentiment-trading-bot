#!/bin/bash
# Smart entrypoint for multi-service Railway deployment
# This script detects which service to start based on SERVICE_TYPE environment variable

set -e

echo "🚀 Starting Railway service..."
echo "📦 SERVICE_TYPE: ${SERVICE_TYPE:-not set}"

case "$SERVICE_TYPE" in
  web)
    echo "🌐 Starting Web Service (FastAPI + Telegram Bot)"
    cd backend && exec uvicorn bot_webhook:app --host 0.0.0.0 --port ${PORT:-8080}
    ;;
  
  worker)
    echo "⚙️  Starting Celery Worker"
    exec python -m celery -A backend.celery_app worker --loglevel=info --concurrency=4
    ;;
  
  beat)
    echo "⏰ Starting Celery Beat Scheduler"
    exec python -m celery -A backend.celery_app beat --loglevel=info
    ;;
  
  *)
    echo "❌ ERROR: SERVICE_TYPE not set or invalid!"
    echo "Valid values: web, worker, beat"
    echo "Set SERVICE_TYPE environment variable in Railway Dashboard"
    exit 1
    ;;
esac
