# CLAUDE_ASSET_PROTECTION.md

This document provides comprehensive guidance on the Asset Protection Strategy feature for protecting existing cryptocurrency holdings from volatile market swings.

## Overview

The Asset Protection Strategy is designed to:
- **Minimize losses** during market downturns with dynamic stop-losses
- **Maximize profit potential** by buying dips and taking profits on pumps  
- **Maintain portfolio balance** through automated rebalancing
- **Provide system stability** with circuit breaker protection

## Architecture

### Core Components

#### 1. **AssetProtectionManager** (`src/asset_protection_manager.py`)
Main orchestration class responsible for:
- Monitoring protected assets for trading opportunities
- Executing dynamic stop-loss orders based on volatility
- Implementing DCA buying on significant dips
- Managing profit taking on significant pumps
- Coordinating portfolio rebalancing
- Integrating with circuit breaker systems

#### 2. **VolatilityCalculator** (`src/volatility_calculator.py`)
Dynamic risk assessment component:
- Calculates asset volatility over configurable time windows
- Provides volatility-adjusted stop-loss percentages
- Implements caching for performance optimization
- Validates statistical significance of calculations

#### 3. **ProtectedAssetStateManager** (`src/protected_asset_state.py`)
Thread-safe state management:
- Persists protected asset information
- Tracks trade history and P&L
- Manages DCA and profit-taking level completion
- Provides atomic file operations with backup/recovery
- Generates portfolio summaries and analytics

#### 4. **CircuitBreaker** (`src/circuit_breaker.py`)
System stability protection:
- Prevents cascade failures during API outages
- Configurable failure thresholds and recovery timeouts
- Specialized circuit breakers for different operation types
- Comprehensive status monitoring and reporting

## Configuration

### Environment Variables

Add these variables to your `.env` file to configure asset protection:

```bash
# Master Feature Toggle
ASSET_PROTECTION_ENABLED=true

# Protected Assets (comma-separated list)
PROTECTED_ASSETS=BTC-EUR,ETH-EUR,ADA-EUR

# Budget Management
MAX_PROTECTION_BUDGET=100.0              # Maximum EUR for protection operations
MAX_DAILY_TRADES=10                      # Maximum trades per day per asset

# Dynamic Stop Loss Configuration
BASE_STOP_LOSS_PCT=15.0                  # Base stop loss percentage
VOLATILITY_WINDOW_HOURS=24               # Hours for volatility calculation
VOLATILITY_MULTIPLIER=1.5                # Volatility adjustment factor
EMERGENCY_STOP_LOSS_PCT=25.0             # Emergency stop loss threshold

# DCA (Dollar Cost Averaging) Configuration
DCA_ENABLED=true
DCA_LEVELS=10:0.3,20:0.4,30:0.3         # Format: threshold_pct:capital_allocation

# Profit Taking Configuration  
PROFIT_TAKING_ENABLED=true
PROFIT_TAKING_LEVELS=20:0.25,40:0.5     # Format: threshold_pct:position_allocation

# Portfolio Rebalancing (Optional)
REBALANCING_ENABLED=false
REBALANCING_THRESHOLD_PCT=10.0           # Trigger rebalancing when drift >10%
TARGET_ALLOCATIONS=BTC-EUR:0.6,ETH-EUR:0.4  # Target portfolio allocations
POSITION_SIZE_LIMIT_PCT=50.0             # Max percentage of budget per asset
```

### Configuration Examples

#### Conservative Strategy
```bash
PROTECTED_ASSETS=BTC-EUR,ETH-EUR
BASE_STOP_LOSS_PCT=10.0
DCA_LEVELS=15:0.5,25:0.5
PROFIT_TAKING_LEVELS=15:0.3,30:0.7
MAX_DAILY_TRADES=5
```

#### Aggressive Strategy
```bash
PROTECTED_ASSETS=BTC-EUR,ETH-EUR,ADA-EUR,DOT-EUR
BASE_STOP_LOSS_PCT=20.0
DCA_LEVELS=5:0.2,10:0.3,20:0.5
PROFIT_TAKING_LEVELS=10:0.2,25:0.3,50:0.5
MAX_DAILY_TRADES=15
```

#### Balanced Strategy (Recommended)
```bash
PROTECTED_ASSETS=BTC-EUR,ETH-EUR
BASE_STOP_LOSS_PCT=15.0
DCA_LEVELS=10:0.3,20:0.4,30:0.3
PROFIT_TAKING_LEVELS=20:0.25,40:0.5
REBALANCING_ENABLED=true
TARGET_ALLOCATIONS=BTC-EUR:0.6,ETH-EUR:0.4
MAX_DAILY_TRADES=10
```

## Key Features

### 1. Dynamic Volatility-Based Stop Losses

The system calculates asset volatility over a configurable time window and adjusts stop-loss percentages accordingly:

- **Low volatility** → Tighter stop losses
- **High volatility** → Wider stop losses to avoid premature exits

**Formula:**
```
Adjusted Stop Loss = Base Stop Loss × (1 + Volatility × Multiplier)
```

### 2. Multi-Level DCA (Dollar Cost Averaging)

Automatically buys more of an asset as its price drops from the entry point:

**Configuration Format:** `threshold_pct:capital_allocation`

**Example:** `DCA_LEVELS=10:0.3,20:0.4,30:0.3`
- At 10% drop: Use 30% of protection budget
- At 20% drop: Use 40% of protection budget  
- At 30% drop: Use 30% of protection budget

### 3. Profit Taking on Price Pumps

Sells portions of positions as prices increase from entry point:

**Configuration Format:** `threshold_pct:position_allocation`

**Example:** `PROFIT_TAKING_LEVELS=20:0.25,40:0.5`
- At 20% gain: Sell 25% of position
- At 40% gain: Sell 50% of remaining position

### 4. Portfolio Rebalancing

Maintains target asset allocations by automatically buying/selling to restore balance:

**Example:** With `TARGET_ALLOCATIONS=BTC-EUR:0.6,ETH-EUR:0.4`
- If BTC allocation drifts to 70%, system will sell some BTC and buy ETH
- Triggered when allocation drift exceeds `REBALANCING_THRESHOLD_PCT`

### 5. Circuit Breaker Protection

Three specialized circuit breakers protect system stability:

- **API Operations**: 5 failures → 5-minute recovery
- **Trading Operations**: 3 failures → 10-minute recovery  
- **Balance Operations**: 4 failures → 3-minute recovery

## Usage Guide

### First-Time Setup

1. **Configure Environment**:
```bash
cp .env.example .env
# Edit .env with your asset protection settings
```

2. **Validate Configuration**:
```bash
python -c "from src.config import load_config; print('✅ Configuration valid')"
```

3. **Run Tests**:
```bash
python -m pytest tests/test_asset_protection*.py -v
```

### Starting Asset Protection

The asset protection manager integrates with the main bot:

```bash
python start_bot.py
```

**Console Output Example:**
```
🛡️  Asset protection: ENABLED
🔒 Protected assets: BTC-EUR, ETH-EUR
💰 Protection budget: €100.0
📊 DCA levels: -10%, -20%, -30%
💸 Profit levels: +20%, +40%
```

### Monitoring Operations

#### Real-Time Status
```bash
# Asset protection status is included in bot output
🕐 12:30:45 | ✅ Bot running | 🛡️ 2 protected assets | 💰 €25/€100 budget used
```

#### Log Monitoring
```bash
tail -f logs/trading.log | grep "AssetProtection"
```

### Manual Intervention

#### Adding New Protected Assets

1. **Stop the bot** (Ctrl+C)
2. **Update `.env`**:
```bash
PROTECTED_ASSETS=BTC-EUR,ETH-EUR,NEW-ASSET-EUR
```
3. **Restart the bot**

#### Adjusting Protection Levels

1. **Update configuration** in `.env`
2. **Restart bot** for changes to take effect

#### Emergency Stop

Force stop all asset protection:
```bash
# Set in .env
ASSET_PROTECTION_ENABLED=false
```

## Data Persistence

### Protected Asset State

Stored in `data/protected_asset_state.json`:

```json
{
  "BTC-EUR": {
    "entry_price": "45000.0",
    "initial_investment_eur": "90.0",
    "current_position_eur": "85.5",
    "current_stop_loss_pct": "17.5",
    "completed_dca_levels": [1],
    "completed_profit_levels": [],
    "trade_history": [
      {
        "timestamp": "2025-01-09T10:30:00",
        "trade_type": "dca_buy",
        "price": "40500.0",
        "amount_eur": "30.0",
        "amount_crypto": "0.00074074",
        "reason": "DCA level 1: 10.0% drop"
      }
    ]
  }
}
```

### Backup and Recovery

The system automatically:
- **Creates backups** before state updates
- **Recovers from corruption** using backup files
- **Persists state** across bot restarts
- **Maintains audit trail** of all operations

## Testing

### Unit Tests (44 tests)

```bash
python -m pytest tests/test_asset_protection.py -v
```

**Test Categories:**
- Configuration parsing and validation
- Volatility calculations
- State management operations
- Asset protection manager functionality

### Integration Tests (11 tests)

```bash
python -m pytest tests/test_asset_protection_integration.py -v
```

**Test Scenarios:**
- Complete initialization workflow
- DCA buying workflow
- Profit taking workflow
- Emergency stop loss workflow
- Circuit breaker integration
- Concurrent operations
- Error recovery

### Manual Testing

#### Simulate Market Conditions

Use the simulator to test asset protection strategies:

```bash
python run_simulation.py
```

Select "Asset Protection Strategy Testing" mode.

## Troubleshooting

### Common Issues

#### 1. Asset Protection Not Starting

**Symptoms:** No protection messages in console output

**Solutions:**
- Check `ASSET_PROTECTION_ENABLED=true` in `.env`
- Verify `PROTECTED_ASSETS` is configured
- Ensure assets have existing balances

#### 2. DCA Orders Not Executing

**Symptoms:** Price drops but no DCA purchases

**Solutions:**
- Check daily budget: `MAX_PROTECTION_BUDGET`
- Verify DCA levels haven't been completed
- Check `MAX_DAILY_TRADES` limit
- Monitor circuit breaker status

#### 3. Circuit Breaker Activated

**Symptoms:** "🚨 CIRCUIT BREAKER: API_Operations protection activated"

**Solutions:**
- Wait for automatic recovery (5-10 minutes)
- Check internet connection
- Verify Bitvavo API status
- Manual reset: restart bot

#### 4. Profit Taking Not Working

**Symptoms:** Prices increase but no profit taking

**Solutions:**
- Verify `PROFIT_TAKING_ENABLED=true`
- Check profit levels configuration
- Ensure sufficient position size
- Monitor trade history logs

### Debug Mode

Enable detailed logging:

```python
import logging
logging.getLogger('src.asset_protection_manager').setLevel(logging.DEBUG)
```

### Performance Monitoring

#### Key Metrics to Monitor

1. **Budget Utilization**
```
Daily spent: €45/€100 (45%)
```

2. **Circuit Breaker Status**
```
API: CLOSED (0 failures)
Trading: CLOSED (0 failures)  
Balance: CLOSED (0 failures)
```

3. **Asset Performance**
```
BTC-EUR: +2.5% (€2.25 unrealized)
ETH-EUR: -1.2% (€1.08 unrealized)
```

## Advanced Usage

### Custom Volatility Windows

Adjust volatility calculation periods:

```bash
# Short-term reactive (more sensitive)
VOLATILITY_WINDOW_HOURS=6

# Long-term stable (less sensitive)  
VOLATILITY_WINDOW_HOURS=72
```

### Dynamic Rebalancing

Set up automatic portfolio rebalancing:

```bash
REBALANCING_ENABLED=true
REBALANCING_THRESHOLD_PCT=5.0     # Rebalance on 5% drift
TARGET_ALLOCATIONS=BTC-EUR:0.5,ETH-EUR:0.3,ADA-EUR:0.2
```

### Integration with Dip Buying

Both strategies can run simultaneously:

```bash
# Both enabled
DIP_BUY_ENABLED=true              # For new listing profits
ASSET_PROTECTION_ENABLED=true     # For existing holdings
```

## Security Considerations

### Budget Protection

- **Daily limits** prevent excessive trading
- **Position size limits** prevent overexposure
- **Circuit breakers** prevent cascade failures
- **Emergency stops** provide hard limits

### Input Validation

- **Regex patterns** validate market formats
- **Range checking** prevents invalid percentages
- **Currency validation** warns about uncommon pairs
- **Allocation validation** ensures totals don't exceed 100%

### Thread Safety

- **Atomic operations** prevent race conditions
- **Proper locking** protects shared state
- **Budget rollback** on failed operations
- **State recovery** from corruption

## Performance Optimization

### Caching Strategy

- **Volatility calculations** cached for 1 hour
- **Price data** cached for API efficiency
- **State persistence** optimized with atomic writes

### API Rate Limiting

- **Circuit breakers** prevent API abuse
- **Request queuing** respects rate limits
- **Retry logic** handles temporary failures

## Future Enhancements

### Planned Features

1. **Advanced Analytics Dashboard**
2. **Machine Learning Risk Models**
3. **Cross-Exchange Asset Protection**
4. **Options-Based Hedging**
5. **Telegram/Discord Notifications**

### Contributing

To contribute improvements:

1. **Add comprehensive tests** for new features
2. **Follow existing code patterns** and style
3. **Update documentation** with examples
4. **Ensure thread safety** for all operations

## Support and Maintenance

### Regular Maintenance

- **Monitor circuit breaker status** daily
- **Review trade history** weekly
- **Adjust volatility settings** based on market conditions
- **Rebalance manually** if automatic rebalancing is disabled

### Backup Procedures

The system automatically backs up state files, but consider:

- **Regular `.env` backups**
- **Trade history exports**
- **Configuration documentation**

---

For additional support, consult:
- Main documentation: `CLAUDE.md`
- Dip buying strategy: `CLAUDE_DIP_BUY.md`
- Simulation guide: `CLAUDE_SIMULATOR.md`