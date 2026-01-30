# 🚀 Railway Multi-Service Deployment Guide

## 📋 PROBLÈME RÉSOLU

Railway ne supporte **pas** plusieurs fichiers `railway.toml` par service, et le `Procfile` ne fonctionne que pour Nixpacks (pas Docker).

**Solution :** Script `entrypoint.sh` intelligent qui détecte quel service lancer via la variable `SERVICE_TYPE`.

---

## ✅ ARCHITECTURE

```
sentiment-trading-bot/
├── entrypoint.sh          # 🎯 Script intelligent (NOUVEAU)
├── Dockerfile             # 🐳 Utilise entrypoint.sh (MODIFIÉ)
├── railway.toml           # ⚙️  Config Railway commune
└── backend/
    ├── bot_webhook.py     # Web service
    ├── celery_app.py      # Celery config
    └── tasks.py           # Tâches automatiques
```

---

## 🔧 ÉTAPE 1 : CONFIGURATION RAILWAY DASHBOARD

### **Service "web" (FastAPI + Bot Telegram)**

1. Railway Dashboard → Service **"web"**
2. **Settings** → **Variables**
3. **Ajoute cette variable :**

```
SERVICE_TYPE=web
```

4. **Save**
5. **Redeploy** (Manual Redeploy)

---

### **Service "worker" (Celery Worker)**

1. Railway Dashboard → Service **"worker"**
2. **Settings** → **Variables**
3. **Ajoute cette variable :**

```
SERVICE_TYPE=worker
```

4. **Save**
5. **Redeploy** (Manual Redeploy)

---

### **Service "beat" (Celery Beat Scheduler)**

1. Railway Dashboard → Service **"beat"**
2. **Settings** → **Variables**
3. **Ajoute cette variable :**

```
SERVICE_TYPE=beat
```

4. **Save**
5. **Redeploy** (Manual Redeploy)

---

## 📊 VÉRIFICATION DES LOGS

Après déploiement, vérifie que chaque service démarre correctement :

### ✅ **Service "web" - Logs attendus :**

```
🚀 Starting Railway service...
📦 SERVICE_TYPE: web
🌐 Starting Web Service (FastAPI + Telegram Bot)
INFO:backend.bot_webhook:🤖 Bot ready in webhook mode
INFO:backend.bot_webhook:🚀 FastAPI server started
INFO:     Uvicorn running on http://0.0.0.0:8080
```

### ✅ **Service "worker" - Logs attendus :**

```
🚀 Starting Railway service...
📦 SERVICE_TYPE: worker
⚙️  Starting Celery Worker
celery@<hostname> ready.
Registered tasks:
  - tasks.fetch_news_task
  - tasks.analyze_articles_task
  - tasks.send_daily_digest_task
Connected to redis://...
```

### ✅ **Service "beat" - Logs attendus :**

```
🚀 Starting Railway service...
📦 SERVICE_TYPE: beat
⏰ Starting Celery Beat Scheduler
beat: Starting...
Scheduler: Sending due task fetch-crypto-news
Scheduler: Sending due task analyze-articles
```

---

## ❌ DÉPANNAGE

### **Problème : Service crash immédiatement**

**Cause :** Variable `SERVICE_TYPE` non définie ou invalide

**Solution :**
1. Vérifie que `SERVICE_TYPE` est bien défini dans **Settings → Variables**
2. Valeurs valides : `web`, `worker`, `beat` (en minuscules)
3. Redéploie après ajout de la variable

---

### **Problème : Tous les services démarrent FastAPI**

**Cause :** `entrypoint.sh` n'est pas exécutable ou Railway n'utilise pas le nouveau Dockerfile

**Solution :**
1. Force un rebuild complet : **Settings → Deployments → Redeploy**
2. Vérifie les Build Logs pour confirmer que `entrypoint.sh` est copié
3. Vérifie que le commit GitHub contient bien les fichiers `entrypoint.sh` et `Dockerfile` modifié

---

### **Problème : Worker/Beat ne reçoivent pas les tâches**

**Cause :** Variables Redis ou Celery manquantes

**Solution :**
1. Vérifie que **tous les services** ont accès aux variables Redis :
   - `REDIS_URL`
   - Ou : `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`
2. Redéploie **worker** et **beat** après ajout des variables

---

## 🎯 VARIABLES D'ENVIRONNEMENT OBLIGATOIRES

### **Service "web" :**

```bash
SERVICE_TYPE=web
TELEGRAM_TOKEN=<ton_token>
REDIS_URL=<redis_url>
OPENAI_API_KEY=<openai_key>
WEBHOOK_URL=<url_railway>
```

### **Service "worker" :**

```bash
SERVICE_TYPE=worker
REDIS_URL=<redis_url>
OPENAI_API_KEY=<openai_key>
TELEGRAM_TOKEN=<ton_token>  # Pour envoyer les alertes
```

### **Service "beat" :**

```bash
SERVICE_TYPE=beat
REDIS_URL=<redis_url>
```

---

## 🔍 COMMENT ÇA FONCTIONNE

### **1. Build unique (Dockerfile)**

Railway build **une seule image Docker** pour tous les services :

```dockerfile
ENTRYPOINT ["/app/entrypoint.sh"]
```

### **2. Détection du service (entrypoint.sh)**

Au démarrage, le script `entrypoint.sh` lit `$SERVICE_TYPE` :

```bash
case "$SERVICE_TYPE" in
  web)    exec uvicorn bot_webhook:app ... ;;
  worker) exec python -m celery -A backend.celery_app worker ... ;;
  beat)   exec python -m celery -A backend.celery_app beat ... ;;
esac
```

### **3. Lancement du bon processus**

Chaque service Railway démarre avec **la même image**, mais exécute **un processus différent** selon `SERVICE_TYPE`.

---

## ✅ CHECKLIST FINALE

- [ ] Les 3 commits sont poussés sur GitHub (entrypoint.sh, Dockerfile, ce guide)
- [ ] Railway a détecté et rebuild les 3 services
- [ ] Variable `SERVICE_TYPE=web` configurée dans service "web"
- [ ] Variable `SERVICE_TYPE=worker` configurée dans service "worker"
- [ ] Variable `SERVICE_TYPE=beat` configurée dans service "beat"
- [ ] Les 3 services sont **Active** (vert) dans Railway Dashboard
- [ ] Les logs de "web" montrent FastAPI démarré
- [ ] Les logs de "worker" montrent Celery worker prêt
- [ ] Les logs de "beat" montrent Celery beat scheduler actif

---

## 🎉 RÉSULTAT ATTENDU

Une fois configuré, tu auras :

✅ **Service "web"** → Bot Telegram + API FastAPI (port 8080)
✅ **Service "worker"** → Exécute les analyses (4 workers parallèles)
✅ **Service "beat"** → Planifie les tâches automatiques (toutes les 4h)

Les 3 services partagent :
- La même codebase GitHub
- La même image Docker
- Les mêmes variables d'environnement (sauf `SERVICE_TYPE`)

---

## 📞 SUPPORT

Si un service ne démarre pas :

1. Vérifie les **Deploy Logs** (onglet Deploy Logs)
2. Cherche les lignes avec `🚀 Starting Railway service...`
3. Vérifie que `SERVICE_TYPE` est affiché correctement
4. Si `SERVICE_TYPE: not set` → Ajoute la variable dans Settings

---

**Créé le :** 30 janvier 2026  
**Auteur :** Trading Bot Business - Week 2  
**Status :** ✅ Production Ready
