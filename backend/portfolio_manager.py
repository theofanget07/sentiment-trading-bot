#!/usr/bin/env python3
"""
Portfolio Manager - Redis-based storage for user crypto portfolios.
Fast, simple, and reliable alternative to PostgreSQL.
"""
from datetime import datetime
from typing import Dict, List, Optional
import logging

try:
    from backend import redis_storage as storage
    from backend.crypto_prices import get_crypto_price, get_multiple_prices, calculate_pnl, format_price
except ImportError:
    import redis_storage as storage
    from crypto_prices import get_crypto_price, get_multiple_prices, calculate_pnl, format_price

logger = logging.getLogger(__name__)

class PortfolioManager:
    """
    Manage user portfolios using Redis.
    Much simpler than PostgreSQL - no sessions, no ORM complexity.
    """
    
    def _ensure_user(self, user_id: int, username: str = None):
        """Ensure user profile exists in Redis."""
        profile = storage.get_user_profile(user_id)
        if not profile:
            storage.set_user_profile(user_id, username or f"user_{user_id}")
            logger.info(f"✅ Created new user: {user_id}")
    
    # Portfolio operations
    
    def get_portfolio(self, user_id: int, username: str = None) -> Dict:
        """
        Get user's portfolio (basic, without real-time prices).
        
        Returns:
            {
                "username": str,
                "positions": {"BTC": {"quantity": float, "avg_price": float}, ...},
                "total_invested": float
            }
        """
        self._ensure_user(user_id, username)
        
        profile = storage.get_user_profile(user_id)
        positions = storage.get_all_positions(user_id)
        
        # Calculate total invested
        total_invested = 0.0
        clean_positions = {}
        
        for symbol, pos in positions.items():
            invested = pos['quantity'] * pos['avg_price']
            total_invested += invested
            clean_positions[symbol] = {
                "quantity": pos['quantity'],
                "avg_price": pos['avg_price']
            }
        
        return {
            "username": profile.get('username', f"user_{user_id}"),
            "positions": clean_positions,
            "total_invested": round(total_invested, 2)
        }
    
    def get_portfolio_with_prices(self, user_id: int, username: str = None) -> Dict:
        """
        Get user's portfolio with current market prices and P&L calculations.
        
        Returns:
            {
                "username": str,
                "positions": {
                    "BTC": {
                        "quantity": float,
                        "avg_price": float,
                        "current_price": float,
                        "invested_value": float,
                        "current_value": float,
                        "pnl_usd": float,
                        "pnl_percent": float
                    }, ...
                },
                "total_invested": float,
                "total_current_value": float,
                "total_pnl_usd": float,
                "total_pnl_percent": float
            }
        """
        self._ensure_user(user_id, username)
        
        profile = storage.get_user_profile(user_id)
        positions = storage.get_all_positions(user_id)
        
        if not positions:
            return {
                "username": profile.get('username', f"user_{user_id}"),
                "positions": {},
                "total_invested": 0.0,
                "total_current_value": 0.0,
                "total_pnl_usd": 0.0,
                "total_pnl_percent": 0.0
            }
        
        # Get symbols and fetch current prices
        symbols = list(positions.keys())
        current_prices = get_multiple_prices(symbols)
        
        # Calculate P&L for each position
        enriched_positions = {}
        total_invested = 0.0
        total_current_value = 0.0
        
        for symbol, pos in positions.items():
            current_price = current_prices.get(symbol)
            
            # Skip if price not available
            if current_price is None:
                logger.warning(f"No price available for {symbol}")
                current_price = pos['avg_price']  # Fallback
            
            invested = pos['quantity'] * pos['avg_price']
            current_value = pos['quantity'] * current_price
            pnl_usd = current_value - invested
            pnl_percent = calculate_pnl(pos['avg_price'], current_price)
            
            enriched_positions[symbol] = {
                "quantity": pos['quantity'],
                "avg_price": pos['avg_price'],
                "current_price": current_price,
                "invested_value": invested,
                "current_value": current_value,
                "pnl_usd": pnl_usd,
                "pnl_percent": pnl_percent
            }
            
            total_invested += invested
            total_current_value += current_value
        
        total_pnl_usd = total_current_value - total_invested
        total_pnl_percent = (total_pnl_usd / total_invested * 100) if total_invested > 0 else 0.0
        
        return {
            "username": profile.get('username', f"user_{user_id}"),
            "positions": enriched_positions,
            "total_invested": round(total_invested, 2),
            "total_current_value": round(total_current_value, 2),
            "total_pnl_usd": round(total_pnl_usd, 2),
            "total_pnl_percent": round(total_pnl_percent, 2)
        }
    
    def add_position(self, user_id: int, symbol: str, quantity: float, price: float, username: str = None) -> Dict:
        """
        Add or update a position (accumulate if exists).
        
        Returns:
            dict with operation result
        """
        self._ensure_user(user_id, username)
        symbol = symbol.upper()
        
        # Check if position exists
        existing_pos = storage.get_position(user_id, symbol)
        
        if existing_pos:
            # Accumulate: calculate new average price
            old_qty = existing_pos['quantity']
            old_avg = existing_pos['avg_price']
            
            new_qty = old_qty + quantity
            new_avg = (old_qty * old_avg + quantity * price) / new_qty
            
            storage.set_position(user_id, symbol, new_qty, round(new_avg, 2))
            action = "updated"
            final_qty = new_qty
            final_avg = round(new_avg, 2)
        else:
            # New position
            storage.set_position(user_id, symbol, quantity, price)
            action = "created"
            final_qty = quantity
            final_avg = price
        
        # Add transaction record
        storage.add_transaction(user_id, {
            "symbol": symbol,
            "action": "BUY",
            "quantity": quantity,
            "price": price,
            "total_usd": round(quantity * price, 2),
            "source": "manual"
        })
        
        logger.info(f"✅ {action.capitalize()} {symbol} position for user {user_id}")
        
        return {
            "action": action,
            "symbol": symbol,
            "quantity": final_qty,
            "avg_price": final_avg
        }
    
    def remove_position(self, user_id: int, symbol: str) -> bool:
        """
        Delete a position entirely.
        
        Returns:
            True if deleted, False if not found
        """
        symbol = symbol.upper()
        existing_pos = storage.get_position(user_id, symbol)
        
        if not existing_pos:
            return False
        
        # Add transaction record before deletion
        storage.add_transaction(user_id, {
            "symbol": symbol,
            "action": "REMOVE",
            "quantity": existing_pos['quantity'],
            "price": existing_pos['avg_price'],
            "total_usd": round(existing_pos['quantity'] * existing_pos['avg_price'], 2),
            "source": "manual"
        })
        
        # Delete position
        storage.delete_position(user_id, symbol)
        
        logger.info(f"✅ Deleted {symbol} position for user {user_id}")
        return True
    
    # Transaction operations
    
    def add_transaction(self, user_id: int, symbol: str, action: str, 
                       quantity: float, price: float, sentiment: str = None, 
                       confidence: int = None, source: str = "manual") -> bool:
        """
        Add a transaction to history.
        
        Returns:
            True if added successfully
        """
        self._ensure_user(user_id)
        
        transaction = {
            "symbol": symbol.upper(),
            "action": action.upper(),
            "quantity": quantity,
            "price": price,
            "total_usd": round(quantity * price, 2),
            "source": source
        }
        
        if sentiment:
            transaction["sentiment"] = sentiment
        if confidence:
            transaction["confidence"] = confidence
        
        success = storage.add_transaction(user_id, transaction)
        
        if success:
            logger.info(f"✅ Added transaction for user {user_id}")
        
        return success
    
    def get_transactions(self, user_id: int, limit: int = 10) -> List[Dict]:
        """
        Get user's transaction history.
        
        Returns:
            List of transaction dicts (most recent first)
        """
        return storage.get_transactions(user_id, limit)
    
    # Backtest support
    
    def get_backtest_data(self, user_id: int) -> Dict:
        """
        Get all data needed for backtesting.
        
        Returns:
            {
                "portfolio": dict,
                "transactions": list
            }
        """
        return {
            "portfolio": self.get_portfolio(user_id),
            "transactions": self.get_transactions(user_id, limit=100)
        }

# Global instance
portfolio_manager = PortfolioManager()
