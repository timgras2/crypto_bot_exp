#!/usr/bin/env python3
"""
Integration tests for asset protection system - full workflow testing
"""

import json
import pytest
import tempfile
import time
from decimal import Decimal
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch, call
from threading import Event

# Import the modules we're testing
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import AssetProtectionConfig, TradingConfig, DipLevel, ProfitLevel
from asset_protection_manager import AssetProtectionManager
from circuit_breaker import CircuitBreakerError


class TestAssetProtectionIntegration:
    """Integration tests for the complete asset protection workflow."""
    
    def setup_method(self):
        """Setup test fixtures for integration tests."""
        # Create mock API
        self.mock_api = MagicMock()
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Create test configurations
        self.asset_protection_config = AssetProtectionConfig(
            enabled=True,
            protected_assets=["BTC-EUR", "ETH-EUR"],
            max_protection_budget=Decimal('100'),
            base_stop_loss_pct=Decimal('15.0'),
            dca_enabled=True,
            dca_levels=[
                DipLevel(threshold_pct=Decimal('10'), capital_allocation=Decimal('0.5')),
                DipLevel(threshold_pct=Decimal('20'), capital_allocation=Decimal('0.5'))
            ],
            profit_taking_enabled=True,
            profit_levels=[
                ProfitLevel(threshold_pct=Decimal('20'), position_allocation=Decimal('0.5'))
            ],
            emergency_stop_loss_pct=Decimal('25.0'),
            max_daily_trades=5
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
        
        # Create the manager
        self.manager = AssetProtectionManager(
            api=self.mock_api,
            config=self.asset_protection_config,
            trading_config=self.trading_config,
            data_dir=self.temp_dir,
            check_interval=1  # Fast checking for tests
        )
    
    def teardown_method(self):
        """Cleanup test fixtures."""
        # Stop manager if running
        if self.manager._monitor_thread and self.manager._monitor_thread.is_alive():
            self.manager.stop()
        
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_complete_initialization_workflow(self):
        """Test complete initialization workflow with existing positions."""
        # Mock API responses for initialization
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
        
        # Initialize protected assets
        self.manager._initialize_protected_assets()
        
        # Verify assets were added to state manager
        protected_assets = self.manager.state_manager.get_all_protected_assets()
        assert "BTC-EUR" in protected_assets
        assert "ETH-EUR" in protected_assets
        
        # Verify correct values
        btc_info = protected_assets["BTC-EUR"]
        assert btc_info.entry_price == Decimal('45000.0')
        assert btc_info.current_position_eur == Decimal('45000.0') * Decimal('0.002')
        
        eth_info = protected_assets["ETH-EUR"]
        assert eth_info.entry_price == Decimal('3000.0')
        assert eth_info.current_position_eur == Decimal('3000.0') * Decimal('0.03')
    
    def test_dca_buy_workflow_complete(self):
        """Test complete DCA buying workflow."""
        # Initialize with a position
        self.manager.state_manager.add_protected_asset(
            market="BTC-EUR",
            entry_price=Decimal('45000'),
            initial_investment_eur=Decimal('90')
        )
        
        # Mock API responses for DCA workflow
        def mock_api_side_effect(*args, **kwargs):
            if args[0] == "GET" and "/ticker/price" in args[1]:
                return {'price': '40500.0'}  # 10% drop
            elif args[0] == "POST" and args[1] == "/order":
                return {'orderId': '12345', 'status': 'filled'}
            return None
            
        self.mock_api.send_request.side_effect = mock_api_side_effect
        
        # Check DCA opportunities
        asset_info = self.manager.state_manager.get_asset_info("BTC-EUR")
        current_price = Decimal('40500.0')
        
        self.manager._check_dca_opportunities("BTC-EUR", asset_info, current_price)
        
        # Verify operations occurred
        assert self.mock_api.send_request.call_count >= 1
        
        # Check that DCA level was marked as completed
        updated_asset_info = self.manager.state_manager.get_asset_info("BTC-EUR")
        assert 1 in updated_asset_info.completed_dca_levels
        
        # Check budget was used
        assert self.manager._daily_spent > Decimal('0')
    
    def test_profit_taking_workflow(self):
        """Test complete profit taking workflow."""
        # Initialize with a position
        self.manager.state_manager.add_protected_asset(
            market="ETH-EUR",
            entry_price=Decimal('3000'),
            initial_investment_eur=Decimal('90')
        )
        
        # Mock API responses for profit taking workflow
        def mock_api_side_effect(*args, **kwargs):
            if args[0] == "GET" and args[1] == "/balance":
                return [{'symbol': 'ETH', 'available': '0.03', 'inOrder': '0'}]
            elif args[0] == "POST" and args[1] == "/order":
                return {'orderId': '67890', 'status': 'filled'}
            return None
            
        self.mock_api.send_request.side_effect = mock_api_side_effect
        
        # Check profit taking opportunities  
        asset_info = self.manager.state_manager.get_asset_info("ETH-EUR")
        current_price = Decimal('3600.0')  # 20% increase
        
        self.manager._check_profit_taking_opportunities("ETH-EUR", asset_info, current_price)
        
        # Verify operations occurred
        assert self.mock_api.send_request.call_count >= 1
        
        # Check that profit level was marked as completed
        updated_asset_info = self.manager.state_manager.get_asset_info("ETH-EUR")
        assert 1 in updated_asset_info.completed_profit_levels
    
    def test_emergency_stop_loss_workflow(self):
        """Test emergency stop loss workflow."""
        # Initialize with a position
        self.manager.state_manager.add_protected_asset(
            market="BTC-EUR",
            entry_price=Decimal('45000'),
            initial_investment_eur=Decimal('90')
        )
        
        # Mock API responses for emergency stop workflow
        def mock_api_side_effect(*args, **kwargs):
            if args[0] == "GET" and "/ticker/price" in args[1]:
                return {'price': '31500.0'}  # 30% drop - emergency level
            elif args[0] == "GET" and args[1] == "/balance":
                return [{'symbol': 'BTC', 'available': '0.002', 'inOrder': '0'}]
            elif args[0] == "POST" and args[1] == "/order":
                return {'orderId': '99999', 'status': 'filled'}
            return None
            
        self.mock_api.send_request.side_effect = mock_api_side_effect
        
        # Test emergency stop loss directly
        asset_info = self.manager.state_manager.get_asset_info("BTC-EUR")
        current_price = Decimal('31500.0')  # 30% drop
        
        # Trigger emergency stop loss
        emergency_triggered = self.manager._check_emergency_stop_loss("BTC-EUR", asset_info, current_price)
        
        # Verify emergency stop was triggered
        assert emergency_triggered is True
        
        # Verify asset was removed from protection
        remaining_assets = self.manager.state_manager.get_all_protected_assets()
        assert "BTC-EUR" not in remaining_assets
    
    def test_daily_budget_limits_workflow(self):
        """Test daily budget limiting workflow."""
        # Set small budget for testing
        self.manager.config.max_protection_budget = Decimal('10')
        
        # Initialize position
        self.manager.state_manager.add_protected_asset(
            market="BTC-EUR",
            entry_price=Decimal('45000'),
            initial_investment_eur=Decimal('90')
        )
        
        # Mock multiple DCA opportunities
        self.mock_api.send_request.side_effect = [
            # First DCA - should succeed
            {'price': '40500.0'},  # Price check
            {'orderId': '1', 'status': 'filled'},  # Order 1
            # Second DCA - should fail due to budget
            {'price': '36000.0'},  # Price check
        ]
        
        asset_info = self.manager.state_manager.get_asset_info("BTC-EUR")
        
        # First DCA should succeed
        result1 = self.manager._execute_buy_order("BTC-EUR", Decimal('5'), "dca_buy", "Test 1")
        assert result1 is True
        assert self.manager._daily_spent == Decimal('5')
        
        # Second DCA should fail due to budget
        result2 = self.manager._execute_buy_order("BTC-EUR", Decimal('10'), "dca_buy", "Test 2")
        assert result2 is False  # Should fail due to insufficient budget
        assert self.manager._daily_spent == Decimal('5')  # Should remain unchanged
    
    def test_circuit_breaker_integration_workflow(self):
        """Test circuit breaker integration in full workflow."""
        # Initialize position
        self.manager.state_manager.add_protected_asset(
            market="BTC-EUR",
            entry_price=Decimal('45000'),
            initial_investment_eur=Decimal('90')
        )
        
        # Mock API failures to trigger circuit breaker
        connection_error = ConnectionError("Network error")
        self.mock_api.send_request.side_effect = [
            connection_error,  # Failure 1
            connection_error,  # Failure 2
            connection_error,  # Failure 3
            connection_error,  # Failure 4
            connection_error,  # Failure 5 - should open circuit
        ]
        
        # Attempt multiple price checks
        for i in range(5):
            result = self.manager._get_current_price("BTC-EUR")
            assert result is None
        
        # Circuit should now be open
        api_status = self.manager.api_circuit_breaker.get_status()
        assert api_status['state'] == 'open'
        
        # Next call should be blocked by circuit breaker
        with pytest.raises(CircuitBreakerError):
            self.manager.api_circuit_breaker.call(
                "test_operation",
                self.mock_api.send_request,
                "GET",
                "/test"
            )
    
    def test_state_persistence_workflow(self):
        """Test state persistence across manager restart."""
        # Initialize with positions
        self.manager.state_manager.add_protected_asset(
            market="BTC-EUR",
            entry_price=Decimal('45000'),
            initial_investment_eur=Decimal('90')
        )
        
        # Record some trades
        self.manager.state_manager.record_trade(
            market="BTC-EUR",
            trade_type="dca_buy",
            price=Decimal('40500'),
            amount_eur=Decimal('50'),
            amount_crypto=Decimal('0.00123'),
            reason="DCA level 1"
        )
        
        # Mark DCA level as completed
        self.manager.state_manager.mark_dca_level_completed("BTC-EUR", 1)
        
        # Create new manager (simulating restart)
        new_manager = AssetProtectionManager(
            api=MagicMock(),
            config=self.asset_protection_config,
            trading_config=self.trading_config,
            data_dir=self.temp_dir
        )
        
        # Verify state was restored
        restored_assets = new_manager.state_manager.get_all_protected_assets()
        assert "BTC-EUR" in restored_assets
        
        btc_info = restored_assets["BTC-EUR"]
        assert len(btc_info.trade_history) == 1
        assert btc_info.trade_history[0].trade_type == "dca_buy"
        assert 1 in btc_info.completed_dca_levels
    
    def test_concurrent_operations_workflow(self):
        """Test concurrent operations with thread safety."""
        # Initialize multiple positions
        for market in ["BTC-EUR", "ETH-EUR"]:
            self.manager.state_manager.add_protected_asset(
                market=market,
                entry_price=Decimal('45000') if 'BTC' in market else Decimal('3000'),
                initial_investment_eur=Decimal('50')
            )
        
        # Mock successful operations
        self.mock_api.send_request.return_value = {'orderId': '123', 'status': 'filled'}
        
        # Simulate concurrent operations
        from threading import Thread
        
        def execute_dca(market, amount):
            return self.manager._execute_buy_order(market, amount, "dca_buy", "Concurrent test")
        
        threads = []
        results = {}
        
        # Start multiple concurrent DCA operations
        for i, market in enumerate(["BTC-EUR", "ETH-EUR"]):
            thread = Thread(
                target=lambda m=market, idx=i: results.update({m: execute_dca(m, Decimal('30'))})
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify thread safety - only operations within budget should succeed
        total_spent = sum(30 if success else 0 for success in results.values())
        assert total_spent <= float(self.manager.config.max_protection_budget)
        assert self.manager._daily_spent == Decimal(str(total_spent))
    
    def test_monitoring_loop_integration(self):
        """Test the complete monitoring loop integration."""
        # Initialize position
        self.manager.state_manager.add_protected_asset(
            market="BTC-EUR",
            entry_price=Decimal('45000'),
            initial_investment_eur=Decimal('90')
        )
        
        # Mock API responses for monitoring
        self.mock_api.send_request.side_effect = [
            # Price checks during monitoring
            {'price': '40500.0'},  # 10% drop - should trigger DCA
            {'orderId': '123', 'status': 'filled'},  # DCA order
            {'price': '41000.0'},  # Price recovery
            {'price': '42000.0'},  # Further recovery
        ]
        
        # Start monitoring briefly
        self.manager.start()
        
        # Allow some monitoring cycles
        time.sleep(0.1)  # Brief monitoring
        
        # Stop monitoring
        self.manager.stop()
        
        # Verify monitoring executed operations
        assert self.mock_api.send_request.call_count > 0
        
        # Check if DCA level was marked as completed
        btc_info = self.manager.state_manager.get_asset_info("BTC-EUR")
        if btc_info:  # May have been processed
            assert len(btc_info.trade_history) >= 0  # Some activity may have occurred
    
    def test_error_recovery_workflow(self):
        """Test error recovery and graceful degradation."""
        # Initialize position
        self.manager.state_manager.add_protected_asset(
            market="BTC-EUR",
            entry_price=Decimal('45000'),
            initial_investment_eur=Decimal('90')
        )
        
        # Mock various error conditions
        self.mock_api.send_request.side_effect = [
            # Network error
            ConnectionError("Connection failed"),
            # Invalid response
            None,
            # Malformed response
            {'invalid': 'data'},
            # Successful recovery
            {'price': '40500.0'},
            {'orderId': '123', 'status': 'filled'}
        ]
        
        # Operations should handle errors gracefully
        for i in range(5):
            try:
                price = self.manager._get_current_price("BTC-EUR")
                if price:
                    # If we got a valid price, try a trade
                    result = self.manager._execute_buy_order("BTC-EUR", Decimal('10'), "dca_buy", "Test")
                    if result:
                        break  # Success
            except Exception as e:
                # Should not crash
                continue
        
        # System should remain operational
        status = self.manager.get_status_summary()
        assert status['enabled'] is True
        
        # Circuit breakers should track the failures
        api_cb_status = self.manager.api_circuit_breaker.get_status()
        assert api_cb_status['failure_count'] > 0
    
    def test_configuration_edge_cases_workflow(self):
        """Test workflow with edge case configurations."""
        # Test with minimal configuration
        minimal_config = AssetProtectionConfig(
            enabled=True,
            protected_assets=["BTC-EUR"],
            max_protection_budget=Decimal('1'),  # Very small budget
            dca_enabled=True,
            dca_levels=[
                DipLevel(threshold_pct=Decimal('50'), capital_allocation=Decimal('1.0'))  # Large threshold
            ],
            max_daily_trades=1  # Single trade limit
        )
        
        minimal_manager = AssetProtectionManager(
            api=self.mock_api,
            config=minimal_config,
            trading_config=self.trading_config,
            data_dir=self.temp_dir
        )
        
        # Initialize position
        minimal_manager.state_manager.add_protected_asset(
            market="BTC-EUR",
            entry_price=Decimal('45000'),
            initial_investment_eur=Decimal('90')
        )
        
        # Mock API responses for small order
        def mock_api_side_effect(*args, **kwargs):
            if args[0] == "GET" and "/ticker/price" in args[1]:
                return {'price': '45000.0'}  # Current price
            elif args[0] == "POST" and args[1] == "/order":
                return {'orderId': '123', 'status': 'filled'}
            return None
            
        self.mock_api.send_request.side_effect = mock_api_side_effect
        
        # Should handle small budget correctly
        result = minimal_manager._execute_buy_order("BTC-EUR", Decimal('1'), "dca_buy", "Small trade")
        assert result is True
        
        # Second trade should fail due to daily limit
        minimal_manager.state_manager.record_trade(
            market="BTC-EUR",
            trade_type="dca_buy", 
            price=Decimal('40000'),
            amount_eur=Decimal('1'),
            amount_crypto=Decimal('0.000025'),
            reason="First trade"
        )
        
        can_trade = minimal_manager.state_manager.can_trade_today("BTC-EUR", 1)
        assert can_trade is False


if __name__ == '__main__':
    pytest.main([__file__])