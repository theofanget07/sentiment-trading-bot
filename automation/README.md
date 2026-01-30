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

## Scheduling

Le workflow est dans `.github/workflows/daily_crypto_digest.yml`.

- Planifié à **08:05 UTC** tous les jours.
- Tu peux aussi lancer manuellement via l'onglet GitHub Actions (workflow_dispatch).

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
python automation/daily_crypto_digest.py
```
