import pytest
import os
from unittest.mock import Mock, patch
from decimal import Decimal

import sys
sys.path.insert(0, 'src')

from src.config import APIConfig, ExchangeConfig, load_config
from src.kucoin_handler import KuCoinAPI
from src.exchange_manager import ExchangeManager


class TestKuCoinIntegration:
    """Test KuCoin integration functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock KuCoin API configuration
        self.kucoin_config = APIConfig(
            api_key="test_api_key_12345678901234567890123456789012",
            api_secret="test_api_secret_12345678901234567890123456789012",
            base_url="https://api.kucoin.com",
            rate_limit=180,
            timeout=30,
            passphrase="test_passphrase"
        )
    
    def test_kucoin_api_initialization(self):
        """Test KuCoin API initialization."""
        api = KuCoinAPI(self.kucoin_config, "test_passphrase")
        
        assert api.config == self.kucoin_config
        assert api.passphrase == "test_passphrase"
        assert api.key_version == "2"
        assert api._request_count == 0
    
    def test_signature_generation(self):
        """Test KuCoin signature generation."""
        api = KuCoinAPI(self.kucoin_config, "test_passphrase")
        
        timestamp = "1640995200000"
        method = "GET"
        endpoint = "/api/v1/accounts"
        body = ""
        
        signature, encrypted_passphrase = api._generate_signature(timestamp, method, endpoint, body)
        
        # Signature should be base64 encoded
        assert isinstance(signature, str)
        assert len(signature) > 0
        
        # Encrypted passphrase should be base64 encoded
        assert isinstance(encrypted_passphrase, str)
        assert len(encrypted_passphrase) > 0
    
    @patch('requests.Session.request')
    def test_kucoin_api_request(self, mock_request):
        """Test KuCoin API request handling."""
        # Mock successful response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "code": "200000",
            "data": [
                {"currency": "BTC", "balance": "0.1", "available": "0.1"},
                {"currency": "USDT", "balance": "1000", "available": "1000"}
            ]
        }
        mock_request.return_value = mock_response
        
        api = KuCoinAPI(self.kucoin_config, "test_passphrase")
        result = api.send_request("GET", "/api/v1/accounts")
        
        # Should return the data portion of the response
        assert result is not None
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["currency"] == "BTC"
    
    @patch('requests.Session.request')
    def test_kucoin_api_error_handling(self, mock_request):
        """Test KuCoin API error handling."""
        # Mock error response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "code": "400001",
            "msg": "Invalid request"
        }
        mock_request.return_value = mock_response
        
        api = KuCoinAPI(self.kucoin_config, "test_passphrase")
        result = api.send_request("GET", "/api/v1/accounts")
        
        # Should return None for error responses
        assert result is None
    
    def test_exchange_manager_with_kucoin(self):
        """Test ExchangeManager with KuCoin configuration."""
        # Mock exchange configuration with KuCoin enabled
        exchange_config = ExchangeConfig(
            enabled_exchanges=["bitvavo", "kucoin"],
            primary_exchange="bitvavo",
            bitvavo=APIConfig(
                api_key="bitvavo_key_12345678901234567890123456789012",
                api_secret="bitvavo_secret_12345678901234567890123456789012",
                base_url="https://api.bitvavo.com/v2",
                rate_limit=300,
                timeout=30
            ),
            kucoin=self.kucoin_config
        )
        
        with patch('src.exchange_manager.BitvavoAPI'), \
             patch('src.exchange_manager.KuCoinAPI') as mock_kucoin:
            
            mock_kucoin.return_value = Mock()
            
            manager = ExchangeManager(exchange_config)
            
            # Should initialize both exchanges
            assert "bitvavo" in manager.exchanges
            assert "kucoin" in manager.exchanges
            assert manager.primary_exchange == "bitvavo"
            
            # Should be able to get KuCoin exchange
            kucoin_api = manager.get_exchange("kucoin")
            assert kucoin_api is not None
    
    def test_symbol_formatting(self):
        """Test symbol formatting for different exchanges."""
        exchange_config = ExchangeConfig(
            enabled_exchanges=["bitvavo", "kucoin"],
            primary_exchange="bitvavo"
        )
        
        with patch('src.exchange_manager.BitvavoAPI'), \
             patch('src.exchange_manager.KuCoinAPI'):
            
            manager = ExchangeManager(exchange_config)
            
            # Test Bitvavo format
            bitvavo_symbol = manager.format_symbol_for_exchange("BTC", "EUR", "bitvavo")
            assert bitvavo_symbol == "BTC-EUR"
            
            # Test KuCoin format
            kucoin_symbol = manager.format_symbol_for_exchange("BTC", "USDT", "kucoin")
            assert kucoin_symbol == "BTC-USDT"
    
    def test_symbol_normalization(self):
        """Test symbol format normalization between exchanges."""
        exchange_config = ExchangeConfig(
            enabled_exchanges=["bitvavo", "kucoin"],
            primary_exchange="bitvavo"
        )
        
        with patch('src.exchange_manager.BitvavoAPI'), \
             patch('src.exchange_manager.KuCoinAPI'):
            
            manager = ExchangeManager(exchange_config)
            
            # Test normalization from Bitvavo to KuCoin
            normalized = manager.normalize_symbol_format("BTC-EUR", "bitvavo", "kucoin")
            assert normalized == "BTC-EUR"  # Same format
            
            # Test with different separator
            normalized = manager.normalize_symbol_format("BTC/EUR", "bitvavo", "kucoin")
            assert normalized == "BTC-EUR"
    
    @patch.dict(os.environ, {
        'ENABLED_EXCHANGES': 'bitvavo,kucoin',
        'PRIMARY_EXCHANGE': 'kucoin',
        'BITVAVO_API_KEY': 'bitvavo_key_12345678901234567890123456789012',
        'BITVAVO_API_SECRET': 'bitvavo_secret_12345678901234567890123456789012',
        'KUCOIN_API_KEY': 'kucoin_key_12345678901234567890123456789012',
        'KUCOIN_API_SECRET': 'kucoin_secret_12345678901234567890123456789012',
        'KUCOIN_PASSPHRASE': 'test_passphrase',
        'MIN_PROFIT_PCT': '5.0',
        'TRAILING_PCT': '3.0',
        'MAX_TRADE_AMOUNT': '10.0',
        'CHECK_INTERVAL': '10',
        'MAX_RETRIES': '3',
        'RETRY_DELAY': '5',
        'OPERATOR_ID': '1001'
    })
    def test_config_loading_with_kucoin(self):
        """Test configuration loading with KuCoin enabled."""
        trading_config, exchange_config, dip_config, asset_protection_config, sentiment_config = load_config()
        
        # Check that both exchanges are enabled
        assert "bitvavo" in exchange_config.enabled_exchanges
        assert "kucoin" in exchange_config.enabled_exchanges
        assert exchange_config.primary_exchange == "kucoin"
        
        # Check KuCoin configuration
        assert exchange_config.kucoin is not None
        assert exchange_config.kucoin.api_key == 'kucoin_key_12345678901234567890123456789012'
        assert exchange_config.kucoin.passphrase == 'test_passphrase'
        assert exchange_config.kucoin.base_url == 'https://api.kucoin.com'
    
    def test_invalid_exchange_configuration(self):
        """Test handling of invalid exchange configurations."""
        with pytest.raises(ValueError, match="Invalid exchanges"):
            ExchangeConfig(
                enabled_exchanges=["invalid_exchange"],
                primary_exchange="invalid_exchange"
            )
    
    def test_primary_exchange_not_in_enabled(self):
        """Test error when primary exchange is not in enabled exchanges."""
        with pytest.raises(ValueError, match="Primary exchange .* must be in enabled exchanges"):
            ExchangeConfig(
                enabled_exchanges=["bitvavo"],
                primary_exchange="kucoin"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])