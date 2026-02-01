# 🤖 Sentiment Trading Bot

> AI-powered crypto sentiment analysis bot powered by Perplexity AI
> 
> **Week 2 Day 4 Live** - Portfolio Tracking with JSON Storage ✨

## 📌 Overview

Telegram bot that analyzes crypto news sentiment using Perplexity AI. Now with **portfolio tracking** and **JSON-based storage**!

**Telegram:** [@sentiment_trading_test_bot](https://t.me/sentiment_trading_test_bot)

---

## 🚀 Features

### ✅ Implemented (Week 1-2)

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

- **Portfolio Tracking** 💼 NEW!
  - View your crypto holdings with `/portfolio`
  - JSON-based storage (no database required)
  - Track positions, transactions, recommendations
  - Ready for backtesting integration

- **Smart Auto-Analysis**
  - Detects URLs and scrapes automatically
  - Auto-analyzes long text messages (>30 chars)
  - Manual analysis with `/analyze` command

- **Railway Deployment** 🚂
  - Running 24/7 on Railway.app
  - Webhook mode for instant responses
  - Automatic redeploys on GitHub push

### ⏳ Coming Soon (Week 2-3)

- Add positions: `/add BTC 0.01 98000`
- Transaction history: `/history`
- Daily digest emails
- Premium tier (€9/month)
- Historical sentiment tracking

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

### 3. Check Portfolio

```
/portfolio
```

### 4. Auto-Analysis

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
- **Storage:** JSON files (backend/user_data/)
- **Web Framework:** FastAPI (webhook mode)
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
```

---

## 📂 Project Structure

```
sentiment-trading-bot/
├── backend/
│   ├── bot_webhook.py           # Main Telegram bot (webhook mode)
│   ├── sentiment_analyzer.py    # Perplexity AI integration
│   ├── article_scraper.py       # URL scraping module
│   ├── portfolio_manager.py     # Portfolio tracking (JSON) 🆕
│   ├── user_data/              # JSON storage directory 🆕
│   │   ├── portfolios.json
│   │   ├── transactions.json
│   │   └── recommendations.json
│   └── requirements.txt         # Python dependencies
├── Dockerfile                   # Railway deployment config
├── .env.example                 # Environment variables template
└── README.md                    # This file
```

---

## 🚦 Getting Started

### Prerequisites

- Python 3.11+
- Telegram account
- Perplexity API key
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
2. Open [@sentiment_trading_test_bot](https://t.me/sentiment_trading_test_bot)
3. Try:
   - `/start`
   - `/help`
   - `/analyze Bitcoin surges to new high`
   - `/portfolio`
   - `https://www.coindesk.com/markets/`

---

## 📊 Portfolio Manager Details

### Features

- **Zero dependencies** - Pure JSON storage
- **User isolation** - Separate data per user ID
- **Atomic operations** - Thread-safe reads/writes
- **Scalable** - Ready for 100+ users

### Data Structure

```json
{
  "123456789": {
    "username": "@trader",
    "positions": {
      "BTC": {
        "quantity": 0.01,
        "avg_price": 98000,
        "last_updated": "2026-01-31T10:00:00Z"
      }
    },
    "total_value_usd": 980.00,
    "created_at": "2026-01-31T09:00:00Z"
  }
}
```

---

## 🎯 Roadmap

### Week 1 (Complete) - MVP Foundation ✅

- ✅ Bot setup + Perplexity integration
- ✅ URL scraping + multi-site support
- ✅ Railway deployment (24/7)
- ✅ Beta user feedback

### Week 2 (In Progress) - Automation

- ✅ JSON storage for portfolios
- ⏳ Add/remove positions commands
- ⏳ Transaction history
- ⏳ Automated news fetching (RSS, Reddit)
- ⏳ Background tasks (Celery + Redis)

### Week 3 - Monetization

- Stripe integration
- Premium tier (€9/month)
- Telegram channel for signals
- Email notifications
- Launch to 10-20 paying users

### Target: Week 8

- **€870/month MRR**
- **80+ paying users**
- **15% monthly churn max**

---

## 📈 Progress

**Current Status:** Week 2 Day 4 (65% complete)

| Milestone | Status | Date |
|-----------|--------|------|
| Bot setup | ✅ Complete | Jan 27, 2026 |
| Sentiment analysis | ✅ Complete | Jan 27, 2026 |
| URL scraping | ✅ Complete | Jan 28, 2026 |
| Railway deploy | ✅ Complete | Jan 30, 2026 |
| Portfolio tracking | ✅ Complete | Feb 1, 2026 |
| Add/history commands | ⏳ In progress | - |
| Monetization | 📅 Planned | Week 3 |

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

- **Telegram Bot:** [@sentiment_trading_test_bot](https://t.me/sentiment_trading_test_bot)
- **GitHub Repo:** [theofanget07/sentiment-trading-bot](https://github.com/theofanget07/sentiment-trading-bot)
- **Railway App:** [Dashboard](https://railway.app/dashboard)
- **Commits:** [View commits](https://github.com/theofanget07/sentiment-trading-bot/commits/main)

---

## 📊 Latest Updates

### February 1, 2026 - Day 4 🔥

- ✅ Fixed portfolio_manager import for Railway
- ✅ Corrected module path (backend.portfolio_manager)
- ✅ Added try/except fallback for local dev
- ✅ Triggered redeploy with updated code
- ✅ Portfolio tracking now fully functional

**Next:** Add positions commands (`/add`, `/remove`, `/history`)

---

**Built with ❤️ and lots of ☕ in Lausanne**
