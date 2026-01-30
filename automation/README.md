# Automation (Digest quotidien)

Ce dossier ajoute une **automatisation simple** pour poster un digest quotidien sur Telegram, sans dépendre de Celery/Railway worker/beat.  
Le digest est exécuté via **GitHub Actions** (cron) et poste dans ton chat ou ton channel Telegram. 

## Configuration (GitHub)

Dans ton repo GitHub → **Settings → Secrets and variables → Actions → New repository secret**.

Secrets requis :
- `PERPLEXITY_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID` (ex: `@ton_channel` ou un id numérique)

Secrets optionnels :
- `PERPLEXITY_MODEL` (par défaut: `sonar-pro`)
- `DIGEST_MAX_ITEMS` (par défaut: `10`, min 3, max 25)
- `DIGEST_MIN_CONFIDENCE` (par défaut: `0`, min 0, max 100) - filtre les articles avec confiance < seuil
- `DIGEST_SOURCES` (par défaut: `coindesk,cointelegraph`) - sources RSS séparées par virgule

## Scheduling

Le workflow est dans `.github/workflows/daily_crypto_digest.yml`.

- Planifié à **08:05 UTC** tous les jours.
- Tu peux aussi lancer manuellement via l'onglet GitHub Actions (workflow_dispatch).

## Nouveautés V3

### One-liner summaries
Chaque article affiche maintenant un résumé en une phrase (le "one_liner" généré par Perplexity lors de l'analyse).

Format :
```
- [Titre de l'article](url) (85%)
  → Résumé en une phrase de l'impact marché
```

### Conclusion marché AI-generated
Une conclusion globale (2-3 phrases) est générée automatiquement par Perplexity en analysant tous les articles du jour.  
Elle identifie les thèmes dominants, les drivers clés, et donne un insight actionnable.

Exemple :
```
💡 Conclusion: Le marché reste prudent (-20%) avec 5 signaux baissiers dominés par le scepticisme réglementaire (Visa/Mastercard, SEC). Les innovations techniques (Lido, Ripple) maintiennent un optimisme de fond mais insuffisant pour renverser la tendance. Position recommandée: HOLD en attendant clarification macro.
```

### Liens cliquables (depuis V2)
Chaque article dans le digest est un lien Markdown cliquable vers l'article source.

### Filtre de confiance (depuis V2)
Utilise `DIGEST_MIN_CONFIDENCE` pour ne garder que les analyses avec une confiance >= seuil.  
Exemple : `DIGEST_MIN_CONFIDENCE=75` → ne publie que les articles avec confiance ≥ 75%.

### Sources configurables (depuis V2)
Active/désactive les sources RSS via `DIGEST_SOURCES`.  
Sources disponibles : `coindesk`, `cointelegraph`.  
Exemple : `DIGEST_SOURCES=coindesk` (uniquement CoinDesk).

## Test local (Mac)

```bash
python automation/daily_crypto_digest.py
```

Exports d'env vars à copier-coller :

```bash
export PERPLEXITY_API_KEY="..."
export TELEGRAM_BOT_TOKEN="..."
export TELEGRAM_CHAT_ID="@ton_channel"
export PERPLEXITY_MODEL="sonar-pro"
export DIGEST_MAX_ITEMS="10"
export DIGEST_MIN_CONFIDENCE="0"
export DIGEST_SOURCES="coindesk,cointelegraph"
python automation/daily_crypto_digest.py
```

## Coûts API

V3 ajoute un appel Perplexity supplémentaire pour générer la conclusion marché (1 appel/jour).  
Coût quotidien estimé : ~€0.03-0.10 (10 analyses + 1 conclusion).
