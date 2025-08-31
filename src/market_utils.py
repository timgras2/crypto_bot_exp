import json
import logging
from pathlib import Path
from typing import List, Tuple

from .requests_handler import BitvavoAPI


class MarketTracker:
    def __init__(self, api: BitvavoAPI, storage_path: Path) -> None:
        self.api = api
        self.storage_path = storage_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

    def load_previous_markets(self) -> List[str]:
        """Load stored markets from JSON file."""
        if self.storage_path.exists():
            try:
                return json.loads(self.storage_path.read_text())
            except json.JSONDecodeError:
                logging.warning("JSON file corrupted, starting with an empty list")
                return []
        return []

    def save_previous_markets(self, markets: List[str]) -> None:
        """Save updated markets to JSON file."""
        self.storage_path.write_text(json.dumps(markets))

    def detect_new_listings(self, previous_markets: List[str]) -> Tuple[List[str], List[str]]:
        """Detect new market listings."""
        try:
            response = self.api.send_request("GET", "/markets")
            if not response:
                return [], previous_markets

            current_markets = [
                market['market'] for market in response
                if isinstance(market, dict) and 'market' in market
            ]

            # If this is the first run (no previous markets), establish baseline
            if not previous_markets:
                logging.info(f"First run: Establishing baseline with {len(current_markets)} existing markets")
                # Return empty new_listings but save current markets as baseline
                return [], current_markets

            # Use set operations for O(n) performance instead of O(n²)
            current_set = set(current_markets)
            previous_set = set(previous_markets)
            new_listings = list(current_set - previous_set)

            if new_listings:
                logging.info(f"New listings detected: {new_listings}")

            return new_listings, current_markets

        except Exception as e:
            logging.exception(f"Error detecting new listings: {str(e)}")
            return [], previous_markets
