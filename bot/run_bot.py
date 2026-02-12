#!/usr/bin/env python
"""
Script to run the Telegram bot independently.
Run with: poetry run python bot/run_bot.py
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from dotenv import load_dotenv
from bot.handlers import CodeforcesBotHandlers

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def main():
    """Run the Telegram bot."""
    bot = CodeforcesBotHandlers()
    bot.run()

if __name__ == '__main__':
    main()
