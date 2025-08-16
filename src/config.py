import os
from decimal import Decimal, InvalidOperation
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

load_dotenv()


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
    
    # Safety filters for slippage and liquidity protection
    max_slippage_pct: Decimal = Decimal('0.5')      # Max allowed slippage percentage
    min_24h_volume_usd: Decimal = Decimal('500000') # Min $500K daily volume required
    
    # Default dip levels: 40% at -10%, 35% at -20%, 25% at -35%
    dip_levels: List[DipLevel] = field(default_factory=lambda: [
        DipLevel(threshold_pct=Decimal('10'), capital_allocation=Decimal('0.4')),
        DipLevel(threshold_pct=Decimal('20'), capital_allocation=Decimal('0.35')),
        DipLevel(threshold_pct=Decimal('35'), capital_allocation=Decimal('0.25'))
    ])


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
        max_slippage_pct=_validate_decimal_range(
            os.getenv("DIP_MAX_SLIPPAGE_PCT", "0.5"), "DIP_MAX_SLIPPAGE_PCT", 0.1, 5.0
        ),
        min_24h_volume_usd=_validate_decimal_range(
            os.getenv("DIP_MIN_24H_VOLUME_USD", "500000"), "DIP_MIN_24H_VOLUME_USD", 10000.0, 100000000.0
        ),
        dip_levels=_parse_dip_levels(os.getenv("DIP_LEVELS", ""))
    )


def load_config() -> tuple[TradingConfig, APIConfig, DipBuyConfig]:
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

    return trading_config, api_config, dip_config
