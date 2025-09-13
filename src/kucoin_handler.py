import time
import hmac
import hashlib
import json
import base64
import logging
import threading
from typing import Any, Optional, Dict

import requests
from requests import Session, RequestException
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

try:
    from .config import APIConfig
except ImportError:
    from config import APIConfig


class KuCoinAPI:
    def __init__(self, api_config: APIConfig, passphrase: str, key_version: str = "2") -> None:
        self.config = api_config
        self.passphrase = passphrase
        self.key_version = key_version
        self.session = self._setup_session()
        self._last_request_time = 0
        self._request_count = 0
        self._rate_limit_lock = threading.Lock()

    def _setup_session(self) -> Session:
        """Setup session with retry mechanism."""
        session = Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        return session

    def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting in a thread-safe manner using sliding window."""
        with self._rate_limit_lock:
            current_time = time.time()
            
            # Initialize if first request
            if self._last_request_time == 0:
                self._last_request_time = current_time
                self._request_count = 1
                return
            
            # If more than 60 seconds have passed, reset the counter
            time_since_last_reset = current_time - self._last_request_time
            if time_since_last_reset >= 60:
                self._request_count = 1
                self._last_request_time = current_time
                return
            
            # Increment request count
            self._request_count += 1
            
            # Check if we've exceeded the rate limit
            if self._request_count > self.config.rate_limit:
                # Calculate how long to sleep to stay within rate limit
                sleep_time = 60 - time_since_last_reset
                if sleep_time > 0:
                    logging.info(f"Rate limit exceeded ({self._request_count}/{self.config.rate_limit}). Sleeping for {sleep_time:.2f} seconds.")
                    time.sleep(sleep_time)
                
                # Reset after sleeping
                self._request_count = 1
                self._last_request_time = time.time()

    def _generate_signature(self, timestamp: str, method: str, endpoint: str, body: str = "") -> tuple[str, str]:
        """Generate HMAC signature and encrypted passphrase for KuCoin API."""
        # Create the prehash string: timestamp + method + endpoint + body
        str_to_sign = f"{timestamp}{method.upper()}{endpoint}{body}"
        
        # Generate signature
        signature = hmac.new(
            self.config.api_secret.encode('utf-8'),
            str_to_sign.encode('utf-8'),
            hashlib.sha256
        ).digest()
        signature_b64 = base64.b64encode(signature).decode('utf-8')
        
        # Encrypt passphrase
        passphrase_signature = hmac.new(
            self.config.api_secret.encode('utf-8'),
            self.passphrase.encode('utf-8'),
            hashlib.sha256
        ).digest()
        passphrase_b64 = base64.b64encode(passphrase_signature).decode('utf-8')
        
        return signature_b64, passphrase_b64

    def send_request(self, method: str, endpoint: str, params: Optional[Dict] = None, body: Optional[Dict] = None) -> Optional[Dict]:
        """Send authenticated request to KuCoin API."""
        self._enforce_rate_limit()

        try:
            timestamp = str(int(time.time() * 1000))
            
            # Handle URL construction
            url = f"{self.config.base_url}{endpoint}"
            query_string = ""
            if params and method.upper() in ['GET', 'DELETE']:
                query_string = "&".join([f"{k}={v}" for k, v in params.items()])
                if query_string:
                    url = f"{url}?{query_string}"
                    endpoint = f"{endpoint}?{query_string}"
            
            # Prepare body string for signature
            body_str = ""
            json_data = None
            if body and method.upper() in ['POST', 'PUT']:
                body_str = json.dumps(body, separators=(',', ':'))
                json_data = body
            
            # Generate signature and encrypted passphrase
            signature, encrypted_passphrase = self._generate_signature(
                timestamp, method, endpoint, body_str
            )

            headers = {
                'KC-API-KEY': self.config.api_key,
                'KC-API-SIGN': signature,
                'KC-API-TIMESTAMP': timestamp,
                'KC-API-PASSPHRASE': encrypted_passphrase,
                'KC-API-KEY-VERSION': self.key_version,
                'Content-Type': 'application/json'
            }

            response = self.session.request(
                method=method.upper(),
                url=url,
                headers=headers,
                json=json_data,
                timeout=self.config.timeout
            )

            response.raise_for_status()
            result = response.json()
            
            # KuCoin API returns responses in format: {"code": "200000", "data": {...}}
            if result.get('code') == '200000':
                return result.get('data')
            else:
                logging.error(f"KuCoin API error: {result.get('msg', 'Unknown error')}")
                return None

        except RequestException as e:
            logging.exception(f"Request failed: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    logging.error(f"API Error: {error_detail}")
                except ValueError:
                    logging.error(f"Raw response: {e.response.text}")
            return None

        except Exception as e:
            logging.exception(f"Unexpected error: {str(e)}")
            return None

    def get_symbols(self) -> Optional[Dict]:
        """Get all trading symbols."""
        return self.send_request("GET", "/api/v2/symbols")

    def get_ticker(self, symbol: str) -> Optional[Dict]:
        """Get 24hr stats for a symbol."""
        return self.send_request("GET", f"/api/v1/market/stats?symbol={symbol}")

    def get_account_balance(self, currency: str = None, account_type: str = "trade") -> Optional[Dict]:
        """Get account balance."""
        endpoint = f"/api/v1/accounts?type={account_type}"
        if currency:
            endpoint += f"&currency={currency}"
        return self.send_request("GET", endpoint)

    def place_market_order(self, symbol: str, side: str, funds: str = None, size: str = None) -> Optional[Dict]:
        """Place a market order."""
        body = {
            "clientOid": str(int(time.time() * 1000)),  # Unique client order ID
            "symbol": symbol,
            "side": side,  # buy or sell
            "type": "market"
        }
        
        if funds:  # For market buy orders with quote currency amount
            body["funds"] = funds
        elif size:  # For market sell orders with base currency amount
            body["size"] = size
        else:
            raise ValueError("Either funds or size must be specified for market orders")
            
        return self.send_request("POST", "/api/v1/orders", body=body)

    def get_order(self, order_id: str) -> Optional[Dict]:
        """Get order details."""
        return self.send_request("GET", f"/api/v1/orders/{order_id}")

    def cancel_order(self, order_id: str) -> Optional[Dict]:
        """Cancel an order."""
        return self.send_request("DELETE", f"/api/v1/orders/{order_id}")