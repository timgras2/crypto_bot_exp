import os
import unittest
from decimal import Decimal
from config import load_config

class TestConfig(unittest.TestCase):
    def setUp(self):
        # Set environment variables for testing - use realistic length keys
        os.environ["BITVAVO_API_KEY"] = "3cc98733593ffecc74e8a62dd5d3bd05f883ed81c5f6f95dd47c15f7bf70337d"
        os.environ["BITVAVO_API_SECRET"] = "9630f918a75642bb1ee763eecfe8813798db164d346727bc3b1b5d98f53bd6a85597e344ac670fad07068dfee7ebd0755d089632ea218265ca0c192b6caee1b9"
        os.environ["MIN_PROFIT_PCT"] = "4.5"
        os.environ["TRAILING_PCT"] = "2.5"
        os.environ["MAX_TRADE_AMOUNT"] = "20.0"
        os.environ["CHECK_INTERVAL"] = "15"
        os.environ["MAX_RETRIES"] = "5"
        os.environ["RETRY_DELAY"] = "3"
        os.environ["BITVAVO_BASE_URL"] = "https://api.test.com/v2"
        os.environ["RATE_LIMIT"] = "250"
        os.environ["API_TIMEOUT"] = "25"
        os.environ["OPERATOR_ID"] = "2001"

    def tearDown(self):
        # Remove the test environment variables
        keys = [
            "BITVAVO_API_KEY", "BITVAVO_API_SECRET", "MIN_PROFIT_PCT", "TRAILING_PCT",
            "MAX_TRADE_AMOUNT", "CHECK_INTERVAL", "MAX_RETRIES", "RETRY_DELAY",
            "BITVAVO_BASE_URL", "RATE_LIMIT", "API_TIMEOUT", "OPERATOR_ID"
        ]
        for key in keys:
            os.environ.pop(key, None)

    def test_load_config(self):
        trading_config, api_config, dip_config = load_config()

        # Check TradingConfig values
        self.assertEqual(trading_config.min_profit_pct, Decimal("4.5"))
        self.assertEqual(trading_config.trailing_pct, Decimal("2.5"))
        self.assertEqual(trading_config.max_trade_amount, Decimal("20.0"))
        self.assertEqual(trading_config.check_interval, 15)
        self.assertEqual(trading_config.max_retries, 5)
        self.assertEqual(trading_config.retry_delay, 3)
        self.assertEqual(trading_config.operator_id, 2001)

        # Check APIConfig values
        self.assertEqual(api_config.api_key, "3cc98733593ffecc74e8a62dd5d3bd05f883ed81c5f6f95dd47c15f7bf70337d")
        self.assertEqual(api_config.api_secret, "9630f918a75642bb1ee763eecfe8813798db164d346727bc3b1b5d98f53bd6a85597e344ac670fad07068dfee7ebd0755d089632ea218265ca0c192b6caee1b9")
        self.assertEqual(api_config.base_url, "https://api.test.com/v2")
        self.assertEqual(api_config.rate_limit, 250)
        self.assertEqual(api_config.timeout, 25)

if __name__ == '__main__':
    unittest.main()
