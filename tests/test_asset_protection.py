#!/usr/bin/env python3
"""
Comprehensive tests for asset protection system
"""

import json
import pytest
import tempfile
from decimal import Decimal
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

# Import the modules we're testing
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import (
    AssetProtectionConfig, ProfitLevel, DipLevel, TradingConfig,
    _parse_protected_assets, _parse_profit_levels, _parse_target_allocations,
    _load_asset_protection_config
)
from volatility_calculator import VolatilityCalculator
from protected_asset_state import (
    ProtectedAssetStateManager, ProtectedAssetInfo, TradeRecord
)
from asset_protection_manager import AssetProtectionManager


class TestAssetProtectionConfig:
    """Test asset protection configuration parsing and validation."""
    
    def test_parse_protected_assets_valid(self):
        """Test parsing valid protected assets string."""
        assets_str = "BTC-EUR,ETH-EUR,ADA-EUR"
        result = _parse_protected_assets(assets_str)
        expected = ["BTC-EUR", "ETH-EUR", "ADA-EUR"]
        assert result == expected
    
    def test_parse_protected_assets_empty(self):
        """Test parsing empty protected assets string."""
        result = _parse_protected_assets("")
        assert result == []
    
    def test_parse_protected_assets_invalid_format(self):
        """Test parsing invalid asset format raises error."""
        with pytest.raises(ValueError, match="Invalid market format"):
            _parse_protected_assets("BTC,ETH")  # Missing -EUR suffix
    
    def test_parse_protected_assets_invalid_characters(self):
        """Test parsing assets with invalid characters raises error."""
        with pytest.raises(ValueError, match="Invalid market format"):
            _parse_protected_assets("BTC@EUR,ETH-EUR")
    
    def test_parse_profit_levels_valid(self):
        """Test parsing valid profit levels string."""
        levels_str = "20:0.25,40:0.5"
        result = _parse_profit_levels(levels_str)
        
        assert len(result) == 2
        assert result[0].threshold_pct == Decimal('20')
        assert result[0].position_allocation == Decimal('0.25')
        assert result[1].threshold_pct == Decimal('40')
        assert result[1].position_allocation == Decimal('0.5')
    
    def test_parse_profit_levels_empty_returns_defaults(self):
        """Test parsing empty profit levels returns defaults."""
        result = _parse_profit_levels("")
        
        assert len(result) == 2
        assert result[0].threshold_pct == Decimal('20')
        assert result[1].threshold_pct == Decimal('40')
    
    def test_parse_profit_levels_invalid_format(self):
        """Test parsing invalid profit levels format raises error."""
        with pytest.raises(ValueError, match="Invalid profit level format"):
            _parse_profit_levels("20-0.25,40:0.5")  # Wrong separator
    
    def test_parse_target_allocations_valid(self):
        """Test parsing valid target allocations string."""
        allocations_str = "BTC-EUR:0.6,ETH-EUR:0.4"
        result = _parse_target_allocations(allocations_str)
        
        expected = {
            "BTC-EUR": Decimal('0.6'),
            "ETH-EUR": Decimal('0.4')
        }
        assert result == expected
    
    def test_parse_target_allocations_exceeds_100_percent(self):
        """Test parsing allocations that exceed 100% raises error."""
        with pytest.raises(ValueError, match="Total target allocation"):
            _parse_target_allocations("BTC-EUR:0.6,ETH-EUR:0.6")  # Total = 1.2 > 1.0
    
    @patch.dict('os.environ', {
        'ASSET_PROTECTION_ENABLED': 'true',
        'PROTECTED_ASSETS': 'BTC-EUR,ETH-EUR',
        'MAX_PROTECTION_BUDGET': '50.0'
    })
    def test_load_asset_protection_config_enabled(self):
        """Test loading asset protection config when enabled."""
        config = _load_asset_protection_config()
        
        assert config.enabled is True
        assert config.protected_assets == ['BTC-EUR', 'ETH-EUR']
        assert config.max_protection_budget == Decimal('50.0')
    
    @patch.dict('os.environ', {'ASSET_PROTECTION_ENABLED': 'false'})
    def test_load_asset_protection_config_disabled(self):
        """Test loading asset protection config when disabled."""
        config = _load_asset_protection_config()
        
        assert config.enabled is False
        assert config.protected_assets == []


class TestVolatilityCalculator:
    """Test volatility calculator functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.mock_api = MagicMock()
        self.volatility_calc = VolatilityCalculator(self.mock_api)
    
    def test_init(self):
        """Test volatility calculator initialization."""
        assert self.volatility_calc.api == self.mock_api
        assert self.volatility_calc.cache_duration_minutes == 30
        assert self.volatility_calc._volatility_cache == {}
    
    def test_get_volatility_invalid_market(self):
        """Test volatility calculation with invalid market name."""
        result = self.volatility_calc.get_volatility("", 24)
        assert result is None
        
        result = self.volatility_calc.get_volatility("BTC", 24)  # Invalid format
        assert result is None
    
    def test_get_volatility_invalid_window(self):
        """Test volatility calculation with invalid window hours."""
        result = self.volatility_calc.get_volatility("BTC-EUR", 0)
        assert result is None
        
        result = self.volatility_calc.get_volatility("BTC-EUR", 200)  # Too large
        assert result is None
    
    def test_get_volatility_insufficient_data(self):
        """Test volatility calculation with insufficient price data."""
        # Mock API to return insufficient data
        self.mock_api.send_request.return_value = [
            [1640995200000, "45000", "45100", "44900", "45050", "100"]  # Only 1 candle
        ]
        
        result = self.volatility_calc.get_volatility("BTC-EUR", 24)
        assert result is None
    
    def test_get_volatility_valid_calculation(self):
        """Test volatility calculation with valid data."""
        # Mock API to return sample candle data
        candle_data = []
        base_price = 45000
        for i in range(20):
            # Create price movements with some volatility
            price_variation = (i % 5) * 100 - 200  # Range: -200 to +200
            price = base_price + price_variation
            candle = [
                1640995200000 + i * 900000,  # 15-minute intervals
                str(price - 10), str(price + 10), str(price - 15), str(price), "100"
            ]
            candle_data.append(candle)
        
        self.mock_api.send_request.return_value = candle_data
        
        result = self.volatility_calc.get_volatility("BTC-EUR", 24)
        assert result is not None
        assert isinstance(result, Decimal)
        assert result > Decimal('0')
    
    def test_get_volatility_caching(self):
        """Test that volatility results are cached properly."""
        # First call
        candle_data = [
            [1640995200000, "45000", "45100", "44900", "45050", "100"],
            [1640995200900, "45050", "45150", "44950", "45100", "100"],
            [1640995201800, "45100", "45200", "45000", "45150", "100"],
            [1640995202700, "45150", "45250", "45050", "45200", "100"],
            [1640995203600, "45200", "45300", "45100", "45250", "100"],
            [1640995204500, "45250", "45350", "45150", "45300", "100"],
            [1640995205400, "45300", "45400", "45200", "45350", "100"],
            [1640995206300, "45350", "45450", "45250", "45400", "100"],
            [1640995207200, "45400", "45500", "45300", "45450", "100"],
            [1640995208100, "45450", "45550", "45350", "45500", "100"],
        ]
        self.mock_api.send_request.return_value = candle_data
        
        result1 = self.volatility_calc.get_volatility("BTC-EUR", 24)
        assert self.mock_api.send_request.call_count == 1
        
        # Second call should use cache
        result2 = self.volatility_calc.get_volatility("BTC-EUR", 24)
        assert self.mock_api.send_request.call_count == 1  # Still 1, used cache
        assert result1 == result2
    
    def test_get_volatility_adjusted_stop_loss(self):
        """Test volatility-adjusted stop loss calculation."""
        # Mock volatility calculation
        with patch.object(self.volatility_calc, 'get_volatility', return_value=Decimal('10.0')):
            result = self.volatility_calc.get_volatility_adjusted_stop_loss(
                "BTC-EUR", Decimal('15.0'), Decimal('1.5')
            )
            # With 10% volatility and 1.5 multiplier, should adjust stop loss upward
            assert result > Decimal('15.0')
            assert result <= Decimal('50.0')  # Within maximum bound
    
    def test_clear_cache(self):
        """Test cache clearing functionality."""
        # Add something to cache
        self.volatility_calc._volatility_cache['test'] = {'data': 'value'}
        
        self.volatility_calc.clear_cache()
        assert len(self.volatility_calc._volatility_cache) == 0


class TestProtectedAssetStateManager:
    """Test protected asset state management."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.state_manager = ProtectedAssetStateManager(self.temp_dir)
    
    def teardown_method(self):
        """Cleanup test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_init(self):
        """Test state manager initialization."""
        assert self.state_manager.data_dir == self.temp_dir
        assert self.state_manager.state_file == self.temp_dir / "protected_assets.json"
        assert len(self.state_manager._state) == 0
    
    def test_add_protected_asset_valid(self):
        """Test adding a valid protected asset."""
        self.state_manager.add_protected_asset(
            market="BTC-EUR",
            entry_price=Decimal('45000'),
            initial_investment_eur=Decimal('100'),
            target_allocation_pct=Decimal('0.6')
        )
        
        assert "BTC-EUR" in self.state_manager._state
        asset_info = self.state_manager._state["BTC-EUR"]
        assert asset_info.market == "BTC-EUR"
        assert asset_info.entry_price == Decimal('45000')
        assert asset_info.current_position_eur == Decimal('100')
        assert asset_info.target_allocation_pct == Decimal('0.6')
    
    def test_add_protected_asset_invalid_price(self):
        """Test adding protected asset with invalid price."""
        self.state_manager.add_protected_asset(
            market="BTC-EUR",
            entry_price=Decimal('0'),  # Invalid price
            initial_investment_eur=Decimal('100')
        )
        
        # Should not be added
        assert "BTC-EUR" not in self.state_manager._state
    
    def test_add_protected_asset_duplicate(self):
        """Test adding duplicate protected asset."""
        # Add first time
        self.state_manager.add_protected_asset(
            market="BTC-EUR",
            entry_price=Decimal('45000'),
            initial_investment_eur=Decimal('100')
        )
        
        # Try to add again
        self.state_manager.add_protected_asset(
            market="BTC-EUR",
            entry_price=Decimal('50000'),
            initial_investment_eur=Decimal('200')
        )
        
        # Should still have original values
        asset_info = self.state_manager._state["BTC-EUR"]
        assert asset_info.entry_price == Decimal('45000')
        assert asset_info.total_invested_eur == Decimal('100')
    
    def test_remove_protected_asset(self):
        """Test removing a protected asset."""
        # Add asset first
        self.state_manager.add_protected_asset(
            market="BTC-EUR",
            entry_price=Decimal('45000'),
            initial_investment_eur=Decimal('100')
        )
        
        # Remove it
        result = self.state_manager.remove_protected_asset("BTC-EUR")
        
        assert result is True
        assert "BTC-EUR" not in self.state_manager._state
    
    def test_remove_nonexistent_asset(self):
        """Test removing non-existent asset."""
        result = self.state_manager.remove_protected_asset("NONEXISTENT-EUR")
        assert result is False
    
    def test_record_trade_dca_buy(self):
        """Test recording a DCA buy trade."""
        # Add asset first
        self.state_manager.add_protected_asset(
            market="BTC-EUR",
            entry_price=Decimal('45000'),
            initial_investment_eur=Decimal('100')
        )
        
        # Record DCA buy
        result = self.state_manager.record_trade(
            market="BTC-EUR",
            trade_type="dca_buy",
            price=Decimal('40000'),
            amount_eur=Decimal('50'),
            amount_crypto=Decimal('0.00125'),
            reason="DCA level 1: 10% drop"
        )
        
        assert result is True
        asset_info = self.state_manager._state["BTC-EUR"]
        assert len(asset_info.trade_history) == 1
        assert asset_info.total_invested_eur > Decimal('100')  # Should increase
        
        # Check trade record
        trade = asset_info.trade_history[0]
        assert trade.trade_type == "dca_buy"
        assert trade.amount_eur == Decimal('50')
        assert trade.reason == "DCA level 1: 10% drop"
    
    def test_record_trade_profit_sell(self):
        """Test recording a profit taking sell trade."""
        # Add asset first
        self.state_manager.add_protected_asset(
            market="BTC-EUR",
            entry_price=Decimal('45000'),
            initial_investment_eur=Decimal('100')
        )
        
        # Record profit sell
        result = self.state_manager.record_trade(
            market="BTC-EUR",
            trade_type="profit_sell",
            price=Decimal('54000'),
            amount_eur=Decimal('25'),
            amount_crypto=Decimal('0.000463'),
            reason="Profit level 1: 20% gain"
        )
        
        assert result is True
        asset_info = self.state_manager._state["BTC-EUR"]
        assert len(asset_info.trade_history) == 1
        assert asset_info.current_position_eur < Decimal('100')  # Should decrease
    
    def test_can_trade_today_within_limit(self):
        """Test daily trade limit check within limits."""
        # Add asset first
        self.state_manager.add_protected_asset(
            market="BTC-EUR",
            entry_price=Decimal('45000'),
            initial_investment_eur=Decimal('100')
        )
        
        # Should be able to trade initially
        assert self.state_manager.can_trade_today("BTC-EUR", 5) is True
        
        # Record a trade
        self.state_manager.record_trade(
            market="BTC-EUR",
            trade_type="dca_buy",
            price=Decimal('40000'),
            amount_eur=Decimal('50'),
            amount_crypto=Decimal('0.00125'),
            reason="Test trade"
        )
        
        # Should still be able to trade (1 < 5)
        assert self.state_manager.can_trade_today("BTC-EUR", 5) is True
    
    def test_can_trade_today_exceed_limit(self):
        """Test daily trade limit check when limit exceeded."""
        # Add asset first
        self.state_manager.add_protected_asset(
            market="BTC-EUR",
            entry_price=Decimal('45000'),
            initial_investment_eur=Decimal('100')
        )
        
        # Record multiple trades to exceed limit
        for i in range(3):
            self.state_manager.record_trade(
                market="BTC-EUR",
                trade_type="dca_buy",
                price=Decimal('40000'),
                amount_eur=Decimal('10'),
                amount_crypto=Decimal('0.00025'),
                reason=f"Test trade {i}"
            )
        
        # Should not be able to trade (3 >= 3)
        assert self.state_manager.can_trade_today("BTC-EUR", 3) is False
    
    def test_update_stop_loss(self):
        """Test updating dynamic stop loss."""
        # Add asset first
        self.state_manager.add_protected_asset(
            market="BTC-EUR",
            entry_price=Decimal('45000'),
            initial_investment_eur=Decimal('100')
        )
        
        # Update stop loss
        self.state_manager.update_stop_loss("BTC-EUR", Decimal('18.5'))
        
        asset_info = self.state_manager._state["BTC-EUR"]
        assert asset_info.current_stop_loss_pct == Decimal('18.5')
        assert asset_info.last_volatility_check.date() == datetime.now().date()
    
    def test_mark_dca_level_completed(self):
        """Test marking DCA level as completed."""
        # Add asset first
        self.state_manager.add_protected_asset(
            market="BTC-EUR",
            entry_price=Decimal('45000'),
            initial_investment_eur=Decimal('100')
        )
        
        # Mark level completed
        self.state_manager.mark_dca_level_completed("BTC-EUR", 1)
        
        asset_info = self.state_manager._state["BTC-EUR"]
        assert 1 in asset_info.completed_dca_levels
    
    def test_mark_profit_level_completed(self):
        """Test marking profit level as completed."""
        # Add asset first
        self.state_manager.add_protected_asset(
            market="BTC-EUR",
            entry_price=Decimal('45000'),
            initial_investment_eur=Decimal('100')
        )
        
        # Mark level completed
        self.state_manager.mark_profit_level_completed("BTC-EUR", 1)
        
        asset_info = self.state_manager._state["BTC-EUR"]
        assert 1 in asset_info.completed_profit_levels
    
    def test_get_portfolio_summary_empty(self):
        """Test portfolio summary with no assets."""
        summary = self.state_manager.get_portfolio_summary()
        
        assert summary['total_assets'] == 0
        assert summary['total_current_value_eur'] == 0
        assert summary['total_invested_eur'] == 0
        assert summary['unrealized_pnl_eur'] == 0
    
    def test_get_portfolio_summary_with_assets(self):
        """Test portfolio summary with assets."""
        # Add two assets
        self.state_manager.add_protected_asset(
            market="BTC-EUR",
            entry_price=Decimal('45000'),
            initial_investment_eur=Decimal('100')
        )
        self.state_manager.add_protected_asset(
            market="ETH-EUR",
            entry_price=Decimal('3000'),
            initial_investment_eur=Decimal('50')
        )
        
        summary = self.state_manager.get_portfolio_summary()
        
        assert summary['total_assets'] == 2
        assert summary['total_current_value_eur'] == 150
        assert summary['total_invested_eur'] == 150
        assert summary['unrealized_pnl_pct'] == 0  # No gains/losses yet
    
    def test_save_and_load_state(self):
        """Test saving and loading state persistence."""
        # Add asset
        self.state_manager.add_protected_asset(
            market="BTC-EUR",
            entry_price=Decimal('45000'),
            initial_investment_eur=Decimal('100')
        )
        
        # Record a trade
        self.state_manager.record_trade(
            market="BTC-EUR",
            trade_type="dca_buy",
            price=Decimal('40000'),
            amount_eur=Decimal('50'),
            amount_crypto=Decimal('0.00125'),
            reason="Test trade"
        )
        
        # Create new state manager and load
        new_state_manager = ProtectedAssetStateManager(self.temp_dir)
        
        # Should have loaded the asset
        assert "BTC-EUR" in new_state_manager._state
        asset_info = new_state_manager._state["BTC-EUR"]
        
        # After DCA trade, entry price should be recalculated as weighted average
        # Original: 100 EUR at 45000 = 0.002222 BTC
        # DCA: 50 EUR at 40000 = 0.00125 BTC  
        # Total: 150 EUR, 0.003472 BTC -> new entry price = 150/0.003472 ≈ 43200
        expected_entry_price = Decimal('150') / (Decimal('100')/Decimal('45000') + Decimal('0.00125'))
        assert abs(asset_info.entry_price - expected_entry_price) < Decimal('0.1')  # Allow small rounding differences
        
        assert len(asset_info.trade_history) == 1
        assert asset_info.trade_history[0].trade_type == "dca_buy"


class TestAssetProtectionManager:
    """Test asset protection manager integration."""
    
    def setup_method(self):
        """Setup test fixtures."""
        # Create mock dependencies
        self.mock_api = MagicMock()
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Create minimal configs
        self.asset_protection_config = AssetProtectionConfig(
            enabled=True,
            protected_assets=["BTC-EUR", "ETH-EUR"],
            max_protection_budget=Decimal('100'),
            dca_levels=[
                DipLevel(threshold_pct=Decimal('10'), capital_allocation=Decimal('0.5')),
                DipLevel(threshold_pct=Decimal('20'), capital_allocation=Decimal('0.5'))
            ],
            profit_levels=[
                ProfitLevel(threshold_pct=Decimal('20'), position_allocation=Decimal('0.5'))
            ]
        )
        
        self.trading_config = TradingConfig(
            min_profit_pct=Decimal('5'),
            trailing_pct=Decimal('3'),
            max_trade_amount=Decimal('10'),
            check_interval=10,
            max_retries=3,
            retry_delay=5,
            operator_id=1001
        )
        
        self.manager = AssetProtectionManager(
            api=self.mock_api,
            config=self.asset_protection_config,
            trading_config=self.trading_config,
            data_dir=self.temp_dir,
            check_interval=30
        )
    
    def teardown_method(self):
        """Cleanup test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_init(self):
        """Test asset protection manager initialization."""
        assert self.manager.api == self.mock_api
        assert self.manager.config == self.asset_protection_config
        assert self.manager.trading_config == self.trading_config
        assert isinstance(self.manager.volatility_calc, VolatilityCalculator)
        assert isinstance(self.manager.state_manager, ProtectedAssetStateManager)
    
    def test_start_stop_disabled(self):
        """Test start/stop when asset protection is disabled."""
        # Create manager with disabled config
        disabled_config = AssetProtectionConfig(enabled=False)
        disabled_manager = AssetProtectionManager(
            api=self.mock_api,
            config=disabled_config,
            trading_config=self.trading_config,
            data_dir=self.temp_dir
        )
        
        disabled_manager.start()
        assert disabled_manager._monitor_thread is None
        
        disabled_manager.stop()  # Should not raise any errors
    
    def test_start_stop_no_assets(self):
        """Test start/stop when no protected assets configured."""
        # Create manager with no assets
        no_assets_config = AssetProtectionConfig(enabled=True, protected_assets=[])
        no_assets_manager = AssetProtectionManager(
            api=self.mock_api,
            config=no_assets_config,
            trading_config=self.trading_config,
            data_dir=self.temp_dir
        )
        
        no_assets_manager.start()
        assert no_assets_manager._monitor_thread is None
    
    @patch('time.sleep')  # Mock sleep to speed up tests
    def test_initialize_protected_assets(self, mock_sleep):
        """Test initialization of protected assets."""
        # Mock API responses
        self.mock_api.send_request.side_effect = [
            # Price response for BTC-EUR
            {'price': '45000.0'},
            # Balance response for BTC-EUR
            [{'symbol': 'BTC', 'available': '0.002', 'inOrder': '0'}],
            # Price response for ETH-EUR
            {'price': '3000.0'},
            # Balance response for ETH-EUR
            [{'symbol': 'ETH', 'available': '0.03', 'inOrder': '0'}]
        ]
        
        self.manager._initialize_protected_assets()
        
        # Check that assets were added to state manager
        protected_assets = self.manager.state_manager.get_all_protected_assets()
        assert "BTC-EUR" in protected_assets
        assert "ETH-EUR" in protected_assets
        
        # Verify correct initialization values
        btc_info = protected_assets["BTC-EUR"]
        assert btc_info.entry_price == Decimal('45000.0')
        assert btc_info.current_position_eur == Decimal('45000.0') * Decimal('0.002')
    
    def test_get_current_price(self):
        """Test getting current market price."""
        # Mock successful price response
        self.mock_api.send_request.return_value = {'price': '45000.0'}
        
        result = self.manager._get_current_price("BTC-EUR")
        assert result == Decimal('45000.0')
        
        # Mock failed response
        self.mock_api.send_request.return_value = None
        result = self.manager._get_current_price("BTC-EUR")
        assert result is None
    
    def test_get_current_balance(self):
        """Test getting current balance for an asset."""
        # Mock balance response
        self.mock_api.send_request.return_value = [
            {'symbol': 'BTC', 'available': '0.002', 'inOrder': '0'},
            {'symbol': 'ETH', 'available': '0.05', 'inOrder': '0'}
        ]
        
        result = self.manager._get_current_balance("BTC-EUR")
        assert result == Decimal('0.002')
        
        result = self.manager._get_current_balance("ETH-EUR")
        assert result == Decimal('0.05')
        
        # Non-existent asset
        result = self.manager._get_current_balance("NONEXISTENT-EUR")
        assert result == Decimal('0')
    
    def test_has_daily_budget(self):
        """Test daily budget checking."""
        # Initially should have full budget
        assert self.manager._has_daily_budget(Decimal('50')) is True
        assert self.manager._has_daily_budget(Decimal('100')) is True
        assert self.manager._has_daily_budget(Decimal('101')) is False
        
        # Spend some budget
        self.manager._daily_spent = Decimal('60')
        assert self.manager._has_daily_budget(Decimal('30')) is True
        assert self.manager._has_daily_budget(Decimal('40')) is True
        assert self.manager._has_daily_budget(Decimal('41')) is False
    
    def test_reset_daily_budget(self):
        """Test daily budget reset functionality."""
        # Spend some budget
        self.manager._daily_spent = Decimal('50')
        
        # Set last reset to yesterday
        yesterday = datetime.now().date() - timedelta(days=1)
        self.manager._last_budget_reset = yesterday
        
        # Reset should occur
        self.manager._reset_daily_budget_if_needed()
        
        assert self.manager._daily_spent == Decimal('0')
        assert self.manager._last_budget_reset == datetime.now().date()
    
    def test_get_status_summary(self):
        """Test status summary generation."""
        # Add some test asset to state
        self.manager.state_manager.add_protected_asset(
            market="BTC-EUR",
            entry_price=Decimal('45000'),
            initial_investment_eur=Decimal('100')
        )
        
        status = self.manager.get_status_summary()
        
        assert status['enabled'] is True
        assert status['protected_assets_count'] == 1
        assert status['total_protected_value_eur'] == 100
        assert 'daily_budget_used_eur' in status
        assert 'daily_budget_remaining_eur' in status
        assert 'BTC-EUR' in status['protected_markets']


if __name__ == '__main__':
    pytest.main([__file__])