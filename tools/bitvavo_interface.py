#!/usr/bin/env python3
"""
Bitvavo Portfolio Tracker - Enhanced version with error handling and features
"""

import os
import logging
from decimal import Decimal, InvalidOperation
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

from python_bitvavo_api.bitvavo import Bitvavo
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class PortfolioItem:
    """Data class for portfolio items"""
    symbol: str
    amount: Decimal
    price_eur: Optional[Decimal]
    value_eur: Optional[Decimal]

class BitvavoPortfolio:
    """Enhanced Bitvavo portfolio tracker with proper error handling"""
    
    def __init__(self):
        self.bitvavo = self._initialize_client()
    
    def _initialize_client(self) -> Bitvavo:
        """Initialize Bitvavo client with proper error handling"""
        load_dotenv()
        
        api_key = os.getenv('BITVAVO_API_KEY')
        api_secret = os.getenv('BITVAVO_API_SECRET')
        
        if not api_key or not api_secret:
            raise ValueError(
                "API credentials not found. Please check your .env file contains "
                "BITVAVO_API_KEY and BITVAVO_API_SECRET"
            )
        
        try:
            return Bitvavo({
                'APIKEY': api_key,
                'APISECRET': api_secret,
                'RESTURL': 'https://api.bitvavo.com/v2',
                'WSURL': 'wss://ws.bitvavo.com/v2/',
                'ACCESSWINDOW': 10000,
                'DEBUGGING': False
            })
        except Exception as e:
            logger.error(f"Failed to initialize Bitvavo client: {e}")
            raise
    
    def _safe_decimal_conversion(self, value: Any) -> Decimal:
        """Safely convert value to Decimal"""
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return Decimal('0')
    
    def _get_eur_price(self, symbol: str) -> Optional[Decimal]:
        """Get EUR price for a given symbol with error handling"""
        try:
            price_data = self.bitvavo.tickerPrice({'market': f'{symbol}-EUR'})
            if 'price' in price_data:
                return self._safe_decimal_conversion(price_data['price'])
        except Exception as e:
            logger.warning(f"Failed to get price for {symbol}: {e}")
        return None
    
    def get_portfolio(self, min_value_eur: Decimal = Decimal('0.01')) -> List[PortfolioItem]:
        """
        Get portfolio with EUR values
        
        Args:
            min_value_eur: Minimum EUR value to include in portfolio
        
        Returns:
            List of PortfolioItem objects
        """
        try:
            balances = self.bitvavo.balance({})
        except Exception as e:
            logger.error(f"Failed to fetch balances: {e}")
            raise
        
        portfolio = []
        
        for asset in balances:
            symbol = asset.get('symbol', '')
            available = self._safe_decimal_conversion(asset.get('available', 0))
            in_order = self._safe_decimal_conversion(asset.get('inOrder', 0))
            total = available + in_order
            
            # Skip empty balances and EUR (base currency)
            if total == 0 or symbol == 'EUR':
                continue
            
            price_eur = self._get_eur_price(symbol)
            value_eur = (price_eur * total) if price_eur else None
            
            # Skip assets below minimum value threshold
            if value_eur and value_eur < min_value_eur:
                continue
            
            portfolio.append(PortfolioItem(
                symbol=symbol,
                amount=total,
                price_eur=price_eur,
                value_eur=value_eur
            ))
        
        # Sort by EUR value (descending), then by symbol
        portfolio.sort(key=lambda x: (x.value_eur or Decimal('0'), x.symbol), reverse=True)
        return portfolio
    
    def get_total_portfolio_value(self) -> Decimal:
        """Calculate total portfolio value in EUR"""
        portfolio = self.get_portfolio()
        total = Decimal('0')
        
        for item in portfolio:
            if item.value_eur:
                total += item.value_eur
        
        return total
    
    def display_portfolio(self, show_totals: bool = True) -> None:
        """Display portfolio in a formatted way"""
        try:
            portfolio = self.get_portfolio()
            
            if not portfolio:
                print("📊 Your portfolio is empty or all assets are below the minimum threshold.")
                return
            
            print("\n📊 Your current portfolio:\n")
            print(f"{'Asset':<8} {'Amount':<15} {'Price (EUR)':<12} {'Value (EUR)':<12}")
            print("-" * 50)
            
            total_value = Decimal('0')
            
            for item in portfolio:
                price_str = f"€{item.price_eur:.4f}" if item.price_eur else "N/A"
                value_str = f"€{item.value_eur:.2f}" if item.value_eur else "N/A"
                
                print(f"{item.symbol:<8} {item.amount:<15.6f} {price_str:<12} {value_str:<12}")
                
                if item.value_eur:
                    total_value += item.value_eur
            
            if show_totals and total_value > 0:
                print("-" * 50)
                print(f"{'TOTAL':<8} {'':<15} {'':<12} €{total_value:.2f}")
                
        except Exception as e:
            logger.error(f"Error displaying portfolio: {e}")
            print(f"❌ Error displaying portfolio: {e}")

def main():
    """Main function"""
    try:
        portfolio_tracker = BitvavoPortfolio()
        portfolio_tracker.display_portfolio()
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        print(f"❌ Configuration error: {e}")
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"❌ An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()