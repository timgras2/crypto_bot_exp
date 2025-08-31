# Dip Buy Strategy Implementation

## Overview
Successfully implemented a sophisticated "dip buying" feature that automatically re-purchases assets after they've been sold via trailing stop-loss, capitalizing on price recovery opportunities.

## 🎯 Key Features Implemented

### **1. Tiered Dip Buying System**
- **Multi-level capital allocation** with configurable thresholds
- **Default levels**: 40% at -10%, 35% at -20%, 25% at -35%
- **Independent execution** - each dip level triggers separately
- **Configurable thresholds** via environment variables

### **2. Smart Decision Engine** 
- **Central evaluation logic** in `DipEvaluator` class
- **Cooldown management** - prevents rapid successive trades
- **Retry limits** - maximum attempts per asset and per level
- **Market context filtering** (optional BTC trend checking)

### **3. Feature Toggle Architecture**
- **Master switch**: `DIP_BUY_ENABLED=false` by default
- **Zero impact when disabled** - original bot behavior unchanged
- **Hot-swappable** - can enable/disable without code changes
- **Safe rollback** options at multiple levels

### **4. State Persistence**
- **Cross-restart recovery** - maintains dip tracking after bot restarts
- **Structured data format** in `data/dip_tracking.json`
- **Automatic cleanup** of expired monitoring windows
- **Thread-safe operations** with proper locking

### **5. Risk Management**
- **Capital limits** - respects existing max trade amounts
- **Cooldown periods** - configurable delays between rebuys
- **Maximum attempts** - prevents excessive trading per asset
- **Monitoring windows** - automatic expiration of tracking

## 📁 File Structure

```
crypto_bot_main/
├── src/
│   ├── config.py                    # Extended with DipBuyConfig
│   ├── main.py                      # Integrated dip manager initialization
│   └── trade_logic.py               # Added dip manager notifications
├── future_work/
│   ├── dip_buy_manager.py          # Main orchestration class
│   ├── dip_evaluator.py            # Central decision engine
│   ├── dip_state.py                # State persistence management
│   └── market_filter.py            # Optional market context checking
├── data/
│   └── dip_tracking.json           # Dip monitoring state (auto-created)
└── .env.example                    # Extended with dip buy parameters
```

## 🔧 Configuration

### **Environment Variables**
```bash
# Master toggle (disabled by default)
DIP_BUY_ENABLED=false

# Monitoring parameters
DIP_MONITORING_HOURS=48           # How long to monitor after sale
DIP_COOLDOWN_HOURS=4              # Cooldown between rebuys
DIP_MAX_REBUYS_PER_ASSET=3        # Maximum attempts per asset

# Optional features  
DIP_USE_MARKET_FILTER=false       # Enable BTC trend filtering

# Dip levels (format: threshold:allocation,threshold:allocation,...)
DIP_LEVELS=10:0.4,20:0.35,35:0.25  # Default: 3 levels
```

### **Custom Dip Levels Examples**
```bash
# Conservative: Single level at -15% 
DIP_LEVELS=15:1.0

# Aggressive: More levels with smaller allocations
DIP_LEVELS=5:0.3,10:0.3,15:0.2,25:0.2

# Balanced: Two levels
DIP_LEVELS=12:0.6,25:0.4
```

## 🔄 Integration Points

### **TradeManager Integration**
- **Notification system**: Triggers dip tracking on trailing stop sales
- **Zero interference**: No changes to existing trade logic
- **Optional connection**: Works with or without dip manager

### **Main Bot Loop**
- **Conditional initialization**: Only loads dip components when enabled
- **Graceful fallback**: Continues working if dip modules unavailable
- **Clean shutdown**: Properly stops dip monitoring service

## 🛡️ Safety Features

### **Isolation & Rollback**
1. **Instant disable**: Set `DIP_BUY_ENABLED=false`
2. **Branch isolation**: Implemented on `feature/dip-buy-strategy` branch
3. **Code removal**: Delete `future_work/dip_*.py` files
4. **Git revert**: `git checkout main` for complete rollback

### **Risk Controls**
- **Capital limits**: Uses existing `MAX_TRADE_AMOUNT` limits
- **Input validation**: Comprehensive parameter validation
- **Error handling**: Graceful degradation on failures
- **Logging**: Detailed activity tracking

## 🚀 How to Enable

1. **Set environment variable**:
   ```bash
   DIP_BUY_ENABLED=true
   ```

2. **Optional: Customize levels** (or use defaults):
   ```bash
   DIP_LEVELS=10:0.4,20:0.35,35:0.25
   ```

3. **Start bot normally**:
   ```bash
   python src/main.py
   ```

4. **Verify activation**:
   Look for "Dip buying: ENABLED" in startup output

## 📊 Expected Behavior

### **When Asset is Sold (Trailing Stop)**
1. Bot records profitable sale
2. Adds asset to dip monitoring
3. Displays dip thresholds and target amounts
4. Begins price monitoring for 48 hours (default)

### **When Dip Detected**
1. Evaluates if conditions are met (threshold, cooldown, limits)
2. Places market buy order if appropriate
3. Sets cooldown period for the asset
4. Continues monitoring for remaining levels

### **User Feedback**
```
🎯 Added PUMP-EUR to dip tracking (sold at €0.12345)
📊 PUMP-EUR Level 1: €0.11111 (-10%) → €4.00
📊 PUMP-EUR Level 2: €0.09876 (-20%) → €3.50
📊 PUMP-EUR Level 3: €0.08024 (-35%) → €2.50

🛒 DIP REBUY: PUMP-EUR at €0.11050 (Level 1 triggered: 10.5% drop)
✅ DIP REBUY SUCCESS: PUMP-EUR €4.00 at €0.11050
```

## 🧪 Testing Status

✅ **All integration tests passing**
- Configuration loading and parsing
- Feature toggle functionality
- Dip evaluation decision logic
- Component integration and status reporting
- Integration with existing codebase

## 📈 Benefits

1. **Automated Recovery**: Capitalizes on post-sale price drops automatically
2. **Risk-Controlled**: Multiple safeguards prevent excessive trading
3. **Non-Intrusive**: Operates independently of existing trading logic
4. **Configurable**: All parameters tunable via environment variables
5. **Persistent**: Maintains state across bot restarts
6. **Safe**: Easy rollback options and disabled by default

## 🔮 Future Enhancements (Not Implemented)

- Web dashboard for monitoring dip opportunities
- More sophisticated market filters (RSI, volume analysis)
- Performance analytics and backtesting
- Position sizing based on profit from original trade
- Dynamic dip levels based on market conditions

## ✅ Implementation Complete

The dip buying feature is fully implemented, tested, and ready for use. It provides a sophisticated yet safe way to automatically rebuy assets at advantageous prices after profitable sales, with comprehensive risk management and easy rollback options.