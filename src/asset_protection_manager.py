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

from config import AssetProtectionConfig, TradingConfig, DipLevel, ProfitLevel
from requests_handler import BitvavoAPI
from volatility_calculator import VolatilityCalculator
from protected_asset_state import ProtectedAssetStateManager, ProtectedAssetInfo
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
        """Check for DCA buying opportunities."""
        try:
            if not self.config.dca_levels:
                return
            
            # Calculate current drop percentage from entry price
            drop_pct = ((asset_info.entry_price - current_price) / asset_info.entry_price) * 100
            
            # Find eligible DCA levels
            for i, dca_level in enumerate(self.config.dca_levels, 1):
                if drop_pct >= dca_level.threshold_pct and i not in asset_info.completed_dca_levels:
                    # Calculate DCA amount
                    dca_amount = self.config.max_protection_budget * dca_level.capital_allocation
                    
                    logger.info(f"🎯 DCA opportunity: {market} level {i} at {drop_pct:.1f}% drop")
                    
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