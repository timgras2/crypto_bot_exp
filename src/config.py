import os
import logging
from decimal import Decimal, InvalidOperation
from dataclasses import dataclass, field
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class TradingConfig:
    """Trading configuration parameters."""
    min_profit_pct: Decimal
    trailing_pct: Decimal
    max_trade_amount: Decimal
    check_interval: int  # seconds
    max_retries: int
    retry_delay: int  # seconds
    operator_id: int  # Required by Bitvavo API for order identification


@dataclass
class APIConfig:
    """API configuration."""
    api_key: str
    api_secret: str
    base_url: str
    rate_limit: int  # requests per minute
    timeout: int  # seconds


@dataclass
class DipLevel:
    """Configuration for a single dip buying level."""
    threshold_pct: Decimal      # Percentage drop to trigger rebuy (e.g., 10%)
    capital_allocation: Decimal # Portion of rebuy budget to use (e.g., 0.4 = 40%)
    max_retries: int = 3       # Technical retry limit for this level


@dataclass 
class DipBuyConfig:
    """Configuration for dip buying strategy."""
    enabled: bool = False                    # Master feature toggle
    monitoring_duration_hours: int = 48      # How long to monitor after sale
    cooldown_hours: int = 4                  # Cooldown between rebuys per asset
    max_rebuys_per_asset: int = 3           # Maximum rebuy attempts per asset
    use_market_filter: bool = False         # Enable BTC trend filtering
    
    # Default dip levels: 40% at -10%, 35% at -20%, 25% at -35%
    dip_levels: List[DipLevel] = field(default_factory=lambda: [
        DipLevel(threshold_pct=Decimal('10'), capital_allocation=Decimal('0.4')),
        DipLevel(threshold_pct=Decimal('20'), capital_allocation=Decimal('0.35')),
        DipLevel(threshold_pct=Decimal('35'), capital_allocation=Decimal('0.25'))
    ])


@dataclass
class ProfitLevel:
    """Configuration for a profit taking level."""
    threshold_pct: Decimal      # Percentage gain to trigger sell (e.g., 20%)
    position_allocation: Decimal # Portion of position to sell (e.g., 0.25 = 25%)


@dataclass
class SwingLevel:
    """Configuration for a swing trading level."""
    threshold_pct: Decimal      # Percentage drop to trigger action (e.g., 5%)
    action: str                 # 'sell' or 'rebuy'
    allocation: Decimal         # Portion to sell/rebuy (e.g., 0.25 = 25%)


@dataclass
class TrendDetectionConfig:
    """Configuration for trend detection and market regime filtering."""
    enabled: bool = True                     # Enable trend-based adjustments
    lookback_hours: int = 168               # Hours to look back for trend (7 days)
    bear_trend_threshold: Decimal = Decimal('-10.0')  # % decline to trigger bear mode
    bull_trend_threshold: Decimal = Decimal('10.0')   # % gain to trigger bull mode
    volatility_threshold: Decimal = Decimal('50.0')   # Daily volatility % for volatile mode

@dataclass
class AssetProtectionConfig:
    """Configuration for asset protection strategy."""
    enabled: bool = False                    # Master feature toggle
    protected_assets: List[str] = field(default_factory=list)  # Assets to protect (e.g., ['BTC-EUR', 'ETH-EUR'])
    max_protection_budget: Decimal = Decimal('100.0')  # Maximum EUR for protection operations
    
    # Trend detection and market regime adaptation
    trend_detection: TrendDetectionConfig = field(default_factory=TrendDetectionConfig)
    
    # Volatility-based stop loss
    base_stop_loss_pct: Decimal = Decimal('15.0')      # Base stop loss percentage
    volatility_window_hours: int = 24                   # Hours to calculate volatility
    volatility_multiplier: Decimal = Decimal('1.5')    # Adjust stop based on volatility
    
    # DCA buying on dips
    dca_enabled: bool = True
    dca_levels: List[DipLevel] = field(default_factory=lambda: [
        DipLevel(threshold_pct=Decimal('10'), capital_allocation=Decimal('0.3')),
        DipLevel(threshold_pct=Decimal('20'), capital_allocation=Decimal('0.4')),
        DipLevel(threshold_pct=Decimal('30'), capital_allocation=Decimal('0.3'))
    ])
    
    # Directional DCA (smart timing based on momentum - upgrade guide implementation)
    directional_dca_enabled: bool = True                    # Enable directional DCA
    dca_momentum_hours: int = 1                             # Hours to look back for momentum  
    dca_falling_multiplier: Decimal = Decimal('0.5')       # Reduce DCA when falling through level
    dca_bouncing_multiplier: Decimal = Decimal('1.5')      # Increase DCA when bouncing off level
    dca_momentum_threshold: Decimal = Decimal('0.5')       # Minimum % momentum to trigger logic
    
    # Recovery Rebuy System (buy on recoveries from any significant drop)
    recovery_rebuy_enabled: bool = True                     # Enable recovery rebuys
    min_recovery_threshold_pct: Decimal = Decimal('15.0')  # Minimum drop required to track for recovery
    recovery_bounce_pct: Decimal = Decimal('8.0')          # % bounce from low to trigger rebuy
    recovery_rebuy_allocation: Decimal = Decimal('0.3')    # Portion of cash reserves to use for recovery rebuy
    
    # Profit taking on pumps
    profit_taking_enabled: bool = True
    profit_levels: List[ProfitLevel] = field(default_factory=lambda: [
        ProfitLevel(threshold_pct=Decimal('20'), position_allocation=Decimal('0.25')),
        ProfitLevel(threshold_pct=Decimal('40'), position_allocation=Decimal('0.5'))
    ])
    
    # Portfolio rebalancing
    rebalancing_enabled: bool = False
    rebalancing_threshold_pct: Decimal = Decimal('10.0') # Trigger rebalancing when allocation drifts >10%
    target_allocations: Dict[str, Decimal] = field(default_factory=dict)  # e.g., {'BTC-EUR': 0.6, 'ETH-EUR': 0.4}
    
    # Risk management
    max_daily_trades: int = 10              # Maximum trades per day per asset
    emergency_stop_loss_pct: Decimal = Decimal('25.0')  # Emergency stop if loss exceeds this
    position_size_limit_pct: Decimal = Decimal('50.0')  # Max percentage of budget per asset
    
    # Position size controls (upgrade guide implementation)
    max_position_multiplier: Decimal = Decimal('2.0')     # Max 2x original position
    position_size_check_enabled: bool = True              # Enable position monitoring
    
    # Loss circuit breaker (upgrade guide implementation)
    loss_circuit_breaker_pct: Decimal = Decimal('15.0')  # Stop buying at -15% loss
    circuit_breaker_enabled: bool = True                  # Enable circuit breaker
    
    # Swing trading protection (sell on drops, rebuy at lows)
    swing_trading_enabled: bool = False     # Enable swing trading mode
    
    # Fixed swing levels to avoid DCA conflicts (sell early, rebuy at major drops)
    swing_levels: List[SwingLevel] = field(default_factory=lambda: [
        SwingLevel(threshold_pct=Decimal('5'), action='sell', allocation=Decimal('0.15')),   # -5%: sell 15% (early warning)
        SwingLevel(threshold_pct=Decimal('8'), action='sell', allocation=Decimal('0.20')),   # -8%: sell 20% (before -10% DCA)
        SwingLevel(threshold_pct=Decimal('30'), action='rebuy', allocation=Decimal('0.40')),  # -30%: rebuy 40% (after major drop)
        SwingLevel(threshold_pct=Decimal('40'), action='rebuy', allocation=Decimal('0.60'))   # -40%: rebuy 60% (confirmed bottom)
    ])
    
    # Bear market swing levels (more aggressive selling, deeper rebuy levels)
    bear_market_swing_levels: List[SwingLevel] = field(default_factory=lambda: [
        SwingLevel(threshold_pct=Decimal('3'), action='sell', allocation=Decimal('0.30')),   # Sell earlier
        SwingLevel(threshold_pct=Decimal('7'), action='sell', allocation=Decimal('0.30')),   # Sell more
        SwingLevel(threshold_pct=Decimal('12'), action='sell', allocation=Decimal('0.25')),  # Keep selling
        SwingLevel(threshold_pct=Decimal('40'), action='rebuy', allocation=Decimal('0.4')),  # Wait deeper
        SwingLevel(threshold_pct=Decimal('60'), action='rebuy', allocation=Decimal('0.6'))   # Major rebuy at bottom
    ])
    
    # Bull market swing levels (less selling, quicker rebuys)
    bull_market_swing_levels: List[SwingLevel] = field(default_factory=lambda: [
        SwingLevel(threshold_pct=Decimal('8'), action='sell', allocation=Decimal('0.15')),   # Sell less
        SwingLevel(threshold_pct=Decimal('15'), action='rebuy', allocation=Decimal('0.5')),  # Rebuy sooner
        SwingLevel(threshold_pct=Decimal('25'), action='rebuy', allocation=Decimal('0.5'))   # Quick recovery
    ])
    
    swing_cash_reserve_pct: Decimal = Decimal('75.0')   # Keep 75% of sale proceeds for rebuying
    swing_trailing_stop_enabled: bool = True            # Trail stops upward on recovery
    
    # Progressive stop loss (sell everything if decline exceeds threshold)
    progressive_stop_loss_enabled: bool = True
    progressive_stop_loss_threshold: Decimal = Decimal('25.0')  # Sell all if down >25% in bear market


def _validate_decimal_range(value: str, name: str, min_val: float, max_val: float) -> Decimal:
    """Validate decimal value is within acceptable range."""
    try:
        decimal_val = Decimal(value)
        if not (min_val <= float(decimal_val) <= max_val):
            raise ValueError(f"{name} must be between {min_val} and {max_val}")
        return decimal_val
    except (ValueError, InvalidOperation) as e:
        raise ValueError(f"Invalid {name} value '{value}': {e}")


def _validate_int_range(value: str, name: str, min_val: int, max_val: int) -> int:
    """Validate integer value is within acceptable range."""
    try:
        int_val = int(value)
        if not (min_val <= int_val <= max_val):
            raise ValueError(f"{name} must be between {min_val} and {max_val}")
        return int_val
    except ValueError as e:
        raise ValueError(f"Invalid {name} value '{value}': {e}")


def _validate_api_credentials(api_key: str, api_secret: str) -> None:
    """Validate API credentials format."""
    if not api_key or len(api_key) < 32:
        raise ValueError("API key appears to be invalid (too short)")
    if not api_secret or len(api_secret) < 32:
        raise ValueError("API secret appears to be invalid (too short)")
    # Basic format validation - should be alphanumeric
    if not api_key.replace('-', '').isalnum():
        raise ValueError("API key contains invalid characters")
    if not api_secret.replace('-', '').isalnum():
        raise ValueError("API secret contains invalid characters")


def _parse_dip_levels(levels_str: str) -> List[DipLevel]:
    """Parse dip levels from environment variable string.
    
    Format: "10:0.4,20:0.35,35:0.25" (threshold_pct:allocation,...)
    """
    if not levels_str.strip():
        # Return default levels if empty
        return [
            DipLevel(threshold_pct=Decimal('10'), capital_allocation=Decimal('0.4')),
            DipLevel(threshold_pct=Decimal('20'), capital_allocation=Decimal('0.35')),
            DipLevel(threshold_pct=Decimal('35'), capital_allocation=Decimal('0.25'))
        ]
    
    levels = []
    total_allocation = Decimal('0')
    
    for level_spec in levels_str.split(','):
        level_spec = level_spec.strip()
        if ':' not in level_spec:
            raise ValueError(f"Invalid dip level format: '{level_spec}'. Expected 'threshold:allocation'")
        
        threshold_str, allocation_str = level_spec.split(':', 1)
        
        try:
            threshold = _validate_decimal_range(threshold_str.strip(), "dip threshold", 1.0, 90.0)
            allocation = _validate_decimal_range(allocation_str.strip(), "capital allocation", 0.01, 1.0)
            total_allocation += allocation
            
            levels.append(DipLevel(
                threshold_pct=threshold,
                capital_allocation=allocation
            ))
        except ValueError as e:
            raise ValueError(f"Invalid dip level '{level_spec}': {e}")
    
    # Validate total allocation doesn't exceed 100%
    if total_allocation > Decimal('1.0'):
        raise ValueError(f"Total dip level allocation {total_allocation:.2f} exceeds 100%")
    
    # Sort by threshold ascending (smallest dips first)
    levels.sort(key=lambda x: x.threshold_pct)
    
    return levels


def _parse_profit_levels(levels_str: str) -> List[ProfitLevel]:
    """Parse profit taking levels from environment variable string.
    
    Format: "20:0.25,40:0.5" (threshold_pct:position_allocation,...)
    """
    if not levels_str.strip():
        # Return default levels if empty
        return [
            ProfitLevel(threshold_pct=Decimal('20'), position_allocation=Decimal('0.25')),
            ProfitLevel(threshold_pct=Decimal('40'), position_allocation=Decimal('0.5'))
        ]
    
    levels = []
    
    for level_spec in levels_str.split(','):
        level_spec = level_spec.strip()
        if ':' not in level_spec:
            raise ValueError(f"Invalid profit level format: '{level_spec}'. Expected 'threshold:allocation'")
        
        threshold_str, allocation_str = level_spec.split(':', 1)
        
        try:
            threshold = _validate_decimal_range(threshold_str.strip(), "profit threshold", 1.0, 1000.0)
            allocation = _validate_decimal_range(allocation_str.strip(), "position allocation", 0.01, 1.0)
            
            levels.append(ProfitLevel(
                threshold_pct=threshold,
                position_allocation=allocation
            ))
        except ValueError as e:
            raise ValueError(f"Invalid profit level '{level_spec}': {e}")
    
    # Sort by threshold ascending (smallest gains first)
    levels.sort(key=lambda x: x.threshold_pct)
    
    return levels


def _parse_protected_assets(assets_str: str) -> List[str]:
    """Parse protected assets from environment variable string.
    
    Format: "BTC-EUR,ETH-EUR,ADA-EUR"
    """
    import re
    
    if not assets_str.strip():
        return []
    
    # Enhanced regex pattern for market validation
    # Matches: 2-10 uppercase alphanumeric characters, dash, 3 uppercase letters
    market_pattern = re.compile(r'^[A-Z0-9]{2,10}-[A-Z]{3}$')
    
    assets = []
    for asset in assets_str.split(','):
        asset = asset.strip().upper()  # Normalize to uppercase
        if not asset:
            continue
            
        # Validate market format with regex
        if not market_pattern.match(asset):
            raise ValueError(
                f"Invalid market format: '{asset}'. "
                f"Expected format: 'SYMBOL-CURRENCY' (e.g., 'BTC-EUR', 'ETH-USD'). "
                f"Symbol must be 2-10 alphanumeric characters, currency must be 3 letters."
            )
            
        # Additional validation for common patterns
        parts = asset.split('-')
        symbol, currency = parts[0], parts[1]
        
        # Validate symbol length and characters
        if len(symbol) < 2 or len(symbol) > 10:
            raise ValueError(f"Invalid symbol length: '{symbol}'. Must be 2-10 characters.")
            
        # Validate currency (common crypto quote currencies)
        valid_currencies = {'EUR', 'USD', 'BTC', 'ETH', 'USDT', 'USDC', 'BNB'}
        if currency not in valid_currencies:
            logger.warning(f"Uncommon quote currency '{currency}' for {asset}. "
                         f"Common currencies: {', '.join(sorted(valid_currencies))}")
            
        assets.append(asset)
    
    return assets


def _parse_target_allocations(allocations_str: str) -> Dict[str, Decimal]:
    """Parse target allocations from environment variable string.
    
    Format: "BTC-EUR:0.6,ETH-EUR:0.4"
    """
    import re
    
    if not allocations_str.strip():
        return {}
    
    # Regex pattern for asset validation (reuse the same pattern)
    market_pattern = re.compile(r'^[A-Z0-9]{2,10}-[A-Z]{3}$')
    
    allocations = {}
    total_allocation = Decimal('0')
    
    for allocation_spec in allocations_str.split(','):
        allocation_spec = allocation_spec.strip()
        if ':' not in allocation_spec:
            raise ValueError(f"Invalid allocation format: '{allocation_spec}'. Expected 'ASSET:percentage'")
        
        asset, allocation_str = allocation_spec.split(':', 1)
        asset = asset.strip().upper()  # Normalize to uppercase
        allocation_str = allocation_str.strip()
        
        # Validate asset format
        if not market_pattern.match(asset):
            raise ValueError(
                f"Invalid asset format in allocation: '{asset}'. "
                f"Expected format: 'SYMBOL-CURRENCY' (e.g., 'BTC-EUR')"
            )
        
        try:
            allocation = _validate_decimal_range(allocation_str, "target allocation", 0.01, 1.0)
            total_allocation += allocation
            allocations[asset] = allocation
        except ValueError as e:
            raise ValueError(f"Invalid target allocation '{allocation_spec}': {e}")
    
    # Validate total allocation doesn't exceed 100%
    if total_allocation > Decimal('1.0'):
        raise ValueError(f"Total target allocation {total_allocation:.2f} exceeds 100%")
    
    # Warn if total allocation is significantly less than 100%
    if total_allocation < Decimal('0.8'):
        logger.warning(f"Target allocations only sum to {total_allocation:.1%}. "
                      f"Consider allocating closer to 100% for better portfolio balance.")
    
    return allocations


def _parse_swing_levels(levels_str: str) -> List[SwingLevel]:
    """Parse swing trading levels from environment variable string.
    
    Format: "5:sell:0.25,10:sell:0.25,20:rebuy:0.5" (threshold_pct:action:allocation,...)
    """
    if not levels_str.strip():
        # Return default levels if empty
        return [
            SwingLevel(threshold_pct=Decimal('5'), action='sell', allocation=Decimal('0.25')),
            SwingLevel(threshold_pct=Decimal('10'), action='sell', allocation=Decimal('0.25')),
            SwingLevel(threshold_pct=Decimal('20'), action='rebuy', allocation=Decimal('0.5')),
            SwingLevel(threshold_pct=Decimal('30'), action='rebuy', allocation=Decimal('0.5'))
        ]
    
    levels = []
    
    for level_spec in levels_str.split(','):
        level_spec = level_spec.strip()
        parts = level_spec.split(':')
        
        if len(parts) != 3:
            raise ValueError(f"Invalid swing level format: '{level_spec}'. Expected 'threshold:action:allocation'")
        
        threshold_str, action_str, allocation_str = parts
        
        try:
            threshold = _validate_decimal_range(threshold_str.strip(), "swing threshold", 1.0, 90.0)
            action = action_str.strip().lower()
            allocation = _validate_decimal_range(allocation_str.strip(), "swing allocation", 0.01, 1.0)
            
            # Validate action
            if action not in ['sell', 'rebuy']:
                raise ValueError(f"Invalid action '{action}'. Must be 'sell' or 'rebuy'")
            
            levels.append(SwingLevel(
                threshold_pct=threshold,
                action=action,
                allocation=allocation
            ))
        except ValueError as e:
            raise ValueError(f"Invalid swing level '{level_spec}': {e}")
    
    # Sort by threshold ascending (smallest drops first)
    levels.sort(key=lambda x: x.threshold_pct)
    
    # Validate that sell levels come before rebuy levels
    sell_thresholds = [l.threshold_pct for l in levels if l.action == 'sell']
    rebuy_thresholds = [l.threshold_pct for l in levels if l.action == 'rebuy']
    
    if sell_thresholds and rebuy_thresholds:
        max_sell = max(sell_thresholds)
        min_rebuy = min(rebuy_thresholds)
        if max_sell >= min_rebuy:
            logger.warning(f"Sell levels should be smaller than rebuy levels. "
                          f"Max sell: {max_sell}%, Min rebuy: {min_rebuy}%")
    
    return levels


def _load_dip_config() -> DipBuyConfig:
    """Load dip buying configuration from environment variables."""
    enabled = os.getenv("DIP_BUY_ENABLED", "false").lower() in ('true', '1', 'yes', 'on')
    
    if not enabled:
        # Return disabled config with defaults
        return DipBuyConfig(enabled=False)
    
    # Parse configuration only if enabled
    return DipBuyConfig(
        enabled=True,
        monitoring_duration_hours=_validate_int_range(
            os.getenv("DIP_MONITORING_HOURS", "48"), "DIP_MONITORING_HOURS", 1, 168  # Max 1 week
        ),
        cooldown_hours=_validate_int_range(
            os.getenv("DIP_COOLDOWN_HOURS", "4"), "DIP_COOLDOWN_HOURS", 1, 48
        ),
        max_rebuys_per_asset=_validate_int_range(
            os.getenv("DIP_MAX_REBUYS_PER_ASSET", "3"), "DIP_MAX_REBUYS_PER_ASSET", 1, 10
        ),
        use_market_filter=os.getenv("DIP_USE_MARKET_FILTER", "false").lower() in ('true', '1', 'yes', 'on'),
        dip_levels=_parse_dip_levels(os.getenv("DIP_LEVELS", ""))
    )


def _load_asset_protection_config() -> AssetProtectionConfig:
    """Load asset protection configuration from environment variables."""
    enabled = os.getenv("ASSET_PROTECTION_ENABLED", "false").lower() in ('true', '1', 'yes', 'on')
    
    if not enabled:
        # Return disabled config with defaults
        return AssetProtectionConfig(enabled=False)
    
    # Parse configuration only if enabled
    return AssetProtectionConfig(
        enabled=True,
        protected_assets=_parse_protected_assets(os.getenv("PROTECTED_ASSETS", "")),
        max_protection_budget=_validate_decimal_range(
            os.getenv("MAX_PROTECTION_BUDGET", "100.0"), "MAX_PROTECTION_BUDGET", 10.0, 100000.0
        ),
        base_stop_loss_pct=_validate_decimal_range(
            os.getenv("BASE_STOP_LOSS_PCT", "15.0"), "BASE_STOP_LOSS_PCT", 1.0, 50.0
        ),
        volatility_window_hours=_validate_int_range(
            os.getenv("VOLATILITY_WINDOW_HOURS", "24"), "VOLATILITY_WINDOW_HOURS", 1, 168
        ),
        volatility_multiplier=_validate_decimal_range(
            os.getenv("VOLATILITY_MULTIPLIER", "1.5"), "VOLATILITY_MULTIPLIER", 0.5, 5.0
        ),
        dca_enabled=os.getenv("DCA_ENABLED", "true").lower() in ('true', '1', 'yes', 'on'),
        dca_levels=_parse_dip_levels(os.getenv("DCA_LEVELS", "10:0.3,20:0.4,30:0.3")),
        profit_taking_enabled=os.getenv("PROFIT_TAKING_ENABLED", "true").lower() in ('true', '1', 'yes', 'on'),
        profit_levels=_parse_profit_levels(os.getenv("PROFIT_TAKING_LEVELS", "")),
        rebalancing_enabled=os.getenv("REBALANCING_ENABLED", "false").lower() in ('true', '1', 'yes', 'on'),
        rebalancing_threshold_pct=_validate_decimal_range(
            os.getenv("REBALANCING_THRESHOLD_PCT", "10.0"), "REBALANCING_THRESHOLD_PCT", 1.0, 50.0
        ),
        target_allocations=_parse_target_allocations(os.getenv("TARGET_ALLOCATIONS", "")),
        max_daily_trades=_validate_int_range(
            os.getenv("MAX_DAILY_TRADES", "10"), "MAX_DAILY_TRADES", 1, 100
        ),
        emergency_stop_loss_pct=_validate_decimal_range(
            os.getenv("EMERGENCY_STOP_LOSS_PCT", "25.0"), "EMERGENCY_STOP_LOSS_PCT", 5.0, 90.0
        ),
        position_size_limit_pct=_validate_decimal_range(
            os.getenv("POSITION_SIZE_LIMIT_PCT", "50.0"), "POSITION_SIZE_LIMIT_PCT", 5.0, 100.0
        ),
        # Position size controls (upgrade guide implementation)
        max_position_multiplier=_validate_decimal_range(
            os.getenv("MAX_POSITION_MULTIPLIER", "2.0"), "MAX_POSITION_MULTIPLIER", 1.0, 10.0
        ),
        position_size_check_enabled=os.getenv("POSITION_SIZE_CHECK_ENABLED", "true").lower() in ('true', '1', 'yes', 'on'),
        # Loss circuit breaker (upgrade guide implementation)
        loss_circuit_breaker_pct=_validate_decimal_range(
            os.getenv("LOSS_CIRCUIT_BREAKER_PCT", "15.0"), "LOSS_CIRCUIT_BREAKER_PCT", 5.0, 50.0
        ),
        circuit_breaker_enabled=os.getenv("CIRCUIT_BREAKER_ENABLED", "true").lower() in ('true', '1', 'yes', 'on'),
        # Directional DCA (upgrade guide implementation)
        directional_dca_enabled=os.getenv("DIRECTIONAL_DCA_ENABLED", "true").lower() in ('true', '1', 'yes', 'on'),
        dca_momentum_hours=_validate_int_range(
            os.getenv("DCA_MOMENTUM_HOURS", "1"), "DCA_MOMENTUM_HOURS", 1, 24
        ),
        dca_falling_multiplier=_validate_decimal_range(
            os.getenv("DCA_FALLING_MULTIPLIER", "0.5"), "DCA_FALLING_MULTIPLIER", 0.0, 2.0
        ),
        dca_bouncing_multiplier=_validate_decimal_range(
            os.getenv("DCA_BOUNCING_MULTIPLIER", "1.5"), "DCA_BOUNCING_MULTIPLIER", 0.5, 5.0
        ),
        dca_momentum_threshold=_validate_decimal_range(
            os.getenv("DCA_MOMENTUM_THRESHOLD", "0.5"), "DCA_MOMENTUM_THRESHOLD", 0.1, 5.0
        ),
        # Recovery rebuy system
        recovery_rebuy_enabled=os.getenv("RECOVERY_REBUY_ENABLED", "true").lower() in ('true', '1', 'yes', 'on'),
        min_recovery_threshold_pct=_validate_decimal_range(
            os.getenv("MIN_RECOVERY_THRESHOLD_PCT", "15.0"), "MIN_RECOVERY_THRESHOLD_PCT", 5.0, 50.0
        ),
        recovery_bounce_pct=_validate_decimal_range(
            os.getenv("RECOVERY_BOUNCE_PCT", "8.0"), "RECOVERY_BOUNCE_PCT", 2.0, 20.0
        ),
        recovery_rebuy_allocation=_validate_decimal_range(
            os.getenv("RECOVERY_REBUY_ALLOCATION", "0.3"), "RECOVERY_REBUY_ALLOCATION", 0.1, 1.0
        ),
        # Swing trading configuration
        swing_trading_enabled=os.getenv("SWING_TRADING_ENABLED", "false").lower() in ('true', '1', 'yes', 'on'),
        swing_levels=_parse_swing_levels(os.getenv("SWING_LEVELS", "")),
        swing_cash_reserve_pct=_validate_decimal_range(
            os.getenv("SWING_CASH_RESERVE_PCT", "75.0"), "SWING_CASH_RESERVE_PCT", 10.0, 100.0
        ),
        swing_trailing_stop_enabled=os.getenv("SWING_TRAILING_STOP_ENABLED", "true").lower() in ('true', '1', 'yes', 'on')
    )


def load_config() -> tuple[TradingConfig, APIConfig, DipBuyConfig, AssetProtectionConfig]:
    """Load and validate configuration."""
    # Validate required environment variables
    required_vars = ["BITVAVO_API_KEY", "BITVAVO_API_SECRET"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    api_key = os.getenv("BITVAVO_API_KEY", "")
    api_secret = os.getenv("BITVAVO_API_SECRET", "")
    
    # Validate API credentials
    _validate_api_credentials(api_key, api_secret)

    # Trading configuration (values can be overridden via environment variables)
    trading_config = TradingConfig(
        min_profit_pct=_validate_decimal_range(
            os.getenv("MIN_PROFIT_PCT", "5.0"), "MIN_PROFIT_PCT", 0.1, 50.0
        ),
        trailing_pct=_validate_decimal_range(
            os.getenv("TRAILING_PCT", "3.0"), "TRAILING_PCT", 0.1, 20.0
        ),
        max_trade_amount=_validate_decimal_range(
            os.getenv("MAX_TRADE_AMOUNT", "10.0"), "MAX_TRADE_AMOUNT", 1.0, 10000.0
        ),
        check_interval=_validate_int_range(
            os.getenv("CHECK_INTERVAL", "10"), "CHECK_INTERVAL", 1, 300
        ),
        max_retries=_validate_int_range(
            os.getenv("MAX_RETRIES", "3"), "MAX_RETRIES", 1, 10
        ),
        retry_delay=_validate_int_range(
            os.getenv("RETRY_DELAY", "5"), "RETRY_DELAY", 1, 60
        ),
        operator_id=_validate_int_range(
            os.getenv("OPERATOR_ID", "1001"), "OPERATOR_ID", 1, 2147483647
        )
    )

    # Validate base URL format
    base_url = os.getenv("BITVAVO_BASE_URL", "https://api.bitvavo.com/v2")
    if not base_url.startswith("https://"):
        raise ValueError("Base URL must use HTTPS")

    # API configuration
    api_config = APIConfig(
        api_key=api_key,
        api_secret=api_secret,
        base_url=base_url,
        rate_limit=_validate_int_range(
            os.getenv("RATE_LIMIT", "300"), "RATE_LIMIT", 10, 1000
        ),
        timeout=_validate_int_range(
            os.getenv("API_TIMEOUT", "30"), "API_TIMEOUT", 5, 120
        )
    )

    # Load dip buy configuration
    dip_config = _load_dip_config()

    # Load asset protection configuration
    asset_protection_config = _load_asset_protection_config()

    return trading_config, api_config, dip_config, asset_protection_config
