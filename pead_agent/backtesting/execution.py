from datetime import date
from pead_agent.backtesting.portfolio import Portfolio

# --- Mock Historical Price Data ---
# This dictionary simulates the price of a stock on specific dates.
HISTORICAL_PRICES = {
    "RELIANCE": {
        date(2023, 1, 15): 100.0,
        date(2023, 3, 10): 110.0, # Price increased
        date(2023, 5, 20): 95.0,  # Price decreased
    }
}

def get_price_for_date(symbol: str, trade_date: date) -> float:
    """
    A mock function to get the price of a stock on a specific date.
    If the exact date is not found, it returns the most recent known price.
    """
    price_data = HISTORICAL_PRICES.get(symbol, {})

    # Find the most recent price on or before the trade date
    relevant_dates = [d for d in price_data.keys() if d <= trade_date]
    if not relevant_dates:
        print(f"WARNING: No historical price data for {symbol} on or before {trade_date}. Defaulting to 100.0.")
        return 100.0

    most_recent_date = max(relevant_dates)
    price = price_data[most_recent_date]
    print(f"INFO: Using price {price} for {symbol} from {most_recent_date} for trade on {trade_date}")
    return price


class BacktestExecutionManager:
    """
    A simulated execution manager for backtesting.
    It records trades in a portfolio instead of placing live orders.
    """

    def __init__(self, portfolio: Portfolio):
        self.portfolio = portfolio

    def execute_trade(self, decision: dict, config: dict, trade_date: date):
        """
        Records a trade in the portfolio based on the agent's decision.

        Args:
            decision: The decision dictionary from the DecisionEngine.
            config: The execution configuration.
            trade_date: The date of the simulated trade.
        """
        final_verdict = decision.get("verdict")
        stock_symbol = decision.get("stock")

        if final_verdict not in ["STRONG BUY", "BUY", "SELL"]:
            return  # No action taken

        side = "BUY" if final_verdict in ["STRONG BUY", "BUY"] else "SELL"
        quantity = config.get("order_quantity", 1)

        price = get_price_for_date(stock_symbol, trade_date)

        self.portfolio.record_trade(
            trade_date=trade_date,
            symbol=stock_symbol,
            quantity=quantity,
            price=price,
            side=side
        )
