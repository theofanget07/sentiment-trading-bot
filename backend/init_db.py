#!/usr/bin/env python3
"""
Database initialization script.
Creates all tables and optionally migrates data from JSON files.
"""
import sys
import os
import json
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from backend.database import init_db, test_connection, engine
    from backend.models import User, PortfolioPosition, Transaction, Recommendation
    from backend.database import SessionLocal
except ImportError:
    from database import init_db, test_connection, engine
    from models import User, PortfolioPosition, Transaction, Recommendation
    from database import SessionLocal

def create_tables():
    """Create all database tables."""
    logger.info("🔨 Starting database initialization...")
    
    # Test connection first
    if not test_connection():
        logger.error("❌ Database connection failed. Check DATABASE_URL environment variable.")
        sys.exit(1)
    
    # Create tables
    try:
        init_db()
        logger.info("✅ All tables created successfully!")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create tables: {e}")
        return False

def migrate_json_data():
    """
    Migrate existing JSON data to PostgreSQL.
    Optional: only run if JSON files exist.
    """
    logger.info("📦 Checking for JSON data to migrate...")
    
    data_dir = Path(__file__).parent / 'user_data'
    portfolios_file = data_dir / 'portfolios.json'
    transactions_file = data_dir / 'transactions.json'
    
    if not portfolios_file.exists():
        logger.info("ℹ️ No JSON data found. Skipping migration.")
        return True
    
    logger.info(f"📥 Found JSON data in {data_dir}")
    logger.info("🔄 Starting migration...")
    
    db = SessionLocal()
    try:
        # Load JSON data
        with open(portfolios_file, 'r') as f:
            portfolios = json.load(f)
        
        with open(transactions_file, 'r') as f:
            transactions = json.load(f)
        
        migrated_users = 0
        migrated_positions = 0
        migrated_transactions = 0
        
        # Migrate portfolios
        for user_id_str, portfolio_data in portfolios.items():
            telegram_id = int(user_id_str)
            
            # Check if user already exists
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            if user:
                logger.info(f"⏭️ User {telegram_id} already exists, skipping...")
                continue
            
            # Create user
            user = User(
                telegram_id=telegram_id,
                username=portfolio_data.get('username', f'user_{telegram_id}')
            )
            db.add(user)
            db.flush()  # Get user.id
            migrated_users += 1
            
            # Migrate positions
            for symbol, pos_data in portfolio_data.get('positions', {}).items():
                position = PortfolioPosition(
                    user_id=user.id,
                    symbol=symbol,
                    quantity=pos_data['quantity'],
                    avg_price=pos_data['avg_price']
                )
                db.add(position)
                migrated_positions += 1
            
            logger.info(f"✅ Migrated user {telegram_id} with {len(portfolio_data.get('positions', {}))} positions")
        
        # Migrate transactions
        for user_id_str, tx_list in transactions.items():
            telegram_id = int(user_id_str)
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            
            if not user:
                logger.warning(f"⚠️ User {telegram_id} not found for transactions, skipping...")
                continue
            
            for tx_data in tx_list:
                transaction = Transaction(
                    user_id=user.id,
                    symbol=tx_data['symbol'],
                    action=tx_data['action'],
                    quantity=tx_data['quantity'],
                    price=tx_data['price'],
                    total_usd=tx_data['total_usd'],
                    source=tx_data.get('source', 'manual'),
                    sentiment=tx_data.get('sentiment'),
                    confidence=tx_data.get('confidence')
                )
                db.add(transaction)
                migrated_transactions += 1
        
        # Commit all changes
        db.commit()
        
        logger.info("🎉 Migration complete!")
        logger.info(f"   ✅ {migrated_users} users migrated")
        logger.info(f"   ✅ {migrated_positions} positions migrated")
        logger.info(f"   ✅ {migrated_transactions} transactions migrated")
        
        # Backup JSON files
        backup_dir = data_dir / 'backup'
        backup_dir.mkdir(exist_ok=True)
        
        import shutil
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        for file in [portfolios_file, transactions_file]:
            if file.exists():
                backup_file = backup_dir / f"{file.stem}_{timestamp}.json"
                shutil.copy(file, backup_file)
                logger.info(f"💾 Backed up {file.name} to {backup_file}")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        db.rollback()
        return False
    
    finally:
        db.close()

def verify_tables():
    """Verify that all tables exist."""
    logger.info("🔍 Verifying database tables...")
    
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    expected_tables = ['users', 'portfolio_positions', 'transactions', 'recommendations']
    
    for table in expected_tables:
        if table in tables:
            logger.info(f"   ✅ Table '{table}' exists")
        else:
            logger.error(f"   ❌ Table '{table}' missing!")
            return False
    
    logger.info("✅ All tables verified successfully!")
    return True

def main():
    """Main initialization flow."""
    logger.info("🚀 Database Initialization Script")
    logger.info("="*50)
    
    # Step 1: Create tables
    if not create_tables():
        logger.error("❌ Failed to create tables. Exiting.")
        sys.exit(1)
    
    # Step 2: Verify tables
    if not verify_tables():
        logger.error("❌ Table verification failed. Exiting.")
        sys.exit(1)
    
    # Step 3: Migrate JSON data (optional)
    migrate_json_data()
    
    logger.info("="*50)
    logger.info("✅ Database initialization complete!")
    logger.info("🛠️ Your PostgreSQL database is ready to use.")

if __name__ == "__main__":
    main()
