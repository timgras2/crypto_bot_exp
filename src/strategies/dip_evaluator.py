#!/usr/bin/env python3
"""
Dip Buy Evaluator - Central decision engine for dip buying strategy
"""

import logging
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass

from src.config import DipBuyConfig, DipLevel

logger = logging.getLogger(__name__)


@dataclass
class RebuyDecision:
    """Decision result for a potential rebuy."""
    should_rebuy: bool
    level: Optional[int] = None
    amount_eur: Optional[Decimal] = None
    reason: str = ""
    threshold_price: Optional[Decimal] = None


@dataclass
class AssetSaleInfo:
    """Information about a completed asset sale."""
    market: str
    sell_price: Decimal
    sell_timestamp: datetime
    trigger_reason: str  # "trailing_stop" or "stop_loss"


class DipEvaluator:
    """Central decision engine for dip buying strategy."""
    
    def __init__(self, config: DipBuyConfig, max_trade_amount: Decimal):
        self.config = config
        self.max_trade_amount = max_trade_amount
        
    def should_rebuy(self, asset_info: AssetSaleInfo, current_price: Decimal, 
                    asset_state: Dict[str, Any]) -> RebuyDecision:
        """
        Evaluate whether to execute a dip rebuy.
        
        Args:
            asset_info: Information about the original sale
            current_price: Current market price
            asset_state: Current tracking state for this asset
            
        Returns:
            RebuyDecision with evaluation result
        """
        # Input validation
        if not self._validate_inputs(asset_info, current_price, asset_state):
            return RebuyDecision(
                should_rebuy=False,
                reason="Invalid input data"
            )
        
        if not self.config.enabled:
            return RebuyDecision(
                should_rebuy=False,
                reason="Dip buying disabled in configuration"
            )
        
        # Check if monitoring period has expired
        monitoring_expires = asset_info.sell_timestamp + timedelta(
            hours=self.config.monitoring_duration_hours
        )
        if datetime.now() >= monitoring_expires:
            return RebuyDecision(
                should_rebuy=False,
                reason="Monitoring period expired"
            )
        
        # Check asset cooldown period
        next_eligible = asset_state.get('next_asset_cooldown')
        if next_eligible:
            cooldown_time = datetime.fromisoformat(next_eligible)
            if datetime.now() < cooldown_time:
                return RebuyDecision(
                    should_rebuy=False,
                    reason=f"Asset in cooldown until {cooldown_time.strftime('%H:%M:%S')}"
                )
        
        # Check maximum rebuy attempts
        completed_rebuys = asset_state.get('completed_rebuys', [])
        if len(completed_rebuys) >= self.config.max_rebuys_per_asset:
            return RebuyDecision(
                should_rebuy=False,
                reason=f"Maximum rebuy attempts ({self.config.max_rebuys_per_asset}) reached"
            )
        
        # Calculate price drop percentage
        price_drop_pct = ((asset_info.sell_price - current_price) / asset_info.sell_price) * 100
        
        logger.debug(f"{asset_info.market}: Price drop {price_drop_pct:.2f}% "
                    f"(${current_price} vs sell ${asset_info.sell_price})")
        
        # Find eligible dip levels
        eligible_level = self._find_eligible_level(price_drop_pct, asset_state)
        if not eligible_level:
            return RebuyDecision(
                should_rebuy=False,
                reason=f"No eligible dip levels for {price_drop_pct:.1f}% drop"
            )
        
        # Calculate rebuy amount
        rebuy_amount = self._calculate_rebuy_amount(eligible_level)
        threshold_price = asset_info.sell_price * (Decimal('1') - eligible_level.threshold_pct / Decimal('100'))
        
        # Market filter check (optional)
        if self.config.use_market_filter:
            market_decision = self._check_market_conditions()
            if not market_decision.should_rebuy:
                return RebuyDecision(
                    should_rebuy=False,
                    reason=f"Market filter: {market_decision.reason}"
                )
        
        return RebuyDecision(
            should_rebuy=True,
            level=self._get_level_number(eligible_level),
            amount_eur=rebuy_amount,
            threshold_price=threshold_price,
            reason=f"Level {self._get_level_number(eligible_level)} triggered: "
                   f"{price_drop_pct:.1f}% drop (threshold: {eligible_level.threshold_pct}%)"
        )
    
    def _find_eligible_level(self, price_drop_pct: Decimal, asset_state: Dict[str, Any]) -> Optional[DipLevel]:
        """Find the highest eligible dip level for the current price drop."""
        if not self.config.dip_levels:
            return None
        
        # Get levels that haven't been completed yet
        completed_levels = set()
        for rebuy in asset_state.get('completed_rebuys', []):
            completed_levels.add(rebuy.get('level'))
        
        # Find the highest threshold that's triggered and not completed
        eligible_level = None
        for level in reversed(self.config.dip_levels):  # Check highest thresholds first
            level_number = self._get_level_number(level)
            
            if level_number in completed_levels:
                logger.debug(f"Level {level_number} already completed, skipping")
                continue
                
            if price_drop_pct >= level.threshold_pct:
                # Check if this level is ready for retry (not in backoff)
                if self._is_level_ready_for_retry(level_number, asset_state):
                    eligible_level = level
                    break
                else:
                    logger.debug(f"Level {level_number} in retry backoff, skipping")
        
        return eligible_level
    
    def _get_level_number(self, level: DipLevel) -> int:
        """Get the level number (1-based index) for a DipLevel."""
        try:
            return self.config.dip_levels.index(level) + 1
        except ValueError:
            return 0
    
    def _is_level_ready_for_retry(self, level_number: int, asset_state: Dict[str, Any]) -> bool:
        """Check if a level is ready for retry after technical failures."""
        # Validate level number bounds
        if level_number < 1 or level_number > len(self.config.dip_levels):
            logger.error(f"Invalid level number: {level_number} (available: 1-{len(self.config.dip_levels)})")
            return False
        
        levels_data = asset_state.get('levels', {})
        level_data = levels_data.get(str(level_number), {})
        
        # Check if level has failed attempts and is in backoff
        next_retry = level_data.get('next_retry_at')
        if next_retry:
            try:
                retry_time = datetime.fromisoformat(next_retry)
                if datetime.now() < retry_time:
                    return False
            except ValueError as e:
                logger.warning(f"Invalid retry timestamp for level {level_number}: {e}")
                # Continue processing if timestamp is invalid
        
        # Check retry count limit - now safe after bounds check
        retry_count = level_data.get('retry_count', 0)
        level_config = self.config.dip_levels[level_number - 1]
        if retry_count >= level_config.max_retries:
            logger.debug(f"Level {level_number} exceeded max retries ({retry_count})")
            return False
        
        return True
    
    def _calculate_rebuy_amount(self, level: DipLevel) -> Decimal:
        """Calculate the EUR amount to rebuy for this level."""
        # Base rebuy amount is the configured allocation of max trade amount
        base_amount = self.max_trade_amount * level.capital_allocation
        
        # Ensure we don't exceed the maximum trade amount per transaction
        return min(base_amount, self.max_trade_amount)
    
    def _check_market_conditions(self) -> RebuyDecision:
        """
        Check overall market conditions to gate rebuy decisions.
        
        For now, this is a simple placeholder. In a full implementation,
        this could check BTC trend, market volatility, etc.
        """
        # Placeholder - always allow for now
        # In a real implementation, this could:
        # - Check if BTC has dropped >15% in 24h
        # - Check market volatility indices
        # - Use simple trend indicators
        
        return RebuyDecision(
            should_rebuy=True,
            reason="Market conditions acceptable"
        )
    
    def get_monitoring_info(self, asset_info: AssetSaleInfo) -> Dict[str, Any]:
        """Get monitoring information for an asset."""
        monitoring_expires = asset_info.sell_timestamp + timedelta(
            hours=self.config.monitoring_duration_hours
        )
        
        # Calculate threshold prices for all levels
        threshold_prices = {}
        for i, level in enumerate(self.config.dip_levels, 1):
            threshold_price = asset_info.sell_price * (Decimal('1') - level.threshold_pct / Decimal('100'))
            threshold_prices[i] = {
                'threshold_pct': float(level.threshold_pct),
                'threshold_price': float(threshold_price),
                'allocation': float(level.capital_allocation),
                'amount_eur': float(self._calculate_rebuy_amount(level))
            }
        
        return {
            'market': asset_info.market,
            'sell_price': float(asset_info.sell_price),
            'sell_timestamp': asset_info.sell_timestamp.isoformat(),
            'monitoring_expires': monitoring_expires.isoformat(),
            'threshold_prices': threshold_prices,
            'trigger_reason': asset_info.trigger_reason
        }
    
    def _validate_inputs(self, asset_info: AssetSaleInfo, current_price: Decimal, 
                        asset_state: Dict[str, Any]) -> bool:
        """Validate inputs for rebuy evaluation."""
        try:
            # Validate current price
            if current_price <= 0:
                logger.error(f"Invalid current price for {asset_info.market}: {current_price}")
                return False
            
            # Validate asset_info
            if not asset_info.market or not asset_info.market.strip():
                logger.error("Missing or empty market name")
                return False
                
            if asset_info.sell_price <= 0:
                logger.error(f"Invalid sell price for {asset_info.market}: {asset_info.sell_price}")
                return False
            
            # Validate asset_state structure
            required_keys = ['completed_rebuys', 'levels']
            for key in required_keys:
                if key not in asset_state:
                    logger.warning(f"Missing key '{key}' in asset state for {asset_info.market}")
                    # Initialize missing keys with defaults
                    if key == 'completed_rebuys':
                        asset_state[key] = []
                    elif key == 'levels':
                        asset_state[key] = {}
            
            # Validate completed_rebuys is a list
            if not isinstance(asset_state.get('completed_rebuys'), list):
                logger.warning(f"Invalid completed_rebuys type for {asset_info.market}, resetting to empty list")
                asset_state['completed_rebuys'] = []
            
            # Validate levels is a dict
            if not isinstance(asset_state.get('levels'), dict):
                logger.warning(f"Invalid levels type for {asset_info.market}, resetting to empty dict")
                asset_state['levels'] = {}
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating inputs for {asset_info.market}: {e}")
            return False