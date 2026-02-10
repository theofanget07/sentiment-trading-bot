#!/usr/bin/env python3
"""
Run All Migrations

Executes all necessary migrations in the correct order:
1. Migrate existing users to users:all set
2. List all users
"""

import os
import sys
import logging

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    logger.info("🚀 Starting all migrations...\n")
    
    # Import and run migration
    logger.info("Step 1: Migrating users to users:all set...")
    from backend.scripts.migrate_users_to_all_set import migrate_users
    migrate_users()
    
    logger.info("\n" + "="*80 + "\n")
    
    # List all users
    logger.info("Step 2: Listing all users...")
    from backend.scripts.list_all_users import list_users
    list_users()
    
    logger.info("✅ All migrations complete!\n")
    logger.info("📌 Next steps:")
    logger.info("1. Find your user ID in the list above")
    logger.info("2. Set yourself as Premium with:")
    logger.info("   python backend/scripts/set_user_premium.py <YOUR_USER_ID>\n")

if __name__ == "__main__":
    main()
