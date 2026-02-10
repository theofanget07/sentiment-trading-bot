# Admin Dashboard Setup

## 🎯 Dashboard déployé

Le dashboard admin est maintenant disponible à l'adresse :

```
https://sentiment-trading-bot-production.up.railway.app/admin/users?token=YOUR_ADMIN_TOKEN
```

## 🔐 Configuration

### 1. Définir le token admin

Dans Railway, ajoute la variable d'environnement :

```
ADMIN_TOKEN=ton_token_secret_secure
```

⚠️ **IMPORTANT** : Utilise un token fort et unique (minimum 32 caractères aléatoires)

Exemple de génération :
```bash
openssl rand -hex 32
```

### 2. Redémarrer l'application

Après avoir ajouté `ADMIN_TOKEN`, Railway redémarrera automatiquement.

### 3. Accéder au dashboard

URL d'accès :
```
https://sentiment-trading-bot-production.up.railway.app/admin/users?token=TON_ADMIN_TOKEN
```

## ✨ Fonctionnalités

Le dashboard permet de :

- ✅ Voir tous les users (total, premium, free)
- ✅ Voir le MRR (Monthly Recurring Revenue)
- ✅ Rechercher un user par ID ou username
- ✅ Basculer un user en Premium/Free manuellement
- ✅ Voir quels users ont un abonnement Stripe actif

## 📊 Interface

Le dashboard affiche :

### Stats Cards
- **Total Users** : Nombre total d'utilisateurs
- **💎 Premium** : Nombre d'utilisateurs Premium  
- **🆓 Free** : Nombre d'utilisateurs Free
- **💰 MRR** : Revenu mensuel récurrent (Premium × €9)

### Table Users
Pour chaque user :
- **User ID** : Telegram user ID
- **Username** : @username ou nom
- **Status** : Badge Premium (💎) ou Free (🆓)
- **Stripe Sub** : Indicateur d'abonnement Stripe actif
- **Action** : Bouton pour basculer Premium/Free

## 🔒 Sécurité

- ✅ Token obligatoire dans l'URL
- ✅ Pas d'accès sans token valide
- ✅ Token stocké en variable d'environnement

## 🛠️ Gestion des Users

### Passer un user en Premium manuellement

1. Accède au dashboard
2. Trouve le user (recherche par ID ou username)
3. Clique sur "↑ Set PREMIUM"
4. Confirme

→ Le user aura accès à toutes les fonctionnalités Premium dans le bot

### Révoquer le Premium

1. Accède au dashboard
2. Trouve le user Premium
3. Clique sur "↓ Set FREE"
4. Confirme

→ Le user repasse en Free tier avec les limitations

## ⚠️ Important

**Le dashboard modifie UNIQUEMENT le statut dans Redis (accès aux features du bot).**

**Pour gérer les paiements Stripe** (remboursements, annulations, invoices) :
→ [Stripe Dashboard](https://dashboard.stripe.com/subscriptions)

## 🎨 Design

- Interface dark mode inspirée de Twitter/X
- Responsive (fonctionne sur mobile)
- Recherche en temps réel
- Tri automatique (Premium en premier)

## 📝 Notes

- Les users Premium manuels n'ont PAS d'abonnement Stripe
- L'indicateur vert (🟢) = Abonnement Stripe actif
- L'indicateur gris (⚫) = Premium manuel (pas de Stripe)
- Le MRR affiché = Premium count × €9 (peu importe la source)

---

✅ **Dashboard opérationnel et sécurisé !**
