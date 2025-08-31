import unittest
import time
import logging
from decimal import Decimal
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.trade_logic import TradeManager
from src.config import TradingConfig

# Configure logging voor de tests
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True
)

class FakeBitvavoAPI:
    def __init__(self):
        self.price = "50000.00"
        
    def send_request(self, method, endpoint, body=None, params=None):
        if method.upper() == "POST" and endpoint == "/order":
            # Voor buy-orders: retourneer een prijs, voor sell-orders: retourneer een orderId
            if body and body.get("side") == "buy":
                return {"price": "50000.00"}
            elif body and body.get("side") == "sell":
                return {"orderId": "test_sell_order", "status": "filled"}
            else:
                return {"orderId": "test_order"}
        elif method.upper() == "GET" and endpoint.startswith("/ticker/price"):
            return {"price": self.price}
        elif method.upper() == "GET" and endpoint == "/balance":
            # Return mock balance data
            return [
                {"symbol": "BTC", "available": "0.1", "inOrder": "0.0"},
                {"symbol": "EUR", "available": "1000.0", "inOrder": "0.0"}
            ]
        return None

class TestTradeLogic(unittest.TestCase):
    def setUp(self):
        logging.info("Setting up test case")
        self.trading_config = TradingConfig(
            min_profit_pct=Decimal("5.0"),
            trailing_pct=Decimal("3.0"),
            max_trade_amount=Decimal("10.0"),
            check_interval=0.1,  # Kortere interval voor testen
            max_retries=2,
            retry_delay=0.1,
            operator_id=1001
        )
        self.fake_api = FakeBitvavoAPI()
        self.trade_manager = TradeManager(self.fake_api, self.trading_config)

    def tearDown(self):
        logging.info("Tearing down test case")
        active_trades = list(self.trade_manager.active_trades.keys())
        for market in active_trades:
            self.trade_manager.stop_monitoring(market)
        time.sleep(0.2)  # Even wachten zodat threads netjes afsluiten

    def test_place_market_buy(self):
        price = self.trade_manager.place_market_buy("BTC-EUR", Decimal("5.0"))
        self.assertEqual(price, Decimal("50000.00"))

    def test_sell_market(self):
        result = self.trade_manager.sell_market("BTC-EUR")
        self.assertTrue(result)

    def test_start_and_stop_monitoring(self):
        self.trade_manager.start_monitoring("BTC-EUR", Decimal("50000.00"))
        time.sleep(0.5)
        self.assertIn("BTC-EUR", self.trade_manager.active_trades)
        self.trade_manager.stop_monitoring("BTC-EUR")
        for _ in range(5):
            if "BTC-EUR" not in self.trade_manager.active_trades:
                break
            time.sleep(0.1)
        self.assertNotIn("BTC-EUR", self.trade_manager.active_trades)

    def test_monitor_trade_triggers_stop_loss(self):
        logging.info("Starting test for stop loss trigger")
        initial_price = Decimal("50000.00")
        self.fake_api.price = str(initial_price)
        
        self.trade_manager.start_monitoring("BTC-EUR", initial_price)
        
        # Wacht tot monitoring is gestart
        start_time = time.time()
        while "BTC-EUR" not in self.trade_manager.active_trades:
            if time.time() - start_time > 2:
                self.fail("Timeout waiting for monitoring to start")
            time.sleep(0.05)
        
        time.sleep(0.2)
        
        # Simuleer een prijsdaling om stop loss te triggeren
        self.fake_api.price = "45000.00"
        
        # Wacht totdat de stop loss getriggerd is en monitoring stopt
        start_time = time.time()
        while "BTC-EUR" in self.trade_manager.active_trades:
            if time.time() - start_time > 3:
                logging.error("Timeout waiting for stop loss to trigger")
                self.fail("Timeout waiting for stop loss to trigger")
            time.sleep(0.05)
        
        logging.info("Stop loss triggered successfully")
        self.assertNotIn("BTC-EUR", self.trade_manager.active_trades)

if __name__ == '__main__':
    unittest.main()
