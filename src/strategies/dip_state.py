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

from .dip_evaluator import AssetSaleInfo
from ..config import DipBuyConfig

logger = logging.getLogger(__name__)


class DipStateManager:
    """Manages persistence and recovery of dip tracking state."""
    
    def __init__(self, data_dir: Path, dip_config: Optional[DipBuyConfig] = None):
        self.data_dir = data_dir
        self.persistence_file = data_dir / "dip_tracking.json"
        self._lock = threading.Lock()
        self.dip_config = dip_config
        
        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"DipStateManager using persistence file: {self.persistence_file}")
    
    def load_state(self) -> Dict[str, Any]:
        """Load dip tracking state from disk with retry logic."""
        for attempt in range(3):  # Retry up to 3 times
            try:
                if not self.persistence_file.exists():
                    logger.info(f"No dip tracking file found at {self.persistence_file} - starting fresh")
                    return {}
                
                with self._lock:
                    state_data = json.loads(self.persistence_file.read_text(encoding='utf-8'))
                    logger.info(f"Loaded dip tracking state for {len(state_data)} assets")
                    return state_data
                    
            except (FileNotFoundError, PermissionError) as e:
                if attempt < 2:  # Retry for file system issues
                    logger.warning(f"File access issue (attempt {attempt + 1}/3): {e}")
                    import time
                    time.sleep(0.1 * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    logger.error(f"Failed to load dip tracking state after retries: {e}")
                    return {}
                    
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse dip tracking state (corrupted JSON): {e}")
                # Move corrupted file out of the way
                if self.persistence_file.exists():
                    backup_path = self.persistence_file.with_suffix('.json.backup')
                    try:
                        self.persistence_file.rename(backup_path)
                        logger.warning(f"Moved corrupted dip tracking file to {backup_path}")
                    except Exception as backup_error:
                        logger.error(f"Failed to backup corrupted file: {backup_error}")
                return {}
                
            except Exception as e:
                logger.error(f"Unexpected error loading dip tracking state: {e}")
                return {}
        
        return {}  # Fallback if all retries failed
    
    def save_state(self, state_data: Dict[str, Any]) -> None:
        """Save dip tracking state to disk with atomic writes."""
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
                
                # Atomic write: write to temporary file first, then rename
                temp_file = self.persistence_file.with_suffix('.tmp')
                try:
                    # Write to temporary file
                    temp_file.write_text(json.dumps(cleaned_state, indent=2), encoding='utf-8')
                    
                    # Atomic rename (works on both Windows and Unix)
                    temp_file.replace(self.persistence_file)
                    logger.debug(f"Saved dip tracking state for {len(cleaned_state)} assets")
                    
                except Exception:
                    # Clean up temp file if something went wrong
                    if temp_file.exists():
                        temp_file.unlink()
                    raise
                
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
        if self.dip_config:
            cooldown_until = datetime.now() + timedelta(hours=self.dip_config.cooldown_hours)
        else:
            # Fallback to default cooldown if config not available
            cooldown_until = datetime.now() + timedelta(hours=4)
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