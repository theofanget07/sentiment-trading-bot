#!/usr/bin/env python3
"""
List All Users Script

Shows all users in the database with their profiles and tier status.
"""

import os
import sys
import json
import logging

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from backend.redis_storage import get_redis_client
from backend.tier_manager import tier_manager

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

def list_users():
    """
    List all users with their profiles and tier status.
    """
    try:
        redis_client = get_redis_client()
        
        # Find all user profile keys
        pattern = "user:*:profile"
        keys = redis_client.keys(pattern)
        
        logger.info(f"\n📋 Found {len(keys)} users:\n")
        logger.info("="*80)
        
        for i, key in enumerate(keys, 1):
            # Extract user_id
            parts = key.split(':')
            if len(parts) >= 2:
                user_id = int(parts[1])
                
                # Get profile
                profile_data = redis_client.get(key)
                if profile_data:
                    profile = json.loads(profile_data)
                    username = profile.get('username', 'Unknown')
                else:
                    username = 'Unknown'
                
                # Get tier status
                is_premium = tier_manager.is_premium(user_id)
                tier = "💎 PREMIUM" if is_premium else "🆓 FREE"
                
                # Check Stripe subscription
                stripe_sub = redis_client.get(f"subscription:telegram:{user_id}")
                stripe_status = "🟢 Stripe Active" if stripe_sub else ""
                
                print(f"{i}. User ID: {user_id}")
                print(f"   Username: @{username}")
                print(f"   Tier: {tier} {stripe_status}")
                print("-" * 80)
        
        logger.info("\n✅ Done!\n")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    list_users()
