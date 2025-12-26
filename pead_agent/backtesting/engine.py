from datetime import date, timedelta
from typing import List
from pead_agent.engine import DecisionEngine

class BacktestingEngine:
    """
    Manages the backtesting simulation loop.
    """

    def __init__(self, decision_engine: DecisionEngine):
        self.decision_engine = decision_engine

    def run(self, symbols: List[str], start_date: date, end_date: date):
        """
        Runs the backtesting simulation.

        Args:
            symbols: A list of stock symbols to backtest.
            start_date: The start date of the simulation.
            end_date: The end date of the simulation.
        """
        print(f"--- Starting Backtest ---")
        print(f"Date Range: {start_date} to {end_date}")
        print(f"Symbols: {symbols}")

        current_date = start_date
        while current_date <= end_date:
            print(f"--- Processing Date: {current_date} ---")
            for symbol in symbols:
                # In a real backtester, we would check if there's a reason to analyze
                # (e.g., earnings announcement). Here, we analyze every day.
                print(f"Analyzing {symbol} for {current_date}...")

                # The DecisionEngine is now configured with the historical stubs
                # and the backtest execution manager.
                self.decision_engine.run_analysis(
                    stock_symbol=symbol,
                    analysis_date=current_date
                )

            current_date += timedelta(days=1)

        print("--- Backtest Finished ---")
