#!/usr/bin/env python3
"""
Database configuration for PostgreSQL using SQLAlchemy.
"""
import os
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

# Get DATABASE_URL from environment - prefer PUBLIC_URL for Railway
# DATABASE_PUBLIC_URL works externally, DATABASE_URL is internal network only
DATABASE_URL = os.getenv('DATABASE_PUBLIC_URL') or os.getenv('DATABASE_URL')

if not DATABASE_URL:
    raise ValueError("DATABASE_PUBLIC_URL or DATABASE_URL environment variable not set!")

# Fix for SQLAlchemy 1.4+ (Railway uses postgres://, SQLAlchemy needs postgresql://)
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

logger.info(f"🗄️ Connecting to PostgreSQL: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'local'}")

# Create engine with shorter timeout and better error handling
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,      # Test connections before using
    pool_size=5,             # Max 5 connections
    max_overflow=10,         # Allow up to 10 overflow connections
    echo=False,              # Set to True for SQL debugging
    connect_args={
        "connect_timeout": 10,  # 10 second timeout instead of 5 minutes
        "options": "-c statement_timeout=30000"  # 30s query timeout
    }
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

def get_db():
    """Get database session (use with dependency injection)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database (create all tables) - SYNCHRONOUS version."""
    from backend.models import User, PortfolioPosition, Transaction, Recommendation
    
    logger.info("🔨 Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database tables created successfully!")

async def init_db_async():
    """Initialize database asynchronously (non-blocking for FastAPI startup).
    
    This runs the synchronous init_db() in a thread pool executor
    to prevent blocking the async event loop.
    """
    logger.info("🔨 Initializing database tables (async)...")
    
    try:
        # Run the blocking database operation in a thread pool
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, init_db)
        logger.info("✅ PostgreSQL tables ready (async init complete)")
        return True
    except Exception as e:
        logger.error(f"❌ PostgreSQL initialization failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        # Re-raise exception to prevent bot from running without database
        raise RuntimeError(f"PostgreSQL connection failed: {e}")

def test_connection():
    """Test database connection."""
    try:
        with engine.connect() as connection:
            result = connection.execute("SELECT 1")
            logger.info("✅ Database connection successful!")
            return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False
