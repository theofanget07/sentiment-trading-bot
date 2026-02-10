# 🔍 CryptoSentinel AI

<div align="center">

**AI-Powered Crypto Trading Assistant for Telegram**

*Automated portfolio tracking · Smart price alerts · AI-driven recommendations*

[![Telegram Bot](https://img.shields.io/badge/Telegram-%40SentinelAI__CryptoBot-blue?logo=telegram)](https://t.me/SentinelAI_CryptoBot)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python)](https://www.python.org/)
[![Railway](https://img.shields.io/badge/Deployed%20on-Railway-0B0D0E?logo=railway)](https://railway.app/)
[![License](https://img.shields.io/badge/License-Private-red)](LICENSE)

[Features](#-features) • [Quick Start](#-quick-start) • [Documentation](./docs/) • [Roadmap](#-roadmap)

</div>

---

## 🎯 What is CryptoSentinel AI?

A **professional-grade Telegram bot** that helps crypto traders make smarter decisions with:

✅ **Real-time portfolio tracking** - Monitor 15+ cryptocurrencies with live P&L
✅ **Intelligent price alerts** - Set Take Profit & Stop Loss with 15-min monitoring
✅ **AI-powered insights** - Personalized trading advice from Perplexity AI
✅ **Automated daily briefings** - Market analysis delivered every morning at 8 AM
✅ **Sentiment analysis** - Analyze crypto news articles instantly

**Built for:** Active crypto traders who want automation without complexity.

---

## ✨ Features

### 💼 Advanced Portfolio Management

- Track unlimited positions across 15+ cryptocurrencies
- Real-time profit/loss calculation (realized + unrealized)
- Average cost basis tracking with DCA support
- Partial buy/sell operations
- Complete transaction history
- Portfolio diversification metrics

```
/add BTC 0.5 45000        # Add position
/portfolio                # View all holdings
/sell BTC 0.2 75000       # Take profit (tracks P&L)
/summary                  # Global analytics
```

### 🔔 Smart Price Alerts

- Set Take Profit and Stop Loss levels
- Automated monitoring every 15 minutes
- Instant Telegram notifications when triggered
- Multi-crypto alert management

```
/setalert BTC tp 80000    # Take Profit at $80k
/setalert BTC sl 70000    # Stop Loss at $70k
/listalerts               # View active alerts
```

### 🤖 AI-Powered Recommendations

- Personalized trading advice based on your portfolio
- Risk assessment and entry/exit strategies
- Powered by Perplexity AI's latest models
- Context-aware suggestions

```
/recommend                # Get AI trading advice
```

### 🌅 Daily Morning Briefing

**Automated at 8:00 AM CET every day:**

- Portfolio performance summary
- Market sentiment analysis
- AI recommendations for your holdings
- **Bonus Trade of the Day** - Curated opportunity
- Top crypto news highlights

### 📈 Sentiment Analysis

- Analyze crypto news articles with AI
- Returns: BULLISH 🚀 | BEARISH 📉 | NEUTRAL ➡️
- Confidence scores + reasoning
- Automatic URL detection and scraping

```
/analyze Bitcoin ETF approval news is bullish
# Or just paste a URL:
https://coindesk.com/markets/bitcoin-rally
```

### 📊 Analytics & Metrics *(Coming Soon)*

- Performance dashboard
- Historical P&L charts
- Win/loss ratio tracking
- Best/worst performers

---

## 🚀 Quick Start

### For Users

1. **Open Telegram** and search for [@SentinelAI_CryptoBot](https://t.me/SentinelAI_CryptoBot)
2. Click **Start** and send `/help`
3. Add your first position: `/add BTC 0.1 45000`
4. Set a price alert: `/setalert BTC tp 50000`
5. Get AI advice: `/recommend`

**That's it!** Your crypto assistant is ready.

### For Developers

See [Developer Setup Guide](./docs/deployment/RAILWAY_SETUP.md) for installation instructions.

---

## 💻 Tech Stack

| Component | Technology |
|-----------|------------|
| **Language** | Python 3.11 |
| **Bot Framework** | python-telegram-bot 20.7 |
| **AI Engine** | Perplexity AI (sonar model) |
| **Storage** | Redis (Railway) |
| **Web Framework** | FastAPI |
| **Task Queue** | Celery + Redis |
| **Deployment** | Railway.app |
| **Price Data** | CoinGecko API |

---

## 📚 Documentation

**Complete documentation available in [/docs](./docs/)**

- 📌 [Features Guides](./docs/features/) - Detailed feature documentation
- 🚀 [Deployment](./docs/deployment/) - Setup & infrastructure
- 📊 [Progress Reports](./docs/reports/) - Development tracking

---

## 🛣 Roadmap

### ✅ Phase 1 - Core Features (Complete)

- [x] Telegram bot foundation
- [x] Perplexity AI integration
- [x] Portfolio tracking with Redis
- [x] Price alerts (TP/SL)
- [x] AI recommendations
- [x] Daily morning briefing
- [x] Railway deployment (24/7 uptime)

### 🔄 Phase 1.4 - Monetization (In Progress)

- [ ] Stripe payment integration
- [ ] Free/Premium tier system (€9/month)
- [ ] Feature gating
- [ ] Customer portal
- [ ] Email notifications

### 📅 Phase 2 - Advanced Trading (Planned)

- [ ] Trading signals dashboard
- [ ] Backtesting engine
- [ ] Multi-exchange support
- [ ] Advanced analytics

**Target**: €5,000/month MRR by Month 6

---

## 📊 Current Status

**Phase**: 1.5 - Analytics & Monitoring ✅  
**Next Milestone**: Launch Premium tier (Week 4)  
**Target**: 80+ paying users @ €9/month = **€720 MRR**

| Metric | Current | Target (Week 8) |
|--------|---------|----------------|
| Active Users | 10 | 150+ |
| Premium Users | 0 | 80+ |
| MRR | €0 | €720+ |
| Uptime | 99.8% | 99.5%+ |

---

## 👥 Who Uses CryptoSentinel AI?

**Perfect for:**

✅ Active crypto traders tracking multiple positions  
✅ DCA investors wanting automated cost basis calculation  
✅ Busy professionals who need automated alerts  
✅ Traders seeking AI-powered market insights  
✅ Anyone wanting a "set and forget" crypto assistant  

---

## 🛡 Security & Privacy

- **No login required** - Works directly in Telegram
- **No exchange API keys** - Manual position tracking only
- **Encrypted storage** - Redis with encryption at rest
- **GDPR compliant** - See [Privacy Policy](./PRIVACY_POLICY.md)
- **Open development** - Transparent progress tracking

---

## 👨‍💻 Author

**Theo Fanget**
- 💼 Project Manager @ Groupe E Celsius (Heating Utilities)
- 📍 Based in Lausanne, Switzerland
- 🎯 Building a €5k+/month SaaS in 6 months
- 🏃 Sports enthusiast (running, rugby, calisthenics)

---

## 🔗 Links

- **Telegram Bot**: [@SentinelAI_CryptoBot](https://t.me/SentinelAI_CryptoBot)
- **Documentation**: [/docs](./docs/)
- **GitHub**: [theofanget07/sentiment-trading-bot](https://github.com/theofanget07/sentiment-trading-bot)
- **Support**: contact.sentinellabs@gmail.com

---

## ⭐ Show Your Support

If you find CryptoSentinel AI useful:

1. ⭐ Star this repository
2. 📣 Share with fellow crypto traders
3. 💬 Join our Telegram community

---

## 📝 License

Private project - All rights reserved.

For collaboration or licensing inquiries: contact.sentinellabs@gmail.com

---

<div align="center">

**Built with ❤️ and lots of ☕ in Lausanne, Switzerland**

*Last Updated: February 10, 2026*

</div>
