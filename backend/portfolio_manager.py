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
    
    def get_enriched_summary(self, user_id: int, username: str = None) -> Dict:
        """
        Get enriched portfolio summary with realized/unrealized P&L breakdown.
        
        Returns:
            {
                "username": str,
                "num_positions": int,
                "total_invested": float,
                "total_current_value": float,
                "unrealized_pnl": float,
                "unrealized_pnl_percent": float,
                "realized_pnl": float,
                "total_pnl": float,
                "best_performer": {"symbol": str, "pnl_percent": float},
                "worst_performer": {"symbol": str, "pnl_percent": float},
                "diversification_score": float,
                "positions": dict
            }
        """
        portfolio = self.get_portfolio_with_prices(user_id, username)
        realized_pnl = storage.get_total_realized_pnl(user_id)
        
        # Find best/worst performers
        best = None
        worst = None
        
        if portfolio["positions"]:
            for symbol, pos in portfolio["positions"].items():
                pnl_pct = pos["pnl_percent"]
                if best is None or pnl_pct > best["pnl_percent"]:
                    best = {"symbol": symbol, "pnl_percent": pnl_pct}
                if worst is None or pnl_pct < worst["pnl_percent"]:
                    worst = {"symbol": symbol, "pnl_percent": pnl_pct}
        
        # Diversification score (simple: num positions / max supported)
        num_positions = len(portfolio["positions"])
        diversification = min(num_positions / 5, 1.0) * 100  # 5+ positions = 100%
        
        return {
            "username": portfolio["username"],
            "num_positions": num_positions,
            "total_invested": portfolio["total_invested"],
            "total_current_value": portfolio["total_current_value"],
            "unrealized_pnl": portfolio["total_pnl_usd"],
            "unrealized_pnl_percent": portfolio["total_pnl_percent"],
            "realized_pnl": round(realized_pnl, 2),
            "total_pnl": round(portfolio["total_pnl_usd"] + realized_pnl, 2),
            "best_performer": best,
            "worst_performer": worst,
            "diversification_score": round(diversification, 1),
            "positions": portfolio["positions"]
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
    
    def remove_position(self, user_id: int, symbol: str, quantity: float = None) -> Dict:
        """
        Remove a position entirely or partially.
        
        Args:
            user_id: User ID
            symbol: Crypto symbol
            quantity: Optional - amount to remove. If None, removes 100%.
        
        Returns:
            {
                "success": bool,
                "action": "partial_remove" or "full_remove",
                "quantity_removed": float,
                "quantity_remaining": float or 0
            }
        """
        symbol = symbol.upper()
        existing_pos = storage.get_position(user_id, symbol)
        
        if not existing_pos:
            return {
                "success": False,
                "error": "Position not found"
            }
        
        current_qty = existing_pos['quantity']
        avg_price = existing_pos['avg_price']
        
        # Full removal if quantity not specified
        if quantity is None or quantity >= current_qty:
            # Add transaction record before deletion
            storage.add_transaction(user_id, {
                "symbol": symbol,
                "action": "REMOVE",
                "quantity": current_qty,
                "price": avg_price,
                "total_usd": round(current_qty * avg_price, 2),
                "source": "manual"
            })
            
            storage.delete_position(user_id, symbol)
            logger.info(f"✅ Full removal: {symbol} for user {user_id}")
            
            return {
                "success": True,
                "action": "full_remove",
                "quantity_removed": current_qty,
                "quantity_remaining": 0
            }
        
        # Partial removal
        if quantity <= 0:
            return {
                "success": False,
                "error": "Quantity must be positive"
            }
        
        if quantity > current_qty:
            return {
                "success": False,
                "error": f"Cannot remove {quantity} (only have {current_qty})"
            }
        
        new_qty = current_qty - quantity
        storage.set_position(user_id, symbol, new_qty, avg_price)
        
        # Add transaction
        storage.add_transaction(user_id, {
            "symbol": symbol,
            "action": "PARTIAL_REMOVE",
            "quantity": quantity,
            "price": avg_price,
            "total_usd": round(quantity * avg_price, 2),
            "source": "manual"
        })
        
        logger.info(f"✅ Partial removal: {quantity} {symbol} for user {user_id}")
        
        return {
            "success": True,
            "action": "partial_remove",
            "quantity_removed": quantity,
            "quantity_remaining": new_qty
        }
    
    def sell_position(self, user_id: int, symbol: str, quantity: float, sell_price: float) -> Dict:
        """
        Sell a position (partial or full) and record realized P&L.
        
        Args:
            user_id: User ID
            symbol: Crypto symbol
            quantity: Amount to sell
            sell_price: Price at which selling
        
        Returns:
            {
                "success": bool,
                "symbol": str,
                "quantity_sold": float,
                "buy_price": float,
                "sell_price": float,
                "pnl_realized": float,
                "pnl_percent": float,
                "quantity_remaining": float
            }
        """
        symbol = symbol.upper()
        existing_pos = storage.get_position(user_id, symbol)
        
        if not existing_pos:
            return {
                "success": False,
                "error": "Position not found"
            }
        
        current_qty = existing_pos['quantity']
        buy_price = existing_pos['avg_price']
        
        if quantity <= 0:
            return {
                "success": False,
                "error": "Quantity must be positive"
            }
        
        if quantity > current_qty:
            return {
                "success": False,
                "error": f"Cannot sell {quantity} (only have {current_qty})"
            }
        
        # Calculate P&L
        pnl_realized = (sell_price - buy_price) * quantity
        pnl_percent = calculate_pnl(buy_price, sell_price)
        
        # Record realized P&L
        storage.add_realized_pnl(user_id, {
            "symbol": symbol,
            "quantity_sold": quantity,
            "buy_price": buy_price,
            "sell_price": sell_price,
            "pnl_realized": round(pnl_realized, 2),
            "pnl_percent": round(pnl_percent, 2)
        })
        
        # Update or remove position
        if quantity >= current_qty:
            # Full sell
            storage.delete_position(user_id, symbol)
            remaining = 0
        else:
            # Partial sell - keep same avg price
            new_qty = current_qty - quantity
            storage.set_position(user_id, symbol, new_qty, buy_price)
            remaining = new_qty
        
        # Add transaction
        storage.add_transaction(user_id, {
            "symbol": symbol,
            "action": "SELL",
            "quantity": quantity,
            "price": sell_price,
            "total_usd": round(quantity * sell_price, 2),
            "pnl": round(pnl_realized, 2),
            "source": "manual"
        })
        
        logger.info(f"✅ Sold {quantity} {symbol} @ {sell_price} (P&L: {pnl_realized:+.2f}) for user {user_id}")
        
        return {
            "success": True,
            "symbol": symbol,
            "quantity_sold": quantity,
            "buy_price": buy_price,
            "sell_price": sell_price,
            "pnl_realized": round(pnl_realized, 2),
            "pnl_percent": round(pnl_percent, 2),
            "quantity_remaining": remaining
        }
    
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
