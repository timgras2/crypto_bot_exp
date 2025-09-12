# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a clean cryptocurrency trading bot project targeting the Bitvavo exchange. The **master branch** contains the essential core functionality: new listing detection and automated trading with trailing stop-loss protection.

**Master Branch Philosophy**: Focused on reliability and simplicity. Advanced features like multi-exchange support, sentiment analysis, and asset protection strategies are available in feature branches but excluded from master to maintain a clean, easy-to-understand codebase.

## Project Structure

```
crypto_bot_main/
├── src/                       # Main source code
│   ├── __init__.py           # Package initialization
│   ├── main.py               # Entry point with TradingBot class
│   ├── config.py             # Configuration management with validation
│   ├── requests_handler.py   # BitvavoAPI wrapper with rate limiting
│   ├── market_utils.py       # MarketTracker for new listings detection
│   └── trade_logic.py        # TradeManager for execution and monitoring
├── tests/                    # Comprehensive unit tests
│   ├── __init__.py
│   ├── conftest.py          # pytest configuration and fixtures
│   ├── test_config.py       # Configuration validation tests
│   ├── test_market_utils.py # Market tracking tests
│   ├── test_requests_handler.py # API wrapper tests
│   └── test_trade_logic.py  # Trade execution and monitoring tests
├── scripts/                  # Utility scripts
│   ├── start_bot.py         # Bot launcher
│   ├── start_bot.bat        # Windows launcher
│   ├── start_bot.sh         # Unix launcher
│   ├── review_trades.py     # Trade analysis tool
│   ├── review_trades.bat    # Windows launcher for trade review
│   └── sell_small_holdings.py # Portfolio cleanup utility
├── docs/                     # Documentation
│   ├── QUICKSTART.md        # Quick setup guide
│   ├── SAFETY_CHECKLIST.md  # Pre-trading safety checks
│   ├── FIRST_RUN_BEHAVIOR.md # First run documentation
│   ├── BITVAVO_API_UPDATE.md # API changes documentation
│   ├── GIT_WORKFLOW.md      # Git workflow guide
│   └── TERMINAL_OUTPUT_EXAMPLE.md # Example bot output
├── requirements.txt          # Python dependencies
├── setup.py                 # Package setup configuration
├── pytest.ini              # pytest configuration
├── .env.example             # Environment variables template
├── .gitignore               # Git ignore rules
└── CLAUDE.md               # This file
```

## Architecture

The main trading bot consists of:

- **TradingBot** (`main.py`): Main orchestrator class with graceful shutdown handling
- **MarketTracker** (`market_utils.py`): Monitors for new token listings on the exchange
- **TradeManager** (`trade_logic.py`): Handles trade execution and trailing stop-loss monitoring
- **BitvavoAPI** (`requests_handler.py`): Rate-limited API wrapper with retry logic
- **Configuration** (`config.py`): Centralized configuration management with enhanced validation and clear error messages

## Environment Configuration

Copy `.env.example` to `.env` and configure:

Required environment variables:
```
BITVAVO_API_KEY=your_api_key
BITVAVO_API_SECRET=your_api_secret
```

Optional trading parameters (with safe defaults):
```
# Critical safety settings
MAX_TRADE_AMOUNT=5.0        # EUR per trade - START VERY SMALL!
MIN_PROFIT_PCT=5.0          # Stop loss percentage (5% loss = sell)
TRAILING_PCT=3.0            # Trailing stop percentage (locks in profits)

# Bot behavior
CHECK_INTERVAL=10           # Price check interval (seconds)
MAX_RETRIES=3               # API request retry attempts
RETRY_DELAY=5               # Delay between retries (seconds)

# Advanced API settings (defaults usually work)
RATE_LIMIT=300              # API requests per minute
API_TIMEOUT=30              # API request timeout (seconds)
OPERATOR_ID=1001            # Required by Bitvavo API
BITVAVO_BASE_URL=https://api.bitvavo.com/v2  # API base URL
```

## Safety and Risk Management

**⚠️ CRITICAL SAFETY WARNINGS:**
- This bot trades with **real money** on cryptocurrency exchanges
- **Always start with very small amounts** (€1-5 per trade) for testing
- Never invest more than you can afford to lose completely
- The bot will automatically trade on **ALL new listings** - this is high risk
- Monitor the bot closely during initial runs
- Consider using Bitvavo's paper trading feature first if available

**Enhanced Safety Features in Master Branch:**
- Improved input validation with clear error messages
- Better API error handling and retry logic  
- Comprehensive parameter range checking
- Safety-focused default values in `.env.example`

## Common Development Commands

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your API credentials
```

### Running the Bot
```bash
# Run the trading bot directly
python src/main.py

# Or use the launcher script (recommended)
python scripts/start_bot.py

# Windows batch file
scripts/start_bot.bat

# Unix shell script  
scripts/start_bot.sh
```

### Testing
```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_config.py

# Run tests with verbose output
python -m pytest tests/ -v
```

## Dependencies

Key dependencies (see `requirements.txt`):
- `python-bitvavo-api>=1.2.3` - Official Bitvavo API client
- `python-dotenv>=1.0.0` - Environment variable management  
- `requests>=2.31.0` - HTTP library for API calls
- `urllib3>=2.0.0` - URL handling library
- `pytest>=7.4.0` - Testing framework

## Key Features

- **New Listing Detection**: Monitors Bitvavo for newly added trading pairs
- **Automated Trading**: Places market buy orders for new listings with volume validation
- **Trailing Stop-Loss**: Dynamic profit protection that adjusts with price increases
- **State Recovery**: Resumes monitoring after bot restarts without losing positions
- **Risk Management**: Configurable trade amounts, stop-loss, and trailing percentages
- **Rate Limiting**: Respects exchange API limits with sliding window implementation
- **Comprehensive Logging**: Detailed activity logs for debugging and monitoring
- **Input Validation**: Extensive validation of all trading parameters and market names

## Data Persistence

Runtime directories are created automatically:
- `data/previous_markets.json` - New listing detection baseline
- `data/active_trades.json` - Active trade state for recovery after restarts
- `logs/trading.log` - Bot activity and error logs

## Threading Model

- Main loop for detecting new listings every `CHECK_INTERVAL` seconds
- Separate dedicated threads for monitoring each active trade with trailing stop-loss
- Thread-safe operations with locks for shared state management
- Graceful shutdown handling with signal handlers (SIGINT/SIGTERM)

## Advanced Features

For advanced features like asset protection, sentiment analysis, and simulation tools, see feature branches:
- `feature/asset-protection-strategy` - DCA buying and profit taking
- `feature/social-media-sentiment-analysis` - Reddit sentiment integration
- `feature/dip-buy-strategy` - Post-sale rebuy logic