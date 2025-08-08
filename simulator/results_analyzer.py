#!/usr/bin/env python3
"""
Simulation Results Analyzer - Analyze and visualize dip buying simulation results
"""

import json
import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TradeAnalysis:
    """Analysis of individual trade performance."""
    market: str
    initial_buy_price: Decimal
    sell_price: Decimal
    profit_loss_pct: float
    hold_duration: str
    dip_rebuys: List[Dict[str, Any]]
    final_outcome: str  # "profit", "loss", "breakeven"


class ResultsAnalyzer:
    """Analyze simulation results and generate insights."""
    
    def __init__(self, results_file: Path):
        self.results_file = results_file
        self.data = self._load_results()
        
    def _load_results(self) -> Dict[str, Any]:
        """Load results from JSON file."""
        try:
            with open(self.results_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load results from {self.results_file}: {e}")
            raise
    
    def generate_summary_report(self) -> str:
        """Generate a comprehensive summary report."""
        report = []
        report.append("📊 DIP BUY STRATEGY SIMULATION RESULTS")
        report.append("=" * 60)
        
        # Basic metrics
        config = self.data["config"]
        results = self.data["results"]
        
        report.append(f"\n🕐 SIMULATION PERIOD:")
        report.append(f"   Start: {config['start_time']}")
        report.append(f"   End: {config['end_time']}")
        report.append(f"   Speed: {config['simulation_speed']:.0f}x real-time")
        report.append(f"   Runtime: {results['duration_seconds']:.1f} seconds")
        
        report.append(f"\n💰 FINANCIAL PERFORMANCE:")
        report.append(f"   Initial Balance: €{config['initial_balance_eur']:.2f}")
        report.append(f"   Final P&L: €{results['total_profit_loss_eur']:+.2f}")
        report.append(f"   Return: {results['profit_loss_pct']:+.1f}%")
        
        report.append(f"\n📈 TRADING ACTIVITY:")
        report.append(f"   Total Trades: {results['total_trades']}")
        report.append(f"   Successful Dip Rebuys: {results['successful_dip_rebuys']}")
        report.append(f"   Assets Traded: {', '.join(config['assets_to_simulate'])}")
        
        # Dip buy effectiveness
        dip_eff = results['dip_buy_effectiveness']
        report.append(f"\n🎯 DIP BUYING EFFECTIVENESS:")
        report.append(f"   Dip Opportunities: {dip_eff['total_dip_opportunities']}")
        report.append(f"   Successful Rebuys: {dip_eff['successful_dip_rebuys']}")
        if dip_eff['total_dip_opportunities'] > 0:
            success_rate = (dip_eff['successful_dip_rebuys'] / dip_eff['total_dip_opportunities']) * 100
            report.append(f"   Success Rate: {success_rate:.1f}%")
        
        if dip_eff['avg_rebuy_amount'] > 0:
            report.append(f"   Avg Rebuy Amount: €{dip_eff['avg_rebuy_amount']:.2f}")
        
        # Rebuys by level
        if dip_eff.get('rebuys_by_level'):
            report.append(f"\n📊 REBUYS BY DIP LEVEL:")
            for level, count in dip_eff['rebuys_by_level'].items():
                report.append(f"   Level {level}: {count} rebuys")
        
        return "\n".join(report)
    
    def analyze_trades_by_asset(self) -> Dict[str, TradeAnalysis]:
        """Analyze trading performance for each asset."""
        trade_events = self.data["trade_events"]
        analyses = {}
        
        # Group events by market
        events_by_market = {}
        for event in trade_events:
            market = event["market"]
            if market not in events_by_market:
                events_by_market[market] = []
            events_by_market[market].append(event)
        
        # Analyze each market
        for market, events in events_by_market.items():
            analysis = self._analyze_market_trades(market, events)
            if analysis:
                analyses[market] = analysis
        
        return analyses
    
    def _analyze_market_trades(self, market: str, events: List[Dict[str, Any]]) -> Optional[TradeAnalysis]:
        """Analyze trades for a specific market."""
        # Sort events by timestamp
        events.sort(key=lambda x: x["timestamp"])
        
        # Find initial buy and final outcome
        initial_buy = None
        final_sell = None
        dip_rebuys = []
        
        for event in events:
            if event["event_type"] == "initial_buy":
                initial_buy = event
            elif event["event_type"] == "trailing_stop_sell":
                final_sell = event
            elif event["event_type"] == "dip_rebuy":
                dip_rebuys.append(event)
        
        if not initial_buy:
            return None
        
        # Calculate metrics
        initial_price = Decimal(str(initial_buy["price"]))
        
        if final_sell:
            sell_price = Decimal(str(final_sell["price"]))
            profit_loss_pct = float(((sell_price - initial_price) / initial_price) * 100)
            
            # Calculate hold duration
            start_time = datetime.fromisoformat(initial_buy["timestamp"])
            end_time = datetime.fromisoformat(final_sell["timestamp"])
            duration = end_time - start_time
            hold_duration = str(duration).split(".")[0]  # Remove microseconds
            
            if profit_loss_pct > 0.1:
                outcome = "profit"
            elif profit_loss_pct < -0.1:
                outcome = "loss"
            else:
                outcome = "breakeven"
        else:
            # Position still open
            sell_price = initial_price  # Assume breakeven for open positions
            profit_loss_pct = 0.0
            hold_duration = "position_open"
            outcome = "open"
        
        return TradeAnalysis(
            market=market,
            initial_buy_price=initial_price,
            sell_price=sell_price,
            profit_loss_pct=profit_loss_pct,
            hold_duration=hold_duration,
            dip_rebuys=dip_rebuys,
            final_outcome=outcome
        )
    
    def generate_detailed_trade_report(self) -> str:
        """Generate detailed trade-by-trade analysis."""
        analyses = self.analyze_trades_by_asset()
        
        report = []
        report.append("\n📋 DETAILED TRADE ANALYSIS")
        report.append("=" * 60)
        
        for market, analysis in analyses.items():
            report.append(f"\n🏷️  {market}")
            report.append(f"   Initial Buy: €{analysis.initial_buy_price:.6f}")
            report.append(f"   Final Price: €{analysis.sell_price:.6f}")
            report.append(f"   P&L: {analysis.profit_loss_pct:+.1f}%")
            report.append(f"   Duration: {analysis.hold_duration}")
            report.append(f"   Outcome: {analysis.final_outcome.upper()}")
            
            if analysis.dip_rebuys:
                report.append(f"   Dip Rebuys: {len(analysis.dip_rebuys)}")
                for i, rebuy in enumerate(analysis.dip_rebuys, 1):
                    level = rebuy.get("dip_level", "?")
                    price = rebuy["price"]
                    amount = rebuy["amount_eur"]
                    reason = rebuy.get("trigger_reason", "")
                    report.append(f"     #{i}: Level {level} at €{price:.6f} (€{amount:.2f}) - {reason}")
            else:
                report.append("   Dip Rebuys: None")
        
        return "\n".join(report)
    
    def calculate_performance_metrics(self) -> Dict[str, Any]:
        """Calculate advanced performance metrics."""
        trade_events = self.data["trade_events"]
        results = self.data["results"]
        config = self.data["config"]
        
        # Basic metrics
        total_return_pct = results["profit_loss_pct"]
        total_trades = results["total_trades"]
        successful_rebuys = results["successful_dip_rebuys"]
        
        # Calculate metrics by trade type
        buy_events = [e for e in trade_events if e["event_type"] in ["initial_buy", "dip_rebuy"]]
        sell_events = [e for e in trade_events if e["event_type"] == "trailing_stop_sell"]
        
        # Average trade amounts
        avg_buy_amount = sum(e["amount_eur"] for e in buy_events) / len(buy_events) if buy_events else 0
        avg_sell_amount = sum(e["amount_eur"] for e in sell_events) / len(sell_events) if sell_events else 0
        
        # Time-based metrics
        if trade_events:
            start_time = datetime.fromisoformat(trade_events[0]["timestamp"])
            end_time = datetime.fromisoformat(trade_events[-1]["timestamp"])
            trading_duration = (end_time - start_time).total_seconds() / 3600  # Hours
            trades_per_hour = total_trades / trading_duration if trading_duration > 0 else 0
        else:
            trading_duration = 0
            trades_per_hour = 0
        
        # Dip buying specific metrics
        dip_effectiveness = results["dip_buy_effectiveness"]
        rebuy_success_rate = (
            dip_effectiveness["successful_dip_rebuys"] / dip_effectiveness["total_dip_opportunities"] * 100
            if dip_effectiveness["total_dip_opportunities"] > 0 else 0
        )
        
        return {
            "total_return_pct": total_return_pct,
            "total_trades": total_trades,
            "avg_buy_amount": avg_buy_amount,
            "avg_sell_amount": avg_sell_amount,
            "trading_duration_hours": trading_duration,
            "trades_per_hour": trades_per_hour,
            "rebuy_success_rate": rebuy_success_rate,
            "successful_rebuys": successful_rebuys,
            "capital_efficiency": total_return_pct / config["initial_balance_eur"] * 100 if config["initial_balance_eur"] > 0 else 0
        }
    
    def generate_recommendations(self) -> List[str]:
        """Generate recommendations based on simulation results."""
        recommendations = []
        
        metrics = self.calculate_performance_metrics()
        results = self.data["results"]
        dip_eff = results["dip_buy_effectiveness"]
        
        # Performance-based recommendations
        if results["profit_loss_pct"] < -5:
            recommendations.append("❌ Consider reducing trade amounts or tightening risk controls")
        elif results["profit_loss_pct"] > 10:
            recommendations.append("✅ Strategy shows strong performance - consider increasing position sizes")
        
        # Dip buying effectiveness
        if metrics["rebuy_success_rate"] < 30:
            recommendations.append("🎯 Low dip rebuy success rate - consider adjusting dip thresholds")
        elif metrics["rebuy_success_rate"] > 70:
            recommendations.append("🎯 High dip rebuy success rate - strategy is working well")
        
        # Trade frequency
        if metrics["trades_per_hour"] > 2:
            recommendations.append("⚡ High trading frequency - monitor for over-trading")
        elif metrics["trades_per_hour"] < 0.1:
            recommendations.append("🐌 Low trading activity - consider more aggressive parameters")
        
        # Rebuys by level analysis
        rebuys_by_level = dip_eff.get("rebuys_by_level", {})
        if rebuys_by_level:
            max_level = max(rebuys_by_level.keys()) if rebuys_by_level else 0
            min_level = min(rebuys_by_level.keys()) if rebuys_by_level else 0
            
            if str(max_level) == "1":
                recommendations.append("📊 Most rebuys at shallow dips - consider deeper dip levels")
            elif str(min_level) == "3":
                recommendations.append("📊 Most rebuys at deep dips - consider shallower entry points")
        
        if not recommendations:
            recommendations.append("✅ Strategy performance within normal parameters")
        
        return recommendations
    
    def save_analysis_report(self, output_file: Optional[Path] = None) -> Path:
        """Save complete analysis report to file."""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.results_file.parent / f"analysis_{timestamp}.txt"
        
        report_sections = [
            self.generate_summary_report(),
            self.generate_detailed_trade_report(),
            "\n🔍 PERFORMANCE METRICS:",
            "=" * 30
        ]
        
        # Add performance metrics
        metrics = self.calculate_performance_metrics()
        for key, value in metrics.items():
            if isinstance(value, float):
                report_sections.append(f"{key}: {value:.2f}")
            else:
                report_sections.append(f"{key}: {value}")
        
        # Add recommendations
        recommendations = self.generate_recommendations()
        report_sections.extend([
            "\n💡 RECOMMENDATIONS:",
            "=" * 20
        ])
        report_sections.extend(recommendations)
        
        # Write to file
        full_report = "\n".join(report_sections)
        output_file.write_text(full_report)
        
        print(f"📊 Analysis report saved to: {output_file}")
        return output_file


def analyze_latest_results() -> None:
    """Analyze the most recent simulation results."""
    results_dir = Path("simulator/results")
    
    if not results_dir.exists():
        print("❌ No simulation results found. Run a simulation first.")
        return
    
    # Find the most recent results file
    results_files = list(results_dir.glob("simulation_results_*.json"))
    if not results_files:
        print("❌ No simulation results found. Run a simulation first.")
        return
    
    latest_file = max(results_files, key=lambda f: f.stat().st_mtime)
    print(f"📊 Analyzing results from: {latest_file.name}")
    
    try:
        analyzer = ResultsAnalyzer(latest_file)
        
        # Display summary
        print(analyzer.generate_summary_report())
        print(analyzer.generate_detailed_trade_report())
        
        # Show recommendations
        recommendations = analyzer.generate_recommendations()
        print("\n💡 RECOMMENDATIONS:")
        print("=" * 20)
        for rec in recommendations:
            print(f"   {rec}")
        
        # Save detailed analysis
        analyzer.save_analysis_report()
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        logging.exception("Analysis error")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    analyze_latest_results()