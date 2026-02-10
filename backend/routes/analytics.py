"""
Analytics API Routes
FastAPI endpoints for analytics dashboard + admin management
"""

import logging
import os
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Query, Header
from pydantic import BaseModel

# Import analytics modules
from backend.analytics.aggregator import MetricsAggregator
from backend.analytics.reporter import ReportGenerator
from backend.analytics.alerts import AlertManager
from backend.redis_storage import get_redis_client
from backend.tier_manager import tier_manager

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

# Admin token from env
ADMIN_TOKEN = os.getenv('ADMIN_TOKEN')

if ADMIN_TOKEN:
    logger.info(f"✅ Admin token configured (length: {len(ADMIN_TOKEN)})")
else:
    logger.warning("⚠️ Admin token NOT configured!")

# ==================== HELPER FUNCTIONS ====================

def verify_admin_token(token: Optional[str] = None) -> bool:
    """Verify admin token for protected endpoints."""
    if not ADMIN_TOKEN:
        logger.warning("⚠️ ADMIN_TOKEN not configured")
        return False
    if not token:
        logger.warning("⚠️ No token provided")
        return False
    
    is_valid = token.strip() == ADMIN_TOKEN.strip()
    
    if not is_valid:
        logger.warning(f"❌ Token mismatch: provided={token[:10]}..., expected={ADMIN_TOKEN[:10]}...")
    else:
        logger.info("✅ Token validated successfully")
    
    return is_valid

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


# ==================== ANALYTICS ENDPOINTS ====================

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
            "/analytics/report/weekly",
            "/analytics/admin/users (protected)",
            "/analytics/admin/user/{user_id}/toggle (protected)"
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


# ==================== ADMIN ENDPOINTS ====================

@router.get("/admin/users", response_model=Dict[str, Any])
async def get_admin_users(
    token: str = Query(..., description="Admin authentication token"),
    search: Optional[str] = Query(None, description="Search by user_id or username")
):
    """
    Get all users with admin management capabilities (PROTECTED).
    
    Args:
        token: Admin token for authentication
        search: Optional search filter
    
    Returns:
        List of users with subscription status
    """
    # Verify admin token
    if not verify_admin_token(token):
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid admin token")
    
    try:
        # Get all user IDs from users:all set
        all_user_ids = redis_client.smembers("users:all")
        users_data = []
        
        logger.info(f"🔍 Found {len(all_user_ids)} users in users:all set")
        
        for user_id_str in all_user_ids:
            # Convert to int (smembers returns strings)
            user_id = int(user_id_str)
            
            # Get user profile (stored as JSON string with SET command)
            profile_json = redis_client.get(f"user:{user_id}:profile")
            
            if not profile_json:
                logger.warning(f"⚠️ User {user_id} in users:all but no profile found")
                continue
            
            # Parse JSON profile
            profile = json.loads(profile_json)
            username = profile.get('username', 'Unknown')
            
            # Apply search filter if provided
            if search:
                if search not in str(user_id) and search.lower() not in username.lower():
                    continue
            
            # Get subscription status
            is_premium = tier_manager.is_premium(user_id)
            
            # Check if has Stripe subscription
            stripe_sub_id = redis_client.get(f"subscription:telegram:{user_id}")
            has_stripe = stripe_sub_id is not None
            
            users_data.append({
                "user_id": user_id,
                "username": username,
                "is_premium": is_premium,
                "has_stripe_subscription": has_stripe,
                "stripe_subscription_id": stripe_sub_id if has_stripe else None
            })
        
        # Sort: Premium first, then by user_id
        users_data.sort(key=lambda x: (-x['is_premium'], x['user_id']))
        
        # Calculate stats
        total_users = len(users_data)
        premium_count = sum(1 for u in users_data if u['is_premium'])
        free_count = total_users - premium_count
        mrr = premium_count * 9.0
        
        logger.info(f"✅ Returning {total_users} users ({premium_count} premium, {free_count} free)")
        
        return {
            "total_users": total_users,
            "premium_users": premium_count,
            "free_users": free_count,
            "mrr_eur": round(mrr, 2),
            "users": users_data
        }
    
    except Exception as e:
        logger.error(f"Error getting admin users: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/user/{user_id}/toggle", response_model=Dict[str, Any])
async def toggle_user_premium(
    user_id: int,
    token: str = Query(..., description="Admin authentication token")
):
    """
    Toggle user between Premium and Free tiers (PROTECTED).
    
    Args:
        user_id: Telegram user ID
        token: Admin token for authentication
    
    Returns:
        Updated user status
    """
    # Verify admin token
    if not verify_admin_token(token):
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid admin token")
    
    try:
        # Get current status
        current_status = tier_manager.is_premium(user_id)
        
        if current_status:
            # Set to Free
            tier_manager.set_tier(user_id, 'free')
            new_status = 'free'
        else:
            # Set to Premium
            tier_manager.set_tier(user_id, 'premium')
            new_status = 'premium'
        
        logger.info(f"✅ Admin toggled user {user_id}: {current_status} → {new_status}")
        
        return {
            "success": True,
            "user_id": user_id,
            "previous_status": "premium" if current_status else "free",
            "new_status": new_status,
            "message": f"User {user_id} is now {new_status.upper()}"
        }
    
    except Exception as e:
        logger.error(f"Error toggling user premium: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
