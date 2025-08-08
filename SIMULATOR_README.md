# Dip Buy Strategy Simulator

## Overview

This simulator allows you to test the dip buying strategy with realistic market data **without risking real money**. It uses your actual dip buying implementation but replaces the live API with historical data simulation.

## 🎯 What It Does

✅ **Simulates Real Trading**: Uses your actual DipBuyManager and decision logic  
✅ **Realistic Price Data**: Generates market-like price movements  
✅ **Time Acceleration**: Run weeks of trading in minutes  
✅ **Comprehensive Analytics**: Detailed performance reports  
✅ **Strategy Comparison**: Test with/without dip buying  
✅ **Parameter Testing**: Optimize dip levels and settings  

## 🚀 Quick Start

### 1. **Test the Simulator**
```bash
python test_simulator.py
```

### 2. **Run Basic Simulation**
```bash
python run_simulation.py
# Choose option 1 for basic simulation
```

### 3. **Analyze Results**
```bash
python simulator/results_analyzer.py
```

## 📊 Simulation Types

### **1. Basic Simulation**
- Tests default dip buying parameters
- 1 week simulation period
- 3-4 test assets
- Good for initial validation

### **2. Strategy Comparison**
- Compares WITH vs WITHOUT dip buying
- Shows exact performance difference
- Proves if strategy adds value
- 2 week simulation period

### **3. Parameter Testing**
- Tests different dip level configurations
- Conservative vs Aggressive vs Patient strategies
- Helps optimize your settings
- Shorter simulation for faster results

## 🔧 Configuration Options

### **Simulation Parameters**
```python
SimulationConfig(
    start_time=datetime(2024, 1, 1, 9, 0),     # Simulation start
    end_time=datetime(2024, 1, 7, 17, 0),      # Simulation end
    initial_balance_eur=Decimal("1000"),        # Starting balance
    max_trade_amount=Decimal("10"),             # Per-trade amount
    simulation_speed=1440.0,                    # Time acceleration (1440x = 1 day/minute)
    assets_to_simulate=["PUMP-EUR", "DOGE-EUR"] # Which assets to trade
)
```

### **Dip Buying Parameters**
```python
# Conservative (single level)
dip_levels=[DipLevel(threshold_pct=Decimal('15'), capital_allocation=Decimal('1.0'))]

# Default (3 levels)
dip_levels=[
    DipLevel(threshold_pct=Decimal('10'), capital_allocation=Decimal('0.4')),
    DipLevel(threshold_pct=Decimal('20'), capital_allocation=Decimal('0.35')),
    DipLevel(threshold_pct=Decimal('35'), capital_allocation=Decimal('0.25'))
]

# Aggressive (early entry)
dip_levels=[
    DipLevel(threshold_pct=Decimal('5'), capital_allocation=Decimal('0.5')),
    DipLevel(threshold_pct=Decimal('10'), capital_allocation=Decimal('0.3')),
    DipLevel(threshold_pct=Decimal('20'), capital_allocation=Decimal('0.2'))
]
```

## 📈 Understanding Results

### **Key Metrics**
- **Total P&L**: Profit/loss in EUR and percentage
- **Total Trades**: Number of buy/sell transactions
- **Successful Dip Rebuys**: How many dip opportunities were captured
- **Success Rate**: Percentage of dip opportunities that triggered rebuys
- **Rebuys by Level**: Which dip thresholds triggered most often

### **Trade Events**
- **initial_buy**: Simulated new listing purchases
- **trailing_stop_sell**: Profitable sales that trigger dip monitoring
- **dip_rebuy**: Automatic rebuys when price drops sufficiently

### **Performance Analysis**
```
📊 COMPARISON RESULTS:
Metric                    With Dip Buy    Without Dip Buy   Difference
Total P&L (EUR)                 +45.23              +12.34       +32.89
P&L Percentage                   +4.5%               +1.2%        +3.3%
Total Trades                        18                  12           +6
Dip Rebuys                           6                   0           +6

✅ Dip buying strategy improved returns by €32.89!
```

## 🧪 Testing Scenarios

### **1. Bull Market Test**
Test during rising market conditions where dip buying should excel.

### **2. Bear Market Test** 
Test during falling market to see if dip buying adds risk.

### **3. Volatile Market Test**
Test in highly volatile conditions with frequent dips.

### **4. Parameter Sensitivity**
Test how sensitive results are to different dip thresholds.

## 📁 File Structure

```
simulator/
├── __init__.py                 # Package initialization
├── mock_api.py                 # Mock Bitvavo API with realistic data
├── simulation_engine.py        # Main simulation logic
└── results_analyzer.py         # Results analysis and reporting

simulator/results/              # Generated results (auto-created)
├── simulation_results_*.json   # Raw simulation data
└── analysis_*.txt             # Analysis reports

run_simulation.py              # Main simulation runner
test_simulator.py              # Validation tests
```

## 🔍 How It Works

### **1. Mock API Layer**
- Replaces real Bitvavo API calls
- Generates realistic price movements
- Simulates order execution with slippage
- Tracks portfolio state

### **2. Time Acceleration**
- Fast-forwards through time periods
- Maintains realistic price relationships
- Preserves trading logic timing

### **3. Real Strategy Code**
- Uses your actual `DipBuyManager`
- Same decision logic as live trading
- Identical risk management rules

### **4. Comprehensive Tracking**
- Records every trade event
- Tracks portfolio changes
- Measures performance metrics

## 💡 Tips for Effective Testing

### **Start Small**
- Test with short time periods first
- Use small trade amounts initially
- Verify results make sense

### **Compare Scenarios**
- Always test WITH and WITHOUT dip buying
- Try different market conditions
- Test various parameter settings

### **Analyze Thoroughly**
- Read the detailed trade reports
- Understand which dip levels trigger most
- Look for patterns in successful rebuys

### **Iterate and Optimize**
- Use results to tune your parameters
- Test multiple configurations
- Find the sweet spot for your risk tolerance

## ⚠️ Important Notes

### **Simulation Limitations**
- **Price data is simulated** (not real historical data)
- **Market conditions are simplified** (no external factors)
- **Slippage is minimal** (real trading has more)
- **No API failures** (real trading has connectivity issues)

### **What This Tests**
✅ **Strategy logic correctness**  
✅ **Parameter sensitivity**  
✅ **Risk management effectiveness**  
✅ **Performance under different scenarios**  

### **What This Doesn't Test**
❌ **Real market conditions**  
❌ **API reliability**  
❌ **Execution timing issues**  
❌ **External market factors**  

### **Before Live Trading**
1. ✅ Run extensive simulations
2. ✅ Test various scenarios  
3. ✅ Understand the risks
4. ✅ Start with small amounts
5. ✅ Monitor performance closely

## 🚀 Next Steps

### **After Successful Simulation**
1. **Analyze Results**: Understand what worked and what didn't
2. **Optimize Parameters**: Fine-tune dip levels based on results
3. **Test Edge Cases**: Try extreme market conditions
4. **Validate with Small Amounts**: Start live trading with minimal risk
5. **Scale Gradually**: Increase position sizes as confidence grows

## 🔧 Customization

### **Adding New Assets**
Modify `assets_to_simulate` in your simulation config:
```python
assets_to_simulate=["BTC-EUR", "ETH-EUR", "ADA-EUR", "DOT-EUR"]
```

### **Custom Price Models**
Edit `_generate_realistic_price_data()` in `mock_api.py` to use:
- Real historical data from CSV files
- More sophisticated price models
- Actual market correlation patterns

### **Advanced Analytics**
Extend `results_analyzer.py` to add:
- Risk-adjusted returns (Sharpe ratio)
- Maximum drawdown analysis
- Win/loss ratio calculations
- Time-based performance patterns

The simulator provides a safe, controlled environment to thoroughly test and optimize your dip buying strategy before risking real capital. Use it extensively to build confidence in your approach! 🎯