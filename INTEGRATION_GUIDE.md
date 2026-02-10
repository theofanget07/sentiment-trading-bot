# 🎯 Guide d'intégration du Dashboard Admin

## Étapes à suivre (2 minutes)

### ÉTAPE 1 : Modifier bot_webhook.py sur GitHub

#### 1.1 Ouvrir le fichier

Allez sur : [backend/bot_webhook.py](https://github.com/theofanget07/sentiment-trading-bot/blob/main/backend/bot_webhook.py)

Cliquez sur le crayon ✏️ "Edit this file" en haut à droite

#### 1.2 Première modification (ligne ~120)

Cherchez cette ligne :
```python
    analytics_router = None
```

Juste APRÈS cette ligne, ajoutez ce bloc :

```python

# Admin Dashboard Router (Phase 1.5)
try:
    from backend.routes.admin import router as admin_router
    ADMIN_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ Admin dashboard router not available")
    ADMIN_AVAILABLE = False
    admin_router = None
```

#### 1.3 Deuxième modification (ligne ~150)

Cherchez cette ligne :
```python
    logger.warning("⚠️ Analytics router NOT registered")
```

Juste APRÈS cette ligne, ajoutez ce bloc :

```python

# Include Admin Dashboard Router (Phase 1.5)
if ADMIN_AVAILABLE and admin_router:
    app.include_router(admin_router)
    logger.info("✅ Admin dashboard router registered at /admin/users")
else:
    logger.warning("⚠️ Admin dashboard router NOT registered")
```

#### 1.4 Sauvegarder

- Cliquez sur **"Commit changes"** en haut à droite
- Message : `feat: Integrate admin dashboard router`
- Cliquez sur **"Commit changes"** (bouton vert)

✅ Railway va automatiquement redémarrer l'application après le commit !

---

### ÉTAPE 2 : Configurer le token admin dans Railway

#### 2.1 Générer un token sécurisé

Ouvre un terminal sur ton Mac et tape :

```bash
openssl rand -hex 32
```

Tu vas obtenir quelque chose comme :
```
a3f89b2e4c1d6f7e9a0b3c5d7e8f1a2b4c6d8e0f2a4b6c8d0e2f4a6b8c0d2e4f
```

**Copie ce token** (tu en auras besoin) !

#### 2.2 Ajouter la variable d'environnement dans Railway

1. Va sur [Railway Dashboard](https://railway.app/dashboard)
2. Ouvre ton projet `sentiment-trading-bot`
3. Clique sur **Variables**
4. Clique sur **New Variable**
5. Nom : `ADMIN_TOKEN`
6. Valeur : _Colle le token généré à l'étape 2.1_
7. Clique sur **Add**

✅ Railway redémarre automatiquement avec le nouveau token !

---

### ÉTAPE 3 : Vérifier que ça fonctionne

#### 3.1 Attendre le redémarrage (1-2 minutes)

Dans Railway, attends que le statut passe de `Building` → `Deploying` → `Active`

#### 3.2 Vérifier les logs

Dans Railway, clique sur **View Logs** et cherche cette ligne :

```
✅ Admin dashboard router registered at /admin/users
```

Si tu vois cette ligne, **c'est bon !** 🎉

#### 3.3 Accéder au dashboard

URL du dashboard :
```
https://sentiment-trading-bot-production.up.railway.app/admin/users?token=TON_ADMIN_TOKEN
```

**Remplace `TON_ADMIN_TOKEN`** par le token que tu as créé à l'étape 2.1

Exemple complet :
```
https://sentiment-trading-bot-production.up.railway.app/admin/users?token=a3f89b2e4c1d6f7e9a0b3c5d7e8f1a2b4c6d8e0f2a4b6c8d0e2f4a6b8c0d2e4f
```

---

## 🎨 Interface du Dashboard

### Stats Cards

- **Total Users** : Nombre total d'utilisateurs
- **💎 Premium** : Nombre d'utilisateurs Premium  
- **🆓 Free** : Nombre d'utilisateurs Free
- **💰 MRR** : Revenu mensuel récurrent (Premium × €9)

### Tableau des Users

Pour chaque user :
- **User ID** : Telegram user ID
- **Username** : @username ou nom
- **Status** : Badge Premium (💎) ou Free (🆓)
- **Stripe Sub** : 🟢 = Abonnement Stripe actif | ⚫ = Premium manuel
- **Action** : Bouton pour basculer Premium/Free

### Fonctionnalités

- ✅ Rechercher un user par ID ou username
- ✅ Basculer un user en Premium/Free manuellement
- ✅ Voir le MRR en temps réel
- ✅ Interface dark mode responsive

---

## 🔐 Utilisation du Token Admin

### Qu'est-ce que le token ?

Le token admin est une **clé secrète** qui protège l'accès au dashboard.

Sans le token, impossible d'accéder au dashboard → **sécurisé !**

### Comment l'utiliser ?

Le token doit être ajouté dans l'URL comme paramètre `token` :

```
https://votre-app.com/admin/users?token=VOTRE_TOKEN_ADMIN
```

### Où le stocker ?

✅ **À faire** :
- Stocker dans un gestionnaire de mots de passe (1Password, Bitwarden, etc.)
- Stocker dans un fichier `.env` local (non commité sur Git)
- Le garder confidentiel

❌ **À NE PAS faire** :
- Le commiter sur GitHub
- Le partager par email/Slack
- L'écrire en clair dans un document public

### Comment changer le token ?

1. Génère un nouveau token : `openssl rand -hex 32`
2. Dans Railway → Variables → Édite `ADMIN_TOKEN`
3. Remplace l'ancienne valeur par la nouvelle
4. Railway redémarre automatiquement
5. Utilise le nouveau token dans l'URL

---

## 🛡️ Sécurité

### Vérification du token

Le dashboard vérifie le token à chaque requête :
- ✅ Token valide → Accès accordé
- ❌ Token invalide/manquant → Erreur 401 (Unauthorized)

### Protection

- 🔒 Pas d'accès sans token
- 🔒 Token stocké en variable d'environnement (pas dans le code)
- 🔒 HTTPS obligatoire (Railway gère automatiquement)

---

## 🚨 Troubleshooting

### Erreur 401 Unauthorized

**Cause** : Token invalide ou manquant

**Solution** :
1. Vérifie que tu as bien ajouté `?token=TON_TOKEN` à l'URL
2. Vérifie que le token dans l'URL correspond à celui dans Railway
3. Vérifie qu'il n'y a pas d'espaces avant/après le token

### Dashboard ne s'affiche pas

**Cause** : Router admin pas enregistré

**Solution** :
1. Vérifie les logs Railway : cherche `✅ Admin dashboard router registered`
2. Si absent, vérifie que tu as bien fait les modifications dans `bot_webhook.py`
3. Redémarre l'application dans Railway

### "Database offline"

**Cause** : Redis n'est pas connecté

**Solution** :
1. Vérifie que `REDIS_URL` est bien configurée dans Railway
2. Vérifie les logs Redis
3. Redémarre l'application

---

## ✅ Checklist de vérification

- [ ] Modifications dans `bot_webhook.py` (2 blocs ajoutés)
- [ ] Token admin généré avec `openssl rand -hex 32`
- [ ] Variable `ADMIN_TOKEN` ajoutée dans Railway
- [ ] Railway redémarré et `Active`
- [ ] Log `✅ Admin dashboard router registered` visible
- [ ] Dashboard accessible avec l'URL + token
- [ ] Stats affichées correctement
- [ ] Recherche fonctionnelle
- [ ] Boutons Premium/Free fonctionnels

---

## 📚 Documentation complète

Pour plus de détails, consulte :
- [ADMIN_SETUP.md](./ADMIN_SETUP.md) : Configuration détaillée
- [backend/routes/admin.py](./backend/routes/admin.py) : Code source du dashboard

---

🎉 **C'est tout ! Le dashboard admin est maintenant opérationnel.**

Si tu as des questions, ping-moi ! 🚀
