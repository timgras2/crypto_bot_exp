import time
import hmac
import hashlib
import json
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


class BitvavoAPI:
    def __init__(self, api_config: APIConfig) -> None:
        self.config = api_config
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

    def _generate_signature(self, method: str, endpoint: str, body: Any, timestamp: str) -> str:
        """Generate HMAC signature for API request."""
        # Ensure the endpoint begins with '/v2'
        full_endpoint = f'/v2{endpoint}' if not endpoint.startswith('/v2') else endpoint
        message = f"{timestamp}{method.upper()}{full_endpoint}"
        if body:
            message += json.dumps(body, separators=(',', ':'))
        return hmac.new(
            self.config.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def send_request(self, method: str, endpoint: str, body: Optional[Dict] = None) -> Optional[Dict]:
        """Send authenticated request to Bitvavo API."""
        self._enforce_rate_limit()

        try:
            timestamp = str(int(time.time() * 1000))
            signature = self._generate_signature(method, endpoint, body, timestamp)

            headers = {
                'bitvavo-access-key': self.config.api_key,
                'bitvavo-access-signature': signature,
                'bitvavo-access-timestamp': timestamp,
                'bitvavo-access-window': '10000',
                'Content-Type': 'application/json'
            }

            url = f"{self.config.base_url}{endpoint}"

            response = self.session.request(
                method=method.upper(),
                url=url,
                headers=headers,
                json=body,
                timeout=self.config.timeout
            )

            response.raise_for_status()
            return response.json()

        except RequestException as e:
            logging.exception(f"Request failed: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    logging.error(f"API Error: {error_detail}")
                    
                    # Special handling for market parameter errors (common with new listings)
                    if error_detail.get('errorCode') == 205:
                        logging.info(f"Market parameter invalid - this is common for very new listings")
                        
                except ValueError:
                    logging.error(f"Raw response: {e.response.text}")
            return None

        except Exception as e:
            logging.exception(f"Unexpected error: {str(e)}")
            return None
