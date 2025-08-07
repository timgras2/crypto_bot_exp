import os
from decimal import Decimal, InvalidOperation
from dataclasses import dataclass
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


def load_config() -> tuple[TradingConfig, APIConfig]:
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

    return trading_config, api_config
