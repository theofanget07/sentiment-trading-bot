# 🚀 Instructions de Déploiement Railway

## 🎯 Objectif

Corrections appliquées pour résoudre le problème du **Morning Briefing quotidien à 8h**.

---

## ✅ Ce qui a été fait sur GitHub

1. **`backend/crypto_prices.py`** - Amélioration rate limiting CoinGecko
2. **`backend/celery_app.py`** - Scheduler Celery avec logs verbeux
3. **`backend/tasks/morning_briefing.py`** - Task résilient avec mode dégradé
4. **`test_morning_briefing.py`** - Script de test manuel
5. **`MORNING_BRIEFING_FIX.md`** - Documentation complète

Tous les fichiers sont sur la branche `main` : https://github.com/theofanget07/sentiment-trading-bot

---

## 🛠️ Ce qu'il faut faire sur Railway

### 1. Vérifier le déploiement automatique

Railway devrait avoir détecté les changements GitHub et redéployé automatiquement.

**À vérifier :**

1. Aller sur [Railway Dashboard](https://railway.app/)
2. Sélectionner le projet `sentiment-trading-bot`
3. Vérifier que le dernier déploiement est **SUCCESS** (✅)
4. Vérifier l'heure du déploiement : doit être après **2026-02-08 18:00 CET**

### 2. Vérifier les logs de démarrage

Dans Railway, aller dans **Logs** et chercher :

```
======================================================================
🚀 CELERY CONFIGURATION LOADED - MORNING BRIEFING ACTIVE
======================================================================
📦 Tasks included: 3 modules
   1. backend.tasks.alerts_checker
   2. backend.tasks.ai_recommender (manual via /recommend)
   3. backend.tasks.morning_briefing ⭐ NEW

⏰ Beat schedules: 2 tasks configured
   1. check-price-alerts     → Every 15 minutes
   2. send-morning-briefing  → Daily 08:00 CET ⭐ NEW

🎯 Next morning briefing: 2026-02-09 08:00:00 CET
======================================================================
```

**✅ Si tu vois ça** = Configuration correcte !  
**❌ Si tu ne vois pas ça** = Problème de déploiement

### 3. (Optionnel) Tester manuellement

Si tu veux tester MAINTENANT sans attendre 8h demain :

**Option A : Via Railway CLI**
```bash
railway run python test_morning_briefing.py
```

**Option B : Forcer l'exécution**

Dans Railway Console :
```bash
python -c "from backend.tasks.morning_briefing import send_morning_briefing; print(send_morning_briefing())"
```

Cela va envoyer le briefing **immédiatement** à tous les utilisateurs.

### 4. Attendre demain matin 8h

Le Morning Briefing s'exécutera automatiquement à **8:00 AM CET** demain.

**Logs à surveiller à 8h dans Railway :**

```
[MORNING BRIEFING] 🌅 Starting Morning Briefing task...
[MORNING BRIEFING] Task started at: 2026-02-09 08:00:00 CET
[MORNING BRIEFING] 📊 Step 1/3: Analyzing Bonus Trade of the Day...
[MORNING BRIEFING] 🏆 Bonus Trade: BTC - BUY (Confidence: 75%)
[MORNING BRIEFING] 👥 Step 2/3: Processing users...
[MORNING BRIEFING] Found 5 users to process
[MORNING BRIEFING] ➡️ Processing user 123456 (1/5)...
[MORNING BRIEFING] ✅ Successfully sent to user 123456
...
[MORNING BRIEFING] ✅ Task completed: 5/5 sent, 0 no portfolio, 0 errors
```

---

## ⚠️ Si le problème persiste

### Diagnostic 1 : Vérifier les variables d'environnement

Dans Railway, vérifier que ces variables sont bien définies :

```
REDIS_URL=redis://...
PERPLEXITY_API_KEY=pplx-...
TELEGRAM_BOT_TOKEN=...
```

### Diagnostic 2 : Vérifier les services Railway

**Services requis :**
1. **Backend (FastAPI)** - API principale
2. **Worker (Celery)** - Exécute les tasks
3. **Beat (Celery Beat)** - Scheduler pour tâches périodiques ⭐
4. **Redis** - Message broker

**❌ Problème fréquent** : Le service **Beat** n'est pas démarré !

**Solution :**

1. Vérifier que tu as bien un service "Beat" dans Railway
2. Sa commande de démarrage doit être :
   ```bash
   celery -A backend.celery_app beat --loglevel=info
   ```
3. Si le service n'existe pas, le créer :
   - New Service → From GitHub Repo
   - Ajouter variable `START_COMMAND=beat`
   - Start command : `celery -A backend.celery_app beat --loglevel=info`

### Diagnostic 3 : Vérifier que Celery Beat tourne

Dans les logs du service **Beat**, tu dois voir :

```
celery beat v5.3.6 (emerald-rush) is starting.
LocalTime -> 2026-02-08 18:00:00
Scheduler -> celery.beat.PersistentScheduler
```

Et toutes les 5 secondes environ :
```
Scheduler: Sending due task check-price-alerts (backend.tasks.alerts_checker.check_all_price_alerts)
```

**❌ Si tu ne vois pas ça** = Beat ne tourne pas correctement

---

## 📊 Monitoring Post-Déploiement

### J+1 (demain 09/02/2026)

- [ ] Vérifier logs Railway à 8h05 CET
- [ ] Confirmer réception du briefing sur Telegram
- [ ] Vérifier aucune erreur CoinGecko 429

### J+2-J+7 (semaine)

- [ ] Briefing envoyé tous les jours à 8h
- [ ] Pas d'erreurs récurrentes dans logs
- [ ] Utilisateurs reçoivent le contenu complet (portfolio + bonus trade + news)

---

## 🔗 Liens Utiles

- **GitHub Repo** : https://github.com/theofanget07/sentiment-trading-bot
- **Railway Dashboard** : https://railway.app/
- **Documentation Fix** : [MORNING_BRIEFING_FIX.md](MORNING_BRIEFING_FIX.md)
- **Script Test** : [test_morning_briefing.py](test_morning_briefing.py)

---

## 📧 Email Professionnel - Prochaines Étapes

Pour créer ton adresse email pro (`hello@sentimenttradingbot.com`) :

### Étape 1 : Acheter un domaine

**Options recommandées :**
- **Namecheap** : ~€10/an (.com)
- **Google Domains** : ~€12/an
- **OVH** : ~€8/an

**Domaines disponibles (vérifier) :**
- `sentimenttradingbot.com` ✅
- `sentimentbot.io` ✅
- `cryptosentiment.bot` ✅

### Étape 2 : Configurer l'email

**Option 1 : Google Workspace** (€5.75/mois/utilisateur)
- Email : `hello@sentimenttradingbot.com`
- Gmail interface
- Très fiable
- **Recommandé pour business**

**Option 2 : Zoho Mail** (GRATUIT jusqu'à 5 utilisateurs)
- Email : `support@sentimenttradingbot.com`
- Gratuit pour 1 domaine
- Interface web correcte
- **Recommandé pour MVP/Phase 1**

**Option 3 : Proton Mail** (€4/mois)
- Email : `contact@sentimenttradingbot.com`
- Privacy-first
- Sécurité maximale

### Étape 3 : Utiliser dans le bot

1. Ajouter variable Railway : `SUPPORT_EMAIL=hello@sentimenttradingbot.com`
2. Modifier messages Telegram pour inclure l'email
3. Créer page "Contact" sur futur site web
4. Ajouter dans mentions légales/CGU

### Étape 4 : Configuration DNS

Une fois domaine acheté, configurer les enregistrements DNS :

```
Type  | Host | Value              | Priority
------|------|--------------------|---------
MX    | @    | mail.zoho.com      | 10
MX    | @    | mail2.zoho.com     | 20
TXT   | @    | v=spf1 include:zoho.com ~all
```

(Exemple pour Zoho Mail, varie selon provider)

---

## ✅ Checklist Complète

### Déploiement Railway

- [x] Code pushé sur GitHub
- [ ] Railway a redéployé automatiquement
- [ ] Logs de démarrage corrects
- [ ] Service Beat actif
- [ ] Test manuel OK (optionnel)
- [ ] Briefing reçu demain 8h

### Email Pro

- [ ] Domaine acheté
- [ ] Email configuré (Zoho/Google)
- [ ] DNS configuré
- [ ] Test envoi/réception OK
- [ ] Variable Railway ajoutée
- [ ] Messages bot mis à jour

---

**Dernière mise à jour** : 2026-02-08 18:05 CET  
**Status** : ✅ Prêt pour déploiement Railway  
**Prochaine action** : Vérifier Railway + attendre 8h demain  
