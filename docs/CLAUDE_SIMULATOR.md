# CLAUDE_SIMULATOR.md

This file provides guidance to Claude Code when working with the dip buying strategy simulator.

## Simulator Overview

The simulator provides a comprehensive testing environment for the dip buying strategy without risking real money. It uses realistic market data simulation with time acceleration to test trading strategies efficiently.

## Architecture

### Core Components

#### **MockBitvavoAPI** (`simulator/mock_api.py`)
- **Purpose**: Replaces real Bitvavo API during simulation
- **Key Classes**:
  - `MockBitvavoAPI`: Main API simulation class
  - `HistoricalDataManager`: Handles price data generation
- **Key Methods**:
  - `send_request()`: Simulates API calls (ticker/price, orders, balance)
  - `advance_time()`: Controls simulation time progression
  - `get_execution_summary()`: Returns trading activity summary
- **Data Generation**: Creates realistic price movements with configurable volatility
- **Order Simulation**: Executes trades with realistic slippage and fills

#### **SimulationEngine** (`simulator/simulation_engine.py`)
- **Purpose**: Main orchestration class for running simulations
- **Key Classes**:
  - `SimulationEngine`: Main simulation controller
  - `SimulationConfig`: Configuration for simulation parameters
  - `TradeEvent`: Individual trading event tracking
  - `SimulationResults`: Complete results with analytics
- **Key Methods**:
  - `run_simulation()`: Execute complete simulation workflow
  - `_simulate_initial_purchases()`: Simulate new listing purchases
  - `_simulate_price_movements_and_sales()`: Handle price changes and triggers
  - `_check_trailing_stops()`: Monitor for profitable sale triggers
  - `_simulate_dip_manager_check()`: Test dip buying opportunities

#### **ResultsAnalyzer** (`simulator/results_analyzer.py`)
- **Purpose**: Analyze and report simulation results
- **Key Classes**:
  - `ResultsAnalyzer`: Main analysis engine
  - `TradeAnalysis`: Individual trade performance analysis
- **Key Methods**:
  - `generate_summary_report()`: High-level performance summary
  - `analyze_trades_by_asset()`: Per-asset trading analysis
  - `calculate_performance_metrics()`: Advanced performance calculations
  - `generate_recommendations()`: Strategy optimization suggestions

## Configuration System

### SimulationConfig Parameters
```python
@dataclass
class SimulationConfig:
    start_time: datetime              # Simulation start timestamp
    end_time: datetime                # Simulation end timestamp
    initial_balance_eur: Decimal      # Starting EUR balance
    max_trade_amount: Decimal         # Per-trade amount limit
    simulation_speed: float           # Time acceleration multiplier
    assets_to_simulate: List[str]     # Assets to trade
    dip_buy_enabled: bool            # Enable/disable dip buying
    dip_levels: List[DipLevel]       # Dip buying thresholds
    monitoring_duration_hours: int   # Hours to monitor after sale
    cooldown_hours: int              # Cooldown between rebuys
    max_rebuys_per_asset: int        # Maximum rebuy attempts
```

### Common Configuration Patterns
```python
# Quick test (1 hour, fast)
SimulationConfig(
    start_time=datetime(2024, 1, 1, 9, 0),
    end_time=datetime(2024, 1, 1, 10, 0),
    simulation_speed=60.0,  # 1 hour = 1 minute
    assets_to_simulate=["TEST-EUR"]
)

# Strategy comparison (1 week, detailed)
SimulationConfig(
    start_time=datetime(2024, 1, 1, 9, 0),
    end_time=datetime(2024, 1, 7, 17, 0),
    simulation_speed=1440.0,  # 1 day = 1 minute
    assets_to_simulate=["PUMP-EUR", "DOGE-EUR", "ADA-EUR"]
)

# Parameter testing (shorter, focused)
SimulationConfig(
    start_time=datetime(2024, 1, 1, 9, 0),
    end_time=datetime(2024, 1, 3, 17, 0),
    simulation_speed=2880.0,  # 2 days = 1 minute
    dip_levels=[DipLevel(threshold_pct=Decimal('15'), capital_allocation=Decimal('1.0'))]
)
```

## Usage Patterns

### Testing Workflow
1. **Component Validation**: `python test_simulator_simple.py`
2. **Basic Simulation**: `python run_simulation.py` (option 1)
3. **Strategy Comparison**: `python run_simulation.py` (option 2)
4. **Parameter Testing**: `python run_simulation.py` (option 3)
5. **Results Analysis**: `python simulator/results_analyzer.py`

### Integration with Real Strategy
- Uses actual `DipBuyManager` from `future_work/dip_buy_manager.py`
- Same decision logic as live trading (`DipEvaluator`)
- Identical configuration system (`DipBuyConfig`, `DipLevel`)
- Real state persistence patterns (`DipStateManager`)

## Data Flow

### Simulation Execution Flow
```
1. SimulationEngine.run_simulation()
   ├── Initialize MockBitvavoAPI
   ├── Create DipBuyManager with mock API
   ├── _simulate_initial_purchases() 
   ├── _simulate_price_movements_and_sales()
   │   ├── _check_trailing_stops()
   │   └── _simulate_dip_manager_check()
   ├── _calculate_results()
   └── _save_results()

2. MockBitvavoAPI.send_request()
   ├── /ticker/price → _handle_ticker_price()
   ├── /order → _handle_order_placement()
   └── /balance → _handle_balance_request()

3. ResultsAnalyzer.generate_summary_report()
   ├── analyze_trades_by_asset()
   ├── calculate_performance_metrics()
   └── generate_recommendations()
```

### State Management
- **Trade Events**: All buy/sell actions recorded with timestamps
- **Portfolio Tracking**: Real-time balance and position tracking
- **Dip State**: Uses actual `DipStateManager` for realistic behavior
- **Results Persistence**: JSON format in `simulator/results/`

## Price Simulation

### Price Generation Algorithm
```python
# In MockBitvavoAPI._generate_realistic_price_data()
def generate_price_movement():
    # Base prices per market
    base_prices = {
        "BTC-EUR": Decimal("45000"),
        "PUMP-EUR": Decimal("0.000045"),  # Meme coin
        "DOGE-EUR": Decimal("0.08")
    }
    
    # Volatility by asset type
    if "PUMP" in market or "DOGE" in market:
        volatility = 0.05  # 5% swings for meme coins
    elif "BTC" in market or "ETH" in market:
        volatility = 0.02  # 2% swings for major coins
    else:
        volatility = 0.03  # 3% swings for altcoins
    
    # Random walk with realistic patterns
    change_pct = random.uniform(-volatility, volatility)
    new_price = current_price * (1 + change_pct)
```

### Time-Based Patterns
- **Deterministic Variation**: Same timestamp always generates same price
- **Daily Cycles**: Price patterns based on time of day
- **Realistic Ranges**: Prices stay within reasonable bounds
- **Volume Simulation**: Realistic volume patterns for different assets

## Testing Scenarios

### Standard Test Configurations

#### **Conservative Strategy**
```python
dip_levels=[DipLevel(threshold_pct=Decimal('15'), capital_allocation=Decimal('1.0'))]
```
- Single deep dip entry
- Lower risk, fewer opportunities
- Good for stable market conditions

#### **Aggressive Strategy**
```python
dip_levels=[
    DipLevel(threshold_pct=Decimal('5'), capital_allocation=Decimal('0.5')),
    DipLevel(threshold_pct=Decimal('10'), capital_allocation=Decimal('0.3')),
    DipLevel(threshold_pct=Decimal('20'), capital_allocation=Decimal('0.2'))
]
```
- Early entry on small dips
- Higher frequency trading
- Good for volatile markets

#### **Balanced Strategy** (Default)
```python
dip_levels=[
    DipLevel(threshold_pct=Decimal('10'), capital_allocation=Decimal('0.4')),
    DipLevel(threshold_pct=Decimal('20'), capital_allocation=Decimal('0.35')),
    DipLevel(threshold_pct=Decimal('35'), capital_allocation=Decimal('0.25'))
]
```
- Multiple entry points
- Balanced risk/reward
- Good for most conditions

### Market Condition Testing
- **Bull Market**: Rising trend, test dip effectiveness
- **Bear Market**: Falling trend, test risk management  
- **Volatile Market**: High swings, test rapid responses
- **Stable Market**: Low volatility, test opportunity detection

## Performance Analysis

### Key Metrics
```python
# Basic Performance
total_return_pct: float           # Overall return percentage
total_trades: int                 # Number of buy/sell transactions
successful_rebuys: int           # Dip rebuys executed
rebuy_success_rate: float        # % of dip opportunities captured

# Advanced Metrics
avg_buy_amount: float            # Average purchase amount
avg_sell_amount: float           # Average sale amount
trading_duration_hours: float    # Total active trading time
trades_per_hour: float           # Trading frequency
capital_efficiency: float        # Return per euro of capital
```

### Analysis Patterns
- **Trade-by-Trade**: Individual asset performance analysis
- **Time Series**: Performance over simulation period
- **Dip Level Analysis**: Which thresholds trigger most often
- **Risk Assessment**: Drawdown and volatility metrics

## Integration Points

### With Real Trading Bot
- **Configuration Compatibility**: Same config classes and parameters
- **Code Reuse**: Actual dip buying implementation used
- **State Format**: Compatible with real persistence files
- **API Interface**: Drop-in replacement for BitvavoAPI

### Development Workflow
1. **Strategy Development**: Test new features in simulator first
2. **Parameter Tuning**: Optimize settings with simulations
3. **Risk Assessment**: Understand potential losses before live trading
4. **Performance Validation**: Prove strategy effectiveness

## Common Issues and Solutions

### Performance Issues
```python
# Issue: Simulation too slow
# Solution: Reduce time range or increase simulation_speed
config.simulation_speed = 2880.0  # 2 days per minute
config.end_time = start_time + timedelta(days=3)  # Shorter period

# Issue: Not enough trading activity
# Solution: Use more volatile assets or shorter time steps
config.assets_to_simulate = ["PUMP-EUR", "DOGE-EUR"]  # Volatile meme coins
```

### Data Issues
```python
# Issue: Unrealistic results
# Solution: Adjust price volatility in mock_api.py
volatility = 0.02  # Reduce from 0.05 for more realistic swings

# Issue: No dip opportunities
# Solution: Ensure sufficient price movement range
time_range = config.end_time - config.start_time
assert time_range >= timedelta(hours=6)  # Minimum for dip patterns
```

### Configuration Issues
```python
# Issue: Dip levels never trigger
# Solution: Align thresholds with expected volatility
if asset_type == "meme_coin":
    dip_levels = [DipLevel(threshold_pct=Decimal('10'), capital_allocation=Decimal('1.0'))]
else:
    dip_levels = [DipLevel(threshold_pct=Decimal('5'), capital_allocation=Decimal('1.0'))]
```

## Testing Best Practices

### Simulation Design
- **Start Small**: Test with short time periods first
- **Single Variable**: Change one parameter at a time
- **Control Group**: Always compare with baseline (no dip buying)
- **Multiple Runs**: Test same scenario multiple times for consistency

### Result Interpretation
- **Statistical Significance**: Look for consistent patterns across runs
- **Risk-Adjusted Returns**: Consider volatility, not just raw returns
- **Market Conditions**: Understand what conditions favor the strategy
- **Edge Cases**: Test extreme scenarios (crashes, pump events)

### Validation Steps
1. **Unit Tests**: `test_simulator_simple.py` passes
2. **Integration Tests**: Full simulation completes without errors
3. **Logic Validation**: Results make intuitive sense
4. **Parameter Sensitivity**: Small changes produce reasonable result variations
5. **Benchmark Comparison**: Performance vs buy-and-hold or no-dip strategies

## Extension Points

### Adding New Analysis
```python
# In ResultsAnalyzer, add new metrics
def calculate_sharpe_ratio(self) -> float:
    returns = [event.profit_loss for event in self.trade_events]
    return mean(returns) / std(returns) if std(returns) > 0 else 0

def calculate_max_drawdown(self) -> Decimal:
    portfolio_values = self._calculate_portfolio_over_time()
    peak = portfolio_values[0]
    max_dd = Decimal('0')
    for value in portfolio_values:
        if value > peak:
            peak = value
        drawdown = (peak - value) / peak
        max_dd = max(max_dd, drawdown)
    return max_dd
```

### Adding New Simulation Modes
```python
# In run_simulation.py, add new test scenarios
def run_stress_test():
    """Test strategy under extreme market conditions."""
    config = SimulationConfig(
        # Extreme volatility settings
        simulation_speed=7200.0,  # Very fast
        assets_to_simulate=["VOLATILE-EUR"],
        # Custom price generation with higher swings
    )

def run_correlation_test():
    """Test strategy with correlated asset movements."""
    # Multiple assets with coordinated price movements
```

### Adding Real Historical Data
```python
# In mock_api.py, replace price generation
def load_historical_data(self, market: str, start: datetime, end: datetime):
    """Load real historical data from CSV files."""
    csv_file = f"data/historical/{market}_{start.strftime('%Y%m%d')}.csv"
    return pd.read_csv(csv_file)  # Real price data

def _get_real_price_at_time(self, market: str, timestamp: datetime):
    """Use actual historical prices instead of generated ones."""
    historical_data = self.load_historical_data(market, timestamp, timestamp)
    return historical_data.loc[timestamp, 'close']
```

The simulator provides a complete, realistic testing environment that allows safe experimentation with dip buying strategies before risking real capital. Use it extensively to build confidence in your approach and optimize parameters for your specific trading style.