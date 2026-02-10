# 💳 Stripe Integration - Premium Tier System

> Monetization system with Free/Premium tiers

---

## Overview

CryptoSentinel AI uses Stripe for payment processing:

- **Free Tier**: Limited features (3 portfolios, 5 alerts/month)
- **Premium Tier**: €9/month - Unlimited features

---

## Premium Features

### Included in Premium (€9/month)

✅ **Unlimited Portfolio Tracking**
- Track unlimited crypto positions
- No limits on add/sell operations
- Full transaction history

✅ **Unlimited Price Alerts**
- Set unlimited TP/SL alerts
- 15-minute monitoring frequency
- Real-time Telegram notifications

✅ **AI Recommendations**
- Personalized trading advice
- Portfolio-aware analysis
- Risk assessment

✅ **Daily Morning Briefing**
- 8:00 AM CET automated insights
- Portfolio performance review
- Market sentiment analysis
- Bonus Trade of the Day

✅ **Analytics Dashboard** (Coming Soon)
- Performance metrics
- P&L charts
- Historical tracking

---

## Commands

### Subscribe to Premium

```
/subscribe
```

**Flow:**
1. Bot sends Stripe Checkout link
2. User completes payment (card/SEPA)
3. Webhook updates user tier to Premium
4. Instant access to all features

---

### Manage Subscription

```
/manage
```

**Actions:**
- View current tier (Free/Premium)
- Access Stripe Customer Portal
- Update payment method
- Cancel subscription
- Download invoices

---

### Check Tier Status

```
/start
```

Shows current tier in welcome message.

---

## Free Tier Limits

| Feature | Free | Premium |
|---------|------|--------|
| Portfolio positions | 3 | ∞ |
| Price alerts/month | 5 | ∞ |
| AI recommendations | ❌ | ✅ |
| Daily briefing | ❌ | ✅ |
| Transaction history | Last 5 | Full |
| Analytics dashboard | ❌ | ✅ |

---

## Technical Implementation

### Stripe Products

- **Product ID**: `prod_xxxxx`
- **Price ID**: `price_xxxxx`
- **Amount**: €9.00/month
- **Currency**: EUR
- **Billing**: Monthly recurring

### Webhooks

Handled events:

```python
checkout.session.completed   # New subscription
customer.subscription.updated # Status change
customer.subscription.deleted # Cancellation
invoice.payment_failed        # Payment issue
```

### Redis Storage

```
user:<user_id>:subscription -> {
  "tier": "premium",
  "stripe_customer_id": "cus_xxxxx",
  "subscription_id": "sub_xxxxx",
  "status": "active",
  "current_period_end": "2026-03-10T00:00:00Z"
}
```

### Feature Gating

Decorators protect premium features:

```python
@require_premium
async def recommend_command(update, context):
    # Only accessible to Premium users
    ...
```

---

## User Flow

### New User (Free)

1. `/start` → Welcome + Free tier message
2. Can use portfolio (up to 3 positions)
3. Can set 5 alerts/month
4. Prompted to `/subscribe` when hitting limits

### Upgrade to Premium

1. `/subscribe` → Stripe Checkout link
2. Complete payment
3. Webhook updates tier → Premium
4. Telegram notification: "Welcome to Premium!"
5. All features unlocked

### Premium User

1. Unlimited access to all features
2. Daily morning briefing at 8 AM CET
3. No limits on operations
4. Can `/manage` subscription anytime

### Cancellation

1. `/manage` → Stripe Customer Portal
2. Cancel subscription
3. Access until end of billing period
4. Downgraded to Free tier after period ends

---

## Testing

### Test Mode (Stripe)

Use test cards:

```
Success: 4242 4242 4242 4242
Declined: 4000 0000 0000 0002
```

### Webhook Testing

```bash
stripe listen --forward-to https://your-railway-url.up.railway.app/webhook/stripe
stripe trigger checkout.session.completed
```

---

## Revenue Tracking

### Target Metrics (Week 8)

- **80+ Premium users**
- **€9/user/month**
- **Total MRR: €720+**
- **Churn rate: <15%/month**

### Current Status

- Implementation: ✅ Complete
- Testing: ⏳ In progress
- Launch: 📅 Week 4 (Feb 12, 2026)

---

## Security

- Stripe webhook signature verification
- HTTPS-only communication
- PCI-DSS compliant (Stripe handles cards)
- No credit card data stored locally
- Redis encryption at rest

---

## Support

For payment issues:

1. Check `/manage` for subscription status
2. Verify payment method in Stripe Portal
3. Contact: contact.sentinellabs@gmail.com

---

**Last Updated**: February 10, 2026
