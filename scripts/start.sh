#!/bin/bash
# Railway startup script - Runs database init then starts bot
# This ensures portfolio tables exist before bot starts

set -e  # Exit on any error

echo "========================================"
echo "🚀 Starting Sentiment Trading Bot"
echo "========================================"
echo ""

# Check DATABASE_URL
if [ -z "$DATABASE_URL" ]; then
    echo "❌ ERROR: DATABASE_URL not set"
    exit 1
fi

echo "✅ DATABASE_URL configured"
echo "   ${DATABASE_URL:0:30}..."
echo ""

# Navigate to backend
cd /app/backend

echo "📊 Initializing portfolio tables..."
if python init_portfolio_tables.py; then
    echo "✅ Portfolio tables ready"
else
    echo "⚠️  Warning: Portfolio init failed (tables may already exist)"
    echo "   Continuing anyway..."
fi

echo ""
echo "🤖 Starting Telegram bot with FastAPI..."
echo "========================================"
echo ""

# Start uvicorn
cd /app
exec python -m uvicorn backend.bot_webhook:app --host 0.0.0.0 --port 8080
