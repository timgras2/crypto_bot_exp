# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a clean cryptocurrency trading bot project targeting the Bitvavo exchange. The project has been consolidated from multiple versions into a single, well-structured codebase with the best features from the previous iterations.

## Project Structure

```
crypto_bot_main/
├── src/                       # Core source code
│   ├── strategies/           # Advanced trading strategies  
│   │   ├── __init__.py      # Package initialization
│   │   ├── dip_buy_manager.py  # Main orchestration for dip buying
│   │   ├── dip_evaluator.py    # Decision engine for rebuy opportunities
│   │   ├── dip_state.py        # Thread-safe state persistence
│   │   └── market_filter.py    # Market condition filtering
│   ├── sentiment/            # Social media sentiment analysis
│   │   ├── __init__.py      # Sentiment package initialization
│   │   ├── sentiment_analyzer.py # VADER-based crypto sentiment analysis
│   │   ├── data_collector.py     # Multi-source social media data coordinator
│   │   ├── reddit_collector.py   # Reddit API data collection
│   │   ├── discord_collector.py  # Discord monitoring (optional)
│   │   ├── telegram_collector.py # Telegram monitoring (optional)
│   │   └── sentiment_cache.py    # Caching and deduplication system
│   ├── __init__.py           # Package initialization
│   ├── main.py               # Entry point with TradingBot class
│   ├── config.py             # Configuration management with validation
│   ├── requests_handler.py   # BitvavoAPI wrapper with rate limiting
│   ├── market_utils.py       # MarketTracker for new listings detection
│   ├── trade_logic.py        # TradeManager for execution and monitoring
│   ├── asset_protection_manager.py # Asset protection orchestration
│   ├── enhanced_asset_protection.py # Enhanced trailing profit and dynamic buybacks
│   ├── volatility_calculator.py    # Dynamic volatility-based risk management
│   ├── protected_asset_state.py    # Thread-safe asset protection state
│   └── circuit_breaker.py          # System stability protection
├── tests/                    # Comprehensive unit tests
│   ├── __init__.py
│   ├── conftest.py          # pytest configuration and fixtures
│   ├── test_config.py       # Configuration validation tests
│   ├── test_market_utils.py # Market tracking tests
│   ├── test_requests_handler.py # API wrapper tests
│   ├── test_trade_logic.py  # Trade execution and monitoring tests
│   ├── test_asset_protection.py # Asset protection unit tests (44 tests)
│   ├── test_asset_protection_integration.py # Asset protection integration tests (11 tests)
│   ├── test_simulator.py    # Comprehensive simulator tests
│   ├── test_simulator_simple.py # Simple simulator tests
│   ├── test_social_media_pipeline.py # Sentiment analysis integration tests
│   ├── test_reddit_connection.py # Reddit API connection tests
│   ├── test_telegram_connection.py # Telegram API connection tests
│   ├── test_sentiment_integration.py # Sentiment integration tests
│   ├── test_vader_sentiment.py # Sentiment analyzer validation
│   └── test_asset_protection_upgrades.py # Asset protection upgrade tests
├── simulator/                # Trading strategy simulator
│   ├── __init__.py          # Package initialization
│   ├── simulation_engine.py # Core simulation engine
│   ├── mock_api.py          # Mock Bitvavo API with historical data
│   ├── results_analyzer.py  # Analysis and reporting tools
│   ├── swing_trading_simulator.py # Swing trading strategy simulator
│   ├── data/               # Historical price data
│   └── results/            # Simulation results and analysis
├── scripts/                  # Utility scripts and launchers
│   ├── start_bot.py         # Convenient launcher script
│   ├── start_bot.bat        # Windows batch launcher
│   ├── start_bot.sh         # Unix shell launcher
│   ├── run_simulation.py    # Trading strategy simulator launcher
│   ├── review_trades.py     # Trade performance analysis
│   ├── review_trades.bat    # Windows launcher for trade review
│   └── sell_small_holdings.py # Portfolio cleanup utility
├── tools/                    # Portfolio management tools
│   ├── __init__.py          # Package initialization
│   └── bitvavo_interface.py # Portfolio tracking functionality
├── docs/                     # Documentation
│   ├── ASSET_PROTECTION_UPGRADE_GUIDE.md # Asset protection upgrades
│   ├── CLAUDE_ASSET_PROTECTION.md # Asset protection strategy guide
│   ├── CLAUDE_DIP_BUY.md    # Comprehensive dip buying strategy guide
│   ├── CLAUDE_SIMULATOR.md  # Detailed simulator documentation
│   ├── CONFIGURATION_GUIDE.md # Configuration documentation
│   ├── DIP_BUY_IMPLEMENTATION.md # Dip buying implementation guide
│   ├── DOCUMENTATION_INDEX.md    # Documentation overview
│   ├── DYNAMIC_REBUY_IMPLEMENTATION_GUIDE.md # Dynamic rebuy guide
│   ├── ENHANCED_FEATURES_SUMMARY.md # Enhanced features overview
│   ├── GIT_WORKFLOW.md      # Git workflow documentation
│   ├── SIMULATOR_ARCHITECTURE.md # Simulator architecture
│   ├── SIMULATOR_README.md  # Simulator usage guide
│   ├── BITVAVO_API_UPDATE.md # API changes documentation
│   ├── FIRST_RUN_BEHAVIOR.md # First run documentation
│   ├── QUICKSTART.md        # Quick setup guide
│   ├── SAFETY_CHECKLIST.md  # Pre-trading safety checks
│   ├── SOCIAL_MEDIA_SENTIMENT_SETUP.md # Sentiment analysis setup guide
│   ├── TERMINAL_OUTPUT_EXAMPLE.md # Example bot output
│   └── UPGRADE_SIMULATION_RESULTS.md # Simulation results documentation
├── requirements.txt         # Python dependencies
├── setup.py                # Package setup configuration
├── pytest.ini             # pytest configuration
├── .env.example           # Environment variables template
└── CLAUDE.md             # This file - main development guide
```

## Architecture

The main trading bot consists of:

- **TradingBot** (`main.py`): Main orchestrator class with graceful shutdown handling
- **MarketTracker** (`market_utils.py`): Monitors for new token listings on the exchange
- **TradeManager** (`trade_logic.py`): Handles trade execution and trailing stop-loss monitoring
- **AssetProtectionManager** (`asset_protection_manager.py`): Protects existing assets with DCA and profit taking
- **BitvavoAPI** (`requests_handler.py`): Rate-limited API wrapper with retry logic
- **Configuration** (`config.py`): Centralized configuration management with dataclasses
- **CircuitBreaker** (`circuit_breaker.py`): System stability protection against cascade failures
- **Sentiment Analysis System** (`sentiment/`): Social media sentiment analysis for position sizing
  - **VaderSentimentAnalyzer**: Crypto-optimized sentiment scoring with 40+ specialized terms
  - **MultiSourceDataCollector**: Unified interface for Reddit, Discord, and other platforms
  - **SentimentCache**: File-based caching with deduplication and cleanup
  - **RedditCollector**: Monitors 9 major crypto subreddits for new coin discussions

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

Asset protection parameters (optional):
```
# Asset Protection Strategy (Manages 100% of designated asset holdings)
ASSET_PROTECTION_ENABLED=false           # Enable/disable asset protection
PROTECTED_ASSETS=BTC-EUR,ETH-EUR         # Assets to protect (comma-separated)
MAX_PROTECTION_BUDGET=100.0              # Maximum EUR for DCA operations only

# CRYPTO-OPTIMIZED LEVELS (v3.0 Upgrade Guide Implementation)
# Conservative settings for BTC/ETH - designed for crypto volatility
DCA_ENABLED=true                         # Enable DCA buying on dips
DCA_LEVELS=15:0.3,25:0.4,40:0.3         # Crypto-appropriate DCA levels
SWING_TRADING_ENABLED=false              # Coordinated swing levels (advanced users)
SWING_LEVELS=12:sell:0.15,18:sell:0.20,35:rebuy:0.40,50:rebuy:0.60

# UPGRADE GUIDE SAFETY FEATURES
# Position Size Controls (prevents over-exposure)
MAX_POSITION_MULTIPLIER=2.0              # Maximum 2x original position size
POSITION_SIZE_CHECK_ENABLED=true         # Enable position monitoring
# Loss Circuit Breaker (stops buying during crashes)
LOSS_CIRCUIT_BREAKER_PCT=25.0            # Stop buying at -25% loss (crypto-appropriate)
CIRCUIT_BREAKER_ENABLED=true             # Enable circuit breaker
# Smart DCA Timing (prevents "falling knife" purchases)
DIRECTIONAL_DCA_ENABLED=true             # Enable momentum-based DCA timing
DCA_MOMENTUM_HOURS=1                     # Hours to analyze momentum
DCA_FALLING_MULTIPLIER=0.5               # Reduce DCA when falling through level
DCA_BOUNCING_MULTIPLIER=1.5              # Increase DCA when bouncing off level
DCA_MOMENTUM_THRESHOLD=0.5               # Minimum momentum to trigger logic
# Recovery Rebuy System (solves "missed opportunity" problem)
RECOVERY_REBUY_ENABLED=true              # Enable recovery rebuys on bounces
MIN_RECOVERY_THRESHOLD_PCT=15.0          # Minimum drop to track for recovery
RECOVERY_BOUNCE_PCT=8.0                  # Bounce % to trigger rebuy
RECOVERY_REBUY_ALLOCATION=0.3            # Use 30% of available cash reserves

# Enhanced Trailing Profit System (Self-funding via profit sales)
ENHANCED_PROTECTION_ENABLED=true         # Enable trailing profits and dynamic buybacks
TRAILING_START_GAIN_PCT=12.0             # Start trailing after +12% gains (crypto-adjusted)
TRAILING_DISTANCE_PCT=8.0                # Trail 8% below highest price (crypto-adjusted)
TRAILING_INCREMENT_PCT=3.0               # Sell 3% of position per trigger (crypto-adjusted)
BUYBACK_TOLERANCE_PCT=5.0                # Buy within 5% of sell price (crypto-adjusted)
MIN_TRADE_VALUE_EUR=20.0                 # Minimum EUR value per trade

# Risk Management (crypto-appropriate levels)
BASE_STOP_LOSS_PCT=18.0                  # Base stop loss percentage (crypto-adjusted)
VOLATILITY_MULTIPLIER=1.5                # Volatility adjustment multiplier
EMERGENCY_STOP_LOSS_PCT=30.0             # Emergency stop loss (crypto-adjusted)
MAX_DAILY_TRADES=10                      # Maximum trades per day per asset

# Portfolio Management
REBALANCING_ENABLED=false                # Enable portfolio rebalancing
TARGET_ALLOCATIONS=BTC-EUR:0.6,ETH-EUR:0.4  # Target allocations

# Social Media Sentiment Analysis (Optional - enhances position sizing)
SENTIMENT_ENABLED=false                  # Enable sentiment-based position adjustment
SENTIMENT_INFLUENCE=0.5                  # How much sentiment affects position size (0.0-1.0)
MIN_SENTIMENT_CONFIDENCE=0.3             # Minimum confidence to use sentiment
MAX_POSITION_MULTIPLIER_SENTIMENT=1.5    # Maximum position increase from positive sentiment

# Reddit API credentials (required for sentiment analysis)
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_secret
REDDIT_USERNAME=your_reddit_username
REDDIT_PASSWORD=your_reddit_password

# Discord API credentials (optional for additional sentiment data)
DISCORD_BOT_TOKEN=your_discord_bot_token
```

## Core Architecture Patterns

### Configuration Management
The bot uses a sophisticated dataclass-based configuration system in `config.py` that:
- Validates all parameters at startup with range checking and format validation
- Supports multiple configuration modes (trading, API, asset protection, sentiment analysis)
- Uses environment variable override patterns with secure defaults
- The `load_config()` function returns a 5-tuple: `(trading_config, api_config, dip_config, asset_protection_config, sentiment_config)`

### Component Initialization Pattern
The `TradingBot` class follows a conditional initialization pattern where advanced features are only loaded if enabled:
- Core components (API, MarketTracker, TradeManager) are always initialized
- Advanced features (AssetProtectionManager, DipBuyManager, SentimentCollector) are conditionally imported and initialized
- Each optional component has fallback error handling that disables the feature on import failure
- Thread-safe shutdown coordination across all initialized components

### Thread Management Architecture
The bot uses a multi-threaded approach with clear separation of concerns:
- **Main thread**: New listing detection loop with interruptible sleep patterns
- **Trade monitoring threads**: One per active trade for trailing stop-loss monitoring  
- **Asset protection thread**: Separate thread for DCA/profit-taking operations (if enabled)
- **Sentiment analysis threads**: ThreadPoolExecutor for concurrent data collection
- All threads coordinate through shared state with proper locking mechanisms

### Error Handling Strategy
The codebase uses a layered error handling approach:
- **API level**: Retry logic with exponential backoff in `requests_handler.py`
- **Component level**: Graceful degradation when optional features fail to initialize
- **Trade level**: Comprehensive validation before executing any financial operation
- **System level**: Signal handlers for graceful shutdown with resource cleanup

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
./scripts/start_bot.sh
```

### Running the Simulator
```bash
# Interactive simulator with strategy testing
python scripts/run_simulation.py

# Quick simulator tests
python tests/test_simulator.py

# Simple functionality test  
python tests/test_simulator_simple.py

# Test Asset Protection Upgrades (v3.0 features)
python tests/test_asset_protection_upgrades.py

# Test social media sentiment analysis pipeline
python tests/test_social_media_pipeline.py

# Test Reddit API connection
python tests/test_reddit_connection.py

# Test VADER sentiment analyzer
python tests/test_vader_sentiment.py
```

### Testing
```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_config.py

# Run tests with verbose output
python -m pytest tests/ -v

# Run single test method
python -m pytest tests/test_config.py::test_load_config -v

# Run sentiment analysis integration tests
python test_sentiment_integration.py

# Run with coverage (if pytest-cov is installed)
python -m pytest tests/ --cov=src --cov-report=html
```

### Configuration Testing
```bash
# Test configuration loading without running the bot
python -c "from src.config import load_config; configs = load_config(); print('Config loaded successfully')"

# Validate environment variables
python -c "from src.config import load_config; trading, api, dip, protection, sentiment = load_config(); print(f'Sentiment enabled: {sentiment.enabled}')"

# Test specific API connection
python test_reddit_connection.py
```

### Development Debugging
```bash
# Run bot with debug logging
PYTHONPATH=src python src/main.py --log-level DEBUG

# Test sentiment analysis pipeline
python test_social_media_pipeline.py

# Validate specific configuration values
python -c "import os; from src.config import _validate_decimal_range; print(_validate_decimal_range(os.getenv('MAX_TRADE_AMOUNT', '10.0'), 'MAX_TRADE_AMOUNT', 1.0, 10000.0))"
```

## Dependencies

Key dependencies (see `requirements.txt`):
- `python-bitvavo-api>=1.2.3` - Official Bitvavo API client
- `python-dotenv>=1.0.0` - Environment variable management  
- `requests>=2.31.0` - HTTP library for API calls
- `urllib3>=2.0.0` - URL handling library
- `pytest>=7.4.0` - Testing framework
- `vaderSentiment>=3.3.2` - Sentiment analysis optimized for social media
- `praw>=7.8.0` - Python Reddit API Wrapper (PRAW) for Reddit data collection
- `discord.py>=2.6.0` - Discord bot library for Discord monitoring (optional)

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
- Sentiment analysis cache in `data/sentiment_cache/` (deduplication and performance)
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
- **Social Media Sentiment Analysis**: Position sizing adjustment based on Reddit community sentiment (optional)

### Advanced Features (Optional)

#### Enhanced Asset Protection Strategy (UPGRADED v3.0)
- **Recovery Rebuy System**: Solves "missed opportunity" problem by catching recoveries from ANY significant drop (≥15%) with 8% bounce trigger
- **Directional DCA**: Smart momentum-based timing reduces DCA when falling through levels (avoid falling knives), increases when bouncing off levels
- **Circuit Breaker Protection**: Stops all buying when losses exceed -25% to prevent cascade failures during crashes
- **Coordinated Strategy Levels**: Fixed swing levels (sell -12%/-18%, rebuy -35%/-50%) eliminate conflicts with DCA levels (-15%/-25%/-40%)
- **Position Size Controls**: Prevents over-exposure with maximum 2x position multiplier across all strategies
- **Crypto-Optimized Thresholds**: Volatility-appropriate levels designed for 15-40% crypto market moves
- **Enhanced Price Tracking**: 24-hour rolling price history with momentum calculation for intelligent decision-making
- **Multi-Asset Intelligence**: Individual tracking and coordination for each protected asset (BTC, ETH, etc.)

#### Legacy Asset Protection Features
- **Enhanced Trailing Profit Taking**: Gradual profit capture as prices rise (starts at +8%, sells 2% per 5% trailing)
- **Dynamic Buyback System**: Automatically buys back near recent sell levels to maintain position exposure
- **Trade Cost Optimization**: Minimum trade thresholds to avoid unnecessary fees (€20 minimum, 2% move threshold)
- **Complete Asset Management**: Manages 100% of designated asset holdings (specified in PROTECTED_ASSETS)
- **Self-Funding Operations**: Profit sales fund buybacks, separate DCA budget for major dips
- **Smart Position Maintenance**: Preserves exposure while capturing gains (solves "rigid level" problem)
- **Dynamic Volatility-Based Stop Losses**: Risk-adjusted stop losses based on market volatility
- **Multi-Level DCA Buying**: Automatically buy dips at configurable price thresholds using protection budget
- **Portfolio Rebalancing**: Maintain target asset allocations automatically
- **Emergency Stop Loss**: Hard limit protection against severe losses
- **Daily Budget Management**: Prevent excessive trading with daily limits

#### Dip Buying Strategy  
- **Post-Sale Monitoring**: Automatically rebuy assets after profitable sales when price drops
- **Multi-Level Dip Tracking**: Configure multiple price thresholds with different capital allocations
- **Market Condition Filtering**: Optional BTC trend analysis to gate rebuy decisions
- **Thread-Safe State Management**: Robust persistence with atomic operations and recovery

#### Social Media Sentiment Analysis (NEW)
- **Multi-Platform Data Collection**: Monitors Reddit (9 subreddits) and Discord channels for new coin discussions
- **VADER Sentiment Analysis**: Crypto-optimized with 40+ specialized terms (HODL, diamond hands, rugpull, moon, etc.)
- **Intelligent Position Sizing**: Adjusts trade amounts based on community sentiment and confidence levels
- **Spam and Pump Detection**: Filters obvious pump attempts, excessive emojis, and bot-generated content
- **Smart Caching System**: File-based deduplication prevents redundant API calls and analysis
- **Conservative Risk Management**: Maximum 1.5x position increase, requires high confidence scores
- **Zero-Cost Implementation**: Uses free Reddit API (100 requests/minute)

### Testing & Simulation
- **Historical Backtesting**: Test strategies against real historical price data
- **Mock API Simulation**: Safe testing environment with realistic market behavior
- **Performance Analysis**: Detailed P&L analysis and strategy optimization
- **Risk Assessment**: Comprehensive reporting on strategy effectiveness
- **Upgrade Guide Testing**: Dedicated simulator (`test_asset_protection_upgrades.py`) validates all v3.0 features
- **Scenario Validation**: Tests "missed opportunity" recovery, directional DCA, circuit breaker protection
- **Multi-Asset Simulation**: Concurrent BTC/ETH testing with realistic crypto volatility patterns

## Testing Architecture

The project includes comprehensive testing at multiple levels:

### Unit Tests (`tests/` directory)
- **Configuration validation** (`test_config.py`): Environment loading, parameter validation, dataclass construction
- **Market tracking** (`test_market_utils.py`): New listing detection logic, JSON persistence
- **API handling** (`test_requests_handler.py`): Rate limiting, retry logic, error handling
- **Trade execution** (`test_trade_logic.py`): Order placement, monitoring, threading
- **Asset protection** (`test_asset_protection.py`): 44 comprehensive tests covering DCA, profit taking, circuit breaker

### Integration Tests (root directory)
- **Sentiment pipeline** (`test_social_media_pipeline.py`): End-to-end sentiment analysis workflow
- **Reddit connectivity** (`test_reddit_connection.py`): API authentication and data collection
- **Sentiment integration** (`test_sentiment_integration.py`): Trading bot integration with sentiment analysis
- **Simulator validation** (`test_simulator.py`): Strategy backtesting and performance analysis

### Testing Configuration
The project uses pytest with configuration in `pytest.ini`:
- Test discovery in `tests/` directory with `src/` on Python path
- Verbose output and short tracebacks by default
- Follows standard pytest naming conventions

Run tests with `python -m pytest tests/ -v` for detailed output.

## Documentation

Additional documentation files provide specific guidance:
- `docs/QUICKSTART.md` - Step-by-step setup instructions
- `docs/SAFETY_CHECKLIST.md` - Pre-trading safety verification  
- `docs/FIRST_RUN_BEHAVIOR.md` - What to expect on first execution
- `docs/BITVAVO_API_UPDATE.md` - Recent API changes and requirements
- `docs/TERMINAL_OUTPUT_EXAMPLE.md` - Example of typical bot output
- `docs/SOCIAL_MEDIA_SENTIMENT_SETUP.md` - Complete sentiment analysis setup guide

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

### Recent v3.0 Upgrade Guide Implementation
- **Asset Protection Upgrades**: Comprehensive implementation of the Asset Protection Upgrade Guide
- **Recovery Rebuy System**: Solves "missed opportunity" problem - catches recoveries from any significant drop (≥15%)
- **Directional DCA**: Smart momentum-based timing prevents "falling knife" purchases
- **Circuit Breaker Protection**: Stops buying during severe crashes (-25% loss threshold)
- **Coordinated Strategy Levels**: Eliminates conflicting buy/sell at same price levels
- **Position Size Controls**: Prevents over-exposure with 2x position multiplier limits
- **Crypto-Optimized Levels**: Volatility-appropriate thresholds (15-40% moves vs 5-30%)
- **Enhanced Price Tracking**: 24-hour rolling price history with momentum calculation
- **Comprehensive Testing**: Full simulation suite validates all upgrade features

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