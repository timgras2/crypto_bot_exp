# Crypto Trading Bot Configuration Guide

This guide explains all the configuration options available in the `.env` file for the cryptocurrency trading bot.

## 📋 Quick Start

1. Copy `.env.example` to `.env`
2. Fill in your API credentials
3. Start with small amounts for testing (`MAX_TRADE_AMOUNT=5.0`)
4. Gradually enable advanced features as you become comfortable

## ⚠️ Safety First

**IMPORTANT: Always start with small amounts for testing!**
- Begin with `MAX_TRADE_AMOUNT=5.0` or lower
- Test all features in a safe environment first
- Never risk more than you can afford to lose
- Monitor the bot closely during initial runs

## 🔑 Required API Configuration

### Bitvavo API
Get your credentials from the Bitvavo Pro interface:
- `BITVAVO_API_KEY`: Your API key
- `BITVAVO_API_SECRET`: Your API secret
- `BITVAVO_BASE_URL`: Always use `https://api.bitvavo.com/v2`

## 🎯 Core Trading Settings

- `MIN_PROFIT_PCT`: Stop loss percentage (e.g., 5.0 = sell at 5% loss)
- `TRAILING_PCT`: Trailing stop percentage (locks in profits as price rises)
- `MAX_TRADE_AMOUNT`: EUR per trade - **START SMALL for testing!**
- `CHECK_INTERVAL`: Seconds between market scans
- `MAX_RETRIES`: API retry attempts on failure
- `RETRY_DELAY`: Seconds between retry attempts
- `RATE_LIMIT`: API requests per minute (300 recommended)
- `API_TIMEOUT`: API request timeout in seconds
- `OPERATOR_ID`: Required by Bitvavo API (use 1001)

## 🛡️ Asset Protection System

Advanced portfolio management for protecting existing holdings (BTC, ETH, etc.).

### Master Controls
- `ASSET_PROTECTION_ENABLED`: Set to `true` to enable the system
- `PROTECTED_ASSETS`: Comma-separated list (e.g., `BTC-EUR,ETH-EUR`)
- `MAX_PROTECTION_BUDGET`: Maximum EUR for DCA operations per day

### Configuration Presets

Choose based on your risk tolerance:

#### Conservative (Recommended for beginners)
Suitable for mature assets like BTC and ETH:
```
DCA_LEVELS=15:0.3,25:0.4,40:0.3
LOSS_CIRCUIT_BREAKER_PCT=25.0
```

#### Aggressive (For experienced users)
More frequent trading with higher volatility tolerance:
```
DCA_LEVELS=10:0.3,20:0.4,35:0.3
LOSS_CIRCUIT_BREAKER_PCT=20.0
```

#### Altcoin (Very high volatility)
For altcoin portfolios with extreme volatility:
```
DCA_LEVELS=20:0.3,35:0.4,55:0.3
LOSS_CIRCUIT_BREAKER_PCT=35.0
```

### DCA (Dollar Cost Averaging)
- `DCA_ENABLED`: Enable automatic buying on price dips
- `DCA_LEVELS`: Format: `drop_percentage:allocation,drop_percentage:allocation`
  - Example: `15:0.3,25:0.4,40:0.3` means:
    - Buy with 30% of budget at -15% drop
    - Buy with 40% of budget at -25% drop  
    - Buy with 30% of budget at -40% drop

### Swing Trading (Advanced)
- `SWING_TRADING_ENABLED`: Enable coordinated sell/rebuy levels
- `SWING_LEVELS`: Format: `percentage:action:allocation`
- `SWING_CASH_RESERVE_PCT`: Percentage of proceeds kept for rebuying

## 🚨 Intelligent Safety Features

### Position Size Protection
- `MAX_POSITION_MULTIPLIER`: Maximum position size growth (2.0 = 200% of original)
- `POSITION_SIZE_CHECK_ENABLED`: Enable position monitoring
- `CIRCUIT_BREAKER_ENABLED`: Enable loss-based buying halt

### Smart DCA Timing
Prevents "falling knife" purchases by analyzing price momentum:
- `DIRECTIONAL_DCA_ENABLED`: Enable momentum-based timing
- `DCA_MOMENTUM_HOURS`: Hours to analyze price momentum
- `DCA_FALLING_MULTIPLIER`: Reduce DCA when falling (0.5 = 50% reduction)
- `DCA_BOUNCING_MULTIPLIER`: Increase DCA when bouncing (1.5 = 50% increase)
- `DCA_MOMENTUM_THRESHOLD`: Minimum momentum percentage to trigger

### Recovery Rebuy System
Solves the "missed opportunity" problem by catching recoveries:
- `RECOVERY_REBUY_ENABLED`: Enable recovery buying on bounces
- `MIN_RECOVERY_THRESHOLD_PCT`: Minimum drop to track (15% recommended)
- `RECOVERY_BOUNCE_PCT`: Bounce percentage to trigger rebuy (8% recommended)
- `RECOVERY_REBUY_ALLOCATION`: Percentage of reserves to use (0.3 = 30%)

**Example:** Asset drops to -27%, then bounces +8% from the low → recovery rebuy triggered

## 📈 Profit Management

### Basic Profit Taking
- `PROFIT_TAKING_ENABLED`: Enable automatic profit taking
- `PROFIT_TAKING_LEVELS`: Format: `gain_percentage:sell_percentage`
  - Example: `25:0.25,50:0.5` = sell 25% at +25% gain, 50% at +50% gain

### Enhanced Protection (Advanced)
- `ENHANCED_PROTECTION_ENABLED`: Enable trailing profits and dynamic buybacks
- `TRAILING_START_GAIN_PCT`: Start trailing after this gain percentage
- `TRAILING_DISTANCE_PCT`: Trail this percentage below highest price
- `TRAILING_INCREMENT_PCT`: Sell this percentage per trigger
- `BUYBACK_TOLERANCE_PCT`: Buy back within this percentage of sell price
- `MIN_TRADE_VALUE_EUR`: Minimum trade size to avoid fees

## 🚀 Risk Management

### Daily Limits
- `MAX_DAILY_TRADES`: Maximum trades per day per asset
- `EMERGENCY_STOP_LOSS_PCT`: Hard stop loss limit

### Volatility-Based Stop Loss
- `BASE_STOP_LOSS_PCT`: Base stop loss percentage
- `VOLATILITY_WINDOW_HOURS`: Hours for volatility calculation
- `VOLATILITY_MULTIPLIER`: Volatility adjustment factor

## 📊 Portfolio Rebalancing (Advanced)

- `REBALANCING_ENABLED`: Enable automatic rebalancing
- `REBALANCING_THRESHOLD_PCT`: Rebalance when allocation drifts beyond this
- `TARGET_ALLOCATIONS`: Format: `ASSET:percentage,ASSET:percentage`

## 🎯 Dip Buying for New Listings

- `DIP_BUY_ENABLED`: Enable post-sale dip buying
- `DIP_MONITORING_HOURS`: Hours to monitor after profitable sale
- `DIP_COOLDOWN_HOURS`: Hours between rebuys per asset
- `DIP_MAX_REBUYS_PER_ASSET`: Maximum rebuy attempts
- `DIP_USE_MARKET_FILTER`: Enable BTC trend filtering
- `DIP_LEVELS`: Dip buy levels (same format as DCA_LEVELS)

## 🧠 Social Media Sentiment Analysis

Enhances trading decisions with community sentiment from Reddit, Discord, and Telegram.

### Core Settings
- `SENTIMENT_ENABLED`: Master toggle for sentiment analysis
- `SENTIMENT_INFLUENCE`: How much sentiment affects decisions (0.0-1.0)
- `MIN_SENTIMENT_CONFIDENCE`: Minimum confidence to use sentiment
- `MAX_POSITION_MULTIPLIER_SENTIMENT`: Max position increase from positive sentiment
- `SENTIMENT_CACHE_HOURS`: Hours to cache sentiment data
- `SPAM_DETECTION_ENABLED`: Enable spam/pump detection
- `MIN_MENTIONS_FOR_ANALYSIS`: Minimum mentions needed for analysis

### API Configurations

#### Reddit (Recommended - FREE!)
Get credentials at: https://www.reddit.com/prefs/apps/
- `REDDIT_CLIENT_ID`: Your Reddit app client ID
- `REDDIT_CLIENT_SECRET`: Your Reddit app secret
- `REDDIT_USERNAME`: Your Reddit username
- `REDDIT_PASSWORD`: Your Reddit password

#### Discord (Optional - Advanced Users)
Create bot at: https://discord.com/developers/applications
- `DISCORD_BOT_TOKEN`: Your Discord bot token

#### Telegram (Optional - Advanced Users)
Get API credentials at: https://my.telegram.org/
- `TELEGRAM_API_ID`: Your Telegram API ID
- `TELEGRAM_API_HASH`: Your Telegram API hash
- `TELEGRAM_PHONE_NUMBER`: Your phone number

### API Cost Information

✅ **FREE APIS (RECOMMENDED):**
- Reddit: 100 requests/minute - perfect for crypto sentiment
- Discord: Unlimited - great for community monitoring  
- Telegram: Free with rate limits - excellent for crypto channels

❌ **EXPENSIVE APIS (NOT RECOMMENDED):**
- X (Twitter): $200/month minimum - too expensive for our use case

## 💡 Key Improvements in Latest Version

### ✅ Fixed Conflicting Strategies
- **Old:** Swing sell at -10% AND DCA buy at -10% = amplified losses
- **New:** Coordinated levels that don't conflict

### ✅ Smart Momentum Analysis
- Reduces DCA when falling through levels (avoid falling knives)
- Increases DCA when bouncing off levels (catch recoveries)

### ✅ Crypto-Appropriate Volatility
- Levels adjusted for crypto market reality (15-40% moves are normal)
- Higher circuit breaker thresholds (25-35% vs 15%)
- Wider swing levels (12-50% vs 5-30%)

### ✅ Position Size Protection
- Prevents excessive position growth from multiple strategies
- Circuit breaker stops buying during severe crashes

### ✅ Enhanced Safety
- Trend analysis delays rebuys during confirmed downtrends
- Multiple layers of risk management and position control

### ✅ Recovery Rebuy System
- Solves "missed opportunity" problem (e.g., BTC drops to -27%, recovers before -30%)
- Tracks lowest price during any significant drop (>15%)
- Triggers rebuy on 8% bounce from the low (catches recoveries)
- Uses swing cash reserves, respects position limits

## 🚨 Important Notes

### Security
- Never commit your `.env` file to version control
- Keep your API credentials secure
- Use environment variables only for sensitive data

### Testing
- Always test with small amounts first
- Monitor bot behavior closely during initial runs
- Use the simulator (`python run_simulation.py`) to test strategies

### Monitoring
- Check logs regularly (`logs/trading.log`)
- Review trade performance with `python scripts/review_trades.py`
- Monitor portfolio with existing tools

## 📞 Support

- Check the main `CLAUDE.md` file for additional documentation
- Review specific feature guides (e.g., `CLAUDE_ASSET_PROTECTION.md`)
- Test configurations with the simulator before live trading