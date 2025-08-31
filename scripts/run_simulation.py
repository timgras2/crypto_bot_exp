#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dip Buy Strategy Simulation Runner
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

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from simulator.simulation_engine import SimulationEngine, SimulationConfig
from src.config import DipLevel


def run_basic_simulation():
    """Run a basic simulation with default parameters."""
    # Configure simulation
    config = SimulationConfig(
        start_time=datetime(2024, 1, 1, 9, 0),
        end_time=datetime(2024, 1, 7, 17, 0),  # 1 week simulation
        initial_balance_eur=Decimal("1000"),
        max_trade_amount=Decimal("10"),
        simulation_speed=1440.0,  # 1440x speed (1 day = 1 minute)
        assets_to_simulate=["PUMP-EUR", "DOGE-EUR", "ADA-EUR"],
        dip_buy_enabled=True,
        dip_levels=[
            DipLevel(threshold_pct=Decimal('10'), capital_allocation=Decimal('0.4')),
            DipLevel(threshold_pct=Decimal('20'), capital_allocation=Decimal('0.35')),
            DipLevel(threshold_pct=Decimal('35'), capital_allocation=Decimal('0.25'))
        ]
    )
    
    # Run simulation
    engine = SimulationEngine(config)
    results = engine.run_simulation()
    
    return results


def run_comparison_simulations():
    """Run multiple simulations to compare dip buying vs no dip buying."""
    print("🔬 Running comparison simulations...")
    
    base_config = SimulationConfig(
        start_time=datetime(2024, 1, 1, 9, 0),
        end_time=datetime(2024, 1, 14, 17, 0),  # 2 weeks
        initial_balance_eur=Decimal("1000"),
        max_trade_amount=Decimal("10"),
        simulation_speed=720.0,  # 720x speed (1 day = 2 minutes)
        assets_to_simulate=["PUMP-EUR", "DOGE-EUR", "ADA-EUR", "DOT-EUR"]
    )
    
    # Simulation 1: With dip buying
    print("\n1️⃣ Simulation WITH dip buying...")
    config_with_dip = base_config
    config_with_dip.dip_buy_enabled = True
    
    engine_with_dip = SimulationEngine(config_with_dip)
    results_with_dip = engine_with_dip.run_simulation()
    
    # Simulation 2: Without dip buying
    print("\n2️⃣ Simulation WITHOUT dip buying...")
    config_no_dip = SimulationConfig(
        start_time=base_config.start_time,
        end_time=base_config.end_time,
        initial_balance_eur=base_config.initial_balance_eur,
        max_trade_amount=base_config.max_trade_amount,
        simulation_speed=base_config.simulation_speed,
        assets_to_simulate=base_config.assets_to_simulate,
        dip_buy_enabled=False  # Key difference
    )
    
    engine_no_dip = SimulationEngine(config_no_dip)
    results_no_dip = engine_no_dip.run_simulation()
    
    # Compare results
    print("\n📊 COMPARISON RESULTS:")
    print("=" * 60)
    print(f"{'Metric':<25} {'With Dip Buy':<15} {'Without Dip Buy':<15} {'Difference':<15}")
    print("-" * 60)
    print(f"{'Total P&L (EUR)':<25} {results_with_dip.total_profit_loss_eur:>12.2f} {results_no_dip.total_profit_loss_eur:>14.2f} {results_with_dip.total_profit_loss_eur - results_no_dip.total_profit_loss_eur:>12.2f}")
    print(f"{'P&L Percentage':<25} {results_with_dip.profit_loss_pct:>11.1f}% {results_no_dip.profit_loss_pct:>13.1f}% {results_with_dip.profit_loss_pct - results_no_dip.profit_loss_pct:>11.1f}%")
    print(f"{'Total Trades':<25} {results_with_dip.total_trades:>14d} {results_no_dip.total_trades:>14d} {results_with_dip.total_trades - results_no_dip.total_trades:>14d}")
    print(f"{'Dip Rebuys':<25} {results_with_dip.successful_dip_rebuys:>14d} {results_no_dip.successful_dip_rebuys:>14d} {results_with_dip.successful_dip_rebuys - results_no_dip.successful_dip_rebuys:>14d}")
    
    improvement = results_with_dip.total_profit_loss_eur - results_no_dip.total_profit_loss_eur
    if improvement > 0:
        print(f"\n✅ Dip buying strategy improved returns by €{improvement:.2f}!")
    elif improvement < 0:
        print(f"\n❌ Dip buying strategy reduced returns by €{abs(improvement):.2f}")
    else:
        print(f"\n➖ No significant difference between strategies")
    
    return results_with_dip, results_no_dip


def run_parameter_testing():
    """Test different dip buying parameters."""
    print("🧪 Testing different dip buying parameters...")
    
    base_config = SimulationConfig(
        start_time=datetime(2024, 1, 1, 9, 0),
        end_time=datetime(2024, 1, 10, 17, 0),  # 10 days
        initial_balance_eur=Decimal("1000"),
        max_trade_amount=Decimal("10"),
        simulation_speed=1440.0,  # Fast simulation
        assets_to_simulate=["PUMP-EUR", "DOGE-EUR"]
    )
    
    # Test different dip level configurations
    configurations = [
        {
            "name": "Conservative (Single Level)",
            "levels": [DipLevel(threshold_pct=Decimal('15'), capital_allocation=Decimal('1.0'))]
        },
        {
            "name": "Aggressive (Early Entry)",
            "levels": [
                DipLevel(threshold_pct=Decimal('5'), capital_allocation=Decimal('0.5')),
                DipLevel(threshold_pct=Decimal('10'), capital_allocation=Decimal('0.3')),
                DipLevel(threshold_pct=Decimal('20'), capital_allocation=Decimal('0.2'))
            ]
        },
        {
            "name": "Patient (Deep Dips)",
            "levels": [
                DipLevel(threshold_pct=Decimal('20'), capital_allocation=Decimal('0.6')),
                DipLevel(threshold_pct=Decimal('40'), capital_allocation=Decimal('0.4'))
            ]
        }
    ]
    
    results = {}
    
    for config_info in configurations:
        print(f"\n🔬 Testing: {config_info['name']}")
        
        test_config = SimulationConfig(
            start_time=base_config.start_time,
            end_time=base_config.end_time,
            initial_balance_eur=base_config.initial_balance_eur,
            max_trade_amount=base_config.max_trade_amount,
            simulation_speed=base_config.simulation_speed,
            assets_to_simulate=base_config.assets_to_simulate,
            dip_buy_enabled=True,
            dip_levels=config_info['levels']
        )
        
        engine = SimulationEngine(test_config)
        result = engine.run_simulation()
        results[config_info['name']] = result
    
    # Compare parameter results
    print(f"\n📊 PARAMETER COMPARISON:")
    print("=" * 80)
    print(f"{'Strategy':<25} {'P&L (EUR)':<12} {'P&L %':<8} {'Trades':<8} {'Rebuys':<8}")
    print("-" * 80)
    
    for name, result in results.items():
        print(f"{name:<25} {result.total_profit_loss_eur:>9.2f} {result.profit_loss_pct:>6.1f}% {result.total_trades:>6d} {result.successful_dip_rebuys:>6d}")
    
    return results


def main():
    """Main simulation runner."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Handle Unicode encoding issues on Windows
    try:
        print("🤖 Dip Buy Strategy Simulator")
    except UnicodeEncodeError:
        print("Dip Buy Strategy Simulator")
    print("=" * 50)
    
    try:
        # Ask user what type of simulation to run
        print("\nChoose simulation type:")
        print("1. Basic simulation (1 week, default parameters)")
        print("2. Comparison (with vs without dip buying)")
        print("3. Parameter testing (different dip configurations)")
        print("4. All of the above")
        
        choice = "1"  # Default to basic simulation for automated run
        
        if choice == "1" or choice == "4":
            print("\n" + "="*50)
            print("RUNNING BASIC SIMULATION")
            print("="*50)
            run_basic_simulation()
        
        if choice == "2" or choice == "4":
            print("\n" + "="*50)
            print("RUNNING COMPARISON SIMULATIONS")
            print("="*50)
            run_comparison_simulations()
        
        if choice == "3" or choice == "4":
            print("\n" + "="*50)
            print("RUNNING PARAMETER TESTING")
            print("="*50)
            run_parameter_testing()
        
        print(f"\n🎉 All simulations completed!")
        print(f"📁 Check simulator/results/ folder for detailed results")
        
    except KeyboardInterrupt:
        print("\n⚠️ Simulation interrupted by user")
    except Exception as e:
        print(f"\n❌ Simulation failed: {e}")
        logging.exception("Simulation error")


if __name__ == "__main__":
    main()