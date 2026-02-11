#!/usr/bin/env python3
"""
Tier Manager for CryptoSentinel AI - Free vs Premium Feature Gating.

Handles:
- User tier verification (free/premium)
- Rate limiting for free users
- Feature access control
- Subscription status management

Limitations:
- Free: 3 analyses/day, 3 positions max, 1 crypto with alerts, 3 AI reco/WEEK
- Premium (9€/month): Unlimited analyses, unlimited positions, unlimited alerts, unlimited AI reco

Author: Theo Fanget
Date: 09 February 2026 (Updated - 3 analyses/day + 3 reco/week for Free)
"""
import logging
from typing import Tuple, Optional
from datetime import datetime, timedelta
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
    
    def set_tier(self, user_id: int, tier: str) -> bool:
        """Manually set user tier (admin function).
        
        Args:
            user_id: Telegram user ID
            tier: 'free' | 'premium'
        
        Returns:
            True if successful
        
        Note:
            This is for manual admin override. 
            For Stripe-based changes, use stripe_service.set_subscription_status()
        """
        from backend.stripe_service import set_subscription_status
        
        if tier not in ['free', 'premium']:
            logger.error(f"Invalid tier: {tier}")
            return False
        
        try:
            # Use stripe_service to update status (maintains consistency)
            success = set_subscription_status(user_id, tier)
            
            if success:
                logger.info(f"✅ Admin manually set user {user_id} to {tier}")
            
            return success
        
        except Exception as e:
            logger.error(f"Error setting tier for user {user_id}: {e}")
            return False
    
    # ===== HELPER: WEEK CALCULATION =====
    
    def _get_week_key(self) -> str:
        """Get current week identifier (resets every Monday at 00:00 UTC).
        
        Returns:
            Week key in format 'YYYY-WW' (e.g., '2026-06')
        
        Examples:
            >>> _get_week_key()
            '2026-06'  # Week 6 of 2026
        """
        now = datetime.utcnow()
        # ISO week: Monday = start of week
        year, week_num, _ = now.isocalendar()
        return f"{year}-W{week_num:02d}"
    
    def _get_next_monday_midnight_utc(self) -> datetime:
        """Get next Monday at 00:00 UTC for expiration.
        
        Returns:
            datetime object of next Monday midnight UTC
        """
        now = datetime.utcnow()
        # Days until next Monday (0 = Monday, 6 = Sunday)
        days_ahead = 7 - now.weekday()  # If today is Monday, this gives 7 (next Monday)
        if days_ahead == 0:
            days_ahead = 7  # If today is Monday, next Monday is in 7 days
        
        next_monday = now + timedelta(days=days_ahead)
        next_monday_midnight = next_monday.replace(hour=0, minute=0, second=0, microsecond=0)
        return next_monday_midnight
    
    # ===== RATE LIMITING FOR FREE USERS =====
    
    def can_analyze(self, user_id: int) -> Tuple[bool, str]:
        """Check if user can perform sentiment analysis (limit 3/day for free).
        
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
        
        # Free users: check daily limit (3 analyses/day)
        today = datetime.utcnow().strftime("%Y-%m-%d")
        key = f"user:{user_id}:analyze_count:{today}"
        
        try:
            count_bytes = self.redis.get(key)
            current = int(count_bytes.decode('utf-8')) if count_bytes else 0
            
            # Check if limit reached
            if current >= 3:
                return False, (
                    "❌ **Limite atteinte** (3 analyses/jour en Free)\n\n"
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
            return True, f"📊 Analyse {current + 1}/3 utilisée aujourd'hui (Free)"
        
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
    
    def can_set_alert(self, user_id: int, current_alert_count: int) -> Tuple[bool, str]:
        """Check if user can set price alerts (1 crypto max for free, unlimited for premium).
        
        Args:
            user_id: Telegram user ID
            current_alert_count: Number of cryptos with active alerts
        
        Returns:
            Tuple of (can_proceed: bool, message: str)
        
        Examples:
            >>> alerts = get_alerts(user_id)
            >>> can, msg = tier_manager.can_set_alert(user_id, len(alerts))
            >>> if can:
            >>>     # Set alert
            >>> else:
            >>>     # Show upgrade message
        """
        # Premium users have unlimited alerts
        if self.is_premium(user_id):
            return True, ""
        
        # Free users: max 1 crypto with alerts (for testing)
        if current_alert_count >= 1:
            return False, (
                "🆓 **Limite Free atteinte** (1 crypto avec alertes max)\n\n"
                f"🔔 Tu as déjà des alertes configurées sur {current_alert_count} crypto.\n\n"
                "🎁 **Version Free** : Teste les alertes sur 1 crypto\n"
                "✨ **Passe Premium (9€/mois)** pour débloquer :\n"
                "• Alertes TP/SL illimitées sur toutes tes cryptos\n"
                "• Morning Briefing quotidien (8h00)\n"
                "• AI Recommendations illimitées\n"
                "• Trade of the Day exclusif\n"
                "• Analyses illimitées\n"
                "• Positions illimitées\n\n"
                "👉 /subscribe pour souscrire"
            )
        
        # User can set first alert
        return True, "🎁 Alerte gratuite (1/1 en Free) - Passe Premium pour alertes illimitées !"
    
    def can_access_ai_recommendations(self, user_id: int) -> Tuple[bool, str]:
        """Check if user can access AI recommendations (3/WEEK for free, unlimited for premium).
        
        Args:
            user_id: Telegram user ID
        
        Returns:
            Tuple of (can_proceed: bool, message: str)
        
        Examples:
            >>> can, msg = tier_manager.can_access_ai_recommendations(user_id)
            >>> if can:
            >>>     # Show recommendations
            >>> else:
            >>>     # Show upgrade message
        """
        # Premium users have unlimited access
        if self.is_premium(user_id):
            return True, ""
        
        # Free users: check WEEKLY limit (3 recommendations/week, resets Monday 00:00 UTC)
        week_key = self._get_week_key()
        key = f"user:{user_id}:recommend_count:{week_key}"
        
        try:
            count_bytes = self.redis.get(key)
            current = int(count_bytes.decode('utf-8')) if count_bytes else 0
            
            # Check if limit reached
            if current >= 3:
                # Calculate when reset happens (next Monday)
                next_monday = self._get_next_monday_midnight_utc()
                days_until_reset = (next_monday - datetime.utcnow()).days
                
                reset_msg = "demain" if days_until_reset == 0 else f"dans {days_until_reset} jour{'s' if days_until_reset > 1 else ''}"
                
                return False, (
                    "🆓 **Limite Free atteinte** (3 recommandations/semaine)\n\n"
                    f"🤖 Tu as utilisé tes 3 recommandations AI cette semaine.\n"
                    f"🔄 Reset: **{reset_msg}** (lundi 00h00 UTC)\n\n"
                    "🎁 **Version Free** : 3 recommandations/semaine pour tester\n"
                    "✨ **Passe Premium (9€/mois)** pour :\n"
                    "• AI Recommendations illimitées 24/7\n"
                    "• Morning Briefing quotidien avec analyse\n"
                    "• Trade of the Day exclusif\n"
                    "• Alertes prix TP/SL illimitées\n"
                    "• Analyses illimitées\n"
                    "• Positions illimitées\n\n"
                    "👉 /subscribe pour souscrire"
                )
            
            # Increment counter
            self.redis.incr(key)
            
            # Set expiration at next Monday midnight UTC
            next_monday_midnight = self._get_next_monday_midnight_utc()
            self.redis.expireat(key, int(next_monday_midnight.timestamp()))
            
            # Return success with counter info
            return True, f"🤖 Recommandation {current + 1}/3 utilisée cette semaine (Free)"
        
        except Exception as e:
            logger.error(f"Error checking AI recommendation limit: {e}")
            # Fail open - allow the recommendation
            return True, ""
    
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
        week_key = self._get_week_key()
        
        analyze_key = f"user:{user_id}:analyze_count:{today}"
        recommend_key = f"user:{user_id}:recommend_count:{week_key}"
        
        try:
            analyze_count_bytes = self.redis.get(analyze_key)
            analyze_count = int(analyze_count_bytes.decode('utf-8')) if analyze_count_bytes else 0
            
            recommend_count_bytes = self.redis.get(recommend_key)
            recommend_count = int(recommend_count_bytes.decode('utf-8')) if recommend_count_bytes else 0
            
            tier = self.get_user_tier(user_id)
            
            return {
                'tier': tier,
                'analyze_count_today': analyze_count,
                'analyze_limit': None if tier == 'premium' else 3,
                'recommend_count_this_week': recommend_count,
                'recommend_limit': None if tier == 'premium' else 3,
                'position_limit': None if tier == 'premium' else 3,
                'alert_limit': None if tier == 'premium' else 1,
                'is_premium': tier == 'premium'
            }
        
        except Exception as e:
            logger.error(f"Error getting usage stats: {e}")
            return {
                'tier': 'free',
                'analyze_count_today': 0,
                'analyze_limit': 3,
                'recommend_count_this_week': 0,
                'recommend_limit': 3,
                'position_limit': 3,
                'alert_limit': 1,
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
            "✅ AI Recommendations illimitées\n"
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
    print(f"\n2. Testing analyze limit (3/day for free)...")
    for i in range(5):
        can, msg = tier_manager.can_analyze(test_user_id)
        print(f"   Attempt {i+1}: {'✅ Allowed' if can else '❌ Blocked'}")
        if msg:
            print(f"   Message: {msg[:50]}...")
    
    # Test position limit
    print(f"\n3. Testing position limit (3 max for free)...")
    for positions in [0, 1, 2, 3, 4]:
        can, msg = tier_manager.can_add_position(test_user_id, positions)
        print(f"   Current: {positions} -> {'✅ Can add' if can else '❌ Limit reached'}")
    
    # Test alert limit (1 crypto for free)
    print(f"\n4. Testing alert limit (1 crypto for free)...")
    for alert_count in [0, 1, 2]:
        can, msg = tier_manager.can_set_alert(test_user_id, alert_count)
        print(f"   Current alerts: {alert_count} -> {'✅ Can set' if can else '❌ Limit reached'}")
    
    # Test AI recommendations (3/WEEK for free)
    print(f"\n5. Testing AI recommendations (3/WEEK for free)...")
    for i in range(5):
        can, msg = tier_manager.can_access_ai_recommendations(test_user_id)
        print(f"   Attempt {i+1}: {'✅ Allowed' if can else '❌ Blocked'}")
        if msg:
            print(f"   Message: {msg[:50]}...")
    
    # Test usage stats
    print(f"\n6. Usage stats:")
    stats = tier_manager.get_usage_stats(test_user_id)
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # Test week key calculation
    print(f"\n7. Week calculation:")
    print(f"   Current week: {tier_manager._get_week_key()}")
    next_monday = tier_manager._get_next_monday_midnight_utc()
    print(f"   Next Monday reset: {next_monday.strftime('%Y-%m-%d %H:%M UTC')}")
    days_until = (next_monday - datetime.utcnow()).days
    print(f"   Days until reset: {days_until}")
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)
