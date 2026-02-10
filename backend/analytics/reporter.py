"""
ReportGenerator - Automated Reporting System
Generates daily/weekly reports and sends them via Telegram
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
import redis

from .aggregator import MetricsAggregator

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    Generates automated analytics reports.
    
    Reports:
    - Daily summary (sent every morning)
    - Weekly overview (sent every Monday)
    - Monthly business review (sent 1st of month)
    """
    
    def __init__(self, redis_client: redis.Redis):
        """
        Initialize the report generator.
        
        Args:
            redis_client: Redis connection instance
        """
        self.redis = redis_client
        self.aggregator = MetricsAggregator(redis_client)
        logger.info("✅ ReportGenerator initialized")
    
    def generate_daily_report(self, date: Optional[datetime] = None) -> str:
        """
        Generate a daily analytics report.
        
        Args:
            date: Target date (defaults to yesterday)
        
        Returns:
            str: Formatted report text (Telegram-ready)
        """
        if date is None:
            # Default to yesterday (report sent in the morning)
            date = datetime.now(timezone.utc) - timedelta(days=1)
        
        date_str = date.strftime("%d/%m/%Y")
        
        # Get metrics
        dau = self.aggregator.get_dau(date)
        new_users = self.aggregator.get_new_users(date)
        commands = self.aggregator.get_command_usage(date)
        error_rate = self.aggregator.get_error_rate(date)
        api_cost = self.aggregator.get_api_cost(date=date)
        
        # Get premium stats
        premium_users = self.aggregator.get_premium_users()
        mrr = self.aggregator.get_mrr()
        conversion_rate = self.aggregator.get_conversion_rate()
        
        # Build report
        report = f"""📊 **CryptoSentinel AI - Daily Report**
📅 Date: {date_str}

👥 **User Metrics**
• Active users: {dau}
• New registrations: {new_users}
• Total users: {self.aggregator.get_total_users()}

💰 **Revenue Metrics**
• Premium users: {premium_users}
• MRR: €{mrr:.2f}
• Conversion rate: {conversion_rate:.1f}%

📊 **Engagement Metrics**
• Commands executed: {commands}
• Error rate: {error_rate:.2f}%

💸 **Costs**
• API costs: ${api_cost:.2f}

✅ **Status**: {'Healthy' if error_rate < 5 else '⚠️ Warning'}
"""
        
        return report
    
    def generate_weekly_report(self, end_date: Optional[datetime] = None) -> str:
        """
        Generate a weekly analytics report.
        
        Args:
            end_date: End date (defaults to yesterday)
        
        Returns:
            str: Formatted report text (Telegram-ready)
        """
        if end_date is None:
            end_date = datetime.now(timezone.utc) - timedelta(days=1)
        
        start_date = end_date - timedelta(days=6)
        
        week_str = f"{start_date.strftime('%d/%m')} - {end_date.strftime('%d/%m/%Y')}"
        
        # Get metrics
        wau = self.aggregator.get_wau(end_date)
        
        # Count new users in the week
        new_users_week = 0
        for i in range(7):
            date = end_date - timedelta(days=i)
            new_users_week += self.aggregator.get_new_users(date)
        
        # Get costs for the week
        costs = self.aggregator.get_total_cost(start_date, end_date)
        
        # Revenue metrics
        premium_users = self.aggregator.get_premium_users()
        mrr = self.aggregator.get_mrr()
        conversion_rate = self.aggregator.get_conversion_rate()
        
        # Build report
        report = f"""📈 **CryptoSentinel AI - Weekly Report**
📅 Week: {week_str}

👥 **User Growth**
• Weekly active users: {wau}
• New users this week: {new_users_week}
• Total users: {self.aggregator.get_total_users()}

💰 **Revenue Performance**
• Premium users: {premium_users}
• MRR: €{mrr:.2f}
• Conversion rate: {conversion_rate:.1f}%
• ARPU: €{self.aggregator.get_arpu():.2f}

💸 **Costs This Week**
• API costs: ${costs['api_costs_usd']:.2f}
• Infrastructure: €{costs['infrastructure_costs_eur']:.2f}
• Total: €{costs['total_costs_eur']:.2f}

🎯 **Key Insights**
• Avg daily users: {wau // 7}
• Avg new users/day: {new_users_week // 7}
• Cost per user: €{(costs['total_costs_eur'] / wau if wau > 0 else 0):.2f}
"""
        
        return report
    
    def generate_monthly_report(self, month: Optional[int] = None, year: Optional[int] = None) -> str:
        """
        Generate a monthly business report.
        
        Args:
            month: Target month (1-12, defaults to last month)
            year: Target year (defaults to current year)
        
        Returns:
            str: Formatted report text (Telegram-ready)
        """
        now = datetime.now(timezone.utc)
        
        if month is None:
            # Last month
            last_month = now.replace(day=1) - timedelta(days=1)
            month = last_month.month
            year = last_month.year
        elif year is None:
            year = now.year
        
        month_name = datetime(year, month, 1).strftime("%B %Y")
        
        # Calculate MAU
        end_date = datetime(year, month, 1, tzinfo=timezone.utc) + timedelta(days=32)
        end_date = end_date.replace(day=1) - timedelta(days=1)  # Last day of month
        mau = self.aggregator.get_mau(end_date)
        
        # Revenue metrics
        premium_users = self.aggregator.get_premium_users()
        mrr = self.aggregator.get_mrr()
        conversion_rate = self.aggregator.get_conversion_rate()
        
        # Build report
        report = f"""📅 **CryptoSentinel AI - Monthly Report**
🗓️ Month: {month_name}

👥 **User Stats**
• Monthly active users: {mau}
• Total users: {self.aggregator.get_total_users()}

💰 **Revenue**
• Premium users: {premium_users}
• MRR: €{mrr:.2f}
• ARR: €{mrr * 12:.2f}
• Conversion rate: {conversion_rate:.1f}%

🎯 **Business Health**
• Revenue/MAU: €{(mrr / mau if mau > 0 else 0):.2f}
• Free users: {self.aggregator.get_total_users() - premium_users}
• Premium ratio: {(premium_users / self.aggregator.get_total_users() * 100 if self.aggregator.get_total_users() > 0 else 0):.1f}%
"""
        
        return report
