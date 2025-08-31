#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for Telegram collector connection and functionality.

This script tests the Telegram API connection and basic functionality
without running the full trading bot.
"""

import sys
import os
import logging
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Fix Unicode encoding on Windows
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, OSError):
        pass

def test_telegram_connection():
    """Test Telegram API connection and collector functionality."""
    try:
        print("=" * 60)
        print("🤖 TESTING TELEGRAM COLLECTOR CONNECTION")
        print("=" * 60)
        
        # Import config and collector
        from config import load_config
        from sentiment.telegram_collector import TelegramCollector
        
        # Load configuration
        configs = load_config()
        sentiment_config = configs[4]  # Fifth element is sentiment config
        
        # Check if Telegram is configured
        telegram_configured = all([
            sentiment_config.TELEGRAM_API_ID,
            sentiment_config.TELEGRAM_API_HASH,
            sentiment_config.TELEGRAM_PHONE_NUMBER
        ])
        
        if not telegram_configured:
            print("\n❌ TELEGRAM NOT CONFIGURED")
            print("Please set the following environment variables:")
            print("- TELEGRAM_API_ID")
            print("- TELEGRAM_API_HASH") 
            print("- TELEGRAM_PHONE_NUMBER")
            print("\nGet these credentials from https://my.telegram.org/")
            return False
        
        print(f"✅ Configuration loaded successfully")
        print(f"   API ID: {sentiment_config.TELEGRAM_API_ID[:8]}...")
        print(f"   Phone: {sentiment_config.TELEGRAM_PHONE_NUMBER[:3]}***")
        
        # Initialize collector
        print(f"\n📱 Initializing Telegram collector...")
        collector = TelegramCollector(sentiment_config)
        
        if not collector.client:
            print("❌ Failed to initialize Telegram client")
            return False
        
        print("✅ Telegram client initialized")
        
        # Test channel info retrieval
        print(f"\n📊 Getting channel information...")
        try:
            channel_info = collector.get_channel_info()
            print(f"✅ Retrieved info for {len(channel_info)} channels")
            
            for channel, info in list(channel_info.items())[:3]:  # Show first 3
                print(f"   • {channel}: {info.get('type', 'Unknown')}")
        
        except Exception as e:
            print(f"⚠️ Channel info retrieval failed: {e}")
        
        # Test message collection for BTC
        print(f"\n💰 Testing message collection for BTC...")
        try:
            btc_messages = collector.collect_for_symbol('BTC', hours_back=1)
            print(f"✅ Collected {len(btc_messages)} BTC-related messages")
            
            if btc_messages:
                # Show sample message
                sample = btc_messages[0]
                print(f"\n📝 Sample message:")
                print(f"   Source: {sample.get('source', 'Unknown')}")
                print(f"   Text: {sample.get('text', '')[:100]}...")
                print(f"   Timestamp: {sample.get('timestamp', 'Unknown')}")
            else:
                print("ℹ️ No BTC messages found in the last hour")
        
        except Exception as e:
            print(f"❌ Message collection failed: {e}")
            return False
        
        # Test general crypto sentiment
        print(f"\n🌐 Testing general crypto sentiment collection...")
        try:
            general_messages = collector.collect_general_crypto_sentiment(hours_back=1)
            print(f"✅ Collected {len(general_messages)} general crypto messages")
            
        except Exception as e:
            print(f"⚠️ General sentiment collection failed: {e}")
        
        print(f"\n🎉 TELEGRAM COLLECTOR TEST COMPLETED!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you have installed all requirements:")
        print("pip install -r requirements.txt")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    """Main test function."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print(f"🔧 Telegram Collector Test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python version: {sys.version}")
    
    success = test_telegram_connection()
    
    if success:
        print(f"\n✅ ALL TESTS PASSED!")
        print(f"Your Telegram collector is ready for sentiment analysis.")
    else:
        print(f"\n❌ SOME TESTS FAILED!")
        print(f"Please check your configuration and try again.")
    
    return 0 if success else 1

if __name__ == '__main__':
    exit(main())