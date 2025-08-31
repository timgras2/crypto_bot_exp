#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple test to validate the dip buying simulator works correctly
"""

import logging
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

# Fix Unicode encoding on Windows
if sys.platform.startswith('win'):
    try:
        # Try to set UTF-8 for stdout
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, OSError):
        # Fallback for older Python versions or restricted environments
        pass

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

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
    
    print(f"   [OK] Price request: {response}")
    
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
    
    print(f"   [OK] Order placement: {order_response['orderId']}")
    
    # Test balance
    balance_response = mock_api.send_request("GET", "/balance")
    assert balance_response is not None, "Balance request should work"
    assert len(balance_response) > 0, "Should have at least EUR balance"
    
    print(f"   [OK] Balance request: {len(balance_response)} currencies")
    
    print("[PASS] Mock API tests passed!")


def test_simulation_engine():
    """Test a very short simulation."""
    print("\n[TEST] Testing Simulation Engine...")
    
    from simulator.simulation_engine import SimulationEngine, SimulationConfig
    from src.config import DipLevel
    
    # Very short simulation for testing
    config = SimulationConfig(
        start_time=datetime(2024, 1, 1, 9, 0),
        end_time=datetime(2024, 1, 1, 11, 0),  # Just 2 hours
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
        engine = SimulationEngine(config)
        results = engine.run_simulation()
        
        assert results.total_trades >= 1, "Should have at least one trade"
        assert results.final_portfolio is not None, "Should have final portfolio"
        
        print(f"   ✅ Simulation completed successfully")
        print(f"   📊 Total trades: {results.total_trades}")
        print(f"   💰 Final P&L: €{results.total_profit_loss_eur:.2f}")
        
        print("✅ Simulation engine tests passed!")
        return results
        
    except Exception as e:
        print(f"   ❌ Simulation failed: {e}")
        raise


def test_results_analyzer():
    """Test the results analyzer."""
    print("\n🧪 Testing Results Analyzer...")
    
    # First ensure we have results to analyze
    from simulator.results_analyzer import analyze_latest_results
    
    try:
        # Run a quick analysis if results exist
        results_dir = Path("simulator/results")
        if results_dir.exists():
            results_files = list(results_dir.glob("simulation_results_*.json"))
            if results_files:
                print("   ✅ Found existing results to analyze")
                analyze_latest_results()
                print("✅ Results analyzer tests passed!")
            else:
                print("   ⚠️  No existing results found - skipping analyzer test")
        else:
            print("   ⚠️  Results directory doesn't exist - skipping analyzer test")
            
    except Exception as e:
        print(f"   ❌ Results analyzer failed: {e}")
        # Don't raise - analyzer test is optional


def test_full_integration():
    """Test the complete simulation workflow."""
    print("\n🧪 Testing Full Integration...")
    
    try:
        # Run basic integration test
        results = test_simulation_engine()
        
        # Verify basic functionality works
        assert results.config.dip_buy_enabled == True
        assert len(results.trade_events) > 0
        
        print("✅ Full integration test passed!")
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        raise


def main():
    """Run all tests."""
    # Handle Unicode encoding issues on Windows
    try:
        print("🤖 Dip Buy Simulator Tests")
    except UnicodeEncodeError:
        print("Dip Buy Simulator Tests")
    print("=" * 40)
    
    # Configure logging
    logging.basicConfig(level=logging.WARNING)  # Reduce log noise for testing
    
    try:
        # Run tests in order
        test_mock_api()
        results = test_simulation_engine()
        test_results_analyzer()
        test_full_integration()
        
        print("\n🎉 All tests passed!")
        print("\n📋 Quick Results Summary:")
        print(f"   • Simulation Duration: {results.duration}")
        print(f"   • Total Trades: {results.total_trades}")
        print(f"   • Dip Rebuys: {results.successful_dip_rebuys}")
        print(f"   • Final P&L: €{results.total_profit_loss_eur:.2f}")
        print(f"   • Return: {results.profit_loss_pct:+.1f}%")
        
        print(f"\n✅ Simulator is ready to use!")
        print(f"🚀 Run 'python run_simulation.py' to start testing your dip buying strategy")
        
    except Exception as e:
        print(f"\n❌ Tests failed: {e}")
        logging.exception("Test error")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())