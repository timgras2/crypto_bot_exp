# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a clean cryptocurrency trading bot project targeting the Bitvavo exchange. The project has been consolidated from multiple versions into a single, well-structured codebase with the best features from the previous iterations.

## Project Structure

```
crypto_bot_main/
├── src/                       # Main source code
│   ├── __init__.py           # Package initialization
│   ├── main.py               # Entry point with TradingBot class
│   ├── config.py             # Configuration management with validation
│   ├── requests_handler.py   # BitvavoAPI wrapper with rate limiting
│   ├── market_utils.py       # MarketTracker for new listings detection
│   ├── trade_logic.py        # TradeManager for execution and monitoring
│   └── crypto_bot.egg-info/  # Package metadata (auto-generated)
├── tests/                    # Comprehensive unit tests
│   ├── __init__.py
│   ├── conftest.py          # pytest configuration and fixtures
│   ├── test_config.py       # Configuration validation tests
│   ├── test_market_utils.py # Market tracking tests
│   ├── test_requests_handler.py # API wrapper tests
│   └── test_trade_logic.py  # Trade execution and monitoring tests
├── data/                    # Data persistence directory
│   ├── README.md           # Data directory documentation
│   ├── previous_markets.json # Historical market listings
│   └── active_trades.json  # Active trade state (auto-managed)
├── logs/                   # Logging directory
│   ├── README.md          # Logging documentation
│   └── trading.log        # Bot activity logs (auto-generated)
├── future_work/           # V3 features for future implementation
│   └── bitvavo_interface.py # Portfolio tracking functionality
├── requirements.txt       # Python dependencies
├── setup.py              # Package setup configuration
├── pytest.ini           # pytest configuration
├── start_bot.py         # Convenient launcher script
├── start_bot.bat        # Windows batch launcher
├── start_bot.sh         # Unix shell launcher
├── .env.example         # Environment variables template
├── CLAUDE.md           # This file
├── QUICKSTART.md       # Quick setup guide
├── SAFETY_CHECKLIST.md # Pre-trading safety checks
├── FIRST_RUN_BEHAVIOR.md # First run documentation
├── BITVAVO_API_UPDATE.md # API changes documentation
└── TERMINAL_OUTPUT_EXAMPLE.md # Example bot output
```

## Architecture

The main trading bot consists of:

- **TradingBot** (`main.py`): Main orchestrator class with graceful shutdown handling
- **MarketTracker** (`market_utils.py`): Monitors for new token listings on the exchange
- **TradeManager** (`trade_logic.py`): Handles trade execution and trailing stop-loss monitoring
- **BitvavoAPI** (`requests_handler.py`): Rate-limited API wrapper with retry logic
- **Configuration** (`config.py`): Centralized configuration management with dataclasses

## Environment Configuration

Copy `.env.example` to `.env` and configure:

Required environment variables:
```
BITVAVO_API_KEY=your_api_key
BITVAVO_API_SECRET=your_api_secret
```

Optional trading parameters (with defaults):
```
MIN_PROFIT_PCT=5.0          # Stop loss percentage
TRAILING_PCT=3.0            # Trailing stop percentage  
MAX_TRADE_AMOUNT=10.0       # Maximum EUR per trade
CHECK_INTERVAL=10           # Price check interval (seconds)
MAX_RETRIES=3               # API request retry attempts
RETRY_DELAY=5               # Delay between retries (seconds)
RATE_LIMIT=300              # API requests per minute
API_TIMEOUT=30              # API request timeout (seconds)
OPERATOR_ID=1001            # Required by Bitvavo API for order identification
BITVAVO_BASE_URL=https://api.bitvavo.com/v2  # API base URL
```

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
python start_bot.py

# Windows batch file
start_bot.bat

# Unix shell script  
./start_bot.sh
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

Development dependencies (optional, in `setup.py`):
- `pytest-cov>=4.1.0` - Test coverage reporting
- `black>=23.0.0` - Code formatting
- `flake8>=6.0.0` - Code linting

## Security Notes

- API credentials are stored in environment variables only with format validation
- Comprehensive input validation for all trading parameters and market names
- All trading operations include proper error handling and logging
- Improved rate limiting with sliding window implementation
- Configuration parameter validation with safe ranges

## Data Persistence

- Market data stored in `data/previous_markets.json` (new listing detection baseline)
- Active trade state in `data/active_trades.json` (for recovery after restarts)
- Trading logs written to `logs/trading.log` (bot activity and errors)
- All data directories created automatically if they don't exist
- Trade state persistence ensures no lost positions during bot restarts

## Threading Model

The bot uses threading for concurrent operations:
- Main loop for detecting new listings every `CHECK_INTERVAL` seconds
- Separate dedicated threads for monitoring each active trade with trailing stop-loss
- Thread-safe operations with locks for shared state management
- Graceful shutdown handling with signal handlers (SIGINT/SIGTERM)
- Interruptible sleep patterns for responsive Ctrl+C handling
- Automatic cleanup of threads and resources on shutdown

## Key Features

- **New Listing Detection**: Monitors Bitvavo for newly added trading pairs
- **Automated Trading**: Places market buy orders for new listings with volume validation
- **Trailing Stop-Loss**: Dynamic profit protection that adjusts with price increases
- **State Recovery**: Resumes monitoring after bot restarts without losing positions
- **Risk Management**: Configurable trade amounts, stop-loss, and trailing percentages
- **Rate Limiting**: Respects exchange API limits with sliding window implementation
- **Comprehensive Logging**: Detailed activity logs for debugging and monitoring
- **Input Validation**: Extensive validation of all trading parameters and market names

## Testing

The project includes comprehensive unit tests covering:
- Configuration validation and environment loading
- Market tracking and new listing detection  
- API request handling and rate limiting
- Trade execution and monitoring logic
- Error handling and edge cases

Run tests with `python -m pytest tests/ -v` for detailed output.

## Documentation

Additional documentation files provide specific guidance:
- `QUICKSTART.md` - Step-by-step setup instructions
- `SAFETY_CHECKLIST.md` - Pre-trading safety verification  
- `FIRST_RUN_BEHAVIOR.md` - What to expect on first execution
- `BITVAVO_API_UPDATE.md` - Recent API changes and requirements
- `TERMINAL_OUTPUT_EXAMPLE.md` - Example of typical bot output

## Future Work

The `future_work/` directory contains portfolio tracking functionality (`bitvavo_interface.py`) that can be integrated when needed. This provides enhanced portfolio management and tracking features beyond basic trading automation.