#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Strategies package for crypto trading bot.
Contains advanced trading strategies like dip buying and market filtering.
"""

from .dip_buy_manager import DipBuyManager
from .dip_evaluator import DipEvaluator
from .dip_state import DipStateManager
from .market_filter import MarketFilter

__all__ = [
    'DipBuyManager',
    'DipEvaluator', 
    'DipStateManager',
    'MarketFilter'
]