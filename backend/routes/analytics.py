"""
Analytics API Routes
FastAPI endpoints for analytics dashboard
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

# Import analytics modules
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analytics.aggregator import MetricsAggregator
from analytics.reporter import ReportGenerator
from analytics.alerts import AlertManager
from redis_storage import get_redis_client

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/analytics", tags=["analytics"])

# Initialize analytics components
try:
    redis_client = get_redis_client()
    aggregator = MetricsAggregator(redis_client)
    reporter = ReportGenerator(redis_client)
    alert_manager = AlertManager(redis_client)
    logger.info("✅ Analytics routes initialized")
except Exception as e:
    logger.error(f"❌ Failed to initialize analytics: {e}")
    aggregator = None
    reporter = None
    alert_manager = None


# ==================== RESPONSE MODELS ====================

class OverviewResponse(BaseModel):
    """Overview dashboard response"""
    timestamp: str
    users: Dict[str, int]
    revenue: Dict[str, float]
    engagement: Dict[str, int]
    costs: Dict[str, float]
    health: Dict[str, Any]


class MetricResponse(BaseModel):
    """Single metric response"""
    metric: str
    value: Any
    timestamp: str


# ==================== ENDPOINTS ====================

@router.get("/", response_model=Dict[str, str])
async def analytics_root():
    """
    Analytics API root endpoint.
    """
    return {
        "service": "CryptoSentinel Analytics API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": [
            "/analytics/overview",
            "/analytics/users",
            "/analytics/revenue",
            "/analytics/engagement",
            "/analytics/costs",
            "/analytics/alerts",
            "/analytics/report/daily",
            "/analytics/report/weekly"
        ]
    }


@router.get("/overview", response_model=OverviewResponse)
async def get_overview():
    """
    Get complete analytics overview.
    
    Returns all key metrics:
    - User counts (total, premium, free, DAU, WAU, MAU)
    - Revenue metrics (MRR, ARPU, conversion rate)
    - Engagement metrics (commands, error rate)
    - Cost metrics (API costs, infrastructure)
    - Health status
    """
    if not aggregator:
        raise HTTPException(status_code=500, detail="Analytics not initialized")
    
    try:
        overview = aggregator.get_overview()
        return overview
    except Exception as e:
        logger.error(f"Error getting overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users", response_model=Dict[str, Any])
async def get_user_metrics(
    days: int = Query(default=7, ge=1, le=90, description="Number of days to analyze")
):
    """
    Get detailed user metrics.
    
    Args:
        days: Number of days to analyze (1-90)
    
    Returns:
        Detailed user statistics and trends
    """
    if not aggregator:
        raise HTTPException(status_code=500, detail="Analytics not initialized")
    
    try:
        today = datetime.now(timezone.utc)
        
        # Collect daily data
        daily_data = []
        for i in range(days):
            date = today - timedelta(days=i)
            daily_data.append({
                "date": date.strftime("%Y-%m-%d"),
                "dau": aggregator.get_dau(date),
                "new_users": aggregator.get_new_users(date)
            })
        
        return {
            "total_users": aggregator.get_total_users(),
            "premium_users": aggregator.get_premium_users(),
            "free_users": aggregator.get_total_users() - aggregator.get_premium_users(),
            "dau": aggregator.get_dau(),
            "wau": aggregator.get_wau(),
            "mau": aggregator.get_mau(),
            "daily_data": daily_data,
            "period_days": days
        }
    except Exception as e:
        logger.error(f"Error getting user metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/revenue", response_model=Dict[str, Any])
async def get_revenue_metrics():
    """
    Get revenue and conversion metrics.
    
    Returns:
        MRR, ARPU, conversion rate, premium user count
    """
    if not aggregator:
        raise HTTPException(status_code=500, detail="Analytics not initialized")
    
    try:
        mrr = aggregator.get_mrr()
        arpu = aggregator.get_arpu()
        conversion_rate = aggregator.get_conversion_rate()
        premium_users = aggregator.get_premium_users()
        total_users = aggregator.get_total_users()
        
        return {
            "mrr_eur": round(mrr, 2),
            "arr_eur": round(mrr * 12, 2),
            "arpu_eur": round(arpu, 2),
            "conversion_rate_pct": round(conversion_rate, 2),
            "premium_users": premium_users,
            "free_users": total_users - premium_users,
            "revenue_per_premium": 9.0,  # € per month
            "ltv_estimate_eur": round(9.0 * 12, 2)  # Assuming 12 month average lifetime
        }
    except Exception as e:
        logger.error(f"Error getting revenue metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/engagement", response_model=Dict[str, Any])
async def get_engagement_metrics(
    days: int = Query(default=7, ge=1, le=30, description="Number of days to analyze")
):
    """
    Get user engagement metrics.
    
    Args:
        days: Number of days to analyze
    
    Returns:
        Command usage, error rates, top features
    """
    if not aggregator:
        raise HTTPException(status_code=500, detail="Analytics not initialized")
    
    try:
        today = datetime.now(timezone.utc)
        
        # Collect command usage over period
        total_commands = 0
        total_errors = 0
        
        for i in range(days):
            date = today - timedelta(days=i)
            commands = aggregator.get_command_usage(date)
            error_rate = aggregator.get_error_rate(date)
            total_commands += commands
            # Estimate errors from error rate
            total_errors += int(commands * error_rate / 100)
        
        avg_commands_per_day = total_commands / days
        
        return {
            "total_commands": total_commands,
            "avg_commands_per_day": round(avg_commands_per_day, 1),
            "error_count": total_errors,
            "error_rate_pct": round(aggregator.get_error_rate(), 2),
            "top_commands": aggregator.get_top_commands(),
            "period_days": days
        }
    except Exception as e:
        logger.error(f"Error getting engagement metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/costs", response_model=Dict[str, Any])
async def get_cost_metrics(
    days: int = Query(default=7, ge=1, le=30, description="Number of days to analyze")
):
    """
    Get cost metrics (API + infrastructure).
    
    Args:
        days: Number of days to analyze
    
    Returns:
        API costs, infrastructure costs, total costs
    """
    if not aggregator:
        raise HTTPException(status_code=500, detail="Analytics not initialized")
    
    try:
        today = datetime.now(timezone.utc)
        start_date = today - timedelta(days=days - 1)
        
        costs = aggregator.get_total_cost(start_date, today)
        
        # Calculate cost per user
        active_users = aggregator.get_wau() if days <= 7 else aggregator.get_mau()
        cost_per_user = costs["total_costs_eur"] / active_users if active_users > 0 else 0
        
        return {
            "api_costs_usd": costs["api_costs_usd"],
            "infrastructure_costs_eur": costs["infrastructure_costs_eur"],
            "total_costs_eur": costs["total_costs_eur"],
            "cost_per_user_eur": round(cost_per_user, 2),
            "period_days": costs["days"],
            "daily_avg_eur": round(costs["total_costs_eur"] / costs["days"], 2)
        }
    except Exception as e:
        logger.error(f"Error getting cost metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts", response_model=Dict[str, Any])
async def check_alerts():
    """
    Check all alert conditions.
    
    Returns:
        List of active alerts with severity and details
    """
    if not alert_manager:
        raise HTTPException(status_code=500, detail="Alert manager not initialized")
    
    try:
        alerts = alert_manager.check_all_alerts()
        
        return {
            "alert_count": len(alerts),
            "alerts": alerts,
            "status": "healthy" if len(alerts) == 0 else "warning",
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error checking alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report/daily", response_model=Dict[str, str])
async def get_daily_report(
    date: Optional[str] = Query(default=None, description="Date in YYYY-MM-DD format")
):
    """
    Get daily analytics report.
    
    Args:
        date: Target date (defaults to yesterday)
    
    Returns:
        Formatted daily report
    """
    if not reporter:
        raise HTTPException(status_code=500, detail="Reporter not initialized")
    
    try:
        if date:
            target_date = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        else:
            target_date = None
        
        report = reporter.generate_daily_report(target_date)
        
        return {
            "report_type": "daily",
            "date": (target_date or datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d"),
            "report": report
        }
    except Exception as e:
        logger.error(f"Error generating daily report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report/weekly", response_model=Dict[str, str])
async def get_weekly_report():
    """
    Get weekly analytics report.
    
    Returns:
        Formatted weekly report (last 7 days)
    """
    if not reporter:
        raise HTTPException(status_code=500, detail="Reporter not initialized")
    
    try:
        report = reporter.generate_weekly_report()
        
        return {
            "report_type": "weekly",
            "period": "last_7_days",
            "report": report
        }
    except Exception as e:
        logger.error(f"Error generating weekly report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=Dict[str, str])
async def health_check():
    """
    Health check endpoint for analytics service.
    """
    status = "healthy"
    
    if not aggregator or not reporter or not alert_manager:
        status = "degraded"
    
    return {
        "status": status,
        "service": "analytics",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
