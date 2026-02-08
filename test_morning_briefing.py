#!/usr/bin/env python3
"""Test script for Morning Briefing task.

Run this to manually trigger the morning briefing and verify it works.

Usage:
    python test_morning_briefing.py
"""

import os
import sys
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Run Morning Briefing test."""
    logger.info("="*70)
    logger.info("🧪 Testing Morning Briefing Task")
    logger.info("="*70)
    
    # Check environment
    logger.info("🔍 Checking environment variables...")
    required_vars = [
        "REDIS_URL",
        "PERPLEXITY_API_KEY",
        "TELEGRAM_BOT_TOKEN",
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"❌ Missing environment variables: {missing_vars}")
        logger.error("Please set them before running this test.")
        return 1
    
    logger.info("✅ All environment variables present")
    
    # Test Redis connection
    logger.info("🔍 Testing Redis connection...")
    try:
        from backend.redis_storage import RedisStorage
        storage = RedisStorage()
        user_ids = storage.get_all_user_ids()
        logger.info(f"✅ Redis connected: {len(user_ids)} users found")
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        return 1
    
    # Test CoinGecko API
    logger.info("🔍 Testing CoinGecko API...")
    try:
        from backend.crypto_prices import get_crypto_price
        btc_price = get_crypto_price("BTC")
        if btc_price:
            logger.info(f"✅ CoinGecko API working: BTC = ${btc_price:,.2f}")
        else:
            logger.warning("⚠️ CoinGecko API returned None (may be rate limited)")
    except Exception as e:
        logger.error(f"❌ CoinGecko API failed: {e}")
    
    # Test Perplexity API
    logger.info("🔍 Testing Perplexity API...")
    try:
        from backend.services.perplexity_client import get_perplexity_client
        perplexity = get_perplexity_client()
        logger.info("✅ Perplexity client initialized")
    except Exception as e:
        logger.error(f"❌ Perplexity client failed: {e}")
        return 1
    
    # Test Telegram bot
    logger.info("🔍 Testing Telegram bot...")
    try:
        from backend.services.notification_service import get_notification_service
        notification_service = get_notification_service()
        logger.info("✅ Telegram bot initialized")
    except Exception as e:
        logger.error(f"❌ Telegram bot failed: {e}")
        return 1
    
    # Run Morning Briefing task
    logger.info("="*70)
    logger.info("🚀 Running Morning Briefing task...")
    logger.info("="*70)
    
    try:
        from backend.tasks.morning_briefing import send_morning_briefing
        result = send_morning_briefing()
        
        logger.info("="*70)
        logger.info("✅ Morning Briefing task completed!")
        logger.info(f"Result: {result}")
        logger.info("="*70)
        
        if result.get("status") == "completed":
            logger.info("✅ SUCCESS: Morning Briefing sent successfully")
            return 0
        else:
            logger.error("❌ FAILED: Morning Briefing task failed")
            return 1
    
    except Exception as e:
        logger.error("="*70)
        logger.error(f"❌ Morning Briefing task crashed: {e}")
        logger.error("="*70)
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
