import unittest
from pathlib import Path
import json
import os
from market_utils import MarketTracker

# A fake API class to simulate /markets response.
class FakeBitvavoAPI:
    def send_request(self, method, endpoint, body=None):
        if endpoint == "/markets":
            # Simulated API response: list of market objects.
            return [
                {"market": "BTC-EUR"},
                {"market": "ETH-EUR"},
                {"market": "LTC-EUR"},
            ]
        return None

class TestMarketTracker(unittest.TestCase):
    def setUp(self):
        self.fake_api = FakeBitvavoAPI()
        # Use a temporary file so as not to overwrite production data.
        self.temp_storage = Path("temp_markets.json")
        if self.temp_storage.exists():
            self.temp_storage.unlink()
        self.tracker = MarketTracker(api=self.fake_api, storage_path=self.temp_storage)

    def tearDown(self):
        if self.temp_storage.exists():
            self.temp_storage.unlink()

    def test_detect_new_listings(self):
        previous_markets = ["BTC-EUR", "ETH-EUR"]
        new_listings, current_markets = self.tracker.detect_new_listings(previous_markets)

        # "LTC-EUR" should be new.
        self.assertEqual(new_listings, ["LTC-EUR"])
        self.assertEqual(current_markets, ["BTC-EUR", "ETH-EUR", "LTC-EUR"])

    def test_detect_no_new_listings(self):
        previous_markets = ["BTC-EUR", "ETH-EUR", "LTC-EUR"]
        new_listings, current_markets = self.tracker.detect_new_listings(previous_markets)
        self.assertEqual(new_listings, [])
        self.assertEqual(current_markets, ["BTC-EUR", "ETH-EUR", "LTC-EUR"])
    
    def test_first_run_establishes_baseline(self):
        """Test that first run with empty previous_markets establishes baseline without new listings."""
        previous_markets = []  # First run - no previous markets
        new_listings, current_markets = self.tracker.detect_new_listings(previous_markets)
        
        # Should return NO new listings on first run (establishing baseline)
        self.assertEqual(new_listings, [])
        # Should return current markets for baseline establishment
        self.assertEqual(current_markets, ["BTC-EUR", "ETH-EUR", "LTC-EUR"])

if __name__ == '__main__':
    unittest.main()
