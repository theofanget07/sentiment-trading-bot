"""Database models for sentiment trading bot."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()

class SubscriptionLevel(enum.Enum):
    """Subscription tiers."""
    FREE = "free"
    PREMIUM = "premium"

class SentimentEnum(enum.Enum):
    """Sentiment categories."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"

class User(Base):
    """User model for subscribers."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, nullable=True, index=True)
    subscription_level = Column(Enum(SubscriptionLevel), default=SubscriptionLevel.FREE, nullable=False)
    stripe_customer_id = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    analyses = relationship("Analysis", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, level={self.subscription_level.value})>"

class Article(Base):
    """Article model for scraped news."""
    __tablename__ = "articles"
    
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, nullable=False, index=True)
    title = Column(String, nullable=False)
    source = Column(String, nullable=False, index=True)  # e.g., "CoinDesk", "Reddit"
    content = Column(Text, nullable=True)
    sentiment = Column(Enum(SentimentEnum), nullable=True, index=True)
    confidence = Column(Float, nullable=True)  # 0.0 to 1.0
    reasoning = Column(Text, nullable=True)
    published_at = Column(DateTime, nullable=True, index=True)
    fetched_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    analyzed_at = Column(DateTime, nullable=True)
    is_analyzed = Column(Boolean, default=False, nullable=False, index=True)
    
    # Relationships
    analyses = relationship("Analysis", back_populates="article")
    
    def __repr__(self):
        return f"<Article(id={self.id}, title={self.title[:50]}, sentiment={self.sentiment})>"

class Analysis(Base):
    """Analysis tracking for user requests."""
    __tablename__ = "analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=True, index=True)
    input_text = Column(Text, nullable=True)  # For manual user analyses
    sentiment = Column(Enum(SentimentEnum), nullable=False)
    confidence = Column(Float, nullable=False)
    reasoning = Column(Text, nullable=True)
    analyzed_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="analyses")
    article = relationship("Article", back_populates="analyses")
    
    def __repr__(self):
        return f"<Analysis(id={self.id}, user_id={self.user_id}, sentiment={self.sentiment.value})>"

class DailyDigest(Base):
    """Track daily digest emails sent."""
    __tablename__ = "daily_digests"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    sent_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    article_count = Column(Integer, nullable=False)
    email_status = Column(String, nullable=False)  # "sent", "failed", "bounced"
    
    def __repr__(self):
        return f"<DailyDigest(id={self.id}, user_id={self.user_id}, sent_at={self.sent_at})>"
