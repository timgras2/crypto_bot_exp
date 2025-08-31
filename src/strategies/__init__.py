"""
Advanced trading strategies module for the crypto trading bot.

This module contains sophisticated trading strategies including:
- Dip buying strategy with multi-level thresholds
- Market condition filtering
- Thread-safe state management
"""

from .dip_buy_manager import DipBuyManager
from .dip_evaluator import DipEvaluator
from .dip_state import DipStateManager
from .market_filter import MarketFilter

__all__ = ['DipBuyManager', 'DipEvaluator', 'DipStateManager', 'MarketFilter']