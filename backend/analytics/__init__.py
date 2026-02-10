"""
Analytics Module for CryptoSentinel AI Bot
Phase 1.5 - Analytics & Monitoring System

This module provides comprehensive analytics and monitoring capabilities:
- Event tracking (all user actions)
- Metrics aggregation (DAU, WAU, MAU, MRR, conversion rates)
- Revenue tracking (Stripe integration)
- Performance monitoring (latency, errors)
- Automated reporting and alerts
"""

from .tracker import AnalyticsTracker
from .aggregator import MetricsAggregator
from .reporter import ReportGenerator
from .alerts import AlertManager

__all__ = [
    'AnalyticsTracker',
    'MetricsAggregator',
    'ReportGenerator',
    'AlertManager'
]

__version__ = '1.0.0'
