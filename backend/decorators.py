#!/usr/bin/env python3
"""
Decorators for CryptoSentinel AI - Feature Access Control.

Provides decorators to protect Telegram commands based on user tier:
- @premium_required: Blocks free users from premium features
- @check_rate_limit: Applies daily rate limits for free users
- @check_position_limit: Enforces position limits for free users

Author: Theo Fanget
Date: 08 February 2026
"""
import logging
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes

# Setup logging
logger = logging.getLogger(__name__)


def premium_required(func):
    """Decorator to restrict command to premium users only.
    
    Usage:
        @premium_required
        async def setalert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            # This will only execute for premium users
            pass
    
    Args:
        func: Async function to wrap
    
    Returns:
        Wrapped function that checks premium status
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        # Get tier_manager from bot_data
        tier_manager = context.bot_data.get('tier_manager')
        
        if not tier_manager:
            logger.error("tier_manager not found in bot_data")
            await update.message.reply_text(
                "❌ Erreur système. Veuillez réessayer."
            )
            return
        
        # Check if user is premium
        if not tier_manager.is_premium(user_id):
            await update.message.reply_text(
                "🔒 **Feature Premium**\n\n"
                "Cette fonctionnalité est réservée aux membres Premium.\n\n"
                "✨ **Passe Premium (9€/mois)** pour débloquer:\n"
                "• Alertes prix TP/SL illimitées\n"
                "• Morning Briefing quotidien (8h00)\n"
                "• AI Recommendations personnalisées\n"
                "• Trade of the Day exclusif\n"
                "• Analyses illimitées\n"
                "• Positions portfolio illimitées\n\n"
                "👉 Tape /subscribe pour souscrire",
                parse_mode='Markdown'
            )
            logger.info(f"❌ Premium feature blocked for free user {user_id} in {func.__name__}")
            return
        
        # User is premium, execute the function
        logger.info(f"✅ Premium feature accessed by user {user_id} in {func.__name__}")
        return await func(update, context)
    
    return wrapper


def check_rate_limit(func):
    """Decorator to apply daily rate limit for free users (5 analyses/day).
    
    Usage:
        @check_rate_limit
        async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            # This will check rate limit for free users
            pass
    
    Args:
        func: Async function to wrap
    
    Returns:
        Wrapped function that checks rate limits
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        # Get tier_manager from bot_data
        tier_manager = context.bot_data.get('tier_manager')
        
        if not tier_manager:
            logger.error("tier_manager not found in bot_data")
            await update.message.reply_text(
                "❌ Erreur système. Veuillez réessayer."
            )
            return
        
        # Check if user can analyze
        can_proceed, message = tier_manager.can_analyze(user_id)
        
        if not can_proceed:
            # Limit reached
            await update.message.reply_text(message, parse_mode='Markdown')
            logger.info(f"❌ Rate limit reached for user {user_id} in {func.__name__}")
            return
        
        # Display counter for free users (informational)
        if message and tier_manager.is_free(user_id):
            # Send counter message (non-blocking)
            try:
                await update.message.reply_text(message)
            except Exception as e:
                logger.warning(f"Could not send counter message: {e}")
        
        # Execute the function
        return await func(update, context)
    
    return wrapper


def check_position_limit(func):
    """Decorator to check position limit for free users (3 max).
    
    Usage:
        @check_position_limit
        async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            # This will check position limit for free users
            pass
    
    Args:
        func: Async function to wrap
    
    Returns:
        Wrapped function that checks position limits
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        # Get tier_manager from bot_data
        tier_manager = context.bot_data.get('tier_manager')
        
        if not tier_manager:
            logger.error("tier_manager not found in bot_data")
            await update.message.reply_text(
                "❌ Erreur système. Veuillez réessayer."
            )
            return
        
        # Get portfolio_manager from bot_data
        portfolio_manager = context.bot_data.get('portfolio_manager')
        
        if not portfolio_manager:
            logger.error("portfolio_manager not found in bot_data")
            await update.message.reply_text(
                "❌ Erreur système. Veuillez réessayer."
            )
            return
        
        # Get current portfolio
        try:
            portfolio = portfolio_manager.get_portfolio(
                user_id,
                update.effective_user.username
            )
            current_positions = len(portfolio.get('positions', []))
        except Exception as e:
            logger.error(f"Error getting portfolio: {e}")
            current_positions = 0
        
        # Check if user can add position
        can_add, message = tier_manager.can_add_position(user_id, current_positions)
        
        if not can_add:
            # Limit reached
            await update.message.reply_text(message, parse_mode='Markdown')
            logger.info(f"❌ Position limit reached for user {user_id} ({current_positions}/3)")
            return
        
        # Execute the function
        return await func(update, context)
    
    return wrapper


def log_command_usage(func):
    """Decorator to log command usage for analytics.
    
    Usage:
        @log_command_usage
        async def any_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            # This will log command usage
            pass
    
    Args:
        func: Async function to wrap
    
    Returns:
        Wrapped function that logs usage
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        username = update.effective_user.username
        command = func.__name__.replace('_command', '').replace('_handler', '')
        
        # Get tier_manager
        tier_manager = context.bot_data.get('tier_manager')
        tier = tier_manager.get_user_tier(user_id) if tier_manager else 'unknown'
        
        logger.info(
            f"📊 Command usage: /{command} by user {user_id} (@{username}) [tier: {tier}]"
        )
        
        # Execute the function
        return await func(update, context)
    
    return wrapper


# ===== COMBINED DECORATORS =====

def premium_with_logging(func):
    """Combined decorator: premium_required + log_command_usage.
    
    Usage:
        @premium_with_logging
        async def setalert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            pass
    """
    return log_command_usage(premium_required(func))


def rate_limited_with_logging(func):
    """Combined decorator: check_rate_limit + log_command_usage.
    
    Usage:
        @rate_limited_with_logging
        async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            pass
    """
    return log_command_usage(check_rate_limit(func))


if __name__ == "__main__":
    # Test script
    print("="*60)
    print("DECORATORS TEST")
    print("="*60)
    
    print("\nAvailable decorators:")
    print("  1. @premium_required - Blocks free users")
    print("  2. @check_rate_limit - 5 analyses/day for free")
    print("  3. @check_position_limit - 3 positions max for free")
    print("  4. @log_command_usage - Logs all commands")
    print("  5. @premium_with_logging - Combined premium + logging")
    print("  6. @rate_limited_with_logging - Combined rate limit + logging")
    
    print("\nUsage examples in bot_webhook.py:")
    print("""
# Premium-only commands
@premium_required
async def setalert_command(update, context):
    pass

@premium_required
async def recommend_command(update, context):
    pass

# Rate-limited commands (free users)
@check_rate_limit
async def analyze_command(update, context):
    pass

# Position-limited commands (free users)
@check_position_limit
async def add_command(update, context):
    pass
    """)
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)
