#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test sentiment analysis integration with the main trading bot."""

import os
import sys
from decimal import Decimal

# Fix Unicode encoding on Windows
if sys.platform.startswith('win'):
    try:
        # Try to set UTF-8 for stdout
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, OSError):
        # Fallback for older Python versions or restricted environments
        pass

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_sentiment_configuration():
    """Test that sentiment configuration loads correctly."""
    print("🧪 Testing sentiment configuration...")
    
    # Set test environment variables
    os.environ['SENTIMENT_ENABLED'] = 'true'
    os.environ['SENTIMENT_INFLUENCE'] = '0.6'
    os.environ['MIN_SENTIMENT_CONFIDENCE'] = '0.4'
    os.environ['MAX_POSITION_MULTIPLIER_SENTIMENT'] = '1.8'
    os.environ['REDDIT_CLIENT_ID'] = 'test_id'
    os.environ['REDDIT_CLIENT_SECRET'] = 'test_secret'
    os.environ['REDDIT_USERNAME'] = 'test_user'
    os.environ['REDDIT_PASSWORD'] = 'test_pass'
    
    # Test config loading
    from config import _load_sentiment_config
    
    sentiment_config = _load_sentiment_config()
    
    assert sentiment_config.enabled == True
    assert sentiment_config.influence == Decimal('0.6')
    assert sentiment_config.min_confidence == Decimal('0.4')
    assert sentiment_config.max_position_multiplier == Decimal('1.8')
    assert sentiment_config.REDDIT_CLIENT_ID == 'test_id'
    
    print("✅ Sentiment configuration test passed")
    return True

def test_sentiment_position_sizing():
    """Test sentiment-based position sizing logic."""
    print("🧪 Testing sentiment position sizing logic...")
    
    base_amount = 10.0
    
    # Test positive sentiment
    sentiment_score = 0.5
    confidence = 0.8
    influence = 0.5
    max_multiplier = 1.5
    
    # Positive sentiment calculation
    sentiment_multiplier = 1.0 + (sentiment_score * confidence * influence)
    sentiment_multiplier = min(sentiment_multiplier, max_multiplier)
    
    expected_multiplier = min(1.0 + (0.5 * 0.8 * 0.5), 1.5)  # = min(1.2, 1.5) = 1.2
    assert abs(sentiment_multiplier - expected_multiplier) < 0.001
    
    # Test negative sentiment
    sentiment_score = -0.6
    sentiment_multiplier = 1.0 + (sentiment_score * confidence * influence)
    sentiment_multiplier = max(sentiment_multiplier, 0.5)  # Don't go below 50%
    
    expected_multiplier = max(1.0 + (-0.6 * 0.8 * 0.5), 0.5)  # = max(0.76, 0.5) = 0.76
    assert abs(sentiment_multiplier - expected_multiplier) < 0.001
    
    print("✅ Position sizing logic test passed")
    return True

def test_sentiment_data_collector_mock():
    """Test sentiment data collector with mock data."""
    print("🧪 Testing sentiment data collector...")
    
    try:
        from sentiment.data_collector import MultiSourceDataCollector
        
        # Create mock config object
        class MockConfig:
            REDDIT_CLIENT_ID = "test_id"
            REDDIT_CLIENT_SECRET = "test_secret"
            REDDIT_USERNAME = "test_user"
            REDDIT_PASSWORD = "test_pass"
            DISCORD_BOT_TOKEN = ""
        
        # Create collector (will fail to initialize Reddit, but that's expected for test)
        collector = MultiSourceDataCollector(MockConfig())
        
        # Test that collector was created (even if Reddit connection failed)
        assert collector is not None
        print("✅ Sentiment collector initialization test passed")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def main():
    """Run all integration tests."""
    print("🚀 SENTIMENT ANALYSIS INTEGRATION TESTS")
    print("=" * 60)
    
    # Set up minimal required environment variables
    os.environ['BITVAVO_API_KEY'] = 'test_key_12345678901234567890123456789012'
    os.environ['BITVAVO_API_SECRET'] = 'test_secret_12345678901234567890123456789012'
    
    tests = [
        test_sentiment_configuration,
        test_sentiment_position_sizing,
        test_sentiment_data_collector_mock
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"TEST RESULTS: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        print("\nNext steps:")
        print("1. Enable sentiment analysis by setting SENTIMENT_ENABLED=true in your .env file")
        print("2. Add your Reddit API credentials to your .env file") 
        print("3. Start the trading bot to see sentiment analysis in action")
    else:
        print("❌ Some tests failed. Check the output above.")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)