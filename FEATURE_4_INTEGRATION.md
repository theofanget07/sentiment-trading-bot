# Feature 4: AI Recommendations - Integration Instructions

Date: February 4, 2026, 15:25 CET
Branch: `feature/ai-recommendations`
Status: **Ready to integrate**

## ✅ What's Been Done

1. **Created `backend/recommend_handler.py`** 
   - Contains the complete `/recommend` command logic
   - Handles AI recommendations via Perplexity API
   - Analyzes user portfolio positions
   - [View file](https://github.com/theofanget07/sentiment-trading-bot/blob/feature/ai-recommendations/backend/recommend_handler.py)

2. **Backend already ready:**
   - `backend/services/perplexity_client.py` - AI client
   - `backend/tasks/ai_recommender.py` - Celery task

## 🔧 What Needs to Be Done

Modify `backend/bot_webhook.py` to integrate the new command:

### Step 1: Add Import (line ~40, after other imports)

```python
# Feature 4: AI Recommendations handler
try:
    from backend.recommend_handler import recommend_command as recommend_handler_fn
except ImportError:
    from recommend_handler import recommend_command as recommend_handler_fn
```

### Step 2: Add Wrapper Function (line ~750, after `removealert_command`)

```python
# ===== AI RECOMMENDATIONS COMMAND (FEATURE 4) =====

async def recommend_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Wrapper for AI recommendations handler."""
    await recommend_handler_fn(
        update, 
        context, 
        DB_AVAILABLE, 
        portfolio_manager, 
        is_symbol_supported, 
        format_price
    )
```

### Step 3: Register Handler (line ~865, in `setup_application()`)

After this line:
```python
application.add_handler(CommandHandler("removealert", removealert_command))
```

Add:
```python
# AI Recommendations (Feature 4)
application.add_handler(CommandHandler("recommend", recommend_command))
```

## 📝 Update `/start` and `/help` Commands (Optional)

Add documentation for the new command in the welcome messages:

**In `/start` command:**
```markdown
━━━━━━━━━━━━━━━━━━
🤖 **AI RECOMMENDATIONS**

• `/recommend` – Get AI analysis for all your positions

• `/recommend <SYMBOL>` – Analyze a specific crypto
  _Example: `/recommend BTC`_
```

**In `/help` command:**
```markdown
━━━━━━━━━━━━━━━━━━
🤖 **4. AI RECOMMENDATIONS**

Get personalized trading advice powered by Perplexity AI:

**Analyze all positions:**
`/recommend`
→ Generates BUY/SELL/HOLD recommendations for each crypto
→ Based on real-time market analysis (48h news)
→ Considers your P&L and position size

**Analyze specific crypto:**
`/recommend BTC`
→ Faster, focused analysis on one crypto
→ More detailed reasoning

**What you get:**
• Recommendation: BUY / SELL / HOLD
• Confidence score (0-100%)
• AI reasoning based on market sentiment
• Actionable insights

**Response time:** 3-10 seconds

_Powered by Perplexity AI analyzing crypto news and market trends_
```

## ✅ Testing Checklist

Once integrated and deployed on Railway:

1. **Test with empty portfolio:**
   ```
   /recommend
   ```
   Expected: "Portfolio Empty" message

2. **Test with one position:**
   ```
   /add BTC 1 45000
   /recommend BTC
   ```
   Expected: AI recommendation with analysis

3. **Test with multiple positions:**
   ```
   /add ETH 10 2000
   /recommend
   ```
   Expected: Separate recommendation for each crypto

4. **Test invalid crypto:**
   ```
   /recommend DOGE
   ```
   Expected: "not supported" error

5. **Test non-held crypto:**
   ```
   /recommend SOL
   ```
   (if you don't hold SOL)
   Expected: "No SOL Position" message

## 🔑 Environment Variables

Ensure these are set on Railway:

- `PERPLEXITY_API_KEY` - **REQUIRED** for AI recommendations
- `TELEGRAM_BOT_TOKEN` - Already configured
- `REDIS_URL` - Already configured

## 🚀 Deployment

1. Merge this branch into `main`:
   ```bash
   git checkout main
   git merge feature/ai-recommendations
   git push origin main
   ```

2. Railway will auto-deploy

3. Test the `/recommend` command

4. If successful, Feature 4 is **COMPLETE** ✅

## 📊 Expected Output Format

When you run `/recommend BTC`, you'll get:

```
🟡 AI RECOMMENDATION - BTC

━━━━━━━━━━━━━━━━━━
💼 YOUR POSITION
━━━━━━━━━━━━━━━━━━

• Quantity: 1
• Entry Price: $45,000
• Current Price: $75,612
• P&L: +$30,612 USD (+68.03%)

━━━━━━━━━━━━━━━━━━
🎯 RECOMMENDATION: HOLD
🔒 Confidence: 75%
━━━━━━━━━━━━━━━━━━

📊 AI Analysis:

[Perplexity AI detailed analysis here...]

_Powered by Perplexity AI_
_Use `/summary` for portfolio overview_
```

## ⚡ Quick Integration (Copy-Paste Method)

If you want to integrate quickly without manual edits:

1. Download [bot_webhook_complete.py](link_here) from this PR
2. Replace your current `backend/bot_webhook.py` with it
3. Commit and push
4. Done!

## ❓ Troubleshooting

### Error: "AI Service Unavailable"
- Check `PERPLEXITY_API_KEY` is set on Railway
- Verify Perplexity API quota (free tier: 5 requests/day)

### Error: "Database offline"
- Check Redis is running on Railway
- Verify `REDIS_URL` environment variable

### Response takes >10 seconds
- Normal for Perplexity API (3-10s response time)
- Consider adding caching if needed

## 📅 Timeline

- **Created:** February 4, 2026, 15:25 CET
- **Estimated integration time:** 5-10 minutes
- **Testing time:** 5 minutes
- **Total:** 15 minutes to Feature 4 complete

---

**Next Feature:** Feature 5 - Daily Insights (automated task at 8am CET)
**Status:** Backend ready, will test tomorrow morning
