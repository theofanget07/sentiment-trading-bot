# 💼 Portfolio Management - Complete Guide

> Advanced crypto portfolio tracking with Redis storage

---

## Overview

CryptoSentinel AI includes a sophisticated portfolio management system that tracks:
- Holdings across 15+ cryptocurrencies
- Realized P&L from completed trades
- Unrealized P&L from current positions
- Transaction history
- Average cost basis per position

---

## Commands

### Add Position

```
/add <SYMBOL> <QUANTITY> <PRICE>
```

**Examples:**
```
/add BTC 0.5 45000
/add ETH 10 3000
/add SOL 100 120
```

**Effect:**
- Adds crypto to portfolio
- Updates average cost basis if position exists
- Records transaction in history

---

### View Portfolio

```
/portfolio
```

**Shows:**
- All current positions
- Quantity held per crypto
- Average purchase price
- Current market price (CoinGecko API)
- Unrealized P&L (USD + %)
- Total portfolio value

---

### Sell Position (Partial or Full)

```
/sell <SYMBOL> <QUANTITY> <PRICE>
```

**Examples:**
```
/sell BTC 0.2 75000      # Partial sell
/sell ETH 5 4500         # Partial sell
```

**Effect:**
- Reduces position size
- Calculates realized P&L: `(sell_price - avg_cost) * quantity`
- Records in realized P&L history
- Keeps remaining position with same avg cost

---

### Remove Position

```
/remove <SYMBOL> [QUANTITY]
```

**Examples:**
```
/remove BTC 0.3          # Remove 0.3 BTC (partial)
/remove SOL              # Remove entire SOL position
```

**Effect:**
- Removes from portfolio (no P&L tracking)
- Use `/sell` instead if you want P&L calculation

---

### Portfolio Summary

```
/summary
```

**Shows:**
- Total portfolio value
- Total unrealized P&L (current positions)
- Total realized P&L (from completed sells)
- **Combined P&L** (unrealized + realized)
- Best performing asset
- Worst performing asset
- Diversification score

---

### Transaction History

```
/history
```

**Shows last 5 transactions:**
- Date & time
- Action (BUY/SELL/REMOVE)
- Symbol
- Quantity
- Price
- Realized P&L (if SELL)

---

## Supported Cryptocurrencies

15 cryptos tracked via CoinGecko API:

| Symbol | Name | CoinGecko ID |
|--------|------|-------------|
| BTC | Bitcoin | bitcoin |
| ETH | Ethereum | ethereum |
| SOL | Solana | solana |
| BNB | Binance Coin | binancecoin |
| XRP | Ripple | ripple |
| ADA | Cardano | cardano |
| AVAX | Avalanche | avalanche-2 |
| DOT | Polkadot | polkadot |
| MATIC | Polygon | matic-network |
| LINK | Chainlink | chainlink |
| UNI | Uniswap | uniswap |
| ATOM | Cosmos | cosmos |
| LTC | Litecoin | litecoin |
| BCH | Bitcoin Cash | bitcoin-cash |
| XLM | Stellar | stellar |

---

## Storage Architecture

### Redis Keys

```
user:<user_id>:profile           → User metadata
user:<user_id>:positions:<SYMBOL> → Position data
user:<user_id>:transactions      → Transaction list
user:<user_id>:realized_pnl      → Realized P&L records
```

### Position Data Structure

```json
{
  "quantity": 0.5,
  "avg_price": 45000,
  "current_price": 75000,
  "pnl_usd": 15000,
  "pnl_percent": 66.67
}
```

### Transaction Structure

```json
{
  "action": "SELL",
  "symbol": "BTC",
  "quantity": 0.2,
  "price": 75000,
  "timestamp": "2026-02-10T10:30:00Z",
  "pnl_realized": 6000
}
```

---

## Use Cases

### Scenario 1: Buy & Hold Tracking

```
/add BTC 1 45000
/add ETH 10 3000
/portfolio              # See current value
/summary                # Total P&L
```

### Scenario 2: Take Profits

```
/add BTC 1 45000        # Initial buy
# ... BTC rises to $75k
/sell BTC 0.5 75000     # Take profit on half
# Result: +$15k realized P&L recorded
/portfolio              # 0.5 BTC remaining @ $45k avg
/summary                # Shows realized + unrealized P&L
```

### Scenario 3: DCA Strategy

```
/add ETH 5 3000         # First buy @ $3k
/add ETH 5 3500         # Second buy @ $3.5k
/portfolio              # Shows: 10 ETH @ $3,250 avg
```

---

## Technical Details

### Price Updates

- Fetched from CoinGecko API
- Cached for 60 seconds (rate limit protection)
- Fallback to last known price if API fails
- Real-time updates on `/portfolio` calls

### Performance

- **Latency**: <100ms per operation
- **Scalability**: Ready for 1000+ users
- **Reliability**: Redis persistence enabled
- **Atomic operations**: Thread-safe

### Error Handling

- Validates crypto symbols before operations
- Checks sufficient quantity before sells/removes
- Graceful degradation if CoinGecko API unavailable
- User-friendly error messages

---

## Coming Soon

- 📊 **Portfolio Charts** - Visual P&L tracking
- 💱 **Multi-currency support** - EUR, CHF display
- 📧 **Email reports** - Weekly portfolio summaries
- 🎯 **Target allocations** - Rebalancing suggestions
- 📈 **Performance analytics** - Sharpe ratio, volatility

---

**Built for**: Serious crypto traders who want professional-grade portfolio tracking

**Last Updated**: February 10, 2026
