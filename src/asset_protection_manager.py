#!/usr/bin/env python3
"""
Asset Protection Manager - Main orchestration class for protecting existing assets
"""

import logging
import threading
import time
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List

try:
    from .config import AssetProtectionConfig, TradingConfig, DipLevel, ProfitLevel
    from .requests_handler import BitvavoAPI
    from .volatility_calculator import VolatilityCalculator
    from .protected_asset_state import ProtectedAssetStateManager, ProtectedAssetInfo
    from .enhanced_asset_protection import EnhancedAssetProtectionManager
    from .circuit_breaker import (
        CircuitBreaker, CircuitBreakerError, 
        create_api_circuit_breaker, create_trading_circuit_breaker, create_balance_circuit_breaker
    )
except ImportError:
    from config import AssetProtectionConfig, TradingConfig, DipLevel, ProfitLevel
    from requests_handler import BitvavoAPI
    from volatility_calculator import VolatilityCalculator
    from protected_asset_state import ProtectedAssetStateManager, ProtectedAssetInfo
    from enhanced_asset_protection import EnhancedAssetProtectionManager
    from circuit_breaker import (
        CircuitBreaker, CircuitBreakerError, 
        create_api_circuit_breaker, create_trading_circuit_breaker, create_balance_circuit_breaker
    )

logger = logging.getLogger(__name__)


class AssetProtectionManager:
    """
    Main orchestration class for the asset protection strategy.
    
    Responsibilities:
    - Monitor protected assets for volatility and price movements
    - Execute dynamic stop-loss orders based on volatility
    - Implement DCA buying on significant dips
    - Execute profit taking on significant pumps
    - Manage portfolio rebalancing
    - Coordinate with existing trading systems
    """
    
    def __init__(self, api: BitvavoAPI, config: AssetProtectionConfig, 
                 trading_config: TradingConfig, data_dir: Path, 
                 check_interval: int = 30):
        self.api = api
        self.config = config
        self.trading_config = trading_config
        self.check_interval = check_interval
        
        # Initialize components
        self.volatility_calc = VolatilityCalculator(api)
        self.state_manager = ProtectedAssetStateManager(data_dir)
        self.enhanced_protection = EnhancedAssetProtectionManager(self)
        
        # Initialize circuit breakers for system stability
        self.api_circuit_breaker = create_api_circuit_breaker()
        self.trading_circuit_breaker = create_trading_circuit_breaker()
        self.balance_circuit_breaker = create_balance_circuit_breaker()
        
        # Threading control
        self._stop_event = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # Budget tracking
        self._daily_spent = Decimal('0')
        self._last_budget_reset = datetime.now().date()
        
        logger.info(f"AssetProtectionManager initialized (enabled: {config.enabled})")
        if config.enabled and config.protected_assets:
            logger.info(f"Protected assets: {', '.join(config.protected_assets)}")
            logger.info(f"Protection budget: €{config.max_protection_budget}")
    
    def start(self) -> None:
        """Start the asset protection monitoring service."""
        if not self.config.enabled:
            logger.info("Asset protection disabled - not starting monitor")
            return
        
        if not self.config.protected_assets:
            logger.info("No protected assets configured - not starting monitor")
            return
        
        if self._monitor_thread and self._monitor_thread.is_alive():
            logger.warning("Asset protection monitor already running")
            return
        
        logger.info("Starting asset protection monitoring service")
        self._stop_event.clear()
        
        # Initialize protected assets if not already tracked
        self._initialize_protected_assets()
        
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name="AssetProtectionMonitor",
            daemon=True
        )
        self._monitor_thread.start()
        
        logger.info("Asset protection monitoring started")
    
    def stop(self) -> None:
        """Stop the asset protection monitoring service."""
        logger.info("Stopping asset protection monitoring service")
        self._stop_event.set()
        
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=10)
            if self._monitor_thread.is_alive():
                logger.warning("Asset protection monitor thread did not stop cleanly")
        
        logger.info("Asset protection monitoring stopped")
    
    def _initialize_protected_assets(self) -> None:
        """Initialize protected assets that aren't already being tracked."""
        try:
            existing_assets = self.state_manager.get_all_protected_assets()
            
            for market in self.config.protected_assets:
                if market not in existing_assets:
                    logger.info(f"Initializing protection for new asset: {market}")
                    
                    # Get current market price
                    current_price = self._get_current_price(market)
                    if current_price is None:
                        logger.error(f"Could not get current price for {market}")
                        continue
                    
                    # Get current balance
                    current_balance = self._get_current_balance(market)
                    if current_balance <= 0:
                        logger.warning(f"No balance found for {market} - skipping protection")
                        continue
                    
                    # Calculate current EUR value
                    current_value_eur = current_balance * current_price
                    
                    # Get target allocation if configured
                    target_allocation = self.config.target_allocations.get(market)
                    
                    # Add to state management
                    self.state_manager.add_protected_asset(
                        market=market,
                        entry_price=current_price,  # Use current price as entry
                        initial_investment_eur=current_value_eur,
                        target_allocation_pct=target_allocation
                    )
                    
                    print(f"🛡️  Added {market} to asset protection: {current_balance:.8f} @ €{current_price}")
                    
        except Exception as e:
            logger.error(f"Error initializing protected assets: {e}")
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop that runs in a separate thread."""
        logger.info("Asset protection monitor loop started")
        
        try:
            while not self._stop_event.is_set():
                try:
                    self._reset_daily_budget_if_needed()
                    self._check_all_protected_assets()
                    self._update_volatility_stops()
                    
                    if self.config.rebalancing_enabled:
                        self._check_portfolio_rebalancing()
                    
                except Exception as e:
                    logger.error(f"Error in asset protection monitoring loop: {e}")
                
                # Sleep with interruptible pattern
                for _ in range(self.check_interval):
                    if self._stop_event.is_set():
                        break
                    time.sleep(1)
                        
        except Exception as e:
            logger.error(f"Fatal error in asset protection monitor loop: {e}")
        finally:
            logger.info("Asset protection monitor loop exiting")
    
    def _check_all_protected_assets(self) -> None:
        """Check all protected assets for trading opportunities."""
        protected_assets = self.state_manager.get_all_protected_assets()
        
        if not protected_assets:
            logger.debug("No protected assets to monitor")
            return
        
        logger.debug(f"Monitoring {len(protected_assets)} protected assets")
        
        for market, asset_info in protected_assets.items():
            try:
                self._check_asset_opportunities(market, asset_info)
            except Exception as e:
                logger.error(f"Error checking opportunities for {market}: {e}")
    
    def _check_asset_opportunities(self, market: str, asset_info: ProtectedAssetInfo) -> None:
        """Check a specific asset for protection opportunities."""
        try:
            # Get current market price
            current_price = self._get_current_price(market)
            if current_price is None:
                logger.debug(f"No price data for {market}")
                return
            
            # Update price history for momentum tracking (upgrade guide implementation)
            self.state_manager.update_price_history(market, current_price)
            
            # Update lowest price tracking for recovery rebuys
            if self.config.recovery_rebuy_enabled:
                self.state_manager.update_lowest_price_tracking(market, current_price)
            
            # Check daily trade limits
            if not self.state_manager.can_trade_today(market, self.config.max_daily_trades):
                logger.debug(f"Daily trade limit reached for {market}")
                return
            
            # Check emergency stop loss
            if self._check_emergency_stop_loss(market, asset_info, current_price):
                return  # Asset emergency sold, stop processing
            
            # Check dynamic stop loss
            if self._check_dynamic_stop_loss(market, asset_info, current_price):
                return  # Asset sold, stop processing
            
            # Check DCA opportunities (buying on dips)
            if self.config.dca_enabled:
                self._check_dca_opportunities(market, asset_info, current_price)
            
            # Check profit taking opportunities
            if self.config.profit_taking_enabled:
                self._check_profit_taking_opportunities(market, asset_info, current_price)
            
            # Check swing trading opportunities
            if self.config.swing_trading_enabled:
                self._check_swing_trading_opportunities(market, asset_info, current_price)
                # Check for recovery rebuys (buy on recoveries from any significant drop)
                self._check_recovery_rebuy_opportunities(market, asset_info, current_price)
            
            # Check enhanced protection opportunities (trailing profit + dynamic buybacks)
            self.enhanced_protection.check_enhanced_opportunities(market, current_price, asset_info)
                
        except Exception as e:
            logger.error(f"Error checking opportunities for {market}: {e}")
    
    def _check_emergency_stop_loss(self, market: str, asset_info: ProtectedAssetInfo, current_price: Decimal) -> bool:
        """Check for emergency stop loss trigger."""
        try:
            # Calculate current loss percentage
            loss_pct = ((asset_info.entry_price - current_price) / asset_info.entry_price) * 100
            
            if loss_pct >= self.config.emergency_stop_loss_pct:
                logger.warning(f"🚨 EMERGENCY STOP LOSS triggered for {market}: {loss_pct:.1f}% loss")
                
                # Execute emergency sell
                success = self._execute_sell_order(market, "emergency_stop", 
                                                 f"Emergency stop loss at {loss_pct:.1f}% loss")
                
                if success:
                    # Remove from protection (position closed)
                    self.state_manager.remove_protected_asset(market)
                    print(f"💥 EMERGENCY STOP: {market} position closed at {loss_pct:.1f}% loss")
                    return True
                    
        except Exception as e:
            logger.error(f"Error checking emergency stop loss for {market}: {e}")
        
        return False
    
    def _check_dynamic_stop_loss(self, market: str, asset_info: ProtectedAssetInfo, current_price: Decimal) -> bool:
        """Check for dynamic stop loss trigger."""
        try:
            # Calculate current loss percentage
            loss_pct = ((asset_info.entry_price - current_price) / asset_info.entry_price) * 100
            
            if loss_pct >= asset_info.current_stop_loss_pct:
                logger.info(f"🛑 Dynamic stop loss triggered for {market}: {loss_pct:.1f}% loss")
                
                # Execute sell
                success = self._execute_sell_order(market, "stop_loss", 
                                                 f"Dynamic stop loss at {loss_pct:.1f}% loss")
                
                if success:
                    print(f"📉 STOP LOSS: {market} sold at {loss_pct:.1f}% loss (dynamic stop)")
                    return True
                    
        except Exception as e:
            logger.error(f"Error checking dynamic stop loss for {market}: {e}")
        
        return False
    
    def _check_dca_opportunities(self, market: str, asset_info: ProtectedAssetInfo, current_price: Decimal) -> None:
        """Check for DCA buying opportunities with upgrade guide improvements."""
        try:
            if not self.config.dca_levels:
                return
            
            # Calculate current drop percentage from entry price
            drop_pct = ((asset_info.entry_price - current_price) / asset_info.entry_price) * 100
            
            # Check loss circuit breaker (upgrade guide implementation)
            if self._is_loss_circuit_breaker_triggered(market, current_price):
                logger.info(f"🚨 Loss circuit breaker active for {market} - skipping DCA")
                return
            
            # Check basic trend analysis for downtrend (upgrade guide implementation)
            if self._is_downtrend_confirmed(market, current_price):
                logger.debug(f"📉 Confirmed downtrend for {market} - being more selective with DCA")
            
            # Find eligible DCA levels
            for i, dca_level in enumerate(self.config.dca_levels, 1):
                if drop_pct >= dca_level.threshold_pct and i not in asset_info.completed_dca_levels:
                    # Calculate base DCA amount
                    base_dca_amount = self.config.max_protection_budget * dca_level.capital_allocation
                    
                    # Apply directional analysis (upgrade guide implementation)
                    dca_amount = self._calculate_directional_dca_amount(market, current_price, base_dca_amount)
                    
                    if dca_amount <= 0:
                        logger.info(f"📊 DCA skipped for {market} level {i}: directional analysis suggests waiting")
                        continue
                    
                    # Check position size limits (upgrade guide implementation)
                    if not self._check_position_size_limits(market, dca_amount):
                        logger.warning(f"⚠️ DCA skipped for {market} level {i}: would exceed position size limits")
                        continue
                    
                    logger.info(f"🎯 DCA opportunity: {market} level {i} at {drop_pct:.1f}% drop (amount: €{dca_amount})")
                    
                    # Execute DCA buy (budget checking happens inside _execute_buy_order)
                    if self._execute_buy_order(market, dca_amount, "dca_buy", 
                                             f"DCA level {i}: {drop_pct:.1f}% drop"):
                        self.state_manager.mark_dca_level_completed(market, i)
                        print(f"🛒 DCA BUY: {market} Level {i} - €{dca_amount} at €{current_price}")
                    else:
                        logger.debug(f"Failed to execute DCA buy for {market} level {i}")
                        
        except Exception as e:
            logger.error(f"Error checking DCA opportunities for {market}: {e}")
    
    def _check_profit_taking_opportunities(self, market: str, asset_info: ProtectedAssetInfo, current_price: Decimal) -> None:
        """Check for profit taking opportunities."""
        try:
            if not self.config.profit_levels:
                return
            
            # Calculate current gain percentage from entry price
            gain_pct = ((current_price - asset_info.entry_price) / asset_info.entry_price) * 100
            
            # Find eligible profit levels
            for i, profit_level in enumerate(self.config.profit_levels, 1):
                if gain_pct >= profit_level.threshold_pct and i not in asset_info.completed_profit_levels:
                    logger.info(f"💰 Profit taking opportunity: {market} level {i} at {gain_pct:.1f}% gain")
                    
                    # Execute partial sell
                    if self._execute_partial_sell(market, profit_level.position_allocation, "profit_sell",
                                                f"Profit taking level {i}: {gain_pct:.1f}% gain"):
                        self.state_manager.mark_profit_level_completed(market, i)
                        print(f"💸 PROFIT TAKE: {market} Level {i} - {profit_level.position_allocation:.0%} at €{current_price}")
                        
        except Exception as e:
            logger.error(f"Error checking profit taking opportunities for {market}: {e}")
    
    def _check_swing_trading_opportunities(self, market: str, asset_info: ProtectedAssetInfo, current_price: Decimal) -> None:
        """Check for swing trading opportunities (sell on drops, rebuy on bigger drops)."""
        if not self.config.swing_trading_enabled:
            return
            
        try:
            # Use swing entry price if available, otherwise use original entry price
            base_price = asset_info.swing_entry_price or asset_info.entry_price
            
            # Calculate current drop percentage from base price
            drop_pct = ((base_price - current_price) / base_price) * 100
            
            # Process swing levels in order
            for i, swing_level in enumerate(self.config.swing_levels, 1):
                if drop_pct >= swing_level.threshold_pct:
                    
                    if swing_level.action == 'sell':
                        # Check if this sell level is already completed
                        if i not in asset_info.completed_swing_sell_levels:
                            logger.info(f"🔄 SWING SELL opportunity: {market} level {i} at {drop_pct:.1f}% drop")
                            
                            # Execute swing sell
                            if self._execute_swing_sell(market, swing_level.allocation, i, drop_pct):
                                print(f"📉 SWING SELL: {market} Level {i} - {swing_level.allocation:.0%} at €{current_price}")
                    
                    elif swing_level.action == 'rebuy':
                        # Check if this rebuy level is already completed
                        if i not in asset_info.completed_swing_rebuy_levels:
                            logger.info(f"🔄 SWING REBUY opportunity: {market} level {i} at {drop_pct:.1f}% drop")
                            
                            # Apply trend analysis for rebuys (upgrade guide implementation)
                            if self._is_downtrend_confirmed(market, current_price):
                                # Only rebuy at deeper levels during downtrends
                                if drop_pct < 35:  # Require -35% drop minimum
                                    logger.info(f"⏳ SWING REBUY delayed: {market} in confirmed downtrend, waiting for deeper drop")
                                    continue
                            
                            # Execute swing rebuy using cash reserves
                            if self._execute_swing_rebuy(market, swing_level.allocation, i, drop_pct):
                                print(f"🛒 SWING REBUY: {market} Level {i} - {swing_level.allocation:.0%} at €{current_price}")
                        
        except Exception as e:
            logger.error(f"Error checking swing trading opportunities for {market}: {e}")
    
    def _execute_swing_sell(self, market: str, position_allocation: Decimal, level: int, drop_pct: float) -> bool:
        """Execute a swing trading sell order."""
        try:
            # Get current balance
            current_balance = self._get_current_balance(market)
            if current_balance <= 0:
                logger.warning(f"No balance to swing sell for {market}")
                return False
            
            # Calculate amount to sell
            sell_amount = current_balance * position_allocation
            
            # Get current price for EUR calculation
            current_price = self._get_current_price(market)
            if current_price is None:
                logger.error(f"Could not get current price for swing sell {market}")
                return False
            
            # Place market sell order
            body = {
                'market': market,
                'side': 'sell',
                'orderType': 'market',
                'amount': str(sell_amount),
                'operatorId': self.trading_config.operator_id
            }
            
            # Use trading circuit breaker for sell order execution
            response = self.trading_circuit_breaker.call(
                f"swing_sell_{market}_level_{level}",
                self.api.send_request,
                "POST",
                "/order",
                body
            )
            
            if response:
                amount_eur = sell_amount * current_price
                
                # Calculate cash to add to reserves (keep percentage for rebuying)
                cash_reserve_amount = amount_eur * (self.config.swing_cash_reserve_pct / 100)
                
                # Add to swing cash reserves
                self.state_manager.add_swing_cash_reserve(market, cash_reserve_amount)
                
                # Record the trade
                self.state_manager.record_trade(
                    market=market,
                    trade_type="swing_sell",
                    price=current_price,
                    amount_eur=amount_eur,
                    amount_crypto=sell_amount,
                    reason=f"Swing sell level {level}: {drop_pct:.1f}% drop"
                )
                
                # Mark level as completed
                self.state_manager.mark_swing_level_completed(market, level, 'sell')
                
                # Update swing entry price for future calculations
                self.state_manager.update_swing_entry_price(market, current_price)
                
                logger.info(f"Executed swing sell for {market}: {sell_amount:.8f} at €{current_price}, reserved €{cash_reserve_amount:.2f}")
                return True
            else:
                logger.error(f"Swing sell order failed for {market} level {level}")
                return False
        
        except CircuitBreakerError as e:
            logger.warning(f"Trading circuit breaker blocked swing sell for {market}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error executing swing sell for {market}: {e}")
            return False
    
    def _execute_swing_rebuy(self, market: str, cash_allocation: Decimal, level: int, drop_pct: float) -> bool:
        """Execute a swing trading rebuy order using cash reserves."""
        try:
            # Check available cash reserves
            available_cash = self.state_manager.get_swing_cash_reserve(market)
            if available_cash <= 0:
                logger.debug(f"No swing cash reserves available for {market} rebuy")
                return False
            
            # Calculate rebuy amount
            rebuy_amount_eur = available_cash * cash_allocation
            
            # Get current price
            current_price = self._get_current_price(market)
            if current_price is None:
                logger.error(f"Could not get current price for swing rebuy {market}")
                return False
            
            # Use swing cash reserves
            if not self.state_manager.use_swing_cash_reserve(market, rebuy_amount_eur):
                logger.debug(f"Failed to reserve swing cash for {market} rebuy")
                return False
            
            # Place market buy order
            body = {
                'market': market,
                'side': 'buy',
                'orderType': 'market',
                'amountQuote': str(rebuy_amount_eur),
                'operatorId': self.trading_config.operator_id
            }
            
            try:
                # Use trading circuit breaker for buy order execution
                response = self.trading_circuit_breaker.call(
                    f"swing_rebuy_{market}_level_{level}",
                    self.api.send_request,
                    "POST",
                    "/order",
                    body
                )
                
                if response:
                    # Calculate crypto amount received (approximate)
                    crypto_amount = rebuy_amount_eur / current_price
                    
                    # Record the trade
                    self.state_manager.record_trade(
                        market=market,
                        trade_type="swing_rebuy",
                        price=current_price,
                        amount_eur=rebuy_amount_eur,
                        amount_crypto=crypto_amount,
                        reason=f"Swing rebuy level {level}: {drop_pct:.1f}% drop"
                    )
                    
                    # Mark level as completed
                    self.state_manager.mark_swing_level_completed(market, level, 'rebuy')
                    
                    logger.info(f"Executed swing rebuy for {market}: €{rebuy_amount_eur} at €{current_price}")
                    return True
                else:
                    logger.error(f"Swing rebuy order failed for {market} level {level}")
                    # Return cash to reserves since order failed
                    self.state_manager.add_swing_cash_reserve(market, rebuy_amount_eur)
                    return False
                    
            except CircuitBreakerError as e:
                logger.warning(f"Trading circuit breaker blocked swing rebuy for {market}: {e}")
                # Return cash to reserves since order was blocked
                self.state_manager.add_swing_cash_reserve(market, rebuy_amount_eur)
                return False
                
        except Exception as e:
            logger.error(f"Error executing swing rebuy for {market}: {e}")
            return False
    
    def _update_volatility_stops(self) -> None:
        """Update dynamic stop losses based on current volatility."""
        try:
            protected_assets = self.state_manager.get_all_protected_assets()
            
            for market, asset_info in protected_assets.items():
                # Check if volatility update is needed (every few hours)
                hours_since_check = (datetime.now() - asset_info.last_volatility_check).total_seconds() / 3600
                
                if hours_since_check >= 4:  # Update every 4 hours
                    new_stop_pct = self.volatility_calc.get_volatility_adjusted_stop_loss(
                        market=market,
                        base_stop_pct=self.config.base_stop_loss_pct,
                        volatility_multiplier=self.config.volatility_multiplier,
                        window_hours=self.config.volatility_window_hours
                    )
                    
                    if abs(new_stop_pct - asset_info.current_stop_loss_pct) > Decimal('1.0'):
                        logger.info(f"Updating {market} stop loss: {asset_info.current_stop_loss_pct:.1f}% → {new_stop_pct:.1f}%")
                        self.state_manager.update_stop_loss(market, new_stop_pct)
                        
        except Exception as e:
            logger.error(f"Error updating volatility stops: {e}")
    
    def _check_portfolio_rebalancing(self) -> None:
        """Check if portfolio rebalancing is needed."""
        try:
            if not self.config.target_allocations:
                return
            
            # Get current portfolio state
            portfolio_summary = self.state_manager.get_portfolio_summary()
            total_value = Decimal(str(portfolio_summary['total_current_value_eur']))
            
            if total_value <= 0:
                return
            
            # Check each asset's allocation drift
            for market, target_pct in self.config.target_allocations.items():
                asset_info = self.state_manager.get_asset_info(market)
                if not asset_info:
                    continue
                
                # Calculate current allocation
                current_allocation_pct = (asset_info.current_position_eur / total_value)
                allocation_drift = abs(current_allocation_pct - target_pct) * 100
                
                if allocation_drift >= self.config.rebalancing_threshold_pct:
                    logger.info(f"Rebalancing needed for {market}: "
                              f"current {current_allocation_pct:.1%}, target {target_pct:.1%}")
                    
                    # TODO: Implement rebalancing logic
                    # This would involve buying/selling to restore target allocation
                    
        except Exception as e:
            logger.error(f"Error checking portfolio rebalancing: {e}")
    
    def _execute_buy_order(self, market: str, amount_eur: Decimal, trade_type: str, reason: str) -> bool:
        """Execute a buy order for asset protection with thread-safe budget management."""
        # Thread-safe budget reservation
        with self._lock:
            if not self._has_daily_budget(amount_eur):
                logger.debug(f"Insufficient daily budget for {market} {trade_type}: need €{amount_eur}, available €{self.config.max_protection_budget - self._daily_spent}")
                return False
            
            # Reserve budget immediately to prevent race conditions
            self._daily_spent += amount_eur
            logger.debug(f"Reserved €{amount_eur} budget for {market} {trade_type} (remaining: €{self.config.max_protection_budget - self._daily_spent})")
        
        try:
            # Get current price for amount calculation (outside lock for API call)
            current_price = self._get_current_price(market)
            if current_price is None:
                logger.error(f"Could not get current price for {market}")
                # Rollback budget reservation on failure
                with self._lock:
                    self._daily_spent -= amount_eur
                return False
            
            # Place market buy order
            body = {
                'market': market,
                'side': 'buy',
                'orderType': 'market',
                'amountQuote': str(amount_eur),
                'operatorId': self.trading_config.operator_id
            }
            
            # Use trading circuit breaker for order execution
            response = self.trading_circuit_breaker.call(
                f"place_buy_order_{market}_{trade_type}",
                self.api.send_request,
                "POST",
                "/order",
                body
            )
            if response:
                # Calculate crypto amount received (approximate)
                crypto_amount = amount_eur / current_price
                
                # Record the trade
                self.state_manager.record_trade(
                    market=market,
                    trade_type=trade_type,
                    price=current_price,
                    amount_eur=amount_eur,
                    amount_crypto=crypto_amount,
                    reason=reason
                )
                
                logger.info(f"Executed {trade_type} for {market}: €{amount_eur} at €{current_price}")
                return True
            else:
                logger.error(f"Order request failed for {market} {trade_type}")
                # Rollback budget reservation on API failure
                with self._lock:
                    self._daily_spent -= amount_eur
                return False
            
        except CircuitBreakerError as e:
            logger.warning(f"Trading circuit breaker blocked buy order for {market}: {e}")
            # Rollback budget reservation
            with self._lock:
                self._daily_spent -= amount_eur
            return False
        except Exception as e:
            logger.error(f"Error executing buy order for {market}: {e}")
            # Rollback budget reservation on exception
            with self._lock:
                self._daily_spent -= amount_eur
            return False
    
    def _execute_sell_order(self, market: str, trade_type: str, reason: str) -> bool:
        """Execute a sell order for the entire position."""
        try:
            # Get current balance
            current_balance = self._get_current_balance(market)
            if current_balance <= 0:
                logger.warning(f"No balance to sell for {market}")
                return False
            
            # Place market sell order
            body = {
                'market': market,
                'side': 'sell',
                'orderType': 'market',
                'amount': str(current_balance),
                'operatorId': self.trading_config.operator_id
            }
            
            # Use trading circuit breaker for sell order execution
            response = self.trading_circuit_breaker.call(
                f"place_sell_order_{market}_{trade_type}",
                self.api.send_request,
                "POST",
                "/order",
                body
            )
            if response:
                current_price = self._get_current_price(market)
                amount_eur = current_balance * current_price if current_price else Decimal('0')
                
                # Record the trade
                self.state_manager.record_trade(
                    market=market,
                    trade_type=trade_type,
                    price=current_price or Decimal('0'),
                    amount_eur=amount_eur,
                    amount_crypto=current_balance,
                    reason=reason
                )
                
                logger.info(f"Executed {trade_type} for {market}: {current_balance} at €{current_price}")
                return True
        
        except CircuitBreakerError as e:
            logger.warning(f"Trading circuit breaker blocked sell order for {market}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error executing sell order for {market}: {e}")
        
        return False
    
    def _execute_partial_sell(self, market: str, percentage: Decimal, trade_type: str, reason: str) -> bool:
        """Execute a partial sell order."""
        try:
            # Get current balance
            current_balance = self._get_current_balance(market)
            if current_balance <= 0:
                return False
            
            # Calculate amount to sell
            sell_amount = current_balance * percentage
            
            # Place market sell order
            body = {
                'market': market,
                'side': 'sell',
                'orderType': 'market',
                'amount': str(sell_amount),
                'operatorId': self.trading_config.operator_id
            }
            
            # Use trading circuit breaker for sell order execution
            response = self.trading_circuit_breaker.call(
                f"place_partial_sell_order_{market}_{trade_type}",
                self.api.send_request,
                "POST",
                "/order",
                body
            )
            if response:
                current_price = self._get_current_price(market)
                amount_eur = sell_amount * current_price if current_price else Decimal('0')
                
                # Record the trade
                self.state_manager.record_trade(
                    market=market,
                    trade_type=trade_type,
                    price=current_price or Decimal('0'),
                    amount_eur=amount_eur,
                    amount_crypto=sell_amount,
                    reason=reason
                )
                
                logger.info(f"Executed {trade_type} for {market}: {sell_amount} ({percentage:.0%}) at €{current_price}")
                return True
        
        except CircuitBreakerError as e:
            logger.warning(f"Trading circuit breaker blocked partial sell order for {market}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error executing partial sell for {market}: {e}")
        
        return False
    
    def _get_current_price(self, market: str) -> Optional[Decimal]:
        """Get current market price with circuit breaker protection."""
        try:
            # Use circuit breaker to protect against repeated API failures
            response = self.api_circuit_breaker.call(
                f"get_price_{market}",
                self.api.send_request,
                "GET",
                f"/ticker/price?market={market}"
            )
            
            # Validate response structure
            if not response:
                logger.warning(f"Empty response for {market} price")
                return None
                
            if not isinstance(response, dict):
                logger.error(f"Invalid response type for {market} price: {type(response)}")
                return None
                
            if 'price' not in response:
                logger.error(f"Missing 'price' field in response for {market}: {response}")
                return None
            
            # Validate and convert price
            price_value = response['price']
            if price_value is None or price_value == '':
                logger.warning(f"Null or empty price for {market}")
                return None
                
            try:
                price = Decimal(str(price_value))
                if price <= 0:
                    logger.error(f"Invalid price value for {market}: {price}")
                    return None
                return price
            except (ValueError, InvalidOperation) as e:
                logger.error(f"Cannot convert price to decimal for {market}: '{price_value}' - {e}")
                return None
            
        except CircuitBreakerError as e:
            logger.warning(f"Circuit breaker blocked price request for {market}: {e}")
        except ConnectionError as e:
            logger.warning(f"Network error getting price for {market}: {e}")
        except TimeoutError as e:
            logger.warning(f"Timeout error getting price for {market}: {e}")
        except KeyError as e:
            logger.error(f"Unexpected response structure for {market}: missing key {e}")
        except Exception as e:
            logger.error(f"Unexpected error getting price for {market}: {e}")
            
        return None
    
    def _get_current_balance(self, market: str) -> Decimal:
        """Get current balance for the base currency of a market with circuit breaker protection."""
        try:
            # Extract symbol from market (e.g., 'BTC' from 'BTC-EUR')
            if '-' not in market:
                logger.error(f"Invalid market format for balance lookup: {market}")
                return Decimal('0')
                
            symbol = market.split('-')[0]
            
            # Use circuit breaker to protect against repeated balance API failures
            balance_response = self.balance_circuit_breaker.call(
                f"get_balance_{symbol}",
                self.api.send_request,
                "GET",
                "/balance"
            )
            
            # Validate response structure
            if not balance_response:
                logger.warning(f"Empty response for balance request")
                return Decimal('0')
                
            if not isinstance(balance_response, list):
                logger.error(f"Invalid balance response type: {type(balance_response)}")
                return Decimal('0')
            
            # Search for the symbol in balance list
            for balance_item in balance_response:
                if not isinstance(balance_item, dict):
                    logger.warning(f"Invalid balance item type: {type(balance_item)}")
                    continue
                    
                if balance_item.get('symbol') == symbol:
                    available = balance_item.get('available', '0')
                    
                    # Validate and convert balance
                    try:
                        balance = Decimal(str(available))
                        if balance < 0:
                            logger.warning(f"Negative balance for {symbol}: {balance}")
                            return Decimal('0')
                        return balance
                    except (ValueError, InvalidOperation) as e:
                        logger.error(f"Cannot convert balance to decimal for {symbol}: '{available}' - {e}")
                        return Decimal('0')
            
            # Symbol not found in balance list
            logger.debug(f"Symbol {symbol} not found in balance response")
            return Decimal('0')
            
        except CircuitBreakerError as e:
            logger.warning(f"Circuit breaker blocked balance request for {market}: {e}")
        except ConnectionError as e:
            logger.warning(f"Network error getting balance for {market}: {e}")
        except TimeoutError as e:
            logger.warning(f"Timeout error getting balance for {market}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error getting balance for {market}: {e}")
        
        return Decimal('0')
    
    def _has_daily_budget(self, amount: Decimal) -> bool:
        """Check if there's sufficient daily budget for a trade."""
        return (self._daily_spent + amount) <= self.config.max_protection_budget
    
    def _reset_daily_budget_if_needed(self) -> None:
        """Reset daily budget counter if it's a new day."""
        today = datetime.now().date()
        if today > self._last_budget_reset:
            self._daily_spent = Decimal('0')
            self._last_budget_reset = today
            logger.debug("Daily protection budget reset")
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get a summary of current asset protection status."""
        try:
            portfolio_summary = self.state_manager.get_portfolio_summary()
            volatility_cache_stats = self.volatility_calc.get_cache_stats()
            
            summary = {
                'enabled': self.config.enabled,
                'monitor_running': self._monitor_thread and self._monitor_thread.is_alive(),
                'protected_assets_count': portfolio_summary.get('total_assets', 0),
                'total_protected_value_eur': portfolio_summary.get('total_current_value_eur', 0),
                'total_invested_eur': portfolio_summary.get('total_invested_eur', 0),
                'unrealized_pnl_pct': portfolio_summary.get('unrealized_pnl_pct', 0),
                'max_drawdown_pct': portfolio_summary.get('max_drawdown_pct', 0),
                'daily_budget_used_eur': float(self._daily_spent),
                'daily_budget_remaining_eur': float(self.config.max_protection_budget - self._daily_spent),
                'volatility_cache_entries': volatility_cache_stats.get('valid_entries', 0),
                'circuit_breakers': {
                    'api': self.api_circuit_breaker.get_status(),
                    'trading': self.trading_circuit_breaker.get_status(),
                    'balance': self.balance_circuit_breaker.get_status()
                }
            }
            
            if self.config.protected_assets:
                summary['protected_markets'] = self.config.protected_assets
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating status summary: {e}")
            return {'enabled': self.config.enabled, 'error': str(e)}
    
    # =========================================================================
    # UPGRADE GUIDE IMPLEMENTATIONS
    # =========================================================================
    
    def _check_position_size_limits(self, market: str, additional_amount_eur: Decimal) -> bool:
        """Check if additional purchase would exceed position size limits."""
        if not self.config.position_size_check_enabled:
            return True
            
        asset_info = self.state_manager.get_asset_info(market)
        if not asset_info:
            return True
        
        # Calculate what position would be after purchase
        current_position_value = asset_info.current_position_eur
        total_after_purchase = current_position_value + additional_amount_eur
        
        # Check against initial investment multiplier
        max_allowed = asset_info.total_invested_eur * self.config.max_position_multiplier
        
        if total_after_purchase > max_allowed:
            logger.warning(f"Position size limit exceeded for {market}: "
                         f"would be €{total_after_purchase:.2f} vs max €{max_allowed:.2f} "
                         f"({self.config.max_position_multiplier}x initial)")
            return False
            
        return True
    
    def _is_loss_circuit_breaker_triggered(self, market: str, current_price: Decimal) -> bool:
        """Check if losses exceed circuit breaker threshold."""
        if not self.config.circuit_breaker_enabled:
            return False
            
        asset_info = self.state_manager.get_asset_info(market)
        if not asset_info:
            return False
        
        # Calculate loss from original entry
        loss_pct = ((asset_info.entry_price - current_price) / asset_info.entry_price) * 100
        
        if loss_pct >= self.config.loss_circuit_breaker_pct:
            logger.warning(f"🚨 LOSS CIRCUIT BREAKER triggered for {market}: {loss_pct:.1f}% loss")
            return True
            
        return False
    
    def _is_downtrend_confirmed(self, market: str, current_price: Decimal) -> bool:
        """Basic trend analysis - check if we're in confirmed downtrend."""
        asset_info = self.state_manager.get_asset_info(market)
        if not asset_info:
            return False
        
        # Simple trend: if down >15% from entry, consider downtrend
        drop_from_entry = ((asset_info.entry_price - current_price) / asset_info.entry_price) * 100
        
        if drop_from_entry > 15:
            logger.debug(f"{market} in downtrend: {drop_from_entry:.1f}% below entry")
            return True
            
        return False
    
    def _calculate_directional_dca_amount(self, market: str, current_price: Decimal, 
                                        base_amount: Decimal) -> Decimal:
        """Calculate DCA amount based on price direction and momentum."""
        if not self.config.directional_dca_enabled:
            return base_amount
            
        # Get price momentum
        momentum = self.state_manager.get_price_momentum(market, self.config.dca_momentum_hours)
        if momentum is None:
            return base_amount
            
        # Determine if price is falling through level or bouncing off it
        if momentum >= self.config.dca_momentum_threshold:
            # Price bouncing up (recovery) - good time to buy more
            adjusted_amount = base_amount * self.config.dca_bouncing_multiplier
            logger.info(f"🔄 DIRECTIONAL DCA: {market} bouncing (+{momentum:.1f}%) - "
                       f"increasing to {self.config.dca_bouncing_multiplier}x")
            return adjusted_amount
            
        elif momentum <= -self.config.dca_momentum_threshold:
            # Price falling through level - reduce exposure
            adjusted_amount = base_amount * self.config.dca_falling_multiplier
            logger.info(f"📉 DIRECTIONAL DCA: {market} falling ({momentum:.1f}%) - "
                       f"reducing to {self.config.dca_falling_multiplier}x")
            return adjusted_amount
            
        else:
            # Momentum neutral - use base amount
            logger.debug(f"📊 DIRECTIONAL DCA: {market} momentum neutral ({momentum:.1f}%) - "
                        f"using base amount")
            return base_amount
    
    def _check_recovery_rebuy_opportunities(self, market: str, asset_info: ProtectedAssetInfo, current_price: Decimal) -> None:
        """Check for recovery rebuy opportunities (buy on bounces from any significant drop)."""
        try:
            if not self.config.recovery_rebuy_enabled:
                return
                
            # Skip if recovery rebuy already completed for this cycle
            if asset_info.recovery_rebuy_completed:
                return
                
            # Skip if no lowest price tracking yet
            if asset_info.lowest_price_since_entry is None:
                return
                
            # Check if we have swing cash reserves available
            available_cash = self.state_manager.get_swing_cash_reserve(market)
            if available_cash <= 0:
                return
            
            # Calculate the drop from entry to lowest price
            lowest_drop_pct = ((asset_info.entry_price - asset_info.lowest_price_since_entry) / asset_info.entry_price) * 100
            
            # Only track recovery if the drop was significant enough
            if lowest_drop_pct < self.config.min_recovery_threshold_pct:
                return
            
            # Calculate the bounce from lowest price
            bounce_pct = ((current_price - asset_info.lowest_price_since_entry) / asset_info.lowest_price_since_entry) * 100
            
            # Check if bounce is significant enough to trigger recovery rebuy
            if bounce_pct >= self.config.recovery_bounce_pct:
                # Calculate recovery rebuy amount
                recovery_amount = available_cash * self.config.recovery_rebuy_allocation
                
                logger.info(f"🔄 RECOVERY REBUY opportunity: {market}")
                logger.info(f"   Drop: {lowest_drop_pct:.1f}% to €{asset_info.lowest_price_since_entry}")
                logger.info(f"   Bounce: {bounce_pct:.1f}% to €{current_price}")
                logger.info(f"   Recovery rebuy: €{recovery_amount:.2f}")
                
                # Check position size limits
                if not self._check_position_size_limits(market, recovery_amount):
                    logger.warning(f"⚠️ Recovery rebuy skipped: would exceed position size limits")
                    return
                
                # Execute recovery rebuy
                if self._execute_recovery_rebuy(market, recovery_amount, bounce_pct, lowest_drop_pct):
                    print(f"🚀 RECOVERY REBUY: {market} - €{recovery_amount:.2f} on {bounce_pct:.1f}% bounce from {lowest_drop_pct:.1f}% drop")
                    
        except Exception as e:
            logger.error(f"Error checking recovery rebuy opportunities for {market}: {e}")
    
    def _execute_recovery_rebuy(self, market: str, rebuy_amount_eur: Decimal, bounce_pct: float, drop_pct: float) -> bool:
        """Execute a recovery rebuy order."""
        try:
            # Get current price
            current_price = self._get_current_price(market)
            if current_price is None:
                logger.error(f"Could not get current price for recovery rebuy {market}")
                return False
            
            # Use swing cash reserves
            if not self.state_manager.use_swing_cash_reserve(market, rebuy_amount_eur):
                logger.debug(f"Failed to reserve swing cash for {market} recovery rebuy")
                return False
            
            # Place market buy order
            body = {
                'market': market,
                'side': 'buy',
                'orderType': 'market',
                'amountQuote': str(rebuy_amount_eur),
                'operatorId': self.trading_config.operator_id
            }
            
            try:
                # Use trading circuit breaker for buy order execution
                response = self.trading_circuit_breaker.call(
                    f"recovery_rebuy_{market}",
                    self.api.send_request,
                    "POST",
                    "/order",
                    body
                )
                
                if response:
                    # Calculate crypto amount received (approximate)
                    crypto_amount = rebuy_amount_eur / current_price
                    
                    # Record the trade
                    self.state_manager.record_trade(
                        market=market,
                        trade_type="recovery_rebuy",
                        price=current_price,
                        amount_eur=rebuy_amount_eur,
                        amount_crypto=crypto_amount,
                        reason=f"Recovery rebuy: {bounce_pct:.1f}% bounce from {drop_pct:.1f}% drop"
                    )
                    
                    # Mark recovery rebuy as completed for this cycle
                    self.state_manager.mark_recovery_rebuy_completed(market)
                    
                    logger.info(f"Executed recovery rebuy for {market}: €{rebuy_amount_eur} at €{current_price}")
                    return True
                else:
                    logger.error(f"Recovery rebuy order failed for {market}")
                    # Return cash to reserves since order failed
                    self.state_manager.add_swing_cash_reserve(market, rebuy_amount_eur)
                    return False
                    
            except CircuitBreakerError as e:
                logger.warning(f"Trading circuit breaker blocked recovery rebuy for {market}: {e}")
                # Return cash to reserves since order was blocked
                self.state_manager.add_swing_cash_reserve(market, rebuy_amount_eur)
                return False
                
        except Exception as e:
            logger.error(f"Error executing recovery rebuy for {market}: {e}")
            return False