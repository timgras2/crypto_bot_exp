#!/usr/bin/env python3
"""
Dip State Management - Handles persistence and recovery of dip tracking data
"""

import json
import logging
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from decimal import Decimal, InvalidOperation

from future_work.dip_evaluator import AssetSaleInfo

logger = logging.getLogger(__name__)


class DipStateManager:
    """Manages persistence and recovery of dip tracking state."""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.persistence_file = data_dir / "dip_tracking.json"
        self._lock = threading.Lock()
        
        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"DipStateManager using persistence file: {self.persistence_file}")
    
    def load_state(self) -> Dict[str, Any]:
        """Load dip tracking state from disk."""
        try:
            if not self.persistence_file.exists():
                logger.info(f"No dip tracking file found at {self.persistence_file} - starting fresh")
                return {}
            
            with self._lock:
                state_data = json.loads(self.persistence_file.read_text())
                logger.info(f"Loaded dip tracking state for {len(state_data)} assets")
                return state_data
                
        except Exception as e:
            logger.error(f"Failed to load dip tracking state: {e}")
            # Move corrupted file out of the way
            if self.persistence_file.exists():
                backup_path = self.persistence_file.with_suffix('.json.backup')
                self.persistence_file.rename(backup_path)
                logger.warning(f"Moved corrupted dip tracking file to {backup_path}")
            return {}
    
    def save_state(self, state_data: Dict[str, Any]) -> None:
        """Save dip tracking state to disk."""
        try:
            with self._lock:
                # Clean up expired entries before saving
                cleaned_state = self._cleanup_expired_entries(state_data)
                
                if not cleaned_state:
                    # If no active tracking, remove the file
                    if self.persistence_file.exists():
                        self.persistence_file.unlink()
                        logger.info("No active dip tracking - removed persistence file")
                    return
                
                # Save to file
                self.persistence_file.write_text(json.dumps(cleaned_state, indent=2))
                logger.debug(f"Saved dip tracking state for {len(cleaned_state)} assets")
                
        except Exception as e:
            logger.error(f"Failed to save dip tracking state: {e}")
    
    def add_asset_for_tracking(self, asset_info: AssetSaleInfo, monitoring_info: Dict[str, Any]) -> None:
        """Add a new asset to dip tracking."""
        state = self.load_state()
        
        # Initialize asset state
        state[asset_info.market] = {
            'sell_price': str(asset_info.sell_price),
            'sell_timestamp': asset_info.sell_timestamp.isoformat(),
            'trigger_reason': asset_info.trigger_reason,
            'monitoring_expires': monitoring_info['monitoring_expires'],
            'completed_rebuys': [],
            'levels': {},  # Will be populated as levels are attempted
            'next_asset_cooldown': None,
            'created_at': datetime.now().isoformat()
        }
        
        logger.info(f"Added {asset_info.market} to dip tracking (sold at €{asset_info.sell_price})")
        self.save_state(state)
    
    def update_level_attempt(self, market: str, level_number: int, status: str, 
                           retry_count: int = 0, next_retry_at: Optional[datetime] = None) -> None:
        """Update the attempt status for a specific dip level."""
        state = self.load_state()
        
        if market not in state:
            logger.warning(f"Attempted to update level for unknown market: {market}")
            return
        
        # Initialize levels dict if not exists
        if 'levels' not in state[market]:
            state[market]['levels'] = {}
        
        level_key = str(level_number)
        state[market]['levels'][level_key] = {
            'status': status,  # 'pending', 'attempting', 'completed', 'failed'
            'retry_count': retry_count,
            'next_retry_at': next_retry_at.isoformat() if next_retry_at else None,
            'last_updated': datetime.now().isoformat()
        }
        
        logger.debug(f"Updated {market} level {level_number}: {status}")
        self.save_state(state)
    
    def record_successful_rebuy(self, market: str, level_number: int, 
                               buy_price: Decimal, amount_eur: Decimal) -> None:
        """Record a successful rebuy execution."""
        state = self.load_state()
        
        if market not in state:
            logger.warning(f"Attempted to record rebuy for unknown market: {market}")
            return
        
        # Add to completed rebuys
        rebuy_record = {
            'level': level_number,
            'buy_price': str(buy_price),
            'amount_eur': str(amount_eur),
            'timestamp': datetime.now().isoformat()
        }
        
        state[market]['completed_rebuys'].append(rebuy_record)
        
        # Update level status
        self.update_level_attempt(market, level_number, 'completed')
        
        # Set asset cooldown
        from src.config import load_config
        _, _, dip_config = load_config()
        cooldown_until = datetime.now() + timedelta(hours=dip_config.cooldown_hours)
        state[market]['next_asset_cooldown'] = cooldown_until.isoformat()
        
        logger.info(f"Recorded successful rebuy for {market} level {level_number}: "
                   f"€{buy_price} x €{amount_eur}")
        self.save_state(state)
    
    def get_asset_state(self, market: str) -> Optional[Dict[str, Any]]:
        """Get the current state for a specific asset."""
        state = self.load_state()
        return state.get(market)
    
    def get_active_tracking(self) -> Dict[str, Any]:
        """Get all assets currently being tracked for dips."""
        state = self.load_state()
        
        # Filter out expired entries
        active_tracking = {}
        now = datetime.now()
        
        for market, asset_data in state.items():
            try:
                monitoring_expires = datetime.fromisoformat(asset_data['monitoring_expires'])
                if now < monitoring_expires:
                    active_tracking[market] = asset_data
            except (KeyError, ValueError) as e:
                logger.warning(f"Invalid monitoring expiration for {market}: {e}")
        
        return active_tracking
    
    def remove_asset_tracking(self, market: str, reason: str = "") -> None:
        """Remove an asset from dip tracking."""
        state = self.load_state()
        
        if market in state:
            del state[market]
            logger.info(f"Removed {market} from dip tracking. Reason: {reason}")
            self.save_state(state)
    
    def _cleanup_expired_entries(self, state_data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove expired tracking entries from state."""
        now = datetime.now()
        cleaned_state = {}
        
        for market, asset_data in state_data.items():
            try:
                monitoring_expires = datetime.fromisoformat(asset_data['monitoring_expires'])
                if now < monitoring_expires:
                    cleaned_state[market] = asset_data
                else:
                    logger.debug(f"Removing expired dip tracking for {market}")
            except (KeyError, ValueError) as e:
                logger.warning(f"Invalid monitoring expiration for {market}: {e}")
        
        return cleaned_state
    
    def get_tracking_summary(self) -> Dict[str, Any]:
        """Get a summary of current dip tracking status."""
        active_tracking = self.get_active_tracking()
        
        summary = {
            'total_assets': len(active_tracking),
            'assets': {},
            'generated_at': datetime.now().isoformat()
        }
        
        for market, asset_data in active_tracking.items():
            try:
                sell_price = Decimal(asset_data['sell_price'])
                completed_rebuys = len(asset_data.get('completed_rebuys', []))
                
                # Calculate total rebuy capital used
                total_rebuy_capital = Decimal('0')
                for rebuy in asset_data.get('completed_rebuys', []):
                    total_rebuy_capital += Decimal(rebuy['amount_eur'])
                
                # Check if asset is in cooldown
                in_cooldown = False
                next_cooldown = asset_data.get('next_asset_cooldown')
                if next_cooldown:
                    cooldown_time = datetime.fromisoformat(next_cooldown)
                    in_cooldown = datetime.now() < cooldown_time
                
                summary['assets'][market] = {
                    'sell_price': float(sell_price),
                    'sell_timestamp': asset_data['sell_timestamp'],
                    'monitoring_expires': asset_data['monitoring_expires'],
                    'completed_rebuys': completed_rebuys,
                    'total_rebuy_capital': float(total_rebuy_capital),
                    'in_cooldown': in_cooldown,
                    'trigger_reason': asset_data.get('trigger_reason', 'unknown')
                }
                
            except (KeyError, ValueError, InvalidOperation) as e:
                logger.warning(f"Error processing summary for {market}: {e}")
        
        return summary