# 📊 Phase 1.5 Analytics Integration Guide

## 🎯 Overview

Ce guide explique comment intégrer le système d'analytics dans `bot_webhook.py` pour tracker automatiquement toutes les actions utilisateurs.

---

## 📦 Fichiers créés

### Core Analytics
- `backend/analytics/__init__.py` - Module structure
- `backend/analytics/tracker.py` - Event tracking
- `backend/analytics/aggregator.py` - Métriques business
- `backend/analytics/reporter.py` - Rapports automatiques
- `backend/analytics/alerts.py` - Système d'alertes

### API & Dashboard
- `backend/routes/analytics.py` - Routes FastAPI
- `backend/analytics_integration.py` - Helper functions
- `backend/dashboard/index.html` - Dashboard frontend
- `backend/dashboard/styles.css` - Styles
- `backend/dashboard/dashboard.js` - JavaScript

---

## ⚙️ Intégration dans bot_webhook.py

### 🔹 Étape 1 : Ajouter les imports

Après les imports existants (ligne ~60), ajouter :

```python
# Analytics System (Phase 1.5)
try:
    from backend.analytics_integration import (
        init_analytics,
        track_command,
        track_registration,
        track_conversion
    )
    from backend.routes.analytics import router as analytics_router
    ANALYTICS_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ Analytics system not available")
    ANALYTICS_AVAILABLE = False
    def init_analytics(): pass
    def track_command(*args, **kwargs): pass
    def track_registration(*args, **kwargs): pass
    def track_conversion(*args, **kwargs): pass
    analytics_router = None
```

---

### 🔹 Étape 2 : Enregistrer les routes analytics

Après `app.include_router(stripe_webhook_router)` (ligne ~120), ajouter :

```python
# Include Analytics Router
if ANALYTICS_AVAILABLE and analytics_router:
    app.include_router(analytics_router)
    logger.info("✅ Analytics router registered at /analytics")
else:
    logger.warning("⚠️ Analytics router NOT registered")
```

---

### 🔹 Étape 3 : Servir le dashboard HTML

Après les routes `/terms` et `/privacy` (ligne ~1050), ajouter :

```python
@app.get("/dashboard", response_class=HTMLResponse)
async def analytics_dashboard():
    """Serve Analytics Dashboard."""
    try:
        dashboard_dir = os.path.join(os.path.dirname(__file__), 'dashboard')
        dashboard_path = os.path.join(dashboard_dir, 'index.html')
        with open(dashboard_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Analytics Dashboard</h1><p>Dashboard not found</p>"

@app.get("/dashboard/styles.css")
async def dashboard_styles():
    """Serve dashboard CSS."""
    try:
        dashboard_dir = os.path.join(os.path.dirname(__file__), 'dashboard')
        css_path = os.path.join(dashboard_dir, 'styles.css')
        with open(css_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return Response(content=content, media_type="text/css")
    except FileNotFoundError:
        return Response(content="/* CSS not found */", media_type="text/css")

@app.get("/dashboard/dashboard.js")
async def dashboard_script():
    """Serve dashboard JavaScript."""
    try:
        dashboard_dir = os.path.join(os.path.dirname(__file__), 'dashboard')
        js_path = os.path.join(dashboard_dir, 'dashboard.js')
        with open(js_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return Response(content=content, media_type="application/javascript")
    except FileNotFoundError:
        return Response(content="// JS not found", media_type="application/javascript")
```

---

### 🔹 Étape 4 : Initialiser analytics au startup

Dans `async def startup()` (ligne ~1070), après la connexion Redis, ajouter :

```python
    # Initialize Analytics System (Phase 1.5)
    if ANALYTICS_AVAILABLE:
        analytics_init = init_analytics()
        if analytics_init:
            logger.info("✅ Analytics system initialized")
        else:
            logger.warning("⚠️ Analytics system failed to initialize")
    else:
        logger.warning("⚠️ Analytics system not available")
```

---

### 🔹 Étape 5 : Tracker les commandes

#### 5a. Tracker /start (registrations)

Dans `async def start()` (ligne ~130), à la fin de la fonction, ajouter :

```python
    # Track registration
    if ANALYTICS_AVAILABLE:
        track_registration(user.id, user.username)
```

#### 5b. Tracker les commandes principales

Pour chaque handler de commande, ajouter le tracking :

**Exemple pour `/analyze` :**

```python
@check_rate_limit
async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # [... code existant ...]
    
    try:
        # [... logique de la commande ...]
        
        # Track success
        if ANALYTICS_AVAILABLE:
            track_command('analyze', user_id, success=True)
        
    except Exception as e:
        # Track error
        if ANALYTICS_AVAILABLE:
            track_command('analyze', user_id, success=False, error=str(e))
        raise
```

**Liste des commandes à tracker :**

1. `/analyze` - `track_command('analyze', user_id, success)`
2. `/portfolio` - `track_command('portfolio', user_id, success)`
3. `/add` - `track_command('add', user_id, success)`
4. `/remove` - `track_command('remove', user_id, success)`
5. `/sell` - `track_command('sell', user_id, success)`
6. `/setalert` - `track_command('setalert', user_id, success)`
7. `/recommend` - `track_command('recommend', user_id, success)`
8. `/subscribe` - `track_command('subscribe', user_id, success)`

#### 5c. Tracker les conversions (Stripe webhook)

Dans `backend/routes/stripe_webhook.py`, dans le handler `checkout.session.completed`, ajouter :

```python
# Track conversion
from backend.analytics_integration import track_conversion

# Après avoir activé le premium
track_conversion(
    user_id=user_id,
    subscription_id=subscription_id,
    amount=9.0
)
```

---

## 📝 Version simplifiée (sans modifier bot_webhook.py)

Si tu veux tester sans modifier bot_webhook.py, tu peux :

1. **Tester les routes API directement :**

```bash
# Test overview
curl https://sentiment-trading-bot-production.up.railway.app/analytics/overview

# Test users
curl https://sentiment-trading-bot-production.up.railway.app/analytics/users?days=7

# Test revenue
curl https://sentiment-trading-bot-production.up.railway.app/analytics/revenue
```

2. **Accéder au dashboard :**

Une fois déployé : `https://sentiment-trading-bot-production.up.railway.app/dashboard`

---

## 🛠️ Configuration

### Variables d'environnement (optionnel)

Aucune variable supplémentaire nécessaire ! Le système utilise la connexion Redis existante.

---

## 📊 Endpoints API disponibles

| Endpoint | Description |
|----------|-------------|
| `GET /analytics/overview` | Vue d'ensemble complète |
| `GET /analytics/users` | Métriques utilisateurs (DAU, WAU, MAU) |
| `GET /analytics/revenue` | Métriques revenue (MRR, ARPU, conversion) |
| `GET /analytics/engagement` | Engagement (commandes, erreurs) |
| `GET /analytics/costs` | Coûts API et infrastructure |
| `GET /analytics/alerts` | Alertes actives |
| `GET /analytics/report/daily` | Rapport quotidien |
| `GET /analytics/report/weekly` | Rapport hebdomadaire |
| `GET /dashboard` | Dashboard HTML |

---

## 🚨 Alertes automatiques

Le système surveille automatiquement :

- **Error rate > 5%** → Alerte HIGH
- **Conversion rate < 5%** → Alerte MEDIUM
- **API costs > budget** → Alerte HIGH
- **Zero activity 2h+** → Alerte LOW

Alertes accessibles via : `GET /analytics/alerts`

---

## 👨‍💻 Testing Local

### 1. Tester le tracker

```python
from analytics.tracker import AnalyticsTracker
from redis_storage import get_redis_client

redis_client = get_redis_client()
tracker = AnalyticsTracker(redis_client)

# Track test event
tracker.track_command('test', 123456, success=True)
print("✅ Event tracked!")
```

### 2. Tester l'aggregator

```python
from analytics.aggregator import MetricsAggregator
from redis_storage import get_redis_client

redis_client = get_redis_client()
aggregator = MetricsAggregator(redis_client)

# Get metrics
overview = aggregator.get_overview()
print(overview)
```

### 3. Tester les routes API (en local)

```bash
# Lancer le serveur
python bot_webhook.py

# Tester (dans un autre terminal)
curl http://localhost:8080/analytics/overview
curl http://localhost:8080/dashboard
```

---

## ✅ Checklist de déploiement

- [ ] Tous les fichiers analytics créés
- [ ] Routes analytics enregistrées dans bot_webhook.py
- [ ] Dashboard accessible via `/dashboard`
- [ ] Tracking actif dans les commandes principales
- [ ] Conversions trackées dans Stripe webhook
- [ ] Test API : `GET /analytics/overview` fonctionne
- [ ] Dashboard affiche les métriques

---

## 💛 Notes importantes

1. **Les métriques sont basées sur Redis** : Si Redis est vidé, les métriques repartent à zéro
2. **TTL des données** : 30 jours pour les événements, 31 jours pour les compteurs
3. **Performance** : Le tracking est non-bloquant, n'impacte pas les commandes
4. **Privacy** : Seuls les user_id Telegram sont stockés (pas de données personnelles)

---

## 🎓 Prochaines étapes (Phase 2)

- [ ] Rapports automatiques par email
- [ ] Intégration Telegram pour recevoir les alertes
- [ ] Export CSV des métriques
- [ ] A/B testing framework
- [ ] Funnel analysis (registration → premium)

---

## 💎 Résultat final

Une fois tout intégré, tu auras :

✅ **Dashboard en temps réel** : `https://sentiment-trading-bot-production.up.railway.app/dashboard`
✅ **API analytics complète** : 8 endpoints disponibles
✅ **Tracking automatique** : Toutes les commandes trackées
✅ **Alertes intelligentes** : Notifications si problèmes
✅ **Rapports quotidiens/hebdomadaires** : Générés automatiquement

**Tu auras une vue claire sur :**
- Nombre d'utilisateurs (total, actifs, premium)
- Revenue (MRR, ARPU, conversion rate)
- Engagement (commandes, features populaires)
- Coûts (API, infrastructure)
- Santé du système (error rate, uptime)

---

## 📞 Support

Si besoin d'aide pour l'intégration, je suis là ! 🚀
