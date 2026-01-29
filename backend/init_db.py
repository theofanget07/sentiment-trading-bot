#!/usr/bin/env python
"""Initialize database tables on Railway."""
import os
import sys
from dotenv import load_dotenv
import logging

load_dotenv()

from database import engine, Base
from models import User, Article, Analysis, DailyDigest

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def init_database():
    """
    Create all database tables.
    Safe to run multiple times (won't recreate existing tables).
    """
    logger.info("🚀 Starting database initialization...")
    
    try:
        # Check database connection
        logger.info(f"📍 Connecting to database...")
        logger.info(f"   Database URL: {os.getenv('DATABASE_URL', 'Not set')[:50]}...")
        
        # Create all tables
        logger.info("📦 Creating tables...")
        Base.metadata.create_all(bind=engine)
        
        logger.info("✅ Database initialization complete!")
        logger.info("")
        logger.info("Tables created:")
        logger.info("  - users")
        logger.info("  - articles")
        logger.info("  - analyses")
        logger.info("  - daily_digests")
        logger.info("")
        logger.info("🎉 Database ready for production!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
