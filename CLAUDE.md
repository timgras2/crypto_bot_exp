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
├── simulator/                # Trading strategy simulator
│   ├── __init__.py          # Package initialization
│   ├── simulation_engine.py # Core simulation engine
│   ├── mock_api.py          # Mock Bitvavo API with historical data
│   ├── results_analyzer.py  # Analysis and reporting tools
│   ├── data/               # Historical price data
│   └── results/            # Simulation results and analysis
├── future_work/             # Advanced features (dip buying strategy)
│   ├── dip_buy_manager.py  # Main orchestration for dip buying
│   ├── dip_evaluator.py    # Decision engine for rebuy opportunities
│   ├── dip_state.py        # Thread-safe state persistence
│   └── market_filter.py    # Market condition filtering
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
├── run_simulation.py    # Trading strategy simulator launcher
├── test_simulator.py    # Comprehensive simulator tests
├── .env.example         # Environment variables template
├── CLAUDE.md           # This file - main development guide
├── CLAUDE_DIP_BUY.md   # Comprehensive dip buying strategy guide
├── CLAUDE_SIMULATOR.md # Detailed simulator documentation
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

### Running the Simulator
```bash
# Interactive simulator with strategy testing
python run_simulation.py

# Quick simulator tests
python test_simulator.py

# Simple functionality test  
python test_simulator_simple.py
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

### Core Trading Features
- **New Listing Detection**: Monitors Bitvavo for newly added trading pairs
- **Automated Trading**: Places market buy orders for new listings with volume validation
- **Trailing Stop-Loss**: Dynamic profit protection that adjusts with price increases
- **State Recovery**: Resumes monitoring after bot restarts without losing positions
- **Risk Management**: Configurable trade amounts, stop-loss, and trailing percentages
- **Rate Limiting**: Respects exchange API limits with sliding window implementation
- **Comprehensive Logging**: Detailed activity logs for debugging and monitoring
- **Input Validation**: Extensive validation of all trading parameters and market names

### Advanced Features (Optional)
- **Dip Buying Strategy**: Automatically rebuy assets after profitable sales when price drops
- **Multi-Level Dip Tracking**: Configure multiple price thresholds with different capital allocations
- **Market Condition Filtering**: Optional BTC trend analysis to gate rebuy decisions
- **Thread-Safe State Management**: Robust persistence with atomic operations and recovery

### Testing & Simulation
- **Historical Backtesting**: Test strategies against real historical price data
- **Mock API Simulation**: Safe testing environment with realistic market behavior
- **Performance Analysis**: Detailed P&L analysis and strategy optimization
- **Risk Assessment**: Comprehensive reporting on strategy effectiveness

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

## Unicode and Encoding Issues (Windows)

When developing on Windows, you may encounter Unicode encoding errors when using emojis or special characters in Python scripts. This is because Windows console often defaults to CP1252 encoding instead of UTF-8.

### Common Unicode Error
```
UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f916' in position 0: character maps to <undefined>
```

### Prevention Template

Add this to the top of Python files that use Unicode characters:

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys

# Fix Unicode encoding on Windows
if sys.platform.startswith('win'):
    try:
        # Try to set UTF-8 for stdout
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, OSError):
        # Fallback for older Python versions or restricted environments
        pass
```

### Handling Print Statements

For print statements with emojis, use try-catch fallback:

```python
try:
    print("🤖 Bot Status")
except UnicodeEncodeError:
    print("Bot Status")  # Fallback without emoji
```

### File Writing

Always specify UTF-8 encoding for file operations:

```python
# Good
file_path.write_text(content, encoding='utf-8')

# Bad (uses system default)
file_path.write_text(content)
```

### Testing

The simulator and test files have been updated with these fixes. Use them as templates for new Python files that include Unicode characters.

## Development Notes

### Recent v2.0 Improvements
- **Thread Safety**: All dip buying components now use atomic operations and proper locking
- **Input Validation**: Comprehensive validation prevents crashes from invalid data
- **API Compliance**: Fixed simulator to properly comply with Bitvavo API requirements
- **Error Recovery**: Graceful handling of file corruption and network issues
- **Performance**: Optimized balance tracking and state management

### Code Quality Standards
- All new code includes comprehensive input validation
- Thread-safe operations use proper locking mechanisms
- File operations are atomic with backup and recovery
- Error messages are descriptive and actionable
- Unicode characters handled properly on Windows

### Testing Requirements
- Unit tests for all critical components
- Integration tests for component interactions
- Simulator tests for strategy validation
- Error injection tests for robustness

## Future Work

The `future_work/` directory contains:
- **Advanced dip buying strategy** (production-ready)
- **Portfolio tracking functionality** (`bitvavo_interface.py`) for enhanced management
- **Market analysis tools** for strategy optimization

All future work follows the same quality standards with comprehensive error handling, input validation, and thread safety.

## Claude Code Development Guidelines

### Unicode/Emoji Handling 
**CRITICAL**: When writing Python scripts that include emojis or Unicode characters on Windows, ALWAYS use the standard Unicode template from this project (see Unicode section above). Do NOT assume Unicode errors are terminal failures - they are easily fixable encoding issues.

**The Issue**: Modern Windows terminals support Unicode perfectly, but Python defaults to CP1252 encoding instead of UTF-8, causing `UnicodeEncodeError: 'charmap' codec can't encode character` errors.

**The Solution**: ALWAYS include this at the top of Python files with Unicode:
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys

# Fix Unicode encoding on Windows  
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, OSError):
        pass
```

**Development Pattern**: 
1. When you encounter Unicode errors, apply the fix above rather than removing emojis
2. Most files in this project already use this pattern - follow their example
3. Look at `review_trades.py`, `run_simulation.py`, `test_simulator.py` as templates
4. The user prefers Unicode characters and emojis in output when appropriate

This prevents the repeated pattern of encountering Unicode issues during testing and development.