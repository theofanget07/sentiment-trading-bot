# 🤖 AI Recommendations Guide

> Personalized crypto trading advice powered by Perplexity AI

---

## Overview

Get AI-powered trading recommendations based on your portfolio holdings, current market conditions, and technical analysis.

**Powered by:** Perplexity AI (sonar-pro model)

---

## Command

```
/recommend [SYMBOL]
```

### Examples

**Analyze entire portfolio:**
```
/recommend
```

**Analyze specific crypto:**
```
/recommend BTC
/recommend ETH
```

---

## What You Get

### For Each Position

📈 **Trading Signal**
- BUY 🚀 - Bullish opportunity
- SELL 📉 - Take profit / exit
- HOLD ➡️ - Wait for better entry/exit

🧠 **AI Analysis**
- Market sentiment
- Technical indicators
- Risk assessment
- News impact

🎯 **Confidence Score**
- HIGH (80%+) - Strong conviction
- MEDIUM (60-80%) - Moderate confidence
- LOW (<60%) - Uncertain conditions

---

## Example Output

### Single Crypto Analysis

```
🤖 AI RECOMMENDATION - BTC

YOUR POSITION
Quantity: 0.5 BTC
Entry Price: $45,000.00
Current Price: $75,000.00
P&L: +$15,000 (+66.67%)

RECOMMENDATION: HOLD ➡️
Confidence: HIGH (85%)

AI Analysis:
Bitcoin is showing strong momentum with institutional buying. 
RSI at 68 (approaching overbought). Consider taking partial 
profits at $80k resistance. Stop loss recommended at $70k 
to protect gains.

Powered by Perplexity AI
Use /summary for portfolio overview
```

---

## How It Works

### 1. Data Collection

- Fetches your portfolio positions from Redis
- Gets current prices from CoinGecko
- Calculates P&L (unrealized)

### 2. AI Analysis

Sends to Perplexity AI:
```
Analyze BTC position:
- Quantity: 0.5 BTC
- Entry: $45,000
- Current: $75,000
- P&L: +66.67%

Provide:
1. Trading recommendation (BUY/SELL/HOLD)
2. Reasoning (market sentiment, technicals)
3. Confidence level (HIGH/MEDIUM/LOW)
```

### 3. Response Parsing

- Extracts recommendation, reasoning, confidence
- Formats for Telegram (markdown)
- Adds position context

---

## Use Cases

### Scenario 1: Daily Check-In

```
# Morning routine
/recommend                # Full portfolio analysis

# Review AI suggestions
# Make informed decisions
```

### Scenario 2: Position Review

```
# Unsure about BTC position
/recommend BTC            # Specific analysis

# AI suggests: HOLD (85% confidence)
# Reasoning: Strong momentum, wait for $80k
```

### Scenario 3: Entry/Exit Timing

```
# Before buying
/recommend ETH
# AI: BUY - Oversold conditions, good entry

/add ETH 10 3000          # Execute trade

# Later...
/recommend ETH
# AI: SELL - Take profit, resistance hit

/sell ETH 10 4500         # Exit with profit
```

---

## Best Practices

### 1. Don't Trade Blindly

❌ **Wrong:**
```
/recommend BTC
# AI says SELL
/sell BTC 1 75000         # Immediate action
```

✅ **Right:**
```
/recommend BTC
# AI says SELL (reasoning: overbought)
# Cross-check:
# - Chart analysis
# - Your strategy
# - Risk tolerance
# THEN decide
```

### 2. Use Confidence Scores

```
HIGH (80%+)    → Strong signal, consider acting
MEDIUM (60-80%) → Moderate, combine with other analysis
LOW (<60%)     → Uncertain, wait for clarity
```

### 3. Combine with Other Tools

```
/recommend              # AI opinion
/portfolio              # Check P&L
/listalerts             # Review TP/SL
# Make holistic decision
```

---

## Technical Details

### AI Model

- **Model**: `sonar-pro` (Perplexity AI)
- **Context window**: 8,192 tokens
- **Response time**: 3-10 seconds
- **Cost**: ~$0.01 per recommendation

### Prompt Engineering

Optimized prompt includes:
- Position details (quantity, entry, P&L)
- Market context request
- Structured output format
- Risk disclaimer

### Rate Limiting

**Free Tier:**
- 10 recommendations/day
- Shared with other AI features

**Premium Tier:**
- Unlimited recommendations
- Priority processing

---

## Limitations

### AI Is Not Financial Advice

⚠️ **Important:**
- AI provides analysis, not guarantees
- Past performance ≠ future results
- You are responsible for your trades
- Always do your own research (DYOR)

### Market Volatility

- Crypto markets move fast
- AI analysis based on current data
- Conditions can change rapidly
- Use stop losses!

### Context Limitations

- AI doesn't know:
  - Your personal risk tolerance
  - Your financial situation
  - Your tax implications
  - Your investment timeframe

---

## Coming Soon

- 📊 **Technical indicators** - RSI, MACD, Bollinger Bands
- 📰 **News integration** - Real-time event analysis
- 🔔 **Alert on signal change** - BUY → SELL notifications
- 📈 **Backtesting** - Historical accuracy tracking
- 🧠 **Learning mode** - AI learns from your preferences

---

## FAQ

**Q: Is AI always right?**
A: No. AI is a tool, not a crystal ball. Use as one input in your decision-making.

**Q: How often should I check recommendations?**
A: Daily or before major trades. Don't over-trade.

**Q: Can I trust HIGH confidence signals?**
A: Higher confidence = stronger conviction, but not guaranteed. Markets are unpredictable.

**Q: What if AI says SELL but I want to HOLD?**
A: Your decision is final. AI provides perspective, you decide.

---

**Disclaimer:** CryptoSentinel AI recommendations are for informational purposes only. Not financial advice. Trade at your own risk.

**Last Updated**: February 10, 2026
