#!/usr/bin/env python3
"""
Tier Manager for CryptoSentinel AI - Free vs Premium Feature Gating.

Handles:
- User tier verification (free/premium)
- Rate limiting for free users
- Feature access control
- Subscription status management

Limitations:
- Free: 5 analyses/day, 3 positions max, NO premium features
- Premium (9€/month): Unlimited analyses, unlimited positions, ALL features

Author: Theo Fanget
Date: 08 February 2026
"""
import logging
from typing import Tuple, Optional
from datetime import datetime
from backend.redis_storage import redis_client
from backend.stripe_service import get_subscription_status

# Setup logging
logger = logging.getLogger(__name__)


class TierManager:
    """Manages user tiers and feature access for free/premium users."""
    
    def __init__(self, redis_client):
        """Initialize TierManager with Redis client.
        
        Args:
            redis_client: Redis client instance
        """
        self.redis = redis_client
        logger.info("✅ TierManager initialized")
    
    # ===== TIER STATUS =====
    
    def get_user_tier(self, user_id: int) -> str:
        """Get user tier from subscription status.
        
        Args:
            user_id: Telegram user ID
        
        Returns:
            'free' | 'premium' | 'cancelled'
        """
        return get_subscription_status(user_id)
    
    def is_premium(self, user_id: int) -> bool:
        """Check if user has premium access.
        
        Args:
            user_id: Telegram user ID
        
        Returns:
            True if user is premium
        """
        tier = self.get_user_tier(user_id)
        return tier == 'premium'
    
    def is_free(self, user_id: int) -> bool:
        """Check if user is on free tier.
        
        Args:
            user_id: Telegram user ID
        
        Returns:
            True if user is free
        """
        tier = self.get_user_tier(user_id)
        return tier in ['free', 'cancelled']
    
    # ===== RATE LIMITING FOR FREE USERS =====
    
    def can_analyze(self, user_id: int) -> Tuple[bool, str]:
        """Check if user can perform sentiment analysis (limit 5/day for free).
        
        Args:
            user_id: Telegram user ID
        
        Returns:
            Tuple of (can_proceed: bool, message: str)
        
        Examples:
            >>> can, msg = tier_manager.can_analyze(123456)
            >>> if can:
            >>>     # Perform analysis
            >>> else:
            >>>     # Show upgrade message
        """
        # Premium users have unlimited access
        if self.is_premium(user_id):
            return True, ""
        
        # Free users: check daily limit (5 analyses/day)
        today = datetime.utcnow().strftime("%Y-%m-%d")
        key = f"user:{user_id}:analyze_count:{today}"
        
        try:
            count_bytes = self.redis.get(key)
            current = int(count_bytes.decode('utf-8')) if count_bytes else 0
            
            # Check if limit reached
            if current >= 5:
                return False, (
                    "❌ **Limite atteinte** (5 analyses/jour en Free)\n\n"
                    "✨ **Passe Premium** pour analyses illimitées: /subscribe"
                )
            
            # Increment counter
            self.redis.incr(key)
            
            # Set expiration at end of day (midnight UTC)
            end_of_day = datetime.utcnow().replace(
                hour=23, minute=59, second=59, microsecond=999999
            )
            self.redis.expireat(key, int(end_of_day.timestamp()))
            
            # Return success with counter info
            return True, f"📊 Analyse {current + 1}/5 utilisée aujourd'hui (Free)"
        
        except Exception as e:
            logger.error(f"Error checking analyze limit: {e}")
            # Fail open - allow the analysis
            return True, ""
    
    def can_add_position(self, user_id: int, current_positions: int) -> Tuple[bool, str]:
        """Check if user can add a position (max 3 for free).
        
        Args:
            user_id: Telegram user ID
            current_positions: Current number of positions
        
        Returns:
            Tuple of (can_proceed: bool, message: str)
        
        Examples:
            >>> portfolio = get_portfolio(user_id)
            >>> can, msg = tier_manager.can_add_position(user_id, len(portfolio['positions']))
            >>> if can:
            >>>     # Add position
            >>> else:
            >>>     # Show upgrade message
        """
        # Premium users have unlimited positions
        if self.is_premium(user_id):
            return True, ""
        
        # Free users: max 3 positions
        if current_positions >= 3:
            return False, (
                "❌ **Limite atteinte** (3 positions max en Free)\n\n"
                f"📊 Positions actuelles: {current_positions}/3\n\n"
                "✨ **Passe Premium** pour positions illimitées: /subscribe"
            )
        
        return True, ""
    
    def can_set_alert(self, user_id: int) -> Tuple[bool, str]:
        """Check if user can set price alerts (premium only).
        
        Args:
            user_id: Telegram user ID
        
        Returns:
            Tuple of (can_proceed: bool, message: str)
        """
        if self.is_premium(user_id):
            return True, ""
        
        return False, (
            "🔒 **Feature Premium**\n\n"
            "Les alertes prix sont réservées aux membres Premium.\n\n"
            "✨ **Passe Premium (9€/mois)** pour débloquer:\n"
            "• Alertes prix TP/SL illimitées\n"
            "• Morning Briefing quotidien\n"
            "• AI Recommendations\n"
            "• Trade of the Day\n"
            "• Analyses illimitées\n"
            "• Positions illimitées\n\n"
            "👉 /subscribe pour souscrire"
        )
    
    def can_access_ai_recommendations(self, user_id: int) -> Tuple[bool, str]:
        """Check if user can access AI recommendations (premium only).
        
        Args:
            user_id: Telegram user ID
        
        Returns:
            Tuple of (can_proceed: bool, message: str)
        """
        if self.is_premium(user_id):
            return True, ""
        
        return False, (
            "🔒 **Feature Premium**\n\n"
            "Les recommandations AI sont réservées aux membres Premium.\n\n"
            "✨ **Passe Premium (9€/mois)** pour débloquer:\n"
            "• AI Recommendations personnalisées\n"
            "• Morning Briefing quotidien\n"
            "• Trade of the Day\n"
            "• Alertes prix TP/SL\n"
            "• Analyses illimitées\n"
            "• Positions illimitées\n\n"
            "👉 /subscribe pour souscrire"
        )
    
    def can_access_morning_briefing(self, user_id: int) -> bool:
        """Check if user can receive morning briefing (premium only).
        
        Args:
            user_id: Telegram user ID
        
        Returns:
            True if user can access morning briefing
        """
        return self.is_premium(user_id)
    
    # ===== ANALYTICS =====
    
    def get_usage_stats(self, user_id: int) -> dict:
        """Get usage statistics for a user.
        
        Args:
            user_id: Telegram user ID
        
        Returns:
            Dict with usage stats
        """
        today = datetime.utcnow().strftime("%Y-%m-%d")
        analyze_key = f"user:{user_id}:analyze_count:{today}"
        
        try:
            analyze_count_bytes = self.redis.get(analyze_key)
            analyze_count = int(analyze_count_bytes.decode('utf-8')) if analyze_count_bytes else 0
            
            tier = self.get_user_tier(user_id)
            
            return {
                'tier': tier,
                'analyze_count_today': analyze_count,
                'analyze_limit': None if tier == 'premium' else 5,
                'position_limit': None if tier == 'premium' else 3,
                'is_premium': tier == 'premium'
            }
        
        except Exception as e:
            logger.error(f"Error getting usage stats: {e}")
            return {
                'tier': 'free',
                'analyze_count_today': 0,
                'analyze_limit': 5,
                'position_limit': 3,
                'is_premium': False
            }
    
    # ===== PREMIUM UPGRADE MESSAGE =====
    
    def get_upgrade_message(self) -> str:
        """Get upgrade to premium message.
        
        Returns:
            Formatted upgrade message
        """
        return (
            "✨ **Passe Premium - 9€/mois**\n\n"
            "**Features Premium :**\n"
            "✅ Analyses sentiment illimitées\n"
            "✅ Positions portfolio illimitées\n"
            "✅ Morning Briefing quotidien (8h00 CET)\n"
            "✅ Alertes prix TP/SL illimitées\n"
            "✅ AI Recommendations personnalisées\n"
            "✅ Trade of the Day exclusif\n"
            "✅ Historique illimité\n\n"
            "**Tarif :**\n"
            "💰 9€/mois (annulation à tout moment)\n\n"
            "👉 Tape /subscribe pour souscrire maintenant !"
        )


# ===== GLOBAL INSTANCE =====

# Create global instance
tier_manager = TierManager(redis_client)


if __name__ == "__main__":
    # Test script
    print("="*60)
    print("TIER MANAGER TEST")
    print("="*60)
    
    # Test user ID
    test_user_id = 999999999
    
    # Test tier check
    print(f"\n1. Testing tier check for user {test_user_id}...")
    tier = tier_manager.get_user_tier(test_user_id)
    print(f"   Tier: {tier}")
    print(f"   Is premium: {tier_manager.is_premium(test_user_id)}")
    print(f"   Is free: {tier_manager.is_free(test_user_id)}")
    
    # Test analyze limit
    print(f"\n2. Testing analyze limit (5/day for free)...")
    for i in range(7):
        can, msg = tier_manager.can_analyze(test_user_id)
        print(f"   Attempt {i+1}: {'✅ Allowed' if can else '❌ Blocked'}")
        if msg:
            print(f"   Message: {msg[:50]}...")
    
    # Test position limit
    print(f"\n3. Testing position limit (3 max for free)...")
    for positions in [0, 1, 2, 3, 4]:
        can, msg = tier_manager.can_add_position(test_user_id, positions)
        print(f"   Current: {positions} -> {'✅ Can add' if can else '❌ Limit reached'}")
    
    # Test premium features
    print(f"\n4. Testing premium features...")
    can_alert, alert_msg = tier_manager.can_set_alert(test_user_id)
    print(f"   Can set alert: {'✅' if can_alert else '❌'}")
    
    can_ai, ai_msg = tier_manager.can_access_ai_recommendations(test_user_id)
    print(f"   Can access AI reco: {'✅' if can_ai else '❌'}")
    
    can_briefing = tier_manager.can_access_morning_briefing(test_user_id)
    print(f"   Can access briefing: {'✅' if can_briefing else '❌'}")
    
    # Test usage stats
    print(f"\n5. Usage stats:")
    stats = tier_manager.get_usage_stats(test_user_id)
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)
