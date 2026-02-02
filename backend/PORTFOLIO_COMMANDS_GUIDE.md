# 📊 Portfolio Management Commands - User Guide

## 🎯 Overview

Your Sentiment Trading Bot now includes comprehensive portfolio management features with real-time profit/loss tracking powered by CoinGecko API.

## 📦 Features

✅ **Track crypto positions** - BTC, ETH, SOL, and 12+ cryptos  
✅ **Real-time P&L calculations** - Current prices from CoinGecko  
✅ **Transaction history** - Every buy/sell recorded  
✅ **Portfolio summary** - Total ROI and performance metrics  
✅ **Automatic price updates** - 5-minute cache for optimal API usage  

---

## 🔑 Command Reference

### 1️⃣ `/portfolio` - View Your Holdings

**Purpose:** Display all your crypto positions with current market prices and P&L.

**Usage:**
```
/portfolio
```

**Output:**
- List of all positions
- Quantity, avg buy price, current price
- Current value and P&L ($ and %)
- Total portfolio value

**Example Response:**
```
💼 Your Crypto Portfolio

BTC 🟢
  • Quantity: 0.5
  • Avg Price: $45,000.00
  • Current: $98,234.56
  • Value: $49,117.28
  • P&L: +$26,617.28 USD (+118.48%)

ETH 🔴
  • Quantity: 10
  • Avg Price: $4,200.00
  • Current: $3,876.45
  • Value: $38,764.50
  • P&L: -$3,235.50 USD (-7.70%)

Total Value: $87,881.78
```

---

### 2️⃣ `/add` - Add a Position

**Purpose:** Add a new crypto position or increase an existing one.

**Usage:**
```
/add <SYMBOL> <QUANTITY> <PRICE>
```

**Parameters:**
- `SYMBOL` - Crypto ticker (BTC, ETH, SOL, etc.)
- `QUANTITY` - Amount purchased (decimals allowed)
- `PRICE` - Purchase price in USD

**Examples:**
```
/add BTC 0.5 45000
/add ETH 10 4200
/add SOL 100 23.50
```

**Behavior:**
- If position doesn't exist → Creates new position
- If position exists → Accumulates and recalculates average price
- Automatically records transaction in history

**Example Response:**
```
✅ Position Created

BTC
  • Quantity: 0.5
  • Avg Price: $45,000.00
  • Total Invested: $22,500.00

📊 Current Status:
  • Market Price: $98,234.56
  • Current Value: $49,117.28
  • P&L: +$26,617.28 USD (+118.48%)
```

---

### 3️⃣ `/remove` - Remove a Position

**Purpose:** Completely remove a crypto position from your portfolio.

**Usage:**
```
/remove <SYMBOL>
```

**Parameter:**
- `SYMBOL` - Crypto ticker to remove

**Examples:**
```
/remove BTC
/remove ETH
```

**Behavior:**
- Deletes entire position (all quantity)
- Records removal in transaction history
- Recalculates total portfolio value

**Example Response:**
```
✅ Position Removed

BTC has been removed from your portfolio.

Use /portfolio to see your updated holdings.
```

---

### 4️⃣ `/summary` - Portfolio Summary

**Purpose:** Get high-level overview with total P&L and performance metrics.

**Usage:**
```
/summary
```

**Output:**
- Number of positions
- Top performer (best % gain)
- Worst performer (biggest % loss)
- Total invested amount
- Current total value
- Overall P&L in USD and %

**Example Response:**
```
🚀 Portfolio Summary

💼 Positions: 3

🏆 Top Performer:
BTC: +118.48%

📉 Worst Performer:
ETH: -7.70%

💰 Total Stats:
  • Invested: $60,000.00
  • Current Value: $98,450.32
  • Total P&L: +$38,450.32 USD
  • ROI: +64.08%

Powered by CoinGecko (prices cached 5 min)
```

---

### 5️⃣ `/history` - Transaction History

**Purpose:** View your last 10 transactions (buys, sells, removes).

**Usage:**
```
/history
```

**Output:**
- Last 10 transactions (most recent first)
- Date, time, action (BUY/REMOVE)
- Symbol, quantity, price
- Total value in USD

**Example Response:**
```
📃 Recent Transactions (last 10)

🟫 BUY BTC
  Feb 02, 14:23 • 0.5 @ $45,000.00
  Total: $22,500.00

🟫 BUY ETH
  Feb 02, 13:15 • 10 @ $4,200.00
  Total: $42,000.00

🗑 REMOVE SOL
  Feb 01, 22:10 • 100 @ $23.50
  Total: $2,350.00

Showing last 3 transaction(s)
```

---

## 🪙 Supported Cryptocurrencies

The bot supports **15 major cryptocurrencies** with real-time CoinGecko pricing:

| Symbol | Name | Example Price |
|--------|------|---------------|
| **BTC** | Bitcoin | $98,000 |
| **ETH** | Ethereum | $3,800 |
| **SOL** | Solana | $145 |
| **BNB** | Binance Coin | $650 |
| **XRP** | Ripple | $2.40 |
| **ADA** | Cardano | $1.20 |
| **AVAX** | Avalanche | $52 |
| **DOT** | Polkadot | $10 |
| **MATIC** | Polygon | $1.10 |
| **LINK** | Chainlink | $23 |
| **UNI** | Uniswap | $14 |
| **ATOM** | Cosmos | $12 |
| **LTC** | Litecoin | $115 |
| **BCH** | Bitcoin Cash | $520 |
| **XLM** | Stellar | $0.40 |

---

## 💡 Pro Tips

### 💰 Average Price Calculation

When you add to an existing position, the bot automatically calculates your new average price:

```
New Avg Price = (Old Qty × Old Price + New Qty × New Price) / (Old Qty + New Qty)
```

**Example:**
- You have: 0.5 BTC @ $40,000 avg
- You buy: 0.3 BTC @ $50,000
- New avg: `(0.5×40000 + 0.3×50000) / 0.8 = $43,750`

### 🔄 Price Updates

Prices are cached for **5 minutes** to optimize API usage:
- CoinGecko free tier: 50 calls/minute
- Cache prevents rate limiting
- Fresh prices every 5 minutes automatically

### 📊 P&L Formula

```
P&L % = ((Current Price - Avg Buy Price) / Avg Buy Price) × 100
P&L USD = Quantity × (Current Price - Avg Buy Price)
```

### 🔒 Data Storage

Your portfolio is stored in JSON files on Railway:
- `user_data/portfolios.json` - All positions
- `user_data/transactions.json` - Transaction history
- Data persists across bot restarts

---

## ⚠️ Important Notes

🚨 **This is a tracking tool, not a trading bot**
- You manually add positions after buying on exchanges
- Bot tracks performance, doesn't execute trades
- Use `/add` after each purchase on Binance/Coinbase/etc.

🔔 **Rate Limits**
- CoinGecko free tier: 50 calls/minute
- 5-minute price cache prevents issues
- If you see errors, wait 1-2 minutes

💾 **Data Privacy**
- Your portfolio is stored per user ID
- Data is private to your Telegram account
- No sharing between users

---

## 🐞 Troubleshooting

### "Unknown crypto symbol"
➡️ Use supported tickers (see table above). Case-insensitive.

### "Invalid input - quantity and price must be numbers"
➡️ Use numbers only. Decimals OK: `/add BTC 0.5 45000`

### "Position not found"
➡️ Check `/portfolio` for exact symbol names. Use uppercase.

### Prices not updating
➡️ Prices cache for 5 min. Wait or use `/summary` to force refresh.

---

## 🚀 Example Workflow

**Day 1 - Initial Purchases:**
```
/add BTC 0.5 45000
/add ETH 10 4200
/add SOL 100 23.50
/portfolio
```

**Day 7 - Check Performance:**
```
/summary
/portfolio
```

**Day 14 - Add More BTC:**
```
/add BTC 0.2 48000
/portfolio  (see updated avg price)
```

**Day 30 - Review Trades:**
```
/history
/summary
```

**When Selling:**
```
/remove ETH  (sold all ETH on exchange)
/portfolio   (see updated holdings)
```

---

## 🔗 Links

- **Bot:** [@sentiment_trading_test_bot](https://t.me/sentiment_trading_test_bot)
- **Railway:** [sentiment-trading-bot-production.up.railway.app](https://sentiment-trading-bot-production.up.railway.app)
- **GitHub:** [theofanget07/sentiment-trading-bot](https://github.com/theofanget07/sentiment-trading-bot)
- **CoinGecko API:** [coingecko.com/api](https://www.coingecko.com/api)

---

## ✨ Next Features (Phase 1.2 Completion)

🔨 **In Development:**
- 📈 Portfolio charts (5-year projections)
- 📧 Daily P&L summary emails
- 🔔 Price alerts (notify when BTC > $100k)
- 📊 Backtesting (test strategies on historical data)
- 💳 Stripe integration for premium features

---

**Last Updated:** February 2, 2026  
**Version:** 1.2.0 (Portfolio Management)  
**Status:** ✅ Production Ready on Railway  
