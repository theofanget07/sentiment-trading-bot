#!/usr/bin/env python3
"""
SQLAlchemy models for PostgreSQL database.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime

try:
    from backend.database import Base
except ImportError:
    from database import Base

class User(Base):
    """
    User account model.
    Stores Telegram user information.
    """
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    positions = relationship("PortfolioPosition", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, username='{self.username}')>"

class PortfolioPosition(Base):
    """
    User's portfolio positions.
    Tracks quantity and average price for each crypto asset.
    """
    __tablename__ = 'portfolio_positions'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    symbol = Column(String, nullable=False, index=True)  # BTC, ETH, etc.
    quantity = Column(Float, nullable=False, default=0.0)
    avg_price = Column(Float, nullable=False, default=0.0)  # Average purchase price in USD
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = relationship("User", back_populates="positions")
    
    def __repr__(self):
        return f"<Position(user_id={self.user_id}, symbol='{self.symbol}', qty={self.quantity}, avg={self.avg_price})>"
    
    @property
    def total_invested(self) -> float:
        """Calculate total invested amount."""
        return self.quantity * self.avg_price

class Transaction(Base):
    """
    Transaction history.
    Tracks all BUY/SELL/REMOVE actions.
    """
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    symbol = Column(String, nullable=False, index=True)
    action = Column(String, nullable=False)  # BUY, SELL, REMOVE
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)  # Price at transaction time (USD)
    total_usd = Column(Float, nullable=False)  # quantity * price
    source = Column(String, default='manual')  # manual, ai_recommendation, auto
    sentiment = Column(String, nullable=True)  # BULLISH, BEARISH, NEUTRAL
    confidence = Column(Integer, nullable=True)  # 0-100
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationship
    user = relationship("User", back_populates="transactions")
    
    def __repr__(self):
        return f"<Transaction(user_id={self.user_id}, {self.action} {self.quantity} {self.symbol} @ ${self.price})>"

class Recommendation(Base):
    """
    AI-generated trading recommendations.
    Tracks sentiment analysis results and suggested actions.
    """
    __tablename__ = 'recommendations'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    symbol = Column(String, nullable=False, index=True)
    action = Column(String, nullable=False)  # BUY, SELL, HOLD
    reasoning = Column(Text, nullable=False)  # AI explanation
    sentiment = Column(String, nullable=False)  # BULLISH, BEARISH, NEUTRAL
    confidence = Column(Integer, nullable=False)  # 0-100
    executed = Column(Boolean, default=False)  # Did user execute this recommendation?
    executed_at = Column(DateTime, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationship
    user = relationship("User", back_populates="recommendations")
    
    def __repr__(self):
        return f"<Recommendation(user_id={self.user_id}, {self.action} {self.symbol}, confidence={self.confidence}%)>"
