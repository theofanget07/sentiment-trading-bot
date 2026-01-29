#!/bin/bash
# Start script for Telegram bot on Railway

echo "🚀 Starting Telegram Bot..."
echo "Working directory: $(pwd)"
echo "Contents: $(ls -la)"

cd /app || exit 1
echo "Changed to: $(pwd)"
echo "Backend exists: $(ls -la backend/ 2>&1)"

# Start the bot
exec python -m backend.bot
