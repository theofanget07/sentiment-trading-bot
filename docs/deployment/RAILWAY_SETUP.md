# 🚀 Railway Deployment Guide

> Complete guide for deploying CryptoSentinel AI on Railway.app

---

## Prerequisites

- GitHub account
- Railway account (free tier available)
- Telegram Bot Token (from @BotFather)
- Perplexity API Key
- Repository access

---

## Architecture

### Services Deployed

```
CryptoSentinel AI Railway Project
├── backend           (FastAPI + Telegram webhook)
├── celery-worker     (Background tasks)
├── celery-beat       (Task scheduler)
├── redis             (Storage + message broker)
└── postgres          (Optional - future use)
```

---

## Step 1: Create Railway Project

1. Go to [railway.app](https://railway.app/)
2. Click **New Project**
3. Select **Deploy from GitHub repo**
4. Choose `theofanget07/sentiment-trading-bot`
5. Railway auto-detects Dockerfile

---

## Step 2: Add Redis Service

1. In your project, click **New**
2. Select **Database** → **Redis**
3. Railway provisions Redis instantly
4. Copy `REDIS_URL` from Variables tab

---

## Step 3: Configure Backend Service

### Environment Variables

Add in Railway dashboard:

```bash
# Telegram
TELEGRAM_BOT_TOKEN=8305583760:AAGuGE4dpZSFAbMPhKp07h-kU07rxgwixSU

# AI
PERPLEXITY_API_KEY=your_perplexity_key_here

# Storage
REDIS_URL=${{Redis.REDIS_URL}}  # Auto-linked

# Webhook
WEBHOOK_URL=https://your-app.up.railway.app
PORT=8000

# Stripe (later)
STRIPE_API_KEY=sk-test-xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
```

### Start Command

```bash
cd backend && uvicorn bot_webhook:app --host 0.0.0.0 --port $PORT
```

---

## Step 4: Setup Celery Worker

1. Click **New** → **Empty Service**
2. Link to same GitHub repo
3. Name: `celery-worker`

### Environment Variables

Same as backend + add:
```bash
REDIS_URL=${{Redis.REDIS_URL}}
TELEGRAM_BOT_TOKEN=${{backend.TELEGRAM_BOT_TOKEN}}
PERPLEXITY_API_KEY=${{backend.PERPLEXITY_API_KEY}}
```

### Start Command

```bash
cd backend && celery -A celery_app worker --loglevel=info
```

---

## Step 5: Setup Celery Beat

1. Click **New** → **Empty Service**
2. Link to same GitHub repo
3. Name: `celery-beat`

### Environment Variables

Same as celery-worker

### Start Command

```bash
cd backend && celery -A celery_app beat --loglevel=info
```

---

## Step 6: Set Telegram Webhook

### Get Railway URL

1. Go to backend service
2. Copy the public URL: `https://sentiment-trading-bot-production-xxx.up.railway.app`

### Set Webhook

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-railway-url.up.railway.app/telegram/webhook"}'
```

### Verify

```bash
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

Should show:
```json
{
  "ok": true,
  "result": {
    "url": "https://your-url.up.railway.app/telegram/webhook",
    "has_custom_certificate": false,
    "pending_update_count": 0
  }
}
```

---

## Step 7: Test Deployment

### Check Logs

**Backend:**
```bash
railway logs -s backend --tail
```

**Celery Worker:**
```bash
railway logs -s celery-worker --tail
```

**Celery Beat:**
```bash
railway logs -s celery-beat --tail
```

### Test Bot

1. Open [@SentinelAI_CryptoBot](https://t.me/SentinelAI_CryptoBot)
2. Send `/start`
3. Try `/add BTC 0.1 45000`
4. Check `/portfolio`

---

## Auto-Deploy Setup

### Enable GitHub Integration

1. Railway dashboard → **Settings**
2. **Deploy Triggers** → Enable
3. Branch: `main`
4. Auto-deploy on push: ✅

### Deploy Flow

```bash
# Local changes
git add .
git commit -m "feat: New feature"
git push origin main

# Railway auto-deploys in ~2 minutes
```

---

## Monitoring

### Service Health

**Railway Dashboard:**
- CPU usage
- Memory usage
- Request count
- Response times

### Logs

**View in real-time:**
```bash
railway logs -s backend --tail 100
```

**Check for errors:**
```bash
railway logs -s backend | grep ERROR
```

---

## Troubleshooting

### Bot Not Responding

1. **Check webhook:**
   ```bash
   curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo
   ```

2. **Check logs:**
   ```bash
   railway logs -s backend --tail 50
   ```

3. **Restart service:**
   Railway dashboard → Backend → **Restart**

### Celery Tasks Not Running

1. **Check Redis connection:**
   ```bash
   railway logs -s celery-worker | grep "Connected to redis"
   ```

2. **Verify beat schedule:**
   ```bash
   railway logs -s celery-beat | grep "Scheduler"
   ```

3. **Restart workers:**
   Railway dashboard → Restart celery-worker & celery-beat

### High Memory Usage

- **Normal**: 150-300 MB per service
- **High**: >500 MB → Potential memory leak
- **Solution**: Check logs for repeated errors, restart services

---

## Costs

### Railway Free Tier

- **$5/month credit**
- **500 hours/month** execution time
- **100 GB** bandwidth

### Expected Usage

| Service | Monthly Cost |
|---------|-------------|
| Backend | ~$5 |
| Celery Worker | ~$3 |
| Celery Beat | ~$2 |
| Redis | Free (built-in) |
| **Total** | **~$10/month** |

### Optimization Tips

1. **Use hobby plan** ($5/month with $5 credit)
2. **Scale down during low traffic**
3. **Optimize Celery tasks** (reduce frequency if possible)

---

## Security

### Environment Variables

❌ **Never commit:**
- `TELEGRAM_BOT_TOKEN`
- `PERPLEXITY_API_KEY`
- `STRIPE_API_KEY`
- `REDIS_URL`

✅ **Use Railway secrets:**
- Store in Railway dashboard
- Reference with `${{SERVICE.VARIABLE}}`

### Webhook Verification

- Telegram webhooks use HTTPS
- Railway provides SSL automatically
- No additional configuration needed

---

## Backup & Recovery

### Redis Data

**Export data:**
```bash
railway run redis-cli --rdb /tmp/dump.rdb
railway run cat /tmp/dump.rdb > backup.rdb
```

**Restore data:**
```bash
cat backup.rdb | railway run redis-cli --pipe
```

### Repository

- **GitHub** stores all code
- **Tags** for version control
- **Branches** for experimentation

---

## Scaling

### Horizontal Scaling

- Add more **celery-worker** instances
- Railway auto-balances tasks
- Redis handles distributed locking

### Vertical Scaling

- Increase memory/CPU in Railway settings
- Recommended for backend service

---

## Next Steps

1. ✅ Deployment complete
2. Monitor logs for 24 hours
3. Test all features (portfolio, alerts, AI)
4. Setup Stripe webhooks (Phase 1.4)
5. Add analytics dashboard

---

**Last Updated**: February 10, 2026
