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

## Nouveautés V2

### Liens cliquables
Chaque article dans le digest est maintenant un lien Markdown cliquable vers l'article source.

### Filtre de confiance
Utilise `DIGEST_MIN_CONFIDENCE` pour ne garder que les analyses avec une confiance >= seuil.  
Exemple : `DIGEST_MIN_CONFIDENCE=75` → ne publie que les articles avec confiance ≥ 75%.

### Sources configurables
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
