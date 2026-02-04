"""Backend package for Sentiment Trading Bot.

This package contains:
- bot_webhook.py: Telegram bot handlers & FastAPI routes
- portfolio_manager.py: Portfolio management logic (Redis-based)
- redis_storage.py: Redis storage layer
- crypto_prices.py: CoinGecko API price fetching
- sentiment_analyzer.py: Perplexity AI sentiment analysis
- news_fetcher.py: RSS news fetching
- celery_app.py: Celery configuration (async tasks)
- services/: API wrappers and external services
- tasks/: Celery background tasks
"""

__version__ = "1.3.0"
