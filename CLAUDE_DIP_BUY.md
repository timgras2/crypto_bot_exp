# CLAUDE_DIP_BUY.md

This file provides guidance to Claude Code when working with the dip buying strategy feature.

## Dip Buy Strategy Overview

This branch (`feature/dip-buy-strategy`) implements an advanced dip buying strategy that automatically re-purchases assets after profitable sales when their price drops significantly.

## Architecture

### Core Components

#### **Configuration System** (`src/config.py`)
- `DipBuyConfig`: Main configuration dataclass with feature toggle
- `DipLevel`: Individual dip level configuration (threshold + allocation)
- `_parse_dip_levels()`: Parses environment variable format "10:0.4,20:0.35,35:0.25"
- `_load_dip_config()`: Loads dip configuration from environment variables

#### **Decision Engine** (`future_work/dip_evaluator.py`)
- `DipEvaluator`: Central decision logic for rebuy opportunities
- `RebuyDecision`: Decision result dataclass
- `AssetSaleInfo`: Information about completed asset sales
- **Input validation** for all price data, market names, and asset states
- **Bounds checking** for array access to prevent IndexError crashes
- Key method: `should_rebuy()` - evaluates all conditions for rebuy

#### **State Management** (`future_work/dip_state.py`)
- `DipStateManager`: Handles persistence in `data/dip_tracking.json`
- **Thread-safe operations** with file locking and atomic writes
- **Retry logic** with exponential backoff for file system operations
- **Automatic cleanup** of expired entries and corruption recovery
- **State validation** with graceful handling of missing or invalid data

#### **Market Context** (`future_work/market_filter.py`)
- `MarketFilter`: Optional BTC trend checking to gate rebuys
- Simple implementation: blocks rebuys if BTC drops >15% in 24h
- Caches BTC price for 5 minutes to reduce API calls

#### **Main Orchestration** (`future_work/dip_buy_manager.py`)
- `DipBuyManager`: Main service class that coordinates all components
- **Configurable API integration** with trading_config.operator_id
- **Thread-safe monitoring** loop in separate thread
- **Comprehensive validation** of market names, prices, and API responses
- **Order execution** with failure recovery and exponential backoff
- **Bitvavo API compliance** with proper balance queries (no "100%" amounts)

### Integration Points

#### **TradeManager** (`src/trade_logic.py`)
- Added `_dip_manager` optional reference
- Added `set_dip_manager()` method for connection
- Modified `record_completed_trade()` to notify dip manager on trailing stops
- Zero impact when dip manager is None

#### **Main Bot** (`src/main.py`)
- Conditional initialization based on `dip_config.enabled`
- Graceful fallback if dip modules can't be imported
- Proper shutdown sequence (stops dip manager before trade manager)
- Status display shows dip buying enabled/disabled and levels

## Configuration Reference

### Environment Variables

```bash
# Master toggle (REQUIRED to enable)
DIP_BUY_ENABLED=false             # Default: disabled

# Timing parameters
DIP_MONITORING_HOURS=48           # How long to monitor for dips after sale
DIP_COOLDOWN_HOURS=4              # Cooldown between rebuys per asset  
DIP_MAX_REBUYS_PER_ASSET=3        # Maximum rebuy attempts per asset

# Market filtering (optional)
DIP_USE_MARKET_FILTER=false       # Enable BTC trend filtering

# Dip levels configuration
DIP_LEVELS=10:0.4,20:0.35,35:0.25  # threshold_pct:capital_allocation
```

### Dip Levels Format
- Format: `"threshold1:allocation1,threshold2:allocation2,..."`
- Threshold: Percentage drop from sell price to trigger rebuy
- Allocation: Portion of max_trade_amount to use (0.0-1.0)
- Example: `"15:0.6,30:0.4"` = 60% capital at -15%, 40% at -30%
- Total allocation should not exceed 1.0 (100%)

## Data Persistence

### Dip Tracking State (`data/dip_tracking.json`)
```json
{
  "ASSET-EUR": {
    "sell_price": "0.12345",
    "sell_timestamp": "2025-01-15T10:30:00",
    "trigger_reason": "trailing_stop",
    "monitoring_expires": "2025-01-17T10:30:00",
    "completed_rebuys": [
      {
        "level": 1,
        "buy_price": "0.11000", 
        "amount_eur": "4.0",
        "timestamp": "2025-01-15T12:00:00"
      }
    ],
    "levels": {
      "1": {"status": "completed", "retry_count": 0, "next_retry_at": null},
      "2": {"status": "pending", "retry_count": 1, "next_retry_at": "2025-01-15T13:00:00"}
    },
    "next_asset_cooldown": "2025-01-15T16:00:00",
    "created_at": "2025-01-15T10:30:05"
  }
}
```

## State Machine

### Asset Lifecycle
1. **Asset Sold** (trailing stop) → Added to tracking
2. **Price Monitoring** → Check every `check_interval` seconds  
3. **Dip Detected** → Evaluate rebuy conditions
4. **Rebuy Executed** → Set cooldown, continue monitoring other levels
5. **Monitoring Expires** → Remove from tracking (after 48h default)

### Level States
- `waiting`: Level threshold not yet reached
- `pending`: Threshold reached, ready for execution
- `attempting`: Rebuy order being placed
- `completed`: Successfully executed rebuy
- `failed`: Failed after max retries

## Safety & Rollback

### Isolation Strategy
- **Feature branch**: All changes on `feature/dip-buy-strategy`
- **Feature toggle**: Master switch prevents any activity when disabled
- **Import protection**: Graceful fallback if dip modules unavailable
- **Path isolation**: All new code in `future_work/` directory

### Rollback Options (Ordered by speed)
1. **Environment toggle**: `DIP_BUY_ENABLED=false` (immediate)
2. **Branch switch**: `git checkout main` (10 seconds)
3. **File removal**: Delete `future_work/dip_*.py` (30 seconds)
4. **Code revert**: Restore original files from git

## Testing & Validation

### Integration Points to Test
- Configuration loading with various DIP_LEVELS formats
- DipEvaluator decision logic with different market conditions
- DipBuyManager initialization and status reporting
- TradeManager notification system
- Graceful handling when feature is disabled

### Common Issues
- **Import errors**: Check Python path includes project root
- **Unicode errors**: Windows terminal encoding issues with emojis
- **State corruption**: Invalid JSON in dip_tracking.json
- **API limits**: Respect existing rate limiting in requests_handler

## Development Guidelines

### Adding New Features
- Extend `DipBuyConfig` for new parameters
- Add validation in `_load_dip_config()`
- Update `.env.example` with new variables
- Maintain backward compatibility with existing state format

### Modifying Decision Logic
- Changes should be made in `DipEvaluator.should_rebuy()`
- Consider impact on existing tracked assets
- Test edge cases (expired monitoring, max retries reached)
- Log decision rationale for debugging

### State Format Changes
- Increment state version if breaking changes needed
- Add migration logic in `DipStateManager.load_state()`
- Backup existing state before applying changes
- Test with various state corruption scenarios

## Performance Considerations

### Threading
- One monitoring thread per DipBuyManager instance
- Thread-safe operations with `_lock` for shared state
- Interruptible sleep patterns for responsive shutdown
- Automatic cleanup of threads on service stop

### API Usage
- Reuses existing BitvavoAPI wrapper and rate limiting
- BTC price cached for 5 minutes in MarketFilter
- Price checks only for assets actively being monitored
- Respects existing retry logic and backoff patterns

### Memory Usage
- State automatically cleaned up (expired entries removed)
- Limited by `DIP_MAX_REBUYS_PER_ASSET` setting
- JSON persistence prevents memory growth across restarts

## Recent Bug Fixes & Improvements (v2.0)

### Critical Fixes Applied
1. **Thread Safety** - Implemented atomic file writes with temporary files and retry logic
2. **API Compliance** - Fixed Bitvavo API compatibility (removed invalid "100%" amounts)
3. **Input Validation** - Added comprehensive validation for all price data and state
4. **Configuration** - Replaced hardcoded operatorId with configurable value
5. **Error Handling** - Added bounds checking and graceful failure recovery
6. **Python Compatibility** - Fixed type hints for Python 3.8+ compatibility

### Validation Improvements
- **Price Validation**: All prices checked for positive values
- **Market Names**: Validated for non-empty strings
- **State Structure**: Missing keys auto-initialized with safe defaults
- **Decimal Conversion**: Protected against invalid numeric formats
- **File Operations**: Retry logic with exponential backoff

### Performance Enhancements
- **Atomic Writes**: Prevent state corruption during file operations
- **Balance Tracking**: Proper calculation of available crypto holdings
- **Error Recovery**: Automatic backup of corrupted state files
- **Memory Management**: Efficient cleanup of expired tracking data

## Debugging

### Key Log Messages
- `"Dip buy manager initialized and connected"` - Integration successful
- `"Added {market} to dip tracking"` - New asset being monitored
- `"Dip rebuy opportunity: {market}"` - Rebuy conditions met
- `"Successfully executed dip rebuy"` - Order completed
- `"Dip rebuy failed"` - Order execution failed
- `"Invalid price data for {market}"` - Validation error (new)
- `"Moved corrupted dip tracking file to backup"` - Recovery action (new)

### Validation Error Messages
- `"Invalid current price for {market}"` - Price validation failed
- `"Missing or empty market name"` - Market name validation
- `"Invalid level number: {level}"` - Bounds checking triggered
- `"Missing key '{key}' in asset state"` - Auto-initialization triggered

### Common Debug Steps
1. Check `DIP_BUY_ENABLED` setting
2. Verify dip manager initialization in logs
3. Examine `data/dip_tracking.json` for asset state
4. Check API credentials and connectivity
5. Verify sufficient account balance for rebuy amounts
6. **New**: Check for validation warnings in logs
7. **New**: Verify backup files if state corruption detected

## System Robustness

### Error Recovery Features
- **Automatic State Recovery**: Corrupted JSON files automatically backed up and reset
- **Graceful Degradation**: Invalid data handled without crashes
- **Retry Logic**: File operations retry with exponential backoff
- **Input Sanitization**: All external data validated before processing

### Production Readiness
This implementation is now **production-ready** with:
- ✅ Thread-safe operations
- ✅ Comprehensive error handling
- ✅ API compliance verification
- ✅ Input validation coverage
- ✅ Graceful failure recovery
- ✅ Performance optimizations

The system handles edge cases gracefully and provides detailed logging for debugging any issues that may arise.