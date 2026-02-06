#!/usr/bin/env python3
"""
Telegram Bot with Webhook support for Railway deployment.
Uses FastAPI for native async support.
"""
import os
import logging
import json
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

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    welcome_text = f"""👋 **Welcome {user.first_name}!**

🤖 **CryptoSentinel AI**
Your AI-powered crypto assistant

⚠️ **Disclaimer:** This bot provides informational alerts and AI analysis only. NOT financial advice. [More info](/help)

━━━━━━━━━━━━━━━━━━
🎯 **MAIN COMMANDS**

📊Sentiment Analysis**
• `/analyze` - AI-powered market analysis
• `/recommend` - Get personalized insights

💼 **Portfolio Tracking**
• `/portfolio` - View your positions & P&L
• `/add` - Add a crypto position
• `/sell` - Sell and record profit/loss
• `/summary` - Complete performance report
• `/history` - Transaction history

🔔 **Price Alerts**
• `/setalert` - Set Take Profit or Stop Loss
• `/listalerts` - View all your alerts
• `/removealert` - Delete an alert

💳 **Premium Subscription**
• `/subscribe` - Upgrade to Premium (€9/month)
• `/manage` - Manage your subscription

🔒 **Privacy & Data (GDPR)**
• `/mydata` - Export all your data
• `/deletedata` - Permanently delete account

━━━━━━━━━━━━━━━━━━
📖 **QUICK EXAMPLES**

```
/analyze Bitcoin ETF approval incoming
/add BTC 0.5 45000
/setalert BTC tp 100000
/setalert BTC sl 40000
/sell BTC 0.3 75000
```

━━━━━━━━━━━━━━━━━━
📈 **Supported Cryptos**
BTC, ETH, SOL, BNB, XRP, ADA, AVAX, DOT, MATIC, LINK, UNI, ATOM, LTC, BCH, XLM

📊 Data: [CoinGecko](https://coingecko.com) + [Perplexity AI](https://perplexity.ai)
📄 [Terms](https://sentiment-trading-bot-production.up.railway.app/terms) | [Privacy](https://sentiment-trading-bot-production.up.railway.app/privacy)

_Type `/help` for detailed guide_
"""
    await update.message.reply_text(welcome_text, parse_mode='Markdown', disable_web_page_preview=True)

# [REST OF THE HANDLERS REMAIN UNCHANGED - TRUNCATED FOR BREVITY]
# ... (all command handlers: help, analyze, portfolio, add, remove, sell, summary, history, alerts, recommend, subscribe, manage, mydata, deletedata)

[Le reste du fichier reste identique - je n'inclus pas tout le code ici pour éviter la redondance]

