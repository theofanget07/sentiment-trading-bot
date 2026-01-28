# 🤖 Sentiment Trading Bot

> AI-powered crypto sentiment analysis bot powered by Perplexity AI
> 
> **Week 1 Day 3 Live** - URL Scraping Feature ✨

## 📌 Overview

Telegram bot that analyzes crypto news sentiment using Perplexity AI. Now with **automatic article scraping** from URLs!

**Telegram:** [@sentiment_trading_test_bot](https://t.me/sentiment_trading_test_bot)

---

## 🚀 Features

### ✅ Implemented (Week 1)

- **Sentiment Analysis** - Analyze crypto news with Perplexity AI
  - Returns: BULLISH 🚀 | BEARISH 📉 | NEUTRAL ➡️
  - Confidence score (0-100%)
  - Reasoning + Key points
  - Additional sources

- **URL Scraping** 🔥 NEW!
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

- **Smart Auto-Analysis**
  - Detects URLs and scrapes automatically
  - Auto-analyzes long text messages (>30 chars)
  - Manual analysis with `/analyze` command

### ⏳ Coming Soon (Week 1-3)

- Database integration (PostgreSQL)
- User management & subscriptions
- Premium tier (€9/month)
- Deployment to Railway (24/7)
- Daily digest emails
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

### 3. Auto-Analysis

Just send any long text (>30 chars):

```
Ethereum upgrade successful, gas fees drop 50% overnight
```

---

## 🛠 Tech Stack

- **Language:** Python 3.11.9
- **Bot Framework:** python-telegram-bot 20.7
- **AI:** Perplexity API (sonar model)
- **Scraping:** BeautifulSoup4 + requests
- **Version Control:** Git + GitHub

### Dependencies

```bash
python-telegram-bot==20.7
anthropic==0.18.1
python-dotenv==1.0.1
fastapi==0.109.2
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
│   ├── bot.py                   # Main Telegram bot
│   ├── sentiment_analyzer.py    # Perplexity AI integration
│   ├── article_scraper.py       # URL scraping module 🆕
│   ├── test_article_scraper.py  # Test suite 🆕
│   └── requirements.txt         # Python dependencies
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
```

5. **Run the bot**

```bash
cd backend
python bot.py
```

---

## 🧪 Testing

### Test Article Scraper

```bash
cd backend
python test_article_scraper.py
```

**Expected output:**
- Test 1: URL detection ✅
- Test 2: Article scraping (5 URLs) ✅
- Test 3: Error handling ✅
- Summary: Success rate 60%+

### Test in Telegram

1. Start bot: `python bot.py`
2. Open [@sentiment_trading_test_bot](https://t.me/sentiment_trading_test_bot)
3. Try:
   - `/start`
   - `/help`
   - `/analyze Bitcoin surges to new high`
   - `https://www.coindesk.com/markets/`

---

## 📊 Article Scraper Details

### Supported Sites

| Site | Selector Strategy | Status |
|------|------------------|--------|
| CoinDesk | `article`, `div.article-content` | ✅ |
| CoinTelegraph | `article`, `div.post-content` | ✅ |
| Bitcoin.com | `article`, `div.entry-content` | ✅ |
| Decrypt | `article`, `div.article-body` | ✅ |
| The Block | `article`, `div.article-content` | ✅ |
| CryptoSlate | `article`, `div.post-content` | ✅ |
| CryptoNews | `article`, `div.article-body` | ✅ |
| Others | Generic fallback | ⚠️ |

### Features

- **Timeout:** 5 seconds max per request
- **Error Handling:** HTTP errors, timeouts, malformed HTML
- **Content Cleaning:** Removes ads, scripts, navigation
- **Fallback:** Multiple strategies if primary fails
- **Logging:** Detailed logs for debugging

### Performance

- **Average time:** 2-3 seconds per article
- **Success rate:** 60-80% (depends on site structure)
- **Min content:** 100 characters required

---

## 🎯 Roadmap

### Week 1 (Current) - MVP Foundation

- ✅ Day 1-2: Bot setup + Perplexity integration
- ✅ Day 3-4: URL scraping + multi-site support
- ⏳ Day 5-6: Railway deployment (24/7)
- ⏳ Day 7: Polish + beta user feedback

### Week 2 - Automation

- Database setup (PostgreSQL)
- Automated news fetching (RSS, Reddit, Twitter)
- Background tasks (Celery + Redis)
- Daily digest emails

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

**Current Status:** Week 1 Day 3 (50% complete)

| Milestone | Status | Date |
|-----------|--------|------|
| Bot setup | ✅ Complete | Jan 27, 2026 |
| Sentiment analysis | ✅ Complete | Jan 27, 2026 |
| URL scraping | ✅ Complete | Jan 28, 2026 |
| Railway deploy | ⏳ In progress | - |
| Database | 📅 Planned | Week 2 |
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
- LinkedIn: [Add your LinkedIn]
- Twitter: [Add your Twitter]

---

## 📧 Support

For issues or questions:
1. Check the [test script](backend/test_article_scraper.py)
2. Review [logs](backend/bot.py) (run with `python bot.py`)
3. Open an issue on GitHub (coming soon)

---

## 🔗 Links

- **Telegram Bot:** [@sentiment_trading_test_bot](https://t.me/sentiment_trading_test_bot)
- **GitHub Repo:** [theofanget07/sentiment-trading-bot](https://github.com/theofanget07/sentiment-trading-bot)
- **Commits:** [View commits](https://github.com/theofanget07/sentiment-trading-bot/commits/main)

---

## 📊 Latest Updates

### January 28, 2026 - Day 3 🔥

- ✅ Added `article_scraper.py` (7,864 bytes)
- ✅ Multi-site support (7+ crypto news sites)
- ✅ Updated `bot.py` with URL auto-detection
- ✅ Created comprehensive test suite
- ✅ 3 commits pushed to GitHub
- ✅ ~550 lines of production-ready code

**Next:** Railway deployment (Week 1 Day 5)

---

**Built with ❤️ and lots of ☕ in Lausanne**
