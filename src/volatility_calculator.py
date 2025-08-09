#!/usr/bin/env python3
"""
Volatility Calculator - Calculates asset volatility for risk management
"""

import logging
import time
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from statistics import stdev

from requests_handler import BitvavoAPI

logger = logging.getLogger(__name__)


class VolatilityCalculator:
    """
    Calculates asset volatility for risk management and dynamic stop-loss adjustment.
    
    Responsibilities:
    - Fetch historical price data from Bitvavo API
    - Calculate price volatility over configurable windows
    - Cache volatility data to reduce API calls
    - Provide volatility-adjusted risk parameters
    """
    
    def __init__(self, api: BitvavoAPI, cache_duration_minutes: int = 30):
        self.api = api
        self.cache_duration_minutes = cache_duration_minutes
        self._volatility_cache: Dict[str, Dict[str, Any]] = {}
        
    def get_volatility(self, market: str, window_hours: int = 24) -> Optional[Decimal]:
        """
        Calculate price volatility for a market over the specified time window.
        
        Args:
            market: Trading pair (e.g., 'BTC-EUR')
            window_hours: Hours of historical data to analyze
            
        Returns:
            Volatility as percentage (e.g., 15.5 for 15.5% daily volatility)
            None if calculation fails
        """
        try:
            # Input validation
            if not market or not market.strip():
                logger.error("Invalid market name provided")
                return None
                
            if not market.replace('-', '').replace('_', '').isalnum() or len(market) < 5:
                logger.error(f"Invalid market format: {market}")
                return None
                
            if window_hours <= 0 or window_hours > 168:  # Max 1 week
                logger.error(f"Invalid window_hours: {window_hours} (must be 1-168)")
                return None
            
            # Check cache first
            cache_key = f"{market}_{window_hours}"
            cached_data = self._volatility_cache.get(cache_key)
            
            if cached_data:
                cache_age_minutes = (time.time() - cached_data['timestamp']) / 60
                if cache_age_minutes < self.cache_duration_minutes:
                    logger.debug(f"Using cached volatility for {market}: {cached_data['volatility']:.2f}%")
                    return cached_data['volatility']
            
            # Fetch historical data
            historical_prices = self._fetch_historical_prices(market, window_hours)
            if not historical_prices or len(historical_prices) < 10:
                logger.warning(f"Insufficient price data for {market} volatility calculation")
                return None
            
            # Calculate volatility
            volatility = self._calculate_price_volatility(historical_prices)
            
            if volatility is not None:
                # Cache the result
                self._volatility_cache[cache_key] = {
                    'volatility': volatility,
                    'timestamp': time.time()
                }
                
                logger.debug(f"Calculated volatility for {market}: {volatility:.2f}%")
                
            return volatility
            
        except Exception as e:
            logger.error(f"Error calculating volatility for {market}: {e}")
            return None
    
    def get_volatility_adjusted_stop_loss(self, market: str, base_stop_pct: Decimal, 
                                        volatility_multiplier: Decimal = Decimal('1.5'),
                                        window_hours: int = 24) -> Decimal:
        """
        Calculate volatility-adjusted stop loss percentage.
        
        Args:
            market: Trading pair
            base_stop_pct: Base stop loss percentage (e.g., 15.0)
            volatility_multiplier: How much to adjust for volatility
            window_hours: Hours of data for volatility calculation
            
        Returns:
            Adjusted stop loss percentage
        """
        try:
            volatility = self.get_volatility(market, window_hours)
            
            if volatility is None:
                logger.warning(f"Could not calculate volatility for {market}, using base stop loss")
                return base_stop_pct
            
            # Adjust stop loss based on volatility
            # Higher volatility = wider stop loss to avoid getting stopped out by noise
            volatility_factor = (volatility / Decimal('10'))  # Normalize around 10% volatility
            adjustment = volatility_factor * volatility_multiplier
            
            adjusted_stop = base_stop_pct * (Decimal('1') + adjustment)
            
            # Apply reasonable bounds (minimum 5%, maximum 50%)
            adjusted_stop = max(Decimal('5.0'), min(adjusted_stop, Decimal('50.0')))
            
            logger.debug(f"{market} volatility-adjusted stop: {adjusted_stop:.1f}% "
                        f"(base: {base_stop_pct}%, volatility: {volatility:.1f}%)")
            
            return adjusted_stop
            
        except Exception as e:
            logger.error(f"Error calculating adjusted stop loss for {market}: {e}")
            return base_stop_pct
    
    def _fetch_historical_prices(self, market: str, window_hours: int) -> Optional[List[Decimal]]:
        """Fetch historical price data from Bitvavo API."""
        try:
            # Calculate time parameters
            end_time = int(time.time() * 1000)  # Current time in milliseconds
            start_time = end_time - (window_hours * 3600 * 1000)  # window_hours ago
            
            # Use appropriate interval based on window size
            if window_hours <= 6:
                interval = '5m'  # 5-minute candles for short windows
            elif window_hours <= 24:
                interval = '15m'  # 15-minute candles for daily windows
            elif window_hours <= 72:
                interval = '1h'   # 1-hour candles for 3-day windows
            else:
                interval = '4h'   # 4-hour candles for longer windows
            
            # Build request parameters
            params = {
                'market': market,
                'interval': interval,
                'start': start_time,
                'end': end_time,
                'limit': 1000  # Max candles to fetch
            }
            
            # Make API request
            response = self.api.send_request("GET", "/candles", params=params)
            
            if not response or not isinstance(response, list):
                logger.warning(f"No candle data received for {market}")
                return None
            
            # Extract closing prices from candle data
            # Bitvavo candles format: [timestamp, open, high, low, close, volume]
            prices = []
            for candle in response:
                if not isinstance(candle, list) or len(candle) < 5:
                    continue
                    
                try:
                    close_price = Decimal(str(candle[4]))  # Close price is index 4
                    if close_price > 0:
                        prices.append(close_price)
                except (ValueError, InvalidOperation):
                    logger.warning(f"Invalid price data in candle: {candle}")
                    continue
            
            if len(prices) < 10:
                logger.warning(f"Insufficient valid price points for {market}: {len(prices)}")
                return None
            
            logger.debug(f"Fetched {len(prices)} price points for {market} over {window_hours}h")
            return prices
            
        except Exception as e:
            logger.error(f"Error fetching historical prices for {market}: {e}")
            return None
    
    def _calculate_price_volatility(self, prices: List[Decimal]) -> Optional[Decimal]:
        """Calculate price volatility from a list of prices."""
        try:
            if len(prices) < 2:
                return None
            
            # Calculate price returns (percentage changes)
            returns = []
            for i in range(1, len(prices)):
                if prices[i-1] > 0:  # Avoid division by zero
                    price_return = (prices[i] - prices[i-1]) / prices[i-1]
                    returns.append(float(price_return))
            
            if len(returns) < 2:
                return None
            
            # Calculate standard deviation of returns
            returns_std = stdev(returns)
            
            # Annualize volatility (convert to percentage)
            # Assuming we have enough data points to represent the full period
            volatility_pct = Decimal(str(returns_std * 100))
            
            # Apply reasonable bounds
            volatility_pct = max(Decimal('0.1'), min(volatility_pct, Decimal('200.0')))
            
            return volatility_pct
            
        except Exception as e:
            logger.error(f"Error calculating price volatility: {e}")
            return None
    
    def clear_cache(self) -> None:
        """Clear the volatility cache."""
        self._volatility_cache.clear()
        logger.info("Volatility cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the volatility cache."""
        current_time = time.time()
        valid_entries = 0
        expired_entries = 0
        
        for cache_data in self._volatility_cache.values():
            cache_age_minutes = (current_time - cache_data['timestamp']) / 60
            if cache_age_minutes < self.cache_duration_minutes:
                valid_entries += 1
            else:
                expired_entries += 1
        
        return {
            'total_entries': len(self._volatility_cache),
            'valid_entries': valid_entries,
            'expired_entries': expired_entries,
            'cache_duration_minutes': self.cache_duration_minutes
        }