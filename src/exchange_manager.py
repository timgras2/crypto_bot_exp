import logging
from typing import Optional, Dict, List, Any

try:
    from .config import ExchangeConfig
    from .requests_handler import BitvavoAPI
    from .kucoin_handler import KuCoinAPI
except ImportError:
    from config import ExchangeConfig
    from requests_handler import BitvavoAPI
    from kucoin_handler import KuCoinAPI


class ExchangeManager:
    """Manages multiple cryptocurrency exchange connections."""
    
    def __init__(self, exchange_config: ExchangeConfig) -> None:
        self.config = exchange_config
        self.exchanges = {}
        self.primary_exchange = exchange_config.primary_exchange
        
        # Initialize exchange APIs
        self._initialize_exchanges()
        
        logging.info(f"ExchangeManager initialized with {len(self.exchanges)} exchanges: {list(self.exchanges.keys())}")
        logging.info(f"Primary exchange: {self.primary_exchange}")
    
    def _initialize_exchanges(self) -> None:
        """Initialize all enabled exchanges."""
        if "bitvavo" in self.config.enabled_exchanges and self.config.bitvavo:
            try:
                self.exchanges["bitvavo"] = BitvavoAPI(self.config.bitvavo)
                logging.info("Bitvavo API initialized successfully")
            except Exception as e:
                logging.error(f"Failed to initialize Bitvavo API: {e}")
                raise
        
        if "kucoin" in self.config.enabled_exchanges and self.config.kucoin:
            try:
                self.exchanges["kucoin"] = KuCoinAPI(
                    self.config.kucoin, 
                    self.config.kucoin.passphrase
                )
                logging.info("KuCoin API initialized successfully")
            except Exception as e:
                logging.error(f"Failed to initialize KuCoin API: {e}")
                raise
    
    def get_exchange(self, exchange_name: str) -> Optional[Any]:
        """Get a specific exchange API instance."""
        return self.exchanges.get(exchange_name.lower())
    
    def get_primary_exchange(self) -> Any:
        """Get the primary exchange API instance."""
        return self.exchanges.get(self.primary_exchange)
    
    def get_all_markets(self) -> Dict[str, List[str]]:
        """Get all available markets from all exchanges."""
        all_markets = {}
        
        for exchange_name, api in self.exchanges.items():
            try:
                if exchange_name == "bitvavo":
                    response = api.send_request("GET", "/markets")
                    if response:
                        markets = [market.get("market", "") for market in response if market.get("status") == "trading"]
                        all_markets[exchange_name] = markets
                        logging.info(f"Retrieved {len(markets)} markets from Bitvavo")
                
                elif exchange_name == "kucoin":
                    response = api.get_symbols()
                    if response:
                        markets = [symbol.get("symbol", "") for symbol in response if symbol.get("enableTrading")]
                        all_markets[exchange_name] = markets
                        logging.info(f"Retrieved {len(markets)} markets from KuCoin")
                        
            except Exception as e:
                logging.error(f"Failed to get markets from {exchange_name}: {e}")
                all_markets[exchange_name] = []
        
        return all_markets
    
    def get_ticker(self, exchange_name: str, symbol: str) -> Optional[Dict]:
        """Get ticker data for a specific symbol from a specific exchange."""
        api = self.get_exchange(exchange_name)
        if not api:
            logging.error(f"Exchange {exchange_name} not available")
            return None
        
        try:
            if exchange_name == "bitvavo":
                return api.send_request("GET", f"/ticker/24h?market={symbol}")
            elif exchange_name == "kucoin":
                return api.get_ticker(symbol)
        except Exception as e:
            logging.error(f"Failed to get ticker for {symbol} from {exchange_name}: {e}")
            return None
    
    def place_market_buy(self, exchange_name: str, symbol: str, amount: float) -> Optional[float]:
        """Place a market buy order on a specific exchange."""
        api = self.get_exchange(exchange_name)
        if not api:
            logging.error(f"Exchange {exchange_name} not available")
            return None
        
        try:
            if exchange_name == "bitvavo":
                # Bitvavo uses quoteOrderAmount for market buy orders
                order_data = {
                    "market": symbol,
                    "side": "buy",
                    "orderType": "market",
                    "quoteOrderAmount": str(amount)
                }
                response = api.send_request("POST", "/order", body=order_data)
                if response and response.get("status") == "filled":
                    return float(response.get("averagePrice", 0))
                    
            elif exchange_name == "kucoin":
                # KuCoin uses funds for market buy orders (quote currency amount)
                response = api.place_market_order(symbol, "buy", funds=str(amount))
                if response and response.get("orderId"):
                    # For KuCoin, we need to get the order details to find the price
                    order_details = api.get_order(response["orderId"])
                    if order_details:
                        return float(order_details.get("price", 0))
                        
        except Exception as e:
            logging.error(f"Failed to place market buy order for {symbol} on {exchange_name}: {e}")
            return None
    
    def get_account_balance(self, exchange_name: str, currency: str = None) -> Optional[Dict]:
        """Get account balance from a specific exchange."""
        api = self.get_exchange(exchange_name)
        if not api:
            logging.error(f"Exchange {exchange_name} not available")
            return None
        
        try:
            if exchange_name == "bitvavo":
                return api.send_request("GET", "/balance")
            elif exchange_name == "kucoin":
                return api.get_account_balance(currency)
        except Exception as e:
            logging.error(f"Failed to get account balance from {exchange_name}: {e}")
            return None
    
    def format_symbol_for_exchange(self, base_symbol: str, quote_symbol: str, exchange_name: str) -> str:
        """Format a trading symbol for a specific exchange."""
        if exchange_name == "bitvavo":
            # Bitvavo format: BTC-EUR
            return f"{base_symbol}-{quote_symbol}"
        elif exchange_name == "kucoin":
            # KuCoin format: BTC-USDT
            return f"{base_symbol}-{quote_symbol}"
        else:
            # Default format
            return f"{base_symbol}-{quote_symbol}"
    
    def normalize_symbol_format(self, symbol: str, from_exchange: str, to_exchange: str) -> str:
        """Convert symbol format between exchanges."""
        if from_exchange == to_exchange:
            return symbol
        
        # Split the symbol
        if "-" in symbol:
            base, quote = symbol.split("-", 1)
        elif "/" in symbol:
            base, quote = symbol.split("/", 1)
        else:
            # Assume the symbol is already in the right format
            return symbol
        
        return self.format_symbol_for_exchange(base, quote, to_exchange)
    
    def get_enabled_exchanges(self) -> List[str]:
        """Get list of enabled exchanges."""
        return list(self.exchanges.keys())
    
    def is_exchange_available(self, exchange_name: str) -> bool:
        """Check if an exchange is available."""
        return exchange_name.lower() in self.exchanges