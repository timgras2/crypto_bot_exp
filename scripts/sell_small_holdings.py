#!/usr/bin/env python3
"""
Small Holdings Cleanup Script

This script sells all cryptocurrency holdings worth less than 5 EUR.
It provides safety checks, confirmation prompts, and detailed reporting.

Usage:
    python sell_small_holdings.py [--dry-run]

Options:
    --dry-run    Show what would be sold without executing trades
"""

import sys
import logging
import time
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# Add src directory to path for imports
src_path = Path(__file__).parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from config import load_config, APIConfig, TradingConfig
from requests_handler import BitvavoAPI


class SmallHoldingsCleanup:
    def __init__(self, api: BitvavoAPI, threshold_eur: float = 5.0):
        self.api = api
        self.threshold_eur = Decimal(str(threshold_eur))
        
    def get_all_balances(self) -> List[Dict]:
        """Fetch all account balances from Bitvavo."""
        try:
            balance_response = self.api.send_request("GET", "/balance")
            
            if not balance_response or not isinstance(balance_response, list):
                logging.error("Failed to get account balance or invalid response format")
                return []
            
            # Filter out zero balances and EUR (base currency)
            non_zero_balances = []
            for balance_item in balance_response:
                if isinstance(balance_item, dict):
                    symbol = balance_item.get('symbol', '')
                    available = float(balance_item.get('available', '0'))
                    in_order = float(balance_item.get('inOrder', '0'))
                    total = available + in_order
                    
                    # Skip EUR (base currency) and zero balances
                    if symbol != 'EUR' and total > 0:
                        non_zero_balances.append(balance_item)
            
            logging.info(f"Found {len(non_zero_balances)} non-EUR holdings with balance > 0")
            return non_zero_balances
            
        except Exception as e:
            logging.error(f"Error fetching balances: {e}")
            return []
    
    def get_market_price(self, symbol: str) -> Optional[Decimal]:
        """Get current EUR price for a cryptocurrency symbol."""
        try:
            market = f"{symbol}-EUR"
            ticker_response = self.api.send_request("GET", f"/ticker/price?market={market}")
            
            if not ticker_response:
                logging.warning(f"No ticker data available for {market}")
                return None
                
            price_str = ticker_response.get('price', '0')
            if not price_str or price_str == '0':
                logging.warning(f"Invalid or zero price for {market}: {price_str}")
                return None
                
            return Decimal(str(price_str))
            
        except Exception as e:
            logging.warning(f"Error getting price for {symbol}: {e}")
            return None
    
    def calculate_eur_values(self, balances: List[Dict]) -> List[Tuple[Dict, Decimal, Decimal]]:
        """Calculate EUR values for all holdings."""
        valued_holdings = []
        
        for balance_item in balances:
            symbol = balance_item.get('symbol', '')
            available = Decimal(balance_item.get('available', '0'))
            in_order = Decimal(balance_item.get('inOrder', '0'))
            total_amount = available + in_order
            
            print(f"📊 Getting price for {symbol}...")
            
            # Get current market price
            price = self.get_market_price(symbol)
            if price is None:
                print(f"⚠️  Could not get price for {symbol}, skipping")
                logging.warning(f"Skipping {symbol} due to missing price data")
                continue
            
            # Calculate EUR value
            eur_value = total_amount * price
            valued_holdings.append((balance_item, price, eur_value))
            
            print(f"   {symbol}: {total_amount} × €{price} = €{eur_value:.2f}")
        
        return valued_holdings
    
    def identify_small_holdings(self, valued_holdings: List[Tuple[Dict, Decimal, Decimal]]) -> List[Tuple[Dict, Decimal, Decimal]]:
        """Filter holdings worth less than threshold."""
        small_holdings = []
        
        for balance_item, price, eur_value in valued_holdings:
            if eur_value < self.threshold_eur:
                small_holdings.append((balance_item, price, eur_value))
        
        return small_holdings
    
    def display_summary(self, small_holdings: List[Tuple[Dict, Decimal, Decimal]], dry_run: bool = False) -> None:
        """Display summary of holdings to be sold."""
        if not small_holdings:
            print("✅ No small holdings found under €{:.2f}".format(float(self.threshold_eur)))
            return
        
        action_word = "would sell" if dry_run else "will sell"
        print(f"\n🧹 Small Holdings Cleanup - {action_word}:")
        print("=" * 60)
        
        total_eur_value = Decimal('0')
        for balance_item, price, eur_value in small_holdings:
            symbol = balance_item.get('symbol', '')
            available = balance_item.get('available', '0')
            in_order = balance_item.get('inOrder', '0')
            
            print(f"{symbol:>8} | Available: {available:>12} | In Order: {in_order:>12} | Value: €{eur_value:.2f}")
            total_eur_value += eur_value
        
        print("=" * 60)
        print(f"Total EUR Value: €{total_eur_value:.2f}")
        print(f"Holdings Count: {len(small_holdings)}")
    
    def confirm_action(self) -> bool:
        """Ask user for confirmation before proceeding."""
        print("\n⚠️  WARNING: This will execute REAL sell orders!")
        print("📈 Make sure you understand the tax implications of selling these positions.")
        print("🔄 This action cannot be undone.")
        
        while True:
            response = input("\nDo you want to proceed? (yes/no): ").strip().lower()
            if response in ['yes', 'y']:
                return True
            elif response in ['no', 'n']:
                return False
            else:
                print("Please enter 'yes' or 'no'")
    
    def sell_holdings(self, small_holdings: List[Tuple[Dict, Decimal, Decimal]]) -> Dict:
        """Execute sell orders for small holdings."""
        results = {
            'success': [],
            'failed': [],
            'skipped': []
        }
        
        print(f"\n🚀 Starting to sell {len(small_holdings)} small holdings...")
        
        for i, (balance_item, price, eur_value) in enumerate(small_holdings, 1):
            symbol = balance_item.get('symbol', '')
            available = balance_item.get('available', '0')
            in_order = balance_item.get('inOrder', '0')
            
            print(f"\n[{i}/{len(small_holdings)}] Processing {symbol}...")
            
            # Skip if no available balance (tied up in orders)
            if float(available) <= 0:
                if float(in_order) > 0:
                    print(f"⏭️  Skipping {symbol}: Tied up in pending orders ({in_order} in order)")
                    results['skipped'].append({'symbol': symbol, 'reason': 'in_order', 'amount': in_order})
                else:
                    print(f"⏭️  Skipping {symbol}: No available balance")
                    results['skipped'].append({'symbol': symbol, 'reason': 'no_balance', 'amount': '0'})
                continue
            
            # Execute sell order
            success = self.execute_sell_order(symbol, available)
            
            if success:
                print(f"✅ Sold {available} {symbol} (€{eur_value:.2f})")
                results['success'].append({
                    'symbol': symbol,
                    'amount': available,
                    'eur_value': float(eur_value)
                })
            else:
                print(f"❌ Failed to sell {symbol}")
                results['failed'].append({
                    'symbol': symbol,
                    'amount': available,
                    'eur_value': float(eur_value)
                })
            
            # Brief pause between orders to be gentle on API
            time.sleep(1)
        
        return results
    
    def get_market_info(self, symbol: str) -> Optional[Dict]:
        """Get market information to determine decimal precision."""
        try:
            target_market = f"{symbol}-EUR"
            response = self.api.send_request("GET", "/markets")
            
            if response and isinstance(response, list):
                # Find the specific market in the response
                for market_data in response:
                    if isinstance(market_data, dict) and market_data.get('market') == target_market:
                        logging.info(f"Found market data for {target_market}: {market_data}")
                        return market_data
            
            logging.warning(f"No market info found for {target_market}")
            return None
            
        except Exception as e:
            logging.warning(f"Error getting market info for {symbol}: {e}")
            return None
    
    def format_amount_for_market(self, symbol: str, amount: str) -> str:
        """Format amount according to market's decimal precision requirements."""
        try:
            # Get market information
            market_info = self.get_market_info(symbol)
            
            if market_info:
                # Extract quantity precision from market info - this is the key field!
                quantity_decimals = market_info.get('quantityDecimals', 8)
                logging.info(f"Market {symbol}-EUR requires {quantity_decimals} decimal places for quantity")
                
                # Format to required precision - round DOWN to avoid "insufficient balance" errors
                amount_decimal = Decimal(amount)
                precision_str = f"1E-{quantity_decimals}"
                formatted_amount = amount_decimal.quantize(Decimal(precision_str), rounding='ROUND_DOWN')
                
                # Check if we're losing a significant amount due to rounding
                lost_amount = amount_decimal - formatted_amount
                if lost_amount > Decimal('0'):
                    lost_percentage = (lost_amount / amount_decimal) * 100
                    logging.info(f"Rounding {symbol}: {amount} -> {formatted_amount} (lost: {lost_amount}, {lost_percentage:.6f}%)")
                    
                    # If we're losing more than 0.1% due to rounding, warn the user
                    if lost_percentage > Decimal('0.1'):
                        print(f"   ⚠️  Rounding will leave {lost_amount} {symbol} unsold ({lost_percentage:.3f}%)")
                else:
                    logging.info(f"Formatted amount for {symbol}: {amount} -> {formatted_amount}")
                
                return str(formatted_amount)
            else:
                # Fallback: try common precisions with ROUND_DOWN
                logging.warning(f"No market info for {symbol}, trying 8 decimal places")
                amount_decimal = Decimal(amount)
                formatted_amount = amount_decimal.quantize(Decimal('1E-8'), rounding='ROUND_DOWN')
                return str(formatted_amount)
                
        except Exception as e:
            logging.warning(f"Error formatting amount for {symbol}: {e}, using original")
            return amount
    
    def execute_sell_order(self, symbol: str, amount: str) -> bool:
        """Execute a single sell order."""
        try:
            market = f"{symbol}-EUR"
            
            # Format amount according to market precision requirements
            formatted_amount = self.format_amount_for_market(symbol, amount)
            
            # Use the same sell logic as the main bot
            body = {
                'market': market,
                'side': 'sell',
                'orderType': 'market',
                'amount': formatted_amount,
                'operatorId': 1001  # Default operator ID
            }
            
            logging.info(f"Selling {formatted_amount} {symbol} on {market} (original: {amount})")
            
            # Try with retries (simplified - just 2 attempts)
            for attempt in range(2):
                response = self.api.send_request("POST", "/order", body)
                if response:
                    logging.info(f"Market sell placed for {market}: {response.get('orderId', 'N/A')}")
                    return True
                
                if attempt < 1:  # Only retry once
                    time.sleep(2)
            
            return False
            
        except Exception as e:
            logging.error(f"Error executing sell order for {symbol}: {e}")
            return False
    
    def print_final_summary(self, results: Dict) -> None:
        """Print final summary of operations."""
        print("\n" + "=" * 60)
        print("🏁 FINAL SUMMARY")
        print("=" * 60)
        
        success_count = len(results['success'])
        failed_count = len(results['failed'])
        skipped_count = len(results['skipped'])
        
        if success_count > 0:
            print(f"✅ Successfully sold {success_count} positions:")
            total_eur = sum(item['eur_value'] for item in results['success'])
            for item in results['success']:
                print(f"   {item['symbol']}: {item['amount']} (€{item['eur_value']:.2f})")
            print(f"   Total EUR from sales: €{total_eur:.2f}")
        
        if failed_count > 0:
            print(f"\n❌ Failed to sell {failed_count} positions:")
            for item in results['failed']:
                print(f"   {item['symbol']}: {item['amount']} (€{item['eur_value']:.2f})")
        
        if skipped_count > 0:
            print(f"\n⏭️  Skipped {skipped_count} positions:")
            for item in results['skipped']:
                reason = "in pending orders" if item['reason'] == 'in_order' else "no available balance"
                print(f"   {item['symbol']}: {reason}")
        
        print("=" * 60)


def main():
    """Main entry point for the script."""
    # Setup logging
    logs_dir = Path(__file__).parent / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(logs_dir / 'small_holdings_cleanup.log'),
            logging.StreamHandler()
        ]
    )
    
    # Check for dry-run flag
    dry_run = '--dry-run' in sys.argv
    
    print("🧹 Small Holdings Cleanup Script")
    print("=" * 40)
    
    if dry_run:
        print("🔍 DRY RUN MODE - No trades will be executed")
    else:
        print("⚠️  LIVE MODE - Real trades will be executed!")
    
    print()
    
    try:
        # Load configuration
        print("📊 Loading configuration...")
        trading_config, api_config = load_config()
        
        # Initialize API
        print("🔌 Connecting to Bitvavo API...")
        api = BitvavoAPI(api_config)
        
        # Initialize cleanup handler
        cleanup = SmallHoldingsCleanup(api, threshold_eur=5.0)
        
        # Get all balances
        print("💰 Fetching account balances...")
        balances = cleanup.get_all_balances()
        
        if not balances:
            print("ℹ️  No cryptocurrency holdings found")
            return
        
        print(f"📈 Found {len(balances)} cryptocurrency holdings")
        
        # Calculate EUR values
        print("\n💱 Calculating EUR values...")
        valued_holdings = cleanup.calculate_eur_values(balances)
        
        # Identify small holdings
        small_holdings = cleanup.identify_small_holdings(valued_holdings)
        
        # Display summary
        cleanup.display_summary(small_holdings, dry_run)
        
        if not small_holdings:
            return
        
        # If dry run, exit here
        if dry_run:
            print("\n🔍 Dry run complete - no trades executed")
            return
        
        # Get confirmation
        if not cleanup.confirm_action():
            print("❌ Operation cancelled by user")
            return
        
        # Execute sells
        results = cleanup.sell_holdings(small_holdings)
        
        # Print final summary
        cleanup.print_final_summary(results)
        
    except KeyboardInterrupt:
        print("\n🛑 Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Script failed: {e}")
        logging.exception("Script execution failed")
        sys.exit(1)


if __name__ == '__main__':
    main()