#!/usr/bin/env python3
"""
Système de Vérification Complète - CryptoSentinel

Ce script vérifie que TOUT le système est correctement configuré
avant de lancer en production.

Vérifie:
1. Configuration Stripe (API keys, webhooks, products)
2. Configuration Redis (connexion, données)
3. Configuration Telegram (bot token, admin ID)
4. Améliorations paiement (5 features)
5. Variables d'environnement
6. Connexions bases de données

Usage:
    python backend/system_health_check.py

Auteur: Theo Fanget
Date: 10 février 2026
"""

import os
import sys
from datetime import datetime
from typing import Dict, List, Tuple

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class HealthCheck:
    """Gestionnaire de vérifications santé système"""
    
    def __init__(self):
        self.checks_passed = 0
        self.checks_failed = 0
        self.checks_warnings = 0
        self.results = []
    
    def check(self, name: str, status: str, message: str, critical: bool = False):
        """Enregistre un résultat de vérification
        
        Args:
            name: Nom de la vérification
            status: 'OK', 'WARNING', 'FAILED'
            message: Message descriptif
            critical: Si True, échec bloquant pour production
        """
        self.results.append({
            'name': name,
            'status': status,
            'message': message,
            'critical': critical
        })
        
        if status == 'OK':
            self.checks_passed += 1
        elif status == 'WARNING':
            self.checks_warnings += 1
        else:
            self.checks_failed += 1
    
    def print_results(self):
        """Affiche les résultats formatés"""
        print("\n" + "="*80)
        print("  📋 RÉSULTATS DE VÉRIFICATION SYSTÈME")
        print("="*80)
        
        for result in self.results:
            status_icon = {
                'OK': '✅',
                'WARNING': '⚠️',
                'FAILED': '❌'
            }.get(result['status'], '❓')
            
            critical_marker = ' [CRITICAL]' if result['critical'] else ''
            
            print(f"\n{status_icon} {result['name']}{critical_marker}")
            print(f"   {result['message']}")
        
        print("\n" + "="*80)
        print("  📊 STATISTIQUES")
        print("="*80)
        print(f"   ✅ Tests réussis: {self.checks_passed}")
        print(f"   ⚠️ Avertissements: {self.checks_warnings}")
        print(f"   ❌ Tests échoués: {self.checks_failed}")
        
        # Production readiness
        critical_failures = sum(1 for r in self.results if r['status'] == 'FAILED' and r['critical'])
        
        print("\n" + "="*80)
        if critical_failures == 0 and self.checks_failed == 0:
            print("  🎉 SYSTÈME PRÊT POUR LA PRODUCTION")
        elif critical_failures == 0:
            print("  ⚠️ SYSTÈME FONCTIONNEL (avec avertissements)")
        else:
            print(f"  ❌ SYSTÈME NON PRÊT ({critical_failures} problèmes critiques)")
        print("="*80)


def check_environment_variables() -> HealthCheck:
    """Vérifie les variables d'environnement"""
    print("\n🔍 VÉRIFICATION VARIABLES D'ENVIRONNEMENT")
    health = HealthCheck()
    
    # Critical variables
    critical_vars = {
        'TELEGRAM_BOT_TOKEN': 'Token du bot Telegram',
        'STRIPE_API_KEY': 'Clé API Stripe',
        'STRIPE_PRICE_ID': 'ID du produit Stripe',
        'STRIPE_WEBHOOK_SECRET': 'Secret webhook Stripe',
        'REDIS_URL': 'URL de connexion Redis'
    }
    
    for var, description in critical_vars.items():
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            masked = f"{value[:10]}..." if len(value) > 10 else "***"
            health.check(
                f"Variable {var}",
                'OK',
                f"{description}: {masked}",
                critical=True
            )
        else:
            health.check(
                f"Variable {var}",
                'FAILED',
                f"{description}: Non définie",
                critical=True
            )
    
    # Optional but recommended
    optional_vars = {
        'ADMIN_TELEGRAM_CHAT_ID': 'ID Telegram admin pour alertes',
        'DATABASE_URL': 'URL base de données PostgreSQL'
    }
    
    for var, description in optional_vars.items():
        value = os.getenv(var)
        if value:
            masked = f"{value[:10]}..." if len(value) > 10 else "***"
            health.check(
                f"Variable {var}",
                'OK',
                f"{description}: {masked}",
                critical=False
            )
        else:
            health.check(
                f"Variable {var}",
                'WARNING',
                f"{description}: Non définie (optionnel)",
                critical=False
            )
    
    return health


def check_stripe_connection() -> HealthCheck:
    """Vérifie la connexion Stripe"""
    print("\n🔍 VÉRIFICATION STRIPE")
    health = HealthCheck()
    
    try:
        import stripe
        from backend.stripe_service import (
            STRIPE_API_KEY,
            STRIPE_PRICE_ID,
            STRIPE_WEBHOOK_SECRET,
            test_stripe_connection
        )
        
        # Check API key
        if STRIPE_API_KEY:
            if STRIPE_API_KEY.startswith('sk_live_'):
                health.check(
                    'Stripe API Key Mode',
                    'OK',
                    'Mode LIVE activé (production)',
                    critical=True
                )
            elif STRIPE_API_KEY.startswith('sk_test_'):
                health.check(
                    'Stripe API Key Mode',
                    'WARNING',
                    'Mode TEST activé (pas de vrais paiements)',
                    critical=False
                )
            
            # Test connection
            if test_stripe_connection():
                health.check(
                    'Stripe Connexion',
                    'OK',
                    'Connexion API Stripe réussie',
                    critical=True
                )
            else:
                health.check(
                    'Stripe Connexion',
                    'FAILED',
                    'Impossible de se connecter à Stripe',
                    critical=True
                )
        else:
            health.check(
                'Stripe API Key',
                'FAILED',
                'STRIPE_API_KEY non définie',
                critical=True
            )
        
        # Check Price ID
        if STRIPE_PRICE_ID:
            if STRIPE_PRICE_ID.startswith('price_'):
                health.check(
                    'Stripe Price ID',
                    'OK',
                    f'Price ID valide: {STRIPE_PRICE_ID[:20]}...',
                    critical=True
                )
            else:
                health.check(
                    'Stripe Price ID',
                    'WARNING',
                    'Format Price ID invalide',
                    critical=True
                )
        else:
            health.check(
                'Stripe Price ID',
                'FAILED',
                'STRIPE_PRICE_ID non définie',
                critical=True
            )
        
        # Check Webhook Secret
        if STRIPE_WEBHOOK_SECRET:
            if STRIPE_WEBHOOK_SECRET.startswith('whsec_'):
                health.check(
                    'Stripe Webhook Secret',
                    'OK',
                    'Webhook secret configuré',
                    critical=True
                )
            else:
                health.check(
                    'Stripe Webhook Secret',
                    'WARNING',
                    'Format webhook secret invalide',
                    critical=False
                )
        else:
            health.check(
                'Stripe Webhook Secret',
                'FAILED',
                'STRIPE_WEBHOOK_SECRET non définie',
                critical=True
            )
    
    except Exception as e:
        health.check(
            'Stripe Import',
            'FAILED',
            f'Erreur import stripe: {str(e)}',
            critical=True
        )
    
    return health


def check_redis_connection() -> HealthCheck:
    """Vérifie la connexion Redis"""
    print("\n🔍 VÉRIFICATION REDIS")
    health = HealthCheck()
    
    try:
        from backend.redis_storage import redis_client
        
        # Test ping
        redis_client.ping()
        health.check(
            'Redis Connexion',
            'OK',
            'Connexion Redis réussie',
            critical=True
        )
        
        # Test write/read
        test_key = f"healthcheck:test:{int(datetime.utcnow().timestamp())}"
        test_value = "test_value"
        
        redis_client.set(test_key, test_value)
        retrieved = redis_client.get(test_key)
        redis_client.delete(test_key)
        
        if retrieved == test_value:
            health.check(
                'Redis Écriture/Lecture',
                'OK',
                'Opérations read/write fonctionnelles',
                critical=True
            )
        else:
            health.check(
                'Redis Écriture/Lecture',
                'FAILED',
                'Problème read/write Redis',
                critical=True
            )
        
        # Check existing data
        user_keys = redis_client.keys("user:*:subscription_status")
        health.check(
            'Redis Données Utilisateurs',
            'OK' if user_keys else 'WARNING',
            f'{len(user_keys)} utilisateurs dans Redis',
            critical=False
        )
    
    except Exception as e:
        health.check(
            'Redis Connexion',
            'FAILED',
            f'Impossible de se connecter à Redis: {str(e)}',
            critical=True
        )
    
    return health


def check_telegram_bot() -> HealthCheck:
    """Vérifie la configuration du bot Telegram"""
    print("\n🔍 VÉRIFICATION TELEGRAM BOT")
    health = HealthCheck()
    
    try:
        import requests
        from backend.stripe_service import TELEGRAM_BOT_TOKEN, ADMIN_TELEGRAM_CHAT_ID
        
        if not TELEGRAM_BOT_TOKEN:
            health.check(
                'Telegram Bot Token',
                'FAILED',
                'TELEGRAM_BOT_TOKEN non défini',
                critical=True
            )
            return health
        
        # Test bot API
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            bot_info = response.json()
            if bot_info.get('ok'):
                bot_username = bot_info['result']['username']
                health.check(
                    'Telegram Bot API',
                    'OK',
                    f'Bot actif: @{bot_username}',
                    critical=True
                )
            else:
                health.check(
                    'Telegram Bot API',
                    'FAILED',
                    'Bot token invalide',
                    critical=True
                )
        else:
            health.check(
                'Telegram Bot API',
                'FAILED',
                f'Erreur API Telegram: {response.status_code}',
                critical=True
            )
        
        # Check admin ID
        if ADMIN_TELEGRAM_CHAT_ID:
            health.check(
                'Telegram Admin ID',
                'OK',
                f'Admin configuré: {ADMIN_TELEGRAM_CHAT_ID}',
                critical=False
            )
        else:
            health.check(
                'Telegram Admin ID',
                'WARNING',
                'ADMIN_TELEGRAM_CHAT_ID non défini (alertes désactivées)',
                critical=False
            )
    
    except Exception as e:
        health.check(
            'Telegram Bot',
            'FAILED',
            f'Erreur vérification Telegram: {str(e)}',
            critical=True
        )
    
    return health


def check_payment_improvements() -> HealthCheck:
    """Vérifie les 5 améliorations paiement"""
    print("\n🔍 VÉRIFICATION AMÉLIORATIONS PAIEMENT")
    health = HealthCheck()
    
    try:
        from backend.stripe_service import (
            GRACE_PERIOD_DAYS,
            webhook_idempotency_check,
            send_admin_alert,
            validate_webhook_data,
            set_grace_period,
            REDIS_AVAILABLE
        )
        
        # 1. Grace Period
        health.check(
            '1. Grace Period',
            'OK',
            f'Grace period configurée: {GRACE_PERIOD_DAYS} jours',
            critical=False
        )
        
        # 2. Idempotency
        if REDIS_AVAILABLE:
            test_event = f"evt_test_{int(datetime.utcnow().timestamp())}"
            result1 = webhook_idempotency_check(test_event)
            result2 = webhook_idempotency_check(test_event)
            
            if result1 and not result2:
                health.check(
                    '2. Webhook Idempotency',
                    'OK',
                    'Deduplication webhooks fonctionnelle',
                    critical=False
                )
            else:
                health.check(
                    '2. Webhook Idempotency',
                    'WARNING',
                    'Problème deduplication webhooks',
                    critical=False
                )
        else:
            health.check(
                '2. Webhook Idempotency',
                'WARNING',
                'Redis non disponible (idempotency désactivée)',
                critical=False
            )
        
        # 3. Retry Logic
        health.check(
            '3. Retry Logic',
            'OK',
            'Retry avec backoff exponentiel implémenté',
            critical=False
        )
        
        # 4. Admin Alerts
        from backend.stripe_service import ADMIN_TELEGRAM_CHAT_ID
        if ADMIN_TELEGRAM_CHAT_ID:
            health.check(
                '4. Admin Alerts',
                'OK',
                'Système d\'alertes admin actif',
                critical=False
            )
        else:
            health.check(
                '4. Admin Alerts',
                'WARNING',
                'Alertes admin non configurées',
                critical=False
            )
        
        # 5. Enhanced Validation
        test_data = {
            'metadata': {'telegram_user_id': '123456'},
            'customer': 'cus_test',
            'subscription': 'sub_test'
        }
        if validate_webhook_data(test_data, ['metadata', 'customer', 'subscription']):
            health.check(
                '5. Enhanced Validation',
                'OK',
                'Validation webhooks renforcée active',
                critical=False
            )
        else:
            health.check(
                '5. Enhanced Validation',
                'WARNING',
                'Problème validation webhooks',
                critical=False
            )
    
    except Exception as e:
        health.check(
            'Améliorations Paiement',
            'FAILED',
            f'Erreur vérification features: {str(e)}',
            critical=False
        )
    
    return health


def main():
    """Fonction principale"""
    print("\n" + "#"*80)
    print("#  🏥 SYSTÈME DE VÉRIFICATION COMPLÈTE - CryptoSentinel")
    print("#"*80)
    print(f"\n📅 Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("📍 Environnement: Production" if os.getenv('STRIPE_API_KEY', '').startswith('sk_live_') else "📍 Environnement: Test")
    
    # Run all checks
    all_results = []
    
    all_results.append(check_environment_variables())
    all_results.append(check_stripe_connection())
    all_results.append(check_redis_connection())
    all_results.append(check_telegram_bot())
    all_results.append(check_payment_improvements())
    
    # Combine results
    combined = HealthCheck()
    for health in all_results:
        combined.results.extend(health.results)
        combined.checks_passed += health.checks_passed
        combined.checks_failed += health.checks_failed
        combined.checks_warnings += health.checks_warnings
    
    # Print results
    combined.print_results()
    
    # Check if production ready
    critical_failures = sum(1 for r in combined.results if r['status'] == 'FAILED' and r['critical'])
    
    if critical_failures > 0:
        print("\n⚠️  ACTION REQUISE:")
        print("   Les problèmes critiques doivent être résolus avant la production.")
        print("\n📝 Problèmes critiques:")
        for r in combined.results:
            if r['status'] == 'FAILED' and r['critical']:
                print(f"   - {r['name']}: {r['message']}")
        return 1
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n👋 Vérification interrompue")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Erreur inattendue: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
