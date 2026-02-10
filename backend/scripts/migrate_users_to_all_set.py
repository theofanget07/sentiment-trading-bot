#!/usr/bin/env python3
"""
Migration Script: Add all existing users to users:all set

This script finds all existing user profiles and adds them to the global
users:all set so they appear in the admin dashboard.

Run this once after deploying the redis_storage.py fix.
"""

import os
import sys
import logging

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from backend.redis_storage import get_redis_client

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def migrate_users():
    """
    Find all existing user profiles and add them to users:all set.
    """
    try:
        redis_client = get_redis_client()
        
        # Find all user profile keys
        pattern = "user:*:profile"
        keys = redis_client.keys(pattern)
        
        logger.info(f"🔍 Found {len(keys)} user profiles")
        
        migrated_count = 0
        
        for key in keys:
            # Extract user_id from key: user:123:profile -> 123
            parts = key.split(':')
            if len(parts) >= 2:
                user_id = parts[1]
                
                # Add to users:all set
                redis_client.sadd("users:all", user_id)
                migrated_count += 1
                logger.info(f"✅ Migrated user {user_id}")
        
        logger.info(f"✅ Migration complete! {migrated_count} users added to users:all set")
        
        # Verify
        total_users = redis_client.scard("users:all")
        logger.info(f"📋 Total users in users:all: {total_users}")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    logger.info("🚀 Starting user migration...")
    migrate_users()
    logger.info("🎉 Migration finished!")
