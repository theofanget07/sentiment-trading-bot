#!/usr/bin/env python3
"""
Portfolio Manager - JSON-based storage for user crypto portfolios.
Supports positions tracking, transaction history, P&L calculations with real-time prices.
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import logging

try:
    from backend.crypto_prices import get_crypto_price, get_multiple_prices, calculate_pnl, format_price
except ImportError:
    from crypto_prices import get_crypto_price, get_multiple_prices, calculate_pnl, format_price

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), 'user_data')
PORTFOLIOS_FILE = os.path.join(DATA_DIR, 'portfolios.json')
TRANSACTIONS_FILE = os.path.join(DATA_DIR, 'transactions.json')
RECOMMENDATIONS_FILE = os.path.join(DATA_DIR, 'recommendations.json')

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

class PortfolioManager:
    """Manage user portfolios using JSON file storage."""
    
    def __init__(self):
        """Initialize portfolio manager and create files if needed."""
        self._ensure_files_exist()
    
    def _ensure_files_exist(self):
        """Create JSON files if they don't exist."""
        for filepath in [PORTFOLIOS_FILE, TRANSACTIONS_FILE, RECOMMENDATIONS_FILE]:
            if not os.path.exists(filepath):
                with open(filepath, 'w') as f:
                    json.dump({}, f)
                logger.info(f"✅ Created {os.path.basename(filepath)}")
    
    def _load_json(self, filepath: str) -> Dict:
        """Load JSON file."""
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _save_json(self, filepath: str, data: Dict):
        """Save data to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    # Portfolio operations
    
    def get_portfolio(self, user_id: int, username: str = None) -> Dict:
        """Get user's portfolio."""
        portfolios = self._load_json(PORTFOLIOS_FILE)
        user_key = str(user_id)
        
        if user_key not in portfolios:
            # Create empty portfolio
            portfolios[user_key] = {
                "username": username or f"user_{user_id}",
                "positions": {},
                "total_value_usd": 0.0,
                "created_at": datetime.utcnow().isoformat() + "Z"
            }
            self._save_json(PORTFOLIOS_FILE, portfolios)
        
        return portfolios[user_key]
    
    def get_portfolio_with_prices(self, user_id: int, username: str = None) -> Dict:
        """Get user's portfolio with current market prices and P&L calculations.
        
        Returns:
            {
                "username": str,
                "positions": {
                    "BTC": {
                        "quantity": float,
                        "avg_price": float,
                        "current_price": float,
                        "total_value": float,
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
        portfolio = self.get_portfolio(user_id, username)
        
        if not portfolio["positions"]:
            return {
                "username": portfolio.get("username", "User"),
                "positions": {},
                "total_invested": 0.0,
                "total_current_value": 0.0,
                "total_pnl_usd": 0.0,
                "total_pnl_percent": 0.0
            }
        
        # Get all symbols
        symbols = list(portfolio["positions"].keys())
        
        # Fetch current prices for all positions
        current_prices = get_multiple_prices(symbols)
        
        # Calculate P&L for each position
        enriched_positions = {}
        total_invested = 0.0
        total_current_value = 0.0
        
        for symbol, pos in portfolio["positions"].items():
            qty = pos["quantity"]
            avg_price = pos["avg_price"]
            current_price = current_prices.get(symbol)
            
            # Skip if price not available
            if current_price is None:
                logger.warning(f"No price available for {symbol}")
                current_price = avg_price  # Fallback to avg price
            
            invested = qty * avg_price
            current_value = qty * current_price
            pnl_usd = current_value - invested
            pnl_percent = calculate_pnl(avg_price, current_price)
            
            enriched_positions[symbol] = {
                "quantity": qty,
                "avg_price": avg_price,
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
            "username": portfolio.get("username", "User"),
            "positions": enriched_positions,
            "total_invested": total_invested,
            "total_current_value": total_current_value,
            "total_pnl_usd": total_pnl_usd,
            "total_pnl_percent": total_pnl_percent
        }
    
    def add_position(self, user_id: int, symbol: str, quantity: float, price: float, username: str = None) -> Dict:
        """Add or update a position (accumulate if exists).
        
        Returns:
            dict with operation result
        """
        portfolios = self._load_json(PORTFOLIOS_FILE)
        user_key = str(user_id)
        
        if user_key not in portfolios:
            portfolios[user_key] = {
                "username": username or f"user_{user_id}",
                "positions": {},
                "total_value_usd": 0.0,
                "created_at": datetime.utcnow().isoformat() + "Z"
            }
        
        symbol = symbol.upper()
        
        # Check if position exists
        if symbol in portfolios[user_key]["positions"]:
            # Accumulate: calculate new average price
            existing = portfolios[user_key]["positions"][symbol]
            old_qty = existing["quantity"]
            old_avg = existing["avg_price"]
            
            new_qty = old_qty + quantity
            new_avg = (old_qty * old_avg + quantity * price) / new_qty
            
            portfolios[user_key]["positions"][symbol] = {
                "quantity": new_qty,
                "avg_price": round(new_avg, 2),
                "last_updated": datetime.utcnow().isoformat() + "Z"
            }
            
            action = "updated"
        else:
            # New position
            portfolios[user_key]["positions"][symbol] = {
                "quantity": quantity,
                "avg_price": price,
                "last_updated": datetime.utcnow().isoformat() + "Z"
            }
            action = "created"
        
        # Recalculate total value
        total_value = sum(
            pos["quantity"] * pos["avg_price"]
            for pos in portfolios[user_key]["positions"].values()
        )
        portfolios[user_key]["total_value_usd"] = round(total_value, 2)
        
        self._save_json(PORTFOLIOS_FILE, portfolios)
        
        # Add transaction record
        self.add_transaction(
            user_id=user_id,
            symbol=symbol,
            action="BUY",
            quantity=quantity,
            price=price,
            source="manual"
        )
        
        logger.info(f"✅ {action.capitalize()} {symbol} position for user {user_id}")
        
        return {
            "action": action,
            "symbol": symbol,
            "quantity": portfolios[user_key]["positions"][symbol]["quantity"],
            "avg_price": portfolios[user_key]["positions"][symbol]["avg_price"]
        }
    
    def remove_position(self, user_id: int, symbol: str) -> bool:
        """Delete a position entirely.
        
        Returns:
            True if deleted, False if not found
        """
        portfolios = self._load_json(PORTFOLIOS_FILE)
        user_key = str(user_id)
        symbol = symbol.upper()
        
        if user_key in portfolios and symbol in portfolios[user_key]["positions"]:
            # Get position details before deletion
            pos = portfolios[user_key]["positions"][symbol]
            
            # Add transaction record
            self.add_transaction(
                user_id=user_id,
                symbol=symbol,
                action="REMOVE",
                quantity=pos["quantity"],
                price=pos["avg_price"],
                source="manual"
            )
            
            # Delete position
            del portfolios[user_key]["positions"][symbol]
            
            # Recalculate total value
            total_value = sum(
                p["quantity"] * p["avg_price"]
                for p in portfolios[user_key]["positions"].values()
            )
            portfolios[user_key]["total_value_usd"] = round(total_value, 2)
            
            self._save_json(PORTFOLIOS_FILE, portfolios)
            logger.info(f"✅ Deleted {symbol} position for user {user_id}")
            return True
        
        return False
    
    # Transaction operations
    
    def add_transaction(self, user_id: int, symbol: str, action: str, 
                       quantity: float, price: float, sentiment: str = None, 
                       confidence: int = None, source: str = "manual"):
        """Add a transaction to history."""
        transactions = self._load_json(TRANSACTIONS_FILE)
        user_key = str(user_id)
        
        if user_key not in transactions:
            transactions[user_key] = []
        
        tx_id = f"tx_{len(transactions[user_key]) + 1:04d}"
        transaction = {
            "id": tx_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "symbol": symbol,
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
        
        transactions[user_key].append(transaction)
        self._save_json(TRANSACTIONS_FILE, transactions)
        logger.info(f"✅ Added transaction {tx_id} for user {user_id}")
        
        return tx_id
    
    def get_transactions(self, user_id: int, limit: int = 50) -> List[Dict]:
        """Get user's transaction history."""
        transactions = self._load_json(TRANSACTIONS_FILE)
        user_key = str(user_id)
        
        if user_key not in transactions:
            return []
        
        # Return most recent first
        return list(reversed(transactions[user_key]))[:limit]
    
    # Recommendation operations
    
    def add_recommendation(self, user_id: int, symbol: str, action: str,
                          reasoning: str, sentiment: str, confidence: int):
        """Add AI recommendation."""
        recommendations = self._load_json(RECOMMENDATIONS_FILE)
        user_key = str(user_id)
        
        if user_key not in recommendations:
            recommendations[user_key] = []
        
        rec_id = f"rec_{len(recommendations[user_key]) + 1:04d}"
        recommendation = {
            "id": rec_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "symbol": symbol,
            "action": action.upper(),
            "reasoning": reasoning,
            "sentiment": sentiment,
            "confidence": confidence,
            "executed": False
        }
        
        recommendations[user_key].append(recommendation)
        self._save_json(RECOMMENDATIONS_FILE, recommendations)
        logger.info(f"✅ Added recommendation {rec_id} for user {user_id}")
        
        return rec_id
    
    def get_recommendations(self, user_id: int, limit: int = 20) -> List[Dict]:
        """Get user's recommendations."""
        recommendations = self._load_json(RECOMMENDATIONS_FILE)
        user_key = str(user_id)
        
        if user_key not in recommendations:
            return []
        
        # Return most recent first
        return list(reversed(recommendations[user_key]))[:limit]
    
    def mark_recommendation_executed(self, user_id: int, rec_id: str):
        """Mark recommendation as executed."""
        recommendations = self._load_json(RECOMMENDATIONS_FILE)
        user_key = str(user_id)
        
        if user_key in recommendations:
            for rec in recommendations[user_key]:
                if rec["id"] == rec_id:
                    rec["executed"] = True
                    rec["executed_at"] = datetime.utcnow().isoformat() + "Z"
                    break
            
            self._save_json(RECOMMENDATIONS_FILE, recommendations)
            logger.info(f"✅ Marked recommendation {rec_id} as executed")
    
    # Backtest support
    
    def get_backtest_data(self, user_id: int) -> Dict:
        """Get all data needed for backtesting."""
        return {
            "portfolio": self.get_portfolio(user_id),
            "transactions": self.get_transactions(user_id, limit=1000),
            "recommendations": self.get_recommendations(user_id, limit=1000)
        }

# Global instance
portfolio_manager = PortfolioManager()
