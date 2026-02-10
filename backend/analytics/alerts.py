"""
AlertManager - Automated Alert System
Monitors metrics and sends alerts when thresholds are breached
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import redis

from .aggregator import MetricsAggregator

logger = logging.getLogger(__name__)


class AlertManager:
    """
    Monitors metrics and sends alerts.
    
    Alert triggers:
    - Error rate > 5%
    - Conversion rate < 5%
    - Churn rate > 10%
    - API costs > budget
    - Zero activity for 2+ hours
    """
    
    # Alert thresholds
    THRESHOLD_ERROR_RATE = 5.0  # percent
    THRESHOLD_CONVERSION_RATE = 5.0  # percent (minimum)
    THRESHOLD_API_COST_DAILY = 5.0  # USD
    THRESHOLD_ZERO_ACTIVITY_HOURS = 2  # hours
    
    def __init__(self, redis_client: redis.Redis):
        """
        Initialize the alert manager.
        
        Args:
            redis_client: Redis connection instance
        """
        self.redis = redis_client
        self.aggregator = MetricsAggregator(redis_client)
        logger.info("✅ AlertManager initialized")
    
    def check_all_alerts(self) -> List[Dict[str, Any]]:
        """
        Check all alert conditions and return triggered alerts.
        
        Returns:
            List of alert dicts with severity, message, and details
        """
        alerts = []
        
        # Check error rate
        error_alert = self.check_error_rate()
        if error_alert:
            alerts.append(error_alert)
        
        # Check conversion rate
        conversion_alert = self.check_conversion_rate()
        if conversion_alert:
            alerts.append(conversion_alert)
        
        # Check API costs
        cost_alert = self.check_api_costs()
        if cost_alert:
            alerts.append(cost_alert)
        
        # Check activity
        activity_alert = self.check_activity()
        if activity_alert:
            alerts.append(activity_alert)
        
        return alerts
    
    def check_error_rate(self) -> Optional[Dict[str, Any]]:
        """
        Check if error rate exceeds threshold.
        
        Returns:
            Alert dict if triggered, None otherwise
        """
        error_rate = self.aggregator.get_error_rate()
        
        if error_rate > self.THRESHOLD_ERROR_RATE:
            return {
                "severity": "high" if error_rate > 10 else "medium",
                "type": "error_rate",
                "message": f"⚠️ **High Error Rate Alert**\n\nError rate: {error_rate:.1f}%\nThreshold: {self.THRESHOLD_ERROR_RATE}%\n\n⚡ Action needed: Check logs and investigate failures.",
                "value": error_rate,
                "threshold": self.THRESHOLD_ERROR_RATE
            }
        
        return None
    
    def check_conversion_rate(self) -> Optional[Dict[str, Any]]:
        """
        Check if conversion rate is below threshold.
        
        Returns:
            Alert dict if triggered, None otherwise
        """
        total_users = self.aggregator.get_total_users()
        
        # Only check if we have enough users (> 50)
        if total_users < 50:
            return None
        
        conversion_rate = self.aggregator.get_conversion_rate()
        
        if conversion_rate < self.THRESHOLD_CONVERSION_RATE:
            return {
                "severity": "medium",
                "type": "conversion_rate",
                "message": f"📉 **Low Conversion Rate Alert**\n\nConversion rate: {conversion_rate:.1f}%\nTarget: >{self.THRESHOLD_CONVERSION_RATE}%\n\n💡 Consider: Improve Premium value prop or adjust pricing.",
                "value": conversion_rate,
                "threshold": self.THRESHOLD_CONVERSION_RATE
            }
        
        return None
    
    def check_api_costs(self) -> Optional[Dict[str, Any]]:
        """
        Check if daily API costs exceed budget.
        
        Returns:
            Alert dict if triggered, None otherwise
        """
        daily_cost = self.aggregator.get_api_cost()
        
        if daily_cost > self.THRESHOLD_API_COST_DAILY:
            return {
                "severity": "high" if daily_cost > 10 else "medium",
                "type": "api_cost",
                "message": f"💸 **High API Cost Alert**\n\nDaily cost: ${daily_cost:.2f}\nBudget: ${self.THRESHOLD_API_COST_DAILY:.2f}\n\n⚡ Action: Review API usage and implement caching.",
                "value": daily_cost,
                "threshold": self.THRESHOLD_API_COST_DAILY
            }
        
        return None
    
    def check_activity(self) -> Optional[Dict[str, Any]]:
        """
        Check if there has been zero activity recently.
        
        Returns:
            Alert dict if triggered, None otherwise
        """
        now = datetime.now(timezone.utc)
        hour_key = now.strftime("%Y-%m-%d-%H")
        
        # Check last 2 hours
        activity_found = False
        for i in range(self.THRESHOLD_ZERO_ACTIVITY_HOURS):
            check_time = now.replace(minute=0, second=0, microsecond=0)
            check_time = check_time.replace(hour=now.hour - i)
            check_key = check_time.strftime("%Y-%m-%d-%H")
            
            active_users = self.redis.scard(f"users:active:hour:{check_key}")
            if active_users > 0:
                activity_found = True
                break
        
        if not activity_found:
            return {
                "severity": "low",
                "type": "zero_activity",
                "message": f"⚠️ **Zero Activity Alert**\n\nNo user activity detected in last {self.THRESHOLD_ZERO_ACTIVITY_HOURS} hours.\n\n🔍 Check: Bot status, Railway deployment, webhook configuration.",
                "value": 0,
                "threshold": 1
            }
        
        return None
    
    def format_alerts_for_telegram(self, alerts: List[Dict[str, Any]]) -> str:
        """
        Format alerts for Telegram message.
        
        Args:
            alerts: List of alert dicts
        
        Returns:
            str: Formatted alert message
        """
        if not alerts:
            return "✅ **All Systems Normal**\n\nNo alerts triggered."
        
        # Sort by severity
        severity_order = {"high": 0, "medium": 1, "low": 2}
        alerts.sort(key=lambda x: severity_order.get(x["severity"], 3))
        
        message = f"🚨 **Analytics Alerts** ({len(alerts)})\n\n"
        
        for alert in alerts:
            message += alert["message"] + "\n\n"
        
        message += f"_Checked at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_"
        
        return message
    
    def should_send_alert(self, alert_type: str) -> bool:
        """
        Check if an alert should be sent (rate limiting).
        
        Args:
            alert_type: Type of alert
        
        Returns:
            bool: True if alert should be sent
        """
        # Check if this alert was sent recently (last 6 hours)
        key = f"alert:sent:{alert_type}"
        last_sent = self.redis.get(key)
        
        if last_sent:
            return False
        
        # Mark alert as sent (6 hour cooldown)
        self.redis.setex(key, 6 * 60 * 60, "1")
        return True
