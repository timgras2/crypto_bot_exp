#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Working Telegram Authentication Script

Uses temp directory to avoid OneDrive sync issues.
"""

import sys
import os
import asyncio
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

async def setup_telegram_auth():
    """Setup Telegram authentication in temp directory."""
    # Load environment variables
    load_dotenv()
    
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    phone = os.getenv('TELEGRAM_PHONE_NUMBER')
    
    if not all([api_id, api_hash, phone]):
        print("ERROR: Missing Telegram credentials in .env file")
        return False
    
    print("Telegram Authentication - Working Version")
    print("=" * 45)
    print(f"API ID: {api_id}")
    print(f"Phone: {phone}")
    print()
    
    # Use temp directory (same as collector will use)
    temp_dir = Path(tempfile.gettempdir()) / 'crypto_bot'
    temp_dir.mkdir(exist_ok=True)
    session_path = temp_dir / 'crypto_sentiment_session'
    
    print(f"Session location: {session_path}")
    print("(This avoids OneDrive sync conflicts)")
    print()
    
    client = TelegramClient(str(session_path), api_id, api_hash)
    
    try:
        print("Connecting to Telegram...")
        await client.start(phone=phone)
        
        # Check if we need 2FA
        if not await client.is_user_authorized():
            print("ERROR: Authentication failed")
            return False
        
        # Get user info
        me = await client.get_me()
        print(f"SUCCESS: Authenticated as {me.first_name}")
        
        # Test accessing a crypto channel
        try:
            entity = await client.get_entity('@binance')
            print(f"SUCCESS: Can access @binance ({entity.title})")
        except Exception as e:
            print(f"Warning: Cannot access @binance: {e}")
        
        await client.disconnect()
        
        # Verify session file was created
        session_file = Path(f"{session_path}.session")
        if session_file.exists():
            size = session_file.stat().st_size
            print(f"SUCCESS: Session file created ({size} bytes)")
            return True
        else:
            print("ERROR: Session file not created")
            return False
            
    except SessionPasswordNeededError:
        print("Two-factor authentication detected.")
        password = input("Enter your 2FA password: ")
        try:
            await client.sign_in(password=password)
            me = await client.get_me()
            print(f"SUCCESS: 2FA authentication as {me.first_name}")
            await client.disconnect()
            return True
        except Exception as e:
            print(f"ERROR: 2FA failed: {e}")
            await client.disconnect()
            return False
            
    except Exception as e:
        print(f"ERROR: Authentication failed: {e}")
        try:
            await client.disconnect()
        except:
            pass
        return False

def main():
    """Main function."""
    print("Telegram Authentication Setup")
    print("This version fixes the OneDrive database conflict issue.")
    print()
    
    try:
        success = asyncio.run(setup_telegram_auth())
        
        if success:
            print()
            print("=" * 45)
            print("SETUP COMPLETE!")
            print("Telegram sentiment collection is now enabled.")
            print()
            print("The session file is stored in:")
            temp_dir = Path(tempfile.gettempdir()) / 'crypto_bot'
            print(f"  {temp_dir}")
            print()
            print("This location avoids OneDrive sync conflicts.")
        else:
            print()
            print("=" * 45)
            print("SETUP FAILED!")
            print("Check error messages above.")
            
    except KeyboardInterrupt:
        print("Setup cancelled.")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()