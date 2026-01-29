# 🚀 RAILWAY DEPLOYMENT GUIDE

**Date:** 29 janvier 2026  
**Objectif:** Déployer le bot en production 24/7 sur Railway  
**Durée:** 2-3 heures

---

## 🎯 ARCHITECTURE PRODUCTION

```
RAILWAY CLOUD
├── Service 1: Telegram Bot (web)
│   └── bot.py (répond aux users)
├── Service 2: Celery Worker (worker)
│   └── Exécute tasks (fetch, analyze)
├── Service 3: Celery Beat (beat)
│   └── Scheduler (toutes les 30 min, heures, etc.)
├── PostgreSQL Plugin
│   └── Database cloud (articles, users)
└── Redis Plugin
    └── Message broker (Celery)
```

---

## 📝 PRÉREQUIS

### **Déjà fait:**
- ✅ Compte Railway créé
- ✅ Termes acceptés
- ✅ Repository GitHub public
- ✅ Procfile + railway.toml créés

### **À préparer:**
- API Keys:
  - PERPLEXITY_API_KEY
  - TELEGRAM_BOT_TOKEN
  - SENDGRID_API_KEY (on le fera après)
  - TELEGRAM_CHANNEL_ID (on le fera après)

---

## 🚀 ÉTAPE 1: CRÉER LE PROJET RAILWAY (10 min)

### **A. Nouveau projet**

1. **Dashboard Railway:** https://railway.app/dashboard
2. **Clique sur:** "New Project"
3. **Sélectionne:** "Deploy from GitHub repo"
4. **Cherche:** `sentiment-trading-bot`
5. **Clique sur:** "Deploy Now"

⚠️ Railway va détecter automatiquement:
- Python project
- requirements.txt
- Procfile

### **B. Attendre le premier build**

✅ Tu verras:
```
Building...
✓ Installing Python 3.11
✓ Installing dependencies
✓ Build complete
❌ Deploy failed (normal, pas de DATABASE_URL encore)
```

**C'est normal !** On ajoute PostgreSQL + Redis maintenant.

---

## 💾 ÉTAPE 2: AJOUTER POSTGRESQL (5 min)

### **A. Ajouter le plugin**

1. **Dans ton projet Railway** > "New Service"
2. **Sélectionne:** "Database" > "PostgreSQL"
3. **Clique:** "Add PostgreSQL"

✅ Railway crée automatiquement:
- Database PostgreSQL
- Variable `DATABASE_URL` (auto-injectée)

### **B. Vérifier la variable**

1. **Clique sur le service PostgreSQL**
2. **Onglet:** "Variables"
3. **Tu dois voir:** `DATABASE_URL=postgresql://...`

✅ **Cette variable sera accessible par tous tes services !**

---

## 📦 ÉTAPE 3: AJOUTER REDIS (5 min)

### **A. Ajouter le plugin**

1. **Dans ton projet** > "New Service"
2. **Sélectionne:** "Database" > "Redis"
3. **Clique:** "Add Redis"

✅ Railway crée automatiquement:
- Redis instance
- Variable `REDIS_URL` (auto-injectée)

### **B. Vérifier la variable**

1. **Clique sur le service Redis**
2. **Onglet:** "Variables"
3. **Tu dois voir:** `REDIS_URL=redis://...`

---

## 🔑 ÉTAPE 4: CONFIGURER LES VARIABLES D'ENVIRONNEMENT (10 min)

### **A. Accéder aux variables**

1. **Clique sur ton service principal** (sentiment-trading-bot)
2. **Onglet:** "Variables"
3. **Clique:** "New Variable"

### **B. Ajouter les variables**

**Ajoute une par une:**

```bash
PERPLEXITY_API_KEY=pplx-xxxxxxxxxxxxxxxxxxxx
TELEGRAM_BOT_TOKEN=7xxxxxxxxx:xxxxxxxxxxxxxxxxxxxxxxxxxxx
PORT=8080
```

**Variables optionnelles (pour plus tard):**
```bash
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxxxx
SENDGRID_FROM_EMAIL=ton@email.com
SENDGRID_FROM_NAME=Crypto Sentiment Bot
TELEGRAM_CHANNEL_ID=-1001234567890
```

### **C. Les variables auto-injectées**

Railway ajoute automatiquement:
- ✅ `DATABASE_URL` (depuis PostgreSQL)
- ✅ `REDIS_URL` (depuis Redis)

**Tu n'as PAS besoin de les ajouter manuellement !**

---

## 👨‍💻 ÉTAPE 5: CRÉER LES SERVICES CELERY (15 min)

### **A. Service Celery Worker**

1. **Nouveau service** > "GitHub Repo"
2. **Sélectionne:** `sentiment-trading-bot` (même repo)
3. **Settings** > "Deploy" >
   - **Start Command:** `cd backend && celery -A celery_app worker --loglevel=info --concurrency=4`
   - **Service Name:** `celery-worker`

4. **Variables:** Copie TOUTES les variables du service principal
   - PERPLEXITY_API_KEY
   - TELEGRAM_BOT_TOKEN
   - (DATABASE_URL et REDIS_URL sont auto-injectés)

### **B. Service Celery Beat**

1. **Nouveau service** > "GitHub Repo"
2. **Sélectionne:** `sentiment-trading-bot` (même repo)
3. **Settings** > "Deploy" >
   - **Start Command:** `cd backend && celery -A celery_app beat --loglevel=info`
   - **Service Name:** `celery-beat`

4. **Variables:** Copie TOUTES les variables du service principal

---

## ⌛ ÉTAPE 6: INITIALISER LA DATABASE (5 min)

### **A. Créer les tables**

Railway ne peut pas exécuter de commandes directement, donc on va créer un script d'initialisation.

**Option 1: Via Railway CLI (recommandé)**

```bash
# Installer Railway CLI
npm i -g @railway/cli

# Login
railway login

# Link au projet
railway link

# Exécuter commande
railway run python backend/init_db.py
```

**Option 2: Créer un endpoint d'initialisation**

On ajoutera un endpoint `/init-db` dans le bot pour créer les tables.

---

## 📡 ÉTAPE 7: DÉPLOYER ET TESTER (15 min)

### **A. Redeploy tous les services**

1. **Service principal** > "Deployments" > "Redeploy"
2. **Celery Worker** > "Deployments" > "Deploy"
3. **Celery Beat** > "Deployments" > "Deploy"

### **B. Vérifier les logs**

**Service principal (bot):**
```
🤖 Bot started successfully
📱 Listening for messages...
```

**Celery Worker:**
```
celery@railway ready.
Tasks:
  . tasks.fetch_news_task
  . tasks.analyze_articles_task
```

**Celery Beat:**
```
beat: Starting...
Scheduler: Sending due task fetch-crypto-news
```

### **C. Tester le bot Telegram**

1. **Ouvre Telegram**
2. **Cherche:** `@sentiment_trading_test_bot`
3. **Envoie:** `/start`

✅ **Attendu:**
```
🚀 Welcome to Crypto Sentiment Bot!

I analyze crypto news sentiment using AI.

Commands:
/start - Show this message
/help - Get help
/analyze - Analyze sentiment
```

---

## 📊 ÉTAPE 8: MONITORING PRODUCTION (Continu)

### **A. Vérifier que tout tourne**

**Dashboard Railway:**
- ✅ Bot service: Running
- ✅ Celery Worker: Running
- ✅ Celery Beat: Running
- ✅ PostgreSQL: Running
- ✅ Redis: Running

### **B. Vérifier les tasks automatiques**

**Dans les logs Celery Beat (toutes les 30 min):**
```
[07:30:00] Scheduler: Sending due task fetch-crypto-news
[08:00:00] Scheduler: Sending due task analyze-articles
```

**Dans les logs Celery Worker:**
```
[07:30:05] Task tasks.fetch_news_task received
[07:30:10] 🔍 Starting news fetch...
[07:30:15] ✅ Fetched 23 articles
```

### **C. Vérifier la database**

**Via Railway PostgreSQL:**
1. **Service PostgreSQL** > "Data"
2. **Query:**
```sql
SELECT COUNT(*) FROM articles;
SELECT COUNT(*) FROM articles WHERE is_analyzed = true;
```

---

## 🐛 TROUBLESHOOTING

### **Erreur: "Module not found"**
```bash
# Vérifier que requirements.txt est à jour
# Redeploy le service
```

### **Erreur: "Cannot connect to database"**
```bash
# Vérifier que DATABASE_URL est injectée
# Service > Variables > DATABASE_URL doit exister
```

### **Erreur: "Redis connection failed"**
```bash
# Vérifier que REDIS_URL est injectée
# Service > Variables > REDIS_URL doit exister
```

### **Bot ne répond pas sur Telegram**
```bash
# Vérifier les logs du service principal
# Vérifier TELEGRAM_BOT_TOKEN dans variables
# Tester avec /start
```

### **Tasks Celery ne s'exécutent pas**
```bash
# Vérifier que Celery Worker ET Beat tournent
# Vérifier les logs des deux services
# Vérifier REDIS_URL est accessible
```

---

## ✅ CHECKLIST FINALE

### **Services Railway:**
- [ ] sentiment-trading-bot (bot principal)
- [ ] celery-worker (background tasks)
- [ ] celery-beat (scheduler)
- [ ] PostgreSQL (database)
- [ ] Redis (message broker)

### **Variables d'environnement:**
- [ ] PERPLEXITY_API_KEY
- [ ] TELEGRAM_BOT_TOKEN
- [ ] DATABASE_URL (auto)
- [ ] REDIS_URL (auto)
- [ ] PORT=8080

### **Tests:**
- [ ] Bot répond sur Telegram (/start)
- [ ] Articles fetchés automatiquement (logs)
- [ ] Articles analysés automatiquement (logs)
- [ ] Database se remplit (query SQL)
- [ ] Celery tasks scheduled (logs Beat)

### **Monitoring:**
- [ ] Tous les services "Running"
- [ ] Logs sans erreurs critiques
- [ ] Bot accessible 24/7
- [ ] Tasks exécutées automatiquement

---

## 🎉 SUCCÈS !

Si tout est ✅:
- Ton bot tourne **24/7 sur Railway**
- Fetch automatique **toutes les 30 min**
- Analyse automatique **toutes les heures**
- **Même si ton Mac est éteint** 🚀

---

## 📈 COÛTS RAILWAY

**Plan gratuit (Trial):**
- $5/mois de crédit gratuit
- Suffisant pour tester (1-2 semaines)

**Plan Hobby ($5/mois):**
- $5/mois + usage
- Estimation pour ton bot:
  - Bot: ~$2/mois
  - Celery Worker: ~$2/mois
  - Celery Beat: ~$1/mois
  - PostgreSQL: ~$1/mois
  - Redis: ~$1/mois
  - **Total: ~$7-10/mois**

**Rentable dès 2 users premium (€9/mois chacun) = €18/mois !**

---

## 👍 PROCHAINES ÉTAPES

1. ✅ Railway déployé
2. 📱 Configurer Telegram Channel (15 min)
3. 📧 Configurer SendGrid (15 min)
4. 🏁 Launch beta (inviter premiers users)
5. 💰 Setup Stripe (week 3)

---

**Repository:** https://github.com/theofanget07/sentiment-trading-bot  
**Railway Dashboard:** https://railway.app/dashboard  
**Status:** 🚀 READY FOR PRODUCTION DEPLOYMENT
