#!/usr/bin/env python3
"""
Auto-integration script for Feature 4: AI Recommendations
This script applies the 3 required modifications to bot_webhook.py
"""

import sys
import os

def integrate_feature4():
    """Apply Feature 4 modifications to bot_webhook.py"""
    
    filepath = 'backend/bot_webhook.py'
    
    if not os.path.exists(filepath):
        print(f"❌ Error: {filepath} not found")
        return False
    
    print("🔧 Integrating Feature 4: AI Recommendations")
    print("="*60)
    
    # Read original file
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Backup
    with open(filepath + '.backup', 'w') as f:
        f.write(content)
    print("✅ Backup created: bot_webhook.py.backup")
    
    # Modification 1: Add import
    print("\n1️⃣  Adding import...")
    content = content.replace(
        '''try:
    from article_scraper import extract_article, extract_urls
except ImportError:
    def extract_article(url): return None
    def extract_urls(text): return []

load_dotenv()''',
        '''try:
    from article_scraper import extract_article, extract_urls
except ImportError:
    def extract_article(url): return None
    def extract_urls(text): return []

# Feature 4: AI Recommendations handler
try:
    from backend.recommend_handler import recommend_command as recommend_handler_fn
except ImportError:
    from recommend_handler import recommend_command as recommend_handler_fn

load_dotenv()'''
    )
    print("✅ Import added")
    
    # Modification 2: Add wrapper function
    print("\n2️⃣  Adding wrapper function...")
    content = content.replace(
        '''        await update.message.reply_text("❌ Error removing alert.", parse_mode='Markdown')

# ===== MESSAGE HANDLERS =====''',
        '''        await update.message.reply_text("❌ Error removing alert.", parse_mode='Markdown')

# ===== AI RECOMMENDATIONS COMMAND (FEATURE 4) =====

async def recommend_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Wrapper for AI recommendations handler."""
    await recommend_handler_fn(
        update, 
        context, 
        DB_AVAILABLE, 
        portfolio_manager, 
        is_symbol_supported, 
        format_price
    )

# ===== MESSAGE HANDLERS ====='''
    )
    print("✅ Wrapper function added")
    
    # Modification 3: Add handler registration
    print("\n3️⃣  Adding handler registration...")
    content = content.replace(
        '''    application.add_handler(CommandHandler("removealert", removealert_command))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))''',
        '''    application.add_handler(CommandHandler("removealert", removealert_command))
    
    # AI Recommendations (Feature 4)
    application.add_handler(CommandHandler("recommend", recommend_command))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))'''
    )
    print("✅ Handler registered")
    
    # Write modified file
    with open(filepath, 'w') as f:
        f.write(content)
    
    print("\n" + "="*60)
    print("✅ Feature 4 integration COMPLETE!")
    print("="*60)
    print("\n🚀 Next steps:")
    print("1. git add backend/bot_webhook.py")
    print("2. git commit -m '🔌 Integrate /recommend command handler'")
    print("3. git push origin feature/ai-recommendations")
    print("4. Merge PR #1 on GitHub")
    print("5. Test /recommend on Telegram after Railway redeploys")
    print("\n🎯 Feature 4: AI Recommendations is ready!")
    
    return True

if __name__ == '__main__':
    success = integrate_feature4()
    sys.exit(0 if success else 1)
