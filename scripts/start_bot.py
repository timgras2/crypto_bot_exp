#!/usr/bin/env python3
"""
Crypto Trading Bot Launcher
Simple script to start the bot with proper error handling and logging setup.
"""

import sys
import os
from pathlib import Path

def main():
    """Launch the crypto trading bot with safety checks."""
    
    # Add src directory to path
    src_path = Path(__file__).parent.parent / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    
    # Check if .env file exists
    env_file = Path(__file__).parent.parent / ".env"
    if not env_file.exists():
        print("ERROR: .env file not found!")
        print("Please copy .env.example to .env and configure your API credentials")
        print("Command: cp .env.example .env")
        return 1
    
    # Check if logs directory exists, create if not
    logs_dir = Path(__file__).parent.parent / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    print("Starting Crypto Trading Bot...")
    print("WARNING: This bot trades with REAL MONEY!")
    print("Check your .env file for trading parameters")
    print("Press Ctrl+C to stop the bot safely")
    print("-" * 50)
    
    try:
        # Import and run the main bot
        from main import main as run_bot
        run_bot()
        
    except KeyboardInterrupt:
        print("\nBot stopped by user")
        return 0
        
    except ImportError as e:
        print(f"ERROR: Failed to import bot components: {e}")
        print("Please ensure all dependencies are installed: pip install -r requirements.txt")
        return 1
        
    except Exception as e:
        print(f"ERROR: Bot crashed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)