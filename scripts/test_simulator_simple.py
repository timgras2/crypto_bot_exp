#!/usr/bin/env python3
"""
Simple ASCII-only test for the dip buying simulator
"""

import logging
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_mock_api():
    """Test the mock API functionality."""
    print("[TEST] Testing Mock API...")
    
    from simulator.mock_api import MockBitvavoAPI
    
    # Initialize mock API
    start_time = datetime(2024, 1, 1, 9, 0)
    mock_api = MockBitvavoAPI(start_time)
    
    # Test price request
    response = mock_api.send_request("GET", "/ticker/price?market=BTC-EUR")
    assert response is not None, "Price request should return data"
    assert "price" in response, "Response should contain price"
    
    print(f"   [OK] Price request returned: {response['price']}")
    
    # Test order placement
    order_response = mock_api.send_request("POST", "/order", {
        "market": "BTC-EUR",
        "side": "buy",
        "orderType": "market",
        "amountQuote": "10.0",
        "operatorId": 1001
    })
    
    assert order_response is not None, "Order should be executed"
    assert "orderId" in order_response, "Order should have ID"
    
    print(f"   [OK] Order executed with ID: {order_response['orderId']}")
    
    # Test balance
    balance_response = mock_api.send_request("GET", "/balance")
    assert balance_response is not None, "Balance request should work"
    assert len(balance_response) > 0, "Should have at least EUR balance"
    
    print(f"   [OK] Balance shows {len(balance_response)} currencies")
    
    print("[PASS] Mock API tests passed!")
    return True


def test_basic_simulation():
    """Test a very short simulation."""
    print("\n[TEST] Testing Basic Simulation...")
    
    from simulator.simulation_engine import SimulationEngine, SimulationConfig
    from src.config import DipLevel
    
    # Very short simulation for testing
    config = SimulationConfig(
        start_time=datetime(2024, 1, 1, 9, 0),
        end_time=datetime(2024, 1, 1, 10, 0),  # Just 1 hour
        initial_balance_eur=Decimal("100"),
        max_trade_amount=Decimal("5"),
        simulation_speed=60.0,  # 1 hour = 1 minute
        assets_to_simulate=["TEST-EUR"],  # Single test asset
        dip_buy_enabled=True,
        dip_levels=[
            DipLevel(threshold_pct=Decimal('10'), capital_allocation=Decimal('1.0'))
        ]
    )
    
    try:
        print("   [INFO] Creating simulation engine...")
        engine = SimulationEngine(config)
        
        print("   [INFO] Running simulation...")
        results = engine.run_simulation()
        
        assert results.total_trades >= 1, "Should have at least one trade"
        assert results.final_portfolio is not None, "Should have final portfolio"
        
        print(f"   [OK] Simulation completed successfully")
        print(f"   [INFO] Total trades: {results.total_trades}")
        print(f"   [INFO] Final P&L: EUR {results.total_profit_loss_eur:.2f}")
        print(f"   [INFO] Duration: {results.duration}")
        
        print("[PASS] Simulation engine tests passed!")
        return results
        
    except Exception as e:
        print(f"   [ERROR] Simulation failed: {e}")
        raise


def test_configuration():
    """Test configuration loading."""
    print("\n[TEST] Testing Configuration...")
    
    from simulator.simulation_engine import SimulationConfig
    from src.config import DipLevel
    
    # Test basic config creation
    config = SimulationConfig(
        start_time=datetime(2024, 1, 1),
        end_time=datetime(2024, 1, 2),
        initial_balance_eur=Decimal("1000")
    )
    
    assert config.initial_balance_eur == Decimal("1000")
    assert config.assets_to_simulate is not None
    assert len(config.dip_levels) > 0
    
    print("   [OK] Basic configuration works")
    
    # Test custom dip levels
    custom_levels = [
        DipLevel(threshold_pct=Decimal('5'), capital_allocation=Decimal('0.5')),
        DipLevel(threshold_pct=Decimal('15'), capital_allocation=Decimal('0.5'))
    ]
    
    config_custom = SimulationConfig(
        start_time=datetime(2024, 1, 1),
        end_time=datetime(2024, 1, 2),
        dip_levels=custom_levels
    )
    
    assert len(config_custom.dip_levels) == 2
    assert config_custom.dip_levels[0].threshold_pct == Decimal('5')
    
    print("   [OK] Custom dip levels work")
    
    print("[PASS] Configuration tests passed!")
    return True


def main():
    """Run all tests."""
    print("Dip Buy Simulator Tests")
    print("=" * 40)
    
    # Reduce log noise for testing
    logging.basicConfig(level=logging.ERROR)
    
    try:
        # Run tests in order
        print("Running component tests...")
        test_mock_api()
        test_configuration()
        
        print("\nRunning integration test...")
        results = test_basic_simulation()
        
        print("\n" + "=" * 40)
        print("ALL TESTS PASSED!")
        print("=" * 40)
        
        print("\nQuick Results Summary:")
        print(f"  Duration: {results.duration}")
        print(f"  Total Trades: {results.total_trades}")
        print(f"  Dip Rebuys: {results.successful_dip_rebuys}")
        print(f"  Final P&L: EUR {results.total_profit_loss_eur:.2f}")
        print(f"  Return: {results.profit_loss_pct:+.1f}%")
        
        print(f"\nSimulator is ready to use!")
        print(f"Run 'python run_simulation.py' to start testing")
        
        return 0
        
    except Exception as e:
        print(f"\nTESTS FAILED: {e}")
        logging.exception("Test error")
        return 1


if __name__ == "__main__":
    sys.exit(main())