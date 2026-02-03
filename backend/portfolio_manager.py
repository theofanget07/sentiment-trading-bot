#!/usr/bin/env python3
"""
Portfolio Manager - PostgreSQL-based storage for user crypto portfolios.
Supports positions tracking, transaction history, P&L calculations with real-time prices.
"""
from datetime import datetime
from typing import Dict, List, Optional
import logging
from sqlalchemy.orm import Session

try:
    from backend.database import SessionLocal
    from backend.models import User, PortfolioPosition, Transaction, Recommendation
    from backend.crypto_prices import get_crypto_price, get_multiple_prices, calculate_pnl, format_price
except ImportError:
    from database import SessionLocal
    from models import User, PortfolioPosition, Transaction, Recommendation
    from crypto_prices import get_crypto_price, get_multiple_prices, calculate_pnl, format_price

logger = logging.getLogger(__name__)

class PortfolioManager:
    """
    Manage user portfolios using PostgreSQL database.
    Thread-safe with session management.
    """
    
    def _get_session(self) -> Session:
        """Get new database session."""
        return SessionLocal()
    
    def _get_or_create_user(self, db: Session, user_id: int, username: str = None) -> User:
        """Get existing user or create new one."""
        user = db.query(User).filter(User.telegram_id == user_id).first()
        
        if not user:
            user = User(
                telegram_id=user_id,
                username=username or f"user_{user_id}"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"✅ Created new user: {user_id}")
        else:
            # Update last_active
            user.last_active = datetime.utcnow()
            db.commit()
        
        return user
    
    # Portfolio operations
    
    def get_portfolio(self, user_id: int, username: str = None) -> Dict:
        """
        Get user's portfolio (basic, without real-time prices).
        
        Returns:
            {
                "username": str,
                "positions": {"BTC": {"quantity": float, "avg_price": float}, ...},
                "total_invested": float,
                "created_at": str
            }
        """
        db = self._get_session()
        try:
            user = self._get_or_create_user(db, user_id, username)
            
            # Get all positions
            positions = db.query(PortfolioPosition).filter(
                PortfolioPosition.user_id == user.id
            ).all()
            
            portfolio_dict = {}
            total_invested = 0.0
            
            for pos in positions:
                portfolio_dict[pos.symbol] = {
                    "quantity": pos.quantity,
                    "avg_price": pos.avg_price
                }
                total_invested += pos.total_invested
            
            return {
                "username": user.username,
                "positions": portfolio_dict,
                "total_invested": round(total_invested, 2),
                "created_at": user.created_at.isoformat() + "Z"
            }
        
        finally:
            db.close()
    
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
        db = self._get_session()
        try:
            user = self._get_or_create_user(db, user_id, username)
            
            # Get all positions
            positions = db.query(PortfolioPosition).filter(
                PortfolioPosition.user_id == user.id
            ).all()
            
            if not positions:
                return {
                    "username": user.username,
                    "positions": {},
                    "total_invested": 0.0,
                    "total_current_value": 0.0,
                    "total_pnl_usd": 0.0,
                    "total_pnl_percent": 0.0
                }
            
            # Get symbols and fetch current prices
            symbols = [pos.symbol for pos in positions]
            current_prices = get_multiple_prices(symbols)
            
            # Calculate P&L for each position
            enriched_positions = {}
            total_invested = 0.0
            total_current_value = 0.0
            
            for pos in positions:
                current_price = current_prices.get(pos.symbol)
                
                # Skip if price not available
                if current_price is None:
                    logger.warning(f"No price available for {pos.symbol}")
                    current_price = pos.avg_price  # Fallback
                
                invested = pos.quantity * pos.avg_price
                current_value = pos.quantity * current_price
                pnl_usd = current_value - invested
                pnl_percent = calculate_pnl(pos.avg_price, current_price)
                
                enriched_positions[pos.symbol] = {
                    "quantity": pos.quantity,
                    "avg_price": pos.avg_price,
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
                "username": user.username,
                "positions": enriched_positions,
                "total_invested": total_invested,
                "total_current_value": total_current_value,
                "total_pnl_usd": total_pnl_usd,
                "total_pnl_percent": total_pnl_percent
            }
        
        finally:
            db.close()
    
    def add_position(self, user_id: int, symbol: str, quantity: float, price: float, username: str = None) -> Dict:
        """
        Add or update a position (accumulate if exists).
        
        Returns:
            dict with operation result
        """
        db = self._get_session()
        try:
            user = self._get_or_create_user(db, user_id, username)
            symbol = symbol.upper()
            
            # Check if position exists
            position = db.query(PortfolioPosition).filter(
                PortfolioPosition.user_id == user.id,
                PortfolioPosition.symbol == symbol
            ).first()
            
            if position:
                # Accumulate: calculate new average price
                old_qty = position.quantity
                old_avg = position.avg_price
                
                new_qty = old_qty + quantity
                new_avg = (old_qty * old_avg + quantity * price) / new_qty
                
                position.quantity = new_qty
                position.avg_price = round(new_avg, 2)
                position.updated_at = datetime.utcnow()
                
                action = "updated"
            else:
                # New position
                position = PortfolioPosition(
                    user_id=user.id,
                    symbol=symbol,
                    quantity=quantity,
                    avg_price=price
                )
                db.add(position)
                action = "created"
            
            db.commit()
            db.refresh(position)
            
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
                "quantity": position.quantity,
                "avg_price": position.avg_price
            }
        
        finally:
            db.close()
    
    def remove_position(self, user_id: int, symbol: str) -> bool:
        """
        Delete a position entirely.
        
        Returns:
            True if deleted, False if not found
        """
        db = self._get_session()
        try:
            user = db.query(User).filter(User.telegram_id == user_id).first()
            if not user:
                return False
            
            symbol = symbol.upper()
            position = db.query(PortfolioPosition).filter(
                PortfolioPosition.user_id == user.id,
                PortfolioPosition.symbol == symbol
            ).first()
            
            if not position:
                return False
            
            # Add transaction record before deletion
            self.add_transaction(
                user_id=user_id,
                symbol=symbol,
                action="REMOVE",
                quantity=position.quantity,
                price=position.avg_price,
                source="manual"
            )
            
            # Delete position
            db.delete(position)
            db.commit()
            
            logger.info(f"✅ Deleted {symbol} position for user {user_id}")
            return True
        
        finally:
            db.close()
    
    # Transaction operations
    
    def add_transaction(self, user_id: int, symbol: str, action: str, 
                       quantity: float, price: float, sentiment: str = None, 
                       confidence: int = None, source: str = "manual") -> int:
        """
        Add a transaction to history.
        
        Returns:
            transaction.id
        """
        db = self._get_session()
        try:
            user = self._get_or_create_user(db, user_id)
            
            transaction = Transaction(
                user_id=user.id,
                symbol=symbol.upper(),
                action=action.upper(),
                quantity=quantity,
                price=price,
                total_usd=round(quantity * price, 2),
                source=source,
                sentiment=sentiment,
                confidence=confidence
            )
            
            db.add(transaction)
            db.commit()
            db.refresh(transaction)
            
            logger.info(f"✅ Added transaction {transaction.id} for user {user_id}")
            return transaction.id
        
        finally:
            db.close()
    
    def get_transactions(self, user_id: int, limit: int = 50) -> List[Dict]:
        """
        Get user's transaction history.
        
        Returns:
            List of transaction dicts (most recent first)
        """
        db = self._get_session()
        try:
            user = db.query(User).filter(User.telegram_id == user_id).first()
            if not user:
                return []
            
            transactions = db.query(Transaction).filter(
                Transaction.user_id == user.id
            ).order_by(Transaction.timestamp.desc()).limit(limit).all()
            
            result = []
            for tx in transactions:
                tx_dict = {
                    "id": tx.id,
                    "timestamp": tx.timestamp.isoformat() + "Z",
                    "symbol": tx.symbol,
                    "action": tx.action,
                    "quantity": tx.quantity,
                    "price": tx.price,
                    "total_usd": tx.total_usd,
                    "source": tx.source
                }
                
                if tx.sentiment:
                    tx_dict["sentiment"] = tx.sentiment
                if tx.confidence:
                    tx_dict["confidence"] = tx.confidence
                
                result.append(tx_dict)
            
            return result
        
        finally:
            db.close()
    
    # Recommendation operations
    
    def add_recommendation(self, user_id: int, symbol: str, action: str,
                          reasoning: str, sentiment: str, confidence: int) -> int:
        """
        Add AI recommendation.
        
        Returns:
            recommendation.id
        """
        db = self._get_session()
        try:
            user = self._get_or_create_user(db, user_id)
            
            recommendation = Recommendation(
                user_id=user.id,
                symbol=symbol.upper(),
                action=action.upper(),
                reasoning=reasoning,
                sentiment=sentiment,
                confidence=confidence
            )
            
            db.add(recommendation)
            db.commit()
            db.refresh(recommendation)
            
            logger.info(f"✅ Added recommendation {recommendation.id} for user {user_id}")
            return recommendation.id
        
        finally:
            db.close()
    
    def get_recommendations(self, user_id: int, limit: int = 20) -> List[Dict]:
        """
        Get user's recommendations.
        
        Returns:
            List of recommendation dicts (most recent first)
        """
        db = self._get_session()
        try:
            user = db.query(User).filter(User.telegram_id == user_id).first()
            if not user:
                return []
            
            recommendations = db.query(Recommendation).filter(
                Recommendation.user_id == user.id
            ).order_by(Recommendation.timestamp.desc()).limit(limit).all()
            
            result = []
            for rec in recommendations:
                rec_dict = {
                    "id": rec.id,
                    "timestamp": rec.timestamp.isoformat() + "Z",
                    "symbol": rec.symbol,
                    "action": rec.action,
                    "reasoning": rec.reasoning,
                    "sentiment": rec.sentiment,
                    "confidence": rec.confidence,
                    "executed": rec.executed
                }
                
                if rec.executed_at:
                    rec_dict["executed_at"] = rec.executed_at.isoformat() + "Z"
                
                result.append(rec_dict)
            
            return result
        
        finally:
            db.close()
    
    def mark_recommendation_executed(self, user_id: int, rec_id: int) -> bool:
        """
        Mark recommendation as executed.
        
        Returns:
            True if marked, False if not found
        """
        db = self._get_session()
        try:
            user = db.query(User).filter(User.telegram_id == user_id).first()
            if not user:
                return False
            
            recommendation = db.query(Recommendation).filter(
                Recommendation.id == rec_id,
                Recommendation.user_id == user.id
            ).first()
            
            if not recommendation:
                return False
            
            recommendation.executed = True
            recommendation.executed_at = datetime.utcnow()
            db.commit()
            
            logger.info(f"✅ Marked recommendation {rec_id} as executed")
            return True
        
        finally:
            db.close()
    
    # Backtest support
    
    def get_backtest_data(self, user_id: int) -> Dict:
        """
        Get all data needed for backtesting.
        
        Returns:
            {
                "portfolio": dict,
                "transactions": list,
                "recommendations": list
            }
        """
        return {
            "portfolio": self.get_portfolio(user_id),
            "transactions": self.get_transactions(user_id, limit=1000),
            "recommendations": self.get_recommendations(user_id, limit=1000)
        }

# Global instance
portfolio_manager = PortfolioManager()
