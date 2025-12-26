import argparse
import sys
import os
from datetime import datetime

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from pead_agent.engine import DecisionEngine
from pead_agent.backtesting.engine import BacktestingEngine
from pead_agent.backtesting.portfolio import Portfolio
from pead_agent.backtesting.execution import BacktestExecutionManager
from pead_agent.backtesting.stubs import (
    HistoricalPEADAnalyzer,
    HistoricalTechnicalAnalyzer,
    HistoricalFundamentalAnalyzer,
    HistoricalGovernanceAnalyzer,
    StubNewsSentimentAnalyzer,
    StubInstitutionalFlowAnalyzer,
)
import yaml

def load_config():
    """Loads the YAML configuration file."""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yml")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def main():
    """
    Main entry point for the backtester.
    """
    parser = argparse.ArgumentParser(description="PEAD Agent Backtester")
    parser.add_argument("--symbol", type=str, required=True, help="Stock symbol to backtest (e.g., RELIANCE)")
    parser.add_argument("--start", type=str, required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, required=True, help="End date (YYYY-MM-DD)")
    args = parser.parse_args()

    start_date = datetime.strptime(args.start, "%Y-%m-%d").date()
    end_date = datetime.strptime(args.end, "%Y-%m-%d").date()

    config = load_config()

    # --- Setup Backtesting Dependencies ---
    portfolio = Portfolio(initial_cash=100000.0)
    backtest_execution_manager = BacktestExecutionManager(portfolio)

    # Initialize the decision engine with historical stubs and the backtest execution manager
    decision_engine = DecisionEngine(
        pead_analyzer=HistoricalPEADAnalyzer(),
        technical_analyzer=HistoricalTechnicalAnalyzer(),
        fundamental_analyzer=HistoricalFundamentalAnalyzer(),
        news_analyzer=StubNewsSentimentAnalyzer(),
        governance_analyzer=HistoricalGovernanceAnalyzer(),
        flow_analyzer=StubInstitutionalFlowAnalyzer(),
        execution_manager=backtest_execution_manager, # Use the backtest one
        config=config,
    )

    # Initialize and run the backtesting engine
    backtesting_engine = BacktestingEngine(decision_engine)
    backtesting_engine.run(
        symbols=[args.symbol],
        start_date=start_date,
        end_date=end_date,
    )

    # Print a summary of the trades
    print("\n--- Backtest Trade Summary ---")
    if not portfolio.trades:
        print("No trades were executed.")
    else:
        for trade in portfolio.trades:
            print(f"  - {trade['date']}: {trade['side']} {trade['quantity']} of {trade['symbol']} @ {trade['price']}")

    # --- Performance Summary ---
    print("\n--- Performance Summary ---")
    # To get a final portfolio value, we need the price at the end of the backtest period.
    from pead_agent.backtesting.execution import get_price_for_date
    final_prices = {args.symbol: get_price_for_date(args.symbol, end_date)}

    final_value = portfolio.get_current_value(final_prices)
    total_pnl = final_value - portfolio.initial_cash

    print(f"Initial Portfolio Value: {portfolio.initial_cash:.2f}")
    print(f"Final Portfolio Value:   {final_value:.2f}")
    print(f"Total PnL:               {total_pnl:.2f}")


if __name__ == "__main__":
    main()
