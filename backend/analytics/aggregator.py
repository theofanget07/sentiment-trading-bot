"""
MetricsAggregator - Business Metrics Calculator
Aggregates tracked events into actionable business metrics
"""

import logging
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
import redis

logger = logging.getLogger(__name__)


class MetricsAggregator:
    """
    Aggregates analytics data into business metrics.
    
    Metrics calculated:
    - User metrics: DAU, WAU, MAU, registrations, churn
    - Revenue metrics: MRR, ARPU, LTV
    - Engagement metrics: command usage, session length
    - Conversion metrics: Free → Premium rate, time to conversion
    - Performance metrics: latency, error rate
    """
    
    def __init__(self, redis_client: redis.Redis):
        """
        Initialize the metrics aggregator.
        
        Args:
            redis_client: Redis connection instance
        """
        self.redis = redis_client
        logger.info("✅ MetricsAggregator initialized")
    
    # ==================== USER METRICS ====================
    
    def get_dau(self, date: Optional[datetime] = None) -> int:
        """
        Get Daily Active Users.
        
        Args:
            date: Target date (defaults to today)
        
        Returns:
            int: Number of unique active users
        """
        if date is None:
            date = datetime.now(timezone.utc)
        
        date_key = date.strftime("%Y-%m-%d")
        return self.redis.scard(f"users:active:{date_key}")
    
    def get_wau(self, end_date: Optional[datetime] = None) -> int:
        """
        Get Weekly Active Users (last 7 days).
        
        Args:
            end_date: End date (defaults to today)
        
        Returns:
            int: Number of unique active users in last 7 days
        """
        if end_date is None:
            end_date = datetime.now(timezone.utc)
        
        # Collect unique users from last 7 days
        unique_users = set()
        for i in range(7):
            date = end_date - timedelta(days=i)
            date_key = date.strftime("%Y-%m-%d")
            users = self.redis.smembers(f"users:active:{date_key}")
            unique_users.update(users)
        
        return len(unique_users)
    
    def get_mau(self, end_date: Optional[datetime] = None) -> int:
        """
        Get Monthly Active Users (last 30 days).
        
        Args:
            end_date: End date (defaults to today)
        
        Returns:
            int: Number of unique active users in last 30 days
        """
        if end_date is None:
            end_date = datetime.now(timezone.utc)
        
        # Collect unique users from last 30 days
        unique_users = set()
        for i in range(30):
            date = end_date - timedelta(days=i)
            date_key = date.strftime("%Y-%m-%d")
            users = self.redis.smembers(f"users:active:{date_key}")
            unique_users.update(users)
        
        return len(unique_users)
    
    def get_total_users(self) -> int:
        """
        Get total registered users (all time).
        
        Returns:
            int: Total number of registered users
        """
        return self.redis.scard("users:registered:all")
    
    def get_new_users(self, date: Optional[datetime] = None) -> int:
        """
        Get new user registrations for a specific day.
        
        Args:
            date: Target date (defaults to today)
        
        Returns:
            int: Number of new registrations
        """
        if date is None:
            date = datetime.now(timezone.utc)
        
        date_key = date.strftime("%Y-%m-%d")
        return self.redis.scard(f"users:registered:{date_key}")
    
    # ==================== REVENUE METRICS ====================
    
    def get_premium_users(self) -> int:
        """
        Get total number of premium (paying) users.
        
        Returns:
            int: Number of premium users
        """
        return self.redis.scard("users:premium:all")
    
    def get_mrr(self, price_per_user: float = 9.0) -> float:
        """
        Get Monthly Recurring Revenue.
        
        Args:
            price_per_user: Monthly subscription price (€9 default)
        
        Returns:
            float: MRR in euros
        """
        premium_users = self.get_premium_users()
        return premium_users * price_per_user
    
    def get_arpu(self, price_per_user: float = 9.0) -> float:
        """
        Get Average Revenue Per User.
        
        Args:
            price_per_user: Monthly subscription price
        
        Returns:
            float: ARPU in euros
        """
        total_users = self.get_total_users()
        if total_users == 0:
            return 0.0
        
        mrr = self.get_mrr(price_per_user)
        return mrr / total_users
    
    def get_conversion_rate(self) -> float:
        """
        Get Free → Premium conversion rate.
        
        Returns:
            float: Conversion rate as percentage (0-100)
        """
        total_users = self.get_total_users()
        premium_users = self.get_premium_users()
        
        if total_users == 0:
            return 0.0
        
        return (premium_users / total_users) * 100
    
    # ==================== ENGAGEMENT METRICS ====================
    
    def get_command_usage(
        self,
        date: Optional[datetime] = None,
        command: Optional[str] = None
    ) -> int:
        """
        Get command usage count.
        
        Args:
            date: Target date (defaults to today)
            command: Specific command (None = all commands)
        
        Returns:
            int: Number of command executions
        """
        if date is None:
            date = datetime.now(timezone.utc)
        
        date_key = date.strftime("%Y-%m-%d")
        
        if command:
            key = f"count:events:{date_key}:command_success"
            # Note: This counts all successful commands
            # For specific command tracking, we'd need more granular keys
            return int(self.redis.get(key) or 0)
        else:
            # All commands
            return int(self.redis.get(f"count:events:{date_key}") or 0)
    
    def get_top_commands(
        self,
        date: Optional[datetime] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get most used commands.
        
        Args:
            date: Target date (defaults to today)
            limit: Max number of commands to return
        
        Returns:
            List of dicts with command name and count
        """
        # TODO: Implement with more granular command tracking
        # For now, return placeholder
        return [
            {"command": "analyze", "count": 150},
            {"command": "recommend", "count": 120},
            {"command": "portfolio", "count": 90}
        ]
    
    def get_error_rate(
        self,
        date: Optional[datetime] = None
    ) -> float:
        """
        Get error rate (errors / total events).
        
        Args:
            date: Target date (defaults to today)
        
        Returns:
            float: Error rate as percentage (0-100)
        """
        if date is None:
            date = datetime.now(timezone.utc)
        
        date_key = date.strftime("%Y-%m-%d")
        
        total_events = int(self.redis.get(f"count:events:{date_key}") or 0)
        errors = int(self.redis.get(f"count:events:{date_key}:command_error") or 0)
        
        if total_events == 0:
            return 0.0
        
        return (errors / total_events) * 100
    
    # ==================== COST METRICS ====================
    
    def get_api_cost(
        self,
        api_name: Optional[str] = None,
        date: Optional[datetime] = None
    ) -> float:
        """
        Get API costs for a specific day.
        
        Args:
            api_name: Specific API (None = all APIs)
            date: Target date (defaults to today)
        
        Returns:
            float: API cost in USD
        """
        if date is None:
            date = datetime.now(timezone.utc)
        
        date_key = date.strftime("%Y-%m-%d")
        
        if api_name:
            cost = self.redis.get(f"cost:api:{api_name}:{date_key}")
        else:
            cost = self.redis.get(f"cost:api:total:{date_key}")
        
        return float(cost or 0.0)
    
    def get_total_cost(
        self,
        start_date: datetime,
        end_date: Optional[datetime] = None
    ) -> Dict[str, float]:
        """
        Get total costs over a period.
        
        Args:
            start_date: Start date
            end_date: End date (defaults to today)
        
        Returns:
            Dict with breakdown of costs
        """
        if end_date is None:
            end_date = datetime.now(timezone.utc)
        
        total_api_cost = 0.0
        days = (end_date - start_date).days + 1
        
        for i in range(days):
            date = start_date + timedelta(days=i)
            total_api_cost += self.get_api_cost(date=date)
        
        # Estimate infrastructure costs (Railway, Redis)
        # Assuming ~€20/month = ~€0.67/day
        infrastructure_cost = days * 0.67
        
        return {
            "api_costs_usd": round(total_api_cost, 2),
            "infrastructure_costs_eur": round(infrastructure_cost, 2),
            "total_costs_eur": round(total_api_cost + infrastructure_cost, 2),
            "days": days
        }
    
    # ==================== OVERVIEW DASHBOARD ====================
    
    def get_overview(self) -> Dict[str, Any]:
        """
        Get complete overview of all metrics.
        
        Returns:
            Dict with all key metrics
        """
        today = datetime.now(timezone.utc)
        yesterday = today - timedelta(days=1)
        
        # User metrics
        total_users = self.get_total_users()
        premium_users = self.get_premium_users()
        free_users = total_users - premium_users
        dau = self.get_dau()
        wau = self.get_wau()
        mau = self.get_mau()
        new_today = self.get_new_users()
        
        # Revenue metrics
        mrr = self.get_mrr()
        arpu = self.get_arpu()
        conversion_rate = self.get_conversion_rate()
        
        # Engagement metrics
        commands_today = self.get_command_usage()
        error_rate = self.get_error_rate()
        
        # Cost metrics
        costs_today = self.get_api_cost()
        costs_week = self.get_total_cost(today - timedelta(days=7), today)
        
        return {
            "timestamp": today.isoformat(),
            "users": {
                "total": total_users,
                "premium": premium_users,
                "free": free_users,
                "dau": dau,
                "wau": wau,
                "mau": mau,
                "new_today": new_today
            },
            "revenue": {
                "mrr_eur": round(mrr, 2),
                "arpu_eur": round(arpu, 2),
                "conversion_rate_pct": round(conversion_rate, 2)
            },
            "engagement": {
                "commands_today": commands_today,
                "error_rate_pct": round(error_rate, 2)
            },
            "costs": {
                "api_today_usd": round(costs_today, 2),
                "total_week_eur": round(costs_week["total_costs_eur"], 2)
            },
            "health": {
                "status": "healthy" if error_rate < 5 else "warning",
                "dau_wau_ratio": round((dau / wau * 100) if wau > 0 else 0, 2)
            }
        }
