#!/usr/bin/env python3
"""
Database initialization script for Railway deployment.
Run this ONCE via Railway CLI to create PostgreSQL tables.

Usage:
  railway run python scripts/init_database.py
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.database import init_db, test_connection

def main():
    print("=" * 60)
    print("PostgreSQL Database Initialization Script")
    print("=" * 60)
    print()
    
    # Test connection first
    print("🔌 Testing database connection...")
    if not test_connection():
        print("❌ ERROR: Cannot connect to PostgreSQL!")
        print()
        print("Make sure:")
        print("  1. PostgreSQL service is running on Railway")
        print("  2. DATABASE_URL environment variable is set")
        print("  3. Network connectivity is working")
        sys.exit(1)
    
    print("✅ Database connection successful!")
    print()
    
    # Create tables
    print("🔨 Creating database tables...")
    try:
        init_db()
        print("✅ Database tables created successfully!")
        print()
        print("Tables created:")
        print("  - users")
        print("  - portfolio_positions")
        print("  - transactions")
        print("  - recommendations")
        print()
        print("=" * 60)
        print("✅ INITIALIZATION COMPLETE")
        print("=" * 60)
        print()
        print("Your bot is now ready to use PostgreSQL!")
        print("Redeploy your bot to start using the database.")
        
    except Exception as e:
        print(f"❌ ERROR: Failed to create tables!")
        print(f"Error: {e}")
        import traceback
        print()
        print("Full traceback:")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
