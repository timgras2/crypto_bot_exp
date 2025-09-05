#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Authentication Setup Script

Run this script once to authenticate with Telegram and create a session file.
After this, the sentiment analyzer will use the session automatically.
"""

import sys
import os
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

# Fix Unicode encoding on Windows
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, OSError):
        pass

async def setup_telegram_auth():
    """Setup Telegram authentication interactively."""
    # Load environment variables
    load_dotenv()
    
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    phone = os.getenv('TELEGRAM_PHONE_NUMBER')
    
    if not all([api_id, api_hash, phone]):
        print("ERROR: Missing Telegram credentials in .env file:")
        print("- TELEGRAM_API_ID")
        print("- TELEGRAM_API_HASH") 
        print("- TELEGRAM_PHONE_NUMBER")
        return False
    
    print("Telegram Authentication Setup")
    print("=" * 40)
    print(f"API ID: {api_id}")
    print(f"Phone: {phone}")
    print()
    
    # Use temp directory to avoid OneDrive sync issues (same as collector)
    import tempfile
    from pathlib import Path
    temp_dir = Path(tempfile.gettempdir()) / 'crypto_bot'
    temp_dir.mkdir(exist_ok=True)
    session_name = str(temp_dir / 'crypto_sentiment_session')
    
    client = TelegramClient(session_name, api_id, api_hash)
    
    try:
        print("Connecting to Telegram...")
        await client.start(phone=phone)
        
        # Check if 2FA is required
        if not await client.is_user_authorized():
            print("ERROR: Authentication failed")
            return False
        
        # Get user info
        me = await client.get_me()
        print(f"SUCCESS: Authenticated as {me.first_name}")
        print(f"Session file created: {session_name}.session")
        print()
        print("You can now use Telegram sentiment collection!")
        
        # Test accessing a crypto channel
        try:
            entity = await client.get_entity('@binance')
            print(f"Test: Successfully accessed @binance ({entity.title})")
        except Exception as e:
            print(f"Warning: Could not access @binance: {e}")
        
        return True
        
    except SessionPasswordNeededError:
        print("ERROR: Two-factor authentication (2FA) is enabled on your account.")
        print("You'll need to provide your 2FA password.")
        
        password = input("Enter your 2FA password: ")
        try:
            await client.sign_in(password=password)
            me = await client.get_me()
            print(f"SUCCESS: Authenticated as {me.first_name}")
            return True
        except Exception as e:
            print(f"ERROR: 2FA authentication failed: {e}")
            return False
            
    except Exception as e:
        print(f"ERROR: Authentication failed: {e}")
        return False
        
    finally:
        await client.disconnect()

def main():
    """Main function."""
    print("Setting up Telegram authentication for crypto sentiment analysis...")
    print()
    
    try:
        success = asyncio.run(setup_telegram_auth())
        
        if success:
            print()
            print("SETUP COMPLETE!")
            print("The sentiment analyzer will now use Telegram data.")
        else:
            print()
            print("SETUP FAILED!")
            print("Telegram collection will be skipped until authentication succeeds.")
            
    except KeyboardInterrupt:
        print("\nSetup cancelled by user.")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()