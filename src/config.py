import os
import logging
from decimal import Decimal, InvalidOperation
from dataclasses import dataclass, field
from typing import List, Optional
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
    passphrase: str = ""  # For KuCoin API


@dataclass
class ExchangeConfig:
    """Multi-exchange configuration."""
    enabled_exchanges: List[str] = field(default_factory=lambda: ["bitvavo"])  # bitvavo, kucoin
    primary_exchange: str = "bitvavo"  # Primary exchange for new listings
    
    # Bitvavo specific config
    bitvavo: Optional[APIConfig] = None
    
    # KuCoin specific config  
    kucoin: Optional[APIConfig] = None


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
    # Basic format validation - should be alphanumeric with dashes and underscores allowed
    if not api_key.replace('-', '').replace('_', '').isalnum():
        raise ValueError("API key contains invalid characters")
    if not api_secret.replace('-', '').replace('_', '').isalnum():
        raise ValueError("API secret contains invalid characters")


def _load_exchange_config() -> ExchangeConfig:
    """Load multi-exchange configuration from environment variables."""
    enabled_exchanges_str = os.getenv("ENABLED_EXCHANGES", "bitvavo")
    enabled_exchanges = [ex.strip().lower() for ex in enabled_exchanges_str.split(",") if ex.strip()]
    
    # Validate enabled exchanges
    valid_exchanges = {"bitvavo", "kucoin"}
    invalid_exchanges = set(enabled_exchanges) - valid_exchanges
    if invalid_exchanges:
        raise ValueError(f"Invalid exchanges: {invalid_exchanges}. Valid exchanges: {valid_exchanges}")
    
    primary_exchange = os.getenv("PRIMARY_EXCHANGE", "bitvavo").lower()
    if primary_exchange not in enabled_exchanges:
        raise ValueError(f"Primary exchange '{primary_exchange}' must be in enabled exchanges: {enabled_exchanges}")
    
    # Initialize exchange configs
    bitvavo_config = None
    kucoin_config = None
    
    # Load Bitvavo config if enabled
    if "bitvavo" in enabled_exchanges:
        bitvavo_api_key = os.getenv("BITVAVO_API_KEY", "")
        bitvavo_api_secret = os.getenv("BITVAVO_API_SECRET", "")
        
        # Validate required Bitvavo credentials
        if not bitvavo_api_key or not bitvavo_api_secret:
            raise ValueError("BITVAVO_API_KEY and BITVAVO_API_SECRET are required when Bitvavo is enabled")
        
        # Validate Bitvavo API credentials
        _validate_api_credentials(bitvavo_api_key, bitvavo_api_secret)
        
        # Validate Bitvavo base URL format
        bitvavo_base_url = os.getenv("BITVAVO_BASE_URL", "https://api.bitvavo.com/v2")
        if not bitvavo_base_url.startswith("https://"):
            raise ValueError("Bitvavo base URL must use HTTPS")
        
        bitvavo_config = APIConfig(
            api_key=bitvavo_api_key,
            api_secret=bitvavo_api_secret,
            base_url=bitvavo_base_url,
            rate_limit=_validate_int_range(
                os.getenv("BITVAVO_RATE_LIMIT", "300"), "BITVAVO_RATE_LIMIT", 10, 1000
            ),
            timeout=_validate_int_range(
                os.getenv("BITVAVO_API_TIMEOUT", "30"), "BITVAVO_API_TIMEOUT", 5, 120
            )
        )
    
    # Load KuCoin config if enabled
    if "kucoin" in enabled_exchanges:
        kucoin_api_key = os.getenv("KUCOIN_API_KEY", "")
        kucoin_api_secret = os.getenv("KUCOIN_API_SECRET", "")
        kucoin_passphrase = os.getenv("KUCOIN_PASSPHRASE", "")
        
        # Validate required KuCoin credentials
        if not kucoin_api_key or not kucoin_api_secret or not kucoin_passphrase:
            raise ValueError("KUCOIN_API_KEY, KUCOIN_API_SECRET, and KUCOIN_PASSPHRASE are required when KuCoin is enabled")
        
        # Validate KuCoin API credentials
        _validate_api_credentials(kucoin_api_key, kucoin_api_secret)
        
        # Validate KuCoin base URL format
        kucoin_base_url = os.getenv("KUCOIN_BASE_URL", "https://api.kucoin.com")
        if not kucoin_base_url.startswith("https://"):
            raise ValueError("KuCoin base URL must use HTTPS")
        
        kucoin_config = APIConfig(
            api_key=kucoin_api_key,
            api_secret=kucoin_api_secret,
            base_url=kucoin_base_url,
            rate_limit=_validate_int_range(
                os.getenv("KUCOIN_RATE_LIMIT", "180"), "KUCOIN_RATE_LIMIT", 10, 1000
            ),
            timeout=_validate_int_range(
                os.getenv("KUCOIN_API_TIMEOUT", "30"), "KUCOIN_API_TIMEOUT", 5, 120
            ),
            passphrase=kucoin_passphrase
        )
    
    return ExchangeConfig(
        enabled_exchanges=enabled_exchanges,
        primary_exchange=primary_exchange,
        bitvavo=bitvavo_config,
        kucoin=kucoin_config
    )


def load_config() -> tuple[TradingConfig, ExchangeConfig]:
    """Load and validate configuration."""

    # Load exchange configuration
    exchange_config = _load_exchange_config()
    
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

    return trading_config, exchange_config
