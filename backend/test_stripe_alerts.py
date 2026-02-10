#!/usr/bin/env python3
"""
Script de Test des Alertes Stripe

Ce script teste toutes les alertes du système de paiement:
1. Alerte utilisateur (payment failed)
2. Alertes admin (INFO, WARNING, ERROR, CRITICAL)

Usage:
    python backend/test_stripe_alerts.py

Pré-requis:
    - TELEGRAM_BOT_TOKEN configuré
    - ADMIN_TELEGRAM_CHAT_ID configuré
    - Redis disponible (optionnel)

Auteur: Theo Fanget
Date: 10 février 2026
"""

import os
import sys
import time
from datetime import datetime, timedelta

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

try:
    from backend.stripe_service import (
        send_admin_alert, 
        notify_user_payment_failed, 
        TELEGRAM_BOT_TOKEN, 
        ADMIN_TELEGRAM_CHAT_ID,
        webhook_idempotency_check,
        set_grace_period,
        check_grace_period_expired,
        get_subscription_status,
        REDIS_AVAILABLE
    )
    import requests
except ImportError as e:
    print(f"❌ Erreur d'import: {e}")
    print("\nAssurez-vous d'être dans le bon répertoire et que les dépendances sont installées.")
    sys.exit(1)


def print_section(title):
    """Affiche une section formatée"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)


def check_config():
    """Vérifie la configuration nécessaire"""
    print_section("📋 VÉRIFICATION CONFIGURATION")
    
    config_ok = True
    
    # Check TELEGRAM_BOT_TOKEN
    if TELEGRAM_BOT_TOKEN:
        print(f"✅ TELEGRAM_BOT_TOKEN: {TELEGRAM_BOT_TOKEN[:10]}...")
    else:
        print("❌ TELEGRAM_BOT_TOKEN: Non configuré")
        config_ok = False
    
    # Check ADMIN_TELEGRAM_CHAT_ID
    if ADMIN_TELEGRAM_CHAT_ID:
        print(f"✅ ADMIN_TELEGRAM_CHAT_ID: {ADMIN_TELEGRAM_CHAT_ID}")
    else:
        print("❌ ADMIN_TELEGRAM_CHAT_ID: Non configuré")
        print("\n💡 Pour obtenir ton Telegram User ID:")
        print("   1. Ouvre Telegram")
        print("   2. Cherche @userinfobot")
        print("   3. Clique Start")
        print("   4. Copie ton User ID")
        print("   5. Ajoute-le à Railway: railway variables set ADMIN_TELEGRAM_CHAT_ID=<ton_id>")
        config_ok = False
    
    # Check Redis
    if REDIS_AVAILABLE:
        print("✅ Redis: Disponible")
    else:
        print("⚠️ Redis: Non disponible (certains tests seront limités)")
    
    return config_ok


def test_admin_alerts():
    """Teste toutes les alertes admin"""
    print_section("🚨 TEST ALERTES ADMIN")
    
    tests = [
        ("INFO", "ℹ️", "Test d'alerte INFO - Tout fonctionne normalement"),
        ("WARNING", "⚠️", "Test d'alerte WARNING - Attention requise"),
        ("ERROR", "❌", "Test d'alerte ERROR - Erreur détectée"),
        ("CRITICAL", "🚨", "Test d'alerte CRITICAL - Action immédiate requise")
    ]
    
    for level, emoji, message in tests:
        print(f"\n{emoji} Envoi alerte {level}...")
        send_admin_alert(message, level)
        print(f"   ✅ Alerte {level} envoyée")
        time.sleep(2)  # Wait 2s between alerts
    
    print("\n✅ Toutes les alertes admin ont été envoyées!")
    print("\n📱 Vérifie ton Telegram - tu devrais avoir reçu 4 messages")


def test_user_payment_failed_notification():
    """Teste la notification utilisateur pour paiement échoué"""
    print_section("📧 TEST NOTIFICATION UTILISATEUR (Payment Failed)")
    
    if not ADMIN_TELEGRAM_CHAT_ID:
        print("❌ Impossible de tester sans ADMIN_TELEGRAM_CHAT_ID")
        return
    
    print(f"\n📤 Envoi notification à l'admin (simulation user)...")
    print(f"   User ID simulé: {ADMIN_TELEGRAM_CHAT_ID}")
    
    # Set grace period for testing (if Redis available)
    if REDIS_AVAILABLE:
        try:
            from backend.redis_storage import redis_client
            grace_end = datetime.utcnow() + timedelta(days=3)
            redis_client.set(
                f"user:{ADMIN_TELEGRAM_CHAT_ID}:grace_period_end",
                grace_end.isoformat()
            )
            print("   ✅ Grace period définie dans Redis")
        except Exception as e:
            print(f"   ⚠️ Impossible de définir grace period: {e}")
    else:
        print("   ⚠️ Redis non disponible - grace period non définie")
    
    # Send notification using REAL function
    print("\n   📨 Appel de notify_user_payment_failed()...")
    try:
        notify_user_payment_failed(int(ADMIN_TELEGRAM_CHAT_ID))
        print("   ✅ Fonction appelée avec succès!")
    except Exception as e:
        print(f"   ❌ Erreur lors de l'appel: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✅ Test terminé!")
    print("\n📱 Vérifie ton Telegram - tu devrais avoir reçu le message de payment failed")
    print("   Le message devrait avoir des retours à la ligne propres (pas de \\n)")


def test_webhook_idempotency():
    """Teste le système d'idempotence des webhooks"""
    print_section("🔒 TEST IDEMPOTENCE WEBHOOKS")
    
    if not REDIS_AVAILABLE:
        print("\n❌ Redis non disponible - test impossible")
        return
    
    try:
        from backend.redis_storage import redis_client
        
        test_event_id = f"evt_test_{int(time.time())}"
        
        print(f"\n🧪 Test avec event ID: {test_event_id}")
        
        # First call - should return True (new event)
        print("\n1️⃣ Premier appel (nouveau webhook)...")
        result1 = webhook_idempotency_check(test_event_id)
        if result1:
            print("   ✅ Webhook accepté (nouveau)")
        else:
            print("   ❌ Webhook rejeté (ERREUR - devrait être accepté)")
        
        # Second call - should return False (duplicate)
        print("\n2️⃣ Deuxième appel (webhook dupliqué)...")
        result2 = webhook_idempotency_check(test_event_id)
        if not result2:
            print("   ✅ Webhook rejeté (dupliqué) - CORRECT!")
        else:
            print("   ❌ Webhook accepté (ERREUR - devrait être rejeté)")
        
        # Check Redis
        print("\n3️⃣ Vérification Redis...")
        key = f"stripe:webhook:processed:{test_event_id}"
        exists = redis_client.exists(key)
        if exists:
            ttl = redis_client.ttl(key)
            print(f"   ✅ Clé existe dans Redis (TTL: {ttl}s = {ttl//86400} jours)")
        else:
            print("   ❌ Clé n'existe pas dans Redis (ERREUR)")
        
        print("\n✅ Test idempotence terminé!")
        
    except Exception as e:
        print(f"\n❌ Erreur lors du test: {e}")
        import traceback
        traceback.print_exc()


def test_grace_period():
    """Teste le système de grace period"""
    print_section("⏳ TEST GRACE PERIOD")
    
    if not REDIS_AVAILABLE:
        print("\n❌ Redis non disponible - test impossible")
        return
    
    try:
        from backend.redis_storage import redis_client
        
        test_user_id = int(ADMIN_TELEGRAM_CHAT_ID) if ADMIN_TELEGRAM_CHAT_ID else 999999999
        test_invoice_id = f"in_test_{int(time.time())}"
        
        print(f"\n🧪 Test avec user ID: {test_user_id}")
        print(f"   Invoice ID: {test_invoice_id}")
        
        # Set grace period
        print("\n1️⃣ Définition grace period (3 jours)...")
        result = set_grace_period(test_user_id, test_invoice_id)
        if result:
            print("   ✅ Grace period définie")
        else:
            print("   ❌ Échec définition grace period")
        
        # Check grace period
        print("\n2️⃣ Vérification grace period...")
        grace_end_str = redis_client.get(f"user:{test_user_id}:grace_period_end")
        if grace_end_str:
            grace_end = datetime.fromisoformat(grace_end_str)
            days_left = (grace_end - datetime.utcnow()).days
            print(f"   ✅ Grace period active jusqu'à: {grace_end.strftime('%Y-%m-%d %H:%M')}")
            print(f"   ⏰ Jours restants: {days_left}")
        else:
            print("   ❌ Grace period non trouvée dans Redis")
        
        # Check subscription status
        print("\n3️⃣ Vérification statut subscription...")
        status = get_subscription_status(test_user_id)
        print(f"   📊 Statut actuel: {status}")
        if status == 'premium':
            print("   ✅ User reste Premium pendant grace period")
        else:
            print(f"   ⚠️ Statut inattendu: {status}")
        
        # Check if expired (should be False)
        print("\n4️⃣ Vérification expiration...")
        expired = check_grace_period_expired(test_user_id)
        if not expired:
            print("   ✅ Grace period pas encore expirée - CORRECT")
        else:
            print("   ❌ Grace period marquée comme expirée (ERREUR)")
        
        # Cleanup
        print("\n5️⃣ Nettoyage...")
        redis_client.delete(f"user:{test_user_id}:grace_period_end")
        redis_client.delete(f"user:{test_user_id}:grace_period_invoice")
        redis_client.delete(f"user:{test_user_id}:subscription_status")
        print("   ✅ Test nettoyé")
        
        print("\n✅ Test grace period terminé!")
        
    except Exception as e:
        print(f"\n❌ Erreur lors du test: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Fonction principale"""
    print("\n" + "#"*60)
    print("#  🧪 SCRIPT DE TEST - ALERTES STRIPE")
    print("#"*60)
    
    # Check configuration
    if not check_config():
        print("\n⚠️ Configuration incomplète - certains tests seront limités")
        response = input("\nContinuer quand même? (y/n): ")
        if response.lower() != 'y':
            print("\n👋 Test annulé")
            return
    
    print("\n" + "="*60)
    print("  🚀 LANCEMENT DES TESTS")
    print("="*60)
    
    # Menu
    print("\nQue veux-tu tester?")
    print("  1. Alertes Admin (INFO, WARNING, ERROR, CRITICAL)")
    print("  2. Notification Utilisateur (Payment Failed)")
    print("  3. Idempotence Webhooks")
    print("  4. Grace Period")
    print("  5. Tout tester")
    print("  0. Quitter")
    
    choice = input("\nTon choix (1-5): ").strip()
    
    if choice == "1":
        test_admin_alerts()
    elif choice == "2":
        test_user_payment_failed_notification()
    elif choice == "3":
        test_webhook_idempotency()
    elif choice == "4":
        test_grace_period()
    elif choice == "5":
        test_admin_alerts()
        time.sleep(3)
        test_user_payment_failed_notification()
        time.sleep(3)
        test_webhook_idempotency()
        time.sleep(3)
        test_grace_period()
    elif choice == "0":
        print("\n👋 Au revoir!")
        return
    else:
        print("\n❌ Choix invalide")
        return
    
    print("\n" + "="*60)
    print("  ✅ TESTS TERMINÉS")
    print("="*60)
    print("\n📱 Vérifie ton Telegram pour les messages reçus")
    print("\n💡 Notes importantes:")
    print("   - Les messages utilisent HTML pour le formatage")
    print("   - Les retours à la ligne doivent être propres (pas de \\n visibles)")
    print("   - Le texte en gras utilise <b>texte</b>")
    print("\n💡 Pour relancer: python backend/test_stripe_alerts.py")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Test interrompu par l'utilisateur")
    except Exception as e:
        print(f"\n\n❌ Erreur inattendue: {e}")
        import traceback
        traceback.print_exc()
