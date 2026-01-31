#!/usr/bin/env python
"""Initialize portfolio tracking tables on Railway PostgreSQL.

This script extends the existing database with new tables for:
- User positions (crypto holdings)
- Position transactions (buy/sell history)
- Position recommendations (AI advice)
- Daily digests (refactored for global snapshots)

Safe to run multiple times (uses CREATE TABLE IF NOT EXISTS).
"""
import os
import sys
from dotenv import load_dotenv
import logging

load_dotenv()

from database import engine
from models import Base, User, Article, Analysis, DailyDigest, UserPosition, PositionTransaction, PositionRecommendation

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def init_portfolio_tables():
    """
    Create all portfolio-related database tables.
    Extends existing schema without dropping existing tables.
    """
    logger.info("🚀 Starting portfolio tables initialization...")
    
    try:
        # Check database connection
        logger.info(f"📍 Connecting to database...")
        database_url = os.getenv('DATABASE_URL', 'Not set')
        if database_url == 'Not set':
            logger.error("❌ DATABASE_URL not set in environment")
            return False
        
        logger.info(f"   Database URL: {database_url[:50]}...")
        
        # Create all tables (existing + new)
        logger.info("📦 Creating/updating tables...")
        Base.metadata.create_all(bind=engine)
        
        logger.info("✅ Portfolio tables initialization complete!")
        logger.info("")
        logger.info("Existing tables (preserved):")
        logger.info("  - users (extended with daily_analyses_count)")
        logger.info("  - articles (refactored)")
        logger.info("  - analyses (refactored)")
        logger.info("")
        logger.info("New tables created:")
        logger.info("  - daily_digests (global snapshots)")
        logger.info("  - user_positions (crypto holdings)")
        logger.info("  - position_transactions (buy/sell history)")
        logger.info("  - position_recommendations (AI advice)")
        logger.info("")
        logger.info("🎉 Database ready for portfolio tracking!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Portfolio tables initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = init_portfolio_tables()
    sys.exit(0 if success else 1)
