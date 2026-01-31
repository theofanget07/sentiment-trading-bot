"""Database models for sentiment trading bot with portfolio tracking."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Enum, Numeric, Date
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

class SignalEnum(enum.Enum):
    """Trading signals."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"

class RecommendationEnum(enum.Enum):
    """Position recommendations."""
    HOLD = "hold"
    BUY_MORE = "buy_more"
    SELL_PARTIAL = "sell_partial"
    SELL_ALL = "sell_all"

class TransactionTypeEnum(enum.Enum):
    """Transaction types."""
    BUY = "buy"
    SELL = "sell"

class User(Base):
    """User model for subscribers."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, nullable=True)
    email = Column(String, nullable=True, index=True)
    subscription_level = Column(Enum(SubscriptionLevel), default=SubscriptionLevel.FREE, nullable=False)
    stripe_customer_id = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)
    daily_analyses_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    analyses = relationship("Analysis", back_populates="user")
    positions = relationship("UserPosition", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, level={self.subscription_level.value})>"

class Article(Base):
    """Article model for scraped news."""
    __tablename__ = "articles"
    
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(500), unique=True, nullable=False, index=True)
    title = Column(Text, nullable=False)
    source = Column(String(100), nullable=False, index=True)  # "CoinDesk", "Cointelegraph"
    content_summary = Column(Text, nullable=True)
    published_at = Column(DateTime, nullable=True, index=True)
    fetched_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    analyses = relationship("Analysis", back_populates="article")
    
    def __repr__(self):
        return f"<Article(id={self.id}, title={self.title[:50]}, source={self.source})>"

class Analysis(Base):
    """Sentiment analysis results."""
    __tablename__ = "analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # NULL for automated digest
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False, index=True)
    sentiment = Column(Enum(SentimentEnum), nullable=False, index=True)
    confidence = Column(Integer, nullable=False)  # 0-100
    one_liner = Column(Text, nullable=True)  # Summary in one sentence
    reasoning = Column(Text, nullable=True)
    analyzed_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="analyses")
    article = relationship("Article", back_populates="analyses")
    
    def __repr__(self):
        return f"<Analysis(id={self.id}, sentiment={self.sentiment.value}, confidence={self.confidence}%)>"

class DailyDigest(Base):
    """Daily sentiment digest snapshots."""
    __tablename__ = "daily_digests"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True, nullable=False, index=True)
    sentiment_score = Column(Integer, nullable=False)  # -100 to +100
    signal = Column(Enum(SignalEnum), nullable=False)
    bullish_count = Column(Integer, default=0, nullable=False)
    bearish_count = Column(Integer, default=0, nullable=False)
    neutral_count = Column(Integer, default=0, nullable=False)
    market_conclusion = Column(Text, nullable=True)  # AI-generated conclusion
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<DailyDigest(date={self.date}, score={self.sentiment_score}, signal={self.signal.value})>"

class UserPosition(Base):
    """User crypto positions (summary)."""
    __tablename__ = "user_positions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    crypto_symbol = Column(String(10), nullable=False, index=True)  # BTC, ETH, SOL, etc.
    quantity = Column(Numeric(18, 8), nullable=False)  # Total quantity held
    avg_buy_price = Column(Numeric(18, 2), nullable=False)  # Average buy price in USD
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="positions")
    transactions = relationship("PositionTransaction", back_populates="position", cascade="all, delete-orphan")
    recommendations = relationship("PositionRecommendation", back_populates="position", cascade="all, delete-orphan")
    
    # Unique constraint: one position per user per crypto
    __table_args__ = (
        {'sqlite_autoincrement': True},
    )
    
    def __repr__(self):
        return f"<UserPosition(id={self.id}, user_id={self.user_id}, symbol={self.crypto_symbol}, qty={self.quantity})>"

class PositionTransaction(Base):
    """Transaction history for user positions."""
    __tablename__ = "position_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    position_id = Column(Integer, ForeignKey("user_positions.id"), nullable=False, index=True)
    transaction_type = Column(Enum(TransactionTypeEnum), nullable=False, index=True)
    quantity = Column(Numeric(18, 8), nullable=False)
    price = Column(Numeric(18, 2), nullable=False)  # Price per unit in USD
    total_value = Column(Numeric(18, 2), nullable=False)  # quantity * price
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    position = relationship("UserPosition", back_populates="transactions")
    
    def __repr__(self):
        return f"<PositionTransaction(id={self.id}, type={self.transaction_type.value}, qty={self.quantity}, price={self.price})>"

class PositionRecommendation(Base):
    """AI-generated position recommendations."""
    __tablename__ = "position_recommendations"
    
    id = Column(Integer, primary_key=True, index=True)
    position_id = Column(Integer, ForeignKey("user_positions.id"), nullable=False, index=True)
    recommendation = Column(Enum(RecommendationEnum), nullable=False, index=True)
    reason = Column(Text, nullable=False)
    sentiment_score = Column(Integer, nullable=True)  # Market sentiment at time of recommendation
    current_price = Column(Numeric(18, 2), nullable=True)
    pnl_percent = Column(Numeric(8, 2), nullable=True)  # Profit/Loss percentage
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    position = relationship("UserPosition", back_populates="recommendations")
    
    def __repr__(self):
        return f"<PositionRecommendation(id={self.id}, recommendation={self.recommendation.value}, pnl={self.pnl_percent}%)>"
