# Dynamic Rebuy Mechanism - Implementation Guide

## 📋 Overview

The Dynamic Rebuy Mechanism solves the "missed opportunity" problem in trading systems where assets recover before hitting predefined rebuy levels. Instead of waiting for fixed percentage drops (e.g., -30%, -50%), this system dynamically tracks any significant drop and triggers rebuys on meaningful recoveries.

## 🎯 Problem Solved

**Before**: BTC drops -27%, recovers before hitting -30% swing level → No rebuy happens → Missed opportunity
**After**: BTC drops -27%, bounces +8% from low → Dynamic rebuy triggered → Opportunity captured

## 🏗️ Core Components

### 1. Price Tracking System
```python
@dataclass
class PricePoint:
    """Price point with timestamp for tracking."""
    price: Decimal
    timestamp: datetime

# Add to your asset state
lowest_price_since_entry: Optional[Decimal] = None
recovery_rebuy_completed: bool = False
```

### 2. Configuration Parameters
```python
@dataclass
class DynamicRebuyConfig:
    """Configuration for dynamic rebuy system."""
    enabled: bool = True
    min_recovery_threshold_pct: Decimal = Decimal('15.0')  # Minimum drop to track
    recovery_bounce_pct: Decimal = Decimal('8.0')          # Bounce % to trigger rebuy
    recovery_rebuy_allocation: Decimal = Decimal('0.3')    # Portion of cash to use
```

### 3. Environment Variables
```bash
# Dynamic Recovery Rebuy System
RECOVERY_REBUY_ENABLED=true               # Master toggle
MIN_RECOVERY_THRESHOLD_PCT=15.0           # Minimum drop required (15%)
RECOVERY_BOUNCE_PCT=8.0                   # Bounce % from low (8%)
RECOVERY_REBUY_ALLOCATION=0.3             # Use 30% of available cash
```

## 🔧 Implementation Steps

### Step 1: Add Price Tracking
```python
def update_lowest_price_tracking(self, asset: str, current_price: Decimal):
    """Track lowest price since entry for recovery detection."""
    asset_info = self.get_asset_info(asset)
    
    # Initialize on first run
    if asset_info.lowest_price_since_entry is None:
        asset_info.lowest_price_since_entry = current_price
        return
    
    # Update if new low
    if current_price < asset_info.lowest_price_since_entry:
        asset_info.lowest_price_since_entry = current_price
        # Reset recovery flag on new lows
        asset_info.recovery_rebuy_completed = False
        print(f"📉 New low: {asset} at {current_price}")
```

### Step 2: Recovery Detection Logic
```python
def check_recovery_rebuy_opportunity(self, asset: str, current_price: Decimal):
    """Check if recovery rebuy should trigger."""
    asset_info = self.get_asset_info(asset)
    
    # Skip if already completed this cycle
    if asset_info.recovery_rebuy_completed:
        return False
    
    # Skip if no tracking data
    if not asset_info.lowest_price_since_entry:
        return False
    
    # Calculate drop from entry to lowest
    entry_price = asset_info.entry_price
    lowest_price = asset_info.lowest_price_since_entry
    drop_pct = ((entry_price - lowest_price) / entry_price) * 100
    
    # Only track significant drops
    if drop_pct < self.config.min_recovery_threshold_pct:
        return False
    
    # Calculate bounce from lowest price
    bounce_pct = ((current_price - lowest_price) / lowest_price) * 100
    
    # Trigger on sufficient bounce
    if bounce_pct >= self.config.recovery_bounce_pct:
        print(f"🚀 Recovery rebuy triggered: {asset}")
        print(f"   Drop: {drop_pct:.1f}% to {lowest_price}")
        print(f"   Bounce: {bounce_pct:.1f}% to {current_price}")
        return True
    
    return False
```

### Step 3: Rebuy Execution
```python
def execute_recovery_rebuy(self, asset: str, current_price: Decimal):
    """Execute the recovery rebuy order."""
    
    # Calculate rebuy amount
    available_cash = self.get_available_cash(asset)
    rebuy_amount = available_cash * self.config.recovery_rebuy_allocation
    
    if rebuy_amount < self.min_trade_amount:
        print(f"⚠️ Recovery rebuy too small: {rebuy_amount}")
        return False
    
    # Check position size limits (optional safety)
    if not self.check_position_limits(asset, rebuy_amount):
        print(f"⚠️ Recovery rebuy exceeds position limits")
        return False
    
    # Place buy order
    success = self.place_buy_order(asset, rebuy_amount)
    
    if success:
        # Mark as completed for this cycle
        self.mark_recovery_rebuy_completed(asset)
        
        # Log the trade
        drop_pct = self.calculate_drop_from_entry(asset)
        bounce_pct = self.calculate_bounce_from_low(asset, current_price)
        
        self.log_trade(
            asset=asset,
            trade_type="recovery_rebuy",
            price=current_price,
            amount=rebuy_amount,
            reason=f"Recovery: {bounce_pct:.1f}% bounce from {drop_pct:.1f}% drop"
        )
        
        print(f"✅ Recovery rebuy executed: {asset} €{rebuy_amount}")
        return True
    
    return False
```

### Step 4: Integration into Main Loop
```python
def monitor_assets(self):
    """Main monitoring loop with recovery rebuy integration."""
    
    for asset in self.protected_assets:
        current_price = self.get_current_price(asset)
        
        # Update lowest price tracking (call on every price update)
        self.update_lowest_price_tracking(asset, current_price)
        
        # Check for recovery rebuy opportunity
        if self.check_recovery_rebuy_opportunity(asset, current_price):
            self.execute_recovery_rebuy(asset, current_price)
        
        # ... other monitoring logic (DCA, swing trading, etc.)
```

## 📊 Configuration Examples

### Conservative (Crypto Assets)
```bash
MIN_RECOVERY_THRESHOLD_PCT=15.0    # Track drops ≥15%
RECOVERY_BOUNCE_PCT=8.0            # Rebuy on 8% bounce
RECOVERY_REBUY_ALLOCATION=0.25     # Use 25% of cash
```

### Aggressive (High Volatility)
```bash
MIN_RECOVERY_THRESHOLD_PCT=10.0    # Track drops ≥10%
RECOVERY_BOUNCE_PCT=5.0            # Rebuy on 5% bounce
RECOVERY_REBUY_ALLOCATION=0.4      # Use 40% of cash
```

### Ultra-Conservative (Large Positions)
```bash
MIN_RECOVERY_THRESHOLD_PCT=20.0    # Track drops ≥20%
RECOVERY_BOUNCE_PCT=12.0           # Rebuy on 12% bounce
RECOVERY_REBUY_ALLOCATION=0.15     # Use 15% of cash
```

## 🎭 Real-World Examples

### Example 1: Bitcoin Recovery
```
Entry: €50,000
Drop to: €36,500 (-27% drop - exceeds 15% threshold)
Recovery: €39,420 (+8% bounce from €36,500)
Action: Recovery rebuy triggered
Result: Buy at €39,420 (still -21% from entry, but caught recovery)
```

### Example 2: Ethereum Scenario
```
Entry: €3,000
Drop to: €2,400 (-20% drop)
Further drop: €2,250 (-25% - new low)
Small bounce: €2,295 (+2% - insufficient)
Major bounce: €2,430 (+8% from €2,250 low)
Action: Recovery rebuy at €2,430
Result: Caught recovery at -19% from entry instead of waiting for -30%
```

### Example 3: Avoided False Signal
```
Entry: €1,000
Drop to: €920 (-8% drop - below 15% threshold)
Bounce: €995 (+8.1% bounce)
Action: No rebuy (drop wasn't significant enough)
Result: Avoided noise trading on minor movements
```

## ⚖️ Safety Considerations

### 1. Position Size Limits
```python
def check_position_limits(self, asset: str, additional_amount: Decimal) -> bool:
    """Prevent excessive position growth."""
    current_position = self.get_position_value(asset)
    original_investment = self.get_original_investment(asset)
    
    total_after_rebuy = current_position + additional_amount
    max_allowed = original_investment * self.max_position_multiplier  # e.g., 2.0x
    
    return total_after_rebuy <= max_allowed
```

### 2. Cash Management
```python
def get_available_cash(self, asset: str) -> Decimal:
    """Get cash available for recovery rebuys."""
    # Use dedicated cash reserves from strategic sells
    # NOT the main DCA budget
    return self.swing_cash_reserves.get(asset, Decimal('0'))
```

### 3. One Per Cycle Logic
```python
def mark_recovery_rebuy_completed(self, asset: str):
    """Mark recovery rebuy completed for this drop cycle."""
    asset_info = self.get_asset_info(asset)
    asset_info.recovery_rebuy_completed = True
    # Flag resets automatically when new lows are hit
```

## 🔄 State Management

### Reset Conditions
The recovery rebuy flag resets when:
- **New lower low is hit**: Starts tracking new drop cycle
- **Significant price recovery**: Above entry price (optional)
- **Time-based reset**: After X days (optional)

### Persistence
```python
# Add to your state serialization
{
    "asset": "BTC-EUR",
    "entry_price": "50000",
    "lowest_price_since_entry": "36500", 
    "recovery_rebuy_completed": false,
    "last_recovery_rebuy": "2024-01-15T10:30:00",
    # ... other fields
}
```

## 🚀 Benefits

1. **Never Miss Recoveries**: Catches bounces from ANY significant drop
2. **Dynamic Adaptation**: Adjusts to actual market behavior vs fixed levels
3. **Capital Efficiency**: Uses available cash reserves optimally
4. **Risk Managed**: Multiple safety checks prevent over-exposure
5. **Backtestable**: Clear logic that can be historically validated

## ⚠️ Considerations

1. **Cash Requirements**: Needs available reserves from strategic sells
2. **False Signals**: Small bounces in continued downtrends
3. **Parameter Tuning**: Needs optimization for different assets/markets
4. **Integration Complexity**: Requires coordination with other strategies

## 🎯 Success Metrics

Track these metrics to optimize your implementation:
- **Recovery Catch Rate**: % of significant recoveries captured
- **False Signal Rate**: % of rebuys that continued falling
- **Average Entry Improvement**: How much better than fixed levels
- **Capital Efficiency**: ROI on recovery rebuy capital

This dynamic rebuy mechanism transforms a reactive trading system into a proactive one that captures opportunities as they develop, regardless of predefined levels! 🎯