#!/bin/bash
# Railway automatic database initialization script
# Runs before starting services to ensure database schema is up-to-date

set -e  # Exit on error

echo "🚀 Starting Railway initialization..."
echo ""

echo "📍 Current directory: $(pwd)"
echo "📦 Python version: $(python --version)"
echo ""

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "❌ ERROR: DATABASE_URL environment variable not set"
    exit 1
fi

echo "✅ DATABASE_URL is set"
echo "   URL: ${DATABASE_URL:0:50}..."
echo ""

# Navigate to backend directory
cd backend

echo "📊 Initializing database tables..."
python init_portfolio_tables.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Database initialization completed successfully!"
    echo ""
else
    echo ""
    echo "❌ Database initialization failed!"
    echo ""
    exit 1
fi

echo "🎉 Railway initialization complete - ready to start services"
echo ""
