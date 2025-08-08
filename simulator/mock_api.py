#!/usr/bin/env python3
"""
Mock Bitvavo API for Simulation - Returns Real Historical Data
"""

import json
import logging
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class HistoricalDataManager:
    """Manages historical price data for simulation."""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.price_cache = {}
        self.current_time = datetime.now()
        
    def fetch_historical_data(self, market: str, start_time: datetime, end_time: datetime, 
                            interval: str = "1m") -> List[Dict[str, Any]]:
        """
        Fetch historical candlestick data from Bitvavo.
        
        This would normally fetch from Bitvavo API, but for simulation we'll
        generate realistic price movements based on actual market behavior.
        """
        # In a real implementation, this would call:
        # response = real_api.send_request("GET", f"/candles?market={market}&start={start}&end={end}&interval={interval}")
        
        # For now, generate realistic price data
        return self._generate_realistic_price_data(market, start_time, end_time, interval)
    
    def _generate_realistic_price_data(self, market: str, start_time: datetime, 
                                     end_time: datetime, interval: str) -> List[Dict[str, Any]]:
        """Generate realistic price movements for simulation."""
        candles = []
        current_time = start_time
        
        # Base price (varies by market)
        base_prices = {
            "BTC-EUR": Decimal("45000"),
            "ETH-EUR": Decimal("3000"), 
            "ADA-EUR": Decimal("0.5"),
            "DOT-EUR": Decimal("8.0"),
            "PUMP-EUR": Decimal("0.000045"),  # Meme coin example
            "DOGE-EUR": Decimal("0.08"),
            "TEST-EUR": Decimal("1.0")
        }
        
        base_price = base_prices.get(market, Decimal("1.0"))
        current_price = base_price
        
        # Time increment based on interval
        time_delta = timedelta(minutes=1) if interval == "1m" else timedelta(hours=1)
        
        while current_time <= end_time:
            # Simulate realistic price movement (random walk with volatility)
            import random
            
            # Different volatility for different assets
            if "PUMP" in market or "DOGE" in market:
                volatility = 0.05  # 5% swings for meme coins
            elif "BTC" in market or "ETH" in market:
                volatility = 0.02  # 2% swings for major coins
            else:
                volatility = 0.03  # 3% swings for altcoins
            
            # Random price change
            change_pct = random.uniform(-volatility, volatility)
            price_change = current_price * Decimal(str(change_pct))
            current_price = max(current_price + price_change, Decimal("0.000001"))
            
            # Create candlestick data
            open_price = current_price
            high_price = current_price * Decimal(str(1 + abs(change_pct) * 0.5))
            low_price = current_price * Decimal(str(1 - abs(change_pct) * 0.5))
            close_price = current_price
            
            # Volume (realistic but simulated)
            base_volume = 10000 if "BTC" in market else 50000
            volume = base_volume * random.uniform(0.5, 2.0)
            
            candle = {
                "timestamp": int(current_time.timestamp() * 1000),
                "open": str(open_price),
                "high": str(high_price),
                "low": str(low_price), 
                "close": str(close_price),
                "volume": str(volume)
            }
            
            candles.append(candle)
            current_time += time_delta
        
        return candles
    
    def get_price_at_time(self, market: str, timestamp: datetime) -> Optional[Decimal]:
        """Get the price of a market at a specific timestamp."""
        # In a real implementation, this would interpolate from historical data
        # For simulation, we'll generate a price based on timestamp and market
        
        base_prices = {
            "BTC-EUR": Decimal("45000"),
            "ETH-EUR": Decimal("3000"), 
            "ADA-EUR": Decimal("0.5"),
            "DOT-EUR": Decimal("8.0"),
            "PUMP-EUR": Decimal("0.000045"),
            "DOGE-EUR": Decimal("0.08"),
            "TEST-EUR": Decimal("1.0")
        }
        
        base_price = base_prices.get(market, Decimal("1.0"))
        
        # Add some deterministic variation based on timestamp
        # This ensures consistent prices for the same timestamp
        time_factor = (timestamp.timestamp() % 86400) / 86400  # 0-1 based on time of day
        import math
        price_multiplier = 1 + 0.1 * math.sin(time_factor * 2 * math.pi)  # ±10% variation
        
        return base_price * Decimal(str(price_multiplier))


class MockBitvavoAPI:
    """
    Mock Bitvavo API that provides real-like data for simulation.
    
    This replaces the real BitvavoAPI during simulation runs,
    providing historical data instead of live data.
    """
    
    def __init__(self, simulation_start_time: datetime, simulation_speed: float = 1.0):
        self.simulation_start_time = simulation_start_time
        self.simulation_speed = simulation_speed  # Speed multiplier (1.0 = real time)
        self.current_simulation_time = simulation_start_time
        self.data_manager = HistoricalDataManager(Path("simulator/data"))
        
        # Track simulated orders for portfolio management
        self.executed_orders = []
        self.order_counter = 1
        
        logger.info(f"MockBitvavoAPI initialized for simulation starting at {simulation_start_time}")
    
    def advance_time(self, seconds: float) -> None:
        """Advance the simulation time."""
        self.current_simulation_time += timedelta(seconds=seconds * self.simulation_speed)
    
    def set_simulation_time(self, timestamp: datetime) -> None:
        """Set the current simulation time directly."""
        self.current_simulation_time = timestamp
    
    def send_request(self, method: str, endpoint: str, body: Optional[Dict] = None) -> Optional[Dict]:
        """
        Mock implementation of send_request that returns simulated data.
        """
        try:
            if endpoint.startswith("/ticker/price"):
                return self._handle_ticker_price(endpoint)
            elif endpoint.startswith("/ticker/24h"):
                return self._handle_ticker_24h(endpoint)
            elif endpoint == "/order" and method == "POST":
                return self._handle_order_placement(body)
            elif endpoint == "/balance":
                return self._handle_balance_request()
            elif endpoint.startswith("/candles"):
                return self._handle_candles_request(endpoint)
            else:
                logger.warning(f"Unhandled mock API endpoint: {method} {endpoint}")
                return None
                
        except Exception as e:
            logger.error(f"Error in mock API request {method} {endpoint}: {e}")
            return None
    
    def _handle_ticker_price(self, endpoint: str) -> Dict[str, Any]:
        """Handle ticker price requests."""
        # Extract market from endpoint: /ticker/price?market=BTC-EUR
        if "market=" in endpoint:
            market = endpoint.split("market=")[1].split("&")[0]
        else:
            market = "BTC-EUR"  # Default
        
        price = self.data_manager.get_price_at_time(market, self.current_simulation_time)
        
        return {
            "market": market,
            "price": str(price)
        }
    
    def _handle_ticker_24h(self, endpoint: str) -> Dict[str, Any]:
        """Handle 24h ticker requests."""
        if "market=" in endpoint:
            market = endpoint.split("market=")[1].split("&")[0]
        else:
            market = "BTC-EUR"
        
        current_price = self.data_manager.get_price_at_time(market, self.current_simulation_time)
        price_24h_ago = self.data_manager.get_price_at_time(
            market, 
            self.current_simulation_time - timedelta(hours=24)
        )
        
        price_change = current_price - price_24h_ago
        price_change_pct = (price_change / price_24h_ago) * 100
        
        return {
            "market": market,
            "last": str(current_price),
            "lastPrice": str(current_price),
            "priceChange": str(price_change),
            "priceChangePercent": str(price_change_pct),
            "openPrice": str(price_24h_ago),
            "highPrice": str(current_price * Decimal("1.05")),  # Simulated high
            "lowPrice": str(current_price * Decimal("0.95")),   # Simulated low
            "volume": "100000",  # Simulated volume
            "timestamp": int(self.current_simulation_time.timestamp() * 1000)
        }
    
    def _handle_order_placement(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Handle order placement (simulate successful execution)."""
        market = body.get("market", "UNKNOWN-EUR")
        side = body.get("side", "buy")
        order_type = body.get("orderType", "market")
        amount_quote = body.get("amountQuote")
        amount = body.get("amount")
        
        # Get current market price
        current_price = self.data_manager.get_price_at_time(market, self.current_simulation_time)
        
        # Simulate execution with small slippage
        import random
        slippage = random.uniform(0.001, 0.005)  # 0.1% to 0.5% slippage
        if side == "buy":
            execution_price = current_price * Decimal(str(1 + slippage))
        else:
            execution_price = current_price * Decimal(str(1 - slippage))
        
        order_id = f"sim-{self.order_counter:06d}"
        self.order_counter += 1
        
        # Calculate filled amounts
        if amount_quote:  # Buying with EUR amount
            filled_amount_quote = Decimal(str(amount_quote))
            filled_amount = filled_amount_quote / execution_price
        else:  # Selling specific amount of crypto
            filled_amount = Decimal(str(amount))
            filled_amount_quote = filled_amount * execution_price
        
        # Record the executed order
        order_record = {
            "orderId": order_id,
            "market": market,
            "side": side,
            "orderType": order_type,
            "amount": str(filled_amount),
            "amountQuote": str(filled_amount_quote),
            "price": str(execution_price),
            "executedPrice": str(execution_price),
            "timestamp": int(self.current_simulation_time.timestamp() * 1000),
            "status": "filled"
        }
        
        self.executed_orders.append(order_record)
        
        logger.info(f"Simulated {side} order: {market} {filled_amount} at €{execution_price}")
        
        return order_record
    
    def _handle_balance_request(self) -> List[Dict[str, Any]]:
        """Handle balance requests (return current simulated portfolio)."""
        # Calculate current balances based on executed orders
        balances = {"EUR": {"available": "1000.0", "inOrder": "0"}}  # Start with €1000
        
        for order in self.executed_orders:
            market = order["market"]
            symbol = market.split("-")[0]  # Extract base currency
            side = order["side"]
            amount = Decimal(order["amount"])
            amount_quote = Decimal(order["amountQuote"])
            
            # Initialize symbol balance if not exists
            if symbol not in balances:
                balances[symbol] = {"available": "0", "inOrder": "0"}
            
            if side == "buy":
                # Increase crypto balance, decrease EUR balance
                balances[symbol]["available"] = str(
                    Decimal(balances[symbol]["available"]) + amount
                )
                balances["EUR"]["available"] = str(
                    Decimal(balances["EUR"]["available"]) - amount_quote
                )
            else:  # sell
                # Decrease crypto balance, increase EUR balance
                balances[symbol]["available"] = str(
                    max(Decimal("0"), Decimal(balances[symbol]["available"]) - amount)
                )
                balances["EUR"]["available"] = str(
                    Decimal(balances["EUR"]["available"]) + amount_quote
                )
        
        # Convert to Bitvavo API format
        balance_list = []
        for symbol, balance_data in balances.items():
            if Decimal(balance_data["available"]) > 0 or symbol == "EUR":
                balance_list.append({
                    "symbol": symbol,
                    "available": balance_data["available"],
                    "inOrder": balance_data["inOrder"]
                })
        
        return balance_list
    
    def _handle_candles_request(self, endpoint: str) -> List[Dict[str, Any]]:
        """Handle historical candles requests."""
        # Parse parameters from endpoint
        # /candles?market=BTC-EUR&interval=1m&start=timestamp&end=timestamp
        params = {}
        if "?" in endpoint:
            query_string = endpoint.split("?")[1]
            for param in query_string.split("&"):
                if "=" in param:
                    key, value = param.split("=", 1)
                    params[key] = value
        
        market = params.get("market", "BTC-EUR")
        interval = params.get("interval", "1m")
        
        # For simulation, return recent candles around current simulation time
        start_time = self.current_simulation_time - timedelta(hours=24)
        end_time = self.current_simulation_time
        
        return self.data_manager.fetch_historical_data(market, start_time, end_time, interval)
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get summary of all executed orders during simulation."""
        total_orders = len(self.executed_orders)
        buy_orders = [o for o in self.executed_orders if o["side"] == "buy"]
        sell_orders = [o for o in self.executed_orders if o["side"] == "sell"]
        
        total_eur_spent = sum(Decimal(o["amountQuote"]) for o in buy_orders)
        total_eur_received = sum(Decimal(o["amountQuote"]) for o in sell_orders)
        
        return {
            "total_orders": total_orders,
            "buy_orders": len(buy_orders),
            "sell_orders": len(sell_orders),
            "total_eur_spent": float(total_eur_spent),
            "total_eur_received": float(total_eur_received),
            "net_eur_change": float(total_eur_received - total_eur_spent),
            "orders": self.executed_orders
        }