# 🏛️ Multi-Service Architecture

> Understanding CryptoSentinel AI's distributed system

---

## Architecture Overview

```
┌────────────────────────────────────┐
│        Telegram User                     │
│   [@SentinelAI_CryptoBot]              │
└─────────────┬───────────────────────┘
               │
               │ HTTPS Webhook
               │
        ┌──────▼──────┐
        │   Backend    │  (FastAPI)
        │   Service    │  - Webhook endpoint
        │              │  - Command handlers
        │   Port 8000  │  - Redis operations
        └──────┬──────┘
               │
               │ Enqueue tasks
               │
        ┌──────▼─────────────────────────┐
        │         Redis                      │
        │  - Message broker                │
        │  - Portfolio storage              │
        │  - User data cache                │
        │  - Task queue                     │
        └──────┬─────────────┬────────────┘
               │               │
               │               │
        ┌──────▼──────┐    ┌─────▼──────┐
        │   Celery    │    │   Celery   │
        │   Worker    │    │    Beat    │
        │             │    │            │
        │ - Executes  │    │ - Schedules│
        │   tasks     │    │   tasks    │
        │ - Alerts    │    │ - Crontab  │
        │ - AI calls  │    │ - Triggers │
        └─────────────┘    └────────────┘
               │               │
               │               │
        ┌──────▼─────────────────────────┐
        │      External APIs              │
        │  - CoinGecko (prices)           │
        │  - Perplexity AI (analysis)     │
        │  - Stripe (payments)            │
        └────────────────────────────────┘
```

---

## Services Explained

### 1. Backend Service (FastAPI)

**Role:** Main application server

**Responsibilities:**
- Receive Telegram webhooks
- Process user commands (`/add`, `/portfolio`, etc.)
- Interact with Redis for data storage
- Enqueue background tasks to Celery
- Serve Stripe webhooks
- Health check endpoints

**Technology:**
- FastAPI (async web framework)
- python-telegram-bot 20.7
- Uvicorn (ASGI server)

**Scaling:**
- Stateless (can run multiple instances)
- Load balanced automatically by Railway

---

### 2. Redis Service

**Role:** Storage + Message Broker

**Use Cases:**

**A. Data Storage:**
```
user:<user_id>:profile
user:<user_id>:positions:<SYMBOL>
user:<user_id>:transactions
user:<user_id>:alerts:<SYMBOL>
user:<user_id>:subscription
```

**B. Message Broker:**
- Celery task queue
- Task results storage
- Distributed locking

**Performance:**
- In-memory (ultra-fast)
- <100ms latency
- Persistence enabled (survives restarts)

---

### 3. Celery Worker

**Role:** Background task execution

**Tasks:**

1. **Price Alerts Checker** (every 15 min)
   - Fetch crypto prices
   - Compare against user alerts
   - Send Telegram notifications

2. **AI Recommendations** (daily 8 AM)
   - Analyze portfolios
   - Call Perplexity AI
   - Send personalized advice

3. **Daily Insights** (daily 8 AM)
   - Portfolio summary
   - Market sentiment
   - News highlights

4. **Bonus Trade** (daily 8 AM)
   - Select crypto opportunity
   - Generate AI analysis
   - Send to all users

**Concurrency:**
- 4 worker processes (default)
- Can scale horizontally

---

### 4. Celery Beat

**Role:** Task scheduler (cron-like)

**Schedule:**

```python
beat_schedule = {
    'check-price-alerts': {
        'task': 'backend.tasks.alerts_checker',
        'schedule': crontab(minute='*/15'),  # Every 15 min
    },
    'generate-ai-recommendations': {
        'task': 'backend.tasks.ai_recommender',
        'schedule': crontab(hour=8, minute=0),  # 8:00 AM CET
    },
    'send-daily-insights': {
        'task': 'backend.tasks.daily_insights',
        'schedule': crontab(hour=8, minute=0),  # 8:00 AM CET
    },
    'bonus-trade-of-day': {
        'task': 'backend.tasks.bonus_trade',
        'schedule': crontab(hour=8, minute=0),  # 8:00 AM CET
    },
}
```

**Important:**
- Only 1 instance should run (avoid duplicate tasks)
- Uses Redis for distributed locking

---

## Data Flow Examples

### Example 1: User Adds Position

```
1. User sends: /add BTC 0.5 45000
   ↓
2. Telegram webhook → Backend FastAPI
   ↓
3. Backend parses command
   ↓
4. Backend writes to Redis:
   user:123:positions:BTC -> {qty: 0.5, avg_price: 45000}
   ↓
5. Backend sends confirmation to Telegram
   ↓
6. User receives: "Added 0.5 BTC @ $45,000"
```

**Latency:** <500ms

---

### Example 2: Price Alert Triggers

```
1. Celery Beat triggers at 10:00 AM
   ↓
2. Enqueues task: check-price-alerts
   ↓
3. Celery Worker picks up task
   ↓
4. Worker fetches all alerts from Redis
   ↓
5. Worker calls CoinGecko API for prices
   ↓
6. Worker compares: BTC $80,000 >= TP $80,000 ✓
   ↓
7. Worker sends Telegram notification
   ↓
8. Worker removes alert from Redis
   ↓
9. User receives: "🎯 TAKE PROFIT ALERT - BTC"
```

**Duration:** ~5-10 seconds

---

### Example 3: Daily Briefing (8 AM)

```
1. Celery Beat triggers at 8:00 AM CET
   ↓
2. Enqueues 3 tasks:
   - generate-ai-recommendations
   - send-daily-insights
   - bonus-trade-of-day
   ↓
3. Celery Worker processes in parallel
   ↓
4. Each task:
   a. Fetches user data from Redis
   b. Calls external APIs (CoinGecko, Perplexity)
   c. Generates messages
   d. Sends to Telegram
   ↓
5. Users receive 3 notifications within 30 seconds
```

**Total time:** ~20-30 seconds for all users

---

## Inter-Service Communication

### Backend ↔ Redis

```python
# Write data
redis_client.set('user:123:profile', json.dumps(user_data))

# Read data
data = redis_client.get('user:123:profile')
user_data = json.loads(data)

# Atomic operations
redis_client.incr('user:123:api_calls')
```

### Backend → Celery (Task Enqueue)

```python
# Enqueue task
from backend.tasks.ai_recommender import generate_recommendations
generate_recommendations.delay(user_id=123, symbol='BTC')
```

### Celery → Telegram

```python
# Send notification
import requests
requests.post(
    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
    json={"chat_id": user_id, "text": message}
)
```

---

## Monitoring

### Service Health Checks

**Backend:**
```bash
curl https://your-app.up.railway.app/health
# Response: {"status": "healthy", "redis": "connected"}
```

**Redis:**
```bash
railway run redis-cli ping
# Response: PONG
```

**Celery Worker:**
```bash
railway logs -s celery-worker | grep "ready"
# Should show: celery@worker ready.
```

**Celery Beat:**
```bash
railway logs -s celery-beat | grep "Scheduler"
# Should show: Scheduler: Sending due task...
```

---

## Failure Scenarios

### Backend Crashes

**Impact:**
- Telegram webhooks fail
- Users can't interact with bot

**Recovery:**
- Railway auto-restarts in ~30 seconds
- Telegram queues missed webhooks (up to 24 hours)

### Redis Crashes

**Impact:**
- All services lose data access
- Task queue stops

**Recovery:**
- Railway restarts Redis
- Data persisted (RDB snapshots)
- Services reconnect automatically

### Celery Worker Crashes

**Impact:**
- Background tasks don't execute
- Alerts delayed

**Recovery:**
- Railway restarts worker
- Pending tasks in Redis queue
- Processes when back online

### Celery Beat Crashes

**Impact:**
- No new tasks scheduled
- Alerts stop triggering

**Recovery:**
- Railway restarts beat
- Catches up on missed schedules
- Runs overdue tasks immediately

---

## Performance Optimization

### Backend

1. **Async operations** - FastAPI handles 1000+ req/s
2. **Connection pooling** - Redis connections reused
3. **Response caching** - 60s cache for crypto prices

### Celery

1. **Concurrency** - 4 workers per instance
2. **Task routing** - Separate queues for priorities
3. **Result backend** - Redis stores task results

### Redis

1. **Persistence** - RDB snapshots every 5 minutes
2. **Eviction policy** - LRU for cache entries
3. **Memory limit** - 256 MB (Railway default)

---

## Scaling Strategy

### Current (10-100 users)

- 1 Backend instance
- 1 Celery Worker
- 1 Celery Beat
- 1 Redis instance

**Cost:** ~$10/month

### Future (100-1000 users)

- 2 Backend instances (load balanced)
- 3 Celery Workers (horizontal scaling)
- 1 Celery Beat (only 1 needed)
- 1 Redis instance (vertical scaling)

**Cost:** ~$30/month

### Enterprise (1000+ users)

- 5+ Backend instances
- 10+ Celery Workers
- Redis cluster (sharding)
- PostgreSQL (analytics)
- CDN for static assets

**Cost:** ~$100+/month

---

**Last Updated**: February 10, 2026
