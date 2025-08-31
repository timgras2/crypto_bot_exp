import logging
import signal
import time
from pathlib import Path

from .config import load_config
from .requests_handler import BitvavoAPI
from .market_utils import MarketTracker
from .trade_logic import TradeManager


class TradingBot:
    def __init__(self) -> None:
        # Load configuration
        self.trading_config, self.api_config, self.dip_config = load_config()

        # Initialize components
        self.api = BitvavoAPI(self.api_config)
        self.market_tracker = MarketTracker(
            api=self.api,
            storage_path=Path("data") / "previous_markets.json"
        )
        self.trade_manager = TradeManager(self.api, self.trading_config)
        
        # Initialize dip buy manager (conditional)
        self.dip_manager = None
        if self.dip_config.enabled:
            try:
                from strategies.dip_buy_manager import DipBuyManager
                data_dir = Path("data")
                self.dip_manager = DipBuyManager(
                    api=self.api,
                    config=self.dip_config,
                    trading_config=self.trading_config,
                    data_dir=data_dir,
                    check_interval=self.trading_config.check_interval
                )
                # Connect dip manager to trade manager
                self.trade_manager.set_dip_manager(self.dip_manager)
                logging.info("Dip buy manager initialized and connected")
            except ImportError as e:
                logging.warning(f"Failed to import dip buy manager: {e}")
                self.dip_config.enabled = False

        # Initialize state
        self.previous_markets = self.market_tracker.load_previous_markets()
        self.running = True
        
        # Restore any previously active trades
        self.trade_manager.restore_monitoring()
        
        # Start dip buying service if enabled
        if self.dip_manager:
            self.dip_manager.start()

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)

    def handle_shutdown(self, signum, frame) -> None:
        """Handle shutdown signals."""
        print("\n🛑 SHUTDOWN REQUESTED - Cleaning up safely...")
        logging.info("Received shutdown signal. Cleaning up...")
        self.running = False

    def shutdown(self) -> None:
        """Perform cleanup operations."""
        print("🔄 Preparing for graceful shutdown...")
        logging.info("Shutting down bot...")
        
        # Stop dip buying service first
        if self.dip_manager:
            self.dip_manager.stop()
            print("🛑 Dip buy monitoring stopped")
        
        # Prepare trade manager for shutdown (prevents file deletion)
        self.trade_manager.prepare_for_shutdown()
        
        # Save active trades before stopping them
        active_count = len(self.trade_manager.active_trades)
        logging.info(f"Shutdown: Found {active_count} active trades to save")
        if active_count > 0:
            print(f"💾 Saving {active_count} active trades for recovery...")
            logging.info(f"Shutdown: Calling save_active_trades with trades: {list(self.trade_manager.active_trades.keys())}")
            self.trade_manager.save_active_trades()
            
            print(f"📊 Stopping monitoring for {active_count} active trades...")
            for market in list(self.trade_manager.active_trades.keys()):
                print(f"🛑 Stopping monitoring: {market}")
                logging.info(f"Shutdown: Stopping monitoring for {market}")
                self.trade_manager.stop_monitoring(market)
        else:
            print("✅ No active trades to save")
            logging.info("Shutdown: No active trades found to save")

        # Save final market state
        if self.previous_markets:
            self.market_tracker.save_previous_markets(self.previous_markets)
            print("💾 Market data saved")
        
        print("✅ Bot shutdown complete - Active trades saved for next startup")

    def run(self) -> None:
        """Main bot loop."""
        logging.info("Starting trading bot...")
        print("🤖 Bot is now active and scanning for new listings...")
        print(f"💰 Max trade amount: €{self.trading_config.max_trade_amount}")
        print(f"🔄 Checking every {self.trading_config.check_interval} seconds")
        print(f"📈 Stop loss: {self.trading_config.min_profit_pct}% | Trailing stop: {self.trading_config.trailing_pct}%")
        
        # Show dip buying status
        if self.dip_config.enabled:
            print(f"🎯 Dip buying: ENABLED")
            levels_str = ", ".join([f"-{level.threshold_pct}%" for level in self.dip_config.dip_levels])
            print(f"📊 Dip levels: {levels_str}")
        else:
            print(f"🎯 Dip buying: DISABLED")
        
        print("-" * 60)
        
        # Check if this is first run
        is_first_run = not self.previous_markets
        if is_first_run:
            print("🔄 First run detected - establishing market baseline...")
        
        scan_count = 0
        while self.running:
            try:
                scan_count += 1
                current_time = time.strftime("%H:%M:%S")
                
                # Show periodic status
                if scan_count % 6 == 1:  # Every minute (6 scans at 10sec intervals)
                    active_trades = len(self.trade_manager.active_trades)
                    if active_trades > 0:
                        print(f"🕐 {current_time} | ✅ Bot running | 📊 {active_trades} active trades | Scan #{scan_count}")
                    else:
                        print(f"🕐 {current_time} | ✅ Bot running | 👀 Scanning for new listings... | Scan #{scan_count}")
                
                # Reload previous_markets from disk to detect manual changes
                old_previous_markets = self.previous_markets
                self.previous_markets = self.market_tracker.load_previous_markets()
                
                # Log if manual changes were detected
                if set(old_previous_markets) != set(self.previous_markets):
                    removed = set(old_previous_markets) - set(self.previous_markets)
                    added = set(self.previous_markets) - set(old_previous_markets)
                    if removed:
                        print(f"📝 Manual file change detected - Removed pairs: {list(removed)}")
                        logging.info(f"Manual removal detected: {list(removed)}")
                    if added:
                        print(f"📝 Manual file change detected - Added pairs: {list(added)}")
                        logging.info(f"Manual additions detected: {list(added)}")
                
                # Check for new listings
                new_listings, current_markets = self.market_tracker.detect_new_listings(
                    self.previous_markets
                )

                # Update stored markets if changes were detected
                if current_markets:
                    self.market_tracker.save_previous_markets(current_markets)
                    self.previous_markets = current_markets
                    
                    # Handle first run baseline establishment
                    if is_first_run and scan_count == 1:
                        print(f"✅ Baseline established: {len(current_markets)} existing markets saved")
                        print(f"📊 Now monitoring for NEW listings added to Bitvavo...")
                        is_first_run = False  # Mark as no longer first run
                    elif scan_count == 1 and not is_first_run:  # Subsequent runs
                        print(f"📊 Monitoring {len(current_markets)} markets for new listings")

                # Place trades for new listings
                for market in new_listings:
                    print(f"\n🚨 NEW LISTING DETECTED: {market}")
                    
                    # Skip if we're already trading this market
                    if market in self.trade_manager.active_trades:
                        print(f"⏭️  Already trading {market}, skipping...")
                        continue

                    logging.info(f"Attempting to trade new listing: {market}")
                    print(f"🔍 Analyzing {market}...")

                    # Try to get ticker data with retries (new markets may take time to have ticker data)
                    ticker = None
                    max_ticker_retries = 3
                    for ticker_attempt in range(max_ticker_retries):
                        ticker = self.api.send_request("GET", f"/ticker/24h?market={market}")
                        if ticker:
                            break
                        
                        if ticker_attempt < max_ticker_retries - 1:
                            print(f"⏳ Ticker data not available, retrying in 2 seconds... (attempt {ticker_attempt + 1}/{max_ticker_retries})")
                            # Use interruptible sleep
                            for _ in range(2):
                                if not self.running:
                                    break
                                time.sleep(1)
                    
                    # If we still can't get ticker data after retries, consider proceeding with caution
                    if not ticker:
                        print(f"⚠️  No ticker data available for {market} after {max_ticker_retries} attempts")
                        print(f"🎲 New listing might be too fresh - attempting trade without volume validation")
                        logging.warning(f"Proceeding with {market} trade without ticker validation - new listing")
                        
                        # Proceed with trade but use smaller amount for safety
                        trade_amount = min(
                            self.trading_config.max_trade_amount * 0.5,  # Use 50% of max for unvalidated trades
                            5.0  # Cap at €5 for safety
                        )
                        print(f"🛡️  Using reduced amount €{trade_amount} for safety")
                        
                        buy_price = self.trade_manager.place_market_buy(market, trade_amount)
                        if buy_price:
                            print(f"✅ BUY SUCCESS: {market} at €{buy_price}")
                            print(f"🎯 Starting monitoring with trailing stop-loss...")
                            self.trade_manager.start_monitoring(market, buy_price)
                        else:
                            print(f"❌ BUY FAILED: Could not execute order for {market}")
                        continue
                    
                    try:
                        volume = float(ticker.get('volume', '0'))
                        price = float(ticker.get('last', '0'))
                        # Check if volume is sufficient for our trade amount
                        min_volume_threshold = float(self.trading_config.max_trade_amount) * 10  # 10x our trade amount
                        
                        print(f"📊 {market} | Price: €{price:.6f} | Volume: €{volume:.2f}")
                        
                        if volume <= min_volume_threshold:
                            print(f"⚠️  Volume too low (€{volume:.2f} < €{min_volume_threshold:.2f}), skipping...")
                            logging.warning(f"Skipping {market} due to insufficient volume: {volume} (min: {min_volume_threshold})")
                            continue
                            
                    except (ValueError, TypeError) as e:
                        print(f"❌ Invalid ticker data for {market}: {e}")
                        logging.warning(f"Skipping {market} due to invalid volume data: {e}")
                        continue

                    print(f"💸 EXECUTING BUY ORDER: €{self.trading_config.max_trade_amount} of {market}")
                    buy_price = self.trade_manager.place_market_buy(
                        market,
                        self.trading_config.max_trade_amount
                    )

                    if buy_price:
                        print(f"✅ BUY SUCCESS: {market} at €{buy_price}")
                        print(f"🎯 Starting monitoring with trailing stop-loss...")
                        self.trade_manager.start_monitoring(market, buy_price)
                    else:
                        print(f"❌ BUY FAILED: Could not execute order for {market}")

                # Use interruptible sleep to allow responsive Ctrl+C
                for _ in range(self.trading_config.check_interval):
                    if not self.running:  # Check if shutdown was requested
                        break
                    time.sleep(1)  # Sleep 1 second at a time

            except Exception as e:
                print(f"🚨 ERROR in main loop: {str(e)}")
                logging.exception(f"Error in main loop: {str(e)}")
                # Use interruptible sleep for error retry delay
                for _ in range(self.trading_config.retry_delay):
                    if not self.running:  # Check if shutdown was requested
                        break
                    time.sleep(1)  # Sleep 1 second at a time


def main() -> None:
    """Entry point for the trading bot."""
    # Configure logging (this is the centralized configuration)
    # Create logs directory if it doesn't exist
    logs_dir = Path(__file__).parent.parent / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(logs_dir / 'trading.log'),
            logging.StreamHandler()
        ]
    )

    print("🚀 Initializing Crypto Trading Bot...")
    bot = TradingBot()
    print("✅ Bot initialized successfully")
    
    try:
        bot.run()
    except KeyboardInterrupt:
        print("\n⌨️  Keyboard interrupt received")
        logging.info("KeyboardInterrupt received.")
    except Exception as e:
        print(f"\n🚨 Unexpected error: {e}")
        logging.exception("Unexpected error in main")
    finally:
        bot.shutdown()


if __name__ == '__main__':
    main()
