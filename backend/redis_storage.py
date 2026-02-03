#!/usr/bin/env python3
"""
Redis storage layer for portfolio management.
Simple, fast, and reliable alternative to PostgreSQL on Railway.
"""
import os
import json
import redis
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Get Redis URL from Railway environment
REDIS_URL = os.getenv('REDIS_URL')

if not REDIS_URL:
    raise ValueError("REDIS_URL environment variable not set!")

# Create Redis client
try:
    redis_client = redis.from_url(
        REDIS_URL,
        decode_responses=True,  # Auto-decode bytes to strings
        socket_connect_timeout=5,
        socket_timeout=5,
        retry_on_timeout=True,
        health_check_interval=30
    )
    logger.info(f"🔥 Connected to Redis: {REDIS_URL.split('@')[1] if '@' in REDIS_URL else 'railway'}")
except Exception as e:
    logger.error(f"❌ Redis connection failed: {e}")
    raise

# Redis Key Structure:
# user:{user_id}:profile -> {"user_id": int, "username": str}
# user:{user_id}:positions:{symbol} -> {"quantity": float, "avg_price": float}
# user:{user_id}:transactions -> [{"symbol": str, "quantity": float, ...}]
# user:{user_id}:realized_pnl -> [{"symbol": str, "quantity_sold": float, "pnl_realized": float, ...}]

def get_user_profile(user_id: int) -> Optional[Dict]:
    """Get user profile from Redis."""
    try:
        data = redis_client.get(f"user:{user_id}:profile")
        return json.loads(data) if data else None
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        return None

def set_user_profile(user_id: int, username: str) -> bool:
    """Save user profile to Redis."""
    try:
        profile = {"user_id": user_id, "username": username}
        redis_client.set(f"user:{user_id}:profile", json.dumps(profile))
        return True
    except Exception as e:
        logger.error(f"Error setting user profile: {e}")
        return False

def get_position(user_id: int, symbol: str) -> Optional[Dict]:
    """Get a specific position for a user."""
    try:
        data = redis_client.get(f"user:{user_id}:positions:{symbol}")
        return json.loads(data) if data else None
    except Exception as e:
        logger.error(f"Error getting position: {e}")
        return None

def set_position(user_id: int, symbol: str, quantity: float, avg_price: float) -> bool:
    """Save/update a position for a user."""
    try:
        position = {
            "symbol": symbol,
            "quantity": quantity,
            "avg_price": avg_price,
            "updated_at": datetime.utcnow().isoformat()
        }
        redis_client.set(f"user:{user_id}:positions:{symbol}", json.dumps(position))
        return True
    except Exception as e:
        logger.error(f"Error setting position: {e}")
        return False

def delete_position(user_id: int, symbol: str) -> bool:
    """Delete a position for a user."""
    try:
        redis_client.delete(f"user:{user_id}:positions:{symbol}")
        return True
    except Exception as e:
        logger.error(f"Error deleting position: {e}")
        return False

def get_all_positions(user_id: int) -> Dict[str, Dict]:
    """Get all positions for a user."""
    try:
        pattern = f"user:{user_id}:positions:*"
        keys = redis_client.keys(pattern)
        
        positions = {}
        for key in keys:
            # Extract symbol from key: user:123:positions:BTC -> BTC
            symbol = key.split(':')[-1]
            data = redis_client.get(key)
            if data:
                positions[symbol] = json.loads(data)
        
        return positions
    except Exception as e:
        logger.error(f"Error getting all positions: {e}")
        return {}

def add_transaction(user_id: int, transaction: Dict) -> bool:
    """Add a transaction to user's history."""
    try:
        # Get current transactions
        data = redis_client.get(f"user:{user_id}:transactions")
        transactions = json.loads(data) if data else []
        
        # Add new transaction with timestamp
        transaction['timestamp'] = datetime.utcnow().isoformat()
        transactions.append(transaction)
        
        # Keep only last 100 transactions (memory management)
        if len(transactions) > 100:
            transactions = transactions[-100:]
        
        # Save back
        redis_client.set(f"user:{user_id}:transactions", json.dumps(transactions))
        return True
    except Exception as e:
        logger.error(f"Error adding transaction: {e}")
        return False

def get_transactions(user_id: int, limit: int = 10) -> List[Dict]:
    """Get user's recent transactions."""
    try:
        data = redis_client.get(f"user:{user_id}:transactions")
        transactions = json.loads(data) if data else []
        
        # Return last N transactions (most recent first)
        return transactions[-limit:][::-1]
    except Exception as e:
        logger.error(f"Error getting transactions: {e}")
        return []

def add_realized_pnl(user_id: int, pnl_record: Dict) -> bool:
    """Add a realized P&L record (from partial or full sell).
    
    Args:
        pnl_record: {
            "symbol": str,
            "quantity_sold": float,
            "buy_price": float,
            "sell_price": float,
            "pnl_realized": float,
            "date": str (ISO format)
        }
    """
    try:
        data = redis_client.get(f"user:{user_id}:realized_pnl")
        records = json.loads(data) if data else []
        
        # Add timestamp if not provided
        if 'date' not in pnl_record:
            pnl_record['date'] = datetime.utcnow().isoformat()
        
        records.append(pnl_record)
        
        # Keep last 100 records
        if len(records) > 100:
            records = records[-100:]
        
        redis_client.set(f"user:{user_id}:realized_pnl", json.dumps(records))
        logger.info(f"✅ Realized P&L recorded: {pnl_record['symbol']} {pnl_record['pnl_realized']:+.2f} USD")
        return True
    except Exception as e:
        logger.error(f"Error adding realized P&L: {e}")
        return False

def get_realized_pnl(user_id: int, symbol: str = None) -> List[Dict]:
    """Get realized P&L records.
    
    Args:
        user_id: User ID
        symbol: Optional - filter by symbol. If None, returns all.
    
    Returns:
        List of P&L records
    """
    try:
        data = redis_client.get(f"user:{user_id}:realized_pnl")
        records = json.loads(data) if data else []
        
        if symbol:
            records = [r for r in records if r['symbol'] == symbol.upper()]
        
        return records
    except Exception as e:
        logger.error(f"Error getting realized P&L: {e}")
        return []

def get_total_realized_pnl(user_id: int) -> float:
    """Calculate total realized P&L across all positions.
    
    Returns:
        Total realized P&L in USD
    """
    try:
        records = get_realized_pnl(user_id)
        return sum(r.get('pnl_realized', 0) for r in records)
    except Exception as e:
        logger.error(f"Error calculating total realized P&L: {e}")
        return 0.0

def test_connection() -> bool:
    """Test Redis connection."""
    try:
        redis_client.ping()
        logger.info("✅ Redis connection successful!")
        return True
    except Exception as e:
        logger.error(f"❌ Redis connection test failed: {e}")
        return False
