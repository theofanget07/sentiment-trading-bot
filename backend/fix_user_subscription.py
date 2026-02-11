#!/usr/bin/env python3
"""
Fix User Subscription Script

Cleans invalid Stripe subscription_id from Redis for users
who are Premium but have invalid/expired subscription IDs.

Usage:
    python fix_user_subscription.py <telegram_user_id>

Example:
    python fix_user_subscription.py 123456789
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Import Redis storage
try:
    from backend import redis_storage
except ImportError:
    import redis_storage

def fix_user_subscription(user_id: int):
    """Clean invalid Stripe data for a user.
    
    Args:
        user_id: Telegram user ID
    """
    print(f"\n🔧 Fixing subscription for user {user_id}...")
    
    # Check if Redis is available
    if not redis_storage.test_connection():
        print("❌ Redis connection failed")
        return False
    
    try:
        # Get current status
        subscription_status = redis_storage.redis_client.get(f"user:{user_id}:subscription_status")
        subscription_id = redis_storage.redis_client.get(f"user:{user_id}:subscription_id")
        customer_id = redis_storage.redis_client.get(f"user:{user_id}:stripe_customer_id")
        
        print(f"\n📊 Current Status:")
        print(f"  • Subscription status: {subscription_status or 'Not set'}")
        print(f"  • Subscription ID: {subscription_id or 'Not set'}")
        print(f"  • Customer ID: {customer_id or 'Not set'}")
        
        # Clean up Stripe data
        if subscription_id:
            redis_storage.redis_client.delete(f"user:{user_id}:subscription_id")
            print(f"\n🧹 Deleted subscription_id: {subscription_id}")
        
        if customer_id:
            redis_storage.redis_client.delete(f"user:{user_id}:stripe_customer_id")
            print(f"🧹 Deleted customer_id: {customer_id}")
        
        # Ensure user is still Premium (manual)
        if subscription_status == 'premium':
            print(f"\n✅ User remains Premium (manual access)")
        else:
            # Set to Premium if not already
            redis_storage.redis_client.set(f"user:{user_id}:subscription_status", 'premium')
            print(f"\n✅ User set to Premium (manual access)")
        
        print(f"\n✨ Fix complete! User {user_id} now has clean Premium status.")
        print(f"\n📱 User can now run /manage command successfully.")
        
        return True
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python fix_user_subscription.py <telegram_user_id>")
        print("Example: python fix_user_subscription.py 123456789")
        sys.exit(1)
    
    try:
        user_id = int(sys.argv[1])
        success = fix_user_subscription(user_id)
        sys.exit(0 if success else 1)
    except ValueError:
        print("❌ Error: User ID must be a number")
        sys.exit(1)
