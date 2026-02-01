#!/usr/bin/env python3
"""
Webhook Reset Script for Telegram Bot

Forces Telegram to reconfigure the webhook URL.
Useful when Railway redeploys with a new container.
"""

import os
import sys
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

if not TELEGRAM_BOT_TOKEN or not WEBHOOK_URL:
    print("❌ Error: TELEGRAM_BOT_TOKEN and WEBHOOK_URL must be set")
    sys.exit(1)

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

def delete_webhook():
    """Delete existing webhook"""
    print("🗑️  Deleting existing webhook...")
    response = requests.post(f"{BASE_URL}/deleteWebhook")
    result = response.json()
    
    if result.get('ok'):
        print("✅ Webhook deleted successfully")
        return True
    else:
        print(f"❌ Failed to delete webhook: {result}")
        return False

def set_webhook():
    """Set new webhook URL"""
    webhook_endpoint = f"{WEBHOOK_URL}/{TELEGRAM_BOT_TOKEN}"
    print(f"🔧 Setting webhook to: {webhook_endpoint}")
    
    response = requests.post(
        f"{BASE_URL}/setWebhook",
        json={"url": webhook_endpoint}
    )
    result = response.json()
    
    if result.get('ok'):
        print("✅ Webhook set successfully")
        return True
    else:
        print(f"❌ Failed to set webhook: {result}")
        return False

def get_webhook_info():
    """Get current webhook info"""
    print("\n📊 Current webhook info:")
    response = requests.get(f"{BASE_URL}/getWebhookInfo")
    result = response.json()
    
    if result.get('ok'):
        info = result.get('result', {})
        print(f"  URL: {info.get('url', 'Not set')}")
        print(f"  Has custom certificate: {info.get('has_custom_certificate', False)}")
        print(f"  Pending update count: {info.get('pending_update_count', 0)}")
        print(f"  Max connections: {info.get('max_connections', 'N/A')}")
        
        last_error = info.get('last_error_message')
        if last_error:
            print(f"  ⚠️  Last error: {last_error}")
            print(f"  Last error date: {info.get('last_error_date', 'N/A')}")
        
        return True
    else:
        print(f"❌ Failed to get webhook info: {result}")
        return False

def main():
    print("🤖 Telegram Webhook Reset Script\n")
    print("="*50)
    
    # Step 1: Get current status
    get_webhook_info()
    
    # Step 2: Delete webhook
    print("\n" + "="*50)
    if not delete_webhook():
        sys.exit(1)
    
    # Step 3: Set new webhook
    print("\n" + "="*50)
    if not set_webhook():
        sys.exit(1)
    
    # Step 4: Verify new configuration
    print("\n" + "="*50)
    get_webhook_info()
    
    print("\n" + "="*50)
    print("✅ Webhook reset complete!")
    print("\n💡 Next steps:")
    print("   1. Test the bot on Telegram with /start")
    print("   2. If it still doesn't work, check Railway Deploy Logs")
    print("   3. Verify WEBHOOK_URL matches Railway public domain\n")

if __name__ == "__main__":
    main()
