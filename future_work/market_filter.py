#!/usr/bin/env python3
"""
Market Filter - Optional market condition checking for dip buying
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)


class MarketFilter:
    """
    Optional market condition filter for dip buying decisions.
    
    This is a simple implementation that can be extended with more
    sophisticated market analysis in the future.
    """
    
    def __init__(self, api_client):
        self.api = api_client
        self._btc_price_cache = {}
        self._cache_duration = timedelta(minutes=5)  # Cache BTC price for 5 minutes
    
    def should_allow_rebuy(self) -> Tuple[bool, str]:
        """
        Check if market conditions allow for rebuy operations.
        
        Returns:
            (should_allow, reason) tuple
        """
        try:
            # Check BTC trend as a proxy for overall market sentiment
            btc_trend_ok, trend_reason = self._check_btc_trend()
            if not btc_trend_ok:
                return False, f"BTC trend filter: {trend_reason}"
            
            # Additional market checks could be added here:
            # - Market volatility index
            # - Major news events
            # - Exchange-specific issues
            
            return True, "Market conditions acceptable"
            
        except Exception as e:
            logger.error(f"Error checking market conditions: {e}")
            # Fail open - allow rebuys if we can't check conditions
            return True, "Market filter unavailable - allowing rebuy"
    
    def _check_btc_trend(self) -> Tuple[bool, str]:
        """
        Check Bitcoin trend as a general market indicator.
        
        Logic: If BTC has dropped >15% in the last 24 hours, 
        it might indicate a broader market crash, so pause rebuys.
        """
        try:
            current_btc_price = self._get_btc_price()
            if current_btc_price is None:
                return True, "BTC price unavailable"
            
            # Get BTC price from 24 hours ago (approximate)
            btc_24h_ago = self._get_btc_price_24h_ago()
            if btc_24h_ago is None:
                return True, "BTC 24h price unavailable"
            
            # Calculate 24h change
            btc_change_pct = ((current_btc_price - btc_24h_ago) / btc_24h_ago) * 100
            
            logger.debug(f"BTC 24h change: {btc_change_pct:.2f}% "
                        f"(€{current_btc_price} vs €{btc_24h_ago})")
            
            # If BTC dropped more than 15%, consider market conditions risky
            if btc_change_pct <= -15:
                return False, f"BTC down {btc_change_pct:.1f}% in 24h (threshold: -15%)"
            
            return True, f"BTC 24h change acceptable ({btc_change_pct:+.1f}%)"
            
        except Exception as e:
            logger.warning(f"Error checking BTC trend: {e}")
            return True, "BTC trend check failed - allowing rebuy"
    
    def _get_btc_price(self) -> Optional[Decimal]:
        """Get current BTC-EUR price with caching."""
        now = datetime.now()
        
        # Check cache
        if 'price' in self._btc_price_cache and 'timestamp' in self._btc_price_cache:
            cache_age = now - self._btc_price_cache['timestamp']
            if cache_age < self._cache_duration:
                return self._btc_price_cache['price']
        
        # Fetch fresh price
        try:
            response = self.api.send_request("GET", "/ticker/price?market=BTC-EUR")
            if response and 'price' in response:
                price = Decimal(str(response['price']))
                
                # Update cache
                self._btc_price_cache = {
                    'price': price,
                    'timestamp': now
                }
                
                return price
                
        except Exception as e:
            logger.warning(f"Failed to fetch BTC price: {e}")
        
        return None
    
    def _get_btc_price_24h_ago(self) -> Optional[Decimal]:
        """
        Get BTC price from ~24 hours ago.
        
        Note: This is a simplified implementation. In a production system,
        you might want to use historical price APIs or maintain your own
        price history database.
        """
        try:
            # For simplicity, we'll use the 24h ticker data if available
            response = self.api.send_request("GET", "/ticker/24hr?market=BTC-EUR")
            
            if response:
                # Try to calculate from current price and 24h change
                current_price = response.get('lastPrice')
                price_change_24h = response.get('priceChange')
                
                if current_price and price_change_24h:
                    current = Decimal(str(current_price))
                    change = Decimal(str(price_change_24h))
                    price_24h_ago = current - change
                    return price_24h_ago
                
                # Alternative: use open price if available
                open_price = response.get('openPrice')
                if open_price:
                    return Decimal(str(open_price))
            
        except Exception as e:
            logger.warning(f"Failed to calculate BTC 24h ago price: {e}")
        
        # Fallback: estimate based on current price (assume no major crash)
        current_price = self._get_btc_price()
        if current_price:
            # Assume roughly stable price as fallback
            return current_price * Decimal('1.0')
        
        return None
    
    def get_market_summary(self) -> Dict[str, Any]:
        """Get a summary of current market conditions."""
        btc_price = self._get_btc_price()
        btc_24h_ago = self._get_btc_price_24h_ago()
        
        btc_change_pct = None
        if btc_price and btc_24h_ago:
            btc_change_pct = float(((btc_price - btc_24h_ago) / btc_24h_ago) * 100)
        
        should_allow, reason = self.should_allow_rebuy()
        
        return {
            'btc_price_eur': float(btc_price) if btc_price else None,
            'btc_24h_change_pct': btc_change_pct,
            'rebuy_allowed': should_allow,
            'filter_reason': reason,
            'timestamp': datetime.now().isoformat()
        }