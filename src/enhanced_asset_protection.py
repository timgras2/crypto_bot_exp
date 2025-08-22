#!/usr/bin/env python3
"""
Enhanced Asset Protection with Trailing Profit Taking and Dynamic Buybacks
"""

import logging
from decimal import Decimal
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class TrailingProfitState:
    """State for trailing profit taking mechanism."""
    highest_price: Decimal  # Highest price seen since entry/last reset
    current_trailing_distance: Decimal  # Current trailing distance percentage
    last_sell_price: Optional[Decimal] = None  # Price of last profit take
    last_sell_amount: Optional[Decimal] = None  # Amount of last profit take
    profit_taken_total: Decimal = Decimal('0')  # Total profit taken in EUR
    

@dataclass
class DynamicBuybackState:
    """State for dynamic buyback mechanism."""
    target_buyback_price: Optional[Decimal] = None  # Price to buy back near
    buyback_amount_eur: Optional[Decimal] = None  # EUR amount to buy back
    buyback_tolerance_pct: Decimal = Decimal('3')  # % tolerance around target price
    min_move_threshold_pct: Decimal = Decimal('2')  # Minimum % move to trigger action


class EnhancedAssetProtectionManager:
    """
    Enhanced asset protection with:
    1. Trailing profit taking (gradual sells as price rises)
    2. Dynamic buybacks near sell levels
    3. Trade cost optimization
    """
    
    def __init__(self, base_manager):
        self.base_manager = base_manager
        self.trailing_states: Dict[str, TrailingProfitState] = {}
        self.buyback_states: Dict[str, DynamicBuybackState] = {}
        
        # Configuration for enhanced features
        self.trailing_start_gain_pct = Decimal('8')  # Start trailing at +8%
        self.trailing_distance_pct = Decimal('5')    # 5% trailing distance
        self.trailing_increment_pct = Decimal('2')   # Sell 2% of position per trigger
        self.max_trailing_sells = 10                 # Max 20% of position via trailing
        
        # Trade cost optimization
        self.min_trade_value_eur = Decimal('20')     # Minimum trade value
        self.min_move_threshold_pct = Decimal('2')   # Minimum % move to trade
        
    def check_enhanced_opportunities(self, market: str, current_price: Decimal, 
                                   asset_info) -> None:
        """Check for enhanced trading opportunities."""
        try:
            # Initialize states if needed
            if market not in self.trailing_states:
                self.trailing_states[market] = TrailingProfitState(
                    highest_price=current_price,
                    current_trailing_distance=self.trailing_distance_pct
                )
            
            if market not in self.buyback_states:
                self.buyback_states[market] = DynamicBuybackState()
            
            # Check trailing profit taking
            self._check_trailing_profit_taking(market, current_price, asset_info)
            
            # Check dynamic buybacks
            self._check_dynamic_buybacks(market, current_price, asset_info)
            
        except Exception as e:
            logger.error(f"Error in enhanced asset protection for {market}: {e}")
    
    def _check_trailing_profit_taking(self, market: str, current_price: Decimal, 
                                    asset_info) -> None:
        """Implement trailing profit taking mechanism."""
        try:
            trailing_state = self.trailing_states[market]
            
            # Calculate current gain from entry
            gain_pct = ((current_price - asset_info.entry_price) / asset_info.entry_price) * 100
            
            # Update highest price seen
            if current_price > trailing_state.highest_price:
                trailing_state.highest_price = current_price
                logger.debug(f"{market}: New high €{current_price}, gain: {gain_pct:.1f}%")
            
            # Only start trailing after minimum gain threshold
            if gain_pct < self.trailing_start_gain_pct:
                return
            
            # Calculate trailing trigger price
            trailing_trigger_price = trailing_state.highest_price * (
                Decimal('1') - trailing_state.current_trailing_distance / Decimal('100')
            )
            
            # Check if price has dropped enough to trigger trailing sell
            if current_price <= trailing_trigger_price:
                
                # Check if move is significant enough (trade cost optimization)
                price_drop_pct = ((trailing_state.highest_price - current_price) / 
                                trailing_state.highest_price) * 100
                
                if price_drop_pct >= self.min_move_threshold_pct:
                    self._execute_trailing_profit_sell(market, current_price, 
                                                     trailing_state, asset_info)
                    
        except Exception as e:
            logger.error(f"Error in trailing profit taking for {market}: {e}")
    
    def _execute_trailing_profit_sell(self, market: str, current_price: Decimal,
                                    trailing_state: TrailingProfitState, asset_info) -> None:
        """Execute a trailing profit sell."""
        try:
            # Calculate sell amount (percentage of current position)
            current_balance = self.base_manager._get_current_balance(market)
            if current_balance <= 0:
                logger.warning(f"No balance for trailing sell {market}")
                return
            
            sell_amount = current_balance * (self.trailing_increment_pct / Decimal('100'))
            sell_value_eur = sell_amount * current_price
            
            # Trade cost optimization - ensure minimum trade value
            if sell_value_eur < self.min_trade_value_eur:
                logger.debug(f"Trailing sell too small for {market}: €{sell_value_eur}")
                return
            
            # Execute the sell
            body = {
                'market': market,
                'side': 'sell',
                'orderType': 'market',
                'amount': str(sell_amount),
                'operatorId': self.base_manager.trading_config.operator_id
            }
            
            response = self.base_manager.api.send_request("POST", "/order", body)
            
            if response and 'orderId' in response:
                # Update states
                trailing_state.last_sell_price = current_price
                trailing_state.last_sell_amount = sell_amount
                trailing_state.profit_taken_total += sell_value_eur
                
                # Set up dynamic buyback
                buyback_state = self.buyback_states[market]
                buyback_state.target_buyback_price = current_price * Decimal('0.97')  # 3% below sell
                buyback_state.buyback_amount_eur = sell_value_eur * Decimal('0.95')  # Keep 5% as profit
                
                logger.info(f"🎯 TRAILING SELL: {market} {self.trailing_increment_pct}% at €{current_price}")
                logger.info(f"📍 BUYBACK TARGET: €{buyback_state.target_buyback_price} for €{buyback_state.buyback_amount_eur}")
                
                # Reset trailing distance for next opportunity
                trailing_state.current_trailing_distance = self.trailing_distance_pct
                
        except Exception as e:
            logger.error(f"Error executing trailing sell for {market}: {e}")
    
    def _check_dynamic_buybacks(self, market: str, current_price: Decimal, 
                              asset_info) -> None:
        """Check for dynamic buyback opportunities."""
        try:
            buyback_state = self.buyback_states[market]
            
            # Only proceed if we have a buyback target
            if (buyback_state.target_buyback_price is None or 
                buyback_state.buyback_amount_eur is None):
                return
            
            # Calculate tolerance band around target price
            tolerance_amount = (buyback_state.target_buyback_price * 
                              buyback_state.buyback_tolerance_pct / Decimal('100'))
            
            price_lower_bound = buyback_state.target_buyback_price - tolerance_amount
            price_upper_bound = buyback_state.target_buyback_price + tolerance_amount
            
            # Check if current price is in buyback range
            if price_lower_bound <= current_price <= price_upper_bound:
                self._execute_dynamic_buyback(market, current_price, buyback_state)
                
        except Exception as e:
            logger.error(f"Error checking dynamic buybacks for {market}: {e}")
    
    def _execute_dynamic_buyback(self, market: str, current_price: Decimal,
                               buyback_state: DynamicBuybackState) -> None:
        """Execute a dynamic buyback."""
        try:
            # Execute buy order
            body = {
                'market': market,
                'side': 'buy',
                'orderType': 'market',
                'amountQuote': str(buyback_state.buyback_amount_eur),
                'operatorId': self.base_manager.trading_config.operator_id
            }
            
            response = self.base_manager.api.send_request("POST", "/order", body)
            
            if response and 'orderId' in response:
                logger.info(f"🔄 DYNAMIC BUYBACK: {market} €{buyback_state.buyback_amount_eur} at €{current_price}")
                
                # Clear buyback state (completed)
                buyback_state.target_buyback_price = None
                buyback_state.buyback_amount_eur = None
                
        except Exception as e:
            logger.error(f"Error executing dynamic buyback for {market}: {e}")
    
    def reset_asset_states(self, market: str) -> None:
        """Reset states when asset is removed or rebalanced."""
        if market in self.trailing_states:
            del self.trailing_states[market]
        if market in self.buyback_states:
            del self.buyback_states[market]
        logger.info(f"Reset enhanced protection states for {market}")
    
    def get_strategy_summary(self, market: str) -> Dict:
        """Get summary of current strategy state."""
        summary = {
            'trailing_profit_taken': Decimal('0'),
            'pending_buyback_target': None,
            'pending_buyback_amount': None
        }
        
        if market in self.trailing_states:
            summary['trailing_profit_taken'] = self.trailing_states[market].profit_taken_total
            
        if market in self.buyback_states:
            summary['pending_buyback_target'] = self.buyback_states[market].target_buyback_price
            summary['pending_buyback_amount'] = self.buyback_states[market].buyback_amount_eur
            
        return summary