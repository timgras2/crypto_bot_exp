#!/usr/bin/env python3
"""
Crypto Trading Bot - Trade Review Script
Displays active and completed trades with profit/loss information.
"""

import json
import argparse
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal

# Set UTF-8 encoding for Windows console
if os.name == 'nt':  # Windows
    os.system('chcp 65001 > nul')

def load_json_file(file_path: Path) -> list:
    """Load JSON data from file, return empty list if file doesn't exist or is invalid."""
    try:
        if file_path.exists():
            data = json.loads(file_path.read_text())
            # Convert dict to list for completed trades (if it's stored as dict)
            if isinstance(data, dict):
                return list(data.values()) if data else []
            return data if isinstance(data, list) else []
        return []
    except Exception as e:
        print(f"⚠️  Warning: Could not load {file_path}: {e}")
        return []

def display_active_trades():
    """Display currently active trades with unrealized P&L."""
    data_dir = Path(__file__).parent / "data"
    active_file = data_dir / "active_trades.json"
    
    print("=" * 80)
    print(">> ACTIVE TRADES (Unrealized P&L)")
    print("=" * 80)
    
    active_data = load_json_file(active_file)
    if isinstance(active_data, dict):
        active_trades = list(active_data.values())
    else:
        active_trades = active_data
    
    if not active_trades:
        print("No active trades")
        return
    
    total_unrealized = 0
    for trade in active_trades:
        try:
            market = trade.get('market', 'Unknown')
            buy_price = Decimal(str(trade.get('buy_price', '0')))
            current_price = Decimal(str(trade.get('current_price', '0')))
            highest_price = Decimal(str(trade.get('highest_price', '0')))
            trailing_stop = Decimal(str(trade.get('trailing_stop_price', '0')))
            
            # Calculate unrealized P&L (assuming €10 trade amount)
            trade_amount = Decimal('10.0')
            quantity = trade_amount / buy_price if buy_price > 0 else Decimal('0')
            unrealized_pnl_eur = (current_price - buy_price) * quantity
            unrealized_pnl_pct = ((current_price - buy_price) / buy_price * 100) if buy_price > 0 else Decimal('0')
            
            total_unrealized += float(unrealized_pnl_eur)
            
            # Calculate duration
            start_time_str = trade.get('start_time', '')
            if start_time_str:
                try:
                    start_time = datetime.fromisoformat(start_time_str)
                    duration = datetime.now() - start_time
                    duration_str = f"{duration.days}d {duration.seconds//3600}h {(duration.seconds//60)%60}m"
                except:
                    duration_str = "Unknown"
            else:
                duration_str = "Unknown"
            
            # Status indicator based on P&L
            status = "UP  " if unrealized_pnl_pct >= 0 else "DOWN"
            
            print(f"{status} {market}")
            print(f"   Buy: €{buy_price:.6f} | Current: €{current_price:.6f} | High: €{highest_price:.6f}")
            print(f"   P&L: €{unrealized_pnl_eur:+.4f} ({unrealized_pnl_pct:+.2f}%) | Stop: €{trailing_stop:.6f}")
            print(f"   Duration: {duration_str}")
            print()
            
        except Exception as e:
            print(f"ERROR processing trade {trade.get('market', 'Unknown')}: {e}")
    
    print(f"Total Unrealized P&L: €{total_unrealized:+.4f}")
    print()

def display_completed_trades(days: int = None):
    """Display completed trades with realized P&L."""
    data_dir = Path(__file__).parent / "data"
    completed_file = data_dir / "completed_trades.json"
    
    print("=" * 80)
    print(f">> COMPLETED TRADES{f' (Last {days} days)' if days else ''}")
    print("=" * 80)
    
    completed_trades = load_json_file(completed_file)
    
    if not completed_trades:
        print("No completed trades")
        return
    
    # Filter by days if specified
    if days:
        cutoff_date = datetime.now() - timedelta(days=days)
        filtered_trades = []
        for trade in completed_trades:
            sell_time_str = trade.get('sell_time', trade.get('last_update', ''))
            if sell_time_str:
                try:
                    sell_time = datetime.fromisoformat(sell_time_str)
                    if sell_time >= cutoff_date:
                        filtered_trades.append(trade)
                except:
                    filtered_trades.append(trade)  # Include if we can't parse date
        completed_trades = filtered_trades
    
    if not completed_trades:
        print(f"No completed trades in the last {days} days")
        return
    
    # Sort by sell time, most recent first
    completed_trades.sort(key=lambda x: x.get('sell_time', x.get('last_update', '')), reverse=True)
    
    total_realized = 0
    winning_trades = 0
    losing_trades = 0
    
    for trade in completed_trades:
        try:
            market = trade.get('market', 'Unknown')
            buy_price = Decimal(str(trade.get('buy_price', '0')))
            sell_price = Decimal(str(trade.get('sell_price', trade.get('current_price', '0'))))
            highest_price = Decimal(str(trade.get('highest_price', '0')))
            
            # Get P&L from stored values or calculate
            if 'profit_loss_pct' in trade:
                pnl_pct = Decimal(str(trade['profit_loss_pct']))
            else:
                pnl_pct = ((sell_price - buy_price) / buy_price * 100) if buy_price > 0 else Decimal('0')
            
            if 'profit_loss_eur' in trade:
                pnl_eur = Decimal(str(trade['profit_loss_eur']))
            else:
                # Estimate EUR P&L (assuming €10 trade)
                pnl_eur = pnl_pct / 100 * Decimal('10.0')
            
            total_realized += float(pnl_eur)
            if pnl_eur >= 0:
                winning_trades += 1
            else:
                losing_trades += 1
            
            # Get timing info
            sell_time_str = trade.get('sell_time', trade.get('last_update', ''))
            duration_str = trade.get('duration_hours', 'Unknown')
            trigger_reason = trade.get('trigger_reason', 'unknown')
            
            # Format sell time
            try:
                if sell_time_str:
                    sell_time = datetime.fromisoformat(sell_time_str)
                    sell_time_formatted = sell_time.strftime('%Y-%m-%d %H:%M')
                else:
                    sell_time_formatted = "Unknown"
            except:
                sell_time_formatted = "Unknown"
            
            # Status and reason indicators
            if pnl_eur >= 0:
                status = "WIN "
                reason_indicator = "PROFIT" if trigger_reason == "trailing_stop" else "STOP" if trigger_reason == "stop_loss" else "MANUAL"
            else:
                status = "LOSS"
                reason_indicator = "STOP"
            
            print(f"{status} {market} | {sell_time_formatted}")
            print(f"   Buy: €{buy_price:.6f} | Sell: €{sell_price:.6f} | High: €{highest_price:.6f}")
            print(f"   P&L: €{pnl_eur:+.4f} ({pnl_pct:+.2f}%) | Duration: {duration_str}h")
            print(f"   Trigger: {trigger_reason.replace('_', ' ').title()} ({reason_indicator})")
            print()
            
        except Exception as e:
            print(f"ERROR processing completed trade {trade.get('market', 'Unknown')}: {e}")
    
    # Summary statistics
    total_trades = winning_trades + losing_trades
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    print(f"SUMMARY: {total_trades} trades | {winning_trades} wins, {losing_trades} losses")
    print(f"Win Rate: {win_rate:.1f}% | Total Realized P&L: €{total_realized:+.4f}")
    print()

def display_summary():
    """Display overall trading performance summary."""
    print("=" * 80)
    print(">> TRADING PERFORMANCE SUMMARY")
    print("=" * 80)
    
    # Get active trades summary
    data_dir = Path(__file__).parent / "data"
    active_file = data_dir / "active_trades.json"
    completed_file = data_dir / "completed_trades.json"
    
    active_data = load_json_file(active_file)
    completed_trades = load_json_file(completed_file)
    
    if isinstance(active_data, dict):
        active_trades = list(active_data.values())
    else:
        active_trades = active_data
    
    # Calculate totals
    total_unrealized = 0
    for trade in active_trades:
        try:
            buy_price = Decimal(str(trade.get('buy_price', '0')))
            current_price = Decimal(str(trade.get('current_price', '0')))
            trade_amount = Decimal('10.0')
            if buy_price > 0:
                quantity = trade_amount / buy_price
                unrealized_pnl = (current_price - buy_price) * quantity
                total_unrealized += float(unrealized_pnl)
        except:
            continue
    
    total_realized = 0
    winning_trades = 0
    losing_trades = 0
    for trade in completed_trades:
        try:
            if 'profit_loss_eur' in trade:
                pnl_eur = Decimal(str(trade['profit_loss_eur']))
            else:
                buy_price = Decimal(str(trade.get('buy_price', '0')))
                sell_price = Decimal(str(trade.get('sell_price', trade.get('current_price', '0'))))
                if buy_price > 0:
                    pnl_pct = (sell_price - buy_price) / buy_price * 100
                    pnl_eur = pnl_pct / 100 * Decimal('10.0')
                else:
                    pnl_eur = Decimal('0')
            
            total_realized += float(pnl_eur)
            if pnl_eur >= 0:
                winning_trades += 1
            else:
                losing_trades += 1
        except:
            continue
    
    total_trades = len(completed_trades)
    active_count = len(active_trades)
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    total_pnl = total_realized + total_unrealized
    
    print(f"Active Positions: {active_count}")
    print(f"Completed Trades: {total_trades} ({winning_trades} wins, {losing_trades} losses)")
    print(f"Win Rate: {win_rate:.1f}%")
    print(f"Realized P&L: €{total_realized:+.4f}")
    print(f"Unrealized P&L: €{total_unrealized:+.4f}")
    print(f"Total P&L: €{total_pnl:+.4f}")
    print()

def main():
    parser = argparse.ArgumentParser(description='Review crypto trading bot performance')
    parser.add_argument('--active', action='store_true', help='Show active trades only')
    parser.add_argument('--completed', action='store_true', help='Show completed trades only')
    parser.add_argument('--days', type=int, help='Show completed trades from last N days')
    parser.add_argument('--summary', action='store_true', help='Show performance summary only')
    
    args = parser.parse_args()
    
    print("\nCrypto Trading Bot - Trade Review")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # If no specific flags, show everything
    if not any([args.active, args.completed, args.summary]):
        display_summary()
        display_active_trades()
        display_completed_trades(args.days)
    else:
        if args.summary:
            display_summary()
        if args.active:
            display_active_trades()
        if args.completed:
            display_completed_trades(args.days)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nReview interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)