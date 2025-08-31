#!/usr/bin/env python3
"""
Dip Buy Manager - Main orchestration class for the dip buying strategy
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional, Dict, Any

from ..config import DipBuyConfig, TradingConfig
from ..requests_handler import BitvavoAPI
from .dip_evaluator import DipEvaluator, AssetSaleInfo, RebuyDecision
from .dip_state import DipStateManager
from .market_filter import MarketFilter

logger = logging.getLogger(__name__)


class DipBuyManager:
    """
    Main orchestration class for the dip buying strategy.
    
    Responsibilities:
    - Monitor assets that were sold via trailing stop
    - Evaluate rebuy opportunities when prices dip
    - Execute rebuy orders through the API
    - Maintain persistent state across bot restarts
    """
    
    def __init__(self, api: BitvavoAPI, config: DipBuyConfig, trading_config: TradingConfig, 
                 data_dir: Path, check_interval: int = 10):
        self.api = api
        self.config = config
        self.trading_config = trading_config
        self.max_trade_amount = trading_config.max_trade_amount
        self.check_interval = check_interval
        
        # Initialize components
        self.evaluator = DipEvaluator(config, self.max_trade_amount)
        self.state_manager = DipStateManager(data_dir, config)
        self.market_filter = MarketFilter(api) if config.use_market_filter else None
        
        # Threading control
        self._stop_event = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        logger.info(f"DipBuyManager initialized (enabled: {config.enabled})")
        if config.enabled:
            logger.info(f"Dip levels: {[(l.threshold_pct, l.capital_allocation) for l in config.dip_levels]}")
    
    def start(self) -> None:
        """Start the dip buying monitoring service."""
        if not self.config.enabled:
            logger.info("Dip buying disabled - not starting monitor")
            return
        
        if self._monitor_thread and self._monitor_thread.is_alive():
            logger.warning("Dip monitor already running")
            return
        
        logger.info("Starting dip buy monitoring service")
        self._stop_event.clear()
        
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name="DipBuyMonitor",
            daemon=True
        )
        self._monitor_thread.start()
        
        logger.info("Dip buy monitoring started")
    
    def stop(self) -> None:
        """Stop the dip buying monitoring service."""
        logger.info("Stopping dip buy monitoring service")
        self._stop_event.set()
        
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=10)
            if self._monitor_thread.is_alive():
                logger.warning("Dip monitor thread did not stop cleanly")
        
        logger.info("Dip buy monitoring stopped")
    
    def on_trade_completed(self, market: str, sell_price: Decimal, trigger_reason: str) -> None:
        """
        Notification from TradeManager when a trade is completed.
        
        This is the entry point for new dip tracking opportunities.
        """
        if not self.config.enabled:
            return
        
        # Only track trailing stop sales (profitable exits), not stop losses
        if trigger_reason != "trailing_stop":
            logger.debug(f"Not tracking {market} for dips (trigger: {trigger_reason})")
            return
        
        try:
            # Create asset sale info
            asset_info = AssetSaleInfo(
                market=market,
                sell_price=sell_price,
                sell_timestamp=datetime.now(),
                trigger_reason=trigger_reason
            )
            
            # Get monitoring information
            monitoring_info = self.evaluator.get_monitoring_info(asset_info)
            
            # Add to state tracking
            self.state_manager.add_asset_for_tracking(asset_info, monitoring_info)
            
            logger.info(f"🎯 Added {market} to dip tracking (sold at €{sell_price})")
            
            # Log dip thresholds for user visibility
            for i, level in enumerate(self.config.dip_levels, 1):
                threshold_price = sell_price * (Decimal('1') - level.threshold_pct / Decimal('100'))
                amount = self.max_trade_amount * level.capital_allocation
                print(f"📊 {market} Level {i}: €{threshold_price:.6f} (-{level.threshold_pct}%) → €{amount:.2f}")
            
        except Exception as e:
            logger.error(f"Failed to start dip tracking for {market}: {e}")
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop that runs in a separate thread."""
        logger.info("Dip buy monitor loop started")
        
        try:
            while not self._stop_event.is_set():
                try:
                    self._check_all_assets()
                except Exception as e:
                    logger.error(f"Error in dip monitoring loop: {e}")
                
                # Sleep with interruptible pattern
                for _ in range(self.check_interval):
                    if self._stop_event.is_set():
                        break
                    time.sleep(1)
                        
        except Exception as e:
            logger.error(f"Fatal error in dip monitor loop: {e}")
        finally:
            logger.info("Dip buy monitor loop exiting")
    
    def _check_all_assets(self) -> None:
        """Check all actively tracked assets for dip opportunities."""
        active_tracking = self.state_manager.get_active_tracking()
        
        if not active_tracking:
            return
        
        logger.debug(f"Checking {len(active_tracking)} assets for dip opportunities")
        
        for market, asset_state in active_tracking.items():
            try:
                self._check_asset_for_dip(market, asset_state)
            except Exception as e:
                logger.error(f"Error checking {market} for dips: {e}")
    
    def _check_asset_for_dip(self, market: str, asset_state: Dict[str, Any]) -> None:
        """Check a specific asset for dip rebuy opportunities."""
        try:
            # Validate market name
            if not market or not market.strip():
                logger.error("Invalid market name provided")
                return
            
            # Get current market price
            response = self.api.send_request("GET", f"/ticker/price?market={market}")
            if not response or 'price' not in response:
                logger.debug(f"No price data for {market}")
                return
            
            # Validate price response
            try:
                current_price = Decimal(str(response['price']))
                if current_price <= 0:
                    logger.error(f"Invalid price received for {market}: {current_price}")
                    return
            except (ValueError, InvalidOperation) as e:
                logger.error(f"Could not parse price for {market}: {response.get('price')} - {e}")
                return
            
            # Validate and reconstruct asset sale info
            try:
                sell_price = Decimal(str(asset_state.get('sell_price', '0')))
                if sell_price <= 0:
                    logger.error(f"Invalid sell_price in asset_state for {market}: {sell_price}")
                    return
                
                sell_timestamp_str = asset_state.get('sell_timestamp')
                if not sell_timestamp_str:
                    logger.error(f"Missing sell_timestamp in asset_state for {market}")
                    return
                
                sell_timestamp = datetime.fromisoformat(sell_timestamp_str)
                
                asset_info = AssetSaleInfo(
                    market=market,
                    sell_price=sell_price,
                    sell_timestamp=sell_timestamp,
                    trigger_reason=asset_state.get('trigger_reason', 'unknown')
                )
                
            except (ValueError, InvalidOperation) as e:
                logger.error(f"Invalid asset_state data for {market}: {e}")
                return
            
            # Evaluate rebuy opportunity
            decision = self.evaluator.should_rebuy(asset_info, current_price, asset_state)
            
            if decision.should_rebuy and decision.level:
                logger.info(f"🎯 Dip rebuy opportunity: {market} - {decision.reason}")
                self._attempt_rebuy(market, decision, current_price)
            else:
                logger.debug(f"{market}: {decision.reason}")
                
        except (InvalidOperation, ValueError) as e:
            logger.error(f"Invalid price data for {market}: {e}")
        except Exception as e:
            logger.error(f"Error evaluating {market}: {e}")
    
    def _attempt_rebuy(self, market: str, decision: RebuyDecision, current_price: Decimal) -> None:
        """Attempt to execute a dip rebuy order."""
        try:
            # Update state to indicate attempt in progress
            self.state_manager.update_level_attempt(
                market, decision.level, 'attempting'
            )
            
            # Execute market buy
            logger.info(f"🛒 Executing dip rebuy: {market} €{decision.amount_eur} at €{current_price}")
            print(f"🛒 DIP REBUY: {market} at €{current_price} (-{decision.reason})")
            
            executed_price = self._place_market_buy(market, decision.amount_eur)
            
            if executed_price:
                # Record successful rebuy
                self.state_manager.record_successful_rebuy(
                    market, decision.level, executed_price, decision.amount_eur
                )
                
                print(f"✅ DIP REBUY SUCCESS: {market} €{decision.amount_eur} at €{executed_price}")
                logger.info(f"Successfully executed dip rebuy for {market} level {decision.level}")
                
            else:
                # Handle execution failure
                self._handle_rebuy_failure(market, decision.level, "Order execution failed")
                
        except Exception as e:
            logger.error(f"Failed to execute dip rebuy for {market}: {e}")
            self._handle_rebuy_failure(market, decision.level, str(e))
    
    def _place_market_buy(self, market: str, amount_eur: Decimal) -> Optional[Decimal]:
        """
        Place a market buy order for dip rebuy.
        
        This is similar to TradeManager.place_market_buy but specifically
        for dip rebuy operations.
        """
        try:
            body = {
                'market': market,
                'side': 'buy',
                'orderType': 'market',
                'amountQuote': str(amount_eur),
                'operatorId': self.trading_config.operator_id
            }
            
            for attempt in range(3):  # Max 3 retry attempts
                response = self.api.send_request("POST", "/order", body)
                if response:
                    # Extract execution price
                    price_str = (response.get('price') or 
                                response.get('executedPrice') or 
                                response.get('avgPrice') or 
                                response.get('fillPrice') or '0')
                    
                    executed_price = Decimal(str(price_str))
                    
                    if executed_price > 0:
                        logger.info(f"Dip rebuy executed for {market} at €{executed_price}")
                        return executed_price
                    else:
                        logger.warning(f"Dip rebuy order placed for {market} but no execution price")
                        # Try to get current market price as fallback
                        ticker_response = self.api.send_request("GET", f"/ticker/price?market={market}")
                        if ticker_response and ticker_response.get('price'):
                            fallback_price = Decimal(str(ticker_response.get('price')))
                            logger.info(f"Using market price {fallback_price} for {market} dip rebuy")
                            return fallback_price
                
                if attempt < 2:  # Don't sleep on last attempt
                    time.sleep(2)  # Brief delay before retry
            
            return None
            
        except Exception as e:
            logger.error(f"Error placing dip rebuy order for {market}: {e}")
            return None
    
    def _handle_rebuy_failure(self, market: str, level_number: int, error_msg: str) -> None:
        """Handle a failed rebuy attempt with exponential backoff."""
        try:
            # Get current retry count
            asset_state = self.state_manager.get_asset_state(market)
            if not asset_state:
                return
            
            levels_data = asset_state.get('levels', {})
            level_data = levels_data.get(str(level_number), {})
            retry_count = level_data.get('retry_count', 0) + 1
            
            # Calculate next retry time with exponential backoff
            backoff_seconds = min(300, 30 * (2 ** (retry_count - 1)))  # Max 5 minutes
            next_retry = datetime.now() + timedelta(seconds=backoff_seconds)
            
            # Update state
            self.state_manager.update_level_attempt(
                market, level_number, 'failed', retry_count, next_retry
            )
            
            logger.warning(f"Dip rebuy failed for {market} level {level_number} "
                          f"(attempt {retry_count}): {error_msg}. "
                          f"Next retry: {next_retry.strftime('%H:%M:%S')}")
            
        except Exception as e:
            logger.error(f"Error handling rebuy failure for {market}: {e}")
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get a summary of current dip buying status."""
        summary = {
            'enabled': self.config.enabled,
            'monitor_running': self._monitor_thread and self._monitor_thread.is_alive(),
            'tracking_summary': self.state_manager.get_tracking_summary()
        }
        
        if self.market_filter:
            summary['market_conditions'] = self.market_filter.get_market_summary()
        
        return summary
    
    def force_check_asset(self, market: str) -> Optional[RebuyDecision]:
        """
        Force a dip check for a specific asset (for testing/debugging).
        
        Returns the rebuy decision without executing it.
        """
        asset_state = self.state_manager.get_asset_state(market)
        if not asset_state:
            logger.warning(f"No dip tracking state found for {market}")
            return None
        
        try:
            # Get current price
            response = self.api.send_request("GET", f"/ticker/price?market={market}")
            if not response or 'price' not in response:
                return None
            
            current_price = Decimal(str(response['price']))
            
            # Reconstruct asset info
            asset_info = AssetSaleInfo(
                market=market,
                sell_price=Decimal(asset_state['sell_price']),
                sell_timestamp=datetime.fromisoformat(asset_state['sell_timestamp']),
                trigger_reason=asset_state.get('trigger_reason', 'unknown')
            )
            
            return self.evaluator.should_rebuy(asset_info, current_price, asset_state)
            
        except Exception as e:
            logger.error(f"Error in force check for {market}: {e}")
            return None