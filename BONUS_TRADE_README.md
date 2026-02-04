# 🏆 BONUS TRADE OF THE DAY - Feature Documentation

## Overview

**Bonus Trade of the Day** est une fonctionnalité premium qui analyse TOUS les cryptos supportés quotidiennement et identifie la meilleure opportunité de trading du jour pour tous les utilisateurs.

### Caractéristiques Clés

- 🤖 **Analyse IA Complète**: Utilise Perplexity AI pour analyser les 15 cryptos supportés
- 🎯 **Scoring Intelligent**: Évalue momentum, sentiment, technicals, et actualités
- 🔔 **Notification Matinale**: Envoi automatique à 8h00 CET à tous les utilisateurs
- 📈 **Recommandation Actionnable**: Inclut prix d'entrée, targets, stop-loss, et raisonnement détaillé
- 🏆 **Top Pick du Jour**: Seule la meilleure opportunité est partagée

---

## Architecture Technique

### Fichiers Créés

```
backend/
├── tasks/
│   └── bonus_trade.py          # Tâche Celery principale
└── services/
    └── notification_service.py  # Méthode send_bonus_trade() ajoutée
```

### Flux de Fonctionnement

1. **8:00 AM CET** - Tâche Celery `send_bonus_trade_of_day()` s'exécute
2. **Récupération des prix** - Fetch les prix actuels pour les 15 cryptos via CoinGecko
3. **Analyse AI** - Pour chaque crypto:
   - Appel à Perplexity API avec prompt détaillé
   - Extraction de: BUY/SELL/HOLD, confidence, risk level, reasoning
   - Calcul du score d'opportunité (0-100)
4. **Sélection du Winner** - Crypto avec le score le plus élevé
5. **Notification Globale** - Envoi à TOUS les utilisateurs du bot

---

## Configuration Celery Beat

Ajouter cette tâche dans `backend/celery_config.py`:

```python
from celery.schedules import crontab

beat_schedule = {
    # ... autres tâches existantes
    
    'bonus-trade-of-day': {
        'task': 'backend.tasks.bonus_trade.send_bonus_trade_of_day',
        'schedule': crontab(hour=8, minute=0),  # 8:00 AM CET
        'options': {
            'expires': 3600,  # Expire après 1h si pas exécutée
        }
    },
}
```

---

## Format du Message Telegram

Exemple de notification envoyée:

```
🏆 BONUS TRADE OF THE DAY
━━━━━━━━━━━━━━━━━━

📈 BTC - BUY

💰 Entry Price: $95,000.00
🎯 Target: $105,000.00 (+10.5%)
🛑 Stop Loss: $92,000.00 (-3.2%)

📊 Confidence: 85%
🟡 Risk Level: MEDIUM

📝 AI Analysis:
Bitcoin is showing strong bullish momentum:
• ETF inflows hitting all-time highs
• Breaking through key resistance at $94,500
• Positive funding rates indicating market confidence

Technical Setup: Clean breakout with volume confirmation.
RSI shows room to run before overbought.

━━━━━━━━━━━━━━━━━━
💡 This is the top opportunity identified by AI 
from analyzing ALL supported cryptos.
⚠️ Always do your own research and manage risk carefully.
```

---

## Tests Manuels

### Test 1: Test Unitaire de la Tâche

```bash
# Depuis le dossier du projet
celery -A backend.celery_app call backend.tasks.bonus_trade.test_bonus_trade --args='[YOUR_CHAT_ID]'
```

### Test 2: Exécution Manuelle Complète

```bash
celery -A backend.celery_app call backend.tasks.bonus_trade.send_bonus_trade_of_day
```

### Test 3: Via Python REPL

```python
from backend.tasks.bonus_trade import send_bonus_trade_of_day

result = send_bonus_trade_of_day()
print(result)
# Expected: {'status': 'completed', 'bonus_trade': {...}, 'users_notified': X}
```

---

## Critères de Sélection

### Scoring Algorithm

Le score d'opportunité (0-100) est calculé selon:

```python
score = confidence * risk_multiplier

Risk Multipliers:
- LOW: 1.1x (favorisé)
- MEDIUM: 1.0x (neutre)
- HIGH: 0.9x (pénalisé)
```

### Filtres d'Exclusion

- ❌ Recommandations HOLD ou SELL (seulement BUY)
- ❌ Confidence < 60%
- ❌ Erreurs d'analyse ou prix manquants

---

## Monitoring & Logs

### Logs Clés à Surveiller

```
[BONUS TRADE] Starting Bonus Trade of the Day analysis...
[BONUS TRADE] Fetching prices for 15 cryptos...
[BONUS TRADE] Got prices for 15/15 cryptos
[BONUS TRADE] Analyzing trading opportunities with Perplexity AI...
[BONUS TRADE] BTC: Score=93.5, Action=BUY, Confidence=85%
[BONUS TRADE] ETH: Score=77.0, Action=BUY, Confidence=70%
...
[BONUS TRADE] 🏆 WINNER: BTC with score 93.5
[BONUS TRADE] Sending to 150 users...
[BONUS TRADE] Task completed: {'status': 'completed', 'users_notified': 150}
```

### Métriques à Tracker

- **Taux de succès**: users_notified / total_users
- **Cryptos analysés**: Devrait être 15/15
- **Temps d'exécution**: < 2 minutes
- **Taux d'erreur API Perplexity**: < 5%

---

## Déploiement sur Railway

### Étape 1: Merger la Branche

```bash
git checkout main
git merge feature/bonus-trade-of-day
git push origin main
```

### Étape 2: Vérifier les Variables d'Environnement

Sur Railway, assurer que ces variables existent:

```
PERPLEXITY_API_KEY=pplx-...
TELEGRAM_BOT_TOKEN=...
REDIS_URL=redis://...
```

### Étape 3: Redémarrer les Services

1. Railway détecte le push et redéploie automatiquement
2. Vérifier que Celery Beat est actif: `railway logs -s celery-beat`
3. Confirmer le schedule: logs doivent montrer `beat schedule registered`

### Étape 4: Validation

Attendre 8h00 CET le lendemain OU exécuter un test manuel:

```bash
railway run celery -A backend.celery_app call backend.tasks.bonus_trade.test_bonus_trade --args='[YOUR_CHAT_ID]'
```

---

## Business Value

### Valeur Ajoutée Utilisateur

- 🎯 **Gain de Temps**: Plus besoin d'analyser 15 cryptos manuellement
- 🤖 **Expertise AI**: Accès à une analyse professionnelle quotidienne
- 📩 **Convenience**: Livré directement chaque matin
- 📈 **Actionnable**: Recommandations claires avec entry/target/SL

### Monétisation Potentielle

**Option 1: Feature Premium**
- Gratuit: Daily Insights basiques
- Premium (€9/mois): + Bonus Trade of the Day
- Conversion estimée: 20% → 30 users @ €9 = **€270/mois**

**Option 2: Tiered Pricing**
- Basic (Gratuit): Portfolio tracking
- Pro (€9/mois): + AI Recommendations
- Elite (€19/mois): + Bonus Trade + Priority support
- Conversion estimée: 15% @ €19 = **€285/mois**

---

## Roadmap & Améliorations Futures

### Phase 1 (Current) ✅
- [x] Analyse des 15 cryptos supportés
- [x] Sélection du top 1 trade
- [x] Notification matinale 8h CET

### Phase 2 (À venir)
- [ ] **Historique des Trades**: Tracker performance des recommandations
- [ ] **Win Rate Dashboard**: Afficher taux de succès via `/stats`
- [ ] **Customisation**: Laisser utilisateurs choisir l'heure de notification
- [ ] **Feedback Loop**: Boutons "Trade pris" / "Trade ignoré" pour améliorer l'algo

### Phase 3 (Advanced)
- [ ] **Multi-Timeframes**: Short-term (1-3j) + Long-term (1-4 sem)
- [ ] **Risk Profiling**: Adapter sélection selon profil utilisateur (conservateur/agressif)
- [ ] **Top 3 Trades**: Envoyer 3 opportunités au lieu d'une seule
- [ ] **Live Alerts**: Si trade devient invalide (stop loss hit), notifier en temps réel

---

## Support & Troubleshooting

### Problème: Aucune notification reçue

**Causes possibles:**
1. Celery Beat pas actif → Vérifier `railway logs -s celery-beat`
2. Schedule mal configuré → Vérifier `beat_schedule` dans celery_config.py
3. Erreur API Perplexity → Vérifier logs: `[BONUS TRADE] Error analyzing`

**Solution:**
```bash
# Redémarrer Celery Beat
railway restart -s celery-beat

# Test manuel
railway run celery -A backend.celery_app call backend.tasks.bonus_trade.send_bonus_trade_of_day
```

### Problème: Score toujours faible

**Cause:** Marché bearish ou volatilité élevée

**Solution:** Ajuster les seuils dans `bonus_trade.py`:
```python
# Ligne 55
if action != "BUY" or confidence < 50:  # Descendre de 60 à 50
    return None
```

### Problème: Temps d'exécution > 3 minutes

**Cause:** Trop d'appels API séquentiels

**Solution:** Implémenter batch processing ou async calls:
```python
import asyncio

# Analyser cryptos en parallèle au lieu de séquentiellement
opportunities = await asyncio.gather(*[
    analyze_crypto_async(symbol) for symbol in valid_cryptos
])
```

---

## Conclusion

**Bonus Trade of the Day** est maintenant prêt à être déployé!

### Prochaines Étapes

1. ✅ Merger `feature/bonus-trade-of-day` vers `main`
2. 🚀 Déployer sur Railway
3. 📊 Monitorer la première exécution demain à 8h00 CET
4. 👥 Collecter feedback utilisateurs
5. 💰 Évaluer monétisation (premium feature)

---

**Questions? Besoin d'aide?**

Références:
- [Perplexity API Docs](https://docs.perplexity.ai)
- [Celery Beat Docs](https://docs.celeryproject.org/en/stable/userguide/periodic-tasks.html)
- [Phase 1.3 Roadmap](./docs/PHASE_1_3_ADVANCED_FEATURES.md)

_Dernière mise à jour: 4 février 2026_
