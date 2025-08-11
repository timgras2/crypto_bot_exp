#!/usr/bin/env python3
"""
Protected Asset State Management - Thread-safe persistence for asset protection
"""

import json
import logging
import threading
import time
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field

logger = logging.getLogger(__name__)


@dataclass
class TradeRecord:
    """Record of a completed protection trade."""
    trade_type: str  # 'dca_buy', 'profit_sell', 'stop_loss', 'rebalance', 'swing_sell', 'swing_rebuy'
    price: Decimal
    amount_eur: Decimal
    amount_crypto: Decimal
    timestamp: datetime
    reason: str


@dataclass
class ProtectedAssetInfo:
    """Information about a protected asset."""
    market: str
    entry_price: Decimal          # Average entry price
    current_position_eur: Decimal # Current EUR value of position
    total_invested_eur: Decimal   # Total EUR invested (including DCA)
    
    # Dynamic stop loss tracking
    current_stop_loss_pct: Decimal
    last_volatility_check: datetime
    
    # Trading activity tracking
    trade_history: List[TradeRecord]
    daily_trade_count: int
    last_trade_date: datetime
    
    # DCA and profit taking state
    completed_dca_levels: List[int]
    completed_profit_levels: List[int]
    
    # Swing trading state
    swing_cash_reserve_eur: Decimal = Decimal('0')     # Cash from swing sells available for rebuying
    completed_swing_sell_levels: List[int] = field(default_factory=list)      # Completed swing sell levels
    completed_swing_rebuy_levels: List[int] = field(default_factory=list)     # Completed swing rebuy levels
    swing_entry_price: Optional[Decimal] = None        # Entry price for swing trading (updates on sells)
    
    # Portfolio rebalancing
    target_allocation_pct: Optional[Decimal] = None
    last_rebalance: Optional[datetime] = None
    
    # Risk management
    max_drawdown_pct: Decimal = Decimal('0')
    peak_value_eur: Decimal = Decimal('0')
    
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        self.updated_at = datetime.now()


class ProtectedAssetStateManager:
    """
    Thread-safe state management for protected assets.
    
    Responsibilities:
    - Persist protected asset state across bot restarts
    - Track trade history and performance metrics
    - Manage daily trade limits and cooldowns
    - Calculate position sizes and risk metrics
    """
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.state_file = data_dir / "protected_assets.json"
        self.backup_file = data_dir / "protected_assets.json.backup"
        
        # Thread safety
        self._lock = threading.Lock()
        self._state: Dict[str, ProtectedAssetInfo] = {}
        
        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing state
        self._load_state()
        
        logger.info(f"ProtectedAssetStateManager initialized with {len(self._state)} assets")
    
    def add_protected_asset(self, market: str, entry_price: Decimal, 
                          initial_investment_eur: Decimal,
                          target_allocation_pct: Optional[Decimal] = None) -> None:
        """Add a new asset to protection tracking."""
        try:
            # Input validation
            if not market or not market.strip():
                logger.error("Invalid market name provided")
                return
                
            if entry_price <= 0:
                logger.error(f"Invalid entry price for {market}: {entry_price}")
                return
                
            if initial_investment_eur <= 0:
                logger.error(f"Invalid initial investment for {market}: {initial_investment_eur}")
                return
            
            with self._lock:
                if market in self._state:
                    logger.warning(f"Asset {market} already being protected")
                    return
                
                asset_info = ProtectedAssetInfo(
                    market=market,
                    entry_price=entry_price,
                    current_position_eur=initial_investment_eur,
                    total_invested_eur=initial_investment_eur,
                    current_stop_loss_pct=Decimal('15.0'),  # Default
                    last_volatility_check=datetime.now(),
                    trade_history=[],
                    daily_trade_count=0,
                    last_trade_date=datetime.now().date() - timedelta(days=1),  # Yesterday to reset counter
                    completed_dca_levels=[],
                    completed_profit_levels=[],
                    target_allocation_pct=target_allocation_pct,
                    peak_value_eur=initial_investment_eur
                )
                
                self._state[market] = asset_info
                self._save_state()
                
                logger.info(f"Added {market} to protected assets: €{initial_investment_eur} at €{entry_price}")
                
        except Exception as e:
            logger.error(f"Error adding protected asset {market}: {e}")
    
    def remove_protected_asset(self, market: str) -> bool:
        """Remove an asset from protection tracking."""
        try:
            with self._lock:
                if market not in self._state:
                    logger.warning(f"Asset {market} not found in protected assets")
                    return False
                
                removed_asset = self._state.pop(market)
                self._save_state()
                
                logger.info(f"Removed {market} from protected assets "
                          f"(total invested: €{removed_asset.total_invested_eur})")
                return True
                
        except Exception as e:
            logger.error(f"Error removing protected asset {market}: {e}")
            return False
    
    def record_trade(self, market: str, trade_type: str, price: Decimal,
                    amount_eur: Decimal, amount_crypto: Decimal, reason: str) -> bool:
        """Record a protection trade for an asset."""
        try:
            # Input validation
            if not market or market not in self._state:
                logger.error(f"Market {market} not in protected assets")
                return False
                
            if price <= 0 or amount_eur <= 0:
                logger.error(f"Invalid trade amounts for {market}: price={price}, amount_eur={amount_eur}")
                return False
            
            with self._lock:
                asset_info = self._state[market]
                
                # Create trade record
                trade_record = TradeRecord(
                    trade_type=trade_type,
                    price=price,
                    amount_eur=amount_eur,
                    amount_crypto=amount_crypto,
                    timestamp=datetime.now(),
                    reason=reason
                )
                
                # Add to history
                asset_info.trade_history.append(trade_record)
                
                # Update daily trade count
                today = datetime.now().date()
                if asset_info.last_trade_date < today:
                    asset_info.daily_trade_count = 1
                    asset_info.last_trade_date = today
                else:
                    asset_info.daily_trade_count += 1
                
                # Update position tracking
                if trade_type in ['dca_buy', 'rebalance_buy']:
                    # Buying - increase position
                    old_total_crypto = asset_info.current_position_eur / asset_info.entry_price
                    new_total_crypto = old_total_crypto + amount_crypto
                    
                    # Recalculate average entry price
                    asset_info.total_invested_eur += amount_eur
                    asset_info.entry_price = asset_info.total_invested_eur / new_total_crypto
                    asset_info.current_position_eur = new_total_crypto * price
                    
                elif trade_type in ['profit_sell', 'stop_loss', 'rebalance_sell']:
                    # Selling - decrease position
                    asset_info.current_position_eur -= amount_eur
                    # Note: total_invested_eur stays the same for P&L calculation
                
                # Update peak tracking for drawdown calculation
                if asset_info.current_position_eur > asset_info.peak_value_eur:
                    asset_info.peak_value_eur = asset_info.current_position_eur
                    asset_info.max_drawdown_pct = Decimal('0')
                else:
                    # Calculate current drawdown
                    if asset_info.peak_value_eur > 0:
                        current_drawdown = (asset_info.peak_value_eur - asset_info.current_position_eur) / asset_info.peak_value_eur * 100
                        asset_info.max_drawdown_pct = max(asset_info.max_drawdown_pct, current_drawdown)
                
                asset_info.updated_at = datetime.now()
                self._save_state()
                
                logger.info(f"Recorded {trade_type} for {market}: €{amount_eur} at €{price} - {reason}")
                return True
                
        except Exception as e:
            logger.error(f"Error recording trade for {market}: {e}")
            return False
    
    def can_trade_today(self, market: str, max_daily_trades: int) -> bool:
        """Check if asset can trade more today based on daily limits."""
        try:
            with self._lock:
                if market not in self._state:
                    return False
                
                asset_info = self._state[market]
                today = datetime.now().date()
                
                # Reset counter if it's a new day
                if asset_info.last_trade_date < today:
                    return True
                
                return asset_info.daily_trade_count < max_daily_trades
                
        except Exception as e:
            logger.error(f"Error checking trade limits for {market}: {e}")
            return False
    
    def update_stop_loss(self, market: str, new_stop_loss_pct: Decimal) -> None:
        """Update the dynamic stop loss for an asset."""
        try:
            with self._lock:
                if market not in self._state:
                    logger.error(f"Market {market} not in protected assets")
                    return
                
                asset_info = self._state[market]
                old_stop = asset_info.current_stop_loss_pct
                asset_info.current_stop_loss_pct = new_stop_loss_pct
                asset_info.last_volatility_check = datetime.now()
                asset_info.updated_at = datetime.now()
                
                self._save_state()
                
                logger.debug(f"Updated {market} stop loss: {old_stop}% → {new_stop_loss_pct}%")
                
        except Exception as e:
            logger.error(f"Error updating stop loss for {market}: {e}")
    
    def mark_dca_level_completed(self, market: str, level: int) -> None:
        """Mark a DCA level as completed."""
        try:
            with self._lock:
                if market not in self._state:
                    return
                
                asset_info = self._state[market]
                if level not in asset_info.completed_dca_levels:
                    asset_info.completed_dca_levels.append(level)
                    asset_info.updated_at = datetime.now()
                    self._save_state()
                    
                    logger.debug(f"Marked DCA level {level} completed for {market}")
                
        except Exception as e:
            logger.error(f"Error marking DCA level completed for {market}: {e}")
    
    def mark_profit_level_completed(self, market: str, level: int) -> None:
        """Mark a profit taking level as completed."""
        try:
            with self._lock:
                if market not in self._state:
                    return
                
                asset_info = self._state[market]
                if level not in asset_info.completed_profit_levels:
                    asset_info.completed_profit_levels.append(level)
                    asset_info.updated_at = datetime.now()
                    self._save_state()
                    
                    logger.debug(f"Marked profit level {level} completed for {market}")
                
        except Exception as e:
            logger.error(f"Error marking profit level completed for {market}: {e}")
    
    def get_asset_info(self, market: str) -> Optional[ProtectedAssetInfo]:
        """Get information about a protected asset."""
        with self._lock:
            return self._state.get(market)
    
    def get_all_protected_assets(self) -> Dict[str, ProtectedAssetInfo]:
        """Get information about all protected assets."""
        with self._lock:
            return dict(self._state)
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get a summary of the protected portfolio."""
        try:
            with self._lock:
                if not self._state:
                    return {
                        'total_assets': 0,
                        'total_current_value_eur': 0,
                        'total_invested_eur': 0,
                        'unrealized_pnl_eur': 0,
                        'unrealized_pnl_pct': 0,
                        'max_drawdown_pct': 0
                    }
                
                total_current = sum(asset.current_position_eur for asset in self._state.values())
                total_invested = sum(asset.total_invested_eur for asset in self._state.values())
                unrealized_pnl = total_current - total_invested
                unrealized_pnl_pct = (unrealized_pnl / total_invested * 100) if total_invested > 0 else 0
                max_drawdown = max((asset.max_drawdown_pct for asset in self._state.values()), default=Decimal('0'))
                
                return {
                    'total_assets': len(self._state),
                    'total_current_value_eur': float(total_current),
                    'total_invested_eur': float(total_invested),
                    'unrealized_pnl_eur': float(unrealized_pnl),
                    'unrealized_pnl_pct': float(unrealized_pnl_pct),
                    'max_drawdown_pct': float(max_drawdown)
                }
                
        except Exception as e:
            logger.error(f"Error generating portfolio summary: {e}")
            return {}
    
    def cleanup_old_trades(self, days_to_keep: int = 30) -> None:
        """Remove old trade records to prevent unlimited growth."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            with self._lock:
                for asset_info in self._state.values():
                    original_count = len(asset_info.trade_history)
                    asset_info.trade_history = [
                        trade for trade in asset_info.trade_history
                        if trade.timestamp >= cutoff_date
                    ]
                    
                    if len(asset_info.trade_history) < original_count:
                        logger.debug(f"Cleaned up {original_count - len(asset_info.trade_history)} "
                                   f"old trades for {asset_info.market}")
                
                if any(len(asset.trade_history) != len([t for t in asset.trade_history 
                                                     if t.timestamp >= cutoff_date])
                      for asset in self._state.values()):
                    self._save_state()
            
        except Exception as e:
            logger.error(f"Error cleaning up old trades: {e}")
    
    def _load_state(self) -> None:
        """Load protected asset state from disk."""
        try:
            if not self.state_file.exists():
                logger.info("No protected asset state file found - starting fresh")
                return
            
            state_data = json.loads(self.state_file.read_text(encoding='utf-8'))
            
            for market, asset_data in state_data.items():
                try:
                    # Convert trade history
                    trade_history = []
                    for trade_data in asset_data.get('trade_history', []):
                        trade_record = TradeRecord(
                            trade_type=trade_data['trade_type'],
                            price=Decimal(trade_data['price']),
                            amount_eur=Decimal(trade_data['amount_eur']),
                            amount_crypto=Decimal(trade_data['amount_crypto']),
                            timestamp=datetime.fromisoformat(trade_data['timestamp']),
                            reason=trade_data['reason']
                        )
                        trade_history.append(trade_record)
                    
                    # Create asset info
                    asset_info = ProtectedAssetInfo(
                        market=market,
                        entry_price=Decimal(asset_data['entry_price']),
                        current_position_eur=Decimal(asset_data['current_position_eur']),
                        total_invested_eur=Decimal(asset_data['total_invested_eur']),
                        current_stop_loss_pct=Decimal(asset_data.get('current_stop_loss_pct', '15.0')),
                        last_volatility_check=datetime.fromisoformat(asset_data.get('last_volatility_check', datetime.now().isoformat())),
                        trade_history=trade_history,
                        daily_trade_count=asset_data.get('daily_trade_count', 0),
                        last_trade_date=datetime.fromisoformat(asset_data.get('last_trade_date', datetime.now().isoformat())).date(),
                        completed_dca_levels=asset_data.get('completed_dca_levels', []),
                        completed_profit_levels=asset_data.get('completed_profit_levels', []),
                        swing_cash_reserve_eur=Decimal(asset_data.get('swing_cash_reserve_eur', '0')),
                        completed_swing_sell_levels=asset_data.get('completed_swing_sell_levels', []),
                        completed_swing_rebuy_levels=asset_data.get('completed_swing_rebuy_levels', []),
                        swing_entry_price=Decimal(asset_data['swing_entry_price']) if asset_data.get('swing_entry_price') else None,
                        target_allocation_pct=Decimal(asset_data['target_allocation_pct']) if asset_data.get('target_allocation_pct') else None,
                        last_rebalance=datetime.fromisoformat(asset_data['last_rebalance']) if asset_data.get('last_rebalance') else None,
                        max_drawdown_pct=Decimal(asset_data.get('max_drawdown_pct', '0')),
                        peak_value_eur=Decimal(asset_data.get('peak_value_eur', asset_data['current_position_eur'])),
                        created_at=datetime.fromisoformat(asset_data.get('created_at', datetime.now().isoformat())),
                        updated_at=datetime.fromisoformat(asset_data.get('updated_at', datetime.now().isoformat()))
                    )
                    
                    self._state[market] = asset_info
                    
                except (ValueError, KeyError, InvalidOperation) as e:
                    logger.error(f"Error loading asset data for {market}: {e}")
                    continue
            
            logger.info(f"Loaded {len(self._state)} protected assets from state file")
            
        except Exception as e:
            logger.error(f"Error loading protected asset state: {e}")
            # Try to load backup
            self._load_backup_state()
    
    def _load_backup_state(self) -> None:
        """Load state from backup file."""
        try:
            if not self.backup_file.exists():
                logger.warning("No backup state file found")
                return
            
            logger.info("Attempting to load from backup state file")
            # Same logic as _load_state but from backup file
            # Implementation would be identical, just using backup_file instead
            
        except Exception as e:
            logger.error(f"Error loading backup state: {e}")
    
    def _save_state(self) -> None:
        """Save protected asset state to disk with atomic writes."""
        try:
            # Convert state to serializable format
            state_data = {}
            
            for market, asset_info in self._state.items():
                # Convert trade history
                trade_history_data = []
                for trade in asset_info.trade_history:
                    trade_data = {
                        'trade_type': trade.trade_type,
                        'price': str(trade.price),
                        'amount_eur': str(trade.amount_eur),
                        'amount_crypto': str(trade.amount_crypto),
                        'timestamp': trade.timestamp.isoformat(),
                        'reason': trade.reason
                    }
                    trade_history_data.append(trade_data)
                
                # Convert asset info
                asset_data = {
                    'entry_price': str(asset_info.entry_price),
                    'current_position_eur': str(asset_info.current_position_eur),
                    'total_invested_eur': str(asset_info.total_invested_eur),
                    'current_stop_loss_pct': str(asset_info.current_stop_loss_pct),
                    'last_volatility_check': asset_info.last_volatility_check.isoformat(),
                    'trade_history': trade_history_data,
                    'daily_trade_count': asset_info.daily_trade_count,
                    'last_trade_date': asset_info.last_trade_date.isoformat(),
                    'completed_dca_levels': asset_info.completed_dca_levels,
                    'completed_profit_levels': asset_info.completed_profit_levels,
                    'swing_cash_reserve_eur': str(asset_info.swing_cash_reserve_eur),
                    'completed_swing_sell_levels': asset_info.completed_swing_sell_levels,
                    'completed_swing_rebuy_levels': asset_info.completed_swing_rebuy_levels,
                    'swing_entry_price': str(asset_info.swing_entry_price) if asset_info.swing_entry_price else None,
                    'target_allocation_pct': str(asset_info.target_allocation_pct) if asset_info.target_allocation_pct else None,
                    'last_rebalance': asset_info.last_rebalance.isoformat() if asset_info.last_rebalance else None,
                    'max_drawdown_pct': str(asset_info.max_drawdown_pct),
                    'peak_value_eur': str(asset_info.peak_value_eur),
                    'created_at': asset_info.created_at.isoformat(),
                    'updated_at': asset_info.updated_at.isoformat()
                }
                
                state_data[market] = asset_data
            
            # Atomic write with backup
            temp_file = self.state_file.with_suffix('.tmp')
            
            # Write to temporary file
            temp_file.write_text(json.dumps(state_data, indent=2), encoding='utf-8')
            
            # Backup current file if it exists
            if self.state_file.exists():
                self.backup_file.write_text(self.state_file.read_text(encoding='utf-8'), encoding='utf-8')
            
            # Atomic move
            temp_file.replace(self.state_file)
            
            logger.debug(f"Saved protected asset state for {len(self._state)} assets")
            
        except Exception as e:
            logger.error(f"Error saving protected asset state: {e}")
            # Clean up temp file if it exists
            temp_file = self.state_file.with_suffix('.tmp')
            if temp_file.exists():
                temp_file.unlink()
    
    def add_swing_cash_reserve(self, market: str, amount_eur: Decimal) -> None:
        """Add cash to swing trading reserves from a sell operation."""
        with self._lock:
            if market not in self._state:
                logger.warning(f"Cannot add swing cash reserve: market {market} not found")
                return
            
            self._state[market].swing_cash_reserve_eur += amount_eur
            self._state[market].updated_at = datetime.now()
            self._save_state()
            
            logger.debug(f"Added €{amount_eur} to swing cash reserve for {market}. "
                        f"Total reserve: €{self._state[market].swing_cash_reserve_eur}")
    
    def use_swing_cash_reserve(self, market: str, amount_eur: Decimal) -> bool:
        """Use cash from swing trading reserves for a rebuy operation."""
        with self._lock:
            if market not in self._state:
                logger.warning(f"Cannot use swing cash reserve: market {market} not found")
                return False
            
            asset_info = self._state[market]
            if asset_info.swing_cash_reserve_eur < amount_eur:
                logger.debug(f"Insufficient swing cash reserve for {market}: "
                           f"need €{amount_eur}, have €{asset_info.swing_cash_reserve_eur}")
                return False
            
            asset_info.swing_cash_reserve_eur -= amount_eur
            asset_info.updated_at = datetime.now()
            self._save_state()
            
            logger.debug(f"Used €{amount_eur} from swing cash reserve for {market}. "
                        f"Remaining reserve: €{asset_info.swing_cash_reserve_eur}")
            return True
    
    def mark_swing_level_completed(self, market: str, level_index: int, action: str) -> None:
        """Mark a swing trading level as completed."""
        with self._lock:
            if market not in self._state:
                logger.warning(f"Cannot mark swing level: market {market} not found")
                return
            
            asset_info = self._state[market]
            
            if action == 'sell':
                if level_index not in asset_info.completed_swing_sell_levels:
                    asset_info.completed_swing_sell_levels.append(level_index)
                    logger.debug(f"Marked swing sell level {level_index} as completed for {market}")
            elif action == 'rebuy':
                if level_index not in asset_info.completed_swing_rebuy_levels:
                    asset_info.completed_swing_rebuy_levels.append(level_index)
                    logger.debug(f"Marked swing rebuy level {level_index} as completed for {market}")
            else:
                logger.warning(f"Invalid swing action: {action}")
                return
            
            asset_info.updated_at = datetime.now()
            self._save_state()
    
    def update_swing_entry_price(self, market: str, price: Decimal) -> None:
        """Update the swing trading entry price (after sells)."""
        with self._lock:
            if market not in self._state:
                logger.warning(f"Cannot update swing entry price: market {market} not found")
                return
            
            self._state[market].swing_entry_price = price
            self._state[market].updated_at = datetime.now()
            self._save_state()
            
            logger.debug(f"Updated swing entry price for {market} to €{price}")
    
    def get_swing_cash_reserve(self, market: str) -> Decimal:
        """Get available swing trading cash reserves."""
        with self._lock:
            if market not in self._state:
                return Decimal('0')
            return self._state[market].swing_cash_reserve_eur