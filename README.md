# 🤖 CryptoSentinel AI

> AI-powered crypto sentinel & portfolio tracker powered by Perplexity AI
> 
> **Week 3 Complete** - Advanced Portfolio Features + Price Alerts + AI Recommendations ✨

## 📌 Overview

Telegram bot that analyzes crypto sentiment using Perplexity AI. Now with **advanced portfolio tracking**, **TP/SL price alerts**, **AI recommendations**, and **daily insights**!

**Telegram:** [@SentinelAI_CryptoBot](https://t.me/SentinelAI_CryptoBot)

---

## 🚀 Features

### ✅ Implemented (Week 1-3)

- **Sentiment Analysis** - Analyze crypto news with Perplexity AI
  - Returns: BULLISH 🚀 | BEARISH 📉 | NEUTRAL ➡️
  - Confidence score (0-100%)
  - Reasoning + Key points
  - Additional sources

- **URL Scraping** 🔥
  - Auto-detect URLs in messages
  - Extract article text automatically
  - Support for 7+ crypto news sites:
    - CoinDesk
    - CoinTelegraph
    - Bitcoin.com
    - Decrypt
    - The Block
    - CryptoSlate
    - CryptoNews
    - Generic fallback for other sites

- **Advanced Portfolio Tracking** 💼
  - View holdings with `/portfolio`
  - Add positions: `/add BTC 0.5 45000`
  - **Partial sells**: `/sell BTC 0.5 75000` ⚡
  - **Partial remove**: `/remove BTC 0.3`
  - Full remove: `/remove BTC`
  - **Enriched summary**: `/summary` (realized + unrealized P&L)
  - Transaction history: `/history`
  - Redis storage (ultra-fast)

- **Price Alerts (TP/SL)** 🔔 NEW!
  - Set Take Profit: `/setalert BTC tp 80000`
  - Set Stop Loss: `/setalert BTC sl 70000`
  - View alerts: `/listalerts`
  - Remove alerts: `/removealert BTC`
  - Automated monitoring every 15 minutes
  - Real-time notifications via Celery workers

- **AI Recommendations** 🤖 NEW!
  - Personalized trading advice: `/recommend`
  - Portfolio-aware suggestions
  - Risk assessment
  - Entry/exit strategies

- **Daily Insights** 📈 NEW!
  - Automated 8:00 AM CET notifications
  - Market sentiment analysis
  - Portfolio performance review
  - Bonus Trade of the Day

- **Smart Auto-Analysis**
  - Detects URLs and scrapes automatically
  - Auto-analyzes long text messages (>30 chars)
  - Manual analysis with `/analyze` command

- **Railway Deployment** 🚂
  - Running 24/7 on Railway.app
  - Webhook mode for instant responses
  - Automatic redeploys on GitHub push
  - Celery workers for background tasks

### ⏳ Coming Soon (Week 4+)

- 💳 Premium tier (€9/month)
- 📊 Analytics dashboard
- 📧 Email notifications
- 🎯 Advanced trading signals

---

## 💬 Usage Examples

### 1. Analyze Text

```
/analyze Bitcoin hits new ATH as institutions buy
```

### 2. Analyze URL

```
https://www.coindesk.com/markets/bitcoin-rally
```

Or:

```
Check this out! https://cointelegraph.com/news/eth-upgrade
```

### 3. Portfolio Management

```
/add BTC 1 45000          # Add 1 BTC @ $45k
/portfolio                # View holdings
/sell BTC 0.5 75000       # Sell 0.5 BTC @ $75k (records P&L)
/remove ETH 2             # Remove 2 ETH
/summary                  # Global analytics
/history                  # Last 5 transactions
```

### 4. Price Alerts

```
/setalert BTC tp 80000    # Take Profit at $80k
/setalert BTC sl 70000    # Stop Loss at $70k
/listalerts               # View active alerts
/removealert BTC          # Delete all BTC alerts
```

### 5. AI Recommendations

```
/recommend                # Get personalized trading advice
```

### 6. Auto-Analysis

Just send any long text (>30 chars):

```
Ethereum upgrade successful, gas fees drop 50% overnight
```

---

## 🛠 Tech Stack

- **Language:** Python 3.11
- **Bot Framework:** python-telegram-bot 20.7
- **AI:** Perplexity API (sonar model)
- **Scraping:** BeautifulSoup4 + requests
- **Storage:** Redis (Railway)
- **Web Framework:** FastAPI (webhook mode)
- **Task Queue:** Celery + Redis
- **Deployment:** Railway.app
- **Version Control:** Git + GitHub

### Dependencies

```bash
python-telegram-bot==20.7
anthropic==0.18.1
python-dotenv==1.0.1
fastapi==0.109.2
uvicorn[standard]==0.27.1
sqlalchemy==2.0.27
celery==5.3.6
requests==2.31.0
beautifulsoup4==4.12.3
redis==5.0.1
```

---

## 📂 Project Structure

```
sentiment-trading-bot/
├── backend/
│   ├── bot_webhook.py           # Main Telegram bot (webhook mode)
│   ├── sentiment_analyzer.py    # Perplexity AI integration
│   ├── article_scraper.py       # URL scraping module
│   ├── portfolio_manager.py     # Portfolio logic
│   ├── redis_storage.py         # Redis storage layer
│   ├── crypto_prices.py         # CoinGecko API
│   ├── celery_worker.py         # Background tasks (alerts, insights)
│   ├── recommend_handler.py     # AI recommendations
│   └── requirements.txt         # Python dependencies
├── Dockerfile                   # Railway deployment config
├── .env.example                 # Environment variables template
└── README.md                    # This file
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Telegram account
- Perplexity API key
- Redis instance (Railway provides one)
- Git

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/theofanget07/sentiment-trading-bot.git
cd sentiment-trading-bot
```

2. **Create virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # Mac/Linux
# OR
venv\Scripts\activate     # Windows
```

3. **Install dependencies**

```bash
pip install -r backend/requirements.txt
```

4. **Setup environment variables**

```bash
cp .env.example .env
```

Edit `.env` and add:

```
TELEGRAM_BOT_TOKEN=your_bot_token_from_BotFather
PERPLEXITY_API_KEY=your_perplexity_api_key
REDIS_URL=redis://localhost:6379
WEBHOOK_URL=https://your-railway-url.up.railway.app
```

5. **Run the bot**

```bash
cd backend
python bot_webhook.py
```

---

## 🧪 Testing

### Test Article Scraper

```bash
cd backend
python test_article_scraper.py
```

### Test in Telegram

1. Start bot: `python bot_webhook.py`
2. Open [@SentinelAI_CryptoBot](https://t.me/SentinelAI_CryptoBot)
3. Try:
   - `/start`
   - `/help`
   - `/add BTC 0.01 45000`
   - `/portfolio`
   - `/setalert BTC tp 50000`
   - `/listalerts`
   - `/recommend`
   - `/summary`
   - `/history`

---

## 📊 Portfolio Manager Details

### Features

- **Redis-based** - Ultra-fast storage (<100ms latency)
- **User isolation** - Separate data per user ID
- **Atomic operations** - Thread-safe reads/writes
- **Scalable** - Ready for 1000+ users
- **Realized P&L tracking** - Record profits from sells

### Data Structure

```json
user:123456789:profile -> {"user_id": 123456789, "username": "@trader"}
user:123456789:positions:BTC -> {"quantity": 0.5, "avg_price": 45000}
user:123456789:transactions -> [{"action": "BUY", "quantity": 1, ...}]
user:123456789:realized_pnl -> [{"symbol": "BTC", "pnl_realized": 15000, ...}]
user:123456789:alerts:BTC -> {"tp": 80000, "sl": 70000}
```

---

## 🎯 Roadmap

### Week 1-2 (Complete) - MVP Foundation ✅

- ✅ Bot setup + Perplexity integration
- ✅ URL scraping + multi-site support
- ✅ Railway deployment (24/7)
- ✅ Redis storage
- ✅ Basic portfolio tracking

### Week 3 (Complete) - Advanced Features ✅

- ✅ Partial sells with P&L tracking
- ✅ Enriched summary (realized + unrealized P&L)
- ✅ Real-time P&L alerts (TP/SL)
- ✅ AI recommendations engine
- ✅ Daily automated insights (8AM CET)
- ✅ Bonus Trade of the Day

### Week 4-8 - Monetization

- Stripe integration
- Premium tier (€9/month)
- Free/Premium feature gating
- Email notifications
- Analytics dashboard
- Launch to 80+ paying users

### Target: Week 8

- **€870/month MRR**
- **80+ paying users**
- **15% monthly churn max**

---

## 📈 Progress

**Current Status:** Week 3 Complete - Phase 1.3 100% ✅

| Milestone | Status | Date |
|-----------|--------|------|
| Bot setup | ✅ Complete | Jan 27, 2026 |
| Sentiment analysis | ✅ Complete | Jan 27, 2026 |
| URL scraping | ✅ Complete | Jan 28, 2026 |
| Railway deploy | ✅ Complete | Jan 30, 2026 |
| Portfolio tracking | ✅ Complete | Feb 1, 2026 |
| Redis migration | ✅ Complete | Feb 3, 2026 |
| Partial sells + P&L | ✅ Complete | Feb 4, 2026 |
| Enriched summary | ✅ Complete | Feb 4, 2026 |
| Price alerts (TP/SL) | ✅ Complete | Feb 4, 2026 |
| AI recommendations | ✅ Complete | Feb 4, 2026 |
| Daily insights | ✅ Complete | Feb 5, 2026 |
| Bot rebranding | ✅ Complete | Feb 5, 2026 |
| Monetization | ⏳ In progress | Week 4+ |

---

## 🤝 Contributing

This is a personal project for now. Contributions will be open once Phase 1 is complete (Week 8).

---

## 📝 License

Private project - All rights reserved.

---

## 👨‍💻 Author

**Theo Fanget**
- Role: Project Manager @ Groupe E Celsius
- Location: Lausanne, Switzerland
- Project: Building €5k+/month SaaS in 6 months

---

## 📧 Support

For issues or questions:
1. Check Railway logs for deployment issues
2. Review bot logs (`python bot_webhook.py`)
3. Test locally before pushing to GitHub

---

## 🔗 Links

- **Telegram Bot:** [@SentinelAI_CryptoBot](https://t.me/SentinelAI_CryptoBot)
- **GitHub Repo:** [theofanget07/sentiment-trading-bot](https://github.com/theofanget07/sentiment-trading-bot)
- **Railway App:** [Dashboard](https://railway.app/dashboard)

---

## 📊 Latest Updates

### February 5, 2026 - Bot Rebranding 🎯

**CryptoSentinel AI Launch!**

- ✅ **Rebranded to @SentinelAI_CryptoBot**
  - Professional username
  - Updated BotFather settings
  - New About/Description
  - Ready for Phase 1.4 monetization

**Phase 1.3 Complete - All Features Shipped:**
- ✅ Price Alerts (TP/SL)
- ✅ AI Recommendations (/recommend)
- ✅ Daily Insights (8AM CET)
- ✅ Bonus Trade of the Day

**Next:** Phase 1.4 - Stripe Integration + Premium Tier (€9/month)

---

### February 4, 2026 - Week 3 Day 1 🔥

**Features 1, 3, 4, 5 Shipped!**

- ✅ **Feature 1: Price Alerts (TP/SL)**
  - `/setalert BTC tp 80000` - Set Take Profit
  - `/setalert BTC sl 70000` - Set Stop Loss
  - Celery workers monitoring prices every 15 min
  - Real-time notifications

- ✅ **Feature 3: Partial Sells & Realized P&L**
  - `/sell BTC 0.5 75000` - Sell position and track P&L
  - `/remove BTC 0.3` - Partial removal support
  - Redis storage for realized P&L history
  - Smart position management (keeps avg price)

- ✅ **Feature 4: AI Recommendations**
  - `/recommend` - Personalized trading advice
  - Portfolio-aware analysis
  - Risk-adjusted suggestions

- ✅ **Feature 5: Daily Insights**
  - Automated 8AM CET notifications
  - Market sentiment + portfolio review
  - Bonus Trade of the Day

- ✅ **Feature 2: Enriched Summary**
  - `/summary` now shows:
    - Unrealized P&L (current positions)
    - Realized P&L (from sells)
    - Total P&L (combined)
    - Best/worst performers
    - Diversification score
  - Enhanced `/history` with P&L on sells

---

### February 3, 2026 - Day 6 ✅

- ✅ Redis migration complete
- ✅ Portfolio tracking fully functional
- ✅ 15 cryptos supported (CoinGecko API)
- ✅ `/add`, `/remove`, `/portfolio`, `/summary`, `/history` working

---

### February 1, 2026 - Day 4 🔥

- ✅ Fixed portfolio_manager import for Railway
- ✅ Corrected module path (backend.portfolio_manager)
- ✅ Added try/except fallback for local dev
- ✅ Triggered redeploy with updated code
- ✅ Portfolio tracking now fully functional

---

**Built with ❤️ and lots of ☕ in Lausanne**
