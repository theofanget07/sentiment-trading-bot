# 🔔 Price Alerts Guide - TP/SL System

> Automated Take Profit & Stop Loss monitoring

---

## Overview

Set price alerts for your crypto positions and get instant Telegram notifications when triggered.

**Features:**
- Take Profit (TP) alerts
- Stop Loss (SL) alerts
- 15-minute monitoring frequency
- Multi-crypto support
- Automatic alert removal after trigger

---

## Commands

### Set Take Profit Alert

```
/setalert <SYMBOL> tp <PRICE>
```

**Example:**
```
/setalert BTC tp 80000
```

**Result:**
- Alert created for BTC @ $80,000
- Monitored every 15 minutes
- Notification sent when BTC ≥ $80,000
- Alert auto-removed after trigger

---

### Set Stop Loss Alert

```
/setalert <SYMBOL> sl <PRICE>
```

**Example:**
```
/setalert ETH sl 2500
```

**Result:**
- Alert created for ETH @ $2,500
- Notification sent when ETH ≤ $2,500
- Prevents further losses

---

### View Active Alerts

```
/listalerts
```

**Shows:**
- All active alerts for your account
- Symbol, type (TP/SL), target price
- Current price
- Distance to target (%)

---

### Remove Alert

```
/removealert <SYMBOL>
```

**Example:**
```
/removealert BTC
```

**Effect:**
- Removes ALL alerts for BTC (both TP and SL)
- Confirmation message sent

---

## How It Works

### Monitoring System

1. **Celery Beat** scheduler runs every 15 minutes
2. **Celery Worker** fetches current prices from CoinGecko
3. Compares prices against active alerts
4. Sends Telegram notification if triggered
5. Removes alert from Redis

### Alert Triggering

**Take Profit (TP):**
```
IF current_price >= tp_price:
    Send notification
    Remove alert
```

**Stop Loss (SL):**
```
IF current_price <= sl_price:
    Send notification
    Remove alert
```

---

## Notification Format

### Take Profit Triggered

```
🎯 TAKE PROFIT ALERT - BTC

Target: $80,000.00
Current: $80,245.50

Your BTC position has reached the take profit level!

Consider selling to lock in profits.
```

### Stop Loss Triggered

```
⚠️ STOP LOSS ALERT - ETH

Target: $2,500.00
Current: $2,487.30

Your ETH position has hit the stop loss level!

Consider selling to limit losses.
```

---

## Use Cases

### Scenario 1: Take Profit Strategy

```
# Buy BTC at $45,000
/add BTC 1 45000

# Set TP at +50%
/setalert BTC tp 67500

# Wait for notification...
# When triggered:
/sell BTC 0.5 67500    # Take 50% profit
```

### Scenario 2: Stop Loss Protection

```
# Buy ETH at $3,000
/add ETH 10 3000

# Set SL at -10%
/setalert ETH sl 2700

# If market crashes:
# Notification received at $2,700
/sell ETH 10 2700      # Exit to limit losses
```

### Scenario 3: Range Trading

```
# Buy SOL at $100
/add SOL 50 100

# Set both TP and SL
/setalert SOL tp 150   # +50% target
/setalert SOL sl 90    # -10% risk

# One will trigger first
```

---

## Technical Details

### Storage (Redis)

```
user:<user_id>:alerts:<SYMBOL> -> {
  "tp": 80000,
  "sl": 70000,
  "created_at": "2026-02-10T10:00:00Z"
}
```

### Celery Task Schedule

```python
beat_schedule = {
    'check-price-alerts': {
        'task': 'backend.tasks.alerts_checker.check_price_alerts',
        'schedule': crontab(minute='*/15'),  # Every 15 min
    }
}
```

### Price Fetching

- **Source**: CoinGecko API (`/simple/price`)
- **Rate limit**: 10-50 calls/min (free tier)
- **Caching**: 60 seconds
- **Fallback**: Last known price if API fails

---

## Limitations

### Free Tier

- **5 alerts per month**
- Resets on 1st of each month
- Upgrade to Premium for unlimited

### Premium Tier (€9/month)

- **Unlimited alerts**
- All cryptos supported
- Priority monitoring

---

## Best Practices

### 1. Set Realistic Targets

❌ **Avoid:**
```
/setalert BTC tp 200000   # Current: $75k (unrealistic)
```

✅ **Better:**
```
/setalert BTC tp 80000    # +6.7% (achievable)
```

### 2. Use Stop Losses

Always protect downside:
```
/setalert BTC tp 80000    # +10% profit
/setalert BTC sl 68000    # -5% loss
```

Risk/Reward = 2:1 (healthy)

### 3. Monitor Alerts

Check regularly:
```
/listalerts               # Weekly review
```

Remove outdated alerts:
```
/removealert SOL          # If strategy changed
```

---

## Troubleshooting

### Alert Not Triggering

**Check:**
1. Alert still active? `/listalerts`
2. Price actually reached target?
3. Celery worker running? (Check Railway logs)

### Delayed Notifications

- Normal delay: 0-15 minutes (monitoring interval)
- If >15 min, check Railway service status

### Wrong Price

- Prices from CoinGecko (delays possible)
- 60s cache (might show old price briefly)
- Use `/portfolio` to see real-time price

---

## Coming Soon

- 📱 **Custom intervals** - Set monitoring frequency
- 📊 **Trailing stops** - Dynamic SL adjustment
- 🔔 **Multiple alerts** - TP1, TP2, TP3 levels
- 📧 **Email notifications** - Backup to Telegram
- 🏁 **Alert history** - See past triggers

---

**Last Updated**: February 10, 2026
