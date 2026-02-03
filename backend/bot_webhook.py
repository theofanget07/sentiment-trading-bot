#!/usr/bin/env python3
"""
Telegram Bot with Webhook support for Railway deployment.
Uses FastAPI for native async support.
"""
import os
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from telegram import Update
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
    from backend.crypto_prices import format_price, get_crypto_price
except ImportError:
    from crypto_prices import format_price, get_crypto_price

try:
    from article_scraper import extract_article, extract_urls
except ImportError:
    def extract_article(url): return None
    def extract_urls(text): return []

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

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_status = "✅ Online" if DB_AVAILABLE else "⚠️ Offline"
    
    welcome_text = f"""
👋 **Bienvenue {user.first_name} !**

🤖 **Sentiment Trading Bot** - Ton assistant crypto intelligent

━━━━━━━━━━━━━━━━━━
📊 **STATUT SYSTÈME**
• Bot: ✅ Online
• Base de données: {db_status}

━━━━━━━━━━━━━━━━━━
🎯 **ANALYSE DE SENTIMENT** (toujours disponible)

• `/analyze <texte>` - Analyse AI du sentiment crypto
  _Ex: `/analyze Bitcoin hits new ATH after ETF approval`_

• **Envoyez un lien** - Scraping + analyse automatique d'articles
  _Ex: https://cointelegraph.com/..._

• **Envoyez du texte** (30+ caractères) - Analyse directe

━━━━━━━━━━━━━━━━━━
💼 **GESTION DE PORTFOLIO** (nécessite DB)

• `/portfolio` - Affiche ton portfolio avec prix actuels & P&L
  _Ex: BTC: 1 @ $45,000 → P&L: +$30,612 (+68%)_

• `/add <SYMBOL> <quantité> <prix>` - Ajoute une position
  _Ex: `/add BTC 0.5 45000`_
  _Ex: `/add ETH 10 2500`_

• `/remove <SYMBOL>` - Supprime une position
  _Ex: `/remove BTC`_

• `/summary` - Résumé global (P&L total, valeur investie)

• `/history` - Historique des 5 dernières transactions

━━━━━━━━━━━━━━━━━━
🚀 **CRYPTOS SUPPORTÉES**
BTC, ETH, SOL, BNB, XRP, ADA, AVAX, DOT, MATIC, LINK, UNI, ATOM, LTC, BCH, XLM

━━━━━━━━━━━━━━━━━━
💡 **FONCTIONNALITÉS**
• Analyse sentiment AI (Perplexity)
• Prix crypto temps réel (CoinGecko)
• Calcul P&L automatique
• Historique transactions
• Portfolio multi-cryptos

_Tape `/help` pour plus d'infos_
"""
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📚 **Guide Complet - Sentiment Trading Bot**

━━━━━━━━━━━━━━━━━━
🔍 **1. ANALYSE DE SENTIMENT**

Le bot utilise Perplexity AI pour analyser le sentiment crypto (BULLISH/BEARISH/NEUTRAL) avec un score de confiance.

**Méthodes d'analyse :**
• `/analyze <texte>` - Analyse un texte que tu fournis
• Envoyer un lien - Le bot scrape l'article automatiquement
• Envoyer du texte long - Détection automatique (30+ caractères)

**Exemple de résultat :**
🚀 **BULLISH** (89%)
💡 "Bitcoin montre une forte dynamique hausssière avec l'approbation des ETF..."

━━━━━━━━━━━━━━━━━━
💼 **2. GESTION DE PORTFOLIO**

**Ajouter une position :**
`/add BTC 1 45000`
→ Ajoute 1 BTC acheté à $45,000
→ Si tu détiens déjà du BTC, recalcule le prix moyen

**Voir ton portfolio :**
`/portfolio`
→ Affiche toutes tes positions avec :
  • Quantité détenue
  • Prix d'achat moyen
  • Prix actuel (temps réel)
  • Valeur actuelle
  • P&L en $ et %

**Supprimer une position :**
`/remove BTC`
→ Supprime complètement la position BTC

**Résumé global :**
`/summary`
→ Affiche ton P&L total sur tout le portfolio

**Historique :**
`/history`
→ Les 5 dernières transactions (BUY/REMOVE)

━━━━━━━━━━━━━━━━━━
🚀 **CRYPTOS DISPONIBLES**

Bitcoin (BTC), Ethereum (ETH), Solana (SOL), Binance Coin (BNB), Ripple (XRP), Cardano (ADA), Avalanche (AVAX), Polkadot (DOT), Polygon (MATIC), Chainlink (LINK), Uniswap (UNI), Cosmos (ATOM), Litecoin (LTC), Bitcoin Cash (BCH), Stellar (XLM)

━━━━━━━━━━━━━━━━━━
🛠️ **INFOS TECHNIQUES**

• **Storage :** Redis (ultra-rapide)
• **Prix :** CoinGecko API (temps réel)
• **AI :** Perplexity API (analyse sentiment)
• **Hosting :** Railway (24/7)

_Retour au menu : `/start`_
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = ' '.join(context.args)
    if not user_text or len(user_text) < 10:
        await update.message.reply_text(
            "⚠️ Please provide text to analyze.\n\n"
            "**Example:** `/analyze Bitcoin surges as ETFs see record inflows`",
            parse_mode='Markdown'
        )
        return
    
    urls = extract_urls(user_text)
    if urls:
        await analyze_url(update, urls[0])
    else:
        await analyze_text(update, user_text)

async def portfolio_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display user's crypto portfolio holdings with current prices."""
    if not DB_AVAILABLE:
        await update.message.reply_text(
            "⚠️ **Database Unavailable**\n\n"
            "The database is currently offline or connecting.\n"
            "Please try again in a few minutes.\n\n"
            "You can still use `/analyze` for sentiment!",
            parse_mode='Markdown'
        )
        return

    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or "User"
    
    logger.info(f"💼 /portfolio called by user {user_id} (@{username})")
    
    try:
        # Get portfolio with current prices
        portfolio = portfolio_manager.get_portfolio_with_prices(user_id, username)
        
        if not portfolio["positions"]:
            response = "💼 **Your Crypto Portfolio**\n\n"
            response += "_Your portfolio is empty._\n\n"
            response += "To add positions, use:\n"
            response += "`/add BTC 0.5 45000`\n\n"
            response += "**Supported cryptos:**\n"
            response += "BTC, ETH, SOL, BNB, XRP, ADA, AVAX, DOT, MATIC, LINK, UNI, ATOM, LTC, BCH, XLM"
        else:
            response = "💼 **Your Crypto Portfolio**\n"
            
            for symbol, pos in portfolio["positions"].items():
                qty = pos["quantity"]
                avg_price = pos["avg_price"]
                current_price = pos["current_price"]
                current_value = pos["current_value"]
                pnl_usd = pos["pnl_usd"]
                pnl_percent = pos["pnl_percent"]
                
                # Choose emoji based on P&L
                pnl_emoji = "🟢" if pnl_percent > 0 else ("🔴" if pnl_percent < 0 else "⚪")
                
                response += f"\n**{symbol}** {pnl_emoji}\n"
                response += f"  • Quantity: `{qty:.8g}`\n"
                response += f"  • Avg Price: `{format_price(avg_price)}`\n"
                response += f"  • Current: `{format_price(current_price)}`\n"
                response += f"  • Value: `{format_price(current_value)}`\n"
                response += f"  • P&L: `{pnl_usd:+,.2f} USD ({pnl_percent:+.2f}%)`"
            
            response += f"\n\n**Total Value:** `{format_price(portfolio['total_current_value'])}`"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        logger.info(f"✅ /portfolio response sent to {user_id}")
        
    except Exception as e:
        logger.error(f"❌ /portfolio error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        await update.message.reply_text(
            "❌ **Error**\n\nSomething went wrong with the database. Please try again.",
            parse_mode='Markdown'
        )

async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not DB_AVAILABLE:
        await update.message.reply_text("⚠️ Database offline. Cannot add position.", parse_mode='Markdown')
        return

    """Add a crypto position to portfolio."""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    # Validate arguments
    if len(context.args) != 3:
        await update.message.reply_text(
            "⚠️ **Usage:** `/add <symbol> <quantity> <price>`\n\n"
            "**Example:** `/add BTC 0.5 45000`",
            parse_mode='Markdown'
        )
        return
    
    symbol = context.args[0].upper()
    
    try:
        quantity = float(context.args[1])
        price = float(context.args[2])
    except ValueError:
        await update.message.reply_text("❌ Quantity and price must be numbers.", parse_mode='Markdown')
        return
    
    if quantity <= 0 or price <= 0:
        await update.message.reply_text("❌ Values must be positive.", parse_mode='Markdown')
        return
    
    try:
        result = portfolio_manager.add_position(user_id, symbol, quantity, price, username)
        current_price = get_crypto_price(symbol)
        
        response = f"✅ **Position {result['action'].capitalize()}**\n\n"
        response += f"**{symbol}**\n"
        response += f"  • Quantity: `{result['quantity']:.8g}`\n"
        response += f"  • Avg Price: `{format_price(result['avg_price'])}`\n"
        
        if current_price:
            current_value = result['quantity'] * current_price
            pnl_usd = current_value - (result['quantity'] * result['avg_price'])
            pnl_percent = ((current_price - result['avg_price']) / result['avg_price']) * 100
            
            response += f"\n📊 **Current Status:**\n"
            response += f"  • P&L: `{pnl_usd:+,.2f} USD ({pnl_percent:+.2f}%)`"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        logger.info(f"✅ /add {symbol} for user {user_id}")
        
    except Exception as e:
        logger.error(f"❌ /add error: {e}")
        await update.message.reply_text(f"❌ Error adding position. Is {symbol} supported?", parse_mode='Markdown')

async def remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not DB_AVAILABLE:
        await update.message.reply_text("⚠️ Database offline.", parse_mode='Markdown')
        return

    user_id = update.effective_user.id
    if len(context.args) != 1:
        await update.message.reply_text("⚠️ Usage: `/remove <symbol>`", parse_mode='Markdown')
        return
    
    symbol = context.args[0].upper()
    try:
        success = portfolio_manager.remove_position(user_id, symbol)
        if success:
            await update.message.reply_text(f"✅ `{symbol}` removed.", parse_mode='Markdown')
        else:
            await update.message.reply_text(f"⚠️ `{symbol}` not found in portfolio.", parse_mode='Markdown')
    except Exception as e:
        logger.error(f"❌ /remove error: {e}")
        await update.message.reply_text("❌ Error removing position.", parse_mode='Markdown')

async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not DB_AVAILABLE:
        await update.message.reply_text("⚠️ Database offline.", parse_mode='Markdown')
        return

    """Show portfolio summary with total P&L."""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or "User"
    
    try:
        portfolio = portfolio_manager.get_portfolio_with_prices(user_id, username)
        if not portfolio["positions"]:
            await update.message.reply_text("📊 **Portfolio Empty**\n\nUse `/add` to start.", parse_mode='Markdown')
            return
        
        total_pnl = portfolio["total_pnl_usd"]
        total_pnl_pct = portfolio["total_pnl_percent"]
        overall_emoji = "🚀" if total_pnl > 0 else "📉"
        
        response = f"{overall_emoji} **Portfolio Summary**\n"
        response += f"━━━━━━━━━━━━━━━━━━\n"
        response += f"**💰 Total P&L: `{total_pnl:+,.2f} USD ({total_pnl_pct:+.2f}%)`**\n"
        response += f"• Invested: `{format_price(portfolio['total_invested'])}`\n"
        response += f"• Current: `{format_price(portfolio['total_current_value'])}`"
        
        await update.message.reply_text(response, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"❌ /summary error: {e}")
        await update.message.reply_text("❌ Error generating summary.", parse_mode='Markdown')

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not DB_AVAILABLE:
        await update.message.reply_text("⚠️ Database offline.", parse_mode='Markdown')
        return
        
    user_id = update.effective_user.id
    try:
        transactions = portfolio_manager.get_transactions(user_id, limit=5)
        if not transactions:
            await update.message.reply_text("📃 No transactions yet.", parse_mode='Markdown')
            return
        
        response = "📃 **Last 5 Transactions**\n"
        for tx in transactions:
            response += f"\n{tx['action']} `{tx['symbol']}`: {tx['quantity']} @ {format_price(tx['price'])}"
        
        await update.message.reply_text(response, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"❌ /history error: {e}")
        await update.message.reply_text("❌ Error loading history.", parse_mode='Markdown')

async def analyze_url(update: Update, url: str):
    scraping_msg = await update.message.reply_text("📰 Scraping article...", parse_mode='Markdown')
    try:
        article_text = extract_article(url)
        if not article_text:
            await scraping_msg.delete()
            await update.message.reply_text("❌ Failed to extract article.", parse_mode='Markdown')
            return
        
        await scraping_msg.edit_text("🔍 Analyzing with Perplexity AI...")
        result = analyze_sentiment(article_text)
        
        emoji = {'BULLISH': '🚀', 'BEARISH': '📉', 'NEUTRAL': '➡️'}.get(result['sentiment'], '❓')
        response = f"""
📰 **Article Analysis**

{emoji} **{result['sentiment']}** ({result['confidence']}% confidence)

💡 {result['reasoning']}

_Powered by Perplexity AI_
"""
        await scraping_msg.delete()
        await update.message.reply_text(response, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in analyze_url: {e}")
        await scraping_msg.delete()
        await update.message.reply_text("❌ Analysis failed.", parse_mode='Markdown')

async def analyze_text(update: Update, text: str):
    analyzing_msg = await update.message.reply_text("🔍 Analyzing...")
    try:
        result = analyze_sentiment(text)
        emoji = {'BULLISH': '🚀', 'BEARISH': '📉', 'NEUTRAL': '➡️'}.get(result['sentiment'], '❓')
        response = f"""
{emoji} **{result['sentiment']}** ({result['confidence']}%)

💡 {result['reasoning']}

_Powered by Perplexity AI_
"""
        await analyzing_msg.delete()
        await update.message.reply_text(response, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error: {e}")
        await analyzing_msg.delete()
        await update.message.reply_text("❌ Analysis failed.", parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    urls = extract_urls(user_message)
    if urls:
        await analyze_url(update, urls[0])
        return
    if len(user_message) > 30:
        await analyze_text(update, user_message)
    else:
        await update.message.reply_text(f"💬 You said: _{user_message}_\n\nUse `/analyze` for sentiment analysis!", parse_mode='Markdown')

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Bot error: {context.error}")

@app.get("/")
async def root():
    return {"status": "ok", "message": "Sentiment Trading Bot Running", "db": DB_AVAILABLE}

@app.get("/health")
async def health():
    # Return 200 even if DB is down, to prevent Railway from killing the bot
    return {
        "status": "ok", 
        "db_connected": DB_AVAILABLE,
        "features": {
            "sentiment": "online",
            "portfolio": "online" if DB_AVAILABLE else "offline"
        }
    }

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return Response(status_code=500)

@app.get("/webhook")
async def webhook_check():
    return {"status": "ok", "method": "GET", "endpoint": "/webhook"}

async def setup_application():
    global application
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN required")
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("analyze", analyze_command))
    application.add_handler(CommandHandler("portfolio", portfolio_command))
    application.add_handler(CommandHandler("add", add_command))
    application.add_handler(CommandHandler("remove", remove_command))
    application.add_handler(CommandHandler("summary", summary_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)
    
    await application.initialize()
    await application.start()
    
    if WEBHOOK_URL:
        clean_webhook_url = WEBHOOK_URL.rstrip('/')
        webhook_endpoint = f"{clean_webhook_url}/webhook"
        await application.bot.set_webhook(url=webhook_endpoint)
        logger.info(f"✅ Webhook configured: {webhook_endpoint}")

@app.on_event("startup")
async def startup():
    global DB_AVAILABLE
    logger.info("🚀 FastAPI startup - Redis Mode")
    
    try:
        logger.info("🔥 Testing Redis connection...")
        redis_connected = redis_storage.test_connection()
        
        if redis_connected:
            DB_AVAILABLE = True
            logger.info("✅ Redis connected successfully!")
        else:
            DB_AVAILABLE = False
            logger.warning("⚠️ Bot starting in LIMITED MODE (Sentiment only, no Portfolio)")
    except Exception as e:
        logger.error(f"⚠️ Redis connection failed: {e}")
        logger.warning("⚠️ Bot starting in LIMITED MODE (Sentiment only, no Portfolio)")
        DB_AVAILABLE = False
    
    await setup_application()
    logger.info("✅ Server ready")

@app.on_event("shutdown")
async def shutdown():
    if application:
        await application.stop()
        await application.shutdown()
