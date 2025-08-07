import json
import logging
import threading
import time
from decimal import Decimal, InvalidOperation
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional, Dict
from pathlib import Path
from config import TradingConfig
from requests_handler import BitvavoAPI

@dataclass
class TradeState:
    """Current state of a trade."""
    market: str
    buy_price: Decimal
    current_price: Decimal
    highest_price: Decimal
    trailing_stop_price: Decimal
    stop_loss_price: Decimal
    start_time: datetime
    last_update: datetime

class TradeManager:
    def __init__(self, api: BitvavoAPI, config: TradingConfig):
        self.api = api
        self.config = config
        self.active_trades: Dict[str, TradeState] = {}
        self._stop_events: Dict[str, threading.Event] = {}
        self._threads: Dict[str, threading.Thread] = {}
        self._lock = threading.Lock()
        # Use absolute path relative to the script location
        project_root = Path(__file__).parent.parent
        self.persistence_file = project_root / "data" / "active_trades.json"
        self.completed_trades_file = project_root / "data" / "completed_trades.json"
        
        # Ensure data directory exists
        self.persistence_file.parent.mkdir(parents=True, exist_ok=True)
        logging.info(f"TradeManager persistence file: {self.persistence_file}")
        logging.info(f"TradeManager completed trades file: {self.completed_trades_file}")
        
        # Flag to prevent file deletion during shutdown
        self._shutting_down = False

    def record_completed_trade(self, market: str, sell_price: Decimal, trigger_reason: str) -> None:
        """Record a completed trade to the completed trades file."""
        try:
            if market not in self.active_trades:
                logging.warning(f"Cannot record completed trade for {market} - not in active trades")
                return
            
            trade = self.active_trades[market]
            
            # Calculate profit/loss
            profit_pct = ((sell_price - trade.buy_price) / trade.buy_price) * 100
            profit_eur = profit_pct / 100 * 10.0  # Approximate EUR profit based on typical €10 trade
            
            # Create completed trade record (same format as active trades + completion info)
            completed_trade = {
                "market": market,
                "buy_price": str(trade.buy_price),
                "sell_price": str(sell_price),
                "current_price": str(sell_price),  # Final price is sell price
                "highest_price": str(trade.highest_price),
                "trailing_stop_price": str(trade.trailing_stop_price),
                "stop_loss_price": str(trade.stop_loss_price),
                "start_time": trade.start_time.isoformat(),
                "sell_time": datetime.now().isoformat(),
                "last_update": datetime.now().isoformat(),
                "profit_loss_pct": f"{profit_pct:.2f}",
                "profit_loss_eur": f"{profit_eur:.4f}",
                "trigger_reason": trigger_reason,
                "duration_hours": f"{(datetime.now() - trade.start_time).total_seconds() / 3600:.1f}"
            }
            
            # Load existing completed trades
            completed_trades = []
            if self.completed_trades_file.exists():
                try:
                    completed_trades = json.loads(self.completed_trades_file.read_text())
                except Exception as e:
                    logging.error(f"Error loading completed trades: {e}")
                    completed_trades = []
            
            # Add new completed trade
            completed_trades.append(completed_trade)
            
            # Save updated completed trades
            self.completed_trades_file.write_text(json.dumps(completed_trades, indent=2))
            logging.info(f"Recorded completed trade for {market}: {profit_pct:+.2f}% profit/loss")
            
        except Exception as e:
            logging.error(f"Failed to record completed trade for {market}: {e}")

    def prepare_for_shutdown(self) -> None:
        """Set shutdown mode to preserve persistence file."""
        self._shutting_down = True
        logging.info("TradeManager set to shutdown mode - will preserve persistence file")

    def save_active_trades(self) -> None:
        """Save active trades to disk for recovery after restart."""
        try:
            logging.info(f"save_active_trades called with {len(self.active_trades)} active trades")
            logging.info(f"Current active trades: {list(self.active_trades.keys())}")
            
            # Use timeout to prevent deadlock during shutdown
            lock_acquired = self._lock.acquire(timeout=5.0)
            if not lock_acquired:
                logging.error("Failed to acquire lock for save_active_trades within 5 seconds - possible deadlock")
                print("⚠️  Warning: Could not save active trades due to lock timeout")
                return
            
            try:
                if not self.active_trades:
                    # During shutdown, preserve the file even if no active trades
                    if self._shutting_down:
                        logging.info("Shutdown mode: Preserving persistence file even with no active trades")
                        return
                    
                    # If no active trades, remove the file (normal operation)
                    if self.persistence_file.exists():
                        self.persistence_file.unlink()
                        logging.info(f"No active trades to save, removed persistence file: {self.persistence_file}")
                        print(f"🗑️  Removed empty persistence file")
                    else:
                        logging.info(f"No active trades and no persistence file to remove")
                    return
                
                # Convert TradeState objects to serializable format
                serializable_trades = {}
                for market, trade_state in self.active_trades.items():
                    trade_dict = asdict(trade_state)
                    # Convert Decimal and datetime to strings for JSON serialization
                    trade_dict['buy_price'] = str(trade_dict['buy_price'])
                    trade_dict['current_price'] = str(trade_dict['current_price'])
                    trade_dict['highest_price'] = str(trade_dict['highest_price'])
                    trade_dict['trailing_stop_price'] = str(trade_dict['trailing_stop_price'])
                    trade_dict['stop_loss_price'] = str(trade_dict['stop_loss_price'])
                    trade_dict['start_time'] = trade_dict['start_time'].isoformat()
                    trade_dict['last_update'] = trade_dict['last_update'].isoformat()
                    serializable_trades[market] = trade_dict
                
                # Save to file
                self.persistence_file.write_text(json.dumps(serializable_trades, indent=2))
                logging.info(f"Saved {len(serializable_trades)} active trades to {self.persistence_file}")
                print(f"💾 Saved {len(serializable_trades)} active trades for recovery")
                
            finally:
                # Always release the lock
                self._lock.release()
                logging.debug("Released lock in save_active_trades")
                
        except Exception as e:
            logging.error(f"Failed to save active trades: {e}")

    def load_active_trades(self) -> Dict[str, TradeState]:
        """Load previously saved active trades from disk."""
        try:
            logging.debug(f"Attempting to load active trades from: {self.persistence_file}")
            if not self.persistence_file.exists():
                logging.info(f"No active trades file found at {self.persistence_file} - starting fresh")
                return {}
            
            trade_data = json.loads(self.persistence_file.read_text())
            restored_trades = {}
            
            for market, trade_dict in trade_data.items():
                # Convert strings back to proper types
                trade_state = TradeState(
                    market=trade_dict['market'],
                    buy_price=Decimal(trade_dict['buy_price']),
                    current_price=Decimal(trade_dict['current_price']),
                    highest_price=Decimal(trade_dict['highest_price']),
                    trailing_stop_price=Decimal(trade_dict['trailing_stop_price']),
                    stop_loss_price=Decimal(trade_dict['stop_loss_price']),
                    start_time=datetime.fromisoformat(trade_dict['start_time']),
                    last_update=datetime.fromisoformat(trade_dict['last_update'])
                )
                restored_trades[market] = trade_state
            
            logging.info(f"Loaded {len(restored_trades)} active trades from {self.persistence_file}")
            print(f"🔄 Loaded {len(restored_trades)} trades from previous session")
            
            return restored_trades
            
        except Exception as e:
            logging.error(f"Failed to load active trades: {e}")
            # Move corrupted file out of the way
            if self.persistence_file.exists():
                backup_path = self.persistence_file.with_suffix('.json.backup')
                self.persistence_file.rename(backup_path)
                logging.warning(f"Moved corrupted active trades file to {backup_path}")
            return {}

    def restore_monitoring(self) -> None:
        """Restore monitoring for previously active trades loaded from disk."""
        logging.info("restore_monitoring called - checking for active trades to restore")
        restored_trades = self.load_active_trades()
        
        if not restored_trades:
            return
        
        print(f"🔄 Restoring monitoring for {len(restored_trades)} trades...")
        
        successfully_restored = 0
        for market, trade_state in restored_trades.items():
            try:
                # Verify the position still exists by checking current balance
                symbol = market.split('-')[0]  # Extract base currency (e.g., 'PUMP' from 'PUMP-EUR')
                balance_response = self.api.send_request("GET", "/balance")
                
                # Debug log the balance response structure
                logging.debug(f"Account balance API response (searching for {symbol}): {balance_response}")
                logging.debug(f"Response type: {type(balance_response)}")
                
                # Handle different response formats from Bitvavo balance API
                balance_found = False
                if balance_response:
                    if isinstance(balance_response, list):
                        # Response is a list of balance objects
                        for balance_item in balance_response:
                            if isinstance(balance_item, dict) and balance_item.get('symbol') == symbol:
                                available = float(balance_item.get('available', '0'))
                                in_order = float(balance_item.get('inOrder', '0'))
                                total_balance = available + in_order
                                if total_balance > 0:
                                    balance_found = True
                                    logging.debug(f"Found {symbol} balance: {available} available, {in_order} in order")
                                break
                    elif isinstance(balance_response, dict) and balance_response.get('symbol') == symbol:
                        # Response is a single balance object
                        available = float(balance_response.get('available', '0'))
                        in_order = float(balance_response.get('inOrder', '0'))
                        total_balance = available + in_order
                        if total_balance > 0:
                            balance_found = True
                            logging.debug(f"Found {symbol} balance: {available} available, {in_order} in order")
                    else:
                        logging.warning(f"Unexpected balance response format for {symbol}: {type(balance_response)}")
                
                if not balance_found:
                    print(f"⚠️  Skipping {market}: Position no longer exists on exchange")
                    logging.warning(f"Position {market} not found on exchange during restoration")
                    continue
                
                # Restore the trade state
                with self._lock:
                    self.active_trades[market] = trade_state
                
                # Start monitoring thread
                stop_event = threading.Event()
                self._stop_events[market] = stop_event
                
                thread = threading.Thread(
                    target=self._monitor_trade,
                    args=(market, stop_event),
                    daemon=True
                )
                self._threads[market] = thread
                thread.start()
                
                # Calculate profit/loss for display
                profit_pct = ((trade_state.current_price - trade_state.buy_price) / trade_state.buy_price) * 100
                elapsed = datetime.now() - trade_state.start_time
                
                print(f"✅ Restored {market}: Buy €{trade_state.buy_price} | Current €{trade_state.current_price} | "
                      f"P&L: {profit_pct:+.1f}% | Running: {str(elapsed).split('.')[0]}")
                
                logging.info(f"Restored monitoring for {market} - Buy: {trade_state.buy_price}, "
                           f"Current: {trade_state.current_price}, Elapsed: {elapsed}")
                
                successfully_restored += 1
                
            except Exception as e:
                logging.error(f"Failed to restore monitoring for {market}: {e}")
                print(f"❌ Failed to restore {market}: {e}")
        
        if successfully_restored > 0:
            print(f"🎯 {successfully_restored} trades successfully restored and being monitored with trailing stop-loss")
        else:
            print("ℹ️  No trades were restored (all positions may have been closed)")
            
        
        # Save current state (with only successfully restored trades)
        if successfully_restored > 0:
            logging.info(f"Saving {successfully_restored} successfully restored trades to persistence")
            self.save_active_trades()

    def place_market_buy(self, market: str, quote_amount: Decimal) -> Optional[Decimal]:
        try:
            # Input validation
            if not market or not isinstance(market, str):
                logging.error("Invalid market name provided")
                return None
            
            # Validate market format (e.g., BTC-EUR)
            if not market.replace('-', '').replace('_', '').isalnum() or len(market) < 5:
                logging.error(f"Invalid market format: {market}")
                return None
                
            if quote_amount <= 0:
                logging.error(f"Trade amount must be positive, got: {quote_amount}")
                return None
                
            if quote_amount > self.config.max_trade_amount:
                logging.warning(f"Trade amount {quote_amount} exceeds maximum {self.config.max_trade_amount}")
                return None

            body = {
                'market': market,
                'side': 'buy',
                'orderType': 'market',
                'amountQuote': str(quote_amount),
                'operatorId': self.config.operator_id  # Required by Bitvavo API as of June 2025
            }

            for attempt in range(self.config.max_retries):
                response = self.api.send_request("POST", "/order", body)
                if response:
                    # Log the full response for debugging
                    logging.debug(f"Order response for {market}: {response}")
                    # Try multiple fields that could contain the execution price
                    price_str = (response.get('price') or 
                                response.get('executedPrice') or 
                                response.get('avgPrice') or 
                                response.get('fillPrice') or '0')
                    
                    price = Decimal(str(price_str))
                    
                    # If price is still 0, but we have a successful response, 
                    # the order was likely executed - fetch current market price as fallback
                    if price == 0 and response.get('orderId'):
                        logging.warning(f"Order placed for {market} but no execution price in response. Using market price as fallback.")
                        # Try to get current market price
                        ticker_response = self.api.send_request("GET", f"/ticker/price?market={market}")
                        if ticker_response and ticker_response.get('price'):
                            price = Decimal(str(ticker_response.get('price')))
                            logging.info(f"Using market price {price} for {market} order")
                        else:
                            logging.warning(f"Could not fetch market price for {market}, using order was likely successful despite missing price")
                            # Return a non-zero price to indicate success, even if we don't have exact price
                            price = Decimal('0.001')  # Placeholder to indicate success
                    
                    logging.info(f"Market buy placed for {market} at {price} (Order ID: {response.get('orderId', 'N/A')})")
                    return price
                
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay)
            
            return None

        except Exception as e:
            logging.error(f"Error placing market buy for {market}: {str(e)}")
            return None

    def sell_market(self, market: str) -> bool:
        try:
            # Input validation
            if not market or not isinstance(market, str):
                logging.error("Invalid market name provided for sell")
                return False
            
            if not market.replace('-', '').replace('_', '').isalnum() or len(market) < 5:
                logging.error(f"Invalid market format for sell: {market}")
                return False
            
            # Get actual balance to sell (Bitvavo doesn't accept '100%')
            symbol = market.split('-')[0]  # Extract base currency (e.g., 'PEPE' from 'PEPE-EUR')
            balance_response = self.api.send_request("GET", "/balance")
            
            # Debug log the complete balance response
            logging.info(f"=== BALANCE API RESPONSE (searching for {symbol}) ===")
            logging.info(f"Response: {balance_response}")
            logging.info(f"Response type: {type(balance_response)}")
            
            if not balance_response or not isinstance(balance_response, list):
                logging.error(f"Failed to get account balance before selling {symbol}")
                return False
            
            # Find the balance for our symbol and check all amounts
            available_amount = None
            in_order_amount = None
            total_amount = None
            
            for balance_item in balance_response:
                if isinstance(balance_item, dict) and balance_item.get('symbol') == symbol:
                    available_amount = balance_item.get('available', '0')
                    in_order_amount = balance_item.get('inOrder', '0')
                    total_amount = float(available_amount) + float(in_order_amount)
                    
                    logging.info(f"Found {symbol} balance details:")
                    logging.info(f"  Available: {available_amount}")
                    logging.info(f"  In Order: {in_order_amount}")
                    logging.info(f"  Total: {total_amount}")
                    break
            
            if not available_amount:
                logging.error(f"Symbol {symbol} not found in balance response")
                return False
            
            # Use available amount, but warn if it's zero while in_order has value
            sellable_amount = float(available_amount)
            if sellable_amount <= 0:
                if float(in_order_amount) > 0:
                    logging.warning(f"{symbol} has {in_order_amount} in open orders but 0 available - position may be tied up in pending orders")
                    print(f"⚠️  {symbol} position tied up in pending orders - cannot sell now")
                else:
                    logging.warning(f"{symbol} position appears to have been sold already (0 available, 0 in order)")
                    print(f"ℹ️  {symbol} position already sold elsewhere - stopping monitoring")
                    
                    # Clean up monitoring for this non-existent position
                    with self._lock:
                        if market in self.active_trades:
                            self.active_trades.pop(market, None)
                            print(f"🧹 Removed {market} from active monitoring (position no longer exists)")
                            logging.info(f"Cleaned up monitoring for sold position: {market}")
                
                logging.error(f"No sellable balance found for {symbol} to sell (available: {available_amount})")
                return False
            
            body = {
                'market': market,
                'side': 'sell',
                'orderType': 'market',
                'amount': str(available_amount),  # Use actual available amount
                'operatorId': self.config.operator_id  # Required by Bitvavo API as of June 2025
            }
            
            logging.info(f"Selling {available_amount} {symbol} on {market}")

            for attempt in range(self.config.max_retries):
                response = self.api.send_request("POST", "/order", body)
                if response:
                    logging.info(f"Market sell placed for {market}")
                    return True
                
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay)
            
            return False

        except Exception as e:
            logging.error(f"Error placing market sell for {market}: {str(e)}")
            return False

    def start_monitoring(self, market: str, buy_price: Decimal) -> None:
        # Input validation
        if not market or not isinstance(market, str):
            logging.error("Invalid market name provided for monitoring")
            return
        
        if not market.replace('-', '').replace('_', '').isalnum() or len(market) < 5:
            logging.error(f"Invalid market format for monitoring: {market}")
            return
            
        if buy_price <= 0:
            logging.error(f"Buy price must be positive, got: {buy_price}")
            return
            
        with self._lock:
            if market in self.active_trades:
                logging.warning(f"Already monitoring {market}")
                return

        logging.info(f"Starting monitoring for {market}")
        stop_event = threading.Event()
        self._stop_events[market] = stop_event

        trade_state = TradeState(
            market=market,
            buy_price=buy_price,
            current_price=buy_price,
            highest_price=buy_price,
            trailing_stop_price=buy_price * (Decimal('1') - self.config.trailing_pct / Decimal('100')),
            stop_loss_price=buy_price * (Decimal('1') - self.config.min_profit_pct / Decimal('100')),
            start_time=datetime.now(),
            last_update=datetime.now()
        )

        with self._lock:
            self.active_trades[market] = trade_state

        thread = threading.Thread(
            target=self._monitor_trade,
            args=(market, stop_event),
            daemon=True
        )
        self._threads[market] = thread
        thread.start()
        logging.info(f"Monitoring thread started for {market}")

    def stop_monitoring(self, market: str) -> None:
        logging.info(f"Stopping monitoring for {market}")
        with self._lock:
            if market not in self._stop_events:
                logging.warning(f"No monitoring active for {market}")
                return
            self._stop_events[market].set()
        
        thread = self._threads.pop(market, None)
        if thread and thread.is_alive():
            logging.info(f"Waiting for thread to finish for {market}")
            thread.join(timeout=2)
        with self._lock:
            self.active_trades.pop(market, None)
            self._stop_events.pop(market, None)
        logging.info(f"Monitoring stopped for {market}")

    def _monitor_trade(self, market: str, stop_event: threading.Event) -> None:
        logging.info(f"Monitoring started for {market}")
        try:
            while not stop_event.is_set():
                try:
                    response = self.api.send_request("GET", f"/ticker/price?market={market}")
                    if not response:
                        logging.debug(f"No response received for {market}, retrying...")
                        time.sleep(self.config.check_interval)
                        continue

                    price_str = response.get('price', '0')
                    try:
                        current_price = Decimal(price_str)
                    except (InvalidOperation, Exception) as e:
                        logging.error(f"Invalid price received for {market}: {price_str} - {e}")
                        time.sleep(self.config.check_interval)
                        continue

                    logging.debug(f"Current price for {market} is {current_price}")

                    with self._lock:
                        if market not in self.active_trades:
                            logging.info(f"Market {market} removed from active_trades, stopping thread.")
                            break
                        trade = self.active_trades[market]
                        trade.current_price = current_price
                        trade.last_update = datetime.now()

                        if current_price > trade.highest_price:
                            trade.highest_price = current_price
                            trade.trailing_stop_price = current_price * (Decimal('1') - self.config.trailing_pct / Decimal('100'))
                            profit_pct = ((current_price - trade.buy_price) / trade.buy_price) * 100
                            print(f"📈 {market} NEW HIGH: €{current_price} (+{profit_pct:.1f}%) | Stop: €{trade.trailing_stop_price}")
                            logging.info(f"Updated {market} - Highest: {trade.highest_price}, Trailing Stop: {trade.trailing_stop_price}")

                        # Check stop loss
                        if current_price <= trade.stop_loss_price:
                            loss_pct = ((current_price - trade.buy_price) / trade.buy_price) * 100
                            print(f"\n🛑 STOP LOSS TRIGGERED: {market}")
                            print(f"💸 Sell at €{current_price} | Loss: {loss_pct:.2f}%")
                            logging.info(f"Stop loss triggered for {market} at {current_price}")
                            if self.sell_market(market):
                                # Record the completed trade before cleanup
                                self.record_completed_trade(market, current_price, "stop_loss")
                                print(f"✅ SELL SUCCESS: {market} position closed")
                                logging.info(f"Exiting thread after stop loss for {market}")
                                # Clean up immediately when triggered
                                self.active_trades.pop(market, None)
                                stop_event.set()
                                break

                        # Check trailing stop (take profit)
                        if current_price <= trade.trailing_stop_price:
                            profit_pct = ((current_price - trade.buy_price) / trade.buy_price) * 100
                            print(f"\n🎯 TRAILING STOP TRIGGERED: {market}")
                            print(f"💰 Sell at €{current_price} | Profit: {profit_pct:.2f}%")
                            logging.info(f"Trailing stop triggered for {market} at {current_price}")
                            if self.sell_market(market):
                                # Record the completed trade before cleanup
                                self.record_completed_trade(market, current_price, "trailing_stop")
                                print(f"✅ SELL SUCCESS: {market} position closed with profit!")
                                logging.info(f"Exiting thread after trailing stop for {market}")
                                # Clean up immediately when triggered
                                self.active_trades.pop(market, None)
                                stop_event.set()
                                break

                except Exception as e:
                    logging.error(f"Error monitoring {market}: {str(e)}")

                time.sleep(self.config.check_interval)
        finally:
            # Ensure cleanup happens only once when thread exits naturally
            logging.info(f"Monitoring thread for {market} exiting naturally")
            # Update persistence file to reflect any trade closures
            self.save_active_trades()
