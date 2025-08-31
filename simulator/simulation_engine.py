#!/usr/bin/env python3
"""
Dip Buy Strategy Simulation Engine
"""

import logging
import time
import json
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

# Import the actual dip buying components
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config import TradingConfig, DipBuyConfig, DipLevel
from src.strategies.dip_buy_manager import DipBuyManager
from src.strategies.dip_evaluator import AssetSaleInfo
from .mock_api import MockBitvavoAPI

logger = logging.getLogger(__name__)


@dataclass
class SimulationConfig:
    """Configuration for simulation runs."""
    start_time: datetime
    end_time: datetime
    initial_balance_eur: Decimal = Decimal("1000")
    max_trade_amount: Decimal = Decimal("10")
    simulation_speed: float = 60.0  # 60x real time (1 hour = 1 minute)
    assets_to_simulate: List[str] = None
    
    # Dip buy configuration
    dip_buy_enabled: bool = True
    dip_levels: List[DipLevel] = None
    monitoring_duration_hours: int = 48
    cooldown_hours: int = 4
    max_rebuys_per_asset: int = 3
    
    def __post_init__(self):
        if self.assets_to_simulate is None:
            self.assets_to_simulate = ["PUMP-EUR", "DOGE-EUR", "ADA-EUR"]
        
        if self.dip_levels is None:
            self.dip_levels = [
                DipLevel(threshold_pct=Decimal('10'), capital_allocation=Decimal('0.4')),
                DipLevel(threshold_pct=Decimal('20'), capital_allocation=Decimal('0.35')),
                DipLevel(threshold_pct=Decimal('35'), capital_allocation=Decimal('0.25'))
            ]


@dataclass
class TradeEvent:
    """Represents a trading event during simulation."""
    timestamp: datetime
    event_type: str  # "initial_buy", "trailing_stop_sell", "dip_rebuy"
    market: str
    price: Decimal
    amount_eur: Decimal
    trigger_reason: str = ""
    dip_level: Optional[int] = None


@dataclass
class SimulationResults:
    """Results of a simulation run."""
    config: SimulationConfig
    duration: timedelta
    total_trades: int
    successful_dip_rebuys: int
    total_profit_loss_eur: Decimal
    profit_loss_pct: float
    trade_events: List[TradeEvent]
    final_portfolio: Dict[str, Decimal]
    dip_buy_effectiveness: Dict[str, Any]


class SimulationEngine:
    """
    Main simulation engine that runs the dip buying strategy against historical data.
    """
    
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.results_dir = Path("simulator/results")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize mock API
        self.mock_api = MockBitvavoAPI(
            simulation_start_time=config.start_time,
            simulation_speed=config.simulation_speed
        )
        
        # Track simulation state
        self.trade_events = []
        self.current_time = config.start_time
        self.active_positions = {}  # market -> {"buy_price": price, "start_time": time}
        
        logger.info(f"Simulation engine initialized for period {config.start_time} to {config.end_time}")
    
    def run_simulation(self) -> SimulationResults:
        """Run the complete simulation."""
        logger.info("Starting dip buy strategy simulation...")
        print(f"[START] Starting simulation: {self.config.start_time} to {self.config.end_time}")
        print(f"[SPEED] Speed: {self.config.simulation_speed}x real-time")
        print(f"[BALANCE] Initial balance: EUR {self.config.initial_balance_eur}")
        print(f"[ASSETS] Assets: {', '.join(self.config.assets_to_simulate)}")
        
        start_real_time = time.time()
        
        try:
            # Initialize dip buy components with simulated API
            trading_config = TradingConfig(
                min_profit_pct=Decimal('5'),  # 5% minimum profit target
                trailing_pct=Decimal('10'),   # 10% trailing stop (more realistic for crypto)
                max_trade_amount=self.config.max_trade_amount,
                check_interval=10,
                max_retries=3,
                retry_delay=5,
                operator_id=1001
            )
            
            dip_config = DipBuyConfig(
                enabled=self.config.dip_buy_enabled,
                monitoring_duration_hours=self.config.monitoring_duration_hours,
                cooldown_hours=self.config.cooldown_hours,
                max_rebuys_per_asset=self.config.max_rebuys_per_asset,
                dip_levels=self.config.dip_levels
            )
            
            # Create dip manager with mock API
            dip_manager = DipBuyManager(
                api=self.mock_api,
                config=dip_config,
                trading_config=trading_config,
                data_dir=Path("simulator/temp_data")
            )
            
            # Run simulation phases
            self._simulate_initial_purchases()
            self._simulate_price_movements_and_sales(dip_manager)
            
            # Calculate results
            results = self._calculate_results(time.time() - start_real_time)
            
            # Save results
            self._save_results(results)
            
            print(f"\n[COMPLETE] Simulation complete!")
            print(f"[P&L] Total P&L: EUR {results.total_profit_loss_eur:.2f} ({results.profit_loss_pct:+.1f}%)")
            print(f"[REBUYS] Successful dip rebuys: {results.successful_dip_rebuys}")
            print(f"[TRADES] Total trades: {results.total_trades}")
            
            return results
            
        except Exception as e:
            logger.error(f"Simulation failed: {e}")
            raise
    
    def _simulate_initial_purchases(self) -> None:
        """Simulate initial purchases of assets (as if they were new listings)."""
        print(f"\n[TIME] {self.current_time.strftime('%Y-%m-%d %H:%M')} - Simulating initial purchases...")
        
        for market in self.config.assets_to_simulate:
            # Get initial price
            current_price = self.mock_api.data_manager.get_price_at_time(market, self.current_time)
            
            # Simulate initial buy (as if it was a new listing)
            buy_response = self.mock_api.send_request("POST", "/order", {
                "market": market,
                "side": "buy", 
                "orderType": "market",
                "amountQuote": str(self.config.max_trade_amount),
                "operatorId": 1001
            })
            
            if buy_response:
                executed_price = Decimal(buy_response["executedPrice"])
                
                # Record trade event
                trade_event = TradeEvent(
                    timestamp=self.current_time,
                    event_type="initial_buy",
                    market=market,
                    price=executed_price,
                    amount_eur=self.config.max_trade_amount,
                    trigger_reason="new_listing_simulation"
                )
                self.trade_events.append(trade_event)
                
                # Track position
                self.active_positions[market] = {
                    "buy_price": executed_price,
                    "start_time": self.current_time,
                    "highest_price": executed_price,
                    "trailing_stop_price": executed_price * (Decimal('1') - Decimal('10') / Decimal('100'))  # 10% trailing stop
                }
                
                print(f"[BUY] Bought {market} at EUR {executed_price:.6f} for EUR {self.config.max_trade_amount}")
    
    def _simulate_price_movements_and_sales(self, dip_manager: DipBuyManager) -> None:
        """Simulate price movements and trigger sales and dip rebuys."""
        print(f"\n[PRICE] Starting price simulation...")
        
        time_step = timedelta(minutes=5)  # Check every 5 minutes of simulation time
        check_count = 0
        
        while self.current_time < self.config.end_time:
            check_count += 1
            if check_count % 100 == 0:  # Progress update every 100 checks
                progress = (self.current_time - self.config.start_time) / (self.config.end_time - self.config.start_time)
                print(f"[PROGRESS] Progress: {progress:.1%} - {self.current_time.strftime('%Y-%m-%d %H:%M')}")
            
            # Update mock API time
            self.mock_api.set_simulation_time(self.current_time)
            
            # Check all active positions for trailing stop triggers
            self._check_trailing_stops(dip_manager)
            
            # Let dip manager check for opportunities (simulate one check cycle)
            self._simulate_dip_manager_check(dip_manager)
            
            # Advance time
            self.current_time += time_step
            
            # Safety break for testing
            if check_count > 10000:  # Prevent infinite loops during testing
                print("[SAFETY] Simulation stopped at safety limit")
                break
    
    def _check_trailing_stops(self, dip_manager: DipBuyManager) -> None:
        """Check if any positions should trigger trailing stops."""
        positions_to_close = []
        
        for market, position in self.active_positions.items():
            try:
                # Get current price
                current_price = self.mock_api.data_manager.get_price_at_time(market, self.current_time)
                
                # Update highest price and trailing stop  
                if current_price > position["highest_price"]:
                    position["highest_price"] = current_price
                    # Use the actual trailing_pct from trading config (10%)
                    trailing_pct = Decimal('10')  # Should match trading_config.trailing_pct
                    position["trailing_stop_price"] = current_price * (Decimal('1') - trailing_pct / Decimal('100'))
                
                # Check if trailing stop is hit
                if current_price <= position["trailing_stop_price"]:
                    # Get actual balance to sell (like the real bot does - Bitvavo doesn't accept '100%')
                    symbol = market.split("-")[0]
                    current_balance = self.mock_api._get_current_balance(symbol)
                    
                    if current_balance <= 0:
                        logger.warning(f"No {symbol} balance to sell for {market}")
                        continue
                    
                    # Trigger sale with actual balance amount
                    sell_response = self.mock_api.send_request("POST", "/order", {
                        "market": market,
                        "side": "sell",
                        "orderType": "market", 
                        "amount": str(current_balance),  # Use actual balance like real bot
                        "operatorId": 1001
                    })
                    
                    if sell_response:
                        sell_price = Decimal(sell_response["executedPrice"])
                        
                        # Record trade event
                        trade_event = TradeEvent(
                            timestamp=self.current_time,
                            event_type="trailing_stop_sell",
                            market=market,
                            price=sell_price,
                            amount_eur=Decimal(sell_response["amountQuote"]),
                            trigger_reason="trailing_stop"
                        )
                        self.trade_events.append(trade_event)
                        
                        # Notify dip manager about the sale
                        dip_manager.on_trade_completed(market, sell_price, "trailing_stop")
                        
                        profit_loss = sell_price - position["buy_price"]
                        profit_pct = (profit_loss / position["buy_price"]) * 100
                        
                        print(f"[SELL] SOLD {market} at EUR {sell_price:.6f} | P&L: {profit_pct:+.1f}% | Now monitoring for dips...")
                        
                        positions_to_close.append(market)
                        
            except Exception as e:
                logger.error(f"Error checking trailing stop for {market}: {e}")
        
        # Remove closed positions
        for market in positions_to_close:
            self.active_positions.pop(market, None)
    
    def _simulate_dip_manager_check(self, dip_manager: DipBuyManager) -> None:
        """Simulate one check cycle of the dip manager."""
        try:
            # Get active dip tracking
            active_tracking = dip_manager.state_manager.get_active_tracking()
            
            for market, asset_state in active_tracking.items():
                try:
                    # Check if this asset should trigger a dip rebuy
                    decision = dip_manager.force_check_asset(market)
                    
                    if decision and decision.should_rebuy:
                        # Execute the dip rebuy
                        current_price = self.mock_api.data_manager.get_price_at_time(market, self.current_time)
                        
                        buy_response = self.mock_api.send_request("POST", "/order", {
                            "market": market,
                            "side": "buy",
                            "orderType": "market", 
                            "amountQuote": str(decision.amount_eur),
                            "operatorId": 1001
                        })
                        
                        if buy_response:
                            executed_price = Decimal(buy_response["executedPrice"])
                            
                            # Record dip rebuy trade event
                            trade_event = TradeEvent(
                                timestamp=self.current_time,
                                event_type="dip_rebuy",
                                market=market,
                                price=executed_price,
                                amount_eur=decision.amount_eur,
                                trigger_reason=decision.reason,
                                dip_level=decision.level
                            )
                            self.trade_events.append(trade_event)
                            
                            # Record successful rebuy in dip manager
                            dip_manager.state_manager.record_successful_rebuy(
                                market, decision.level, executed_price, decision.amount_eur
                            )
                            
                            print(f"[DIP] DIP REBUY: {market} at EUR {executed_price:.6f} | Level {decision.level} | {decision.reason}")
                            
                            # Add back to active positions for potential future sale
                            self.active_positions[market] = {
                                "buy_price": executed_price,
                                "start_time": self.current_time,
                                "highest_price": executed_price,
                                "trailing_stop_price": executed_price * (Decimal('1') - Decimal('10') / Decimal('100'))  # 10% trailing stop
                            }
                        
                except Exception as e:
                    logger.error(f"Error simulating dip check for {market}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in dip manager simulation: {e}")
    
    def _calculate_results(self, runtime_seconds: float) -> SimulationResults:
        """Calculate final simulation results."""
        # Get final portfolio state
        final_balances = self.mock_api.send_request("GET", "/balance")
        final_portfolio = {}
        
        if final_balances:
            for balance in final_balances:
                symbol = balance["symbol"]
                amount = Decimal(balance["available"])
                if amount > 0:
                    final_portfolio[symbol] = amount
        
        # Calculate total P&L
        initial_eur = self.config.initial_balance_eur
        final_eur = final_portfolio.get("EUR", Decimal("0"))
        
        # Add value of remaining crypto positions
        for symbol, amount in final_portfolio.items():
            if symbol != "EUR" and amount > 0:
                market = f"{symbol}-EUR"
                try:
                    current_price = self.mock_api.data_manager.get_price_at_time(market, self.current_time)
                    crypto_value = amount * current_price
                    final_eur += crypto_value
                except:
                    pass  # Skip if can't get price
        
        total_profit_loss = final_eur - initial_eur
        profit_loss_pct = float((total_profit_loss / initial_eur) * 100)
        
        # Count successful dip rebuys
        dip_rebuys = [event for event in self.trade_events if event.event_type == "dip_rebuy"]
        
        # Calculate dip buy effectiveness
        dip_effectiveness = {
            "total_dip_opportunities": len([e for e in self.trade_events if e.event_type == "trailing_stop_sell"]),
            "successful_dip_rebuys": len(dip_rebuys),
            "rebuys_by_level": {},
            "avg_rebuy_amount": float(sum(e.amount_eur for e in dip_rebuys) / len(dip_rebuys)) if dip_rebuys else 0
        }
        
        # Group by dip level
        for event in dip_rebuys:
            level = event.dip_level or 0
            if level not in dip_effectiveness["rebuys_by_level"]:
                dip_effectiveness["rebuys_by_level"][level] = 0
            dip_effectiveness["rebuys_by_level"][level] += 1
        
        return SimulationResults(
            config=self.config,
            duration=timedelta(seconds=runtime_seconds),
            total_trades=len(self.trade_events),
            successful_dip_rebuys=len(dip_rebuys),
            total_profit_loss_eur=total_profit_loss,
            profit_loss_pct=profit_loss_pct,
            trade_events=self.trade_events,
            final_portfolio=final_portfolio,
            dip_buy_effectiveness=dip_effectiveness
        )
    
    def _save_results(self, results: SimulationResults) -> None:
        """Save simulation results to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"simulation_results_{timestamp}.json"
        filepath = self.results_dir / filename
        
        # Convert results to JSON-serializable format
        results_dict = {
            "config": {
                "start_time": results.config.start_time.isoformat(),
                "end_time": results.config.end_time.isoformat(),
                "initial_balance_eur": float(results.config.initial_balance_eur),
                "max_trade_amount": float(results.config.max_trade_amount),
                "simulation_speed": results.config.simulation_speed,
                "assets_to_simulate": results.config.assets_to_simulate,
                "dip_buy_enabled": results.config.dip_buy_enabled,
                "dip_levels": [
                    {"threshold_pct": float(level.threshold_pct), "capital_allocation": float(level.capital_allocation)}
                    for level in results.config.dip_levels
                ]
            },
            "results": {
                "duration_seconds": results.duration.total_seconds(),
                "total_trades": results.total_trades,
                "successful_dip_rebuys": results.successful_dip_rebuys,
                "total_profit_loss_eur": float(results.total_profit_loss_eur),
                "profit_loss_pct": results.profit_loss_pct,
                "final_portfolio": {k: float(v) for k, v in results.final_portfolio.items()},
                "dip_buy_effectiveness": results.dip_buy_effectiveness
            },
            "trade_events": [
                {
                    "timestamp": event.timestamp.isoformat(),
                    "event_type": event.event_type,
                    "market": event.market,
                    "price": float(event.price),
                    "amount_eur": float(event.amount_eur),
                    "trigger_reason": event.trigger_reason,
                    "dip_level": event.dip_level
                }
                for event in results.trade_events
            ]
        }
        
        with open(filepath, 'w') as f:
            json.dump(results_dict, f, indent=2)
        
        print(f"[SAVE] Results saved to: {filepath}")
        logger.info(f"Simulation results saved to {filepath}")