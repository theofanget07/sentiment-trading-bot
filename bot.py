#!/usr/bin/env python3
"""
Root bot.py for Railway deployment
Uses webhook version for cloud hosting
"""
import sys
import os

# Add backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

if __name__ == "__main__":
    # Import and run webhook version for Railway
    from bot_webhook import app, setup_application, PORT
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # Setup Telegram application
        setup_application()
        logger.info(f"🚀 Starting bot in webhook mode on port {PORT}")
        
        # Start Flask server
        app.run(host='0.0.0.0', port=PORT)
    except Exception as e:
        logger.error(f"❌ Failed to start bot: {e}")
        raise
