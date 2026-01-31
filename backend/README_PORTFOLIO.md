# Portfolio Tracking Feature

## Overview

This module adds crypto portfolio tracking and AI-powered recommendations to the sentiment trading bot.

## Features

### 1. Position Management
- Track multiple crypto positions per user
- Record buy/sell transactions with full history
- Automatic calculation of average buy price
- Real-time P&L tracking via CoinGecko API

### 2. Transaction History
- Complete log of all buy/sell transactions
- Transaction details: quantity, price, total value, timestamp
- Optional notes for each transaction
- Premium users: unlimited history, Free users: 30 days

### 3. AI Recommendations
- Personalized recommendations based on:
  - Current market sentiment (from daily digest)
  - Position P&L (profit/loss %)
  - 7-day sentiment trend
- Recommendation types:
  - `HOLD`: Market neutral or position healthy
  - `BUY_MORE`: Bullish market + position down (average down)
  - `SELL_PARTIAL`: Bearish market + position up (take profit)
  - `SELL_ALL`: Bearish market + position down (cut losses)

### 4. Bot Commands

#### View Portfolio
```
/portfolio
```
Displays all positions with:
- Symbol, quantity, avg buy price
- Current price, current value
- P&L percentage and amount
- Latest AI recommendation

#### Add Position (Buy)
```
/add BTC 0.5 45000
```
Args: `symbol quantity price`
- Adds new transaction
- Updates position average price
- Logs transaction in history

#### Sell Position
```
/sell BTC 0.2 50000
```
Args: `symbol quantity price`
- Records sell transaction
- Updates position quantity
- Recalculates average price

#### Remove Position
```
/remove BTC
```
- Deletes position entirely
- Clears all transaction history
- Use with caution!

#### Get Advice
```
/advice
```
Get AI recommendations for all positions.

```
/advice BTC
```
Get AI recommendation for specific crypto.

#### Transaction History
```
/history BTC
```
View all buy/sell transactions for BTC.

```
/history
```
View all transactions across all positions.

## Database Schema

### user_positions
Summary table for each user's crypto holdings.
- `user_id`: FK to users
- `crypto_symbol`: BTC, ETH, SOL, etc.
- `quantity`: Total quantity held
- `avg_buy_price`: Average buy price (USD)
- Unique constraint: (user_id, crypto_symbol)

### position_transactions
Complete history of all buy/sell transactions.
- `position_id`: FK to user_positions
- `transaction_type`: BUY or SELL
- `quantity`: Amount bought/sold
- `price`: Price per unit (USD)
- `total_value`: quantity * price
- `notes`: Optional notes
- `created_at`: Timestamp

### position_recommendations
AI-generated recommendations log.
- `position_id`: FK to user_positions
- `recommendation`: HOLD, BUY_MORE, SELL_PARTIAL, SELL_ALL
- `reason`: AI explanation
- `sentiment_score`: Market sentiment at time (-100 to +100)
- `current_price`: Price at recommendation time
- `pnl_percent`: P&L percentage
- `created_at`: Timestamp

## CoinGecko Integration

### API Limits (Free Tier)
- 50 calls/minute
- No API key required
- Rate limited but sufficient

### Caching Strategy
- Prices cached for 5 minutes
- In-memory cache (dict)
- Reduces API calls significantly

### Supported Symbols
BTC, ETH, SOL, BNB, XRP, ADA, AVAX, DOT, MATIC, LINK, UNI, ATOM, LTC, BCH, XLM

Easy to extend in `crypto_prices.py` SYMBOL_TO_ID mapping.

## Recommendation Logic (MVP)

### Simple Rules
1. **HOLD** (default):
   - Sentiment between -50% and +50%
   - Or no strong signal

2. **BUY_MORE**:
   - Market sentiment > +50% (bullish)
   - Position P&L < -10% (down)
   - Opportunity to average down

3. **SELL_PARTIAL**:
   - Market sentiment < -50% (bearish)
   - Position P&L > +20% (up)
   - Take profit before reversal

4. **SELL_ALL**:
   - Market sentiment < -50% (bearish)
   - Position P&L < -20% (down)
   - Cut losses to prevent further damage

### Future Enhancements (Phase 2)
- User-configurable rules
- Stop-loss / take-profit alerts
- Multi-factor analysis (volume, RSI, MA)
- Machine learning predictions

## Setup Instructions

### 1. Initialize Database
Run on Railway after deploying code:
```bash
python backend/init_portfolio_tables.py
```

This creates all new tables without dropping existing data.

### 2. Test CoinGecko
Local test:
```bash
python backend/crypto_prices.py
```

Should output BTC/ETH/SOL prices.

### 3. Deploy Bot Updates
Push code to GitHub, Railway auto-deploys.

### 4. Test Commands
In Telegram:
```
/add BTC 0.5 45000
/portfolio
/advice
```

## Cost Estimate

### CoinGecko API
- Free tier: $0/month
- Pro tier (if needed later): $29/month (10k calls)

### Railway PostgreSQL
- Already included in current plan (~€5/month)
- New tables add minimal storage (<100 MB for 1000 users)

### Total Additional Cost
**€0/month** for MVP (using free CoinGecko)

## Future: Exchange Integration

Planned for Phase 2 (Week 9+):

### Binance/Kraken API Sync
- OAuth connection flow
- Import positions automatically
- Sync transactions history
- Real-time balance updates

### Security
- API keys encrypted in database
- Read-only permissions
- Never store passwords

### Implementation Complexity
- Medium (2-3 days dev)
- Requires cryptography library
- Exchange-specific parsing

**Decision**: Manual entry for MVP, automatic sync for Premium feature later.

## Testing Checklist

- [ ] `init_portfolio_tables.py` runs successfully on Railway
- [ ] `crypto_prices.py` fetches BTC/ETH/SOL prices
- [ ] `/add BTC 0.5 45000` creates position
- [ ] `/portfolio` displays position with P&L
- [ ] `/advice` generates recommendation
- [ ] `/sell BTC 0.2 50000` updates position
- [ ] `/history BTC` shows transactions
- [ ] `/remove BTC` deletes position
- [ ] Free tier limit (5 analyses/day) enforced
- [ ] Premium tier (unlimited) works

## Troubleshooting

### Database connection error
- Check `DATABASE_URL` env var on Railway
- Verify PostgreSQL service is running

### CoinGecko rate limit
- Check cache is working (5 min TTL)
- Reduce concurrent requests
- Consider Pro tier if hitting limits

### Position not updating
- Check transaction logs in `position_transactions` table
- Verify average price calculation logic
- Test with simple buy/sell scenario

## Next Steps

1. **Today**: Deploy schema + CoinGecko integration
2. **Tomorrow**: Implement bot commands (/portfolio, /add, /advice)
3. **Day 3**: Test + fix bugs
4. **Day 4**: Documentation + user guide
