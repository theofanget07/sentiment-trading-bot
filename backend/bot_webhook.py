#!/usr/bin/env python3
"""
Telegram Bot with Webhook support for Railway deployment.
Uses FastAPI for native async support.
"""
import os
import logging
import json
import traceback as tb_module
from datetime import datetime
from io import BytesIO
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

import sys
sys.path.insert(0, os.path.dirname(__file__))

from sentiment_analyzer import analyze_sentiment

# Global DB Status
DB_AVAILABLE = False

# Fix: Use absolute import for Railway deployment
try:
    from backend.portfolio_manager import portfolio_manager
    from backend import redis_storage
except ImportError:
    # Fallback for local development
    from portfolio_manager import portfolio_manager
    import redis_storage

try:
    from backend.crypto_prices import format_price, get_crypto_price, is_symbol_supported
except ImportError:
    from crypto_prices import format_price, get_crypto_price, is_symbol_supported

try:
    from article_scraper import extract_article, extract_urls
except ImportError:
    def extract_article(url): return None
    def extract_urls(text): return []

# Feature 4: AI Recommendations handler
try:
    from backend.recommend_handler import recommend_command as recommend_handler_fn
except ImportError:
    from recommend_handler import recommend_command as recommend_handler_fn

# Stripe integration for Premium subscriptions
try:
    from backend.stripe_service import create_checkout_session, get_subscription_status, retrieve_subscription
    STRIPE_AVAILABLE = True
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("⚠️ Stripe service not available - Premium subscriptions disabled")
    STRIPE_AVAILABLE = False

# Stripe Webhook Router
try:
    from backend.routes.stripe_webhook import router as stripe_webhook_router
    STRIPE_WEBHOOK_AVAILABLE = True
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("⚠️ Stripe webhook router not available")
    STRIPE_WEBHOOK_AVAILABLE = False
    stripe_webhook_router = None

# Free/Premium Tier Management
try:
    from backend.tier_manager import tier_manager
    from backend.decorators import (
        premium_required,
        check_rate_limit,
        check_position_limit,
        check_alert_limit,
        check_recommendation_limit
    )
    TIER_SYSTEM_AVAILABLE = True
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("⚠️ Tier management not available")
    TIER_SYSTEM_AVAILABLE = False
    # Dummy decorators if tier system not available
    def premium_required(func): return func
    def check_rate_limit(func): return func
    def check_position_limit(func): return func
    def check_alert_limit(func): return func
    def check_recommendation_limit(func): return func

# Analytics System (Phase 1.5)
try:
    from backend.analytics_integration import (
        init_analytics,
        track_command,
        track_registration,
        track_conversion
    )
    from backend.routes.analytics import router as analytics_router
    ANALYTICS_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"⚠️ Analytics system not available: {e}")
    ANALYTICS_AVAILABLE = False
    ANALYTICS_IMPORT_ERROR = str(e)
    def init_analytics(): return False
    def track_command(*args, **kwargs): pass
    def track_registration(*args, **kwargs): pass
    def track_conversion(*args, **kwargs): pass
    analytics_router = None

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
PORT = int(os.getenv('PORT', 8080))

app = FastAPI()
application = None

# Include Stripe Webhook Router
if STRIPE_WEBHOOK_AVAILABLE and stripe_webhook_router:
    app.include_router(stripe_webhook_router)
    logger.info("✅ Stripe webhook router registered at /webhook/stripe")
else:
    logger.warning("⚠️ Stripe webhook router NOT registered - payments won't be processed")

# Include Analytics Router (Phase 1.5)
if ANALYTICS_AVAILABLE and analytics_router:
    app.include_router(analytics_router)
    logger.info("✅ Analytics router registered at /analytics")
else:
    logger.warning("⚠️ Analytics router NOT registered")

# ... [ALL THE COMMAND HANDLERS STAY THE SAME - skipping 700+ lines for brevity] ...

# Insert this diagnostic endpoint RIGHT HERE (after last command handler, before @app.get("/"))

@app.get("/analytics/debug")
async def analytics_debug():
    """
    Diagnostic endpoint to troubleshoot analytics initialization.
    """
    diagnostics = {
        "analytics_available": ANALYTICS_AVAILABLE,
        "analytics_router_present": analytics_router is not None,
        "tests": []
    }
    
    if not ANALYTICS_AVAILABLE:
        diagnostics["import_error"] = globals().get('ANALYTICS_IMPORT_ERROR', 'Unknown')
        diagnostics["status"] = "FAILED_IMPORT"
        return diagnostics
    
    # Test 1: Import analytics_integration
    try:
        from backend.analytics_integration import init_analytics as test_init
        diagnostics["tests"].append({"test": "import_analytics_integration", "status": "OK"})
    except Exception as e:
        diagnostics["tests"].append({
            "test": "import_analytics_integration",
            "status": "FAILED",
            "error": str(e),
            "traceback": tb_module.format_exc()
        })
        return diagnostics
    
    # Test 2: Import AnalyticsTracker
    try:
        from backend.analytics.tracker import AnalyticsTracker
        diagnostics["tests"].append({"test": "import_tracker", "status": "OK"})
    except Exception as e:
        diagnostics["tests"].append({
            "test": "import_tracker",
            "status": "FAILED",
            "error": str(e),
            "traceback": tb_module.format_exc()
        })
        return diagnostics
    
    # Test 3: Get Redis client
    try:
        from backend.redis_storage import get_redis_client
        redis_client = get_redis_client()
        diagnostics["tests"].append({"test": "get_redis_client", "status": "OK"})
    except Exception as e:
        diagnostics["tests"].append({
            "test": "get_redis_client",
            "status": "FAILED",
            "error": str(e),
            "traceback": tb_module.format_exc()
        })
        return diagnostics
    
    # Test 4: Initialize AnalyticsTracker
    try:
        tracker = AnalyticsTracker(redis_client)
        diagnostics["tests"].append({"test": "init_tracker", "status": "OK"})
    except Exception as e:
        diagnostics["tests"].append({
            "test": "init_tracker",
            "status": "FAILED",
            "error": str(e),
            "traceback": tb_module.format_exc()
        })
        return diagnostics
    
    # Test 5: Call init_analytics()
    try:
        result = test_init()
        diagnostics["tests"].append({
            "test": "call_init_analytics",
            "status": "OK" if result else "RETURNED_FALSE",
            "result": result
        })
    except Exception as e:
        diagnostics["tests"].append({
            "test": "call_init_analytics",
            "status": "FAILED",
            "error": str(e),
            "traceback": tb_module.format_exc()
        })
        return diagnostics
    
    # Test 6: Import analytics routes
    try:
        from backend.routes.analytics import router as test_router
        diagnostics["tests"].append({"test": "import_analytics_router", "status": "OK"})
    except Exception as e:
        diagnostics["tests"].append({
            "test": "import_analytics_router",
            "status": "FAILED",
            "error": str(e),
            "traceback": tb_module.format_exc()
        })
        return diagnostics
    
    diagnostics["status"] = "ALL_TESTS_PASSED"
    return diagnostics

# [Rest of the file continues with @app.get("/"), @app.get("/health"), etc. - keeping all existing code]
