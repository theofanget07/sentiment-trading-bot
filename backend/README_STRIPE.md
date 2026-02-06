# Stripe Integration Guide - CryptoSentinel AI Premium

## 🎯 Overview

This guide explains how to integrate Stripe payments for CryptoSentinel AI Premium subscriptions (€9/month).

## 📦 What's Been Created

### 1. **stripe_service.py** - Core Stripe Logic
Location: `backend/stripe_service.py`

**Features:**
- ✅ Create Checkout Session (€9/month recurring)
- ✅ Process webhooks (payment success, subscription events)
- ✅ Manage subscriptions (cancel, retrieve)
- ✅ Redis integration for user subscription status
- ✅ Complete error handling & logging

**Functions:**
```python
# Checkout
create_checkout_session(user_id, username, email) -> Dict

# Webhooks
process_webhook(payload, sig_header) -> Dict

# Subscription Management
get_subscription_status(user_id) -> str  # 'free' | 'premium' | 'cancelled'
set_subscription_status(user_id, status) -> bool
cancel_subscription(user_id) -> Dict
retrieve_subscription(user_id) -> Dict

# Testing
test_stripe_connection() -> bool
```

### 2. **routes/stripe_webhook.py** - FastAPI Webhook Endpoint
Location: `backend/routes/stripe_webhook.py`

**Endpoints:**
- `POST /webhook/stripe` - Receives Stripe webhook events
- `GET /webhook/stripe/health` - Health check

### 3. **Requirements Updated**
Added: `stripe==8.2.0`

---

## 🔧 Setup Instructions

### Step 1: Configure Stripe Account

1. **Go to Stripe Dashboard**
   - Test mode: https://dashboard.stripe.com/test
   - Live mode: https://dashboard.stripe.com/

2. **Create Product "CryptoSentinel Premium"**
   ```
   Name: CryptoSentinel Premium
   Price: €9.00 / month
   Recurring: Monthly
   ```

3. **Get API Keys**
   - Go to **Developers > API keys**
   - Copy:
     - `Publishable key` (not needed for bot)
     - `Secret key` (needed! Starts with sk_test_ for test mode)

4. **Get Price ID**
   - Go to **Products**
   - Click on "CryptoSentinel Premium"
   - Copy the Price ID (starts with `price_...`)

5. **Setup Webhook**
   - Go to **Developers > Webhooks**
   - Click "Add endpoint"
   - Endpoint URL: `https://your-railway-url.railway.app/webhook/stripe`
   - Select events:
     - `checkout.session.completed`
     - `customer.subscription.created`
     - `customer.subscription.updated`
     - `customer.subscription.deleted`
     - `invoice.payment_succeeded`
     - `invoice.payment_failed`
   - Copy the **Signing secret** (starts with `whsec_...`)

### Step 2: Configure Railway Environment Variables

Add these to your Railway backend service:

```bash
STRIPE_API_KEY=<your_stripe_secret_key_here>
STRIPE_WEBHOOK_SECRET=<your_webhook_secret_here>
STRIPE_PRICE_ID=<your_price_id_here>
STRIPE_SUCCESS_URL=https://t.me/SentinelAI_CryptoBot?start=payment_success
STRIPE_CANCEL_URL=https://t.me/SentinelAI_CryptoBot?start=payment_cancelled
```

**Important:**
- Use test mode keys (sk_test_...) for testing
- Use live mode keys (sk_live_...) for production
- Never commit API keys to GitHub!
- Get your keys from Stripe Dashboard > Developers > API keys

### Step 3: Update bot_webhook.py

Add the `/subscribe` command handler:

```python
# At the top with other imports
from backend.stripe_service import (
    create_checkout_session,
    get_subscription_status
)

# Add this command handler
async def subscribe_handler(update, context):
    """Handle /subscribe command - Create Stripe Checkout Session."""
    user = update.effective_user
    chat_id = user.id
    username = user.username or user.first_name
    
    logger.info(f"User {chat_id} requested Premium subscription")
    
    # Check current subscription status
    current_status = get_subscription_status(chat_id)
    
    if current_status == 'premium':
        await update.message.reply_text(
            "✅ **You're already a Premium member!**\n\n"
            "Use /manage to manage your subscription."
        )
        return
    
    # Create Stripe Checkout Session
    result = create_checkout_session(
        user_id=chat_id,
        username=username,
        email=None  # Optional: can be added later
    )
    
    if result['success']:
        # Send checkout link
        await update.message.reply_text(
            "🚀 **Upgrade to CryptoSentinel Premium!**\n\n"
            "🌟 **Premium Features:**\n"
            "• Unlimited price alerts (TP/SL)\n"
            "• Daily AI market insights (8:00 AM)\n"
            "• Personalized recommendations\n"
            "• Bonus Trade of the Day\n"
            "• Priority support\n\n"
            "💳 **Price:** €9/month\n\n"
            f"[Click here to subscribe]({result['url']})",
            parse_mode='Markdown',
            disable_web_page_preview=False
        )
        logger.info(f"✅ Checkout session created for user {chat_id}: {result['session_id']}")
    else:
        await update.message.reply_text(
            "❌ **Error creating checkout session**\n\n"
            f"Error: {result['error']}\n\n"
            "Please try again later or contact support."
        )
        logger.error(f"❌ Checkout creation failed for user {chat_id}: {result['error']}")

# Add this command handler
async def manage_subscription_handler(update, context):
    """Handle /manage command - View/cancel subscription."""
    user = update.effective_user
    chat_id = user.id
    
    status = get_subscription_status(chat_id)
    
    if status == 'free':
        await update.message.reply_text(
            "🆓 **You're on the Free plan**\n\n"
            "Upgrade to Premium to unlock all features!\n\n"
            "Use /subscribe to upgrade."
        )
    elif status == 'premium':
        from backend.stripe_service import retrieve_subscription
        
        sub_info = retrieve_subscription(chat_id)
        
        if sub_info['success']:
            sub = sub_info['subscription']
            from datetime import datetime
            
            # Format dates
            period_end = datetime.fromtimestamp(sub['current_period_end']).strftime('%d %B %Y')
            
            message = (
                "✅ **Premium Subscription Active**\n\n"
                f"📅 Next billing date: {period_end}\n"
                f"💳 Price: €9/month\n\n"
            )
            
            if sub['cancel_at_period_end']:
                cancel_date = datetime.fromtimestamp(sub['cancel_at']).strftime('%d %B %Y')
                message += f"⚠️ **Subscription will cancel on {cancel_date}**\n\n"
            
            message += (
                "To cancel your subscription, use:\n"
                "`/cancel_subscription`"
            )
            
            await update.message.reply_text(message, parse_mode='Markdown')
        else:
            await update.message.reply_text(
                "✅ **You're a Premium member!**\n\n"
                "Could not retrieve subscription details."
            )
    elif status == 'cancelled':
        await update.message.reply_text(
            "⚠️ **Your subscription has been cancelled**\n\n"
            "Reactivate anytime with /subscribe"
        )

# Add this command handler
async def cancel_subscription_handler(update, context):
    """Handle /cancel_subscription command."""
    user = update.effective_user
    chat_id = user.id
    
    status = get_subscription_status(chat_id)
    
    if status != 'premium':
        await update.message.reply_text(
            "⚠️ **No active subscription found**\n\n"
            "You can only cancel an active Premium subscription."
        )
        return
    
    from backend.stripe_service import cancel_subscription
    
    result = cancel_subscription(chat_id)
    
    if result['success']:
        from datetime import datetime
        cancel_date = datetime.fromtimestamp(result['cancel_at']).strftime('%d %B %Y')
        
        await update.message.reply_text(
            "✅ **Subscription cancelled successfully**\n\n"
            f"You'll keep access until: **{cancel_date}**\n\n"
            "You can reactivate anytime with /subscribe"
        )
        logger.info(f"✅ Subscription cancelled for user {chat_id}")
    else:
        await update.message.reply_text(
            "❌ **Error cancelling subscription**\n\n"
            f"Error: {result['message']}\n\n"
            "Please contact support."
        )
        logger.error(f"❌ Cancel failed for user {chat_id}: {result['message']}")

# Register commands in setup_application()
application.add_handler(CommandHandler("subscribe", subscribe_handler))
application.add_handler(CommandHandler("manage", manage_subscription_handler))
application.add_handler(CommandHandler("cancel_subscription", cancel_subscription_handler))
```

### Step 4: Add Webhook Route to FastAPI

In your main FastAPI app (where you initialize FastAPI):

```python
from backend.routes import stripe_webhook_router

# Add webhook router
app.include_router(stripe_webhook_router)
```

### Step 5: Update /start and /help Messages

Add Premium info:

```python
start_message = (
    "👋 Welcome to **CryptoSentinel AI**!\n\n"
    # ... existing content ...
    "\n🌟 **Upgrade to Premium** (€9/month):\n"
    "• Use /subscribe to unlock all features!\n"
    "• Unlimited alerts, AI insights, bonus trades\n\n"
    # ... rest of message ...
)
```

---

## 🧪 Testing

### Local Testing (before deployment)

1. **Test Stripe Connection**
   ```bash
   cd backend
   python stripe_service.py
   ```
   
   Expected output:
   ```
   ✅ Stripe connection OK
   ✅ Redis connection OK
   ```

2. **Test Checkout Session Creation**
   ```python
   from backend.stripe_service import create_checkout_session
   
   result = create_checkout_session(
       user_id=123456789,
       username="test_user"
   )
   
   print(result['url'])  # Should print Stripe checkout URL
   ```

### Testing on Telegram (after Railway deployment)

1. **Test Free User**
   - Send `/start` to bot
   - Send `/subscribe`
   - Should receive Stripe checkout link

2. **Test Checkout Flow**
   - Click the checkout link
   - Use test card: `4242 4242 4242 4242`
   - Expiry: Any future date (e.g., 12/34)
   - CVC: Any 3 digits (e.g., 123)
   - Complete payment
   - Should redirect to bot with success message

3. **Verify Premium Status**
   - Check Redis: `redis-cli GET user:123456789:subscription_status`
   - Should return `"premium"`
   - Test premium features (alerts, AI insights)

4. **Test Webhook Reception**
   - Go to Stripe Dashboard > Webhooks
   - Find your webhook
   - Should show successful events (✅ 200 OK)

### Stripe Test Cards

- **Successful payment:** `4242 4242 4242 4242`
- **Payment requires authentication:** `4000 0027 6000 3184`
- **Card declined:** `4000 0000 0000 0002`
- **Insufficient funds:** `4000 0000 0000 9995`

More test cards: https://stripe.com/docs/testing

### Test Webhooks Locally with Stripe CLI

1. **Install Stripe CLI**
   ```bash
   brew install stripe/stripe-cli/stripe
   ```

2. **Login to Stripe**
   ```bash
   stripe login
   ```

3. **Forward webhooks to local server**
   ```bash
   stripe listen --forward-to localhost:8000/webhook/stripe
   ```

4. **Trigger test events**
   ```bash
   stripe trigger checkout.session.completed
   stripe trigger customer.subscription.deleted
   ```

---

## 🔒 Premium Features Gating

Create a decorator to protect premium features:

```python
from functools import wraps
from backend.stripe_service import get_subscription_status

def require_premium(func):
    """Decorator to require Premium subscription."""
    @wraps(func)
    async def wrapper(update, context, *args, **kwargs):
        chat_id = update.effective_chat.id
        status = get_subscription_status(chat_id)
        
        if status != "premium":
            await update.message.reply_text(
                "🔒 **This feature is Premium-only**\n\n"
                "Upgrade to Premium for €9/month to unlock:\n"
                "• Unlimited price alerts\n"
                "• Daily AI insights\n"
                "• Bonus Trade recommendations\n"
                "• Priority support\n\n"
                "Use /subscribe to upgrade!"
            )
            return
        
        return await func(update, context, *args, **kwargs)
    return wrapper

# Use it on premium commands
@require_premium
async def set_alert_handler(update, context):
    # Premium feature - only accessible to subscribers
    pass
```

### Features to Protect

**FREE TIER:**
- ✅ Basic portfolio tracking
- ✅ 1 price alert per day
- ✅ Manual `/recommend` (1x per day)
- ✅ View prices

**PREMIUM TIER (€9/month):**
- 🔒 **Unlimited** price alerts
- 🔒 Daily AI Insights (automatic 8:00 AM)
- 🔒 Bonus Trade of the Day (automatic 8:00 AM)
- 🔒 Personalized AI recommendations (unlimited)
- 🔒 Priority support

---

## 📊 Monitoring

### Railway Logs

Monitor Stripe events:
```bash
railway logs -s backend | grep "Stripe"
railway logs -s backend | grep "Checkout"
railway logs -s backend | grep "Webhook"
```

### Key Metrics to Track

1. **MRR (Monthly Recurring Revenue)**
   ```python
   from backend.redis_storage import redis_client
   
   # Count premium users
   pattern = "user:*:subscription_status"
   keys = redis_client.keys(pattern)
   premium_count = sum(
       1 for key in keys
       if redis_client.get(key) == "premium"
   )
   
   mrr = premium_count * 9  # €9/month per user
   print(f"MRR: €{mrr}")
   ```

2. **Conversion Rate**
   ```python
   total_users = len(redis_client.keys("user:*:profile"))
   conversion_rate = (premium_count / total_users) * 100
   print(f"Conversion: {conversion_rate:.1f}%")
   ```

3. **Churn Rate**
   - Track cancelled subscriptions
   - Monitor `customer.subscription.deleted` webhooks

---

## 🐛 Troubleshooting

### Issue 1: Webhook not received

**Symptoms:** Payment succeeds but user not upgraded to Premium

**Solutions:**
1. Check Railway logs: `railway logs -s backend | grep webhook`
2. Verify webhook URL in Stripe Dashboard
3. Check `STRIPE_WEBHOOK_SECRET` is set correctly
4. Test webhook endpoint: `curl https://your-railway-url.railway.app/webhook/stripe/health`

### Issue 2: "Stripe API key not configured"

**Solution:**
1. Verify `STRIPE_API_KEY` is set in Railway
2. Restart backend service
3. Check logs: `railway logs -s backend | grep "Stripe API"`

### Issue 3: User stays "free" after payment

**Solution:**
1. Check Redis: `redis-cli GET user:123456789:subscription_status`
2. Check webhook was received successfully
3. Manually update if needed:
   ```python
   from backend.stripe_service import set_subscription_status
   set_subscription_status(123456789, 'premium')
   ```

### Issue 4: Checkout link doesn't work

**Solution:**
1. Check `STRIPE_PRICE_ID` is correct
2. Verify Stripe product exists and is active
3. Check logs for error message

---

## 🚀 Go Live Checklist

Before launching to real customers:

- [ ] Switch to **Live** Stripe API keys (not test keys)
- [ ] Create production product in Stripe (not test mode)
- [ ] Update `STRIPE_PRICE_ID` with live product ID
- [ ] Configure webhook with live endpoint URL
- [ ] Test payment flow with real card
- [ ] Verify webhook events are received
- [ ] Test subscription cancellation flow
- [ ] Monitor logs for errors
- [ ] Update Terms of Service with pricing
- [ ] Update Privacy Policy with payment processor info

---

## 📚 Resources

- **Stripe Documentation:** https://stripe.com/docs
- **Stripe Testing:** https://stripe.com/docs/testing
- **Stripe Webhooks:** https://stripe.com/docs/webhooks
- **Stripe API Python:** https://stripe.com/docs/api/python
- **Railway Environment Variables:** https://docs.railway.app/develop/variables

---

## 💡 Next Steps

1. ✅ Complete bot integration (add /subscribe command)
2. ✅ Test with Stripe test mode
3. ✅ Deploy to Railway
4. ✅ Verify webhooks work
5. ✅ Implement premium feature gating
6. ✅ Test complete flow end-to-end
7. ✅ Switch to live mode
8. 🚀 **Launch Premium!**

---

**Status:** Phase 1.4 - Stripe Integration **READY FOR TESTING** ✅

**Target:** €720/month MRR (80 Premium users × €9/month)

**Timeline:** Weeks 6-8 (06-26 February 2026)
