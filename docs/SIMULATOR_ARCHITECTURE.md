# Trading Strategy Simulator - Architecture Guide

## Overview

The simulator provides a comprehensive testing environment for trading strategies using real historical price data. It enables safe backtesting of strategies without risking real capital or hitting API limits.

## Core Components

### 1. SimulationEngine (`simulator/simulation_engine.py`)
- **Purpose**: Main orchestrator for running simulations
- **Key Features**:
  - Configurable time periods and simulation speed
  - Multi-asset trading simulation
  - Integration with dip buying strategy
  - Progress tracking and event logging
  - Performance analytics

### 2. MockBitvavoAPI (`simulator/mock_api.py`)
- **Purpose**: Realistic simulation of Bitvavo API responses
- **Features**:
  - Historical price data integration
  - Order execution simulation with slippage
  - Balance tracking with proper accounting
  - Thread-safe operations with retry logic
  - **Fixed**: Proper balance calculations (no more hardcoded amounts)
  - **Fixed**: Bitvavo API compliance (no "100%" amounts)

### 3. ResultsAnalyzer (`simulator/results_analyzer.py`)
- **Purpose**: Comprehensive analysis and reporting of simulation results
- **Features**:
  - P&L calculation and performance metrics
  - Trade analysis and success rates
  - Strategy effectiveness evaluation
  - Detailed reporting with recommendations
  - **Fixed**: UTF-8 file writing for Unicode characters

## Recent Improvements (v2.0)

### Critical Bug Fixes
1. **Balance Tracking**: Fixed simulator to properly track crypto holdings instead of using hardcoded values
2. **API Compliance**: Removed invalid "100%" amount parameter, now uses actual balance calculations
3. **Decimal Handling**: Added comprehensive error handling for decimal conversions
4. **Thread Safety**: Improved concurrent access to shared state
5. **Unicode Support**: Fixed encoding issues on Windows systems

### Performance Enhancements
- **Realistic Slippage**: 0.1-0.5% simulated market impact
- **Proper P&L Calculation**: Now shows realistic results (e.g., -0.3% vs previous -99%+ losses)
- **Memory Optimization**: Efficient data handling for long simulations
- **Error Recovery**: Graceful handling of invalid data

## Simulation Configuration

### Basic Parameters
```python
config = SimulationConfig(
    start_time=datetime(2024, 1, 1, 9, 0, 0),
    end_time=datetime(2024, 1, 7, 17, 0, 0),
    initial_balance_eur=Decimal("1000"),
    max_trade_amount=Decimal("10"),
    simulation_speed=1440.0,  # 1440x = 1 week in ~7 minutes
    assets_to_simulate=["PUMP-EUR", "DOGE-EUR", "ADA-EUR"]
)
```

### Dip Buying Strategy Parameters
```python
dip_config = DipBuyConfig(
    enabled=True,
    monitoring_duration_hours=48,
    cooldown_hours=4,
    max_rebuys_per_asset=3,
    dip_levels=[
        DipLevel(threshold_pct=Decimal('10'), capital_allocation=Decimal('0.4')),
        DipLevel(threshold_pct=Decimal('20'), capital_allocation=Decimal('0.35')),
        DipLevel(threshold_pct=Decimal('35'), capital_allocation=Decimal('0.25'))
    ]
)
```

## Running Simulations

### Interactive Mode
```bash
python run_simulation.py
```
- Choose from predefined simulation types
- Configure parameters interactively
- Real-time progress display
- Automatic result analysis

### Programmatic Usage
```python
from simulator.simulation_engine import SimulationEngine
from src.config import DipLevel

engine = SimulationEngine(config)
results = engine.run_simulation()
print(f"Final P&L: {results['final_pnl']}")
```

### Testing Framework
```bash
# Comprehensive tests
python test_simulator.py

# Quick validation
python test_simulator_simple.py
```

## Data Management

### Historical Price Data (`simulator/data/`)
- Real price data from multiple cryptocurrency exchanges
- Organized by asset and time period
- Efficient lookup with datetime indexing
- Automatic fallback for missing data points

### Results Storage (`simulator/results/`)
- JSON format for detailed trade data
- Text reports with human-readable analysis
- Automatic timestamping for result tracking
- Performance metrics and recommendations

### Temporary Data (`simulator/temp_data/`)
- Simulation state persistence
- Dip tracking during simulations
- Automatic cleanup after completion

## Performance Metrics

### Key Indicators
- **Total P&L**: Overall profit/loss in EUR
- **ROI Percentage**: Return on initial investment
- **Trade Success Rate**: Percentage of profitable trades
- **Dip Rebuy Effectiveness**: Success rate of dip buying strategy
- **Risk Metrics**: Maximum drawdown, volatility measures

### Reporting Features
- **Trade Journal**: Detailed log of all trading decisions
- **Performance Charts**: Visual representation of P&L over time
- **Strategy Analysis**: Effectiveness of different dip levels
- **Risk Assessment**: Comprehensive risk evaluation

## Integration Points

### Main Trading Bot
- Uses identical configuration system
- Same API wrapper and rate limiting
- Compatible with all trading logic
- Shared state management patterns

### Dip Buying Strategy
- Full integration with dip buying components
- Real-time monitoring simulation
- Multi-level rebuy testing
- Market condition filtering

## Best Practices

### Simulation Setup
1. Use realistic time periods (1-4 weeks)
2. Configure appropriate simulation speed
3. Set realistic initial balance and trade amounts
4. Choose representative asset selection

### Strategy Testing
1. Test multiple market conditions
2. Validate with different time periods
3. Compare strategies side-by-side
4. Analyze edge cases and failure modes

### Result Interpretation
1. Focus on risk-adjusted returns
2. Consider transaction costs in real trading
3. Validate assumptions with live trading
4. Monitor for overfitting to historical data

## Development Guidelines

### Adding New Strategies
1. Extend `SimulationConfig` for new parameters
2. Implement strategy logic in separate modules
3. Integrate with `SimulationEngine.run_simulation()`
4. Add corresponding test cases

### Performance Optimization
1. Use efficient data structures for price lookups
2. Minimize object creation in tight loops
3. Consider memory usage for long simulations
4. Profile critical code paths

### Testing Strategy
1. Unit tests for individual components
2. Integration tests for complete simulations
3. Performance benchmarks for optimization
4. Edge case validation for robustness

This simulator provides a robust foundation for strategy development and backtesting, with comprehensive error handling and realistic market simulation capabilities.