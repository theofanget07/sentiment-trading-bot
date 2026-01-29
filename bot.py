#!/usr/bin/env python3
"""
Root bot.py for Railway deployment
Imports and runs the actual bot from backend/
"""
import sys
import os

# Add backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

if __name__ == "__main__":
    import bot as backend_bot
    backend_bot.main()
