#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple Reddit API connection test.
This will verify your Reddit credentials are working correctly.
"""

import sys
import os
from pathlib import Path

# Fix Unicode encoding on Windows
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, OSError):
        pass

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_reddit_credentials():
    """Test Reddit API credentials directly."""
    print("🔍 REDDIT API CONNECTION TEST")
    print("=" * 50)
    
    # Check if credentials are loaded
    reddit_creds = {
        'REDDIT_CLIENT_ID': os.getenv('REDDIT_CLIENT_ID'),
        'REDDIT_CLIENT_SECRET': os.getenv('REDDIT_CLIENT_SECRET'), 
        'REDDIT_USERNAME': os.getenv('REDDIT_USERNAME'),
        'REDDIT_PASSWORD': os.getenv('REDDIT_PASSWORD')
    }
    
    print("1. Checking environment variables...")
    missing_creds = []
    for key, value in reddit_creds.items():
        if value:
            # Show first 4 characters for verification
            display_value = f"{value[:4]}***" if len(value) > 4 else "***"
            print(f"   ✅ {key}: {display_value}")
        else:
            print(f"   ❌ {key}: Missing")
            missing_creds.append(key)
    
    if missing_creds:
        print(f"\n❌ Missing credentials: {missing_creds}")
        print("Please check your .env file contains all Reddit credentials.")
        assert False, f"Missing Reddit credentials: {missing_creds}"
    
    print("\n2. Testing Reddit API connection...")
    
    try:
        import praw
        
        # Initialize Reddit client
        reddit = praw.Reddit(
            client_id=reddit_creds['REDDIT_CLIENT_ID'],
            client_secret=reddit_creds['REDDIT_CLIENT_SECRET'],
            user_agent="crypto_sentiment_bot/1.0 by " + reddit_creds['REDDIT_USERNAME'],
            username=reddit_creds['REDDIT_USERNAME'],
            password=reddit_creds['REDDIT_PASSWORD']
        )
        
        # Test authentication
        print("   Authenticating with Reddit...")
        user = reddit.user.me()
        print(f"   ✅ Successfully authenticated as: {user}")
        
        # Test basic API call
        print("   Testing subreddit access...")
        subreddit = reddit.subreddit('CryptoCurrency')
        print(f"   ✅ Accessed r/CryptoCurrency - {subreddit.subscribers:,} subscribers")
        
        # Test getting recent posts
        print("   Testing post retrieval...")
        posts = list(subreddit.new(limit=5))
        print(f"   ✅ Retrieved {len(posts)} recent posts")
        
        if posts:
            latest_post = posts[0]
            print(f"   📋 Latest post: \"{latest_post.title[:50]}...\"")
        
        print("\n🎉 SUCCESS: Reddit API connection is working perfectly!")
        return  # Test passed
        
    except Exception as e:
        print(f"   ❌ Reddit API Error: {e}")
        
        # Common error diagnosis
        error_str = str(e).lower()
        if "401" in error_str or "unauthorized" in error_str:
            print("\n🚨 DIAGNOSIS: Authentication failed")
            print("   - Check your Reddit username and password are correct")
            print("   - Verify your Client ID and Secret from https://www.reddit.com/prefs/apps/")
            print("   - Make sure your Reddit app type is set to 'script'")
        elif "403" in error_str or "forbidden" in error_str:
            print("\n🚨 DIAGNOSIS: Access forbidden")
            print("   - Your Reddit account may need verification")
            print("   - Check if your account has any restrictions")
        elif "rate" in error_str or "429" in error_str:
            print("\n🚨 DIAGNOSIS: Rate limited")
            print("   - Wait a few minutes and try again")
        else:
            print("\n🚨 DIAGNOSIS: Other error")
            print("   - Check your internet connection")
            print("   - Verify Reddit is accessible")
        
        assert False, "Reddit test failed"

def test_sentiment_collection():
    """Test collecting sentiment for a real cryptocurrency."""
    print("\n" + "="*50)
    print("🎯 REAL SENTIMENT COLLECTION TEST")
    print("="*50)
    
    try:
        # Test with our data collector
        from sentiment.data_collector import MultiSourceDataCollector
        
        # Create mock config with actual credentials
        class Config:
            def __init__(self):
                self.REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID')
                self.REDDIT_CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET')
                self.REDDIT_USERNAME = os.getenv('REDDIT_USERNAME')
                self.REDDIT_PASSWORD = os.getenv('REDDIT_PASSWORD')
        
        config = Config()
        collector = MultiSourceDataCollector(config)
        
        print("1. Initialized sentiment collector")
        print(f"   Available sources: {list(collector.collectors.keys())}")
        
        # Test with Bitcoin (should have plenty of discussions)
        print("\n2. Collecting sentiment for BTC...")
        print("   (This may take 10-30 seconds)")
        
        result = collector.collect_for_symbol("BTC", hours_back=12)
        
        print(f"\n3. Results for BTC:")
        print(f"   📊 Total posts found: {result['total_posts']}")
        print(f"   ✅ Processed posts: {result['processed_posts']}")
        print(f"   🗑️ Filtered spam: {result['filtered_spam']}")
        print(f"   💭 Sentiment score: {result['aggregated_sentiment']:.3f}")
        print(f"   🎯 Confidence: {result['confidence']:.3f}")
        print(f"   💪 Strength: {result['sentiment_strength']}")
        print(f"   🚨 Pump detected: {result['pump_detected']}")
        
        # Show source breakdown
        if result['source_breakdown']:
            print(f"\n   📱 Source breakdown:")
            for source, data in result['source_breakdown'].items():
                print(f"     {source}: {data['count']} posts, avg sentiment: {data['avg_sentiment']:.3f}")
        
        if result['total_posts'] > 0:
            print("\n🎉 SUCCESS: Sentiment collection is working!")
            print("Your bot can now analyze crypto sentiment from Reddit!")
        else:
            print("\n⚠️ No posts found for BTC (unusual but possible)")
            print("This might be due to timing or Reddit API issues")
        
        # Test passes if collector runs without error, regardless of post count
        print("✅ Sentiment collection test completed successfully")
        
    except Exception as e:
        print(f"❌ Sentiment collection error: {e}")
        import traceback
        traceback.print_exc()
        assert False, "Reddit test failed"

def main():
    """Run Reddit connection tests."""
    try:
        print("🚀 Testing your Reddit API setup...\n")
        
        # Test basic credentials and connection
        connection_ok = test_reddit_credentials()
        
        if connection_ok:
            # Test actual sentiment collection
            sentiment_ok = test_sentiment_collection()
            
            if sentiment_ok:
                print("\n" + "="*50)
                print("🎉 ALL TESTS PASSED!")
                print("="*50)
                print("✅ Reddit API credentials are working")
                print("✅ Sentiment analysis system is ready")
                print("✅ Your bot can now collect crypto sentiment!")
                print("\nNext steps:")
                print("1. Your sentiment system is ready to use")
                print("2. Start your trading bot to see sentiment in action")
                print("3. Monitor logs for sentiment-influenced trades")
            else:
                print("\n⚠️ Reddit connection works, but sentiment collection had issues")
        else:
            print("\n❌ Reddit API connection failed")
            print("Please fix the credentials and try again")
            
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()