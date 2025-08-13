#!/usr/bin/env python3
"""
Enhanced Swing Trading Simulator - Test adaptive asset protection strategies

Features:
- 12 realistic market scenarios (bear, bull, volatile, crash, etc.)
- Adaptive strategy that changes based on market regime detection  
- Progressive stop-loss protection for bear markets
- Comprehensive backtesting and performance analysis
- Multi-strategy comparison (Conservative, Balanced, Aggressive, Bear-Protected)

Usage:
    python swing_trading_simulator.py
    
Choose from:
1. Quick test with sample data
2. Detailed simulation with your BTC portfolio  
3. Comprehensive analysis across all market scenarios (recommended)
4. Custom scenario builder (coming soon)
"""

import sys
import json
import math
import random
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import AssetProtectionConfig, SwingLevel, TrendDetectionConfig, load_config

@dataclass
class SimulatedPosition:
    """Represents a position during simulation."""
    symbol: str
    amount: Decimal          # Amount of crypto held
    cash_reserve: Decimal    # Cash from swing sells available for rebuying
    entry_price: Decimal     # Original entry price
    swing_entry_price: Decimal  # Current swing trading baseline price
    completed_sell_levels: List[int]
    completed_rebuy_levels: List[int]
    total_invested: Decimal  # Total EUR invested
    trade_count: int
    current_market_regime: str  # 'normal', 'bull', 'bear', 'volatile'
    progressive_stop_triggered: bool  # Whether progressive stop loss has been triggered

@dataclass
class Trade:
    """Record of a simulated trade."""
    timestamp: datetime
    action: str              # 'swing_sell' or 'swing_rebuy'
    price: Decimal
    amount_crypto: Decimal
    amount_eur: Decimal
    reason: str
    cash_reserve_after: Decimal
    position_after: Decimal

@dataclass
class SimulationResult:
    """Results of a swing trading simulation."""
    initial_value_eur: Decimal
    final_value_eur: Decimal
    final_crypto_amount: Decimal
    final_cash_reserve: Decimal
    total_profit_eur: Decimal
    profit_percentage: float
    max_drawdown_pct: float
    total_trades: int
    trades: List[Trade]
    price_data: List[Tuple[datetime, Decimal]]  # Price history

class SwingTradingSimulator:
    """Simulator for swing trading asset protection strategies."""
    
    def __init__(self, config: AssetProtectionConfig):
        self.config = config
        self.trades: List[Trade] = []
        
    def simulate_market_scenario(self, 
                                initial_price: Decimal,
                                initial_amount: Decimal,
                                scenario: str = "crash_recovery") -> SimulationResult:
        """
        Simulate swing trading through various market scenarios.
        
        Args:
            initial_price: Starting price per unit
            initial_amount: Amount of crypto held
            scenario: Type of market scenario to simulate
        """
        print(f"Simulating swing trading scenario: {scenario}")
        print(f"Initial position: {initial_amount} @ EUR{initial_price} (EUR{initial_amount * initial_price:.2f})")
        print()
        
        # Generate price data based on scenario
        scenario_map = {
            "crash_recovery": self._generate_crash_recovery_scenario,
            "volatile_waves": self._generate_volatile_waves_scenario,
            "gradual_decline": self._generate_gradual_decline_scenario,
            "bear_market": self._generate_bear_market_scenario,
            "bull_market": self._generate_bull_market_scenario,
            "sideways_market": self._generate_sideways_market_scenario,
            "flash_crash": self._generate_flash_crash_scenario,
            "crypto_winter": self._generate_crypto_winter_scenario,
            "altcoin_season": self._generate_altcoin_season_scenario,
            "double_bottom": self._generate_double_bottom_scenario,
            "dead_cat_bounce": self._generate_dead_cat_bounce_scenario,
            "whale_manipulation": self._generate_whale_manipulation_scenario
        }
        
        if scenario not in scenario_map:
            raise ValueError(f"Unknown scenario: {scenario}. Available: {list(scenario_map.keys())}")
        
        price_data = scenario_map[scenario](initial_price)
        
        # Initialize position
        position = SimulatedPosition(
            symbol="BTC",
            amount=initial_amount,
            cash_reserve=Decimal('0'),
            entry_price=initial_price,
            swing_entry_price=initial_price,
            completed_sell_levels=[],
            completed_rebuy_levels=[],
            total_invested=initial_amount * initial_price,
            trade_count=0,
            current_market_regime="normal",
            progressive_stop_triggered=False
        )
        
        self.trades = []
        max_value = initial_amount * initial_price
        min_value = max_value
        
        # Simulate trading through price movements
        for i, (timestamp, price) in enumerate(price_data):
            # Update market regime based on recent price history
            if self.config.trend_detection.enabled and i >= 24:  # Need some history
                self._update_market_regime(position, price_data[max(0, i-168):i+1])
            
            # Check for progressive stop loss first (in bear markets)
            if self._check_progressive_stop_loss(position, price, timestamp):
                # Progressive stop triggered - position liquidated
                continue
            
            # Check for swing trading opportunities with adaptive levels
            self._process_adaptive_swing_opportunities(position, price, timestamp)
            
            # Track drawdown
            current_value = position.amount * price + position.cash_reserve
            if current_value > max_value:
                max_value = current_value
            if current_value < min_value:
                min_value = current_value
        
        # Calculate final results
        final_price = price_data[-1][1]
        final_value = position.amount * final_price + position.cash_reserve
        initial_value = initial_amount * initial_price
        
        profit = final_value - initial_value
        profit_pct = float(profit / initial_value * 100)
        max_drawdown_pct = float((max_value - min_value) / max_value * 100)
        
        return SimulationResult(
            initial_value_eur=initial_value,
            final_value_eur=final_value,
            final_crypto_amount=position.amount,
            final_cash_reserve=position.cash_reserve,
            total_profit_eur=profit,
            profit_percentage=profit_pct,
            max_drawdown_pct=max_drawdown_pct,
            total_trades=len(self.trades),
            trades=self.trades,
            price_data=price_data
        )
    
    def _generate_crash_recovery_scenario(self, initial_price: Decimal) -> List[Tuple[datetime, Decimal]]:
        """Generate price data for crash (-35%) and recovery (+110%) with waves."""
        price_data = []
        current_time = datetime.now()
        
        # Phase 1: Initial crash over 7 days (-35%)
        crash_target = initial_price * Decimal('0.65')  # -35%
        steps = 168  # 7 days, hourly data
        
        for i in range(steps):
            # Add some volatility to the crash
            base_decline = float(i) / float(steps - 1)  # Linear decline
            volatility = random.uniform(-0.02, 0.02)  # ±2% random movement
            
            price_ratio = 1.0 - (0.35 * base_decline) + volatility
            price_ratio = max(0.6, min(1.0, price_ratio))  # Clamp between -40% and 0%
            
            price = initial_price * Decimal(str(price_ratio))
            price_data.append((current_time + timedelta(hours=i), price))
        
        # Phase 2: Volatile bottom for 3 days
        bottom_hours = 72  # 3 days
        for i in range(bottom_hours):
            volatility = random.uniform(-0.05, 0.05)  # ±5% movement at bottom
            price_ratio = 0.65 + volatility
            price_ratio = max(0.60, min(0.70, price_ratio))  # Stay near bottom
            
            price = initial_price * Decimal(str(price_ratio))
            price_data.append((current_time + timedelta(hours=steps + i), price))
        
        # Phase 3: Recovery with waves (+110% total = +71% from current level)
        recovery_target = initial_price * Decimal('1.10')  # +10% above initial
        recovery_steps = 240  # 10 days recovery
        
        for i in range(recovery_steps):
            # Wavy recovery - not linear
            base_progress = float(i) / float(recovery_steps - 1)
            wave = 0.1 * math.sin(base_progress * 6 * math.pi)  # Multiple waves
            volatility = random.uniform(-0.03, 0.03)  # ±3% random movement
            
            # Progress from 0.65 to 1.10 (65% to 110%)
            price_ratio = 0.65 + (0.45 * base_progress) + wave + volatility
            price_ratio = max(0.60, min(1.15, price_ratio))  # Reasonable bounds
            
            price = initial_price * Decimal(str(price_ratio))
            price_data.append((current_time + timedelta(hours=steps + bottom_hours + i), price))
        
        return price_data
    
    def _generate_volatile_waves_scenario(self, initial_price: Decimal) -> List[Tuple[datetime, Decimal]]:
        """Generate price data with multiple volatile waves."""
        price_data = []
        current_time = datetime.now()
        
        # 14 days of volatile waves
        steps = 336  # 14 days hourly
        
        for i in range(steps):
            time_ratio = float(i) / float(steps - 1)
            
            # Multiple overlapping waves
            wave1 = 0.15 * math.sin(time_ratio * 3 * math.pi)      # Large waves
            wave2 = 0.08 * math.sin(time_ratio * 8 * math.pi)      # Medium waves  
            wave3 = 0.05 * math.sin(time_ratio * 20 * math.pi)     # Small waves
            volatility = random.uniform(-0.02, 0.02)               # Random noise
            
            price_ratio = 1.0 + wave1 + wave2 + wave3 + volatility
            price_ratio = max(0.70, min(1.30, price_ratio))        # ±30% range
            
            price = initial_price * Decimal(str(price_ratio))
            price_data.append((current_time + timedelta(hours=i), price))
        
        return price_data
    
    def _generate_gradual_decline_scenario(self, initial_price: Decimal) -> List[Tuple[datetime, Decimal]]:
        """Generate gradual decline scenario."""
        price_data = []
        current_time = datetime.now()
        
        # 21 days of gradual decline to -50%
        steps = 504  # 21 days hourly
        
        for i in range(steps):
            base_decline = float(i) / float(steps - 1) * 0.50  # 50% decline
            volatility = random.uniform(-0.03, 0.03)  # ±3% daily volatility
            
            price_ratio = 1.0 - base_decline + volatility
            price_ratio = max(0.45, min(1.05, price_ratio))
            
            price = initial_price * Decimal(str(price_ratio))
            price_data.append((current_time + timedelta(hours=i), price))
        
        return price_data
    
    def _generate_bear_market_scenario(self, initial_price: Decimal) -> List[Tuple[datetime, Decimal]]:
        """Generate extended bear market decline over several months."""
        price_data = []
        current_time = datetime.now()
        
        # 90 days of gradual decline to -70% with relief rallies
        steps = 2160  # 90 days hourly
        
        for i in range(steps):
            time_ratio = float(i) / float(steps - 1)
            
            # Base decline from 1.0 to 0.3 (-70%)
            base_decline = 0.7 * time_ratio
            
            # Add relief rallies (temporary bounces upward)
            relief_rally = 0.1 * math.sin(time_ratio * 8 * math.pi) * (1 - time_ratio)  # Weaker over time
            
            # Daily volatility decreases over time (capitulation)
            volatility_factor = max(0.02, 0.08 * (1 - time_ratio))
            volatility = random.uniform(-volatility_factor, volatility_factor)
            
            price_ratio = 1.0 - base_decline + relief_rally + volatility
            price_ratio = max(0.25, min(1.1, price_ratio))  # Floor at -75%, ceiling at +10%
            
            price = initial_price * Decimal(str(price_ratio))
            price_data.append((current_time + timedelta(hours=i), price))
        
        return price_data
    
    def _generate_bull_market_scenario(self, initial_price: Decimal) -> List[Tuple[datetime, Decimal]]:
        """Generate strong bull market with corrections."""
        price_data = []
        current_time = datetime.now()
        
        # 60 days rising to +300% with corrections
        steps = 1440  # 60 days hourly
        
        for i in range(steps):
            time_ratio = float(i) / float(steps - 1)
            
            # Exponential growth pattern (slower initially, accelerates)
            growth_factor = time_ratio ** 1.5  # Exponential curve
            base_growth = 3.0 * growth_factor  # 300% total growth
            
            # Add corrections (temporary drops)
            correction = -0.2 * math.sin(time_ratio * 6 * math.pi) * random.uniform(0.5, 1.0)
            
            # Higher volatility in bull markets
            volatility = random.uniform(-0.05, 0.08)  # Slightly bullish bias
            
            price_ratio = 1.0 + base_growth + correction + volatility
            price_ratio = max(0.8, min(5.0, price_ratio))  # Floor at -20%, ceiling at +400%
            
            price = initial_price * Decimal(str(price_ratio))
            price_data.append((current_time + timedelta(hours=i), price))
        
        return price_data
    
    def _generate_sideways_market_scenario(self, initial_price: Decimal) -> List[Tuple[datetime, Decimal]]:
        """Generate sideways/range-bound market."""
        price_data = []
        current_time = datetime.now()
        
        # 30 days of sideways action in ±15% range
        steps = 720  # 30 days hourly
        
        for i in range(steps):
            time_ratio = float(i) / float(steps - 1)
            
            # Oscillating pattern within range
            oscillation = 0.15 * math.sin(time_ratio * 10 * math.pi)  # 10 cycles
            
            # Random noise
            noise = random.uniform(-0.05, 0.05)
            
            # Slight trend bias (can go either direction)
            trend_bias = random.choice([-0.02, 0.02]) * time_ratio
            
            price_ratio = 1.0 + oscillation + noise + trend_bias
            price_ratio = max(0.8, min(1.2, price_ratio))  # Stay in ±20% range
            
            price = initial_price * Decimal(str(price_ratio))
            price_data.append((current_time + timedelta(hours=i), price))
        
        return price_data
    
    def _generate_flash_crash_scenario(self, initial_price: Decimal) -> List[Tuple[datetime, Decimal]]:
        """Generate flash crash and quick recovery."""
        price_data = []
        current_time = datetime.now()
        
        # Phase 1: Normal trading for 2 days
        for i in range(48):
            volatility = random.uniform(-0.02, 0.02)
            price_ratio = 1.0 + volatility
            price = initial_price * Decimal(str(price_ratio))
            price_data.append((current_time + timedelta(hours=i), price))
        
        # Phase 2: Flash crash over 4 hours (-50%)
        crash_start = 48
        crash_hours = 4
        for i in range(crash_hours):
            crash_progress = (i + 1) / crash_hours
            # Accelerating crash
            crash_factor = -(0.5 * (crash_progress ** 2))  # -50% crash
            volatility = random.uniform(-0.1, 0.05)  # High volatility during crash
            
            price_ratio = 1.0 + crash_factor + volatility
            price_ratio = max(0.4, price_ratio)  # Floor at -60%
            
            price = initial_price * Decimal(str(price_ratio))
            price_data.append((current_time + timedelta(hours=crash_start + i), price))
        
        # Phase 3: Quick recovery over 8 hours back to -10%
        recovery_start = crash_start + crash_hours
        recovery_hours = 8
        for i in range(recovery_hours):
            recovery_progress = (i + 1) / recovery_hours
            # From -50% back to -10%
            recovery_factor = -0.5 + (0.4 * recovery_progress)  # Recover 40 percentage points
            volatility = random.uniform(-0.08, 0.08)  # High volatility during recovery
            
            price_ratio = 1.0 + recovery_factor + volatility
            price_ratio = max(0.4, min(1.0, price_ratio))
            
            price = initial_price * Decimal(str(price_ratio))
            price_data.append((current_time + timedelta(hours=recovery_start + i), price))
        
        # Phase 4: Gradual normalization over remaining time
        normalization_start = recovery_start + recovery_hours
        remaining_hours = 168 - normalization_start  # Fill to 7 days total
        
        for i in range(remaining_hours):
            normalization_progress = (i + 1) / remaining_hours
            # Gradually return toward initial price
            base_recovery = -0.1 + (0.15 * normalization_progress)  # -10% to +5%
            volatility = random.uniform(-0.03, 0.03)
            
            price_ratio = 1.0 + base_recovery + volatility
            price_ratio = max(0.7, min(1.1, price_ratio))
            
            price = initial_price * Decimal(str(price_ratio))
            price_data.append((current_time + timedelta(hours=normalization_start + i), price))
        
        return price_data
    
    def _generate_crypto_winter_scenario(self, initial_price: Decimal) -> List[Tuple[datetime, Decimal]]:
        """Generate crypto winter (prolonged bear market with low volatility)."""
        price_data = []
        current_time = datetime.now()
        
        # 120 days of gradual decline to -80% with decreasing volatility
        steps = 2880  # 120 days hourly
        
        for i in range(steps):
            time_ratio = float(i) / float(steps - 1)
            
            # Steep initial decline, then slow grind down
            if time_ratio < 0.3:  # First 30% of time
                decline_factor = -0.6 * (time_ratio / 0.3)  # -60% in first phase
            else:  # Remaining 70% of time
                remaining_progress = (time_ratio - 0.3) / 0.7
                decline_factor = -0.6 + (-0.2 * remaining_progress)  # Additional -20%
            
            # Decreasing volatility over time (market "dies")
            volatility_factor = max(0.01, 0.06 * (1 - time_ratio))
            volatility = random.uniform(-volatility_factor, volatility_factor)
            
            # Occasional dead cat bounces
            if random.random() < 0.05:  # 5% chance
                bounce = random.uniform(0.05, 0.15)  # 5-15% bounce
            else:
                bounce = 0
            
            price_ratio = 1.0 + decline_factor + volatility + bounce
            price_ratio = max(0.15, min(1.0, price_ratio))  # Floor at -85%
            
            price = initial_price * Decimal(str(price_ratio))
            price_data.append((current_time + timedelta(hours=i), price))
        
        return price_data
    
    def _generate_altcoin_season_scenario(self, initial_price: Decimal) -> List[Tuple[datetime, Decimal]]:
        """Generate altcoin season (explosive growth with high volatility)."""
        price_data = []
        current_time = datetime.now()
        
        # 45 days of explosive growth to +800% with extreme volatility
        steps = 1080  # 45 days hourly
        
        for i in range(steps):
            time_ratio = float(i) / float(steps - 1)
            
            # Parabolic growth pattern
            growth_factor = 8.0 * (time_ratio ** 2)  # Parabolic to +800%
            
            # Extreme volatility (±20% swings)
            volatility = random.uniform(-0.2, 0.25)  # Slightly bullish bias
            
            # Periodic corrections
            correction_cycle = math.sin(time_ratio * 8 * math.pi)
            correction = -0.15 * correction_cycle * random.uniform(0, 1)
            
            price_ratio = 1.0 + growth_factor + volatility + correction
            price_ratio = max(0.5, min(12.0, price_ratio))  # Floor at -50%, ceiling at +1100%
            
            price = initial_price * Decimal(str(price_ratio))
            price_data.append((current_time + timedelta(hours=i), price))
        
        return price_data
    
    def _generate_double_bottom_scenario(self, initial_price: Decimal) -> List[Tuple[datetime, Decimal]]:
        """Generate double bottom pattern (classic reversal)."""
        price_data = []
        current_time = datetime.now()
        
        # 40 days forming double bottom pattern
        steps = 960  # 40 days hourly
        
        for i in range(steps):
            time_ratio = float(i) / float(steps - 1)
            
            # Create double bottom pattern
            if time_ratio < 0.2:  # First decline to -40%
                decline_factor = -0.4 * (time_ratio / 0.2)
            elif time_ratio < 0.4:  # First recovery to -15%
                recovery_progress = (time_ratio - 0.2) / 0.2
                decline_factor = -0.4 + (0.25 * recovery_progress)
            elif time_ratio < 0.6:  # Second decline to -40% (double bottom)
                decline_progress = (time_ratio - 0.4) / 0.2
                decline_factor = -0.15 + (-0.25 * decline_progress)
            else:  # Final recovery and breakout to +50%
                breakout_progress = (time_ratio - 0.6) / 0.4
                decline_factor = -0.4 + (0.9 * (breakout_progress ** 1.5))  # Accelerating recovery
            
            # Moderate volatility
            volatility = random.uniform(-0.04, 0.04)
            
            price_ratio = 1.0 + decline_factor + volatility
            price_ratio = max(0.55, min(1.6, price_ratio))
            
            price = initial_price * Decimal(str(price_ratio))
            price_data.append((current_time + timedelta(hours=i), price))
        
        return price_data
    
    def _generate_dead_cat_bounce_scenario(self, initial_price: Decimal) -> List[Tuple[datetime, Decimal]]:
        """Generate dead cat bounce (false recovery after crash)."""
        price_data = []
        current_time = datetime.now()
        
        # 30 days: crash, bounce, then continued decline
        steps = 720  # 30 days hourly
        
        for i in range(steps):
            time_ratio = float(i) / float(steps - 1)
            
            if time_ratio < 0.3:  # Initial crash to -60%
                crash_progress = time_ratio / 0.3
                decline_factor = -0.6 * crash_progress
            elif time_ratio < 0.6:  # Dead cat bounce back to -25%
                bounce_progress = (time_ratio - 0.3) / 0.3
                decline_factor = -0.6 + (0.35 * bounce_progress)
            else:  # Continued decline to -75%
                decline_progress = (time_ratio - 0.6) / 0.4
                decline_factor = -0.25 + (-0.5 * decline_progress)
            
            # Higher volatility during bounce phase
            if 0.3 <= time_ratio <= 0.6:
                volatility = random.uniform(-0.08, 0.08)
            else:
                volatility = random.uniform(-0.04, 0.04)
            
            price_ratio = 1.0 + decline_factor + volatility
            price_ratio = max(0.2, min(1.0, price_ratio))
            
            price = initial_price * Decimal(str(price_ratio))
            price_data.append((current_time + timedelta(hours=i), price))
        
        return price_data
    
    def _generate_whale_manipulation_scenario(self, initial_price: Decimal) -> List[Tuple[datetime, Decimal]]:
        """Generate whale manipulation pattern (pump and dump cycles)."""
        price_data = []
        current_time = datetime.now()
        
        # 21 days with multiple pump and dump cycles
        steps = 504  # 21 days hourly
        
        for i in range(steps):
            time_ratio = float(i) / float(steps - 1)
            
            # Base gradual decline
            base_decline = -0.3 * time_ratio
            
            # Multiple pump cycles (4 pumps over the period)
            cycle_position = (time_ratio * 4) % 1  # 4 cycles
            
            if cycle_position < 0.3:  # Pump phase (quick rise)
                pump_progress = cycle_position / 0.3
                pump_factor = 0.4 * math.sin(pump_progress * math.pi)  # +40% pump
            elif cycle_position < 0.8:  # Dump phase (gradual decline)
                dump_progress = (cycle_position - 0.3) / 0.5
                pump_factor = 0.4 * (1 - dump_progress)  # Gradual dump
            else:  # Consolidation
                pump_factor = 0
            
            # High volatility during pump/dump
            if cycle_position < 0.8:
                volatility = random.uniform(-0.1, 0.1)
            else:
                volatility = random.uniform(-0.03, 0.03)
            
            price_ratio = 1.0 + base_decline + pump_factor + volatility
            price_ratio = max(0.4, min(1.8, price_ratio))
            
            price = initial_price * Decimal(str(price_ratio))
            price_data.append((current_time + timedelta(hours=i), price))
        
        return price_data
    
    def _update_market_regime(self, position: SimulatedPosition, recent_data: List[Tuple[datetime, Decimal]]) -> None:
        """Update market regime based on recent price history."""
        if len(recent_data) < 2:
            return
            
        # Calculate trend over lookback period
        start_price = recent_data[0][1]
        end_price = recent_data[-1][1]
        trend_pct = ((end_price - start_price) / start_price) * 100
        
        # Calculate volatility (daily price changes)
        daily_changes = []
        for i in range(1, len(recent_data), 24):  # Sample every 24 hours
            if i < len(recent_data):
                prev_price = recent_data[i-1][1] if i > 0 else recent_data[0][1]
                curr_price = recent_data[i][1]
                daily_change = abs((curr_price - prev_price) / prev_price) * 100
                daily_changes.append(daily_change)
        
        avg_volatility = sum(daily_changes) / len(daily_changes) if daily_changes else 0
        
        # Determine market regime
        old_regime = position.current_market_regime
        
        if trend_pct <= self.config.trend_detection.bear_trend_threshold:
            position.current_market_regime = "bear"
        elif trend_pct >= self.config.trend_detection.bull_trend_threshold:
            position.current_market_regime = "bull" 
        elif avg_volatility >= float(self.config.trend_detection.volatility_threshold):
            position.current_market_regime = "volatile"
        else:
            position.current_market_regime = "normal"
            
        # Reset completed levels when regime changes significantly
        if old_regime != position.current_market_regime and old_regime != "normal":
            position.completed_sell_levels = []
            position.completed_rebuy_levels = []
            
        # Optional: Log regime changes for debugging
        # if old_regime != position.current_market_regime:
        #     print(f"Market regime changed: {old_regime} -> {position.current_market_regime} "
        #           f"(trend: {trend_pct:+.1f}%, volatility: {avg_volatility:.1f}%)")
    
    def _check_progressive_stop_loss(self, position: SimulatedPosition, price: Decimal, timestamp: datetime) -> bool:
        """Check and execute progressive stop loss in bear markets."""
        if not self.config.progressive_stop_loss_enabled:
            return False
            
        if position.progressive_stop_triggered:
            return True  # Already triggered
            
        # Only activate in bear market regime
        if position.current_market_regime != "bear":
            return False
            
        # Check if decline exceeds threshold
        decline_pct = ((position.swing_entry_price - price) / position.swing_entry_price) * 100
        
        if decline_pct >= self.config.progressive_stop_loss_threshold:
            # Trigger progressive stop - sell everything
            if position.amount > 0:
                sell_value_eur = position.amount * price
                cash_reserve_amount = sell_value_eur * (self.config.swing_cash_reserve_pct / 100)
                
                # Record the emergency sell
                trade = Trade(
                    timestamp=timestamp,
                    action="emergency_stop",
                    price=price,
                    amount_crypto=position.amount,
                    amount_eur=sell_value_eur,
                    reason=f"Progressive stop loss: {decline_pct:.1f}% decline in bear market",
                    cash_reserve_after=cash_reserve_amount,
                    position_after=Decimal('0')
                )
                self.trades.append(trade)
                
                print(f"{timestamp.strftime('%H:%M')} EMERGENCY STOP: "
                      f"Sold all {position.amount:.8f} BTC at EUR{price} ({decline_pct:+.1f}%) -> "
                      f"Cash: +EUR{cash_reserve_amount:.2f}")
                
                # Update position
                position.amount = Decimal('0')
                position.cash_reserve = cash_reserve_amount
                position.progressive_stop_triggered = True
                position.trade_count += 1
                
            return True
            
        return False
    
    def _get_adaptive_swing_levels(self, position: SimulatedPosition) -> List[SwingLevel]:
        """Get swing levels adapted to current market regime."""
        if position.current_market_regime == "bear":
            return self.config.bear_market_swing_levels
        elif position.current_market_regime == "bull":
            return self.config.bull_market_swing_levels
        else:
            return self.config.swing_levels  # Normal/volatile use standard levels
    
    def _process_adaptive_swing_opportunities(self, position: SimulatedPosition, price: Decimal, timestamp: datetime):
        """Process swing trading with adaptive levels based on market regime."""
        if not self.config.swing_trading_enabled:
            return
            
        if position.progressive_stop_triggered:
            # Only allow rebuying after progressive stop, no more selling
            swing_levels = [level for level in self._get_adaptive_swing_levels(position) if level.action == 'rebuy']
        else:
            swing_levels = self._get_adaptive_swing_levels(position)
        
        # Calculate drop percentage from swing entry price
        drop_pct = ((position.swing_entry_price - price) / position.swing_entry_price) * 100
        
        # Process swing levels in order
        for i, swing_level in enumerate(swing_levels, 1):
            if drop_pct >= swing_level.threshold_pct:
                
                if swing_level.action == 'sell' and not position.progressive_stop_triggered:
                    # Check if this sell level is already completed
                    if i not in position.completed_sell_levels:
                        success = self._execute_adaptive_swing_sell(position, price, swing_level, i, timestamp, drop_pct)
                        if success:
                            position.completed_sell_levels.append(i)
                
                elif swing_level.action == 'rebuy':
                    # Check if this rebuy level is already completed
                    if i not in position.completed_rebuy_levels:
                        success = self._execute_adaptive_swing_rebuy(position, price, swing_level, i, timestamp, drop_pct)
                        if success:
                            position.completed_rebuy_levels.append(i)
    
    def _execute_adaptive_swing_sell(self, position: SimulatedPosition, price: Decimal, 
                           swing_level: SwingLevel, level: int, timestamp: datetime, drop_pct: float) -> bool:
        """Execute adaptive swing sell with regime-specific logic."""
        if position.amount <= 0:
            return False
        
        # Calculate amount to sell
        sell_amount = position.amount * swing_level.allocation
        sell_value_eur = sell_amount * price
        
        # Calculate cash to reserve (keep percentage for rebuying)
        cash_reserve_amount = sell_value_eur * (self.config.swing_cash_reserve_pct / 100)
        
        # Update position
        position.amount -= sell_amount
        position.cash_reserve += cash_reserve_amount
        position.swing_entry_price = price  # Update swing baseline
        position.trade_count += 1
        
        # Record trade
        trade = Trade(
            timestamp=timestamp,
            action=f"swing_sell_{position.current_market_regime}",
            price=price,
            amount_crypto=sell_amount,
            amount_eur=sell_value_eur,
            reason=f"{position.current_market_regime.title()} swing sell level {level}: {drop_pct:.1f}% drop",
            cash_reserve_after=position.cash_reserve,
            position_after=position.amount
        )
        self.trades.append(trade)
        
        print(f"{timestamp.strftime('%H:%M')} {position.current_market_regime.upper()} SELL Level {level}: "
              f"{swing_level.allocation:.0%} at EUR{price} ({drop_pct:+.1f}%) -> "
              f"Cash: +EUR{cash_reserve_amount:.2f}")
        
        return True
    
    def _execute_adaptive_swing_rebuy(self, position: SimulatedPosition, price: Decimal,
                            swing_level: SwingLevel, level: int, timestamp: datetime, drop_pct: float) -> bool:
        """Execute adaptive swing rebuy with regime-specific logic."""
        if position.cash_reserve <= 0:
            return False
        
        # Calculate rebuy amount
        rebuy_amount_eur = position.cash_reserve * swing_level.allocation
        rebuy_amount_crypto = rebuy_amount_eur / price
        
        # Update position
        position.amount += rebuy_amount_crypto
        position.cash_reserve -= rebuy_amount_eur
        position.trade_count += 1
        
        # Record trade
        trade = Trade(
            timestamp=timestamp,
            action=f"swing_rebuy_{position.current_market_regime}",
            price=price,
            amount_crypto=rebuy_amount_crypto,
            amount_eur=rebuy_amount_eur,
            reason=f"{position.current_market_regime.title()} swing rebuy level {level}: {drop_pct:.1f}% drop",
            cash_reserve_after=position.cash_reserve,
            position_after=position.amount
        )
        self.trades.append(trade)
        
        print(f"{timestamp.strftime('%H:%M')} {position.current_market_regime.upper()} REBUY Level {level}: "
              f"{swing_level.allocation:.0%} cash at EUR{price} ({drop_pct:+.1f}%) -> "
              f"BTC: +{rebuy_amount_crypto:.8f}")
        
        return True
    
    def _process_swing_opportunities(self, position: SimulatedPosition, price: Decimal, timestamp: datetime):
        """Process swing trading opportunities at current price."""
        if not self.config.swing_trading_enabled:
            return
        
        # Calculate drop percentage from swing entry price
        drop_pct = ((position.swing_entry_price - price) / position.swing_entry_price) * 100
        
        # Process swing levels in order
        for i, swing_level in enumerate(self.config.swing_levels, 1):
            if drop_pct >= swing_level.threshold_pct:
                
                if swing_level.action == 'sell':
                    # Check if this sell level is already completed
                    if i not in position.completed_sell_levels:
                        success = self._execute_swing_sell(position, price, swing_level, i, timestamp, drop_pct)
                        if success:
                            position.completed_sell_levels.append(i)
                
                elif swing_level.action == 'rebuy':
                    # Check if this rebuy level is already completed
                    if i not in position.completed_rebuy_levels:
                        success = self._execute_swing_rebuy(position, price, swing_level, i, timestamp, drop_pct)
                        if success:
                            position.completed_rebuy_levels.append(i)
    
    def _execute_swing_sell(self, position: SimulatedPosition, price: Decimal, 
                           swing_level: SwingLevel, level: int, timestamp: datetime, drop_pct: float) -> bool:
        """Execute a simulated swing sell."""
        if position.amount <= 0:
            return False
        
        # Calculate amount to sell
        sell_amount = position.amount * swing_level.allocation
        sell_value_eur = sell_amount * price
        
        # Calculate cash to reserve (keep percentage for rebuying)
        cash_reserve_amount = sell_value_eur * (self.config.swing_cash_reserve_pct / 100)
        
        # Update position
        position.amount -= sell_amount
        position.cash_reserve += cash_reserve_amount
        position.swing_entry_price = price  # Update swing baseline
        position.trade_count += 1
        
        # Record trade
        trade = Trade(
            timestamp=timestamp,
            action="swing_sell",
            price=price,
            amount_crypto=sell_amount,
            amount_eur=sell_value_eur,
            reason=f"Swing sell level {level}: {drop_pct:.1f}% drop",
            cash_reserve_after=position.cash_reserve,
            position_after=position.amount
        )
        self.trades.append(trade)
        
        print(f"{timestamp.strftime('%H:%M')} SWING SELL Level {level}: "
              f"{swing_level.allocation:.0%} at EUR{price} ({drop_pct:+.1f}%) -> "
              f"Cash: +EUR{cash_reserve_amount:.2f}")
        
        return True
    
    def _execute_swing_rebuy(self, position: SimulatedPosition, price: Decimal,
                            swing_level: SwingLevel, level: int, timestamp: datetime, drop_pct: float) -> bool:
        """Execute a simulated swing rebuy."""
        if position.cash_reserve <= 0:
            return False
        
        # Calculate rebuy amount
        rebuy_amount_eur = position.cash_reserve * swing_level.allocation
        rebuy_amount_crypto = rebuy_amount_eur / price
        
        # Update position
        position.amount += rebuy_amount_crypto
        position.cash_reserve -= rebuy_amount_eur
        position.trade_count += 1
        
        # Record trade
        trade = Trade(
            timestamp=timestamp,
            action="swing_rebuy",
            price=price,
            amount_crypto=rebuy_amount_crypto,
            amount_eur=rebuy_amount_eur,
            reason=f"Swing rebuy level {level}: {drop_pct:.1f}% drop",
            cash_reserve_after=position.cash_reserve,
            position_after=position.amount
        )
        self.trades.append(trade)
        
        print(f"{timestamp.strftime('%H:%M')} SWING REBUY Level {level}: "
              f"{swing_level.allocation:.0%} cash at EUR{price} ({drop_pct:+.1f}%) -> "
              f"BTC: +{rebuy_amount_crypto:.8f}")
        
        return True

def create_sample_config() -> AssetProtectionConfig:
    """Create a sample swing trading configuration."""
    return AssetProtectionConfig(
        enabled=True,
        protected_assets=["BTC-EUR"],
        swing_trading_enabled=True,
        swing_levels=[
            SwingLevel(threshold_pct=Decimal('5'), action='sell', allocation=Decimal('0.25')),
            SwingLevel(threshold_pct=Decimal('10'), action='sell', allocation=Decimal('0.25')),
            SwingLevel(threshold_pct=Decimal('20'), action='rebuy', allocation=Decimal('0.5')),
            SwingLevel(threshold_pct=Decimal('30'), action='rebuy', allocation=Decimal('0.5'))
        ],
        swing_cash_reserve_pct=Decimal('75.0'),
        swing_trailing_stop_enabled=True
    )

def print_detailed_results(result: SimulationResult):
    """Print detailed simulation results."""
    print("\n" + "="*60)
    print("SWING TRADING SIMULATION RESULTS")
    print("="*60)
    
    print(f"Initial Value:     EUR{result.initial_value_eur:,.2f}")
    print(f"Final Value:       EUR{result.final_value_eur:,.2f}")
    print(f"Total Profit:      EUR{result.total_profit_eur:+,.2f}")
    print(f"Profit %:          {result.profit_percentage:+.2f}%")
    print()
    print(f"Initial BTC:       {result.trades[0].position_after + result.trades[0].amount_crypto:.8f} BTC" if result.trades else "N/A")
    print(f"Final BTC:         {result.final_crypto_amount:.8f} BTC")
    print(f"Final Cash:        EUR{result.final_cash_reserve:.2f}")
    print()
    print(f"Max Drawdown:      {result.max_drawdown_pct:.1f}%")
    print(f"Total Trades:      {result.total_trades}")
    print()
    
    if result.trades:
        print("TRADE HISTORY:")
        print("-" * 60)
        for i, trade in enumerate(result.trades, 1):
            action_icon = "SELL" if trade.action == "swing_sell" else "BUY "
            print(f"{i:2d}. {action_icon} {trade.timestamp.strftime('%m/%d %H:%M')} "
                  f"{trade.action.upper():11s} "
                  f"EUR{trade.price:7,.0f} "
                  f"{trade.amount_crypto:12.8f} BTC "
                  f"EUR{trade.amount_eur:8,.2f}")

def run_comprehensive_analysis():
    """Run comprehensive analysis across all market scenarios."""
    print("COMPREHENSIVE SWING TRADING ANALYSIS")
    print("=" * 60)
    
    # User's actual holdings
    btc_amount = Decimal('0.376')
    btc_price = Decimal('105000')
    
    print(f"Your BTC Holdings: {btc_amount} BTC @ EUR{btc_price}")
    print(f"Total Value: EUR{btc_amount * btc_price:,.2f}")
    print()
    
    # Test configurations with adaptive bear market protection
    configs = {
        "Bear-Protected": AssetProtectionConfig(
            enabled=True,
            swing_trading_enabled=True,
            # Normal market levels (moderate selling)
            swing_levels=[
                SwingLevel(threshold_pct=Decimal('6'), action='sell', allocation=Decimal('0.20')),
                SwingLevel(threshold_pct=Decimal('12'), action='sell', allocation=Decimal('0.20')),
                SwingLevel(threshold_pct=Decimal('25'), action='rebuy', allocation=Decimal('0.6')),
                SwingLevel(threshold_pct=Decimal('35'), action='rebuy', allocation=Decimal('0.4'))
            ],
            # Bear market levels (aggressive selling, deep rebuys)
            bear_market_swing_levels=[
                SwingLevel(threshold_pct=Decimal('2'), action='sell', allocation=Decimal('0.25')),
                SwingLevel(threshold_pct=Decimal('5'), action='sell', allocation=Decimal('0.30')),
                SwingLevel(threshold_pct=Decimal('10'), action='sell', allocation=Decimal('0.35')),
                SwingLevel(threshold_pct=Decimal('50'), action='rebuy', allocation=Decimal('0.4')),
                SwingLevel(threshold_pct=Decimal('70'), action='rebuy', allocation=Decimal('0.6'))
            ],
            # Bull market levels (minimal selling, quick rebuys)
            bull_market_swing_levels=[
                SwingLevel(threshold_pct=Decimal('10'), action='sell', allocation=Decimal('0.15')),
                SwingLevel(threshold_pct=Decimal('18'), action='rebuy', allocation=Decimal('0.7')),
                SwingLevel(threshold_pct=Decimal('28'), action='rebuy', allocation=Decimal('0.3'))
            ],
            swing_cash_reserve_pct=Decimal('80.0'),
            progressive_stop_loss_enabled=True,
            progressive_stop_loss_threshold=Decimal('20.0')
        ),
        "Conservative": AssetProtectionConfig(
            enabled=True,
            swing_trading_enabled=True,
            swing_levels=[
                SwingLevel(threshold_pct=Decimal('8'), action='sell', allocation=Decimal('0.15')),
                SwingLevel(threshold_pct=Decimal('15'), action='sell', allocation=Decimal('0.15')),
                SwingLevel(threshold_pct=Decimal('25'), action='rebuy', allocation=Decimal('0.7')),
                SwingLevel(threshold_pct=Decimal('40'), action='rebuy', allocation=Decimal('0.3'))
            ],
            bear_market_swing_levels=[
                SwingLevel(threshold_pct=Decimal('5'), action='sell', allocation=Decimal('0.20')),
                SwingLevel(threshold_pct=Decimal('10'), action='sell', allocation=Decimal('0.25')),
                SwingLevel(threshold_pct=Decimal('15'), action='sell', allocation=Decimal('0.30')),
                SwingLevel(threshold_pct=Decimal('45'), action='rebuy', allocation=Decimal('0.5')),
                SwingLevel(threshold_pct=Decimal('65'), action='rebuy', allocation=Decimal('0.5'))
            ],
            bull_market_swing_levels=[
                SwingLevel(threshold_pct=Decimal('12'), action='sell', allocation=Decimal('0.10')),
                SwingLevel(threshold_pct=Decimal('20'), action='rebuy', allocation=Decimal('0.6')),
                SwingLevel(threshold_pct=Decimal('30'), action='rebuy', allocation=Decimal('0.4'))
            ],
            swing_cash_reserve_pct=Decimal('85.0'),
            progressive_stop_loss_enabled=True,
            progressive_stop_loss_threshold=Decimal('30.0')
        ),
        "Aggressive": AssetProtectionConfig(
            enabled=True,
            swing_trading_enabled=True,
            swing_levels=[
                SwingLevel(threshold_pct=Decimal('3'), action='sell', allocation=Decimal('0.30')),
                SwingLevel(threshold_pct=Decimal('7'), action='sell', allocation=Decimal('0.30')),
                SwingLevel(threshold_pct=Decimal('15'), action='rebuy', allocation=Decimal('0.6')),
                SwingLevel(threshold_pct=Decimal('25'), action='rebuy', allocation=Decimal('0.4'))
            ],
            bear_market_swing_levels=[
                SwingLevel(threshold_pct=Decimal('1'), action='sell', allocation=Decimal('0.30')),
                SwingLevel(threshold_pct=Decimal('3'), action='sell', allocation=Decimal('0.35')),
                SwingLevel(threshold_pct=Decimal('6'), action='sell', allocation=Decimal('0.25')),
                SwingLevel(threshold_pct=Decimal('40'), action='rebuy', allocation=Decimal('0.5')),
                SwingLevel(threshold_pct=Decimal('60'), action='rebuy', allocation=Decimal('0.5'))
            ],
            bull_market_swing_levels=[
                SwingLevel(threshold_pct=Decimal('8'), action='sell', allocation=Decimal('0.20')),
                SwingLevel(threshold_pct=Decimal('15'), action='rebuy', allocation=Decimal('0.8')),
                SwingLevel(threshold_pct=Decimal('25'), action='rebuy', allocation=Decimal('0.2'))
            ],
            swing_cash_reserve_pct=Decimal('70.0'),
            progressive_stop_loss_enabled=True,
            progressive_stop_loss_threshold=Decimal('15.0')
        )
    }
    
    all_scenarios = ["crash_recovery", "volatile_waves", "gradual_decline", "bear_market", 
                    "bull_market", "sideways_market", "flash_crash", "crypto_winter", 
                    "altcoin_season", "double_bottom", "dead_cat_bounce", "whale_manipulation"]
    
    # Comprehensive results storage
    all_results = {}
    
    print("RUNNING COMPREHENSIVE ANALYSIS...")
    print("This may take a moment to complete all scenarios...")
    print()
    
    for config_name, config in configs.items():
        print(f"Testing {config_name} strategy across all scenarios...")
        config_results = {}
        
        for scenario in all_scenarios:
            simulator = SwingTradingSimulator(config)
            result = simulator.simulate_market_scenario(btc_price, btc_amount, scenario)
            config_results[scenario] = result
        
        all_results[config_name] = config_results
        print(f"  Completed {config_name}")
    
    # Generate comprehensive analysis
    print("\n" + "=" * 80)
    print("COMPREHENSIVE ANALYSIS RESULTS")
    print("=" * 80)
    
    # Summary table by strategy
    print("\nSUMMARY BY STRATEGY:")
    print("-" * 60)
    print(f"{'Strategy':<12} {'Avg Profit':<12} {'Win Rate':<10} {'Max Gain':<12} {'Max Loss':<12}")
    print("-" * 60)
    
    strategy_summaries = {}
    for config_name, config_results in all_results.items():
        profits = [result.total_profit_eur for result in config_results.values()]
        profit_pcts = [result.profit_percentage for result in config_results.values()]
        
        avg_profit = sum(profits) / len(profits)
        avg_profit_pct = sum(profit_pcts) / len(profit_pcts)
        win_rate = len([p for p in profits if p > 0]) / len(profits) * 100
        max_gain = max(profit_pcts)
        max_loss = min(profit_pcts)
        
        strategy_summaries[config_name] = {
            'avg_profit_eur': avg_profit,
            'avg_profit_pct': avg_profit_pct,
            'win_rate': win_rate,
            'max_gain': max_gain,
            'max_loss': max_loss,
            'total_trades': sum(result.total_trades for result in config_results.values())
        }
        
        print(f"{config_name:<12} EUR{avg_profit:+7.0f} ({avg_profit_pct:+5.1f}%) "
              f"{win_rate:>6.0f}% {max_gain:+8.1f}% {max_loss:+8.1f}%")
    
    # Scenario analysis
    print("\n\nPERFORMANCE BY MARKET SCENARIO:")
    print("-" * 80)
    print(f"{'Scenario':<16} {'Conservative':<14} {'Balanced':<12} {'Aggressive':<12} {'Best Strategy'}")
    print("-" * 80)
    
    for scenario in all_scenarios:
        scenario_results = {config: all_results[config][scenario].profit_percentage 
                          for config in configs.keys()}
        
        best_strategy = max(scenario_results.keys(), key=lambda x: scenario_results[x])
        
        print(f"{scenario.replace('_', ' ').title():<16} "
              f"{scenario_results['Conservative']:+6.1f}% "
              f"     {scenario_results['Balanced']:+6.1f}% "
              f"    {scenario_results['Aggressive']:+6.1f}% "
              f"    {best_strategy}")
    
    # Risk analysis
    print("\n\nRISK ANALYSIS:")
    print("-" * 50)
    for config_name, summary in strategy_summaries.items():
        drawdowns = [all_results[config_name][scenario].max_drawdown_pct 
                    for scenario in all_scenarios]
        avg_drawdown = sum(drawdowns) / len(drawdowns)
        max_drawdown = max(drawdowns)
        
        print(f"\n{config_name} Strategy:")
        print(f"  Average Drawdown: {avg_drawdown:.1f}%")
        print(f"  Maximum Drawdown: {max_drawdown:.1f}%")
        print(f"  Total Trades: {summary['total_trades']}")
        print(f"  Risk-Adjusted Return: {summary['avg_profit_pct'] / max(1, max_drawdown):.2f}")
    
    # Recommendations
    print("\n\nRECOMMENDATIONS:")
    print("-" * 40)
    
    best_overall = max(strategy_summaries.keys(), 
                      key=lambda x: strategy_summaries[x]['avg_profit_pct'])
    most_consistent = max(strategy_summaries.keys(),
                         key=lambda x: strategy_summaries[x]['win_rate'])
    
    print(f"Best Overall Performance: {best_overall}")
    print(f"Most Consistent (Win Rate): {most_consistent}")
    
    # Market-specific recommendations
    print(f"\nMarket-Specific Recommendations:")
    bear_scenarios = ['bear_market', 'crypto_winter', 'gradual_decline', 'dead_cat_bounce']
    bull_scenarios = ['bull_market', 'altcoin_season', 'double_bottom']
    volatile_scenarios = ['crash_recovery', 'volatile_waves', 'flash_crash', 'whale_manipulation']
    
    for scenario_type, scenarios in [('Bear Markets', bear_scenarios), 
                                   ('Bull Markets', bull_scenarios),
                                   ('Volatile Markets', volatile_scenarios)]:
        
        type_results = {}
        for config in configs.keys():
            avg_profit = sum(all_results[config][scenario].profit_percentage 
                           for scenario in scenarios) / len(scenarios)
            type_results[config] = avg_profit
        
        best_for_type = max(type_results.keys(), key=lambda x: type_results[x])
        print(f"  {scenario_type}: {best_for_type} strategy "
              f"(avg: {type_results[best_for_type]:+.1f}%)")
    
    return all_results

def run_user_portfolio_simulation():
    """Run simulation with user's actual BTC holdings."""
    print("SWING TRADING SIMULATION - YOUR BTC PORTFOLIO")
    print("=" * 60)
    
    # User's actual holdings
    btc_amount = Decimal('0.376')
    btc_price = Decimal('45000')  # Approximate current price
    
    print(f"Your BTC Holdings: {btc_amount} BTC @ EUR{btc_price}")
    print(f"Total Value: EUR{btc_amount * btc_price:,.2f}")
    print()
    
    # Test different configurations
    configs = {
        "Conservative": AssetProtectionConfig(
            enabled=True,
            swing_trading_enabled=True,
            swing_levels=[
                SwingLevel(threshold_pct=Decimal('8'), action='sell', allocation=Decimal('0.15')),
                SwingLevel(threshold_pct=Decimal('15'), action='sell', allocation=Decimal('0.15')),
                SwingLevel(threshold_pct=Decimal('25'), action='rebuy', allocation=Decimal('0.7')),
                SwingLevel(threshold_pct=Decimal('40'), action='rebuy', allocation=Decimal('0.3'))
            ],
            swing_cash_reserve_pct=Decimal('85.0')
        ),
        "Balanced": AssetProtectionConfig(
            enabled=True,
            swing_trading_enabled=True,
            swing_levels=[
                SwingLevel(threshold_pct=Decimal('5'), action='sell', allocation=Decimal('0.25')),
                SwingLevel(threshold_pct=Decimal('10'), action='sell', allocation=Decimal('0.25')),
                SwingLevel(threshold_pct=Decimal('20'), action='rebuy', allocation=Decimal('0.5')),
                SwingLevel(threshold_pct=Decimal('30'), action='rebuy', allocation=Decimal('0.5'))
            ],
            swing_cash_reserve_pct=Decimal('75.0')
        ),
        "Aggressive": AssetProtectionConfig(
            enabled=True,
            swing_trading_enabled=True,
            swing_levels=[
                SwingLevel(threshold_pct=Decimal('3'), action='sell', allocation=Decimal('0.30')),
                SwingLevel(threshold_pct=Decimal('7'), action='sell', allocation=Decimal('0.30')),
                SwingLevel(threshold_pct=Decimal('15'), action='rebuy', allocation=Decimal('0.6')),
                SwingLevel(threshold_pct=Decimal('25'), action='rebuy', allocation=Decimal('0.4'))
            ],
            swing_cash_reserve_pct=Decimal('70.0')
        )
    }
    
    scenarios = ["crash_recovery", "volatile_waves", "gradual_decline", "bear_market", 
                 "bull_market", "sideways_market", "flash_crash", "crypto_winter", 
                 "altcoin_season", "double_bottom", "dead_cat_bounce", "whale_manipulation"]
    
    for config_name, config in configs.items():
        print(f"\nTESTING {config_name.upper()} STRATEGY")
        print("-" * 40)
        
        for scenario in scenarios:
            print(f"\nScenario: {scenario.replace('_', ' ').title()}")
            simulator = SwingTradingSimulator(config)
            result = simulator.simulate_market_scenario(btc_price, btc_amount, scenario)
            
            print(f"  Profit: EUR{result.total_profit_eur:+,.2f} ({result.profit_percentage:+.1f}%)")
            print(f"  Trades: {result.total_trades}")
            print(f"  Max Drawdown: {result.max_drawdown_pct:.1f}%")

def main():
    """Main simulation runner."""
    try:
        print("SWING TRADING STRATEGY SIMULATOR")
        print("=" * 50)
        print()
        
        choice = input("Choose simulation:\n"
                      "1. Quick test with sample data\n"
                      "2. Detailed simulation with your BTC portfolio\n"
                      "3. Comprehensive analysis across all market scenarios\n"
                      "4. Custom scenario\n"
                      "Enter choice (1-4): ").strip()
        
        if choice == "1":
            # Quick test
            config = create_sample_config()
            simulator = SwingTradingSimulator(config)
            result = simulator.simulate_market_scenario(
                Decimal('45000'), Decimal('0.376'), "crash_recovery"
            )
            print_detailed_results(result)
            
        elif choice == "2":
            # Detailed simulation with user's portfolio
            run_user_portfolio_simulation()
            
        elif choice == "3":
            # Comprehensive analysis across all scenarios
            run_comprehensive_analysis()
            
        elif choice == "4":
            # Custom scenario
            print("Custom scenario builder coming soon!")
            
        else:
            print("Invalid choice. Running quick test...")
            config = create_sample_config()
            simulator = SwingTradingSimulator(config)
            result = simulator.simulate_market_scenario(
                Decimal('45000'), Decimal('0.376'), "crash_recovery"
            )
            print_detailed_results(result)
    
    except KeyboardInterrupt:
        print("\n\nSimulation cancelled by user")
    except Exception as e:
        print(f"\nSimulation error: {e}")

if __name__ == "__main__":
    main()