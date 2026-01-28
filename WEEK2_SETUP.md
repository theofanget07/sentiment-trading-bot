# 🚀 WEEK 2 SETUP GUIDE - AUTOMATISATION

## 🎯 Objectif Week 2

Transformer le bot manuel en système d'automatisation complet:
- 🔄 Auto-fetching RSS + Reddit (50-100 articles/jour)
- 📧 Daily email digests (8h00 UTC)
- 📱 Telegram channel premium (signaux automatiques)
- 💾 PostgreSQL database (historique + analytics)
- ⏱️ Background tasks (Celery + Redis)

---

## 1️⃣ INSTALLATION

### A. Installer les dépendances

```bash
cd backend
pip install -r requirements.txt
```

### B. Configurer les variables d'environnement

1. Copier `.env.example` vers `.env`:
```bash
cp .env.example .env
```

2. Éditer `.env` avec vos vraies clés:
```bash
# Déjà configurées Week 1
TELEGRAM_BOT_TOKEN=...
PERPLEXITY_API_KEY=...

# NOUVELLES pour Week 2
DATABASE_URL=postgresql://user:password@localhost:5432/sentiment_bot
REDIS_URL=redis://localhost:6379/0
SENDGRID_API_KEY=...
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
TELEGRAM_CHANNEL_ID=@your_channel
```

---

## 2️⃣ SETUP INFRASTRUCTURE

### A. PostgreSQL (Base de données)

#### Option 1: Railway (Production - Recommandé)
1. Aller sur [railway.app](https://railway.app)
2. Créer nouveau projet → PostgreSQL
3. Copier `DATABASE_URL` dans `.env`

#### Option 2: Local (Développement)
```bash
# Mac avec Homebrew
brew install postgresql
brew services start postgresql

# Créer la database
psql postgres
CREATE DATABASE sentiment_bot;
\q
```

### B. Redis (Queue pour Celery)

#### Option 1: Railway (Production)
1. Dans le même projet Railway → Add Redis
2. Copier `REDIS_URL` dans `.env`

#### Option 2: Local (Développement)
```bash
# Mac avec Homebrew
brew install redis
brew services start redis

# Tester
redis-cli ping  # Devrait répondre "PONG"
```

### C. SendGrid (Emails)

1. Aller sur [sendgrid.com](https://sendgrid.com)
2. Créer compte gratuit (100 emails/jour)
3. Settings → API Keys → Create API Key
4. Copier dans `.env` → `SENDGRID_API_KEY`
5. Sender Authentication → Single Sender → Vérifier email

### D. Reddit API (Optionnel)

1. Aller sur [reddit.com/prefs/apps](https://reddit.com/prefs/apps)
2. Create App → Script
3. Copier `client_id` et `secret` dans `.env`

### E. Telegram Channel (Premium)

1. Créer un channel Telegram:
   - Ouvrir Telegram → New Channel
   - Nom: "Sentiment Trading Signals" (ou autre)
   - Type: Public (avec @username) ou Private

2. Ajouter ton bot comme admin:
   - Channel Settings → Administrators
   - Add Administrator → Chercher ton bot
   - Donner permission "Post Messages"

3. Obtenir le Channel ID:
   - Si public: `@your_channel_name`
   - Si private: Utilise [@getidsbot](https://t.me/getidsbot)

4. Mettre dans `.env`:
```bash
TELEGRAM_CHANNEL_ID=@your_channel  # ou -1001234567890
```

---

## 3️⃣ INITIALISER LA DATABASE

```bash
cd backend

# Test connection
python database.py
# Devrait afficher: "Database connection OK"

# Initialize tables
python -c "from database import init_db; init_db()"
# Devrait créer toutes les tables
```

---

## 4️⃣ TESTER CHAQUE COMPOSANT

### Test 1: News Fetcher (RSS + Reddit)

```bash
python news_fetcher.py
```

**Résultat attendu:**
```
🔍 Fetching from CoinDesk...
  ✅ Bitcoin Surges Past $50k...
  ✅ Ethereum ETF Approval...
✅ Fetched 15 articles from CoinDesk
🎯 Total RSS articles: 45
🎯 Total Reddit posts: 25
💾 Saved 70 new articles to database
```

### Test 2: Sentiment Analyzer (sur articles fetchés)

```bash
python -c "
from sentiment_analyzer import SentimentAnalyzer
from database import get_db_session
from models import Article

analyzer = SentimentAnalyzer()
with get_db_session() as db:
    article = db.query(Article).filter(Article.is_analyzed == False).first()
    if article:
        result = analyzer.analyze(article.title)
        print(f'Title: {article.title}')
        print(f'Sentiment: {result}')
"
```

### Test 3: Email Service

```bash
python email_service.py
# Enter your test email when prompted
```

**Vérifier:** Email reçu avec "Test Email - Sentiment Bot"

### Test 4: Telegram Channel Broadcaster

```bash
python channel_broadcaster.py
```

**Vérifier:** Message de test dans ton channel Telegram

### Test 5: Celery Tasks (individuellement)

```bash
# Terminal 1: Démarrer Redis
redis-server  # Si local

# Terminal 2: Démarrer Celery worker
celery -A celery_app worker --loglevel=info

# Terminal 3: Tester les tasks
python tasks.py
```

---

## 5️⃣ DÉMARRAGE COMPLET

### A. Développement Local

**Terminal 1: Redis**
```bash
redis-server
```

**Terminal 2: Celery Worker**
```bash
cd backend
celery -A celery_app worker --loglevel=info
```

**Terminal 3: Celery Beat (Scheduler)**
```bash
cd backend
celery -A celery_app beat --loglevel=info
```

**Terminal 4: Telegram Bot**
```bash
cd backend
python bot.py
```

### B. Vérifier que tout fonctionne

1. **Celery Beat** devrait afficher:
```
Scheduler: Sending due task fetch-crypto-news
Scheduler: Sending due task analyze-articles
```

2. **Celery Worker** devrait exécuter les tasks:
```
[2026-01-28 20:00:00] Task tasks.fetch_news_task started
[2026-01-28 20:00:03] Task tasks.fetch_news_task succeeded
```

3. **Database** devrait se remplir d'articles:
```bash
psql $DATABASE_URL -c "SELECT COUNT(*) FROM articles;"
# Devrait augmenter toutes les 30 minutes
```

---

## 6️⃣ SCHEDULE DES TASKS

Voici quand chaque task s'exécute:

| Task | Fréquence | Heure | Action |
|------|-----------|-------|--------|
| **fetch_news_task** | Toutes les 30 min | :00, :30 | Fetch RSS + Reddit |
| **analyze_articles_task** | Toutes les heures | :00 | Analyse sentiment (20 articles) |
| **send_daily_digest_task** | Quotidien | 8:00 AM UTC | Email premium users |
| **post_telegram_signals_task** | Toutes les 2h | :00 | Post high-confidence signals |
| **cleanup_old_data_task** | Hebdomadaire | Dimanche 3:00 AM | Delete articles >30 jours |

---

## 7️⃣ MONITORING & DEBUG

### Vérifier le statut des tasks

```bash
# Flower (Celery monitoring UI)
pip install flower
celery -A celery_app flower
# Ouvrir http://localhost:5555
```

### Vérifier la database

```bash
# Nombre d'articles
psql $DATABASE_URL -c "SELECT COUNT(*) FROM articles;"

# Articles récents
psql $DATABASE_URL -c "SELECT title, sentiment, confidence FROM articles WHERE is_analyzed = true ORDER BY analyzed_at DESC LIMIT 5;"

# Users
psql $DATABASE_URL -c "SELECT telegram_id, subscription_level FROM users;"
```

### Logs

```bash
# Voir les logs Celery en temps réel
tail -f celery.log

# Logs du bot Telegram
tail -f bot.log
```

---

## 8️⃣ TROUBLESHOOTING

### Problème: "Connection refused" (Redis)
**Solution:**
```bash
brew services restart redis
redis-cli ping  # Doit répondre PONG
```

### Problème: "Database connection failed"
**Solution:**
```bash
# Vérifier DATABASE_URL dans .env
psql $DATABASE_URL -c "SELECT 1;"
```

### Problème: "SendGrid API error"
**Solution:**
1. Vérifier `SENDGRID_API_KEY` dans `.env`
2. Vérifier sender email vérifié dans SendGrid
3. Regarder SendGrid Activity Feed

### Problème: "Telegram channel posting failed"
**Solution:**
1. Bot ajouté comme admin du channel?
2. Permission "Post Messages" activée?
3. `TELEGRAM_CHANNEL_ID` correct dans `.env`?

---

## 9️⃣ PROCHAINES ÉTAPES (JOUR 2-4)

- ✅ JOUR 1: RSS feeds + Celery + Redis ← **DONE!**
- 🕐 JOUR 2: FastAPI REST API + alembic migrations
- 🕐 JOUR 3: Free vs Premium tiers + Stripe integration
- 🕐 JOUR 4: Tests complets + monitoring + deploy Railway

---

## 📝 COMMANDES UTILES

```bash
# Fetch news maintenant (manual trigger)
celery -A celery_app call tasks.fetch_news_task

# Analyser articles (manual trigger)
celery -A celery_app call tasks.analyze_articles_task

# Envoyer digest test
celery -A celery_app call tasks.send_daily_digest_task

# Reset database (DANGER!)
python -c "from database import Base, engine; Base.metadata.drop_all(engine); Base.metadata.create_all(engine)"

# Voir toutes les tasks scheduled
celery -A celery_app inspect scheduled

# Voir tasks actives
celery -A celery_app inspect active
```

---

## ✅ CHECKLIST JOUR 1

- [ ] PostgreSQL installé et connecté
- [ ] Redis installé et running
- [ ] SendGrid API key configurée
- [ ] Reddit API configurée (optionnel)
- [ ] Telegram channel créé
- [ ] Bot ajouté comme admin du channel
- [ ] Database initialisée (tables créées)
- [ ] Test news_fetcher.py → articles fetched
- [ ] Test email_service.py → email reçu
- [ ] Test channel_broadcaster.py → message posté
- [ ] Celery worker démarre sans erreur
- [ ] Celery beat schedule des tasks
- [ ] Bot Telegram fonctionne toujours

**Si tous les ✅ → JOUR 1 COMPLET! 🎉**

---

## 🆘 Support

Problèmes? Check:
1. Logs Celery: `celery -A celery_app worker --loglevel=debug`
2. PostgreSQL: `psql $DATABASE_URL`
3. Redis: `redis-cli monitor`
4. [COMPLETE_KIT.md](./COMPLETE_KIT.md) → Troubleshooting section
