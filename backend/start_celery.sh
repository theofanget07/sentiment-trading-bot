#!/bin/bash
# Start Celery Worker + Beat for 24/7 automation
# Week 2 Day 2 - Sentiment Trading Bot

echo "🚀 Starting Celery Worker + Beat for 24/7 automation..."
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Redis is running
echo "📍 Step 1/3: Checking Redis connection..."
if redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Redis is running${NC}"
else
    echo -e "${RED}❌ Redis is not running. Start it with: brew services start redis${NC}"
    exit 1
fi

# Check if venv is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not activated${NC}"
    echo "Activating venv..."
    source ../venv/bin/activate
fi

# Check environment variables
echo ""
echo "📍 Step 2/3: Checking environment variables..."
if [ -z "$DATABASE_URL" ]; then
    echo -e "${YELLOW}⚠️  DATABASE_URL not set, loading from .env${NC}"
    export $(grep -v '^#' .env | xargs)
fi

echo -e "${GREEN}✅ Environment loaded${NC}"

# Start Celery Worker + Beat
echo ""
echo "📍 Step 3/3: Starting Celery..."
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

# Start Celery with both worker and beat in one process (development mode)
celery -A celery_app worker --beat --loglevel=info

# Note: In production, you should run worker and beat in separate processes:
# Terminal 1: celery -A celery_app worker --loglevel=info
# Terminal 2: celery -A celery_app beat --loglevel=info
