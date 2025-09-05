#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Diagnostic Script - Find and fix database issues
"""

import sys
import os
import sqlite3
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from dotenv import load_dotenv

def diagnose_telegram_issue():
    """Diagnose Telegram session file issues."""
    print("Telegram Diagnostic Tool")
    print("=" * 40)
    
    # Load environment
    load_dotenv()
    
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    phone = os.getenv('TELEGRAM_PHONE_NUMBER')
    
    print(f"✓ API ID: {api_id}")
    print(f"✓ API Hash: {api_hash[:10]}...")
    print(f"✓ Phone: {phone}")
    print()
    
    # Check session file
    scripts_dir = Path(__file__).parent
    session_file = scripts_dir / "crypto_sentiment_session.session"
    
    print("Session File Analysis:")
    print(f"Path: {session_file}")
    
    if session_file.exists():
        size = session_file.stat().st_size
        print(f"✓ File exists: {size} bytes")
        
        # Try to open as SQLite database
        try:
            conn = sqlite3.connect(str(session_file))
            cursor = conn.cursor()
            
            # Check if it has the expected tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            print(f"✓ SQLite database: {len(tables)} tables")
            for table in tables:
                print(f"  - {table[0]}")
                
            # Check if sessions table has data
            try:
                cursor.execute("SELECT COUNT(*) FROM sessions;")
                session_count = cursor.fetchone()[0]
                print(f"✓ Sessions table: {session_count} entries")
            except:
                print("✗ No sessions table or corrupted")
                
            conn.close()
            
        except sqlite3.DatabaseError as e:
            print(f"✗ SQLite error: {e}")
            print("  → Session file is corrupted")
            
            # Offer to delete corrupted file
            response = input("\nDelete corrupted session file? (y/n): ")
            if response.lower() == 'y':
                session_file.unlink()
                print("✓ Corrupted session file deleted")
                return "deleted"
            else:
                print("✗ Keeping corrupted file")
                return "corrupted"
                
        except Exception as e:
            print(f"✗ Unexpected error: {e}")
            return "error"
            
    else:
        print("✗ Session file doesn't exist")
        return "missing"
    
    return "ok"

def create_fresh_session():
    """Create a fresh session using a simpler approach."""
    print("\nCreating Fresh Session")
    print("=" * 30)
    
    # Move to user's temp directory to avoid OneDrive sync issues
    import tempfile
    temp_dir = Path(tempfile.gettempdir())
    temp_session = temp_dir / "crypto_temp_session"
    
    print(f"Using temporary location: {temp_session}")
    
    load_dotenv()
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    phone = os.getenv('TELEGRAM_PHONE_NUMBER')
    
    try:
        from telethon import TelegramClient
        import asyncio
        
        async def auth():
            client = TelegramClient(str(temp_session), api_id, api_hash)
            await client.start(phone=phone)
            
            if await client.is_user_authorized():
                me = await client.get_me()
                print(f"✓ Authenticated as: {me.first_name}")
                
                await client.disconnect()
                
                # Move to final location
                scripts_dir = Path(__file__).parent
                final_session = scripts_dir / "crypto_sentiment_session.session"
                temp_session_file = Path(f"{temp_session}.session")
                
                if temp_session_file.exists():
                    import shutil
                    if final_session.exists():
                        final_session.unlink()
                    shutil.copy2(temp_session_file, final_session)
                    temp_session_file.unlink()  # Clean up temp file
                    print(f"✓ Session moved to: {final_session}")
                    return True
                else:
                    print("✗ Temp session file not created")
                    return False
            else:
                print("✗ Authentication failed")
                await client.disconnect()
                return False
        
        return asyncio.run(auth())
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def main():
    """Main diagnostic function."""
    try:
        result = diagnose_telegram_issue()
        
        if result in ["corrupted", "missing", "deleted"]:
            print("\nWould you like to create a fresh session? (y/n): ", end="")
            response = input()
            
            if response.lower() == 'y':
                if create_fresh_session():
                    print("\n✓ SUCCESS: Fresh session created!")
                    print("Telegram should now work with the sentiment analyzer.")
                else:
                    print("\n✗ FAILED: Could not create fresh session")
                    print("You may need to run the setup manually.")
            else:
                print("Session creation skipped.")
        elif result == "ok":
            print("\n✓ Session file appears to be valid")
            print("If you're still getting errors, the issue might be elsewhere.")
        
    except KeyboardInterrupt:
        print("\nDiagnostic cancelled.")
    except Exception as e:
        print(f"\nUnexpected error: {e}")

if __name__ == "__main__":
    main()