#!/usr/bin/env python3
"""
Main entry point for Railway deployment
"""

import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the bot
from telegram_bot_simple import SimpleTelegramBot

if __name__ == "__main__":
    bot = SimpleTelegramBot()
    bot.run()

