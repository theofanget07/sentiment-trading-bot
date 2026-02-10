#!/usr/bin/env python3
"""
Set User Premium Script

Sets a specific user as Premium tier.

Usage:
    python set_user_premium.py <user_id>

Example:
    python set_user_premium.py 123456789
"""

import os
import sys
import logging

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from backend.tier_manager import tier_manager
from backend.redis_storage import get_redis_client

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

def set_premium(user_id: int):
    """
    Set a user as Premium tier.
    """
    try:
        redis_client = get_redis_client()
        
        # Check if user exists
        profile = redis_client.get(f"user:{user_id}:profile")
        if not profile:
            logger.error(f"❌ User {user_id} not found!")
            logger.info("\nRun 'python list_all_users.py' to see all users.")
            sys.exit(1)
        
        # Get current tier
        current_tier = "premium" if tier_manager.is_premium(user_id) else "free"
        
        if current_tier == "premium":
            logger.info(f"⚠️ User {user_id} is already Premium!")
        else:
            # Set to Premium
            tier_manager.set_tier(user_id, 'premium')
            logger.info(f"✅ User {user_id} is now PREMIUM! 💎")
        
        # Verify
        is_premium = tier_manager.is_premium(user_id)
        logger.info(f"\n📋 Current status: {'PREMIUM 💎' if is_premium else 'FREE 🆓'}")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python set_user_premium.py <user_id>")
        print("\nExample: python set_user_premium.py 123456789")
        print("\nTo find your user ID, run: python list_all_users.py")
        sys.exit(1)
    
    try:
        user_id = int(sys.argv[1])
    except ValueError:
        logger.error("❌ Invalid user ID! Must be a number.")
        sys.exit(1)
    
    set_premium(user_id)
